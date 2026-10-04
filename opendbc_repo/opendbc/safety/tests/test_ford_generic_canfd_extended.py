"""Generic CAN FD extension; helpers composed without inheriting other suites."""
import unittest
from opendbc.car import structs
from opendbc.safety.tests import test_ford as ford
from opendbc.safety.tests.libsafety import libsafety_py


class TestFordGenericCanfdExtended(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.safety.set_alternative_experience(0)
    self.debug = self.safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) == 0
    self.fixture = ford.TestFordCANFDLongitudinalSafety()
    self.fixture.SAFETY_PARAM = 66
    self.fixture.setUp()

  def __getattr__(self, name):
    fixture = self.__dict__.get("fixture")
    if fixture is not None:
      return getattr(fixture, name)
    raise AttributeError(name)

  def tearDown(self):
    self.safety.set_alternative_experience(0)
    self.safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)

  def select(self, word, ae=0):
    self.safety.set_alternative_experience(ae)
    self.safety.set_safety_hooks(structs.CarParams.SafetyModel.ford, word)
    self.safety.init_tests()
    self.safety.set_timer(0)

  def announce(self):
    msg = self._lkas_command_msg(0)
    msg[0].data[4] = 2
    return self._tx(msg)

  def prepare(self, speed=5.):
    # Unit-limit setup only; actual caller packet proof uses physical RX instead.
    self._reset_curvature_measurement(0., speed)
    self._set_prev_desired_angle(0.)
    self.safety.set_controls_allowed(True)

  def test_exact_namespace_and_release_long_denial(self):
    for word in (66,67):
      self.select(word)
      admitted = word == 66 or self.debug
      self.assertEqual(admitted, self.announce())
      self.prepare()
      self.assertEqual(admitted, self._tx(self._lat_ctl_msg(True,0,0,0,.0002)))
      self.assertEqual(word == 67 and self.debug,
        self._tx(self._acc_command_msg(self.INACTIVE_GAS,self.INACTIVE_ACCEL,False)))
    for word, ae in ((64,0),(65,0),(68,0),(70,0),(74,0),(82,0),(98,0),(194,0),(66,33),(67,33)):
      self.select(word,ae)
      self.assertFalse(self.announce())
      self.assertFalse(self._tx(self._lat_ctl_msg(False,0,0,0,0)))
    for word in (66, 67):
      self.select(word, 32)
      self.assertEqual(word == 66 or self.debug, self.announce())
      self.assertFalse(self._tx(self._lat_ctl_msg(True, 0, 0, .0002, 0)))

  def test_announcement_path_and_inactive_contract(self):
    self.prepare()
    self.assertFalse(self._tx(self._lat_ctl_msg(True,0,0,0,.0002)))
    self.assertTrue(self.announce())
    for rate in (-.001024,.001023):
      self.prepare()
      self.assertTrue(self._tx(self._lat_ctl_msg(True,0,0,0,rate)))
    for offset,angle,curvature,rate in ((.01,0,0,0),(0,.01,0,0),(0,0,.001,0),(0,0,0,.0002)):
      self.prepare()
      self.assertTrue(self._tx(self._lat_ctl_msg(True,0,0,.0002,0)))
      self.assertEqual(10,self.safety.get_desired_curvature_last())
      self.assertFalse(self._tx(self._lat_ctl_msg(False,offset,angle,curvature,rate)))
      self.assertEqual(0,self.safety.get_desired_curvature_last())
    self.assertTrue(self._tx(self._lat_ctl_msg(False,0,0,0,0)))

  def test_modern_envelope_and_rejected_history(self):
    self.assertTrue(self.announce())
    for speed,accept,reject in ((15.,40,70),(26.,8,12)):
      self.prepare(speed)
      self.assertTrue(self._tx(self._lat_ctl_msg(True,0,0,accept/self.DEG_TO_CAN,0)))
      self.assertEqual(accept,self.safety.get_desired_curvature_last())
      # Keep the accepted previous command for the extension-only path rejection.
      self.assertFalse(self._tx(self._lat_ctl_msg(True,0,.01,accept/self.DEG_TO_CAN,0)))
      self.assertEqual(0,self.safety.get_desired_curvature_last())
      self.prepare(speed)
      self.assertFalse(self._tx(self._lat_ctl_msg(True,0,0,reject/self.DEG_TO_CAN,0)))
      self.assertEqual(0,self.safety.get_desired_curvature_last())
      self.assertTrue(self._tx(self._lat_ctl_msg(True,0,0,-accept/self.DEG_TO_CAN,0)))
