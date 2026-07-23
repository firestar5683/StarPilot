import importlib
import sys
import types
import unittest

from openpilot.selfdrive.ui.tests.test_aethergrid import (
  _clear_modules,
  _install_aethergrid_stubs,
  _install_panel_stubs,
)

AETHERGRID_MODULE = "openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid"
PANEL_MODULE = "openpilot.selfdrive.ui.layouts.settings.starpilot.panel"
LATERAL_MODULE = "openpilot.selfdrive.ui.layouts.settings.starpilot.lateral"


class FakeParams:
  def __init__(self, memory=False):
    self.store = {}

  def get(self, key, **kwargs):
    v = self.store.get(key)
    return None if v is None else str(v).encode()

  def get_bool(self, key, **kwargs):
    return bool(self.store.get(key, False))

  def get_int(self, key, **kwargs):
    return int(self.store.get(key, 0))

  def get_float(self, key, **kwargs):
    return float(self.store.get(key, 0.0))

  def put(self, key, val, **kwargs):
    self.store[key] = val

  def put_bool(self, key, val, **kwargs):
    self.store[key] = bool(val)

  def put_int(self, key, val, **kwargs):
    self.store[key] = int(val)

  def put_float(self, key, val, **kwargs):
    self.store[key] = float(val)

  def remove(self, key):
    self.store.pop(key, None)


def _install_lateral_stubs():
  _install_aethergrid_stubs()

  sys.modules["openpilot.system.ui.lib.multilang"].tr_noop = lambda text: text
  sys.modules["openpilot.system.ui.lib.application"].gui_app.push_widget = lambda widget: None

  hardware_mod = types.ModuleType("openpilot.system.hardware")
  hardware_mod.HARDWARE = types.SimpleNamespace(reboot=lambda: None)
  sys.modules["openpilot.system.hardware"] = hardware_mod

  state_mod = types.ModuleType("openpilot.selfdrive.ui.lib.starpilot_state")
  state_mod.starpilot_state = types.SimpleNamespace(
    car_state=types.SimpleNamespace(
      hasNNFFLog=False,
      isAngleCar=False,
      isTorqueCar=True,
      hasAutoTune=False,
      steerActuatorDelay=0.0,
      friction=0.0,
      steerKp=0.0,
      latAccelFactor=0.0,
      steerRatio=0.0,
    )
  )
  sys.modules["openpilot.selfdrive.ui.lib.starpilot_state"] = state_mod

  variables_mod = types.ModuleType("openpilot.starpilot.common.starpilot_variables")
  variables_mod.update_starpilot_toggles = lambda: None
  sys.modules["openpilot.starpilot.common.starpilot_variables"] = variables_mod


def _import_lateral():
  _install_lateral_stubs()
  _clear_modules(AETHERGRID_MODULE)
  aethergrid = importlib.import_module(AETHERGRID_MODULE)
  _install_panel_stubs(aethergrid)

  params_mod = types.ModuleType("openpilot.common.params")
  params_mod.Params = FakeParams
  params_mod.UnknownKeyName = Exception
  sys.modules["openpilot.common.params"] = params_mod

  _clear_modules(PANEL_MODULE, LATERAL_MODULE)
  importlib.import_module(PANEL_MODULE)
  return importlib.import_module(LATERAL_MODULE)


class TestLateralLaneCenteringRows(unittest.TestCase):
  def setUp(self):
    lateral = _import_lateral()
    self.layout = lateral.StarPilotLateralLayout()
    self.params = self.layout._params
    self.rows = {row.id: row for row in self.layout._advanced_rows}

  def test_rows_exist_with_expected_types(self):
    self.assertIn("LaneCentering", self.rows)
    self.assertIn("LaneCenterOffset", self.rows)
    self.assertIn("CameraOffset", self.rows)
    self.assertEqual(self.rows["LaneCentering"].type, "toggle")
    self.assertEqual(self.rows["LaneCenterOffset"].type, "value")
    self.assertEqual(self.rows["CameraOffset"].type, "value")

  def test_visibility_requires_advanced_parent(self):
    self.params.put_bool("AdvancedLateralTune", False)
    self.params.put_bool("LaneCentering", True)
    self.assertFalse(self.rows["LaneCentering"].visible())
    self.assertFalse(self.rows["LaneCenterOffset"].visible())

  def test_offset_visible_only_while_lane_centering_enabled(self):
    self.params.put_bool("AdvancedLateralTune", True)
    self.params.put_bool("LaneCentering", False)
    self.assertTrue(self.rows["LaneCentering"].visible())
    self.assertFalse(self.rows["LaneCenterOffset"].visible())

    self.params.put_bool("LaneCentering", True)
    self.assertTrue(self.rows["LaneCenterOffset"].visible())

  def test_toggle_params_callback(self):
    self.assertFalse(self.rows["LaneCentering"].get_state())
    self.rows["LaneCentering"].set_state(True)
    self.assertTrue(self.params.get_bool("LaneCentering"))
    self.assertTrue(self.rows["LaneCentering"].get_state())
    self.rows["LaneCentering"].set_state(False)
    self.assertFalse(self.params.get_bool("LaneCentering"))

  def test_offset_display_shows_meters(self):
    self.params.put_float("LaneCenterOffset", 0.25)
    self.assertEqual(self.rows["LaneCenterOffset"].get_value(), "0.25 m")
    self.params.put_float("LaneCenterOffset", -0.1)
    self.assertEqual(self.rows["LaneCenterOffset"].get_value(), "-0.10 m")

  def test_offset_slider_range_step_and_unit(self):
    calls = []
    self.layout._show_slider = lambda *args, **kwargs: calls.append((args, kwargs))
    self.rows["LaneCenterOffset"].on_click()
    self.assertEqual(len(calls), 1)
    args, kwargs = calls[0]
    self.assertEqual(args, ("LaneCenterOffset", -0.5, 0.5))
    self.assertEqual(kwargs["step"], 0.01)
    self.assertEqual(kwargs["unit"], " m")
    self.assertEqual(kwargs["value_type"], "float")

  def test_camera_offset_display_and_slider_contract(self):
    self.params.put_float("CameraOffset", -0.12)
    self.assertEqual(self.rows["CameraOffset"].get_value(), "-0.12 m")

    calls = []
    self.layout._show_slider = lambda *args, **kwargs: calls.append((args, kwargs))
    self.rows["CameraOffset"].on_click()
    self.assertEqual(len(calls), 1)
    args, kwargs = calls[0]
    self.assertEqual(args, ("CameraOffset", -0.35, 0.35))
    self.assertEqual(kwargs["step"], 0.01)
    self.assertEqual(kwargs["unit"], " m")
    self.assertEqual(kwargs["value_type"], "float")

  def test_slider_confirm_writes_float_param(self):
    panel = importlib.import_module(PANEL_MODULE)
    captured = {}

    class FakeDialog:
      def __init__(self, title, min_v, max_v, step, current, callback, **kwargs):
        captured["range"] = (min_v, max_v)
        captured["step"] = step
        captured["unit"] = kwargs.get("unit")
        captured["callback"] = callback

    original = panel.AetherSliderDialog
    panel.AetherSliderDialog = FakeDialog
    try:
      self.layout._show_slider("LaneCenterOffset", -0.5, 0.5, step=0.01, unit=" m", value_type="float")
    finally:
      panel.AetherSliderDialog = original

    self.assertEqual(captured["range"], (-0.5, 0.5))
    self.assertEqual(captured["step"], 0.01)
    self.assertEqual(captured["unit"], " m")

    confirm = sys.modules["openpilot.system.ui.widgets"].DialogResult.CONFIRM
    captured["callback"](confirm, 0.3)
    self.assertAlmostEqual(self.params.get_float("LaneCenterOffset"), 0.3)


if __name__ == "__main__":
  unittest.main()
