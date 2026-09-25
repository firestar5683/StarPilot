import unittest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, structs
from opendbc.car.toyota import toyotacan
from opendbc.car.toyota.carcontroller import CarController
from opendbc.car.toyota.carstate import CarState
from opendbc.car.toyota.interface import CarInterface, apply_toyota_auto_hold, toyota_auto_hold_supported
from opendbc.car.toyota.values import CAR, DBC, ToyotaFlags, ToyotaSafetyFlags, TOYOTA_AUTO_HOLD_CARS
from opendbc.safety import ALTERNATIVE_EXPERIENCE as AE


def setup_hold(car=CAR.TOYOTA_COROLLA_TSS2, enabled=True):
  cp = CarInterface.get_params(car, {0: {}, 1: {}, 2: {}}, [], False, False, False)
  apply_toyota_auto_hold(cp, enabled)
  state = CarState(cp)
  state.out = structs.CarState()
  state.out.standstill = True
  state.out.brakePressed = True
  state.out.cruiseState.available = True
  state.out.gearShifter = structs.CarState.GearShifter.drive
  return cp, CarController(DBC[car], cp), structs.CarControl(), state


def step_hold(controller, command, state):
  return controller.update(command.as_reader(), state, controller.frame * 10_000_000)[1]


def decode(cp, frame, name):
  parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [(name, 0)], frame[2])
  parser.update([(1, [frame])])
  return parser.vl[name]


class TestToyotaAutoHold(unittest.TestCase):
  def test_admission_and_default_off_preserve_unrelated_bits(self):
    for car in CAR:
      with self.subTest(car=car):
        cp = CarInterface.get_params(car, {0: {}, 1: {}, 2: {}}, [], False, False, False)
        self.assertFalse(cp.flags & ToyotaFlags.AUTO_BRAKE_HOLD)
        cp.alternativeExperience = AE.ALLOW_AEB | AE.DISABLE_STOCK_AEB
        expected = car in TOYOTA_AUTO_HOLD_CARS and cp.openpilotLongitudinalControl and not cp.dashcamOnly
        self.assertEqual(apply_toyota_auto_hold(cp, True), expected)
        if expected:
          bit = AE.TOYOTA_AEB_HOLD if car == CAR.TOYOTA_CAMRY_TSS2 else AE.TOYOTA_AUTO_HOLD
          self.assertEqual(cp.alternativeExperience, bit | AE.ALLOW_AEB | AE.DISABLE_STOCK_AEB)
        apply_toyota_auto_hold(cp, False)
        self.assertEqual(cp.alternativeExperience, AE.ALLOW_AEB | AE.DISABLE_STOCK_AEB)
        self.assertFalse(cp.flags & ToyotaFlags.AUTO_BRAKE_HOLD)
    for field in ('passive', 'notCar', 'dashcamOnly'):
      cp, _, _, _ = setup_hold(enabled=False)
      setattr(cp, field, True)
      self.assertFalse(toyota_auto_hold_supported(cp))
    cp, _, _, _ = setup_hold(enabled=False)
    cp.brand = 'subaru'
    cp.flags = 4096
    cp.alternativeExperience = 128
    self.assertFalse(apply_toyota_auto_hold(cp, True))
    self.assertEqual((cp.flags, cp.alternativeExperience), (4096, 128))
    cp, _, _, _ = setup_hold(enabled=False)
    cp.safetyConfigs[0].safetyParam |= int(ToyotaSafetyFlags.STOCK_LONGITUDINAL)
    self.assertFalse(apply_toyota_auto_hold(cp, True))

  def test_acc_activation_brake_release_and_cancel(self):
    cp, controller, command, state = setup_hold()
    for _ in range(100):
      step_hold(controller, command, state)
      self.assertFalse(controller.brake_hold_active)
    step_hold(controller, command, state)
    self.assertTrue(controller.brake_hold_active)
    state.out.brakePressed = False
    for _ in range(5):
      sends = step_hold(controller, command, state)
      for frame in sends:
        if frame[0] == 0x343:
          values = decode(cp, frame, 'ACC_CONTROL')
          self.assertEqual(values['ACCEL_CMD'], -1.0)
          self.assertEqual(values['PERMIT_BRAKING'], 1)
          self.assertEqual(values['RELEASE_STANDSTILL'], 0)
          self.assertEqual(values['CANCEL_REQ'], 0)
    command.cruiseControl.cancel = True
    step_hold(controller, command, state)
    self.assertFalse(controller.brake_hold_active)
    self.assertEqual(controller._brake_hold_counter, 0)

  def test_acc_and_camry_sensor_revocations(self):
    for car in (CAR.TOYOTA_COROLLA_TSS2, CAR.TOYOTA_CAMRY_TSS2):
      for cause in ('gas', 'moving', 'main', 'cruise', 'park', 'reverse'):
        with self.subTest(car=car, cause=cause):
          _, controller, command, state = setup_hold(car)
          for _ in range(101):
            step_hold(controller, command, state)
          self.assertTrue(controller.brake_hold_active)
          if cause == 'gas':
            state.out.gasPressed = True
          elif cause == 'moving':
            state.out.standstill = False
          elif cause == 'main':
            state.out.cruiseState.available = False
          elif cause == 'cruise':
            state.out.cruiseState.enabled = True
          else:
            state.out.gearShifter = getattr(structs.CarState.GearShifter, cause)
          step_hold(controller, command, state)
          self.assertFalse(controller.brake_hold_active)
          self.assertEqual(controller._brake_hold_counter, 0)

  def test_interrupted_brake_dwell_preserves_source_counter(self):
    _, controller, command, state = setup_hold()
    for _ in range(50):
      step_hold(controller, command, state)
    state.out.brakePressed = False
    for _ in range(10):
      step_hold(controller, command, state)
    self.assertEqual(controller._brake_hold_counter, 50)
    state.out.brakePressed = True
    for _ in range(50):
      step_hold(controller, command, state)
    self.assertFalse(controller.brake_hold_active)
    step_hold(controller, command, state)
    self.assertTrue(controller.brake_hold_active)

  def test_camry_source_cancel_distinction_and_pulse(self):
    cp, controller, command, state = setup_hold(CAR.TOYOTA_CAMRY_TSS2)
    command.cruiseControl.cancel = True
    for _ in range(101):
      sends = step_hold(controller, command, state)
    self.assertTrue(controller.brake_hold_active)
    frame = next(frame for frame in sends if frame[0] == 0x344)
    values = decode(cp, frame, 'PRE_COLLISION_2')
    self.assertEqual(values['DSS1GDRV'], -1.0)
    self.assertEqual(values['PBRTRGR'], 1)
    self.assertEqual(frame[2], 0)
    self.assertFalse(any(frame[0] == 0x344 for frame in step_hold(controller, command, state)))
    for tick in (726, 728, 730):
      frame = toyotacan.create_brake_hold_command(controller.packer, tick, {}, True)
      self.assertEqual(decode(cp, frame, 'PRE_COLLISION_2')['PBRTRGR'], tick % 730 < 727)

  def test_camry_camera_capture_and_inactive_pass_through(self):
    cp, controller, command, state = setup_hold(CAR.TOYOTA_CAMRY_TSS2)
    camera = CANPacker(DBC[cp.carFingerprint][Bus.pt]).make_can_msg('PRE_COLLISION_2', 2,
      {'DSS1GDRV': -0.5, 'PBRTRGR': 1, 'DS1STAT2': 3, 'PCSWAR': 1, 'PCSABK': 1, 'BRKHLD': 1, 'PCSDIS': 1})
    parsers = state.get_can_parsers(cp)
    state.update(parsers)
    parsers[Bus.cam].update([(1_000_000_000, [camera])])
    state.update(parsers)
    output = toyotacan.create_brake_hold_command(controller.packer, 0, state.pre_collision_2, False)
    self.assertEqual(output[1], camera[1])
    self.assertIn('PRE_COLLISION_2', parsers[Bus.cam].vl)
    cp, _, _, _ = setup_hold(CAR.TOYOTA_CAMRY_TSS2, enabled=False)
    self.assertNotIn('PRE_COLLISION_2', CarState.get_can_parsers(cp)[Bus.cam].vl)

  def test_feature_off_has_no_hold_or_camera_messages(self):
    for car in (CAR.TOYOTA_COROLLA_TSS2, CAR.TOYOTA_CAMRY_TSS2):
      cp, controller, command, state = setup_hold(car, False)
      packer = CANPacker(DBC[car][Bus.pt])
      for _ in range(105):
        sends = step_hold(controller, command, state)
        self.assertFalse(controller.brake_hold_active)
        self.assertFalse(any(frame[0] == 0x344 for frame in sends))
        for frame in sends:
          if frame[0] == 0x343:
            self.assertEqual(frame, toyotacan.create_accel_command(packer, 0, False, True, False, True, 1, False, 0))
