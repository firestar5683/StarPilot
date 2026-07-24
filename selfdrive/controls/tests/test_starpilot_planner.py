import math
from pathlib import Path
from types import SimpleNamespace

from openpilot.common.realtime import DT_MDL
from openpilot.starpilot.controls.starpilot_planner import StarPilotPlanner
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
    "minimum_lane_change_speed": 100.0,
    "pause_lateral_below_speed": 10.0,
    "pause_lateral_below_signal": True,
    "pause_lateral_signal_delay": 0.0,
    "set_speed_offset": 0,
    "weather_presets": False,
  }
  defaults.update(overrides)
  return SimpleNamespace(**defaults)


def make_sm(planner, *, frame: int, v_ego: float, left_blinker: bool, right_blinker: bool = False):
  return FakeSM(frame, {
    "radarState": SimpleNamespace(
      leadOne=SimpleNamespace(status=False, dRel=float("inf"), vLead=0.0, modelProb=0.0, radar=False),
    ),
    "selfdriveState": SimpleNamespace(enabled=True),
    "carState": SimpleNamespace(
      vCruise=50.0,
      vEgo=v_ego,
      standstill=False,
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
  monkeypatch.setattr(planner.longitudinal_intent, "update", lambda *args, **kwargs: None)
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
