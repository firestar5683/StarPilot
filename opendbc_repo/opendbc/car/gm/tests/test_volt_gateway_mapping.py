"""Gateway Volt demand mapping and exact configuration admission."""

import math
import unittest
from bisect import bisect_right

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.longitudinal import volt_policy_for
from opendbc.car.gm.profiles import profiles_supported
from opendbc.car.gm.tests.test_volt_grade import command, params
from opendbc.car.gm.values import CAR, DBC, GMSafetyFlags


# Literal tables and coefficients from the original Dom values.py/controller.py.
_SPEED = (1.29, 1.52, 1.55, 1.6, 1.7, 1.8, 2.0, 2.2, 2.5, 5.52, 9.6, 20.5, 23.5, 35.0)
_THRESHOLD = (0.0, -0.14, -0.16, -0.18, -0.215, -0.255, -0.32, -0.41,
              -0.5, -0.72, -0.895, -1.125, -1.145, -1.16)


def original_interp(x, xp, fp):
  # np.interp selects the last duplicate breakpoint, including x=0 at low speed.
  i = bisect_right(xp, x)
  if i == 0:
    return fp[0]
  if i == len(xp):
    return fp[-1]
  return fp[i - 1] + (x - xp[i - 1]) * (fp[i] - fp[i - 1]) / (xp[i] - xp[i - 1])


def original_demand(accel, speed, pitch, mass, wheelbase):
  grade = math.sin(pitch) * 9.81 if pitch is not None and speed > .75 else 0.0
  grade = 0.0 if grade > 0 and accel > 0 else min(grade, .20)
  aero = .5 * .30 * (1.05 * wheelbase + .0679) * 1.225 * speed ** 2 / mass
  gas_accel = min(2., max(-4., accel + aero + grade))
  brake_accel = min(2., max(-4., accel + aero + grade * original_interp(speed, (5., 10.), (0., 1.))))
  threshold = original_interp(speed, _SPEED, _THRESHOLD)
  raw = round(original_interp(gas_accel, (threshold, max(0., threshold), 2.), (5500., 6150., 8191.)))
  brake = round(original_interp(brake_accel, (-4., threshold), (400., 0.)))
  raw = min(8191, max(5500, raw))
  brake = min(400, max(0, brake))
  return (5500 if brake > 0 else raw) - 6150, brake


class TestVoltGatewayMapping(unittest.TestCase):
  def test_final_cp_admission_and_restored_policy(self):
    expected = int(GMSafetyFlags.EV | GMSafetyFlags.VOLT_GATEWAY_LONG)
    for alpha in (False, True):
      cp = params(CAR.CHEVROLET_VOLT, alpha=alpha)
      self.assertEqual(cp.safetyConfigs[0].safetyParam, expected)
      self.assertTrue(cp.openpilotLongitudinalControl)
      self.assertFalse(cp.pcmCruise or cp.radarUnavailable or cp.dashcamOnly)
      self.assertEqual(cp.networkLocation, structs.CarParams.NetworkLocation.gateway)
      self.assertEqual(CarController(DBC[cp.carFingerprint], cp).params.MAX_GAS, 2041)
      self.assertIsNotNone(volt_policy_for(cp))
      self.assertTrue(profiles_supported(cp))
      for invalid in (int(GMSafetyFlags.EV), expected | int(GMSafetyFlags.HW_CAM),
                      expected | int(GMSafetyFlags.PEDAL_LONG), expected | int(GMSafetyFlags.NO_ACC)):
        bad = params(CAR.CHEVROLET_VOLT, alpha=alpha)
        bad.safetyConfigs[0].safetyParam = invalid
        self.assertIsNone(volt_policy_for(bad))
        self.assertFalse(profiles_supported(bad))
        self.assertFalse(CarController(DBC[bad.carFingerprint], bad).volt_gateway_long)
      no_radar = CarInterface.get_params(CAR.CHEVROLET_VOLT, gen_empty_fingerprint(), [], alpha, False, False)
      # A missing radar and camera header cannot admit the new selector.
      self.assertEqual(no_radar.safetyConfigs[0].safetyParam, int(GMSafetyFlags.EV))
      self.assertTrue(no_radar.radarUnavailable and no_radar.dashcamOnly)
      self.assertIsNone(volt_policy_for(no_radar))
      self.assertEqual(CarController(DBC[no_radar.carFingerprint], no_radar).params.MAX_GAS, 1018)
      for field, value in (('radarUnavailable', True), ('passive', True), ('dashcamOnly', True),
                           ('pcmCruise', True), ('flags', 1)):
        rejected = params(CAR.CHEVROLET_VOLT, alpha=alpha)
        setattr(rejected, field, value)
        self.assertFalse(profiles_supported(rejected), field)
        controller = CarController(DBC[rejected.carFingerprint], rejected)
        self.assertFalse(controller.volt_gateway_long, field)
        self.assertEqual(controller.params.MAX_GAS, 1018, field)

  def test_original_flat_wire_examples(self):
    # Original-controller commands, normalized via the proven DBC bit equivalence.
    rows = ((2., -.5, -650, 19, '4142abe000bd541f', 'afed501201'),
            (10., 0., 31, 0, '4142c12800bd3ed7', '1000efff01'),
            (10., 1., 1052, 0, '4142e11000bd1eef', '1000efff01'),
            (2., 2., 2041, 0, '4142fff800bd0007', '1000efff01'))
    for alpha in (False, True):
      cp = params(CAR.CHEVROLET_VOLT, alpha=alpha)
      for speed, accel, gas, brake, gas_hex, brake_hex in rows:
        with self.subTest(alpha=alpha, speed=speed, accel=accel):
          controller, messages = command(cp, accel=accel, speed=speed, orientation=[])
          self.assertEqual((controller.apply_gas, controller.apply_brake), (gas, brake))
          self.assertEqual(next(msg[1].hex() for msg in messages if msg[0] == 0x2CB), gas_hex)
          self.assertEqual(next(msg[1].hex() for msg in messages if msg[0] == 0x315), brake_hex)

  def test_independent_original_equation_across_breakpoints_and_pitch(self):
    for alpha in (False, True):
      cp = params(CAR.CHEVROLET_VOLT, alpha=alpha)
      for speed in (0., .5, .75, .7501, 5., 10., 35., 50.,
                    *(s + d for s in _SPEED for d in (-.0001, 0., .0001))):
        for accel in (-4., -2., -1.5, -.5, 0., .5, 1., 2.):
          for pitch in (None, -.06, .06):
            with self.subTest(alpha=alpha, speed=speed, accel=accel, pitch=pitch):
              controller, _ = command(cp, accel=accel, speed=speed,
                                      orientation=[] if pitch is None else [0., pitch, 0.])
              # CarState and CarControl serialize their numeric inputs to float32.
              state_speed = float(structs.CarState(vEgo=speed).as_reader().vEgo)
              control_accel = float(structs.CarControl(actuators=structs.CarControl.Actuators(accel=accel)).as_reader().actuators.accel)
              state_pitch = None if pitch is None else float(structs.CarControl(orientationNED=[0., pitch, 0.]).as_reader().orientationNED[1])
              self.assertEqual((controller.apply_gas, controller.apply_brake),
                               original_demand(control_accel, state_speed, state_pitch, cp.mass, cp.wheelbase))


if __name__ == '__main__':
  unittest.main()
