"""Optional GM grade compensation preserves the original physical demand law."""
import math
import unittest

import numpy as np

from opendbc.car.gm.carcontroller import bolt_euv_demands, volt_demands, volt_grade_demands


class TestLongPitch(unittest.TestCase):
  def test_original_off_counterexample_and_three_laws(self):
    self.assertEqual(bolt_euv_demands(-.5, 12., None, 1805., 2.63779, 400), (-284, 0))
    self.assertEqual(bolt_euv_demands(-.5, 12., [0., -.03, 0.], 1805., 2.63779, 400), (-466, 0))
    calls = ((bolt_euv_demands, (1805., 2.63779, 400), .25),
             (volt_demands, (.75, 1743., 2.694, -3.5, 2., 400), .75),
             (volt_grade_demands, (.25, -3.5, 2.), .25))
    for helper, args, threshold in calls:
      for speed in (threshold - 1e-6, threshold, threshold + 1e-6, 7., 12.):
        for accel in (-2., -.5, 0., 1.):
          flat = helper(accel, speed, [0., 0., 0.], *args)
          self.assertEqual(helper(accel, speed, None, *args), flat)
          for invalid in ([], [0.], [0., float('nan'), 0.], [0., float('inf'), 0.]):
            self.assertEqual(helper(accel, speed, invalid, *args), flat)
          for pitch in (-.03, .03):
            if speed <= threshold or (pitch > 0 and accel > 0):
              self.assertEqual(helper(accel, speed, [0., pitch, 0.], *args), flat)

  def test_controller_original_demand_and_literal_bytes(self):
    from unittest.mock import patch
    from opendbc.car.gm.carcontroller import CarController
    from opendbc.car.gm.tests.test_ascm_intercept import params
    from opendbc.car.gm.tests.test_bolt_euv_control import original_demand as euv_demand, original_frames
    from opendbc.car.gm.tests.test_volt_gateway_mapping import original_interp, _SPEED, _THRESHOLD
    from opendbc.car.gm.tests import test_volt_grade as fixture
    from opendbc.car.gm.values import CAR

    def volt_demand(cp, accel, speed, pitch):
      threshold_speed = .25 if cp.carFingerprint == CAR.CHEVROLET_VOLT_ASCM else .75
      grade = math.sin(pitch) * 9.81 if speed > threshold_speed else 0.
      grade = 0. if grade > 0 and accel > 0 else min(grade, .20)
      aero = .5 * .30 * (1.05 * cp.wheelbase + .0679) * 1.225 * speed ** 2 / cp.mass
      gas_accel = min(2., max(-4., accel + aero + grade))
      brake_accel = min(2., max(-4., accel + aero + grade * original_interp(speed, (5., 10.), (0., 1.))))
      threshold = original_interp(speed, _SPEED, _THRESHOLD)
      raw = round(original_interp(gas_accel, (threshold, max(0., threshold), 2.), (5500., 6150., 8191.)))
      brake = round(original_interp(brake_accel, (-4., threshold), (400., 0.)))
      return (5500 if brake > 0 else min(8191, max(5500, raw))), min(400, max(0, brake))

    for candidate in (CAR.CHEVROLET_BOLT_EUV, CAR.CHEVROLET_VOLT, CAR.CHEVROLET_VOLT_ASCM):
      for alpha in (False, True):
        cp = params(candidate, alpha=alpha, radar=candidate == CAR.CHEVROLET_VOLT,
                    sascm=candidate == CAR.CHEVROLET_VOLT_ASCM)
        for enabled in (True, False):
          for frame in (0, 4, 8, 12):
            for speed, accel, pitch in ((12., -.5, -.03), (7., -2., .03), (12., 1., .03),
                                        (.25, -.5, -.03), (.3, -.5, -.03), (.75, -.5, -.03), (2., 2., -.03)):
              with self.subTest(candidate=candidate, alpha=alpha, enabled=enabled, frame=frame, speed=speed, accel=accel):
                def create(*args, enabled=enabled):
                  controller = CarController(*args)
                  self.assertTrue(controller.long_pitch)
                  controller.long_pitch = enabled
                  return controller
                with patch.object(fixture, 'CarController', side_effect=create):
                  actual, messages = fixture.command(cp, accel=accel, speed=speed, orientation=[0., pitch, 0.], frame=frame)
                if not cp.openpilotLongitudinalControl:
                  self.assertFalse(any(m[0] in (0x2cb, 0x315) for m in messages))
                  continue
                a, v, p = (float(np.float32(x)) for x in (accel, speed, pitch if enabled else 0.))
                raw, brake = (euv_demand(cp, True, v, a, 'pid', False, p) if candidate == CAR.CHEVROLET_BOLT_EUV
                              else volt_demand(cp, a, v, p))
                self.assertEqual((actual.apply_gas, actual.apply_brake), (raw - 6150, brake))
                expected = original_frames(raw, brake, frame // 4, True, False)[:2]
                if candidate != CAR.CHEVROLET_BOLT_EUV:
                  mode = 10 if brake else 1
                  encoded_brake = (-brake) & 4095
                  checksum = (65536 - (mode << 12) - encoded_brake - frame // 4) & 65535
                  expected[1] = (0x315, bytes([(mode << 4) | (encoded_brake >> 8), encoded_brake & 255,
                                               checksum >> 8, checksum & 255, frame // 4]),
                                 0 if candidate == CAR.CHEVROLET_VOLT_ASCM else 2)
                self.assertEqual([m for m in messages if m[0] in (0x2cb, 0x315)], expected)
