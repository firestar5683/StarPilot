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
