"""Observed Volt ASCM topology: final admission, continuous commands and legacy isolation."""
import unittest
from types import SimpleNamespace

from opendbc.car import structs
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.longitudinal import volt_policy_for
from opendbc.car.gm.profiles import profiles_supported
from opendbc.car.gm.tests.test_ascm_intercept import params
from opendbc.car.gm.tests.test_volt_transitions import wire_at_counter
from opendbc.car.gm.values import CAR, DBC, GMSafetyFlags, is_volt_ascm_longitudinal


# Original Volt ASCM wire values, including its .25 m/s stop transition.
# Phase fields: name, frames, enabled, long-active, speed, acceleration,
# state, resume, standstill, gas-pressed, brake-pressed, pitch.
PHASES = (('disabled', 7, False, False, 12.0, 1.0, 'off', False, False, False, False, 0.0),
 ('positive', 9, True, True, 12.0, 1.005, 'pid', False, False, False, False, 0.0),
 ('coast', 7, True, True, 12.0, 0.0, 'pid', False, False, False, False, 0.0),
 ('regen', 9, True, True, 12.0, -0.5, 'pid', False, False, False, False, 0.0),
 ('friction', 7, True, True, 12.0, -2.0, 'pid', False, False, False, False, 0.0),
 ('accelerator_override', 9, True, False, 12.0, 2.0, 'pid', False, False, True, False, -0.04),
 ('override_release', 7, True, True, 12.0, 1.0, 'pid', False, False, False, False, 0.0),
 ('graded_decel', 9, True, True, 7.0, -1.5, 'pid', False, False, False, False, -0.04),
 ('stop_above_threshold', 7, True, True, 0.6, -2.0, 'stopping', False, False, False, False, 0.0),
 ('stop_mid_threshold', 9, True, True, 0.3, -2.0, 'stopping', False, False, False, False, 0.0),
 ('near_stop_fixed', 7, True, True, 0.1, 1.0, 'stopping', False, False, False, False, 0.0),
 ('standstill_hold', 9, True, True, 0.0, -4.0, 'stopping', False, True, False, False, 0.0),
 ('resume_while_stopping', 7, True, True, 0.0, 1.0, 'stopping', True, True, False, False, 0.0),
 ('starting_standstill', 9, True, True, 0.0, 0.5, 'starting', True, True, False, False, 0.0),
 ('starting_rolling', 7, True, True, 0.3, 0.5, 'starting', True, False, False, False, 0.0),
 ('resume_pid', 9, True, True, 2.0, 2.0, 'pid', False, False, False, False, 0.0),
 ('brake_disengage', 7, False, False, 2.0, -4.0, 'off', False, False, False, True, 0.0),
 ('disengaged_hold', 9, False, False, 0.0, -4.0, 'stopping', False, True, False, True, 0.0))
WIRE = {'disabled': (-650, 0, 0, '0042abe001bd5420', '1000f00000'),
 'positive': (1070, 0, 2, '8142e1a000bd1e5e', '1000effe02'),
 'coast': (45, 0, 0, '0142c19800bd3e68', '1000f00000'),
 'regen': (-314, 0, 2, '8142b66000bd499e', '1000effe02'),
 'friction': (-650, 132, 0, '0142abe000bd5420', 'af7c508400'),
 'accelerator_override': (-650, 0, 2, '8142abe000bd541e', '1000effe02'),
 'override_release': (1065, 0, 0, '0142e17800bd1e88', '1000f00000'),
 'graded_decel': (-650, 107, 2, '8142abe000bd541e', 'af95506902'),
 'stop_above_threshold': (-650, 200, 0, '0142abe000bd5420', 'af3850c800'),
 'stop_mid_threshold': (-650, 200, 2, '8142abe000bd541e', 'af3850c602'),
 'near_stop_fixed': (-650, 25, 0, '0142abe000bd5420', 'afe7501900'),
 'standstill_hold': (-650, 25, 2, '8162abe0009d541e', 'dfe7201702'),
 'resume_while_stopping': (-650, 0, 0, '0162abe0009d5420', '1000f00000'),
 'starting_standstill': (510, 0, 2, '8142d02000bd2fde', '1000effe02'),
 'starting_rolling': (510, 0, 0, '0142d02000bd2fe0', '1000f00000'),
 'resume_pid': (2041, 0, 2, '8142fff800bd0006', '1000effe02'),
 'brake_disengage': (-650, 0, 0, '0042abe001bd5420', '1000f00000'),
 'disengaged_hold': (-650, 0, 2, '8042abe001bd541e', '1000effe02')}


class TestVoltAscmControl(unittest.TestCase):
  def test_actual_ascm_camera_dashboard_source_and_sender(self):
    from opendbc.can import CANPacker
    from opendbc.can.parser import CANParser
    from opendbc.car import Bus
    from opendbc.car.gm.carstate import CarState
    from opendbc.car.gm.values import gm_control_word

    cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, accelerator=True, radar=True)
    cp.safetyConfigs[0].safetyParam = 0xD114
    cp.alternativeExperience = 32
    self.assertTrue(is_volt_ascm_longitudinal(cp))
    self.assertEqual(gm_control_word(cp), 0x4A87)
    for enabled in (False, True):
      for stock_level, aeb, local_fcw in ((0, False, False), (1, False, False), (2, False, False),
                                         (3, False, False), (0, True, False), (2, True, False),
                                         (0, False, True), (1, False, True)):
        with self.subTest(enabled=enabled, stock_level=stock_level, aeb=aeb, local_fcw=local_fcw):
          state = CarState(cp)
          parsers = state.get_can_parsers(cp)
          packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
          camera = [packer.make_can_msg('ASCMLKASteeringCmd', 2, {}),
                    packer.make_can_msg('ASCMActiveCruiseControlStatus', 2,
                                       {'ACCCruiseState': 2, 'FCWAlert': stock_level}),
                    packer.make_can_msg('AEBCmd', 2, {'AEBCmdActive': int(aeb)})]
          parsers[Bus.cam].update([(1_000_000_000, camera)])
          out = state.update(parsers)
          self.assertEqual(state.stock_fcw_alert, stock_level)
          self.assertEqual(out.stockFcw, stock_level != 0)
          self.assertEqual(out.stockAeb, aeb)
          state.out = out.as_reader()
          control = structs.CarControl(enabled=enabled, longActive=enabled)
          control.hudControl.setSpeed = 20.
          control.hudControl.leadDistanceBars = 3
          control.hudControl.leadVisible = True
          control.hudControl.visualAlert = (structs.CarControl.HUDControl.VisualAlert.fcw if local_fcw else
                                           structs.CarControl.HUDControl.VisualAlert.none)
          controller = CarController(DBC[cp.carFingerprint], cp)
          decoder = CANParser(DBC[cp.carFingerprint][Bus.pt], [('ASCMActiveCruiseControlStatus', 25)], 0)
          sent = []
          for index in range(8):
            now = 1_000_000_000 + index * 10_000_000
            _, frames = controller.update(control.as_reader(), state, now)
            status = [msg for msg in frames if msg[0] == 0x370]
            self.assertEqual(len(status), int(index % 4 == 0), index)
            for message in status:
              self.assertEqual(message[2], 0)
              sent.append(bytes(message[1]))
              decoder.update([(now, [message])])
              decoded = decoder.vl['ASCMActiveCruiseControlStatus']
              self.assertEqual(decoded['ACCCruiseState'], 2)
              self.assertEqual(decoded['ACCCmdActive'], enabled)
              self.assertEqual(decoded['ACCAlwaysOne'], 1)
              self.assertEqual(decoded['ACCAlwaysOne2'], 1)
              self.assertEqual(decoded['ACCGapLevel'], 3 * enabled)
              self.assertEqual(decoded['FCWAlert'], 3 if local_fcw else stock_level or (3 if aeb else 0))
          self.assertEqual(len(sent), 2)

  def test_dashboard_stock_ascm_and_generic_sender_isolation(self):
    from opendbc.car.gm.carstate import CarState

    for candidate, alpha, expected in ((CAR.CHEVROLET_VOLT_ASCM, False, None),
                                      (CAR.GMC_ACADIA, True, bytes.fromhex('010000000110'))):
      cp = params(candidate, sascm=True, alpha=alpha, accelerator=True, radar=True)
      state = CarState(cp)
      state.out = state.update(state.get_can_parsers(cp)).as_reader()
      controller = CarController(DBC[cp.carFingerprint], cp)
      control = structs.CarControl(enabled=False, longActive=False)
      control.hudControl.leadVisible = True
      status = []
      for index in range(8):
        _, frames = controller.update(control.as_reader(), state, 1_000_000_000 + index * 10_000_000)
        status.extend(msg for msg in frames if msg[0] == 0x370)
      if expected is None:
        self.assertFalse(status)
      else:
        self.assertEqual(len(status), 2)
        self.assertTrue(all(msg[2] == 0 and bytes(msg[1]) == expected for msg in status))

  def test_exact_observed_admission_and_legacy_isolation(self):
    for alpha in (False, True):
      for brake_c9 in (False, True):
        for radar in (False, True):
          cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=alpha, accelerator=not brake_c9, radar=radar)
          self.assertEqual(is_volt_ascm_longitudinal(cp), alpha)
          self.assertEqual(volt_policy_for(cp) is not None, alpha)
          self.assertEqual(profiles_supported(cp), alpha)
          expected = int(GMSafetyFlags.EV | GMSafetyFlags.HW_CAM | GMSafetyFlags.ASCM_INTERCEPT)
          if alpha:
            expected |= int(GMSafetyFlags.HW_CAM_LONG | GMSafetyFlags.VOLT_LONG)
          if brake_c9:
            expected |= int(GMSafetyFlags.ASCM_BRAKE_C9)
          if radar:
            expected |= int(GMSafetyFlags.ASCM_RADAR)
          self.assertEqual(cp.safetyConfigs[0].safetyParam, expected)
          if alpha:
            for field, value in (('alphaLongitudinalAvailable', False), ('passive', True), ('dashcamOnly', True),
                                 ('pcmCruise', True), ('flags', 2), ('radarUnavailable', radar)):
              bad = cp.as_reader().as_builder()
              setattr(bad, field, value)
              self.assertFalse(is_volt_ascm_longitudinal(bad), field)
              self.assertIsNone(volt_policy_for(bad), field)
            for bit in (GMSafetyFlags.VOLT_GATEWAY_ALT_BRAKE, GMSafetyFlags.PEDAL_LONG, GMSafetyFlags.SDGM):
              bad = cp.as_reader().as_builder()
              bad.safetyConfigs[0].safetyParam |= int(bit)
              self.assertFalse(is_volt_ascm_longitudinal(bad))
            legacy = cp.as_reader().as_builder()
            legacy.safetyConfigs[0].safetyParam &= ~int(GMSafetyFlags.VOLT_LONG)
            self.assertIsNone(volt_policy_for(legacy))
            self.assertFalse(profiles_supported(legacy))
            self.assertEqual(CarController(DBC[legacy.carFingerprint], legacy).params.MAX_GAS, 1346.)
    for sascm, release in ((False, False), (True, True)):
      cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=sascm, alpha=True, release=release)
      self.assertFalse(cp.openpilotLongitudinalControl)
      self.assertFalse(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.VOLT_LONG)
      self.assertIsNone(volt_policy_for(cp))

  def test_continuous_original_frames_and_routing(self):
    for alpha in (False, True):
      for brake_c9 in (False, True):
        for radar in (False, True):
          for alignment in range(4):
            cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=alpha, accelerator=not brake_c9, radar=radar)
            controller = CarController(DBC[cp.carFingerprint], cp)
            controller.frame = alignment
            for phase, length, enabled, active, speed, accel, state, resume, still, gas_pressed, brake_pressed, pitch in PHASES:
              for _ in range(length):
                frame = controller.frame
                now = 1_000_000_000 + frame * 10_000_000
                control = structs.CarControl(enabled=enabled, longActive=alpha and active, orientationNED=[0., pitch, 0.])
                control.cruiseControl.resume = resume
                control.actuators.accel = accel
                control.actuators.longControlState = getattr(structs.CarControl.Actuators.LongControlState, state)
                car = structs.CarState(vEgo=speed, standstill=still, gasPressed=gas_pressed, brakePressed=brake_pressed)
                car.cruiseState.available = True
                car.cruiseState.enabled = enabled and not alpha
                car.gearShifter = structs.CarState.GearShifter.drive
                cs = SimpleNamespace(out=car.as_reader(), stock_fcw_alert=0, cam_lka_steering_cmd_counter=0,
                                     loopback_lka_steering_cmd_updated=False, loopback_lka_steering_cmd_ts_nanos=now,
                                     pt_lka_steering_cmd_counter=0, buttons_counter=0,
                                     pscm_status=dict.fromkeys(('HandsOffSWDetectionMode', 'HandsOffSWlDetectionStatus', 'LKATorqueDeliveredStatus',
                                        'LKADriverAppldTrq', 'LKATorqueDelivered', 'LKATotalTorqueDelivered', 'RollingCounter', 'PSCMStatusChecksum'), 0))
                _, frames = controller.update(control.as_reader(), cs, now)
                actual = [tuple(msg) for msg in frames if msg[0] in (0x2cb, 0x315)]
                self.assertFalse(any(msg[2] == 1 for msg in frames))
                self.assertFalse(any(msg[0] in (0x200, 0x1f5) for msg in frames))
                if not alpha or frame % 4:
                  self.assertFalse(actual)
                  continue
                expected = [(address, payload, 0) for address, payload, _ in wire_at_counter(WIRE[phase], (frame // 4) % 4)]
                self.assertEqual(actual, expected, (alpha, brake_c9, radar, alignment, phase, frame))
                self.assertEqual((controller.apply_gas, controller.apply_brake), WIRE[phase][:2])
