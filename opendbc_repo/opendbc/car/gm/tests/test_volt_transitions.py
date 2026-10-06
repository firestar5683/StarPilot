"""Gateway Volt longitudinal transitions, cadence and wire compatibility."""

import unittest
from dataclasses import dataclass
from types import SimpleNamespace

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR, DBC, GMSafetyFlags


def volt_camera_pedal_params(*, camera=True, be=True, pedal=True, gear=True, release=False, alpha=False):
  fingerprint = gen_empty_fingerprint()
  fingerprint[0].update({0x184: 8, 0x34A: 5, 0x348: 5, 0x1E1: 7, 0x1C4: 8, 0xC9: 8, 0xBD: 7, 0x232: 8})
  fingerprint[0][0xBE if be else 0xF1] = 6
  if pedal:
    fingerprint[0][0x201] = 6
  if gear:
    fingerprint[0][0x1F5] = 8
  if camera:
    fingerprint[2].update({0x320: 6, 0x180: 4, 0x370: 6})
  return CarInterface.get_params(CAR.CHEVROLET_VOLT_CAMERA, fingerprint, [], alpha, release, False)


def volt_gateway_pedal_params(*, camera=True, be=True, pedal=True, gear=True, release=False, alpha=False, radar=True):
  from opendbc.car.gm.radar_interface import RADAR_HEADER_MSG
  fingerprint = gen_empty_fingerprint()
  fingerprint[0].update({0x184: 8, 0x34A: 5, 0x348: 5, 0x1E1: 7, 0x1C4: 8, 0xC9: 8, 0xBD: 7, 0x232: 8})
  fingerprint[0][0xBE if be else 0xF1] = 6
  if pedal:
    fingerprint[0][0x201] = 6
  if gear:
    fingerprint[0][0x1F5] = 8
  if camera:
    fingerprint[2].update({0x320: 6, 0x180: 4, 0x370: 6})
  if radar:
    fingerprint[1][RADAR_HEADER_MSG] = 8
  return CarInterface.get_params(CAR.CHEVROLET_VOLT, fingerprint, [], alpha, release, False)


def volt_ascm_pedal_params(*, be=True, radar=True, sascm=False, alpha=False, release=False, pedal=True, gear=True, be_length=6):
  from opendbc.car.gm.radar_interface import RADAR_HEADER_MSG
  fingerprint = gen_empty_fingerprint()
  fingerprint[0].update({0x184: 8, 0x34A: 5, 0x348: 5, 0x1E1: 7, 0x1C4: 8, 0xC9: 8, 0xBD: 7, 0x232: 8})
  fingerprint[0][0xBE if be else 0xF1] = be_length if be else 6
  if pedal:
    fingerprint[0][0x201] = 6
  if gear:
    fingerprint[0][0x1F5] = 8
  if sascm:
    fingerprint[0][0x2FF] = 8
  fingerprint[2].update({0x320: 6, 0x180: 4, 0x370: 6})
  if radar:
    fingerprint[1][RADAR_HEADER_MSG] = 8
  return CarInterface.get_params(CAR.CHEVROLET_VOLT_ASCM, fingerprint, [], alpha, release, False)


def volt_sdgm_pedal_params(*, be=True, radar=True, sascm=False, alpha=False, release=False, pedal=True, gear=True, be_length=6):
  from opendbc.car.gm.radar_interface import RADAR_HEADER_MSG
  fingerprint = gen_empty_fingerprint()
  fingerprint[0].update({0x184: 8, 0x34A: 5, 0x348: 5, 0x1E1: 7, 0x1C4: 8, 0xC9: 8, 0xBD: 7, 0x232: 8})
  fingerprint[0][0xBE if be else 0xF1] = be_length if be else 6
  if pedal:
    fingerprint[0][0x201] = 6
  if gear:
    fingerprint[0][0x1F5] = 8
  if sascm:
    fingerprint[0][0x2FF] = 8
  fingerprint[2].update({0x320: 6, 0x180: 4, 0x370: 6})
  if radar:
    fingerprint[1][RADAR_HEADER_MSG] = 8
  return CarInterface.get_params(CAR.CHEVROLET_VOLT_2019, fingerprint, [], alpha, release, False)


def volt_cc_pedal_params(*, be=True, radar=True, sascm=False, alpha=False, release=False, pedal=True, gear=True, be_length=6, removed=False):
  from opendbc.car.gm.radar_interface import RADAR_HEADER_MSG
  fingerprint = gen_empty_fingerprint()
  fingerprint[0].update({0x184: 8, 0x34A: 5, 0x348: 5, 0x1E1: 7, 0x1C4: 8, 0xC9: 8, 0xBD: 7, 0x232: 8, 0x3D1: 8})
  fingerprint[0][0xBE if be else 0xF1] = be_length if be else 6
  if pedal:
    fingerprint[0][0x201] = 6
  if gear:
    fingerprint[0][0x1F5] = 8
  if sascm:
    fingerprint[0][0x2FF] = 8
  if not removed:
    fingerprint[2].update({0x320: 6, 0x180: 4})
  if radar:
    fingerprint[1][RADAR_HEADER_MSG] = 8
  return CarInterface.get_params(CAR.CHEVROLET_VOLT_CC, fingerprint, [], alpha, release, False)


@dataclass(frozen=True)
class Phase:
  name: str
  frames: int
  enabled: bool
  active: bool
  speed: float
  accel: float
  state: str
  resume: bool = False
  standstill: bool = False
  gas_pressed: bool = False
  brake_pressed: bool = False
  pitch: float = 0.


PHASES = (
  Phase('disabled', 7, False, False, 12., 1., 'off'),
  Phase('engage', 9, True, True, 12., 1.005, 'pid'),
  Phase('coast', 7, True, True, 12., .04, 'pid'),
  Phase('brake', 9, True, True, 12., -.995, 'pid'),
  Phase('accelerator_override', 7, True, False, 12., 2., 'pid', gas_pressed=True, pitch=-.04),
  Phase('override_release', 9, True, True, 12., 1., 'pid'),
  Phase('graded_decel', 9, True, True, 7., -1.5, 'pid', pitch=-.04),
  Phase('approach_stop', 7, True, True, .6, -2., 'stopping'),
  Phase('near_stop_fixed', 9, True, True, .1, 1., 'stopping'),
  Phase('standstill_hold', 9, True, True, 0., -4., 'stopping', standstill=True),
  Phase('resume_while_stopping', 7, True, True, 0., 1., 'stopping', resume=True, standstill=True),
  Phase('starting_standstill', 9, True, True, 0., .5, 'starting', resume=True, standstill=True),
  Phase('starting_rolling', 7, True, True, .3, .5, 'starting', resume=True),
  Phase('resume_pid', 9, True, True, 2., 2., 'pid'),
  Phase('brake_disengage', 9, False, False, 2., -4., 'off', brake_pressed=True),
  Phase('disengaged_hold', 7, False, False, 0., -4., 'stopping', standstill=True, brake_pressed=True),
  Phase('reengage_hold', 9, True, True, 0., -4., 'stopping', standstill=True),
  Phase('reengage_resume', 7, True, True, .6, 1., 'starting', resume=True, pitch=.04),
)

# Legacy gateway wire fixtures, independent of the current demand mapping and DBC encoder.
# Each row is (gas, brake, counter, gas frame, friction frame).
WIRE = {
  'disabled': (-650, 0, 0, '0042abe001bd5420', '1000f00000'),
  'engage': (1070, 0, 2, '8142e1a000bd1e5e', '1000effe02'),
  'coast': (86, 0, 0, '0142c2e000bd3d20', '1000f00000'),
  'brake': (-650, 1, 2, '8142abe000bd541e', 'afff4fff02'),
  'accelerator_override': (-650, 0, 0, '0142abe000bd5420', '1000f00000'),
  'override_release': (1065, 0, 2, '8142e17800bd1e86', '1000effe02'),
  'graded_decel': (-650, 107, 0, '0142abe000bd5420', 'af95506b00'),
  'approach_stop': (-650, 200, 3, 'c142abe000bd541d', 'af3850c503'),
  'near_stop_fixed': (-650, 150, 0, '0142abe000bd5420', 'af6a509600'),
  'standstill_hold': (-650, 150, 3, 'c162abe0009d541d', 'df6a209303'),
  'resume_while_stopping': (-650, 0, 1, '4162abe0009d541f', '1000efff01'),
  'starting_standstill': (510, 0, 3, 'c162d020009d2fdd', '1000effd03'),
  'starting_rolling': (510, 0, 1, '4142d02000bd2fdf', '1000efff01'),
  'resume_pid': (2041, 0, 3, 'c142fff800bd0005', '1000effd03'),
  'brake_disengage': (-650, 0, 1, '4042abe001bd541f', '1000efff01'),
  'disengaged_hold': (-650, 0, 3, 'c042abe001bd541d', '1000effd03'),
  'reengage_hold': (-650, 150, 1, '4162abe0009d541f', 'df6a209501'),
  'reengage_resume': (1021, 0, 3, 'c142e01800bd1fe5', '1000effd03'),
}


def wire_at_counter(row, counter):
  _, _, old_counter, gas_hex, brake_hex = row
  gas, brake = bytearray.fromhex(gas_hex), bytearray.fromhex(brake_hex)
  gas[0] = (gas[0] & 0x3f) | (counter << 6)
  gas[7] = (gas[7] + old_counter - counter) & 0xff
  brake[4] = (brake[4] & 0xfc) | counter
  checksum = (int.from_bytes(brake[2:4], 'big') + old_counter - counter) & 0xffff
  brake[2:4] = checksum.to_bytes(2, 'big')
  return [(0x2cb, bytes(gas), 0), (0x315, bytes(brake), 2)]


class TestVoltTransitions(unittest.TestCase):
  def test_opt_in_stock_stop_resume_keeps_numeric_and_friction_owners(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus
    from opendbc.car.gm.tests.test_ascm_intercept import params
    from opendbc.car.gm.tests.test_bolt_cc import feed, setup, native
    from opendbc.car.gm.tests.test_volt_camera_control import camera_params
    from opendbc.car.gm.tests.test_volt_camera_removed import removed_params
    from opendbc.car.gm.tests.test_volt_sdgm_control import sdgm_params
    from opendbc.safety.tests.libsafety import libsafety_py
    from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
    from openpilot.starpilot.controller_extensions import configure_controller
    from openpilot.starpilot.longitudinal.tests.test_gm_volt_long_policy import SubMasterFixture
    from unittest.mock import patch
    release = libsafety_py.libsafety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    profiles = [params(CAR.CHEVROLET_VOLT, radar=True, accelerator=source) for source in (False, True)]
    profiles += [params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, accelerator=source, radar=radar)
                 for source in (False, True) for radar in (False, True)]
    profiles += [camera_params(radar=radar) for radar in (False, True)]
    profiles += [removed_params(alternate=source) for source in (False, True)]
    profiles += [sdgm_params(brake_c9=source) for source in (False, True)]
    if release:
      # Only gateway longitudinal profiles are admitted by actual release startup.
      profiles = [cp for cp in profiles if cp.networkLocation == structs.CarParams.NetworkLocation.gateway]
    for cp in profiles:
      with self.subTest(identity=cp.carFingerprint, word=cp.safetyConfigs[0].safetyParam):
        ci, baseline = CarInterface(cp), CarInterface(cp)
        VehicleStartupPreferences(volt_sng=True).configure_controller(ci)
        producer = SubMasterFixture(1_000_000_000)
        producer.update = lambda _: None
        with patch('openpilot.starpilot.controller_extensions.messaging.SubMaster', return_value=producer) as subscribe:
          configure_controller(ci, None)
          configure_controller(baseline, None)
        subscribe.assert_called_once_with(['deviceState', 'carState', 'longitudinalPlan'], frequency=25)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        setup(cp)
        for tick in range(24):
          now = 1_000_000_000 + tick * 40_000_000
          stop, resume = tick < 10 or tick >= 20, 10 <= tick < 15
          _, rx = feed(SimpleNamespace(update=lambda _: None), packer, now, speed=0. if stop or resume else 2., camera=True)
          rx = [m for m in rx if m[0] not in (0xBE, 0x1E1, 0x1A1)]
          rx += [packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': 4 if stop or resume else 2}),
                 packer.make_can_msg('ASCMSteeringButton', 0, {'ACCButtons': 3 if tick == 0 else 1, 'RollingCounter': tick % 4}),
                 packer.make_can_msg('ECMAcceleratorPos', 0, {}),
                 packer.make_can_msg('EBCMBrakePedalPosition', 0, {}),
                 packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCruiseState': 3})]
          for instance in (ci, baseline):
            instance.update([(now - 1_000_000, rx)])
            out = instance.update([(now, rx)])
            self.assertTrue(out.canValid)
            self.assertEqual(out.cruiseState.standstill, stop or resume)
          for message in rx:
            native('rx', message, now // 1000)
          libsafety_py.libsafety.safety_tick()
          if tick == 0:  # Native enters on actual falling SET edge at the next source frame.
            continue
          self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
          cc = structs.CarControl(enabled=True, longActive=True)
          cc.cruiseControl.resume = resume
          cc.cruiseControl.cancel = True  # Actual non-pcm Volt Controls stock-cancel publication.
          cc.actuators.accel = .5 if resume or not stop else -2.
          cc.actuators.longControlState = (structs.CarControl.Actuators.LongControlState.starting if resume else
                                           structs.CarControl.Actuators.LongControlState.stopping if stop else
                                           structs.CarControl.Actuators.LongControlState.pid)
          for instance in (ci, baseline):
            instance.CC.frame = tick * 4
          producer.data['carState'] = ci.CS.out
          producer['longitudinalPlan'].shouldStop = stop and not resume
          for name in ('deviceState', 'carState', 'longitudinalPlan'):
            producer.logMonoTime[name] = now - 1_000_000
            producer.recv_time[name] = (now - 500_000) / 1e9
          with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now)), \
               patch('openpilot.starpilot.controller_extensions.time.monotonic_ns', return_value=now):
            _, actual = ci.apply(cc.as_reader(), now)
          _, expected = baseline.apply(cc.as_reader(), now)
          self.assertEqual([(a,b,d) for a,b,d in actual if a != 0x2CB],
                           [(a,b,d) for a,b,d in expected if a != 0x2CB])
          gas = next(data for address,data,_ in actual if address == 0x2CB)
          gas_default = next(data for address,data,_ in expected if address == 0x2CB)
          self.assertEqual(bool(gas[0] & 1), not resume)
          self.assertEqual(gas[1:4], gas_default[1:4])
          for message in actual:
            self.assertTrue(native('tx', message, now // 1000), message)
        from opendbc.car.gm.longitudinal import volt_sng_release
        cc.cruiseControl.resume = True
        cc.actuators.longControlState = structs.CarControl.Actuators.LongControlState.starting
        # Each exclusion starts from packed, valid stock-STANDSTILL state.
        for name, fields in (('AcceleratorPedal2', {'CruiseState': 4, 'AcceleratorPedal2': 30}),
                             ('ECMEngineStatus', {'CruiseMainOn': 1, 'BrakePressed': 1}),
                             ('EBCMRegenPaddle', {'RegenPaddle': 2}), ('ECMPRDNL2', {'PRNDL2': 3})):
          selected = [m for m in rx if m[0] not in (0x1A1, 0xC9, 0xBD, 0x1F5)]
          selected += [packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': 4}),
                       packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': 1}),
                       packer.make_can_msg('EBCMRegenPaddle', 0, {}),
                       packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 4}), packer.make_can_msg(name, 0, fields)]
          # The selected physical pedal must also match the finalized gateway/ASCM brake source.
          if name == 'ECMEngineStatus':
            selected = [m for m in selected if m[0] not in (0xBE, 0xF1)]
            selected += [packer.make_can_msg('ECMAcceleratorPos', 0, {'BrakePedalPos': 10}),
                         packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': 20})]
          stamp = now + 10_000_000
          ci.update([(stamp, selected)])
          self.assertTrue(ci.CS.out.canValid)
          self.assertTrue(ci.CS.out.cruiseState.standstill)
          self.assertFalse(volt_sng_release(cp, True, cc, ci.CS, stamp, plan_current=True))
        # Re-prime with real packed neutral sources, then independently expire/future-date the observation.
        selected = [m for m in rx if m[0] != 0x1A1] + [packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': 4})]
        stamp = now + 20_000_000
        ci.update([(stamp, selected)])
        self.assertTrue(ci.CS.out.canValid)
        self.assertTrue(volt_sng_release(cp, True, cc, ci.CS, stamp, plan_current=True))
        self.assertFalse(volt_sng_release(cp, True, cc, ci.CS, stamp - 1, plan_current=True))
        self.assertFalse(volt_sng_release(cp, True, cc, ci.CS, stamp + 101_000_000, plan_current=True))
        # Releasing the ACC-state bit never bypasses numeric gas limits or confers brake permission.
        from opendbc.car.gm import gmcan
        for demand, allowed in ((ci.CC.params.MAX_GAS, True), (ci.CC.params.MAX_GAS + .125, False)):
          command = gmcan.create_gas_regen_command(packer, 0, demand, 1, False, False)
          self.assertEqual(bool(native('tx', command, now // 1000)), allowed)
        native('rx', packer.make_can_msg('ASCMSteeringButton', 0, {'ACCButtons': 6}), stamp // 1000)
        self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
        for demand, allowed in ((ci.CC.params.INACTIVE_REGEN, True), (0., False)):
          command = gmcan.create_gas_regen_command(packer, 0, demand, 1, False, False)
          self.assertEqual(bool(native('tx', command, stamp // 1000)), allowed)

  def test_continuous_controller_transitions(self):
    for alpha in (False, True):
      for alignment in range(4):
        with self.subTest(alpha=alpha, alignment=alignment):
          self.check_transitions(alpha, alignment)

  def check_transitions(self, alpha, alignment):
    fingerprint = gen_empty_fingerprint()
    fingerprint[1][0x460] = 8
    fingerprint[0][0xbe] = 8
    cp = CarInterface.get_params(CAR.CHEVROLET_VOLT, fingerprint, [], alpha, False, False)
    self.assertEqual(cp.safetyConfigs[0].safetyParam, GMSafetyFlags.EV | GMSafetyFlags.VOLT_GATEWAY_LONG)
    self.assertTrue(cp.openpilotLongitudinalControl)
    self.assertFalse(cp.pcmCruise or cp.autoResumeSng)
    controller = CarController(DBC[cp.carFingerprint], cp)
    prior = (0, 0)
    counters = []
    phases = (Phase('disabled', alignment, False, False, 12., 0., 'off'), *PHASES)
    for phase in phases:
      for _ in range(phase.frames):
        frame = controller.frame
        now = 1_000_000_000 + frame * 10_000_000
        control = structs.CarControl(enabled=phase.enabled, longActive=phase.active,
                                     orientationNED=[0., phase.pitch, 0.])
        control.cruiseControl.resume = phase.resume
        control.actuators.accel = phase.accel
        control.actuators.longControlState = getattr(structs.CarControl.Actuators.LongControlState, phase.state)
        state = structs.CarState(vEgo=phase.speed, standstill=phase.standstill,
                                 gasPressed=phase.gas_pressed, brakePressed=phase.brake_pressed,
                                 gearShifter=structs.CarState.GearShifter.drive)
        state.cruiseState.available = True
        cs = SimpleNamespace(out=state.as_reader(), cam_lka_steering_cmd_counter=0,
                             loopback_lka_steering_cmd_updated=False, loopback_lka_steering_cmd_ts_nanos=now,
                             pt_lka_steering_cmd_counter=0, pscm_status={})
        actuators, messages = controller.update(control.as_reader(), cs, now)
        actual = [tuple(m) for m in messages if m[0] in (0x2cb, 0x315)]
        self.assertFalse(any(m[0] in (0x200, 0x1e1) for m in messages), (phase.name, frame))
        if frame % 4:
          expected = []
        else:
          row = WIRE[phase.name]
          counter = (frame // 4) % 4
          expected = wire_at_counter(row, counter)
          prior = row[:2]
          counters.append(counter)
        self.assertEqual(actual, expected, (phase.name, frame))
        self.assertEqual((actuators.gas, actuators.brake), prior, (phase.name, frame))
        self.assertEqual((controller.apply_gas, controller.apply_brake), prior)
        self.assertEqual(controller.frame, frame + 1)
    self.assertTrue(all(b == (a + 1) % 4 for a, b in zip(counters, counters[1:], strict=False)))


if __name__ == '__main__':
  unittest.main()


class TestVoltCameraPedalProfiles(unittest.TestCase):
  def test_actual_factory_composes_hold_and_one_pedal_without_losing_interceptor(self):
    from opendbc.car.gm.values import (camera_acc_pedal_profile, apply_gm_auto_hold, apply_volt_one_pedal,
                                      is_gm_auto_hold, is_volt_one_pedal, is_volt_longitudinal)
    from opendbc.car.gm.startup_preferences import prepare_disable_longitudinal
    for camera in (True, False):
      for be in (True, False):
        index = int(not camera) * 2 + int(not be)
        for hold, one, start in ((False, False, 0xE200), (True, False, 0xE220),
                                 (False, True, 0xE240), (True, True, 0xE260)):
          with self.subTest(camera=camera, be=be, hold=hold, one=one):
            cp = volt_camera_pedal_params(camera=camera, be=be)
            self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE200 + index)
            apply_gm_auto_hold(cp, hold)
            apply_volt_one_pedal(cp, one, hold)
            self.assertEqual(cp.safetyConfigs[0].safetyParam, start + index)
            profile = camera_acc_pedal_profile(cp)
            self.assertTrue(profile.volt and profile.longitudinal and is_volt_longitudinal(cp))
            self.assertEqual((profile.auto_hold, profile.one_pedal), (hold, one))
            self.assertEqual(is_volt_one_pedal(cp), one)
            self.assertEqual(is_gm_auto_hold(cp), hold or one)
            prepare_disable_longitudinal(cp, True)
            self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE210 + index)
            self.assertFalse(cp.openpilotLongitudinalControl or cp.autoResumeSng)
            self.assertTrue(cp.pcmCruise)
            apply_gm_auto_hold(cp, True)
            apply_volt_one_pedal(cp, True, True)
            self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE210 + index)
        self.assertEqual(volt_camera_pedal_params(camera=camera, be=be, release=True).safetyConfigs[0].safetyParam,
                         0xE210 + index)
        self.assertEqual(volt_camera_pedal_params(camera=camera, be=be, gear=False).safetyConfigs[0].safetyParam,
                         0xE210 + index)


class TestVoltGatewayPedalProfiles(unittest.TestCase):
  def test_actual_factory_preserves_gateway_tune_and_composed_owners(self):
    from opendbc.car.gm.values import (camera_acc_pedal_profile, apply_gm_auto_hold, apply_volt_one_pedal,
                                      is_gm_auto_hold, is_volt_one_pedal, is_volt_gateway_longitudinal, CarControllerParams)
    from opendbc.car.gm.startup_preferences import prepare_disable_longitudinal
    from opendbc.car.gm.camera import policy_for
    for camera in (True, False):
      for be in (True, False):
        index = int(not camera) * 2 + int(not be)
        for hold, one, start in ((False, False, 0xE300), (True, False, 0xE320),
                                 (False, True, 0xE340), (True, True, 0xE360)):
          with self.subTest(camera=camera, be=be, hold=hold, one=one):
            cp = volt_gateway_pedal_params(camera=camera, be=be)
            self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE300 + index)
            apply_gm_auto_hold(cp, hold)
            apply_volt_one_pedal(cp, one, hold)
            self.assertEqual(cp.safetyConfigs[0].safetyParam, start + index)
            profile = camera_acc_pedal_profile(cp)
            self.assertEqual(profile.topology, "gateway")
            self.assertTrue(is_volt_gateway_longitudinal(cp))
            self.assertEqual(is_gm_auto_hold(cp), hold or one)
            self.assertEqual(is_volt_one_pedal(cp), one)
            self.assertEqual(list(cp.longitudinalTuning.kiBP), [5., 35.])
            self.assertEqual(list(cp.longitudinalTuning.kiV), [.5, .5])
            policy = policy_for(cp)
            self.assertEqual((policy.kp, policy.starting_speed, policy.stopping_decel_rate), (0., .75, 3.))
            self.assertEqual(policy.feedforward(1., 12., 0.), 1.)
            self.assertEqual(CarInterface.get_pid_accel_limits(cp, 0., 0.),
                             (CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX))
            params = CarControllerParams(cp)
            self.assertEqual((params.MAX_GAS, params.INACTIVE_REGEN), (2041., -650.))
            prepare_disable_longitudinal(cp, True)
            self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE310 + index)
            self.assertFalse(cp.openpilotLongitudinalControl or cp.pcmCruise or cp.autoResumeSng)
            apply_gm_auto_hold(cp, True)
            apply_volt_one_pedal(cp, True, True)
            self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE310 + index)
        for options in ({"release": True}, {"gear": False}):
          cp = volt_gateway_pedal_params(camera=camera, be=be, **options)
          self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE310 + index)
        self.assertTrue(volt_gateway_pedal_params(camera=camera, be=be, radar=False).dashcamOnly)

  def test_actual_parser_preserves_final_gateway_brake_sources(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus
    from opendbc.car.gm import gmcan
    from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
    for camera in (True, False):
      for be in (True, False):
        with self.subTest(camera=camera, be=be):
          from opendbc.car.gm.values import apply_gm_auto_hold
          cp = volt_gateway_pedal_params(camera=camera, be=be)
          apply_gm_auto_hold(cp, True)
          ci = CarInterface(cp)
          packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
          for tick in range(64):
            pressed = tick >= 48
            frames = [frame for frame in pt_frames(packer, counter=tick % 4, acc_cruise=2)
                      if frame[0] not in (0xBE, 0xF1, 0xC9)]
            analog = 0 if pressed else 8
            if not be:
              analog = 6 if pressed else 5
            frames += [packer.make_can_msg('ECMEngineStatus', 0,
                       {'CruiseMainOn': 1, 'BrakePressed': pressed if be else not pressed}),
                       packer.make_can_msg('ECMAcceleratorPos' if be else 'EBCMBrakePedalPosition', 0,
                       {'BrakePedalPos': analog} if be else {'BrakePedalPosition': analog}),
                       packer.make_can_msg('EBCMRegenPaddle', 0, {})]
            if camera:
              frames += [packer.make_can_msg('ASCMLKASteeringCmd', 2, {'RollingCounter': tick % 4}),
                         packer.make_can_msg('AEBCmd', 2, {}),
                         packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {})]
            if tick % 2 == 0:
              sensor = bytearray.fromhex('0279012a0000')
              sensor[4] = tick // 2 % 16
              sensor[5] = gmcan.pedal_crc(sensor)
              frames.append((0x201, bytes(sensor), 0))
            state = ci.update([(1_000_000_000 + tick * 10_000_000, frames)])
            if tick >= 40:
              self.assertTrue(state.canValid)
              self.assertTrue(state.cruiseState.available)
              self.assertEqual(state.brakePressed, pressed)
              self.assertAlmostEqual(ci.CS.gm_auto_hold_brake, analog if be else analog / 208, places=6)

  def test_actual_stock_parser_and_cancel_use_fresh_neutral_counter(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus
    from opendbc.car.gm import gmcan
    from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
    from opendbc.car.gm.values import CruiseButtons
    for camera in (True, False):
      for be in (True, False):
        with self.subTest(camera=camera, be=be):
          cp = volt_gateway_pedal_params(camera=camera, be=be, release=True)
          ci = CarInterface(cp)
          packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
          command = structs.CarControl()
          command.cruiseControl.cancel = True
          cancellations = []
          for tick in range(72):
            now = 1_000_000_000 + tick * 10_000_000
            counter = tick % 4 if tick < 52 or tick >= 64 else 3
            frames = [frame for frame in pt_frames(packer, counter=counter, acc_cruise=2 if tick < 64 else 0)
                      if frame[0] not in (0xBE, 0xF1, 0x1E1)]
            frames += [gmcan.create_buttons(packer, 0, counter, CruiseButtons.UNPRESS),
                       packer.make_can_msg('ECMAcceleratorPos' if be else 'EBCMBrakePedalPosition', 0,
                                           {'BrakePedalPos': 0} if be else {'BrakePedalPosition': 0}),
                       packer.make_can_msg('EBCMRegenPaddle', 0, {})]
            if camera:
              frames += [packer.make_can_msg('ASCMLKASteeringCmd', 2, {'RollingCounter': tick % 4}),
                         packer.make_can_msg('AEBCmd', 2, {}),
                         packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {})]
            state = ci.update([(now, frames)])
            _, sends = ci.apply(command.as_reader(), now)
            buttons = [frame for frame in sends if frame[0] == 0x1E1]
            if tick >= 40:
              self.assertTrue(state.canValid)
              self.assertTrue(all(frame[2] == 2 for frame in buttons))
              if tick >= 62:
                self.assertEqual(buttons, [])
              cancellations.extend(buttons)
          self.assertTrue(cancellations)


class TestVoltAscmPedalProfiles(unittest.TestCase):
  def test_stale_physical_source_withdraws_dashboard_while_enabled(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus
    from opendbc.car.gm import gmcan
    from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
    cp = volt_ascm_pedal_params()
    ci = CarInterface(cp)
    ci.CC.camera_pedal_input = SimpleNamespace(update=lambda now: True)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    command = structs.CarControl()
    command.enabled = True
    command.longActive = True
    command.actuators.accel = .2
    dashboards = []
    healthy_dashboards = []
    for tick in range(180):
      now = 1_000_000_000 + tick * 10_000_000
      frames = [frame for frame in pt_frames(packer, counter=tick % 4, acc_cruise=2)
                if frame[0] not in (0xF1, 0x184) or tick < 40]
      frames += [packer.make_can_msg('EBCMRegenPaddle', 0, {}),
                 packer.make_can_msg('ASCMLKASteeringCmd', 2, {'RollingCounter': tick % 4}),
                 packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {})]
      if tick % 2 == 0:
        sensor = bytearray.fromhex('0279012a0000')
        sensor[4] = tick // 2 % 16
        sensor[5] = gmcan.pedal_crc(sensor)
        frames.append((0x201, bytes(sensor), 0))
      ci.update([(now, frames)])
      _, sends = ci.apply(command.as_reader(), now)
      if 32 <= tick < 40:
        healthy_dashboards += [frame for frame in sends if frame[0] == 0x370]
      if tick >= 160:
        dashboards += [frame for frame in sends if frame[0] == 0x370]
    self.assertTrue(healthy_dashboards)
    self.assertTrue(all(frame[1][2] & 0x80 for frame in healthy_dashboards))
    self.assertTrue(command.enabled)
    self.assertTrue(dashboards)
    self.assertTrue(all(not (frame[1][2] & 0x80) for frame in dashboards))

  def test_actual_factory_admits_hardware_without_sascm_and_preserves_tune(self):
    from opendbc.car.gm.values import (camera_acc_pedal_profile, apply_gm_auto_hold, apply_volt_one_pedal,
                                      is_gm_auto_hold, is_volt_one_pedal, is_volt_ascm_longitudinal, CarControllerParams)
    from opendbc.car.gm.startup_preferences import prepare_disable_longitudinal
    from opendbc.car.gm.camera import policy_for
    for be in (True, False):
      for radar in (False, True):
        index = int(radar) * 2 + int(not be)
        for sascm, alpha in ((False, False), (False, True), (True, False), (True, True)):
          for hold, one, start in ((False, False, 0xE400), (True, False, 0xE420),
                                   (False, True, 0xE440), (True, True, 0xE460)):
            with self.subTest(be=be, radar=radar, sascm=sascm, alpha=alpha, hold=hold, one=one):
              cp = volt_ascm_pedal_params(be=be, radar=radar, sascm=sascm, alpha=alpha)
              self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE400 + index)
              self.assertEqual(cp.alphaLongitudinalAvailable, sascm)
              apply_gm_auto_hold(cp, hold)
              apply_volt_one_pedal(cp, one, hold)
              self.assertEqual(cp.safetyConfigs[0].safetyParam, start + index)
              profile = camera_acc_pedal_profile(cp)
              self.assertEqual((profile.topology, profile.radar, profile.removed), ("ascm", radar, False))
              self.assertTrue(is_volt_ascm_longitudinal(cp))
              self.assertEqual(is_gm_auto_hold(cp), hold or one)
              self.assertEqual(is_volt_one_pedal(cp), one)
              self.assertEqual(list(cp.longitudinalTuning.kiBP), [5., 35.])
              self.assertEqual(list(cp.longitudinalTuning.kiV), [.5, .5])
              policy = policy_for(cp)
              self.assertEqual((policy.kp, policy.starting_speed, policy.stopping_decel_rate), (0., .25, 1.))
              self.assertEqual(policy.feedforward(1., 12., 0.), 1.)
              self.assertEqual(CarInterface.get_pid_accel_limits(cp, 0., 0.),
                               (CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX))
              params = CarControllerParams(cp)
              self.assertEqual((params.MAX_GAS, params.INACTIVE_REGEN), (2041., -650.))
              prepare_disable_longitudinal(cp, True)
              self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE410 + index)
              self.assertFalse(cp.openpilotLongitudinalControl or cp.pcmCruise or cp.autoResumeSng)
              apply_gm_auto_hold(cp, True)
              apply_volt_one_pedal(cp, True, True)
              self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE410 + index)
        if be:
          for length in (6, 7, 8):
            self.assertEqual(volt_ascm_pedal_params(radar=radar, be_length=length).safetyConfigs[0].safetyParam,
                             0xE400 + index)
          self.assertTrue(volt_ascm_pedal_params(radar=radar, be_length=5).dashcamOnly)
        for options in ({"release": True}, {"gear": False}):
          cp = volt_ascm_pedal_params(be=be, radar=radar, **options)
          self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE410 + index)


class TestVoltCameraLaunchCurrentSchema(unittest.TestCase):
  def test_actual_parser_launch_preserves_physical_standstill_bypass(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus
    from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
    from opendbc.car.gm import gmcan
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.starpilot.controller_extensions import configure_controller
    with OpenpilotPrefix():
      settings = Params()
      settings.put_bool('OpenpilotEnabledToggle', True, block=True)
      cp = volt_camera_pedal_params(alpha=True)
      ci = CarInterface(cp)
      configure_controller(ci, settings)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      command = structs.CarControl(enabled=True, longActive=True)
      command.cruiseControl.resume = True
      command.actuators.accel = .5
      for tick in range(64):
        now = 1_000_000_000 + tick * 10_000_000
        raw = 200 if tick < 44 else 34 if tick < 50 else 0
        frames = pt_frames(packer, counter=tick % 4, acc_cruise=4)
        frames = [frame for frame in frames if frame[0] not in (0x34A, 0x348)]
        frames += [packer.make_can_msg('EBCMWheelSpdRear', 0, {'RLWheelSpd': raw * .0311, 'RRWheelSpd': raw * .0311}),
                   packer.make_can_msg('EBCMWheelSpdFront', 0, {'FLWheelSpd': (200 if 50 <= tick < 55 else raw) * .0311,
                                                                     'FRWheelSpd': (200 if 50 <= tick < 55 else raw) * .0311}),
                   packer.make_can_msg('EBCMRegenPaddle', 0, {}),
                   packer.make_can_msg('ASCMLKASteeringCmd', 2, {'RollingCounter': tick % 4}),
                   packer.make_can_msg('AEBCmd', 2, {}),
                   packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCruiseState': 4})]
        if tick % 2 == 0:
          sensor = bytearray.fromhex('0279012a0000')
          sensor[4] = tick // 2 % 16
          sensor[5] = gmcan.pedal_crc(sensor)
          frames.append((0x201, bytes(sensor), 0))
        state = ci.update([(now, frames)])
        ci.apply(command.as_reader(), now)
        if tick in (44, 52):
          self.assertTrue(state.canValid)
          self.assertGreater(state.vEgo, .3)
          self.assertEqual(state.standstill, tick == 52)
          self.assertEqual(ci.CC.camera_pedal_launch, tick == 52)


class TestVoltSdgmPedalProfiles(unittest.TestCase):
  def test_actual_parser_uses_be_threshold_and_f1_c9_pressed(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus
    from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
    for be in (True, False):
      cp = volt_sdgm_pedal_params(be=be)
      ci = CarInterface(cp)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      for tick in range(64):
        pressed = tick >= 48
        frames = [frame for frame in pt_frames(packer, counter=tick % 4, acc_cruise=2)
                  if frame[0] not in (0xBE, 0xF1, 0xC9)]
        frames += [packer.make_can_msg('ECMEngineStatus', 0,
                   {'CruiseMainOn': 1, 'BrakePressed': not pressed if be else pressed}),
                   packer.make_can_msg('ECMAcceleratorPos' if be else 'EBCMBrakePedalPosition', 0,
                   {'BrakePedalPos': 8 if pressed else 0} if be else {'BrakePedalPosition': 0 if pressed else 30}),
                   packer.make_can_msg('EBCMRegenPaddle', 0, {}),
                   packer.make_can_msg('ASCMLKASteeringCmd', 2, {'RollingCounter': tick % 4}),
                   packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {})]
        state = ci.update([(1_000_000_000 + tick * 10_000_000, frames)])
        if tick >= 40:
          self.assertEqual(state.brakePressed, pressed)

  def test_actual_factory_preserves_sdgm_topology_and_composition(self):
    from opendbc.car.gm.values import camera_acc_pedal_profile, apply_gm_auto_hold, apply_volt_one_pedal
    from opendbc.car.gm.startup_preferences import prepare_disable_longitudinal
    for be in (True, False):
      for radar in (False, True):
        for sascm in (False, True):
          for alpha in (False, True):
            cp = volt_sdgm_pedal_params(be=be, radar=radar, sascm=sascm, alpha=alpha)
            self.assertEqual(cp.alphaLongitudinalAvailable, sascm)
            self.assertTrue(cp.openpilotLongitudinalControl)
            self.assertFalse(cp.pcmCruise)
            self.assertEqual(cp.radarUnavailable, not radar)
            for hold, one, base in ((False, False, 0xE500), (True, False, 0xE520),
                                    (False, True, 0xE540), (True, True, 0xE560)):
              choice = cp.as_reader().as_builder()
              apply_gm_auto_hold(choice, hold)
              apply_volt_one_pedal(choice, one, hold)
              self.assertEqual(choice.safetyConfigs[0].safetyParam, base + 2 * int(radar) + int(not be))
              self.assertIsNotNone(camera_acc_pedal_profile(choice))
              prepare_disable_longitudinal(choice, True)
              self.assertFalse(choice.openpilotLongitudinalControl)
              self.assertFalse(choice.pcmCruise)
              self.assertEqual(choice.safetyConfigs[0].safetyParam, 0xE510 + 2 * int(radar) + int(not be))

  def test_retention_requires_explicit_auto_hold_owner(self):
    from opendbc.car.gm.values import apply_gm_auto_hold, apply_volt_one_pedal
    from opendbc.car.gm.auto_hold import config_for, stopped_for_hold
    state = SimpleNamespace(standstill=False, vEgo=.2, wheelSpeeds=SimpleNamespace(rl=.2, rr=.2))
    for hold, one in ((True, False), (False, True), (True, True)):
      cp = volt_sdgm_pedal_params()
      apply_gm_auto_hold(cp, hold)
      apply_volt_one_pedal(cp, one, hold)
      config = config_for(cp)
      self.assertEqual(config.minimum_brake, 100)
      self.assertEqual(config.continued_stop_speed, .25 if hold else .02)
      self.assertEqual(stopped_for_hold(state, config, True), hold)
      self.assertFalse(stopped_for_hold(state, config, False))


class TestVoltCcPedalProfiles(unittest.TestCase):
  def test_actual_factory_binds_direct_pedal_owner_and_stock_reduction(self):
    from opendbc.car.gm.values import volt_cc_pedal_profile
    from opendbc.car.gm.startup_preferences import prepare_disable_longitudinal
    for be in (True, False):
      for radar in (False, True):
        for removed in (False, True):
          index = 4 * int(radar) + 2 * int(removed) + int(not be)
          cp = volt_cc_pedal_params(be=be, radar=radar, removed=removed)
          self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE600 + index)
          self.assertIsNotNone(volt_cc_pedal_profile(cp))
          self.assertEqual(cp.radarUnavailable, not radar)
          prepare_disable_longitudinal(cp, True)
          self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE610 + index)
          self.assertFalse(cp.pcmCruise)
          self.assertFalse(cp.openpilotLongitudinalControl)
          self.assertIsNotNone(volt_cc_pedal_profile(cp))

  def test_actual_parser_keeps_cc_engagement_and_pedal_telemetry_distinct(self):
    from itertools import product
    from opendbc.can import CANPacker, CANParser
    from opendbc.car import Bus
    from opendbc.car.gm import gmcan
    from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.starpilot.controller_extensions import configure_controller
    for be, removed, radar, release in product((False, True), repeat=4):
      with self.subTest(be=be, removed=removed, radar=radar, release=release), OpenpilotPrefix():
        params = Params()
        params.put_bool('OpenpilotEnabledToggle', True, block=True)
        cp = volt_cc_pedal_params(be=be, removed=removed, radar=radar, release=release)
        ci = CarInterface(cp)
        configure_controller(ci, params)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        output = CANParser(DBC[cp.carFingerprint][Bus.pt], [('GAS_COMMAND', float('nan'))], 0)
        command = structs.CarControl(enabled=True, longActive=not release)
        command.actuators.accel = .5
        loopback = []
        for tick in range(104):
          now = 1_000_000_000 + tick * 10_000_000
          frames = [frame for frame in pt_frames(packer, counter=tick % 4, acc_cruise=6) if frame[0] not in (0xBE, 0xF1)]
          frames.append(packer.make_can_msg('ECMAcceleratorPos' if be else 'EBCMBrakePedalPosition', 0, {}))
          frames += [packer.make_can_msg('ECMCruiseControl', 0, {'CruiseActive': 1, 'CruiseSetSpeed': 80}),
                     packer.make_can_msg('EBCMRegenPaddle', 0, {})]
          if not removed:
            frames += [packer.make_can_msg('ASCMLKASteeringCmd', 2, {'RollingCounter': tick % 4}),
                       packer.make_can_msg('AEBCmd', 2, {})]
          if not release and tick % 2 == 0:
            sensor = bytearray.fromhex('0279012a0000')
            sensor[4] = tick // 2 % 16
            sensor[5] = gmcan.pedal_crc(sensor)
            frames.append((0x201, bytes(sensor), 0))
          state = ci.update([(now, frames + loopback)])
          actuators, tx = ci.apply(command.as_reader(), now)
          loopback = [(addr, data, 128) for addr, data, _ in tx if addr == 0x180]
          keepalives = [addr for addr, _, _ in tx if addr in (0x409, 0x40A)]
          if release:
            self.assertEqual(keepalives, [])
          if tick == 100:
            self.assertTrue(state.canValid)
            self.assertEqual(keepalives, [0x409, 0x40A] if removed and not release else [])
          if tick == 60:
            self.assertTrue(state.canValid)
            self.assertTrue(state.cruiseState.enabled)
            self.assertAlmostEqual(state.cruiseState.speed, 80 / 3.6, places=4)
            self.assertFalse(state.accFaulted)
            if release:
              self.assertFalse(any(a == 0x200 for a, _, _ in tx))
            else:
              pedal = next(frame for frame in tx if frame[0] == 0x200)
              output.update([(now, [pedal])])
              self.assertGreater(actuators.gas, 0.)
              self.assertEqual(actuators.brake, 0.)
              self.assertAlmostEqual(output.vl['GAS_COMMAND']['GAS_COMMAND'] / 255., actuators.gas, delta=.001)
            if removed:
              self.assertNotIn(0x180, ci.can_parsers[Bus.pt].vl)
              self.assertNotIn(0x180, ci.can_parsers[Bus.cam].vl)
