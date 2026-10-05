"""Gateway Volt longitudinal transitions, cadence and wire compatibility."""

import unittest
from dataclasses import dataclass
from types import SimpleNamespace

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR, DBC, GMSafetyFlags


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
