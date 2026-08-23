from types import SimpleNamespace

from openpilot.common.constants import CV
from openpilot.starpilot.common.experimental_state import CCStatus
from openpilot.starpilot.controls.lib.conditional_chill_mode import ConditionalChillMode


class FakeParams:
  def __init__(self, bools=None, ints=None):
    self.bools = dict(bools or {})
    self.ints = dict(ints or {})

  def get_bool(self, key):
    return bool(self.bools.get(key, False))

  def put_bool(self, key, value):
    self.bools[key] = bool(value)

  def get_int(self, key, default=0):
    return int(self.ints.get(key, default))

  def put_int(self, key, value):
    self.ints[key] = int(value)


class FakeDetector:
  def __init__(self):
    self.curve_detected = False
    self.slow_lead_detected = False
    self.stop_light_detected = False
    self.stop_light_model_detected = False
    self.toggle_objects = []

  def curve_detection(self, _v_ego, toggles):
    self.toggle_objects.append(toggles)
    return None

  def slow_lead(self, toggles, _v_ego):
    self.toggle_objects.append(toggles)
    return None

  def stop_sign_and_light(self, *_args, **_kwargs):
    return None


class FakeSubMaster:
  def __init__(self, services):
    self.services = dict(services)

  def __getitem__(self, key):
    return self.services[key]


def make_sm():
  return {
    "carState": SimpleNamespace(standstill=False, leftBlinker=False, rightBlinker=False),
    "selfdriveState": SimpleNamespace(enabled=True),
    "longitudinalPlan": SimpleNamespace(allowThrottle=True, shouldStop=False),
    "starpilotCarState": SimpleNamespace(trafficModeEnabled=False),
    "starpilotPlan": SimpleNamespace(redLight=False, forcingStop=False),
    "starpilotRadarState": SimpleNamespace(
      leadLeft=SimpleNamespace(status=False, dRel=float("inf"), vLead=0.0),
      leadRight=SimpleNamespace(status=False, dRel=float("inf"), vLead=0.0),
    ),
  }


def make_submaster_sm():
  return FakeSubMaster(make_sm())


def make_toggles():
  return SimpleNamespace(
    conditional_chill_speed=45 * CV.MPH_TO_MS,
    conditional_chill_speed_lead=35 * CV.MPH_TO_MS,
    conditional_chill_speed_margin=3 * CV.MPH_TO_MS,
    conditional_chill_lead=True,
    conditional_chill_launch_assist=False,
  )


def make_ccm():
  planner = SimpleNamespace(
    params=FakeParams(),
    params_memory=FakeParams(),
    starpilot_vcruise=SimpleNamespace(
      stop_sign_confirmed=False,
      forcing_stop=False,
      slc=SimpleNamespace(experimental_mode=False),
    ),
    raw_model_stopped=False,
    model_stopped=False,
    tracking_lead=False,
    lead_one=SimpleNamespace(
      status=False,
      dRel=float("inf"),
      vLead=0.0,
      vRel=0.0,
      aLeadK=0.0,
      modelProb=0.0,
      radar=False,
    ),
  )
  detector = FakeDetector()
  return planner, detector, ConditionalChillMode(planner, detector)


def test_ccm_stays_experimental_when_no_chill_condition_matches(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  toggles = make_toggles()

  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 1.0)
  ccm.update(20 * CV.MPH_TO_MS, 21 * CV.MPH_TO_MS, sm, toggles)

  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]


def test_ccm_reuses_detector_toggles(monkeypatch):
  _planner, detector, ccm = make_ccm()
  sm = make_sm()
  toggles = make_toggles()
  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 1.0)

  ccm.update(20 * CV.MPH_TO_MS, 21 * CV.MPH_TO_MS, sm, toggles)
  first_curve_toggles, first_slow_lead_toggles = detector.toggle_objects
  detector.toggle_objects.clear()
  ccm.update(20 * CV.MPH_TO_MS, 21 * CV.MPH_TO_MS, sm, toggles)
  second_curve_toggles, second_slow_lead_toggles = detector.toggle_objects

  assert first_curve_toggles is first_slow_lead_toggles
  assert second_curve_toggles is second_slow_lead_toggles
  assert first_curve_toggles is second_curve_toggles


def test_ccm_enters_chill_for_open_road_speed_recovery(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  toggles = make_toggles()
  monotonic_values = iter([10.0, 10.5])
  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: next(monotonic_values))

  v_ego = 55 * CV.MPH_TO_MS
  v_cruise = v_ego + 5 * CV.MPH_TO_MS
  ccm.update(v_ego, v_cruise, sm, toggles)
  ccm.update(v_ego, v_cruise, sm, toggles)

  assert not ccm.experimental_mode
  assert ccm.status_value == CCStatus["SPEED"]
  assert planner.params_memory.get_int("CCStatus") == CCStatus["SPEED"]


def test_ccm_enters_chill_for_stable_lead_cruising(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  toggles = make_toggles()
  monotonic_values = iter([10.0, 11.1])
  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: next(monotonic_values))

  planner.tracking_lead = True
  planner.lead_one.status = True
  planner.lead_one.dRel = 45.0
  planner.lead_one.vLead = 24.8
  planner.lead_one.radar = True

  v_ego = 58 * CV.MPH_TO_MS
  ccm.update(v_ego, v_ego, sm, toggles)
  ccm.update(v_ego, v_ego, sm, toggles)

  assert not ccm.experimental_mode
  assert ccm.status_value == CCStatus["LEAD"]


def test_ccm_stable_lead_requires_longer_entry_debounce(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  toggles = make_toggles()
  monotonic_values = iter([10.0, 10.6])
  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: next(monotonic_values))

  planner.tracking_lead = True
  planner.lead_one.status = True
  planner.lead_one.dRel = 45.0
  planner.lead_one.vLead = 24.8
  planner.lead_one.radar = True

  v_ego = 58 * CV.MPH_TO_MS
  ccm.update(v_ego, v_ego, sm, toggles)
  ccm.update(v_ego, v_ego, sm, toggles)

  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]


def test_ccm_hard_vetoes_force_experimental(monkeypatch):
  planner, detector, ccm = make_ccm()
  sm = make_sm()
  toggles = make_toggles()
  v_ego = 60 * CV.MPH_TO_MS
  v_cruise = v_ego + 5 * CV.MPH_TO_MS

  veto_scenes = []

  detector.slow_lead_detected = True
  veto_scenes.append(("slow_lead", make_sm()))
  detector.slow_lead_detected = False

  traffic_sm = make_sm()
  traffic_sm["starpilotCarState"].trafficModeEnabled = True
  veto_scenes.append(("traffic_mode", traffic_sm))

  adjacent_sm = make_sm()
  adjacent_sm["starpilotRadarState"].leadLeft = SimpleNamespace(status=True, dRel=25.0, vLead=12.0)
  veto_scenes.append(("adjacent_lead", adjacent_sm))

  for index, (_name, scene_sm) in enumerate(veto_scenes, start=1):
    monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda idx=index: float(idx))
    if _name == "slow_lead":
      detector.slow_lead_detected = True
    else:
      detector.slow_lead_detected = False
    ccm.update(v_ego, v_cruise, scene_sm, toggles)
    assert ccm.experimental_mode
    assert ccm.status_value == CCStatus["OFF"]

  planner.starpilot_vcruise.slc.experimental_mode = True
  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 10.0)
  ccm.update(v_ego, v_cruise, sm, toggles)
  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]


def test_ccm_far_lateral_adjacent_lead_does_not_block_open_road_chill(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  toggles = make_toggles()
  monotonic_values = iter([10.0, 10.5])
  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: next(monotonic_values))

  sm["starpilotRadarState"].leadLeft = SimpleNamespace(status=True, dRel=18.0, vLead=12.0, yRel=6.5)

  v_ego = 55 * CV.MPH_TO_MS
  v_cruise = v_ego + 5 * CV.MPH_TO_MS
  ccm.update(v_ego, v_cruise, sm, toggles)
  ccm.update(v_ego, v_cruise, sm, toggles)

  assert not ccm.experimental_mode
  assert ccm.status_value == CCStatus["SPEED"]


def test_ccm_immediate_adjacent_lead_still_blocks_open_road_chill(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  toggles = make_toggles()

  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 10.0)
  sm["starpilotRadarState"].leadLeft = SimpleNamespace(status=True, dRel=18.0, vLead=12.0, yRel=4.5)

  v_ego = 55 * CV.MPH_TO_MS
  v_cruise = v_ego + 5 * CV.MPH_TO_MS
  ccm.update(v_ego, v_cruise, sm, toggles)

  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]


def test_ccm_immediately_exits_chill_when_scene_turns_into_slow_lead(monkeypatch):
  planner, detector, ccm = make_ccm()
  sm = make_sm()
  toggles = make_toggles()
  monotonic_values = iter([10.0, 11.1, 11.2])
  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: next(monotonic_values))

  planner.tracking_lead = True
  planner.lead_one.status = True
  planner.lead_one.dRel = 40.0
  planner.lead_one.vLead = 24.9
  planner.lead_one.radar = True

  v_ego = 58 * CV.MPH_TO_MS
  ccm.update(v_ego, v_ego, sm, toggles)
  ccm.update(v_ego, v_ego, sm, toggles)
  assert not ccm.experimental_mode

  detector.slow_lead_detected = True
  ccm.update(v_ego, v_ego, sm, toggles)

  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]


def test_ccm_launch_assist_enters_chill_from_standstill_when_planner_wants_to_go(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  sm["carState"].standstill = True
  toggles = make_toggles()
  toggles.conditional_chill_launch_assist = True

  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 20.0)
  ccm.update(0.0, 25 * CV.MPH_TO_MS, sm, toggles)

  assert not ccm.experimental_mode
  assert ccm.status_value == CCStatus["SPEED"]


def test_ccm_launch_assist_does_not_bypass_real_stop_scene(monkeypatch):
  planner, detector, ccm = make_ccm()
  sm = make_sm()
  sm["carState"].standstill = True
  sm["longitudinalPlan"].shouldStop = True
  toggles = make_toggles()
  toggles.conditional_chill_launch_assist = True

  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 21.0)
  ccm.update(0.0, 25 * CV.MPH_TO_MS, sm, toggles)

  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]

  detector.stop_light_detected = True
  sm["longitudinalPlan"].shouldStop = False
  ccm.update(0.0, 25 * CV.MPH_TO_MS, sm, toggles)
  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]


def test_ccm_launch_assist_rejects_red_light_stationary_lead_even_if_planner_says_go(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  sm["carState"].standstill = True
  sm["starpilotPlan"].redLight = True
  toggles = make_toggles()
  toggles.conditional_chill_launch_assist = True

  planner.tracking_lead = True
  planner.lead_one.status = True
  planner.lead_one.dRel = 6.1
  planner.lead_one.vLead = 0.01
  planner.lead_one.vRel = -0.08
  planner.lead_one.aLeadK = 0.0
  planner.lead_one.radar = True

  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 22.0)
  ccm.update(0.0, 25 * CV.MPH_TO_MS, sm, toggles)

  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]


def test_ccm_launch_assist_requires_real_lead_departure_signal(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  sm["carState"].standstill = True
  toggles = make_toggles()
  toggles.conditional_chill_launch_assist = True

  planner.tracking_lead = True
  planner.lead_one.status = True
  planner.lead_one.dRel = 18.0
  planner.lead_one.vLead = 0.12
  planner.lead_one.vRel = 0.05
  planner.lead_one.aLeadK = 0.02
  planner.lead_one.radar = True

  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 23.0)
  ccm.update(0.0, 25 * CV.MPH_TO_MS, sm, toggles)

  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]

  planner.lead_one.vLead = 0.8
  planner.lead_one.vRel = 0.5
  planner.lead_one.aLeadK = 0.2
  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 23.2)
  ccm.update(0.0, 25 * CV.MPH_TO_MS, sm, toggles)

  assert not ccm.experimental_mode
  assert ccm.status_value == CCStatus["LEAD"]


def test_ccm_launch_assist_exits_once_launch_speed_is_reached(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  sm["carState"].standstill = True
  toggles = make_toggles()
  toggles.conditional_chill_launch_assist = True
  monotonic_values = iter([30.0, 30.2])
  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: next(monotonic_values))

  ccm.update(0.0, 25 * CV.MPH_TO_MS, sm, toggles)
  assert not ccm.experimental_mode

  sm["carState"].standstill = False
  ccm.update(16 * CV.MPH_TO_MS, 25 * CV.MPH_TO_MS, sm, toggles)

  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]


def test_ccm_launch_assist_exits_immediately_if_lead_slows_again(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  sm["carState"].standstill = True
  toggles = make_toggles()
  toggles.conditional_chill_launch_assist = True
  monotonic_values = iter([40.0, 40.1])
  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: next(monotonic_values))

  planner.tracking_lead = True
  planner.lead_one.status = True
  planner.lead_one.dRel = 18.0
  planner.lead_one.vLead = 2.0
  planner.lead_one.vRel = 2.0
  planner.lead_one.aLeadK = 0.2
  planner.lead_one.radar = True

  ccm.update(0.0, 25 * CV.MPH_TO_MS, sm, toggles)
  assert not ccm.experimental_mode
  assert ccm.status_value == CCStatus["LEAD"]

  sm["carState"].standstill = False
  planner.lead_one.vLead = 0.2
  planner.lead_one.vRel = 0.0
  planner.lead_one.aLeadK = -0.4
  ccm.update(3 * CV.MPH_TO_MS, 25 * CV.MPH_TO_MS, sm, toggles)

  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]


def test_ccm_respects_manual_chill_override(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  toggles = make_toggles()
  planner.params_memory.put_int("CCStatus", CCStatus["USER_CHILL"])

  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 1.0)
  ccm.update(55 * CV.MPH_TO_MS, 60 * CV.MPH_TO_MS, sm, toggles)

  assert not ccm.experimental_mode
  assert ccm.status_value == CCStatus["USER_CHILL"]


def test_ccm_launch_assist_is_disabled_by_default(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  sm["carState"].standstill = True
  toggles = make_toggles()

  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 50.0)
  ccm.update(0.0, 25 * CV.MPH_TO_MS, sm, toggles)

  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]


def test_ccm_restores_persisted_manual_experimental_override(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_sm()
  toggles = make_toggles()
  planner.params.put_bool("PersistChillState", True)
  planner.params.put_int("PersistedCCStatus", CCStatus["USER_EXPERIMENTAL"])

  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 1.0)
  ccm.update(55 * CV.MPH_TO_MS, 60 * CV.MPH_TO_MS, sm, toggles)

  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["USER_EXPERIMENTAL"]
  assert planner.params_memory.get_int("CCStatus") == CCStatus["USER_EXPERIMENTAL"]


def test_ccm_adjacent_lead_veto_works_with_submaster_like_input(monkeypatch):
  planner, _detector, ccm = make_ccm()
  sm = make_submaster_sm()
  toggles = make_toggles()
  sm["starpilotRadarState"].leadLeft = SimpleNamespace(status=True, dRel=20.0, vLead=12.0)

  monkeypatch.setattr("openpilot.starpilot.controls.lib.conditional_chill_mode.time.monotonic", lambda: 10.0)
  ccm.update(60 * CV.MPH_TO_MS, 65 * CV.MPH_TO_MS, sm, toggles)

  assert ccm.experimental_mode
  assert ccm.status_value == CCStatus["OFF"]
