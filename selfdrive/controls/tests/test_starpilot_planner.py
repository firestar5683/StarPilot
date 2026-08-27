import math
from pathlib import Path
from types import SimpleNamespace

from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL
from openpilot.starpilot.controls.starpilot_planner import StarPilotPlanner, get_force_stop_jerk_scale
from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import get_lead_follow_jerk_scale
import openpilot.starpilot.controls.starpilot_planner as starpilot_planner_module


class DummyThemeManager:
  def update_wheel_image(self, *args, **kwargs):
    pass


class FakeSM(dict):
  def __init__(self, frame: int, services: dict):
    super().__init__(services)
    self.frame = frame


def make_toggles(**overrides):
  defaults = {
    "compass": False,
    "conditional_experimental_mode": False,
    "minimum_lane_change_speed": 100.0,
    "pause_lateral_below_speed": 10.0,
    "pause_lateral_below_signal": True,
    "pause_lateral_signal_delay": 0.0,
    "set_speed_offset": 0,
    "weather_presets": False,
  }
  defaults.update(overrides)
  return SimpleNamespace(**defaults)


def test_force_stop_jerk_scale_is_platform_specific():
  assert get_force_stop_jerk_scale(SimpleNamespace(carFingerprint="HYUNDAI_ELANTRA_2021")) == 0.80
  assert get_force_stop_jerk_scale(SimpleNamespace(carFingerprint="OTHER_CAR")) == 0.32


def test_lead_follow_jerk_scale_is_platform_specific():
  assert get_lead_follow_jerk_scale(SimpleNamespace(brand="hyundai", carFingerprint="HYUNDAI_ELANTRA_2021")) == 1.25
  assert get_lead_follow_jerk_scale(SimpleNamespace(brand="other", carFingerprint="OTHER_CAR")) == 1.0


def make_sm(planner, *, frame: int, v_ego: float, left_blinker: bool, right_blinker: bool = False, standstill: bool = False):
  return FakeSM(frame, {
    "radarState": SimpleNamespace(
      leadOne=SimpleNamespace(status=False, dRel=float("inf"), vLead=0.0, modelProb=0.0, radar=False),
    ),
    "selfdriveState": SimpleNamespace(enabled=True),
    "carState": SimpleNamespace(
      vCruise=50.0,
      vEgo=v_ego,
      standstill=standstill,
      leftBlinker=left_blinker,
      rightBlinker=right_blinker,
    ),
    "controlsState": SimpleNamespace(curvature=0.0),
    "modelV2": SimpleNamespace(position=SimpleNamespace(x=[0.0, 30.0]), laneLines=[None] * 4, roadEdges=[None] * 2),
    "starpilotCarState": SimpleNamespace(pauseLateral=False, alwaysOnLateralEnabled=False),
    planner.gps_location_service: SimpleNamespace(latitude=1.0, longitude=1.0, bearingDeg=90.0),
  })


def make_planner(monkeypatch):
  planner = StarPilotPlanner(Path("/tmp/nonexistent"), DummyThemeManager())
  monkeypatch.setattr(starpilot_planner_module, "calculate_road_curvature", lambda model, v_ego: (0.01, 0.0))
  monkeypatch.setattr(planner.starpilot_acceleration, "update", lambda *args, **kwargs: None)
  monkeypatch.setattr(planner.starpilot_events, "update", lambda *args, **kwargs: None)
  monkeypatch.setattr(planner.starpilot_following, "update", lambda *args, **kwargs: None)
  monkeypatch.setattr(planner.starpilot_vcruise, "update", lambda *args, **kwargs: 0.0)
  monkeypatch.setattr(planner.starpilot_weather, "update_weather", lambda *args, **kwargs: None)
  monkeypatch.setattr(planner.starpilot_cem, "stop_sign_and_light", lambda *args, **kwargs: None)
  monkeypatch.setattr(planner, "update_lead_status", lambda *args, **kwargs: False)
  return planner


def test_lateral_resume_delay_zero_keeps_immediate_resume(monkeypatch):
  planner = make_planner(monkeypatch)

  try:
    toggles = make_toggles(pause_lateral_signal_delay=0.0)

    planner.update(0.0, False, make_sm(planner, frame=1, v_ego=4.0, left_blinker=True), toggles)
    assert planner.lateral_check is False

    planner.update(0.0, False, make_sm(planner, frame=2, v_ego=4.0, left_blinker=False), toggles)
    assert planner.lateral_check is True
    assert planner.blinker_delay_active is False
  finally:
    planner.shutdown()


def test_turn_signal_keeps_lateral_paused_at_standstill(monkeypatch):
  planner = make_planner(monkeypatch)

  try:
    toggles = make_toggles(pause_lateral_below_speed=99.0)

    planner.update(0.0, False, make_sm(planner, frame=1, v_ego=0.0, left_blinker=True, standstill=True), toggles)

    assert planner.lateral_check is False
  finally:
    planner.shutdown()


def test_standstill_without_turn_signal_keeps_lateral_allowed(monkeypatch):
  planner = make_planner(monkeypatch)

  try:
    toggles = make_toggles(pause_lateral_below_speed=99.0)

    planner.update(0.0, False, make_sm(planner, frame=1, v_ego=0.0, left_blinker=False, standstill=True), toggles)

    assert planner.lateral_check is True
  finally:
    planner.shutdown()


def test_manual_lateral_pause_blocks_lateral_while_cruise_is_enabled(monkeypatch):
  planner = make_planner(monkeypatch)

  try:
    sm = make_sm(planner, frame=1, v_ego=20.0, left_blinker=False)
    sm["starpilotCarState"].pauseLateral = True

    planner.update(0.0, False, sm, make_toggles())

    assert planner.lateral_check is False
  finally:
    planner.shutdown()


def test_pulse_glide_target_is_published_after_vcruise_update(monkeypatch):
  planner = make_planner(monkeypatch)

  try:
    normal_target = 65.0 * CV.MPH_TO_MS
    glide_target = 60.0 * CV.MPH_TO_MS
    monkeypatch.setattr(planner.starpilot_vcruise, "update", lambda *args, **kwargs: normal_target)

    def publish_glide_target(*args, **kwargs):
      planner.starpilot_acceleration.pulse_glide_target = glide_target

    monkeypatch.setattr(planner.starpilot_acceleration, "update", publish_glide_target)
    planner.update(0.0, False, make_sm(planner, frame=1, v_ego=normal_target, left_blinker=False), make_toggles())

    assert planner.v_cruise == glide_target
  finally:
    planner.shutdown()


def test_lateral_resume_delay_holds_resume_after_low_speed_turn(monkeypatch):
  planner = make_planner(monkeypatch)

  try:
    toggles = make_toggles(pause_lateral_signal_delay=0.5)

    planner.update(0.0, False, make_sm(planner, frame=1, v_ego=4.0, left_blinker=True), toggles)
    planner.update(0.0, False, make_sm(planner, frame=2, v_ego=4.0, left_blinker=False), toggles)

    assert planner.lateral_check is False
    assert planner.blinker_delay_active is True

    resume_frame = 2 + math.ceil(toggles.pause_lateral_signal_delay / DT_MDL)
    planner.update(0.0, False, make_sm(planner, frame=resume_frame, v_ego=4.0, left_blinker=False), toggles)

    assert planner.lateral_check is True
    assert planner.blinker_delay_active is False
  finally:
    planner.shutdown()


def test_lateral_resume_delay_ignores_signal_cycles_that_never_slow_enough(monkeypatch):
  planner = make_planner(monkeypatch)

  try:
    toggles = make_toggles(pause_lateral_signal_delay=0.5)

    planner.update(0.0, False, make_sm(planner, frame=1, v_ego=8.0, left_blinker=True), toggles)
    planner.update(0.0, False, make_sm(planner, frame=2, v_ego=8.0, left_blinker=False), toggles)

    assert planner.lateral_check is True
    assert planner.blinker_delay_active is False
  finally:
    planner.shutdown()


def test_hybrid_mode_keeps_cem_detector_warm_with_modes_off(monkeypatch):
  planner = make_planner(monkeypatch)
  monkeypatch.setattr(planner.starpilot_cem, "update", lambda *args, **kwargs: None)

  try:
    toggles = make_toggles(hybrid_experimental_mode=True)

    planner.update(0.0, False, make_sm(planner, frame=1, v_ego=20.0, left_blinker=False), toggles)

    assert planner.starpilot_ccm.experimental_mode is False
    assert planner.starpilot_cem.experimental_mode is False
  finally:
    planner.shutdown()


def test_radarless_follow_hold_applies_to_tracked_vision_lead(monkeypatch):
  planner = StarPilotPlanner(Path("/tmp/nonexistent"), DummyThemeManager())

  try:
    monkeypatch.setattr(starpilot_planner_module.time, "monotonic", lambda: 100.0)
    planner.model_length = 30.0
    planner.tracking_lead = True
    planner.starpilot_following.t_follow = 1.45
    planner.lead_one = SimpleNamespace(
      status=True,
      dRel=46.0,
      vLead=27.0,
      aLeadK=0.0,
      modelProb=0.98,
      radar=False,
    )

    planner.update_lead_status(27.5)
    assert planner.radarless_follow_hold_until > 100.0
  finally:
    planner.shutdown()


def test_tracked_vision_lead_uses_exit_hysteresis_at_mid_speed():
  planner = StarPilotPlanner(Path("/tmp/nonexistent"), DummyThemeManager())

  try:
    planner.model_length = 174.0
    planner.tracking_lead = True
    planner.tracking_lead_filter.x = 1.0
    planner.lead_one = SimpleNamespace(
      status=True,
      dRel=44.5,
      vLead=16.7,
      yRel=-0.69,
      aLeadK=0.0,
      modelProb=0.99,
      radar=False,
    )

    assert planner.update_lead_status(16.8)
  finally:
    planner.shutdown()


def test_untracked_vision_lead_still_uses_strict_entry_gate():
  planner = StarPilotPlanner(Path("/tmp/nonexistent"), DummyThemeManager())

  try:
    planner.model_length = 174.0
    planner.lead_one = SimpleNamespace(
      status=True,
      dRel=44.5,
      vLead=16.7,
      yRel=-0.69,
      aLeadK=0.0,
      modelProb=0.99,
      radar=False,
    )

    assert not planner.update_lead_status(16.8)
  finally:
    planner.shutdown()
