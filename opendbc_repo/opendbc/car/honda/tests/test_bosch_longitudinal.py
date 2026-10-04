import math
import time
from types import SimpleNamespace

import pytest

from opendbc.car import ACCELERATION_DUE_TO_GRAVITY, gen_empty_fingerprint, structs
from opendbc.car.honda.bosch_longitudinal import BoschLongitudinal, qualified
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, CarControllerParams


def owner(identity=CAR.HONDA_ACCORD):
  cp = CarInterface.get_params(identity, gen_empty_fingerprint(), [], True, False, False)
  assert qualified(cp)
  return BoschLongitudinal(cp, CarControllerParams(cp))


def inputs(speed=0.0, measured=0.0, active=True, state="pid", gas=False, brake=False):
  cc = structs.CarControl(longActive=active)
  cc.actuators.longControlState = state
  cs = SimpleNamespace(out=SimpleNamespace(vEgo=speed, aEgo=measured, gasPressed=gas, brakePressed=brake))
  return cc, cs


def test_pitch_observation_retains_odd_frame_sample_for_next_command():
  controller = owner()
  controller.observe_orientation((0.0, 0.1, 0.0))
  controller.observe_orientation(())
  cc, cs = inputs(state="off")
  result = controller.update(cc, cs, 0.0)
  assert result[2] == pytest.approx(math.sin(0.1) * ACCELERATION_DUE_TO_GRAVITY)
  controller.observe_orientation((0.0, -0.1, 0.0))
  assert controller.update(cc, cs, 0.0)[2] < 0


def test_disabled_update_preserves_original_gas_ramp_without_requesting_brakes():
  controller = owner()
  cc, cs = inputs(active=False, state="off")
  controller.observe_orientation((0.0, 0.2, 0.0))
  first = controller.update(cc, cs, 0.0)
  second = controller.update(cc, cs, 0.0)
  assert first[1] == 60.0
  assert second[1] == 120.0
  assert first[3] is second[3] is False
  assert controller.bosch_gas_factor == controller.bosch_wind_factor == 1.0


@pytest.mark.parametrize("identity,rate", ((CAR.HONDA_ACCORD, 50.0), (CAR.HONDA_INSIGHT, 150.0),
                                         (CAR.ACURA_RDX_3G, 300.0), (CAR.ACURA_RDX_3G_MMR, 300.0)))
def test_learning_uses_actual_vehicle_rate_and_driver_gas_override(identity, rate):
  controller = owner(identity)
  cc, cs = inputs(measured=0.5)
  controller.update(cc, cs, 1.0)
  assert controller.bosch_gas_factor == pytest.approx(1.0 + 0.5 / rate)
  previous = controller.bosch_gas_factor
  cs.out.gasPressed = True
  controller.update(cc, cs, 1.0)
  assert controller.bosch_gas_factor == previous


def test_braking_hysteresis_stopping_and_inactive_release():
  controller = owner()
  cc, cs = inputs(state="off")
  assert controller.update(cc, cs, -0.13)[3]
  assert controller.update(cc, cs, -0.03)[3]
  assert not controller.update(cc, cs, -0.01)[3]
  cc.actuators.longControlState = "stopping"
  assert controller.update(cc, cs, 0.1)[3]
  cc.longActive = False
  assert not controller.update(cc, cs, 0.0)[3]


def test_saved_factors_keep_shared_learner_range_and_reject_invalid_values():
  controller = owner()
  controller.set_factors(0.01, 5.0)
  assert (controller.bosch_gas_factor, controller.bosch_wind_factor) == (0.01, 5.0)
  controller.set_factors(float("nan"), float("inf"))
  assert (controller.bosch_gas_factor, controller.bosch_wind_factor) == (1.0, 1.0)


def test_actual_controller_captures_pitch_on_non_transmit_frame():
  cp = CarInterface.get_params(CAR.HONDA_ACCORD, gen_empty_fingerprint(), [], True, False, False)
  ci = CarInterface(cp)
  ci.update([])
  command = structs.CarControl()
  command.actuators.longControlState = "off"
  ci.apply(command.as_reader(), 1_000_000_000)
  command.orientationNED = [0.0, 0.1, 0.0]
  ci.apply(command.as_reader(), 1_010_000_000)
  command.orientationNED = []
  ci.apply(command.as_reader(), 1_020_000_000)
  assert ci.CC.bosch_longitudinal.pitch == pytest.approx(0.1)
  assert ci.CC.bosch_longitudinal.bosch_last_gas > 0.0


def test_actual_configure_loads_typed_factors_without_startup_rewrite():
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.starpilot.controller_extensions import configure_controller

  with OpenpilotPrefix():
    saved = Params()
    saved.put("HondaGasFactorParams", 1.25, block=True)
    saved.put("HondaWindFactorParams", 0.85, block=True)
    cp = CarInterface.get_params(CAR.HONDA_ACCORD, gen_empty_fingerprint(), [], True, False, False)
    ci = CarInterface(cp)
    configure_controller(ci, saved)
    learning = ci.CC.bosch_learning_params
    assert learning.owner is ci.CC.bosch_longitudinal
    assert (learning.owner.bosch_gas_factor, learning.owner.bosch_wind_factor) == (1.25, 0.85)
    learning.owner.set_factors(1.1, 0.9)
    learning.persist(0)
    learning.persist(5999)
    assert saved.get("HondaGasFactorParams") == 1.25
    assert saved.get("HondaWindFactorParams") == 0.85
    learning.persist(6000)
    deadline = time.monotonic() + 2.0
    while saved.get("HondaWindFactorParams") != 0.9 and time.monotonic() < deadline:
      time.sleep(0.01)
    assert saved.get("HondaGasFactorParams") == pytest.approx(1.1)
    assert saved.get("HondaWindFactorParams") == pytest.approx(0.9)
