"""Exact Mach-E extension intersects current Ford safety; variant-select methods."""
import unittest

from opendbc.safety.tests import test_ford as ford
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests import test_ford_aol


class TestFordMachEExtended(unittest.TestCase):
  SAFETY_PARAM = 18
  REQUIRES_DEBUG = None
  MAX_CURVATURE_ERROR = 0.006

  def setUp(self):
    safety = libsafety_py.libsafety
    debug = safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) == 0
    safety.set_safety_hooks(CarParams.SafetyModel.noOutput, 0)
    safety.set_alternative_experience(0)
    if self.REQUIRES_DEBUG is not None and debug != self.REQUIRES_DEBUG:
      self.skipTest("This case requires " + ("DEBUG" if self.REQUIRES_DEBUG else "RELEASE") + " safety")
    self._message_fixture = ford.TestFordCANFDStockSafety()
    self._message_fixture.SAFETY_PARAM = self.SAFETY_PARAM
    self._message_fixture.setUp()

  def __getattr__(self, name):
    fixture = self.__dict__.get("_message_fixture")
    if fixture is None:
      raise AttributeError(name)
    return getattr(fixture, name)

  def announce(self, active=True, forbidden=False):
    msg = self._lkas_command_msg(0)
    msg[0].data[4] = (2 if active else 0) | int(forbidden)
    return self._tx(msg)

  def prepare(self, speed=5.0, curvature=0.0195):
    self._reset_curvature_measurement(curvature, speed)
    self._set_prev_desired_angle(curvature)
    self.safety.set_controls_allowed(True)

  def command(self, enabled=True, curvature=0.0195, rate=0.0, angle=0.02, offset=0.0, *, increment_timer=True):
    return self._lat_ctl_msg(enabled, offset, angle, curvature, rate, increment_timer=increment_timer)

  def test_accepted_announcement_required_rejected_frame_cannot_grant(self):
    self.prepare()
    self.assertFalse(self._tx(self.command()))
    self.assertFalse(self.announce(forbidden=True))
    self.prepare()
    self.assertFalse(self._tx(self.command()))
    self.assertTrue(self.announce())
    self.prepare()
    self.assertTrue(self._tx(self.command()))
    self.assertTrue(self.announce(active=False))
    self.prepare()
    self.assertFalse(self._tx(self.command()))

  def test_original_path_recipe_and_inactive_fields(self):
    self.assertTrue(self.announce())
    self.prepare()
    self.assertTrue(self._tx(self.command()))
    for kwargs in ({'angle': -0.02}, {'angle': 0.161}, {'angle': 0.08}, {'curvature': 0.0194}, {'offset': 0.01}):
      with self.subTest(kwargs=kwargs):
        self.prepare()
        self.assertFalse(self._tx(self.command(**kwargs)))
    self.prepare()
    self.assertTrue(self._tx(self.command(enabled=False, curvature=0.0, angle=0.0)))
    self.prepare()
    self.assertFalse(self._tx(self.command(enabled=False, rate=0.000001, curvature=0.0, angle=0.0)))

  def test_modern_jerk_rejects_original_rate_counterexample(self):
    self.assertTrue(self.announce())
    self.prepare(speed=15.0, curvature=0.0)
    # Original15m/s lookup permits75CANunits; modernISOjerk permits46.
    self.assertFalse(self._tx(self.command(curvature=0.0015, angle=0.0)))
    self.prepare(speed=15.0, curvature=0.0)
    self.assertTrue(self._tx(self.command(curvature=0.0009, angle=0.0)))

  def test_speed_combined_accel_and_authority_denials(self):
    self.assertTrue(self.announce())
    for speed in (2.9, 8.8):
      self.prepare(speed=speed)
      self.assertFalse(self._tx(self.command()))
    self.prepare()
    self.assertTrue(self._tx(self.command(angle=0.05)))
    self.prepare()
    self.assertTrue(self._tx(self.command(angle=0.1)))
    self.prepare(speed=8.7)
    # 0.0195 * 8.7**2 + 0.12 * 8.7 > 2.5; path delta is only40CAN.
    self.assertFalse(self._tx(self.command(angle=0.12)))
    self.prepare()
    self.safety.set_controls_allowed(False)
    self.assertFalse(self._tx(self.command()))

  def test_rejected_path_does_not_commit_curvature_history(self):
    self.assertTrue(self.announce())
    self.prepare()
    self.assertFalse(self._tx(self.command(curvature=0.0175)))
    self._reset_curvature_measurement(0.0, 5.0)
    self.safety.set_controls_allowed(True)
    # Reset history permits125CAN from zero; a leaked875CAN rejects this step.
    self.assertTrue(self._tx(self.command(curvature=0.0025, angle=0.0)))

  def test_namespace_unknown_words_and_siblings_cannot_acquire(self):
    for word, ae in ((2, 0), (3, 0), (10, 0), (11, 0), (22, 0), (26, 0), (50, 0), (18, 32)):
      with self.subTest(word=word, ae=ae):
        self.safety.set_alternative_experience(ae)
        self.safety.set_safety_hooks(CarParams.SafetyModel.ford, word)
        self.announce()
        self.prepare()
        self.assertFalse(self._tx(self.command()))

  def test_typed_aol_retains_curvature_without_path_angle(self):
    for sign in (-1, 1):
      with self.subTest(sign=sign):
        self.setUp()
        intent = test_ford_aol.TestFordAolDriverIntent()
        intent.setUp()
        intent.reset(self.SAFETY_PARAM)
        intent.arm()
        intent.pump(12, mask=1, speed=7.5, curvature=sign * .02)
        self.assertTrue(self.safety.safety_config_valid())
        self.assertEqual(self.safety.aol_get_permission_mask(), 1)
        self.assertFalse(self.safety.get_controls_allowed())
        self.assertTrue(self.announce())
        self._set_prev_desired_angle(sign * .02)
        self.assertFalse(self._tx(self.command(curvature=sign * .02, angle=sign * .055, increment_timer=False)))
        self._set_prev_desired_angle(sign * .02)
        self.assertTrue(self._tx(self.command(curvature=sign * .02, angle=0., increment_timer=False)))

  def test_accelerator_assist_requires_retained_full_engagement(self):
    for sign in (-1, 1):
      with self.subTest(sign=sign):
        self.setUp()
        intent = test_ford_aol.TestFordAolDriverIntent()
        intent.setUp()
        intent.reset(self.SAFETY_PARAM)
        intent.arm()
        intent.pump(12, mask=1, speed=7.5, curvature=sign * .02)
        self.assertTrue(self.safety.safety_config_valid())
        self.assertEqual(self.safety.aol_get_permission_mask(), 1)
        self._set_prev_desired_angle(sign * .02)
        self._rx(self._pcm_status_msg(True))
        self.assertTrue(self.announce())
        for gas in (0., 25., 0.):
          self._rx(self._user_gas_msg(gas))
          self.assertTrue(self.safety.get_controls_allowed())
          self.assertTrue(self._tx(self.command(curvature=sign * .02, angle=sign * .055, increment_timer=False)))

        # Cruise returning to available revokes full engagement, while typed AOL keeps the lateral axis.
        intent.rx('EngBrakeData', {'BpedDrvAppl_D_Actl': 1, 'CcStat_D_Actl': 3})
        self.assertFalse(self.safety.get_controls_allowed())
        self.assertEqual(self.safety.aol_get_permission_mask(), 1)
        self.assertFalse(self._tx(self.command(curvature=sign * .02, angle=sign * .055, increment_timer=False)))
        self._set_prev_desired_angle(sign * .02)
        self.assertTrue(self._tx(self.command(curvature=sign * .02, angle=0., increment_timer=False)))

        self._rx(self._pcm_status_msg(True))
        self._rx(self._user_brake_msg(True))
        self.assertFalse(self.safety.get_controls_allowed())
        self.assertEqual(self.safety.aol_get_permission_mask(), 1)
        self.assertFalse(self._tx(self.command(curvature=sign * .02, angle=sign * .055, increment_timer=False)))
        self._set_prev_desired_angle(sign * .02)
        self.assertTrue(self._tx(self.command(curvature=sign * .02, angle=0., increment_timer=False)))


class TestFordMachEDebugLongExtended(TestFordMachEExtended):
  SAFETY_PARAM = 19
  REQUIRES_DEBUG = True


class TestFordMachELongReleaseDenied(unittest.TestCase):
  SAFETY_PARAM = 19
  REQUIRES_DEBUG = False

  def setUp(self):
    safety = libsafety_py.libsafety
    debug = safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) == 0
    safety.set_safety_hooks(CarParams.SafetyModel.noOutput, 0)
    safety.set_alternative_experience(0)
    if self.REQUIRES_DEBUG is not None and debug != self.REQUIRES_DEBUG:
      self.skipTest("This case requires " + ("DEBUG" if self.REQUIRES_DEBUG else "RELEASE") + " safety")
    self._message_fixture = ford.TestFordCANFDStockSafety()
    self._message_fixture.SAFETY_PARAM = self.SAFETY_PARAM
    self._message_fixture.setUp()

  def __getattr__(self, name):
    fixture = self.__dict__.get("_message_fixture")
    if fixture is None:
      raise AttributeError(name)
    return getattr(fixture, name)

  def test_long_profile_no_transmit_authority_in_release(self):
    self.safety.set_controls_allowed(True)
    self.assertFalse(self._tx(self._lat_ctl_msg(True, 0.0, 0.0, 0.0, 0.0)))
