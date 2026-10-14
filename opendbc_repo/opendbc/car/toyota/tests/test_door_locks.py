"""Actual factory Toyota controller emits only one stationary transition command."""

import pytest

from opendbc.car import structs
from opendbc.car.toyota.door_locks import LOCK_CMD, UNLOCK_CMD
from opendbc.car.toyota.tests.test_auto_hold import setup_hold, step_hold
from opendbc.car.toyota.values import CAR

Gear = structs.CarState.GearShifter


def body_commands(controller, command, state):
  return [frame for frame in step_hold(controller, command, state) if frame[0] == 0x750 and frame[1] in (LOCK_CMD, UNLOCK_CMD)]


@pytest.mark.parametrize('car', [CAR.TOYOTA_PRIUS, CAR.TOYOTA_COROLLA_TSS2, CAR.TOYOTA_RAV4_TSS2])
def test_actual_controller_park_drive_park_one_shot_with_no_control_enable(car):
  _, controller, command, state = setup_hold(car, enabled=False)
  assert not command.enabled and not command.latActive and not command.longActive
  controller.door_locks.lock = controller.door_locks.unlock = True
  state.out.gearShifter = Gear.park
  assert body_commands(controller, command, state) == []
  state.out.gearShifter = Gear.drive
  assert body_commands(controller, command, state) == [(0x750, LOCK_CMD, 0)]
  assert body_commands(controller, command, state) == []
  state.out.gearShifter = Gear.park
  assert body_commands(controller, command, state) == [(0x750, UNLOCK_CMD, 0)]
  assert body_commands(controller, command, state) == []


@pytest.mark.parametrize('fault', ['moving', 'door', 'gas', 'invalid_can', 'timeout', 'invalid_sensors'])
def test_actual_controller_rejects_physical_or_source_fault_at_transition(fault):
  _, controller, command, state = setup_hold(enabled=False)
  controller.door_locks.lock = controller.door_locks.unlock = True
  state.out.gearShifter = Gear.park
  assert body_commands(controller, command, state) == []
  state.out.gearShifter = Gear.drive
  if fault == 'moving':
    state.out.standstill, state.out.vEgoRaw = False, 1.0
  elif fault == 'door':
    state.out.doorOpen = True
  elif fault == 'gas':
    state.out.gasPressed = True
  elif fault == 'invalid_can':
    state.out.canValid = False
  elif fault == 'timeout':
    state.out.canTimeout = True
  else:
    state.out.vehicleSensorsInvalid = True
  assert body_commands(controller, command, state) == []


def test_defaults_off_and_starting_in_drive_never_create_transition():
  _, controller, command, state = setup_hold(enabled=False)
  state.out.gearShifter = Gear.park
  assert body_commands(controller, command, state) == []
  state.out.gearShifter = Gear.drive
  assert body_commands(controller, command, state) == []
  _, controller, command, state = setup_hold(enabled=False)
  controller.door_locks.lock = True
  assert body_commands(controller, command, state) == []
