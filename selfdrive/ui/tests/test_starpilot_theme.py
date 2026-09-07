import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

MODULE_PATH = Path(__file__).resolve().parents[1] / "lib" / "starpilot_theme.py"
SPEC = importlib.util.spec_from_file_location("starpilot_theme_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None


class FakeGuiApp:
  def __init__(self):
    self._frame = 0

  @property
  def frame(self):
    return self._frame


application_module_name = "openpilot.system.ui.lib.application"
application_module = sys.modules.get(application_module_name)
installed_fake_application = application_module is None
if application_module is None:
  application_module = ModuleType(application_module_name)
  application_module.gui_app = FakeGuiApp()
  sys.modules[application_module_name] = application_module

starpilot_theme = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(starpilot_theme)
if installed_fake_application:
  sys.modules.pop(application_module_name, None)


def _reset_theme_cache():
  starpilot_theme._THEME_COLOR_CACHE.update(frame=None, stamp=None, colors=None)


def _track_file_stamps(monkeypatch):
  file_stamps = []
  original_file_stamp = starpilot_theme._file_stamp

  def file_stamp(path):
    file_stamps.append(path)
    return original_file_stamp(path)

  monkeypatch.setattr(starpilot_theme, "_file_stamp", file_stamp)
  return file_stamps


def _color_tuple(color):
  return color.r, color.g, color.b, color.a


def test_theme_files_are_checked_once_per_render_frame(tmp_path, monkeypatch):
  stock_path = tmp_path / "stock.json"
  active_path = tmp_path / "active.json"
  stock_path.write_text(json.dumps({"LaneLines": {"red": 1, "green": 2, "blue": 3}}))
  active_path.write_text(json.dumps({}))
  monkeypatch.setattr(starpilot_theme, "STOCK_THEME_COLORS_PATH", stock_path)
  monkeypatch.setattr(starpilot_theme, "ACTIVE_THEME_COLORS_PATH", active_path)
  monkeypatch.setattr(starpilot_theme.gui_app, "_frame", 10)
  file_stamps = _track_file_stamps(monkeypatch)
  _reset_theme_cache()

  assert _color_tuple(starpilot_theme.get_theme_color("LaneLines")) == (1, 2, 3, 178)
  assert _color_tuple(starpilot_theme.get_theme_color("Path")) == (48, 255, 156, 255)
  assert len(file_stamps) == 2

  monkeypatch.setattr(starpilot_theme.gui_app, "_frame", 11)
  starpilot_theme.get_theme_color("LeadMarker")
  assert len(file_stamps) == 4


def test_theme_file_changes_are_seen_on_the_next_frame(tmp_path, monkeypatch):
  stock_path = tmp_path / "stock.json"
  active_path = tmp_path / "active.json"
  stock_path.write_text(json.dumps({}))
  active_path.write_text(json.dumps({"Path": {"red": 1, "green": 2, "blue": 3, "alpha": 4}}))
  monkeypatch.setattr(starpilot_theme, "STOCK_THEME_COLORS_PATH", stock_path)
  monkeypatch.setattr(starpilot_theme, "ACTIVE_THEME_COLORS_PATH", active_path)
  monkeypatch.setattr(starpilot_theme.gui_app, "_frame", 20)
  _reset_theme_cache()

  assert _color_tuple(starpilot_theme.get_theme_color("Path")) == (1, 2, 3, 4)
  active_path.write_text(json.dumps({"Path": {"red": 5, "green": 6, "blue": 7, "alpha": 8}}))
  assert _color_tuple(starpilot_theme.get_theme_color("Path")) == (1, 2, 3, 4)

  monkeypatch.setattr(starpilot_theme.gui_app, "_frame", 21)
  assert _color_tuple(starpilot_theme.get_theme_color("Path")) == (5, 6, 7, 8)


def test_frame_counter_reset_checks_theme_files_again(tmp_path, monkeypatch):
  stock_path = tmp_path / "stock.json"
  active_path = tmp_path / "active.json"
  stock_path.write_text(json.dumps({}))
  active_path.write_text(json.dumps({}))
  monkeypatch.setattr(starpilot_theme, "STOCK_THEME_COLORS_PATH", stock_path)
  monkeypatch.setattr(starpilot_theme, "ACTIVE_THEME_COLORS_PATH", active_path)
  monkeypatch.setattr(starpilot_theme.gui_app, "_frame", 30)
  file_stamps = _track_file_stamps(monkeypatch)
  _reset_theme_cache()

  starpilot_theme.get_theme_color("Path")
  monkeypatch.setattr(starpilot_theme.gui_app, "_frame", 0)
  starpilot_theme.get_theme_color("Path")

  assert len(file_stamps) == 4
