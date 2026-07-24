from types import SimpleNamespace

import pytest

from openpilot.starpilot.common.experimental_state import CEStatus
from openpilot.starpilot.controls.lib.unified_longitudinal_intent import (
  MODEL_STOP_ENTER,
  UnifiedLongitudinalIntent,
)


class FakeParamsMemory:
  def __init__(self):
    self.values = {}

  def put_int(self, key, value):
    self.values[key] = value


def make_controller():
  planner = SimpleNamespace(
    params_memory=FakeParamsMemory(),
    driving_in_curve=False,
    road_curvature_detected=False,
    starpilot_vcruise=SimpleNamespace(
      forcing_stop=False,
      stop_sign_confirmed=False,
      slc=SimpleNamespace(experimental_mode=False),
    ),
  )
  return planner, UnifiedLongitudinalIntent(planner)


def make_sm(*, v_ego=10.0, should_stop=False, model_distance=100.0,
            end_speed=10.0, traffic=False, lead_one=None, lead_two=None):
  model = SimpleNamespace(
    action=SimpleNamespace(shouldStop=should_stop),
    position=SimpleNamespace(x=[0.0, model_distance]),
    velocity=SimpleNamespace(x=[v_ego, end_speed]),
  )
  empty_lead = SimpleNamespace(status=False)
  return {
    "modelV2": model,
    "carState": SimpleNamespace(
      standstill=v_ego == 0.0,
      leftBlinker=False,
      rightBlinker=False,
      steeringAngleDeg=0.0,
    ),
    "radarState": SimpleNamespace(
      leadOne=lead_one or empty_lead,
      leadTwo=lead_two or empty_lead,
    ),
    "starpilotCarState": SimpleNamespace(trafficModeEnabled=traffic),
  }


def toggles(model_first=False):
  return SimpleNamespace(longitudinal_model_preference=model_first)


def settle(controller, sm, *, v_ego=10.0, frames=20):
  for _ in range(frames):
    controller.update(v_ego, sm, toggles())


def test_open_road_has_no_stop_intent():
  _, controller = make_controller()
  sm = make_sm()

  settle(controller, sm)

  assert not controller.stop_detected
  assert controller.status_value == CEStatus["OFF"]


def test_model_stop_is_filtered_then_latched():
  _, controller = make_controller()
  sm = make_sm(model_distance=5.0, end_speed=0.0)

  while controller.stop_filter.x < MODEL_STOP_ENTER:
    controller.update(10.0, sm, toggles())

  assert controller.stop_detected
  assert controller.status_value == CEStatus["STOP_LIGHT"]


def test_stop_intent_releases_with_hysteresis():
  _, controller = make_controller()
  stop_scene = make_sm(should_stop=True)
  settle(controller, stop_scene)
  assert controller.stop_detected

  clear_scene = make_sm()
  controller.update(10.0, clear_scene, toggles())
  assert controller.stop_detected
  settle(controller, clear_scene)
  assert not controller.stop_detected


@pytest.mark.parametrize("hard_stop", ["forcing_stop", "stop_sign_confirmed"])
def test_explicit_stop_sources_pin_intent(hard_stop):
  planner, controller = make_controller()
  setattr(planner.starpilot_vcruise, hard_stop, True)

  controller.update(5.0, make_sm(v_ego=5.0), toggles())

  assert controller.stop_detected
  assert controller.status_value == CEStatus["STOP_LIGHT"]


def test_committed_turn_vetoes_model_stop_false_positive():
  planner, controller = make_controller()
  planner.driving_in_curve = True
  sm = make_sm(v_ego=4.0, should_stop=True)
  sm["carState"].leftBlinker = True
  sm["carState"].steeringAngleDeg = 60.0

  settle(controller, sm, v_ego=4.0)

  assert not controller.stop_detected


def test_traffic_mode_vetoes_model_stop_but_not_explicit_force_stop():
  planner, controller = make_controller()
  sm = make_sm(should_stop=True, traffic=True)
  settle(controller, sm)
  assert not controller.stop_detected

  planner.starpilot_vcruise.forcing_stop = True
  controller.update(10.0, sm, toggles())
  assert controller.stop_detected


def test_either_credible_slow_lead_slot_sets_diagnostic_status():
  _, controller = make_controller()
  slow_lead = SimpleNamespace(
    status=True,
    dRel=25.0,
    vLead=4.0,
    modelProb=0.95,
    radar=False,
  )
  sm = make_sm(v_ego=10.0, lead_two=slow_lead)

  settle(controller, sm)

  assert not controller.stop_detected
  assert controller.status_value == CEStatus["LEAD"]


def test_model_first_preference_is_status_only_not_a_separate_controller():
  planner, controller = make_controller()

  controller.update(10.0, make_sm(), toggles(model_first=True))

  assert not controller.stop_detected
  assert controller.status_value == CEStatus["USER_OVERRIDDEN"]
  assert planner.params_memory.values["CEStatus"] == CEStatus["USER_OVERRIDDEN"]
