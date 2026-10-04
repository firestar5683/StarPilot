"""Base Suburban gateway configuration and CAN ownership contracts."""

import unittest
from types import SimpleNamespace

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR, DBC, CarControllerParams
from opendbc.car.gm.tests.test_volt_grade import command
from opendbc.safety.tests.libsafety import libsafety_py


class TestSuburbanGateway(unittest.TestCase):

  def test_final_configuration(self):
    for alpha in (False, True):
      for release in (False, True):
        fp = gen_empty_fingerprint()
        fp[1][0x460] = 8
        cp = CarInterface.get_params(CAR.CHEVROLET_SUBURBAN, fp, [], alpha, release, False)
        self.assertEqual(cp.safetyConfigs[0].safetyParam, 0)
        self.assertEqual(cp.networkLocation, structs.CarParams.NetworkLocation.gateway)
        self.assertTrue(cp.openpilotLongitudinalControl)
        self.assertFalse(cp.pcmCruise or cp.alphaLongitudinalAvailable or cp.radarUnavailable)
        self.assertEqual(list(cp.longitudinalTuning.kiBP), [5.0, 35.0, 60.0])
        self.assertEqual(list(cp.longitudinalTuning.kiV), [0.5, 0.5, 0.5])
        self.assertAlmostEqual(cp.steerActuatorDelay, 0.2)
        self.assertEqual(CarControllerParams(cp).MAX_GAS, 1018)
        self.assertEqual(DBC[CAR.CHEVROLET_SUBURBAN], DBC[CAR.CHEVROLET_SUBURBAN_ASCM])

  def test_host_longitudinal_output_native_zero_profile(self):
    fp = gen_empty_fingerprint()
    fp[1][0x460] = 8
    cp = CarInterface.get_params(CAR.CHEVROLET_SUBURBAN, fp, [], False, False, False)
    safety = libsafety_py.libsafety
    for active in (False, True):
      for accel in (-4.0, -1.0, 0.0, 1.0, 2.0):
        safety.set_safety_hooks(structs.CarParams.SafetyModel.gm, 0)
        safety.init_tests()
        safety.set_controls_allowed(True)
        controller, messages = command(cp, accel=accel, speed=12.0, orientation=[], active=active)
        addresses = {m[0] for m in messages}
        self.assertTrue({0x2CB, 0x315, 0x370}.issubset(addresses))
        for addr, data, bus in messages:
          self.assertTrue(safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, data)), (active, accel, hex(addr), bus, data.hex()))

  def test_positive_rx_and_controller_steering(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus
    from opendbc.car.gm.carcontroller import CarController
    fp = gen_empty_fingerprint()
    fp[1][0x460] = 8
    cp = CarInterface.get_params(CAR.CHEVROLET_SUBURBAN, fp, [], False, False, False)
    packer = CANPacker(DBC[CAR.CHEVROLET_SUBURBAN][Bus.pt])
    safety = libsafety_py.libsafety
    safety.set_safety_hooks(structs.CarParams.SafetyModel.gm, 0)
    safety.init_tests()
    required = [('PSCMStatus', {}), ('EBCMWheelSpdRear', {'RLWheelSpd': 12, 'RRWheelSpd': 12}),
                ('ASCMSteeringButton', {'ACCButtons': 1}),
                ('ECMAcceleratorPos', {}), ('AcceleratorPedal2', {}), ('ECMEngineStatus', {})]
    for t in range(20):
      safety.set_timer(t * 100_000)
      for name, values in required:
        addr, data, bus = packer.make_can_msg(name, 0, values)
        self.assertTrue(safety.safety_rx_hook(libsafety_py.make_CANPacket(addr, bus, data)))
      safety.safety_tick()
    self.assertTrue(safety.safety_config_valid())
    addr, data, bus = packer.make_can_msg('ASCMSteeringButton', 0, {'ACCButtons': 2})
    safety.safety_rx_hook(libsafety_py.make_CANPacket(addr, bus, data))
    self.assertTrue(safety.get_controls_allowed())
    controller = CarController(DBC[CAR.CHEVROLET_SUBURBAN], cp)
    state = structs.CarState(vEgo=12)
    state.cruiseState.available = True
    cs = SimpleNamespace(out=state.as_reader(), cam_lka_steering_cmd_counter=0, loopback_lka_steering_cmd_updated=False,
                         loopback_lka_steering_cmd_ts_nanos=1_000_000_000, pt_lka_steering_cmd_counter=0)
    seen = 0
    for frame in range(100):
      control = structs.CarControl(enabled=True, latActive=True, longActive=True)
      control.actuators.torque = 0.2 if frame < 50 else -0.2
      _, messages = controller.update(control.as_reader(), cs, 2_000_000_000 + frame * 10_000_000)
      for addr, data, bus in messages:
        self.assertTrue(safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, data)), (frame, hex(addr), bus, data.hex()))
        seen += addr == 0x180
    self.assertGreater(seen, 20)

  def test_pitch_owner_and_invalid_grade(self):
    import math
    from opendbc.car.gm.carcontroller import CarController, suburban_gateway_demands
    fp = gen_empty_fingerprint()
    fp[1][0x460] = 8
    cp = CarInterface.get_params(CAR.CHEVROLET_SUBURBAN, fp, [], False, False, False)
    flat = suburban_gateway_demands(-0.5, 12.0, None, cp)
    for orientation in (None, [], [0.0, float('inf'), 0.0], [0.0, float('nan'), 0.0]):
      self.assertEqual(suburban_gateway_demands(-0.5, 12.0, orientation, cp), flat)
    for pitch in (-0.06, 0.06):
      for accel in (-0.5, 0.5):
        grade = math.sin(pitch) * 9.81
        grade = 0.0 if grade > 0 and accel > 0 else min(grade, 0.2)
        self.assertEqual(suburban_gateway_demands(accel, 12.0, [0.0, pitch, 0.0], cp), suburban_gateway_demands(accel + grade, 12.0, None, cp))
    from unittest.mock import patch
    for enabled in (False, True):
      for orientation in ([], [0.0, -0.06, 0.0], [0.0, 0.06, 0.0], [0.0, float('nan'), 0.0], [0.0, float('inf'), 0.0]):
        controller = CarController(DBC[cp.carFingerprint], cp)
        controller.long_pitch = enabled
        with patch('opendbc.car.gm.tests.test_volt_grade.CarController', return_value=controller):
          actual, _ = command(cp, accel=-0.5, speed=12.0, orientation=orientation)
        expected = suburban_gateway_demands(-0.5, 12.0, orientation if enabled else None, cp)
        self.assertEqual((actual.apply_gas, actual.apply_brake), expected)
