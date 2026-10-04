from openpilot.starpilot.longitudinal.tests.extension_helpers import extension_state
import unittest
from itertools import product
from types import SimpleNamespace as NS
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_bolt_pedal import params
from opendbc.car.gm.tests import test_bolt_pedal as pedal_fixtures
from opendbc.car.gm.tests.test_bolt_pedal_slew import linear, pedal_step, pedal_wire
from opendbc.car.gm.values import CAR, DBC, PEDAL_BOLT_CAR
from opendbc.car.vehicle_model import VehicleModel
from openpilot.cereal import messaging
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.starpilot.longitudinal.tests.test_gm_pedal_long_policy import state
from openpilot.starpilot.longitudinal.tests.test_gm_volt_cc_policy import fixture, physical_frames

def stopping_step(previous, target, speed, brake=False):
  output = min(previous, 0.) - .008 if previous > -.25 else previous
  if not brake and speed > 1.5 and target < output - .25:
    output = max(target, output - linear(speed, [1.5, 3., 6., 10.], [.02, .03, .05, .07]))
  return output


class TestBoltPedalMovingStop(unittest.TestCase):
  def test_actual_longcontrol_stop_recurrence_and_neighbor_isolation(self):
    for candidate, alpha in product(PEDAL_BOLT_CAR, (False, True)):
      for speed in (0., 1.5, 1.50001, 3., 6., 10.):
        for brake in (False, True):
          cp = params(candidate, True, True, alpha)
          long = LongControl(cp)
          cs = state(speed)
          cs.brakePressed = brake
          expected = 0.
          for _ in range(40):
            expected = stopping_step(expected, -2., speed, brake)
            self.assertAlmostEqual(long.update(True, cs, -2., True, (-4., 2.)), expected, places=10)
            self.assertEqual(long.long_control_state, structs.CarControl.Actuators.LongControlState.stopping)
          self.assertEqual(long.update(False, cs, 0., False, (-4., 2.)), 0.)
          self.assertEqual(long.long_control_state, structs.CarControl.Actuators.LongControlState.off)
          neighbor = LongControl(params(candidate, False, False, alpha))
          self.assertFalse(hasattr(extension_state(neighbor, 'vehicle_policy'), 'stopping_output'))

  def test_target_gap_and_clipping_boundary_through_longcontrol(self):
    for candidate, alpha, target in product(PEDAL_BOLT_CAR, (False, True), (-.257999, -.258, -.258001, -4.)):
      long = LongControl(params(candidate, True, True, alpha))
      self.assertAlmostEqual(long.update(True, state(6.), target, True, (-4., 2.)),
                             stopping_step(0., target, 6.), places=12)

  def test_real_parser_controls_card_wire_stop_release_and_disable(self):
    for candidate, alpha in product(PEDAL_BOLT_CAR, (False, True)):
      for speed in (0., 6.):
        controls, card, _, _, sent, base, _ = fixture(alpha)
        cp = params(candidate, True, True, alpha)
        ci = CarInterface(cp)
        controls.CP, controls.CI = cp, ci
        controls.LoC, controls.VM = LongControl(cp), VehicleModel(cp)
        controls.longitudinal_inputs.gm_cc_enabled = False
        controls.longitudinal_inputs.gm_start_enabled = candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL
        controls.longitudinal_inputs.gm_boot_offset_ns, controls.longitudinal_inputs.gm_source_floor_ns = 0, base - 500_000_000
        controls.longitudinal_inputs.gm_profile_host = controls.longitudinal_inputs.gm_traffic_state = None
        log = messaging.new_message('controlsState').controlsState.lateralControlState.init('torqueState')
        controls.LaC = NS(reset=lambda: None, update=lambda *args, log=log: (0., 0., log))
        card.CP, card.CI, card.volt_cc_selected = cp, ci, False
        packer = CANPacker(DBC[candidate][Bus.pt])
        for warm in (2, 1):
          warm_frames = physical_frames(packer, speed=speed, gear=6)
          warm_frames.append(pedal_fixtures.TestBoltPedalMessages.sensor(packer, 0., 16 - warm))
          warm_frames += [packer.make_can_msg(name, 2, {}) for name in ('ASCMLKASteeringCmd', 'AEBCmd', 'ASCMActiveCruiseControlStatus')]
          ci.update([(base - warm * 10_000_000, warm_frames)])
        expected, steady, prior = 0., None, structs.CarControl.Actuators.LongControlState.off
        cancel_seen = False
        for tick in range(25):
          now = base + tick * 10_000_000
          frames = physical_frames(packer, speed=speed, gear=6, counter=tick % 4)
          frames.append(pedal_fixtures.TestBoltPedalMessages.sensor(packer, 30. if tick == 20 else 0., tick % 16))
          stock_held = candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL and tick < 6
          acc_status = packer.make_can_msg("AcceleratorPedal2", 0, {"CruiseState": int(stock_held)})
          frames = [m for m in frames if m[0] != acc_status[0]] + [acc_status]
          engine = packer.make_can_msg("ECMEngineStatus", 0, {"CruiseMainOn": 1, "BrakePressed": int(tick == 24)})
          frames = [m for m in frames if m[0] != engine[0]] + [engine]
          frames += [packer.make_can_msg(name, 2, {}) for name in ('ASCMLKASteeringCmd', 'AEBCmd', 'ASCMActiveCruiseControlStatus')]
          out = ci.update([(now - 2_000_000, frames)])
          self.assertTrue(out.canValid)
          self.assertTrue(ci.CS.pedal_sensor_healthy)
          controls.sm.data['carState'] = out
          plan = controls.sm['longitudinalPlan']
          plan.aTarget, plan.shouldStop = (-2., True) if tick < 12 else (.5, False)
          controls.sm['selfdriveState'].enabled = tick != 16
          for name in controls.sm.logMonoTime:
            controls.sm.logMonoTime[name] = now - 2_000_000
            controls.sm.recv_time[name] = (now - 1_000_000) / 1e9
          with patch('openpilot.selfdrive.car.card.REPLAY', False), \
               patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now)), \
               patch('openpilot.selfdrive.car.card.time.monotonic', return_value=now / 1e9):
            if controls.longitudinal_inputs.gm_start_enabled:
              self.assertIsNotNone(controls.longitudinal_inputs._gm_start_evidence())
            cc, lateral = controls.state_control()
            controls.publish(cc, lateral)
            controls.sm.data['carControl'] = cc
            for mapping in (controls.sm.seen, controls.sm.alive, controls.sm.valid):
              mapping['carControl'] = True
            controls.sm.logMonoTime['carControl'] = now - 2_000_000
            controls.sm.recv_time['carControl'] = (now - 1_000_000) / 1e9
            card.controls_update(out, cc.as_reader())
          cancel_seen |= any(m[0] == 0x1e1 and m[2] == 2 for m in sent[-1][0])
          self.assertEqual(cc.actuators.longControlState, controls.LoC.long_control_state if controls.longitudinal_inputs.gm_start_enabled else prior)
          prior = controls.LoC.long_control_state
          if tick < 12:
            expected = stopping_step(expected, -2., out.vEgo)
            self.assertAlmostEqual(cc.actuators.accel, expected, places=6)
          elif tick == 16:
            self.assertEqual(cc.actuators.accel, 0.)
            self.assertEqual(prior, structs.CarControl.Actuators.LongControlState.off)
          elif tick < 16:
            self.assertNotEqual(prior, structs.CarControl.Actuators.LongControlState.stopping)
          if tick in (0, 4, 8, 12):
            accel = cc.actuators.accel
            shaped_accel = 0. if abs(accel) < .04 else accel
            offset = linear(out.vEgo, [0, 1, 3, 6, 15, 30], [.085, .11, .17, .23, .235, .23])
            gain = linear(out.vEgo, [0, 3, 8, 20], [.47, .52, .57, .61])
            scale = linear(abs(shaped_accel), [0, .35, .8, 1.5, 2.5], [.44, .54, .70, .89, 1.] if accel < 0 else [.58, .68, .82, .93, 1.])
            ceiling = linear(out.vEgo, [0, 1, 2.5, 4.5, 6, 8, 12], [.2, .235, .29, .365, .52, .78, 1.])
            target = max(0., min(ceiling, offset + shaped_accel * scale * gain))
            if stock_held:
              steady = None
              self.assertEqual(next(m[1] for m in sent[-1][0] if m[0] == 0x200), pedal_wire(0., tick // 4))
              self.assertFalse(any(m[0] == 0x315 for m in sent[-1][0]))
              continue
            if candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
              self.assertTrue(any(m[0] == 0x315 for m in sent[-1][0]))
            steady = target if steady is None else pedal_step(target, steady, accel, out.vEgo)
            self.assertFalse(ci.CC.regen_paddle_pressed)
            self.assertEqual(next(m[1] for m in sent[-1][0] if m[0] == 0x200), pedal_wire(steady, tick // 4))
          if tick == 20:
            self.assertTrue(out.gasPressed)
          if tick == 24:
            self.assertTrue(out.brakePressed)
          if tick in (16, 20, 24):
            self.assertEqual(next(m[1][:4] for m in sent[-1][0] if m[0] == 0x200), b'\x00' * 4)

        if candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
          self.assertTrue(cancel_seen)
