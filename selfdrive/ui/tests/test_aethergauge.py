import sys
import types
import unittest
from unittest.mock import MagicMock

from collections import namedtuple

ColorClass = namedtuple("Color", ["r", "g", "b", "a"])

# 1. Register Mock/Stub for pyray
rl = types.SimpleNamespace(
  Color=lambda r, g, b, a=255: ColorClass(r, g, b, a),
  Rectangle=lambda x=0, y=0, width=0, height=0: types.SimpleNamespace(x=x, y=y, width=width, height=height),
  Vector2=lambda x=0, y=0: types.SimpleNamespace(x=x, y=y),
  Texture2D=type("Texture2D", (), {}),
  Font=type("Font", (), {}),
  WHITE=ColorClass(255, 255, 255, 255),
  BLACK=ColorClass(0, 0, 0, 255),
  get_time=lambda: 1.0,
)
sys.modules["pyray"] = rl

# 2. Register Mock/Stub for text_measure
text_measure = types.SimpleNamespace(
  measure_text_cached=lambda *a, **k: types.SimpleNamespace(x=100, y=20)
)
sys.modules["openpilot.system.ui.lib.text_measure"] = text_measure

# 3. Register Mock/Stub for starpilot_border
starpilot_border = types.SimpleNamespace(
  _csc_state=lambda: None,
  _intensity=lambda c: 0.0,
  _glow_color=lambda i: rl.Color(0, 255, 0, 255),
)
sys.modules["openpilot.selfdrive.ui.onroad.starpilot.starpilot_border"] = starpilot_border

class MockSubMaster:
  def __init__(self):
    self.valid = {}
    self.updated = {}
    self.data = {}

  def __getitem__(self, key):
    return self.data.get(key)

  def __setitem__(self, key, value):
    self.data[key] = value

  def reset(self):
    self.valid.clear()
    self.updated.clear()
    self.data.clear()

mock_ui_state = types.SimpleNamespace(
  is_metric=False,
  sm=MockSubMaster(),
)
ui_state_mod = types.ModuleType("openpilot.selfdrive.ui.ui_state")
ui_state_mod.ui_state = mock_ui_state
sys.modules["openpilot.selfdrive.ui.ui_state"] = ui_state_mod

# Now import aethergauge
from openpilot.selfdrive.ui.onroad.starpilot.aethergauge import (
  AetherGauge,
  AetherGaugeData,
  IndicatorType,
  _is_lead,
  _lead_data,
  _is_stop_light,
  _is_curvature,
)

class TestAetherGaugeLeadLogic(unittest.TestCase):
  def setUp(self):
    mock_ui_state.sm.reset()

  def test_is_lead_inactive_if_not_experimental(self):
    mock_ui_state.sm.valid["starpilotPlan"] = True
    mock_ui_state.sm.valid["radarState"] = True
    mock_ui_state.sm["starpilotPlan"] = types.SimpleNamespace(
      experimentalMode=False,
      trackingLead=True,
    )
    mock_ui_state.sm["radarState"] = types.SimpleNamespace(
      leadOne=types.SimpleNamespace(status=True, vLead=5.0, dRel=20.0)
    )
    self.assertFalse(_is_lead())

  def test_is_lead_inactive_if_not_tracking_lead(self):
    mock_ui_state.sm.valid["starpilotPlan"] = True
    mock_ui_state.sm.valid["radarState"] = True
    mock_ui_state.sm["starpilotPlan"] = types.SimpleNamespace(
      experimentalMode=True,
      trackingLead=False,
    )
    mock_ui_state.sm["radarState"] = types.SimpleNamespace(
      leadOne=types.SimpleNamespace(status=True, vLead=5.0, dRel=20.0)
    )
    self.assertFalse(_is_lead())

  def test_is_lead_active_when_experimental_and_tracking(self):
    mock_ui_state.sm.valid["starpilotPlan"] = True
    mock_ui_state.sm.valid["radarState"] = True
    mock_ui_state.sm["starpilotPlan"] = types.SimpleNamespace(
      experimentalMode=True,
      trackingLead=True,
    )
    mock_ui_state.sm["radarState"] = types.SimpleNamespace(
      leadOne=types.SimpleNamespace(status=True, vLead=5.0, dRel=20.0)
    )
    self.assertTrue(_is_lead())

  def test_lead_data_slow(self):
    mock_ui_state.sm.valid["radarState"] = True
    mock_ui_state.sm["radarState"] = types.SimpleNamespace(
      leadOne=types.SimpleNamespace(status=True, vLead=5.0, dRel=25.0)
    )
    data = _lead_data()
    self.assertEqual(data.text, "SLOW")
    self.assertEqual(data.indicator_extra, "slower")
    self.assertEqual(data.indicator_value, 25.0)
    self.assertEqual(data.indicator_type, IndicatorType.LEAD)

  def test_lead_data_stopped(self):
    mock_ui_state.sm.valid["radarState"] = True
    mock_ui_state.sm["radarState"] = types.SimpleNamespace(
      leadOne=types.SimpleNamespace(status=True, vLead=0.5, dRel=12.0)
    )
    data = _lead_data()
    self.assertEqual(data.text, "STOPPED")
    self.assertEqual(data.indicator_extra, "stopped")
    self.assertEqual(data.indicator_value, 12.0)
    self.assertEqual(data.indicator_type, IndicatorType.LEAD)

  def test_is_stop_light(self):
    mock_ui_state.sm.valid["starpilotPlan"] = True
    mock_ui_state.sm["starpilotPlan"] = types.SimpleNamespace(
      experimentalMode=True,
      redLight=True,
    )
    self.assertTrue(_is_stop_light())

    mock_ui_state.sm["starpilotPlan"].redLight = False
    self.assertFalse(_is_stop_light())

  def test_is_curvature(self):
    mock_ui_state.sm.valid["starpilotPlan"] = True
    mock_ui_state.sm["starpilotPlan"] = types.SimpleNamespace(
      experimentalMode=True,
      roadCurvature=0.002,
    )
    self.assertTrue(_is_curvature())

    mock_ui_state.sm["starpilotPlan"].roadCurvature = 0.0005
    self.assertFalse(_is_curvature())



if __name__ == "__main__":
  unittest.main()
