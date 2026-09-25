"""Actual classic-Bosch Honda CP/controller frames against the AOL safety hooks."""

import unittest
from types import SimpleNamespace

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.honda.carcontroller import CarController
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, CarControllerParams, HondaSafetyFlags
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests.test_honda import Btn
from openpilot.starpilot.car.honda.aol import CLASSIC_BOSCH_AOL_CARS, qualified_honda
from openpilot.starpilot.aol.runtime import decide_axes


def _frames(candidate, cp, *, lat: bool, long: bool):
  cc = structs.CarControl()
  cc.enabled = lat or long
  cc.latActive = lat
  cc.longActive = long
  cc.actuators.torque = 0.01
  cc.actuators.accel = 1.0
  state = SimpleNamespace(out=structs.CarState(), v_cruise_factor=1.0, is_metric=True, acc_hud={}, lkas_hud={})
  state.out.vEgo = 20.0
  state.out.cruiseState.available = True
  controller = CarController(candidate.config.dbc_dict, cp)
  _, sent = controller.update(cc.as_reader(), state, 0)
  return {msg[0]: msg for msg in sent if isinstance(msg, tuple)}


def _packet(frame):
  address, data, bus = frame
  return libsafety_py.make_CANPacket(address, bus, data)


class TestHondaAolFamily(unittest.TestCase):
  def test_real_controller_frames_obey_native_four_axis_masks(self):
    if libsafety_py.libsafety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0:
      self.skipTest('Independent AOL axes require ALLOW_DEBUG firmware')
    from opendbc.safety.tests.test_honda import TestHondaBoschLongSafety
    gas_lookup = list(CarControllerParams.BOSCH_GAS_LOOKUP_V)
    try:
      for candidate in sorted(CLASSIC_BOSCH_AOL_CARS, key=str):
        for detected_alt in ((False, True) if candidate == CAR.HONDA_ACCORD else (False,)):
          with self.subTest(candidate=candidate, detected_alt=detected_alt):
            CarControllerParams.BOSCH_GAS_LOOKUP_V = list(gas_lookup)
            fingerprint = gen_empty_fingerprint()
            if detected_alt:
              fingerprint[1][0x1BE] = 3
            cp = CarInterface.get_params(candidate, fingerprint, [], True, False, False)
            self.assertTrue(qualified_honda(cp))
            self.assertEqual(bool(cp.safetyConfigs[0].safetyParam & HondaSafetyFlags.ALT_BRAKE),
                             candidate in (CAR.HONDA_CRV_5G, CAR.ACURA_RDX_3G) or detected_alt)

            for mode, lat, long in (("off", False, False), ("lateralOnly", True, False),
                                    ("longitudinalOnly", False, True), ("combined", True, True)):
              with self.subTest(mode=mode):
                native = SimpleNamespace(requestedLateral=lat, requestedLongitudinal=long,
                                         lateralAllowed=lat, longitudinalAllowed=long)
                state = structs.CarState(canValid=True, gearShifter=structs.CarState.GearShifter.drive, vEgo=20.0)
                intent = SimpleNamespace(allowedLatch=lat, pauseLateral=not lat, pauseLongitudinal=not long)
                decision = decide_axes(standard_lateral=False, standard_longitudinal=long, intent=intent,
                                       native=native, car_state=state, initialized=True, model_ready=True,
                                       no_entry=False, immediate_disable=False, dm_lockout=False, pause_brake_mps=5.0)
                self.assertEqual(decision.mode, mode)
                frames = _frames(candidate, cp, lat=decision.lateral_active, long=decision.longitudinal_active)
                self.assertEqual(frames[0xE4][2], 1)
                self.assertEqual(frames[0x1DF][2], 1)

                fixture = TestHondaBoschLongSafety('test_diagnostics')
                fixture.setUp()
                safety = fixture.safety
                safety.set_safety_hooks(structs.CarParams.SafetyModel.hondaBosch,
                                        int(cp.safetyConfigs[0].safetyParam) | int(HondaSafetyFlags.AOL_BOSCH_LONG))
                safety.init_tests()
                safety.set_timer(1_000_000)
                safety.set_aol_test_heartbeat(True)
                fixture._rx(fixture._acc_state_msg(True))
                fixture._rx(fixture._button_msg(Btn.NONE))
                fixture._rx(fixture._speed_msg(20))
                fixture._rx(fixture._powertrain_data_msg())
                if cp.safetyConfigs[0].safetyParam & HondaSafetyFlags.ALT_BRAKE:
                  fixture._rx(fixture._alt_brake_msg(0))
                if long:
                  fixture._rx(fixture._button_msg(Btn.SET))
                  fixture._rx(fixture._button_msg(Btn.NONE))
                  self.assertTrue(safety.get_controls_allowed())
                safety.aol_set_host_request(int(lat) | (int(long) << 1))
                self.assertEqual(safety.aol_get_permission_mask(), int(lat) | (int(long) << 1))
                steer = _packet(frames[0xE4])
                acc = _packet(frames[0x1DF])
                self.assertTrue(safety.safety_tx_hook(steer))
                self.assertTrue(safety.safety_tx_hook(acc))

                active_steer = _frames(candidate, cp, lat=True, long=False)[0xE4]
                active_acc = _frames(candidate, cp, lat=False, long=True)[0x1DF]
                if not lat:
                  self.assertFalse(safety.safety_tx_hook(_packet(active_steer)))
                if not long:
                  self.assertFalse(safety.safety_tx_hook(_packet(active_acc)))
    finally:
      CarControllerParams.BOSCH_GAS_LOOKUP_V = gas_lookup

  def test_native_main_brake_source_and_health_for_both_safety_params(self):
    if libsafety_py.libsafety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0:
      self.skipTest('Independent AOL axes require ALLOW_DEBUG firmware')
    from opendbc.safety.tests.test_honda import TestHondaBoschLongSafety

    for alt_brake in (False, True):
      with self.subTest(alt_brake=alt_brake):
        fixture = TestHondaBoschLongSafety('test_diagnostics')
        fixture.setUp()
        safety = fixture.safety
        safety.set_safety_hooks(structs.CarParams.SafetyModel.hondaBosch,
                                int(HondaSafetyFlags.BOSCH_LONG | HondaSafetyFlags.AOL_BOSCH_LONG |
                                    (HondaSafetyFlags.ALT_BRAKE if alt_brake else 0)))
        safety.init_tests()
        safety.set_timer(1_000_000)
        safety.set_aol_test_heartbeat(True)
        fixture._rx(fixture._acc_state_msg(True))
        fixture._rx(fixture._button_msg(Btn.NONE))
        fixture._rx(fixture._speed_msg(20))
        fixture._rx(fixture._powertrain_data_msg())
        safety.aol_set_host_request(1)
        self.assertEqual(safety.aol_get_permission_mask(), 0 if alt_brake else 1)
        if alt_brake:
          wrong_bus = fixture._alt_brake_msg(0)
          wrong_bus[0].bus = 0
          fixture._rx(wrong_bus)
          self.assertEqual(safety.aol_get_permission_mask(), 0)
          bad_checksum = fixture._alt_brake_msg(0)
          bad_checksum[0].data[2] ^= 1
          self.assertFalse(fixture._rx(bad_checksum))
          self.assertEqual(safety.aol_get_permission_mask(), 0)
          safety.set_safety_hooks(structs.CarParams.SafetyModel.hondaBosch,
                                  int(HondaSafetyFlags.BOSCH_LONG | HondaSafetyFlags.AOL_BOSCH_LONG |
                                      HondaSafetyFlags.ALT_BRAKE))
          safety.init_tests()
          safety.set_timer(1_000_000)
          safety.set_aol_test_heartbeat(True)
          fixture._rx(fixture._acc_state_msg(True))
          fixture._rx(fixture._button_msg(Btn.NONE))
          fixture._rx(fixture._speed_msg(20))
          fixture._rx(fixture._powertrain_data_msg())
          fixture._rx(fixture._alt_brake_msg(0))
          safety.aol_set_host_request(1)
          self.assertEqual(safety.aol_get_permission_mask(), 1)
          fixture._rx(fixture._alt_brake_msg(1))
          self.assertTrue(safety.get_brake_pressed_prev())
          self.assertEqual(safety.aol_get_permission_mask(), 1)  # native lateral permission is separate from brake-paused host intent
          fixture._rx(fixture._alt_brake_msg(0))
          safety.aol_set_host_request(1)
          self.assertEqual(safety.aol_get_permission_mask(), 1)
        safety.set_timer(1_300_001)
        self.assertEqual(safety.aol_get_permission_mask(), 0)
        safety.set_timer(1_400_000)
        fixture._rx(fixture._acc_state_msg(True))
        fixture._rx(fixture._button_msg(Btn.NONE))
        fixture._rx(fixture._speed_msg(20))
        fixture._rx(fixture._powertrain_data_msg())
        if alt_brake:
          fixture._rx(fixture._alt_brake_msg(0))
        safety.aol_set_host_request(1)
        self.assertEqual(safety.aol_get_permission_mask(), 1)
        fixture._rx(fixture._button_msg(Btn.CANCEL))
        self.assertEqual(safety.aol_get_permission_mask(), 0)
        safety.aol_set_host_request(1)
        safety.set_aol_test_heartbeat(False)
        self.assertEqual(safety.aol_get_permission_mask(), 0)
        safety.set_aol_test_heartbeat(True)
        fixture._rx(fixture._acc_state_msg(False))
        safety.aol_set_host_request(1)
        self.assertEqual(safety.aol_get_permission_mask(), 0)


class TestHondaAolFamilyRelease(unittest.TestCase):
  def setUp(self):
    self.gas_lookup = list(CarControllerParams.BOSCH_GAS_LOOKUP_V)
    self.addCleanup(setattr, CarControllerParams, 'BOSCH_GAS_LOOKUP_V', self.gas_lookup)

  def test_release_firmware_never_advertises_family_axis_permission(self):
    safety = libsafety_py.libsafety
    if safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) == 0:
      self.skipTest('Release-only denial contract')
    for candidate in sorted(CLASSIC_BOSCH_AOL_CARS, key=str):
      with self.subTest(candidate=candidate):
        CarControllerParams.BOSCH_GAS_LOOKUP_V = list(self.gas_lookup)
        cp = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], True, False, False)
        self.assertTrue(qualified_honda(cp))
        safety.set_safety_hooks(structs.CarParams.SafetyModel.hondaBosch,
                                int(cp.safetyConfigs[0].safetyParam) | int(HondaSafetyFlags.AOL_BOSCH_LONG))
        safety.init_tests()
        safety.set_aol_test_heartbeat(True)
        safety.aol_set_host_request(3)
        self.assertEqual(safety.aol_get_permission_mask(), 0)
        frames = _frames(candidate, cp, lat=True, long=True)
        self.assertFalse(safety.safety_tx_hook(_packet(frames[0xE4])))
        self.assertFalse(safety.safety_tx_hook(_packet(frames[0x1DF])))
