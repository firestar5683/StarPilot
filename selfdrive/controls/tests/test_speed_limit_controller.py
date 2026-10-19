from datetime import UTC, datetime
from concurrent.futures import Future
from types import SimpleNamespace

import pytest

from cereal import custom
from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL
from openpilot.starpilot.controls.lib.speed_limit_controller import (
  SOURCE_DASHBOARD, SOURCE_MAP, SOURCE_MAPBOX, SOURCE_NONE, SOURCE_PREVIOUS_LIMIT, SOURCE_VISION, SpeedLimitController,
)
from openpilot.starpilot.controls.lib.mapbox_speed_limit import MapboxSpeedLimit


def mph(speed):
  return speed * CV.MPH_TO_MS


class FakeParams:
  def __init__(self, values=None):
    self.values = dict(values or {})
    self.writes = []

  def get(self, key, encoding=None):
    return self.values.get(key)

  def get_bool(self, key):
    return bool(self.values.get(key, False))

  def get_float(self, key):
    return float(self.values.get(key, 0) or 0)

  def get_int(self, key):
    return int(self.values.get(key, 0) or 0)

  def put_float(self, key, value):
    self.values[key] = value

  def put_nonblocking(self, key, value):
    self.values[key] = value
    self.writes.append((key, value))

  def remove(self, key):
    self.values.pop(key, None)


def make_toggles(**overrides):
  defaults = {
    "is_metric": False,
    "map_speed_lookahead_higher": 0.0,
    "map_speed_lookahead_lower": 0.0,
    "slc_fallback_experimental_mode": False,
    "slc_fallback_previous_speed_limit": False,
    "slc_fallback_set_speed": False,
    "slc_mapbox_filler": False,
    "speed_limit_confirmation_higher": False,
    "speed_limit_confirmation_lower": False,
    "redneck_cruise": False,
    "speed_limit_priority1": SOURCE_DASHBOARD,
    "speed_limit_priority2": SOURCE_MAP,
    "speed_limit_priority_highest": False,
    "speed_limit_priority_lowest": False,
    "vision_speed_limit_detection": False,
    "vision_speed_limit_low_limit_filter": False,
    "vision_speed_limit_low_limit_threshold": mph(25),
  }
  defaults.update({f"speed_limit_offset{i}": 0.0 for i in range(1, 8)})
  defaults.update(overrides)
  return SimpleNamespace(**defaults)


@pytest.fixture
def controller_factory():
  controllers = []

  def create(*, persisted=0.0, **toggles):
    params = FakeParams({"PreviousSpeedLimit": persisted} if persisted else {})
    planner = SimpleNamespace(
      gps_position={}, gps_valid=False, params=params, params_memory=FakeParams(),
    )
    controller = SpeedLimitController(SimpleNamespace(starpilot_planner=planner))
    controller.starpilot_toggles = make_toggles(**toggles)
    controllers.append(controller)
    return controller

  yield create
  for controller in controllers:
    controller.shutdown()


def step(controller, *, dashboard=0.0, map_limit=0.0, way=custom.WaySelectionType.fail,
         next_limit=0.0, next_distance=0.0, road="", cruise=None, ego=None,
         enabled=True, long_active=True, accel=False, decel=False, gas=False,
         standstill=False, active=True, display_only=False, vision=None, support_count=0,
         support_speed=0.0, cruise_diff=0.0, ego_diff=0.0):
  cruise = mph(60) if cruise is None else cruise
  ego = mph(50) if ego is None else ego
  memory = controller.starpilot_planner.params_memory
  if vision is not None:
    memory.put_float("VisionSpeedLimit", vision)
    memory.values["VisionSpeedLimitSupportCount"] = support_count
    memory.put_float("VisionSpeedLimitSupportSpeed", support_speed)
  sm = {
    "carControl": SimpleNamespace(longActive=long_active),
    "carState": SimpleNamespace(gasPressed=gas, steeringAngleDeg=0.0, standstill=standstill,
                                vCruise=cruise / CV.KPH_TO_MS),
    "liveParameters": SimpleNamespace(angleOffsetDeg=0.0),
    "mapdOut": SimpleNamespace(nextSpeedLimitDistance=next_distance, nextSpeedLimit=next_limit,
                                speedLimit=map_limit, waySelectionType=way, roadName=road),
    "selfdriveState": SimpleNamespace(enabled=enabled),
    "starpilotCarState": SimpleNamespace(accelPressed=accel, decelPressed=decel),
  }
  controller.update(dashboard, datetime.now(UTC), False, cruise, cruise_diff, ego, ego_diff, sm,
                    active=active, display_only=display_only)
  return sm


@pytest.mark.parametrize(
  ("priority1", "priority2", "highest", "lowest", "expected_source", "expected_speed"),
  [
    (SOURCE_DASHBOARD, SOURCE_MAP, False, False, SOURCE_DASHBOARD, 45),
    (SOURCE_MAP, SOURCE_DASHBOARD, False, False, SOURCE_MAP, 55),
    (SOURCE_DASHBOARD, SOURCE_MAP, True, False, SOURCE_MAP, 55),
    (SOURCE_DASHBOARD, SOURCE_MAP, False, True, SOURCE_DASHBOARD, 45),
    (SOURCE_VISION, SOURCE_DASHBOARD, False, False, SOURCE_VISION, 65),
  ],
)
def test_source_selection(controller_factory, priority1, priority2, highest, lowest, expected_source, expected_speed):
  controller = controller_factory(
    speed_limit_priority1=priority1, speed_limit_priority2=priority2,
    speed_limit_priority_highest=highest, speed_limit_priority_lowest=lowest,
    vision_speed_limit_detection=True,
  )
  step(controller, dashboard=mph(45), map_limit=mph(55), way=custom.WaySelectionType.current,
       vision=mph(65), cruise=mph(65))
  assert controller.source == expected_source
  assert controller.target == pytest.approx(mph(expected_speed))


def test_vision_only_participates_when_configured(controller_factory):
  controller = controller_factory(vision_speed_limit_detection=True)
  step(controller, vision=mph(45), cruise=mph(45))
  assert controller.source == SOURCE_NONE
  controller.starpilot_toggles.speed_limit_priority2 = SOURCE_VISION
  step(controller, vision=mph(45), cruise=mph(45))
  assert controller.source == SOURCE_VISION


def test_vision_filter_and_large_discrepancy_support(controller_factory):
  controller = controller_factory(
    speed_limit_priority1=SOURCE_VISION, vision_speed_limit_detection=True,
    vision_speed_limit_low_limit_filter=True,
  )
  step(controller, vision=mph(25), cruise=mph(25))
  assert controller.vision_limit == pytest.approx(mph(25))
  assert controller.source == SOURCE_NONE
  step(controller, vision=mph(70), cruise=mph(30), ego=mph(30), support_count=2, support_speed=mph(70))
  assert controller.source == SOURCE_NONE
  step(controller, vision=mph(70), cruise=mph(30), ego=mph(30), support_count=3, support_speed=mph(70))
  assert controller.source == SOURCE_VISION


def test_display_only_keeps_raw_vision_but_clears_control_state(controller_factory):
  controller = controller_factory(
    speed_limit_priority1=SOURCE_VISION, vision_speed_limit_detection=True,
    vision_speed_limit_low_limit_filter=True,
  )
  step(controller, vision=mph(15), cruise=mph(15), active=False, display_only=True)
  assert controller.source == SOURCE_VISION
  assert controller.target == pytest.approx(mph(15))
  assert controller.last_valid_limit == 0
  assert not controller.confirmation_pending
  assert controller.overridden_speed == 0


def test_map_lookahead_and_explicit_failure(controller_factory):
  controller = controller_factory(map_speed_lookahead_lower=5.0)
  step(controller, map_limit=mph(55), next_limit=mph(45), next_distance=100,
       way=custom.WaySelectionType.current, ego=mph(50))
  assert controller.map_speed_limit == pytest.approx(mph(45))
  assert controller.next_speed_limit == pytest.approx(mph(45))
  assert controller.last_valid_limit == pytest.approx(mph(45))
  step(controller, way=custom.WaySelectionType.fail)
  assert controller.map_speed_limit == 0
  assert controller.next_speed_limit == 0
  assert controller.source == SOURCE_NONE
  assert controller.last_valid_limit == pytest.approx(mph(45))


def test_predicted_map_retains_only_lower_candidate(controller_factory):
  controller = controller_factory()
  step(controller, map_limit=mph(55), way=custom.WaySelectionType.current)
  step(controller, map_limit=mph(65), way=custom.WaySelectionType.predicted)
  assert controller.map_speed_limit == pytest.approx(mph(55))
  step(controller, map_limit=mph(45), way=custom.WaySelectionType.possible)
  assert controller.map_speed_limit == pytest.approx(mph(45))


def test_mapbox_fills_absence_and_resets_for_primary_source(controller_factory):
  controller = controller_factory(slc_mapbox_filler=True)
  controller.starpilot_planner.gps_valid = True
  controller.mapbox.token = "test"
  step(controller, ego=0)
  controller.mapbox.limit = mph(45)
  controller.mapbox.segment_distance = 1000
  step(controller)
  assert controller.source == SOURCE_MAPBOX
  assert controller.last_valid_source == SOURCE_MAPBOX
  step(controller, dashboard=mph(55))
  assert controller.source == SOURCE_DASHBOARD
  assert controller.mapbox.limit == 0


def test_real_source_invalidates_inflight_mapbox_result(controller_factory):
  controller = controller_factory(slc_mapbox_filler=True)
  controller.starpilot_planner.gps_valid = True
  controller.mapbox.token = "test"
  old = Future()
  old.set_running_or_notify_cancel()
  controller.mapbox.future = old
  step(controller, dashboard=mph(45))
  assert controller.mapbox.future is None
  old.set_result((mph(65), 100.0))
  step(controller, dashboard=mph(45))
  assert controller.mapbox.limit == 0
  assert controller.source == SOURCE_DASHBOARD


@pytest.mark.parametrize("first_display_only", [False, True])
def test_mode_transition_invalidates_inflight_mapbox_result(controller_factory, first_display_only):
  controller = controller_factory(slc_mapbox_filler=True)
  controller.starpilot_planner.gps_valid = True
  controller.mapbox.token = "test"
  step(controller, ego=0, active=not first_display_only, display_only=first_display_only)
  old = Future()
  old.set_running_or_notify_cancel()
  controller.mapbox.future = old

  step(controller, ego=0, active=first_display_only, display_only=not first_display_only)
  assert controller.mapbox.future is None
  old.set_result((mph(65), 100.0))
  step(controller, ego=0, active=first_display_only, display_only=not first_display_only)
  assert controller.mapbox.limit == 0
  assert controller.source == SOURCE_NONE


def test_previous_fallback_keeps_real_history_and_session_source(controller_factory):
  controller = controller_factory(slc_fallback_previous_speed_limit=True)
  step(controller, dashboard=mph(45))
  writes = list(controller.starpilot_planner.params.writes)
  step(controller)
  assert controller.target == pytest.approx(mph(45))
  assert controller.source == SOURCE_DASHBOARD
  assert controller.last_valid_limit == pytest.approx(mph(45))
  assert controller.starpilot_planner.params.writes == writes


def test_previous_fallback_startup_has_unknown_source(controller_factory):
  controller = controller_factory(persisted=mph(45), slc_fallback_previous_speed_limit=True)
  step(controller)
  assert controller.target == pytest.approx(mph(45))
  assert controller.source == SOURCE_NONE
  assert controller.last_valid_source == SOURCE_NONE
  assert controller.presented_source == SOURCE_PREVIOUS_LIMIT


def test_set_speed_fallback_does_not_present_a_posted_limit(controller_factory):
  controller = controller_factory(persisted=mph(45), slc_fallback_set_speed=True)
  step(controller, cruise=mph(60))
  assert controller.target == pytest.approx(mph(60))
  assert controller.presented_source == SOURCE_NONE


@pytest.mark.parametrize("fallback", ["set", "experimental"])
def test_fallback_never_enters_accepted_history(controller_factory, fallback):
  controller = controller_factory(
    slc_fallback_set_speed=fallback == "set",
    slc_fallback_experimental_mode=fallback == "experimental",
  )
  step(controller, cruise=mph(60))
  assert controller.source == SOURCE_NONE
  assert controller.target == (mph(60) if fallback == "set" else 0.0)
  assert controller.experimental_mode == (fallback == "experimental")
  assert controller.last_valid_limit == 0
  assert controller.starpilot_planner.params.writes == []


def test_adopt_uses_real_candidate_only(controller_factory):
  controller = controller_factory(slc_fallback_set_speed=True)
  memory = controller.starpilot_planner.params_memory
  memory.values["SLCAdoptSpeedLimit"] = True
  step(controller, cruise=mph(60))
  assert controller.last_valid_limit == 0
  assert "SLCForceCruiseSpeed" not in memory.values
  assert "SLCAdoptSpeedLimit" not in memory.values
  memory.values["SLCAdoptSpeedLimit"] = True
  step(controller, dashboard=mph(45))
  assert controller.last_valid_limit == pytest.approx(mph(45))
  assert memory.get_float("SLCForceCruiseSpeed") == pytest.approx(mph(45))


def test_pending_candidate_changes_speed_and_source(controller_factory):
  controller = controller_factory(speed_limit_confirmation_lower=True, speed_limit_priority1=SOURCE_MAP,
                                  speed_limit_priority2=SOURCE_DASHBOARD)
  step(controller, dashboard=mph(65))
  step(controller, dashboard=mph(45))
  assert controller.confirmation_pending
  assert controller.pending_source == SOURCE_DASHBOARD
  assert controller.limit_change_started
  first_time = controller.confirmation_time
  step(controller, dashboard=mph(45))
  assert not controller.limit_change_started
  assert controller.confirmation_time > first_time
  step(controller, map_limit=mph(45), way=custom.WaySelectionType.current)
  assert controller.pending_source == SOURCE_MAP
  assert not controller.limit_change_started
  assert controller.confirmation_time > first_time
  step(controller, map_limit=mph(55), way=custom.WaySelectionType.current)
  assert controller.pending_limit == pytest.approx(mph(55))
  assert controller.pending_source == SOURCE_MAP
  assert controller.limit_change_started
  assert controller.confirmation_time == pytest.approx(DT_MDL)


def test_pending_disappearance_discards_stale_acceptance(controller_factory):
  controller = controller_factory(speed_limit_confirmation_lower=True)
  step(controller, dashboard=mph(55))
  step(controller, dashboard=mph(45))
  assert controller.confirmation_pending
  step(controller)
  assert not controller.confirmation_pending
  assert controller.confirmation_time == 0
  controller.starpilot_planner.params_memory.values["SpeedLimitAccepted"] = True
  step(controller)
  assert controller.last_valid_limit == pytest.approx(mph(55))
  assert "SpeedLimitAccepted" not in controller.starpilot_planner.params_memory.values


def test_ui_acceptance_only_accepts_stored_pending_candidate(controller_factory):
  controller = controller_factory(speed_limit_confirmation_lower=True)
  step(controller, dashboard=mph(65))
  step(controller, dashboard=mph(45))
  controller.starpilot_planner.params_memory.values["SpeedLimitAccepted"] = True
  step(controller, dashboard=mph(55))
  assert controller.pending_limit == pytest.approx(mph(55))
  assert controller.last_valid_limit == pytest.approx(mph(65))
  step(controller, dashboard=mph(55))
  assert controller.confirmation_pending
  controller.starpilot_planner.params_memory.values["SpeedLimitAccepted"] = True
  step(controller, dashboard=mph(55))
  assert controller.target == pytest.approx(mph(55))
  assert controller.last_valid_limit == pytest.approx(mph(55))


def test_accel_on_replacement_frame_does_not_accept_unshown_speed(controller_factory):
  controller = controller_factory(speed_limit_confirmation_lower=True)
  step(controller, dashboard=mph(65))
  step(controller, dashboard=mph(45))
  step(controller, dashboard=mph(55), accel=True)
  assert controller.pending_limit == pytest.approx(mph(55))
  assert controller.last_valid_limit == pytest.approx(mph(65))
  assert controller.confirmation_button_consumed
  step(controller, dashboard=mph(55), accel=True)
  assert controller.target == pytest.approx(mph(55))
  assert controller.last_valid_limit == pytest.approx(mph(55))


def test_accel_confirmation_consumes_adjacent_set_speed_edge(controller_factory):
  controller = controller_factory(speed_limit_confirmation_higher=True)
  step(controller, dashboard=mph(45), cruise=mph(45))
  step(controller, dashboard=mph(50), cruise=mph(45))
  step(controller, dashboard=mph(50), cruise=mph(45), accel=True)
  assert controller.target == pytest.approx(mph(50))
  assert controller.confirmation_button_consumed
  step(controller, dashboard=mph(50), cruise=mph(55))
  assert controller.overridden_speed == 0
  step(controller, dashboard=mph(50), cruise=mph(60), accel=True)
  assert controller.overridden_speed == pytest.approx(mph(60))


def test_higher_confirmation_forces_cruise_only_when_needed(controller_factory):
  controller = controller_factory(speed_limit_confirmation_higher=True, speed_limit_offset4=mph(5))
  step(controller, dashboard=mph(35), cruise=mph(40))
  step(controller, dashboard=mph(45), cruise=mph(40))
  controller.starpilot_planner.params_memory.values["SpeedLimitAccepted"] = True
  step(controller, dashboard=mph(45), cruise=mph(40))
  assert controller.target == pytest.approx(mph(45))
  assert controller.starpilot_planner.params_memory.get_float("SLCForceCruiseSpeed") == pytest.approx(mph(50))


def test_enabled_without_long_control_does_not_time_out_confirmation(controller_factory):
  controller = controller_factory(speed_limit_confirmation_lower=True)
  step(controller, dashboard=mph(55))
  for _ in range(int(30 / DT_MDL) + 1):
    step(controller, dashboard=mph(45), long_active=False, enabled=True)
  assert controller.confirmation_pending
  assert controller.denied_limit == 0


def test_rejection_and_timeout_do_not_change_history(controller_factory):
  controller = controller_factory(speed_limit_confirmation_lower=True)
  step(controller, dashboard=mph(55))
  writes = list(controller.starpilot_planner.params.writes)
  step(controller, dashboard=mph(45))
  step(controller, dashboard=mph(45), decel=True)
  assert controller.denied_limit == pytest.approx(mph(45))
  assert controller.presented_source == SOURCE_DASHBOARD
  assert controller.last_valid_limit == pytest.approx(mph(55))
  assert controller.starpilot_planner.params.writes == writes
  step(controller, dashboard=mph(45))
  assert not controller.confirmation_pending
  step(controller, dashboard=mph(40))
  for _ in range(int(30 / DT_MDL) + 1):
    step(controller, dashboard=mph(40))
  assert controller.denied_limit == pytest.approx(mph(40))
  assert controller.last_valid_limit == pytest.approx(mph(55))


def test_rejected_limit_does_not_label_set_speed_fallback_as_posted(controller_factory):
  controller = controller_factory(
    speed_limit_confirmation_lower=True,
    slc_fallback_set_speed=True,
  )
  step(controller, dashboard=mph(55))
  step(controller, dashboard=mph(45))
  step(controller, dashboard=mph(45), decel=True)
  assert controller.presented_source == SOURCE_DASHBOARD
  step(controller, cruise=mph(60))
  assert controller.target == pytest.approx(mph(60))
  assert controller.presented_source == SOURCE_NONE


def test_disabling_confirmation_accepts_a_previously_denied_limit(controller_factory):
  controller = controller_factory(speed_limit_confirmation_lower=True)
  step(controller, dashboard=mph(55))
  step(controller, dashboard=mph(45))
  step(controller, dashboard=mph(45), decel=True)
  assert controller.denied_limit == pytest.approx(mph(45))

  controller.starpilot_toggles.speed_limit_confirmation_lower = False
  step(controller, dashboard=mph(45))
  assert controller.source == SOURCE_DASHBOARD
  assert controller.target == pytest.approx(mph(45))
  assert controller.denied_limit == 0
  assert not controller.limit_change_started


def test_road_change_clears_denial_before_comparison(controller_factory):
  controller = controller_factory(speed_limit_priority1=SOURCE_MAP, speed_limit_confirmation_lower=True)
  step(controller, map_limit=mph(55), way=custom.WaySelectionType.current, road="Road A")
  step(controller, map_limit=mph(45), way=custom.WaySelectionType.current, road="Road A", decel=True)
  assert controller.denied_limit == pytest.approx(mph(45))
  step(controller, map_limit=mph(45), way=custom.WaySelectionType.current, road="Road B")
  assert controller.confirmation_pending
  assert controller.pending_limit == pytest.approx(mph(45))


def test_same_speed_source_change_does_not_alert_or_disturb_override(controller_factory):
  controller = controller_factory(speed_limit_priority1=SOURCE_MAP, speed_limit_priority2=SOURCE_DASHBOARD)
  step(controller, dashboard=mph(45), cruise=mph(45))
  step(controller, dashboard=mph(45), cruise=mph(60))
  assert controller.set_speed_override == pytest.approx(mph(60))
  step(controller, map_limit=mph(45), way=custom.WaySelectionType.current, cruise=mph(60))
  assert controller.source == SOURCE_MAP
  assert controller.last_valid_source == SOURCE_MAP
  assert not controller.limit_change_started
  assert controller.set_speed_override == pytest.approx(mph(60))


def test_equivalent_speed_churn_does_not_rewrite_persisted_limit(controller_factory):
  controller = controller_factory()
  step(controller, dashboard=mph(45))
  initial_writes = list(controller.starpilot_planner.params.writes)
  for speed in (45.5, 45, 45.5, 45):
    step(controller, dashboard=mph(speed))
  assert controller.starpilot_planner.params.writes == initial_writes
  assert controller.last_valid_limit == pytest.approx(mph(45))
  step(controller, dashboard=mph(50))
  assert controller.starpilot_planner.params.writes[-1] == ("PreviousSpeedLimit", mph(50))
  assert len(controller.starpilot_planner.params.writes) == len(initial_writes) + 1


def test_override_pedal_layers_over_persistent_and_new_lower_clears(controller_factory):
  controller = controller_factory()
  step(controller, dashboard=mph(45), cruise=mph(45), ego=mph(45))
  step(controller, dashboard=mph(45), cruise=mph(60), ego=mph(45))
  assert controller.overridden_speed == pytest.approx(mph(60))
  step(controller, dashboard=mph(45), cruise=mph(60), ego=mph(65), gas=True)
  assert controller.overridden_speed == pytest.approx(mph(65))
  step(controller, dashboard=mph(45), cruise=mph(60), ego=mph(50))
  assert controller.overridden_speed == pytest.approx(mph(60))
  step(controller, dashboard=mph(40), cruise=mph(60))
  assert controller.set_speed_override == 0
  assert controller.overridden_speed == 0


def test_higher_limit_clears_override_only_when_target_reaches_it(controller_factory):
  controller = controller_factory()
  step(controller, dashboard=mph(35), cruise=mph(35))
  step(controller, dashboard=mph(35), cruise=mph(55))
  step(controller, dashboard=mph(45), cruise=mph(55))
  assert controller.set_speed_override == pytest.approx(mph(55))
  step(controller, dashboard=mph(55), cruise=mph(55))
  assert controller.set_speed_override == 0


def test_higher_limit_with_offset_clears_reached_override(controller_factory):
  controller = controller_factory(speed_limit_offset4=mph(5))
  step(controller, dashboard=mph(35), cruise=mph(35))
  step(controller, dashboard=mph(35), cruise=mph(50))
  assert controller.set_speed_override == pytest.approx(mph(50))
  step(controller, dashboard=mph(45), cruise=mph(50))
  assert controller.set_speed_override == 0


def test_plus_after_automatic_acceptance_is_a_real_override_edge(controller_factory):
  controller = controller_factory()
  step(controller, dashboard=mph(45), cruise=mph(45))
  assert not controller.confirmation_pending
  step(controller, dashboard=mph(45), cruise=mph(55), accel=True)
  assert controller.set_speed_override == pytest.approx(mph(55))


def test_redneck_override_can_move_below_target(controller_factory):
  controller = controller_factory(redneck_cruise=True)
  step(controller, dashboard=mph(45), cruise=mph(45))
  step(controller, dashboard=mph(45), cruise=mph(60))
  step(controller, dashboard=mph(45), cruise=mph(35))
  assert controller.overridden_speed == pytest.approx(mph(35))


@pytest.mark.parametrize(
  ("manual_setting", "set_speed_setting"),
  [(False, False), (True, False), (False, True)],
)
def test_legacy_slc_override_setting_does_not_change_current_override_policy(
  controller_factory, manual_setting, set_speed_setting,
):
  controller = controller_factory(
    speed_limit_controller_override_manual=manual_setting,
    speed_limit_controller_override_set_speed=set_speed_setting,
  )
  step(controller, dashboard=mph(45), cruise=mph(45))
  step(controller, dashboard=mph(45), cruise=mph(55))
  assert controller.set_speed_override == pytest.approx(mph(55))
  step(controller, dashboard=mph(45), cruise=mph(55), ego=mph(60), gas=True)
  assert controller.pedal_override == pytest.approx(mph(60))


@pytest.mark.parametrize("display_only", [False, True])
def test_inactive_mode_clears_override_and_reseeds_set_speed(controller_factory, display_only):
  controller = controller_factory()
  step(controller, dashboard=mph(45), cruise=mph(45))
  step(controller, dashboard=mph(45), cruise=mph(60))
  assert controller.set_speed_override > 0
  step(controller, dashboard=mph(45), cruise=mph(70), active=False, display_only=display_only)
  assert controller.set_speed_override == 0
  assert controller.previous_set_speed is None
  step(controller, dashboard=mph(45), cruise=mph(70))
  assert controller.set_speed_override == 0
  assert controller.previous_set_speed == pytest.approx(mph(70))


def test_inactive_mode_consumes_stale_one_shots(controller_factory):
  controller = controller_factory(speed_limit_confirmation_lower=True)
  step(controller, dashboard=mph(55))
  step(controller, dashboard=mph(45))
  memory = controller.starpilot_planner.params_memory
  memory.values["SpeedLimitAccepted"] = True
  memory.values["SLCAdoptSpeedLimit"] = True
  step(controller, active=False)
  assert not controller.confirmation_pending
  assert "SpeedLimitAccepted" not in memory.values
  assert "SLCAdoptSpeedLimit" not in memory.values
  assert controller.last_valid_limit == pytest.approx(mph(55))


def test_brief_disengage_keeps_override_then_sustained_disengage_clears_it(controller_factory):
  controller = controller_factory()
  step(controller, dashboard=mph(45), cruise=mph(45))
  step(controller, dashboard=mph(45), cruise=mph(60))
  for _ in range(int(0.5 / DT_MDL)):
    step(controller, dashboard=mph(45), cruise=mph(60), enabled=False)
  assert controller.set_speed_override == pytest.approx(mph(60))
  for _ in range(int(0.5 / DT_MDL) + 1):
    step(controller, dashboard=mph(45), cruise=mph(60), enabled=False)
  assert controller.set_speed_override == 0


def test_disengaged_confirmation_auto_accepts_without_timing_out(controller_factory):
  controller = controller_factory(speed_limit_confirmation_lower=True)
  step(controller, dashboard=mph(55))
  step(controller, dashboard=mph(45), enabled=False, long_active=False)
  assert controller.target == pytest.approx(mph(45))
  assert not controller.confirmation_pending


def test_fully_disengaged_auto_accept_takes_precedence_over_decel(controller_factory):
  controller = controller_factory(speed_limit_confirmation_lower=True)
  step(controller, dashboard=mph(55))
  step(controller, dashboard=mph(45), enabled=False, long_active=False, decel=True)
  assert controller.target == pytest.approx(mph(45))
  assert controller.last_valid_limit == pytest.approx(mph(45))
  assert controller.denied_limit == 0


def test_presented_source_tracks_pending_candidate_and_rejected_accepted_limit(controller_factory):
  controller = controller_factory(speed_limit_confirmation_lower=True)
  step(controller, dashboard=mph(55))
  assert controller.presented_source == SOURCE_DASHBOARD

  step(controller, map_limit=mph(45), way=custom.WaySelectionType.current)
  assert controller.confirmation_pending
  assert controller.source == SOURCE_NONE
  assert controller.presented_source == SOURCE_MAP

  step(controller, map_limit=mph(45), way=custom.WaySelectionType.current, decel=True)
  assert not controller.confirmation_pending
  assert controller.presented_source == SOURCE_DASHBOARD

  step(controller)
  assert controller.presented_source == SOURCE_NONE


def test_explicit_accept_takes_precedence_over_simultaneous_reject(controller_factory):
  controller = controller_factory(speed_limit_confirmation_lower=True)
  step(controller, dashboard=mph(55))
  step(controller, dashboard=mph(45))
  step(controller, dashboard=mph(45), accel=True, decel=True)
  assert controller.target == pytest.approx(mph(45))
  assert controller.denied_limit == 0


def test_offset_bucket_boundary(controller_factory):
  controller = controller_factory(speed_limit_offset1=1.0, speed_limit_offset2=2.0)
  assert controller.get_offset(11.2) == 2.0


def test_mapbox_reset_discards_obsolete_future():
  helper = MapboxSpeedLimit(FakeParams({"MapboxSecretKey": "test"}))
  try:
    old = Future()
    old.set_running_or_notify_cancel()
    helper.future = old
    helper.reset()
    old.set_result((mph(45), 100.0))
    helper.update(datetime.now(UTC), False, 0.0, True, {}, 0.0, 0.0)
    assert helper.limit == 0

    newer = Future()
    newer.set_result((mph(55), 100.0))
    helper.future = newer
    helper.update(datetime.now(UTC), False, mph(40), True, {}, 0.0, 0.0)
    assert helper.limit == pytest.approx(mph(55))
    helper.requests["total_requests"] = helper.requests["max_requests"]
    helper.update(datetime.now(UTC), False, mph(40), True, {}, 0.0, 0.0)
    assert helper.limit == 0
  finally:
    helper.shutdown()


def test_mapbox_ping_failure_keeps_previous_retry_distance(monkeypatch):
  import openpilot.starpilot.controls.lib.mapbox_speed_limit as mapbox_module

  helper = MapboxSpeedLimit(FakeParams({"MapboxSecretKey": "test"}))
  try:
    monkeypatch.setattr(mapbox_module, "is_url_pingable", lambda _host: False)
    assert helper._request({}, mph(45)) == (0.0, mph(45))
  finally:
    helper.shutdown()


def test_mapbox_parses_first_segment_without_worker_state_mutation(monkeypatch):
  import openpilot.starpilot.controls.lib.mapbox_speed_limit as mapbox_module

  helper = MapboxSpeedLimit(FakeParams({"MapboxSecretKey": "test"}))
  try:
    monkeypatch.setattr(mapbox_module, "is_url_pingable", lambda _host: True)
    monkeypatch.setattr(mapbox_module, "calculate_bearing_offset", lambda *_args: (1.0, 2.0))
    response = SimpleNamespace(
      raise_for_status=lambda: None,
      json=lambda: {"matchings": [{"legs": [{"annotation": {
        "distance": [150.0], "maxspeed": [{"speed": 45, "unit": "mph"}],
      }}]}]},
    )
    monkeypatch.setattr(helper.session, "get", lambda *_args, **_kwargs: response)
    assert helper._request({"bearing": 0, "latitude": 0, "longitude": 0}, mph(40)) == pytest.approx((mph(45), 150.0))
    assert helper.limit == 0
  finally:
    helper.shutdown()
