import types
import unittest

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
from openpilot.selfdrive.ui.onroad.starpilot import aethergauge
from openpilot.selfdrive.ui.onroad.starpilot.aethergauge import (
  AetherGauge,
  AetherGaugeData,
  IndicatorType,
  _is_lead,
  _lead_data,
  _is_stop_light,
  _is_curvature,
)
aethergauge.ui_state = mock_ui_state

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
