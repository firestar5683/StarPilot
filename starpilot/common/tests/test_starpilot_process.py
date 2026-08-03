import json
from types import SimpleNamespace

from openpilot.starpilot import starpilot_process


class FakeParams:
  def __init__(self):
    self.writes = []

  def put(self, key, value):
    self.writes.append((key, value))


class FakeThreadManager:
  def run_with_lock(self, *args, **kwargs):
    return None


class FakeThemeManager:
  def update_active_theme(self, *args, **kwargs):
    return None


class FakeModelManager:
  def randomize_selected_model(self):
    return None


def test_background_toggle_update_does_not_mutate_active_toggles():
  active_toggles = SimpleNamespace(holiday_themes=False, random_themes=False, enabled=False)

  class FakeVariables:
    def __init__(self):
      self.starpilot_toggles = active_toggles
      self.clear_update_flag = None

    def update(self, holiday_theme, started, clear_update_flag=True):
      self.clear_update_flag = clear_update_flag
      self.starpilot_toggles.enabled = True

  theme_manager = FakeThemeManager()
  theme_manager.holiday_theme = "stock"
  theme_manager.theme_updated = False
  result = {}

  starpilot_process.update_toggles_in_background(
    result,
    FakeVariables(),
    True,
    theme_manager,
    FakeThreadManager(),
    False,
    FakeParams(),
    active_toggles,
  )

  updated_variables, updated_toggles = result["update"]
  assert active_toggles.enabled is False
  assert updated_toggles.enabled is True
  assert updated_variables.clear_update_flag is False


def test_transition_offroad_skips_invalid_gps_persist():
  params = FakeParams()
  planner = SimpleNamespace(gps_position={
    "latitude": 0.0,
    "longitude": 0.0,
    "bearing": 0.0,
    "speed": 0.0,
    "hasFix": False,
    "updatedAtMonotonic": 1.0,
    "updatedAtSec": 1.0,
  })
  toggles = SimpleNamespace(lock_doors_timer=0, random_themes=False)

  starpilot_process.transition_offroad(
    planner,
    FakeModelManager(),
    FakeThemeManager(),
    FakeThreadManager(),
    False,
    None,
    params,
    toggles,
  )

  assert params.writes == []


def test_transition_offroad_skips_missing_gps_persist():
  params = FakeParams()
  planner = SimpleNamespace(gps_position=None)
  toggles = SimpleNamespace(lock_doors_timer=0, random_themes=False)

  starpilot_process.transition_offroad(
    planner,
    FakeModelManager(),
    FakeThemeManager(),
    FakeThreadManager(),
    False,
    None,
    params,
    toggles,
  )

  assert params.writes == []


def test_transition_offroad_skips_malformed_gps_persist():
  params = FakeParams()
  planner = SimpleNamespace(gps_position={"hasFix": True})
  toggles = SimpleNamespace(lock_doors_timer=0, random_themes=False)

  starpilot_process.transition_offroad(
    planner,
    FakeModelManager(),
    FakeThemeManager(),
    FakeThreadManager(),
    False,
    None,
    params,
    toggles,
  )

  assert params.writes == []


def test_transition_offroad_persists_valid_gps():
  params = FakeParams()
  gps_position = {
    "latitude": 41.0,
    "longitude": -87.0,
    "bearing": 90.0,
    "speed": 12.0,
    "hasFix": True,
    "updatedAtMonotonic": 1.0,
    "updatedAtSec": 2.0,
  }
  planner = SimpleNamespace(gps_position=gps_position)
  toggles = SimpleNamespace(lock_doors_timer=0, random_themes=False)

  starpilot_process.transition_offroad(
    planner,
    FakeModelManager(),
    FakeThemeManager(),
    FakeThreadManager(),
    False,
    None,
    params,
    toggles,
  )

  assert params.writes == [("LastGPSPosition", json.dumps(gps_position))]


def test_transition_onroad_stops_dashboard_analysis(monkeypatch, tmp_path):
  calls = []
  dashboard_utilities = SimpleNamespace(stop_dashboard_background_analysis=lambda: calls.append("stop"))
  monkeypatch.setattr(starpilot_process, "get_dashboard_utilities", lambda: dashboard_utilities)
  error_log = tmp_path / "error.txt"
  error_log.write_text("old error")

  starpilot_process.transition_onroad(error_log)

  assert calls == ["stop"]
  assert not error_log.exists()
