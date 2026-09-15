import types

import pytest


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
  conditional_status=0,
  starpilot_toggles={
    "conditional_experimental_mode": True,
    "conditional_curves": True,
  },
)
from openpilot.selfdrive.ui.onroad.starpilot import aethergauge
from openpilot.selfdrive.ui.onroad.starpilot.aethergauge import (
  AetherGauge,
  AetherGaugeData,
  IndicatorType,
  _cem_curvature_data,
  _is_cem_curvature,
  _is_curve_speed,
  _is_lead,
  _is_stop_light,
  _lead_data,
  _to_display_distance,
  _to_display_speed,
)
from openpilot.starpilot.common.experimental_state import CEStatus

aethergauge.ui_state = mock_ui_state


@pytest.fixture(autouse=True)
def reset_ui_state():
  mock_ui_state.sm.reset()
  mock_ui_state.is_metric = False
  mock_ui_state.conditional_status = CEStatus["OFF"]
  mock_ui_state.starpilot_toggles.update({
    "conditional_experimental_mode": True,
    "conditional_curves": True,
  })
  mock_ui_state.sm.valid["selfdriveState"] = True
  mock_ui_state.sm["selfdriveState"] = types.SimpleNamespace(enabled=True)


def _set_plan(**overrides):
  plan = types.SimpleNamespace(
    experimentalMode=True,
    roadCurvature=0.002,
    cscSpeed=0.0,
    vCruise=20.0,
    redLight=False,
    forcingStop=False,
    trackingLead=False,
  )
  for key, value in overrides.items():
    setattr(plan, key, value)
  mock_ui_state.sm.valid["starpilotPlan"] = True
  mock_ui_state.sm["starpilotPlan"] = plan
  return plan


def test_is_lead_inactive_if_not_experimental():
  _set_plan(experimentalMode=False, trackingLead=True)
  mock_ui_state.sm.valid["radarState"] = True
  mock_ui_state.sm["radarState"] = types.SimpleNamespace(
    leadOne=types.SimpleNamespace(status=True, vLead=5.0, dRel=20.0)
  )
  assert not _is_lead()


def test_is_lead_inactive_if_not_tracking_lead():
  _set_plan(trackingLead=False)
  mock_ui_state.sm.valid["radarState"] = True
  mock_ui_state.sm["radarState"] = types.SimpleNamespace(
    leadOne=types.SimpleNamespace(status=True, vLead=5.0, dRel=20.0)
  )
  assert not _is_lead()


def test_is_lead_active_when_experimental_and_tracking():
  _set_plan(trackingLead=True)
  mock_ui_state.sm.valid["radarState"] = True
  mock_ui_state.sm["radarState"] = types.SimpleNamespace(
    leadOne=types.SimpleNamespace(status=True, vLead=5.0, dRel=20.0)
  )
  assert _is_lead()


def test_lead_data_slow():
  mock_ui_state.sm.valid["radarState"] = True
  mock_ui_state.sm["radarState"] = types.SimpleNamespace(
    leadOne=types.SimpleNamespace(status=True, vLead=5.0, dRel=25.0)
  )
  data = _lead_data()
  assert data.text == "SLOW"
  assert data.indicator_extra == "slower"
  assert data.indicator_value == 25.0
  assert data.indicator_type is IndicatorType.LEAD


def test_lead_data_stopped():
  mock_ui_state.sm.valid["radarState"] = True
  mock_ui_state.sm["radarState"] = types.SimpleNamespace(
    leadOne=types.SimpleNamespace(status=True, vLead=0.5, dRel=12.0)
  )
  data = _lead_data()
  assert data.text == "STOPPED"
  assert data.indicator_extra == "stopped"
  assert data.indicator_value == 12.0
  assert data.indicator_type is IndicatorType.LEAD


def test_is_stop_light():
  _set_plan(redLight=True)
  assert _is_stop_light()

  mock_ui_state.sm["starpilotPlan"].redLight = False
  assert not _is_stop_light()


@pytest.mark.parametrize(
  ("is_metric", "expected_distance", "expected_speed"),
  [
    (False, (33, "ft"), (22, "mph")),
    (True, (10, "m"), (36, "km/h")),
  ],
)
def test_aether_gauge_uses_display_units(is_metric, expected_distance, expected_speed):
  mock_ui_state.is_metric = is_metric

  assert _to_display_distance(10.0) == expected_distance
  assert _to_display_speed(10.0) == expected_speed


def test_is_curve_speed_follows_csc_activation_without_mode_gate(monkeypatch):
  monkeypatch.setattr(aethergauge, "_csc_state", lambda: {"active": True, "curvature": 0.002})
  assert _is_curve_speed()

  monkeypatch.setattr(aethergauge, "_csc_state", lambda: {"active": False, "curvature": 0.002})
  assert not _is_curve_speed()


def test_is_cem_curvature_requires_selected_cem_reason():
  _set_plan()
  mock_ui_state.conditional_status = CEStatus["SPEED"]
  assert not _is_cem_curvature()

  mock_ui_state.conditional_status = CEStatus["CURVATURE"]
  assert _is_cem_curvature()


def test_is_cem_curvature_uses_status_not_curvature_threshold():
  _set_plan(roadCurvature=0.00001)
  mock_ui_state.conditional_status = CEStatus["CURVATURE"]
  assert _is_cem_curvature()


def test_is_cem_curvature_requires_experimental_mode():
  _set_plan(experimentalMode=False)
  mock_ui_state.conditional_status = CEStatus["CURVATURE"]
  assert not _is_cem_curvature()


def test_is_cem_curvature_requires_cem_mode_enabled():
  _set_plan()
  mock_ui_state.conditional_status = CEStatus["CURVATURE"]
  mock_ui_state.starpilot_toggles["conditional_experimental_mode"] = False
  assert not _is_cem_curvature()


def test_is_cem_curvature_requires_curve_toggle():
  _set_plan()
  mock_ui_state.conditional_status = CEStatus["CURVATURE"]
  mock_ui_state.starpilot_toggles["conditional_curves"] = False
  assert not _is_cem_curvature()


def test_is_cem_curvature_rejects_stale_status_when_tracking_stops():
  _set_plan()
  mock_ui_state.conditional_status = CEStatus["CURVATURE"]
  mock_ui_state.sm["selfdriveState"].enabled = False
  assert not _is_cem_curvature()


def test_cem_curvature_data_preserves_curve_metrics(monkeypatch):
  _set_plan(roadCurvature=0.003, cscSpeed=8.0, vCruise=10.0)
  mock_ui_state.sm.valid["carState"] = True
  mock_ui_state.sm["carState"] = types.SimpleNamespace(vEgo=12.0)
  monkeypatch.setattr(aethergauge, "get_border_color", lambda _: aethergauge.COLOR_CEM_SPEED)

  data = _cem_curvature_data()

  assert isinstance(data, AetherGaugeData)
  assert data.indicator_type is IndicatorType.ROAD_CURVE
  assert data.indicator_value == pytest.approx(0.003)
  assert data.reduction_text


def test_widget_wires_cem_source_to_road_curve_data(monkeypatch):
  _set_plan(roadCurvature=0.003, cscSpeed=8.0, vCruise=10.0)
  mock_ui_state.sm.valid["carState"] = True
  mock_ui_state.sm["carState"] = types.SimpleNamespace(vEgo=12.0)
  mock_ui_state.conditional_status = CEStatus["CURVATURE"]
  monkeypatch.setattr(aethergauge, "_is_curve_speed", lambda: False)
  monkeypatch.setattr(aethergauge, "get_border_color", lambda _: aethergauge.COLOR_CEM_SPEED)
  monkeypatch.setattr(aethergauge.rl, "get_time", lambda: 1.0)

  gauge = AetherGauge()
  data = gauge.get_active_data()

  assert data is not None
  assert data.indicator_type is IndicatorType.ROAD_CURVE
  assert data.indicator_value == pytest.approx(0.003)


def test_csc_source_precedes_cem_source(monkeypatch):
  _set_plan(roadCurvature=0.003, cscSpeed=8.0, vCruise=10.0)
  mock_ui_state.sm.valid["carState"] = True
  mock_ui_state.sm["carState"] = types.SimpleNamespace(vEgo=12.0)
  mock_ui_state.conditional_status = CEStatus["CURVATURE"]
  monkeypatch.setattr(aethergauge, "_csc_state", lambda: {"active": True, "curvature": 0.01})
  monkeypatch.setattr(aethergauge, "get_border_color", lambda _: aethergauge.COLOR_CEM_SPEED)
  monkeypatch.setattr(aethergauge.rl, "get_time", lambda: 1.0)

  gauge = AetherGauge()
  data = gauge.get_active_data()

  assert data is not None
  assert data.indicator_type is IndicatorType.ROAD_CURVE
  assert data.indicator_value == pytest.approx(0.01)




def test_priority_downgrade_updates_live_immediately(monkeypatch):
  # Start at Priority 0 (Force Stop)
  _set_plan(forcingStop=True, redLight=False, forcingStopLength=20.0)
  mock_ui_state.sm.valid["carState"] = True
  mock_ui_state.sm["carState"] = types.SimpleNamespace(gearShifter=1)
  time_val = [1.0]
  monkeypatch.setattr(aethergauge.rl, "get_time", lambda: time_val[0])

  gauge = AetherGauge()
  data0 = gauge.get_active_data()
  assert data0.indicator_type is IndicatorType.FORCE_STOP
  assert data0.indicator_value == 20.0

  # Downgrade to Priority 1 (Stop Light)
  time_val[0] = 1.05  # only 50ms later (well before 0.5s cooldown)
  _set_plan(forcingStop=False, redLight=True, forcingStopLength=15.0)
  data1 = gauge.get_active_data()
  assert data1 is not None
  assert data1.indicator_type is IndicatorType.STOP_LIGHT
  assert data1.indicator_value == 15.0


def test_lead_data_schmitt_trigger_hysteresis():
  mock_ui_state.sm.valid["radarState"] = True

  # 1. Start fast -> SLOW
  mock_ui_state.sm["radarState"] = types.SimpleNamespace(
    leadOne=types.SimpleNamespace(status=True, vLead=3.0, dRel=20.0)
  )
  data = _lead_data()
  assert data.text == "SLOW"

  # 2. Slow down to 0.9 m/s (below 1.0, but above 0.8 entry) -> should STAY SLOW
  mock_ui_state.sm["radarState"].leadOne.vLead = 0.9
  data = _lead_data()
  assert data.text == "SLOW"

  # 3. Slow down to 0.7 m/s (below 0.8 entry) -> transitions to STOPPED
  mock_ui_state.sm["radarState"].leadOne.vLead = 0.7
  data = _lead_data()
  assert data.text == "STOPPED"

  # 4. Accelerate to 1.1 m/s (above 1.0, but below 1.2 exit) -> should STAY STOPPED
  mock_ui_state.sm["radarState"].leadOne.vLead = 1.1
  data = _lead_data()
  assert data.text == "STOPPED"

  # 5. Accelerate to 1.3 m/s (above 1.2 exit) -> transitions to SLOW
  mock_ui_state.sm["radarState"].leadOne.vLead = 1.3
  data = _lead_data()
  assert data.text == "SLOW"


def test_monotonic_ratchet_clamp_prevents_upward_bounce(monkeypatch):
  mock_ui_state.sm.valid["carState"] = True
  mock_ui_state.sm["carState"] = types.SimpleNamespace(vEgo=5.0, standstill=False)
  mock_ui_state.is_metric = True

  rendered_data = []
  gauge = AetherGauge()
  monkeypatch.setattr(gauge, "_render_unified_road", lambda rect, cx, cy, data, fb, fm, alpha: rendered_data.append(data))

  # Initial frame at 30m
  _set_plan(redLight=True, forcingStopLength=30.0)
  gauge.render(None, None, None, current_speed=10.0, cx=100.0, bottom=200.0)
  assert int(rendered_data[-1].text) == 30

  # Step closer: raw jumps UPWARD to 35m due to optical camera noise
  _set_plan(redLight=True, forcingStopLength=35.0)
  gauge.render(None, None, None, current_speed=10.0, cx=100.0, bottom=200.0)
  # Ratchet clamp must prevent the display number from increasing above 30m!
  assert int(rendered_data[-1].text) <= 30
