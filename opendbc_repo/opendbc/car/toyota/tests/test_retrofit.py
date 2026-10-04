import unittest

from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR, ToyotaFlags
from opendbc.car.toyota.fingerprints import FINGERPRINTS


def params(car, fp=None, alpha=False):
  return CarInterface.get_params(car, fp or {0: {}, 1: {}, 2: {}}, [], alpha, False, False)


class TestRetrofit(unittest.TestCase):
  def test_original_stock_contracts(self):
    for car, word, factor, friction in ((CAR.TOYOTA_MATRIX_RETROFIT, 856, 4.05, .10),
                                        (CAR.TOYOTA_PRIUS_RETROFIT, 585, 1.60, .151515)):
      for alpha in (False, True):
        cp = params(car, alpha=alpha)
        self.assertEqual(cp.safetyConfigs[0].safetyParam, word)
        self.assertTrue(cp.pcmCruise)
        self.assertFalse(cp.openpilotLongitudinalControl)
        self.assertFalse(cp.dashcamOnly)
        self.assertFalse(cp.alphaLongitudinalAvailable)
        self.assertAlmostEqual(cp.lateralTuning.torque.latAccelFactor, factor, places=5)
        self.assertAlmostEqual(cp.lateralTuning.torque.friction, friction, places=5)
        self.assertNotIn(car, FINGERPRINTS)  # Explicit rack choice is not an observed automatic fingerprint.
    cp = params(CAR.TOYOTA_PRIUS_RETROFIT)
    self.assertTrue(cp.flags & ToyotaFlags.HYBRID)
    self.assertEqual(cp.minEnableSpeed, -1)
    self.assertEqual(params(CAR.TOYOTA_PRIUS).safetyConfigs[0].safetyParam & 255, 66)

  def test_observed_takeover_requires_paired_port(self):
    for car in (CAR.TOYOTA_MATRIX_RETROFIT, CAR.TOYOTA_PRIUS_RETROFIT):
      for fp in ({0: {0x2FF: 8}, 1: {}, 2: {}},
                 {0: {}, 1: {}, 2: {0x343: 8}}):
        cp = params(car, fp, True)
        self.assertTrue(cp.dashcamOnly)
        self.assertFalse(cp.openpilotLongitudinalControl)
        self.assertFalse(cp.alphaLongitudinalAvailable)
        self.assertEqual(cp.safetyConfigs[0].safetyParam & 255, 88 if car == CAR.TOYOTA_MATRIX_RETROFIT else 73)

  def test_pedal_presence_without_takeover_keeps_original_stock_owner(self):
    for car in (CAR.TOYOTA_MATRIX_RETROFIT, CAR.TOYOTA_PRIUS_RETROFIT):
      cp = params(car, {0: {0x201: 6}, 1: {}, 2: {}}, True)
      self.assertFalse(cp.dashcamOnly)
      self.assertFalse(cp.openpilotLongitudinalControl)
      filter_only = params(car, {0: {0x2AA: 8}, 1: {}, 2: {}}, True)
      self.assertFalse(filter_only.dashcamOnly)
      self.assertFalse(filter_only.openpilotLongitudinalControl)

  def test_retrofit_rack_is_distinct_from_standard_prius(self):
    from opendbc.car.structs import CarParams
    fw = CarParams.CarFw.new_message(ecu=CarParams.Ecu.eps, fwVersion=b'8965B47070\x00\x00\x00\x00\x00\x00')
    fp = {0: {}, 1: {}, 2: {}}
    cp = CarInterface.get_params(CAR.TOYOTA_PRIUS_RETROFIT, fp, [fw], False, False, False)
    self.assertFalse(cp.dashcamOnly)
    self.assertAlmostEqual(cp.steerActuatorDelay, .14, places=5)
    self.assertAlmostEqual(cp.lateralTuning.torque.steeringAngleDeadzoneDeg, .3, places=5)
    normal = CarInterface.get_params(CAR.TOYOTA_PRIUS, fp, [fw], False, False, False)
    self.assertTrue(normal.dashcamOnly)

  def test_actual_native_scale_and_stock_accel_gate(self):
    from opendbc.car.structs import CarParams
    from opendbc.safety.tests.common import CANPackerSafety
    from opendbc.safety.tests.libsafety import libsafety_py
    safety = libsafety_py.libsafety
    for car, scale, dbc in ((CAR.TOYOTA_MATRIX_RETROFIT, 88, 'toyota_new_mc_pt_generated'),
                            (CAR.TOYOTA_PRIUS_RETROFIT, 73, 'toyota_nodsu_pt_generated')):
      cp = params(car)
      packer = CANPackerSafety(dbc)
      safety.set_safety_hooks(CarParams.SafetyModel.toyota, cp.safetyConfigs[0].safetyParam)
      safety.init_tests()
      sensor = packer.make_can_msg_safety('STEER_TORQUE_SENSOR', 0, {'STEER_TORQUE_EPS': 100})
      raw = (sensor.data[5] << 8) | sensor.data[6]
      expected = raw * scale // 100
      for _ in range(6):
        self.assertTrue(safety.safety_rx_hook(sensor))
      self.assertEqual(safety.get_torque_meas_min(), expected - 1)
      self.assertEqual(safety.get_torque_meas_max(), expected + 1)
      safety.set_controls_allowed(True)
      self.assertFalse(safety.safety_tx_hook(packer.make_can_msg_safety('ACC_CONTROL', 0, {'ACCEL_CMD': 1})))

  def test_packed_retrofit_lkas_and_gap_buttons(self):
    from opendbc.can import CANPacker
    from opendbc.car.toyota.carstate import CarState
    from opendbc.car.toyota.values import DBC
    from opendbc.car import Bus, structs
    cp = params(CAR.TOYOTA_PRIUS_RETROFIT)
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    state.update(parsers)  # Real lazy subscriptions, with no first-frame event.
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    now = 1_000_000_000
    frames = [packer.make_can_msg('LKAS_HUD', 2, {'LDA_ON_MESSAGE': 1}),
              packer.make_can_msg('ACC_CONTROL', 0, {'DISTANCE': 1})]
    for parser in parsers.values():
      parser.update([[now, frames]])
    events = state.update(parsers).buttonEvents
    self.assertEqual([(e.type, e.pressed) for e in events],
                     [(structs.CarState.ButtonEvent.Type.lkas, True),
                      (structs.CarState.ButtonEvent.Type.lkas, False),
                      (structs.CarState.ButtonEvent.Type.gapAdjustCruise, True)])
    self.assertEqual(list(state.update(parsers).buttonEvents), [])
    release = [packer.make_can_msg('ACC_CONTROL', 0, {'DISTANCE': 0})]
    parsers[Bus.pt].update([[now + 30_000_000, release]])
    events = state.update(parsers).buttonEvents
    self.assertEqual([(e.type, e.pressed) for e in events],
                     [(structs.CarState.ButtonEvent.Type.gapAdjustCruise, False)])
