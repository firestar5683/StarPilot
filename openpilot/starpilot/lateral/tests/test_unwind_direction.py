"""Exercise magnitude-based unwind through each production torque policy."""
from collections import deque
from unittest.mock import patch

import pytest

from opendbc.car import structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR as HYUNDAI
from opendbc.car.toyota.values import CAR as TOYOTA
from opendbc.car.vehicle_model import VehicleModel
from openpilot.cereal import log
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.starpilot.lateral.torque_extension import selected_policy


@pytest.mark.parametrize('vehicle', [HYUNDAI.GENESIS_G70_2020, HYUNDAI.GENESIS_GV70_ELECTRIFIED_1ST_GEN,
                                     TOYOTA.TOYOTA_COROLLA_TSS2, HYUNDAI.HYUNDAI_IONIQ_6])
@pytest.mark.parametrize('previous,current,expected', [(.25, .1, True), (-.25, -.1, True),
                                                     (.1, .25, False), (-.1, -.25, False),
                                                     (.1, -.1, False), (-.1, .1, False),
                                                     (.1, 0., True), (-.1, 0., True), (0., 0., False)])
def test_actual_pid_unwind_is_mirrored_and_handles_zero_crossing(vehicle, previous, current, expected):
  cp = interfaces[vehicle].get_non_essential_params(vehicle)
  controller = LatControlTorque(cp.as_reader(), interfaces[vehicle](cp), .01)
  owner = selected_policy(controller)
  assert owner is not None
  cs = structs.CarState.new_message(vEgo=25., steeringAngleDeg=0., steeringPressed=False, gearShifter='drive')
  params = log.VehicleParameters.new_message(angleOffsetDeg=0., roll=0.)
  curvature = current / cs.vEgo ** 2
  owner.curvature_request_buffer = deque([curvature] * owner.request_buffer_len, maxlen=owner.request_buffer_len)
  owner.prev_desired_lateral_accel = previous
  with patch.object(controller.pid, 'update', wraps=controller.pid.update) as pid:
    _, _, state = controller.update(True, cs, VehicleModel(cp), params, False, curvature, False, .2)
  assert state.active
  assert owner.prev_desired_lateral_accel == pytest.approx(current)
  assert bool(pid.call_args.kwargs['freeze_integrator']) is expected
