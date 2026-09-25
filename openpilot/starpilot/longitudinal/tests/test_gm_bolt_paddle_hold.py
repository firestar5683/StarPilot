import unittest
from dataclasses import dataclass
from itertools import product
from types import SimpleNamespace as NS
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests import test_bolt_pedal as pedal_fixtures
from opendbc.car.gm.tests.test_bolt_pedal_slew import linear, pedal_wire, pedal_step
from opendbc.car.gm.values import CAR, DBC, PEDAL_BOLT_CAR
from opendbc.car.vehicle_model import VehicleModel
from openpilot.cereal import messaging
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.starpilot.longitudinal.tests.test_gm_volt_cc_policy import fixture, physical_frames


@dataclass
class PaddleLaw:
  hold: bool = False
  pressed: bool = False
  press_count: int = 0
  release_count: int = 0
  min_on: int = 0
  min_off: int = 0

  def update_hold(self, accel, speed, active):
    if not active:
      self.hold = False
    elif accel <= linear(speed, [0, 4, 12, 25], [-.95, -.82, -.70, -.62]):
      self.hold = True
    elif accel >= linear(speed, [0, 4, 12, 25], [-.14, -.22, -.30, -.36]):
      self.hold = False

  def update_paddle(self, accel, measured, speed, active):
    if not active:
      self.hold = self.pressed = False
      self.press_count = self.release_count = self.min_on = self.min_off = 0
      return
    bp = [0, 4, 12, 25]
    press_cmd = linear(speed, bp, [-.90, -.82, -.72, -.65])
    release_cmd = linear(speed, bp, [-.10, -.17, -.24, -.30])
    press_measured = linear(speed, bp, [-.95, -.86, -.76, -.70])
    release_measured = linear(speed, bp, [-.16, -.23, -.30, -.36])
    boost = round(linear(speed, [0, 6, 8, 20, 25], [0, 0, 3, 3, 0]))
    press_frames = round(linear(speed, bp, [8, 6, 5, 4])) + boost
    release_frames = round(linear(speed, bp, [18, 15, 12, 10])) + boost
    self.press_count = self.press_count + 1 if self.hold or accel <= press_cmd or measured <= press_measured else max(0, self.press_count - 1)
    self.release_count = self.release_count + 1 if not self.hold and accel >= release_cmd and measured >= release_measured else max(0, self.release_count - 1)
    if self.hold and accel <= press_cmd - .30:
      self.press_count = max(self.press_count, press_frames)
    self.min_on, self.min_off = max(0, self.min_on - 1), max(0, self.min_off - 1)
    if self.pressed:
      if self.min_on == 0 and self.release_count >= release_frames:
        self.pressed = False
        self.min_off = round(linear(speed, bp, [16, 14, 12, 10]))
        self.release_count = 0
    elif self.min_off == 0 and self.press_count >= press_frames:
      self.pressed = True
      self.min_on = round(linear(speed, bp, [34, 27, 20, 16]))
      self.press_count = 0


def pedal_target(accel, speed, paddle):
  accel = 0. if abs(accel) < .04 else accel
  gain = linear(speed, [.559, 1.678, 2.797, 3.916, 5.035, 6.154, 7.273, 8.392, 9.511, 10.63,
                        11.749, 12.868, 13.987, 15.106, 16.225, 17.344, 18.463, 19.582, 20.701, 21.820,
                        22.939, 24.058, 25.177, 26.296],
                       [1.01, 1.01, 1.02, 1.05, 1.08, 1.31, 1.33, 1.34, 1.35, 1.36, 1.37, 1.38, 1.39, 1.39,
                        1.40, 1.40, 1.41, 1.42, 1.43, 1.43, 1.44, 1.44, 1.45, 1.45])
  gain *= linear(speed, [0, 2, 4, 5.5, 8, 12], [.92, .92, .93, .94, .96, 1])
  scale = linear(abs(accel), [0, .35, .8, 1.5, 2.5], [.58, .68, .82, .93, 1] if accel >= 0 else [.44, .54, .70, .89, 1])
  command = accel * scale
  if accel < -2:
    command *= linear(abs(accel), [2, 2.5, 3], [1, 1.03, 1.06])
  offset = linear(speed, [0, 1, 3, 6, 15, 30], [.085, .11, .17, .23, .235, .23])
  accel_gain = linear(speed, [0, 3, 8, 20], [.47, .52, .57, .61])
  ceiling = linear(speed, [0, 1, 2.5, 4.5, 6, 8, 12], [.20, .235, .29, .365, .52, .78, 1])
  return max(0., min(ceiling, offset + command * accel_gain / max(gain, .001) if paddle else offset + command * accel_gain))


class TestBoltPaddleHold(unittest.TestCase):
  def test_actual_parsed_controls_card_controller_multirate_and_overrides(self):
    for candidate, alpha, speed in product(PEDAL_BOLT_CAR, (False, True), (2.68, 2.70, 12.)):
      controls, card, _, _, sent, base, _ = fixture(alpha)
      cp = pedal_fixtures.params(candidate, True, True, alpha)
      ci = CarInterface(cp)
      controls.CP, controls.CI, controls.LoC, controls.VM = cp, ci, LongControl(cp), VehicleModel(cp)
      controls.longitudinal_inputs.gm_cc_enabled = False
      controls.longitudinal_inputs.gm_start_enabled = candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL
      controls.longitudinal_inputs.gm_boot_offset_ns, controls.longitudinal_inputs.gm_source_floor_ns = 0, base - 500_000_000
      controls.longitudinal_inputs.gm_profile_host = controls.longitudinal_inputs.gm_traffic_state = None
      log = messaging.new_message('controlsState').controlsState.lateralControlState.init('torqueState')
      controls.LaC = NS(reset=lambda: None, update=lambda *args, log=log: (0., 0., log))
      card.CP, card.CI, card.volt_cc_selected = cp, ci, False
      packer = CANPacker(DBC[candidate][Bus.pt])
      law, steady, previous_active = PaddleLaw(), 0., False
      gen2 = candidate in (CAR.CHEVROLET_BOLT_CC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)
      pressed_seen = False
      for tick in range(-2, 216):
        now = base + tick * 10_000_000
        stock = controls.longitudinal_inputs.gm_start_enabled and 172 <= tick < 180
        gas, brake, regen = 160 <= tick < 164, 164 <= tick < 168, 168 <= tick < 172
        frames = physical_frames(packer, speed=speed, gear=6, counter=tick % 4)
        for name, values in (('AcceleratorPedal2', {'CruiseState': int(stock)}),
                             ('ECMEngineStatus', {'CruiseMainOn': 1, 'BrakePressed': int(brake)}),
                             ('EBCMRegenPaddle', {'RegenPaddle': 2 if regen else 0})):
          msg = packer.make_can_msg(name, 0, values)
          frames = [m for m in frames if m[0] != msg[0]] + [msg]
        if not 188 <= tick < 200:
          frames.append(pedal_fixtures.TestBoltPedalMessages.sensor(packer, 30. if gas else 0., tick % 16))
        frames += [packer.make_can_msg(name, 2, {}) for name in ('ASCMLKASteeringCmd', 'AEBCmd', 'ASCMActiveCruiseControlStatus')]
        out = ci.update([(now - 2_000_000, frames)])
        if tick < 0:
          continue
        controls.sm.data['carState'] = out
        plan = controls.sm['longitudinalPlan']
        plan.aTarget = -4. if tick == 1 or 141 <= tick < 160 or tick >= 200 else -1.5 if 2 <= tick <= 80 else 0.
        plan.shouldStop = False
        controls.sm['selfdriveState'].enabled = not 180 <= tick < 188
        for name in controls.sm.logMonoTime:
          controls.sm.logMonoTime[name] = now - 2_000_000
          controls.sm.recv_time[name] = (now - 1_000_000) / 1e9
        with patch('openpilot.selfdrive.car.card.REPLAY', False), \
             patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now)), \
             patch('openpilot.selfdrive.car.card.time.monotonic', return_value=now / 1e9):
          cc, lateral = controls.state_control()
          controls.publish(cc, lateral)
          controls.sm.data['carControl'] = cc
          for mapping in (controls.sm.seen, controls.sm.alive, controls.sm.valid):
            mapping['carControl'] = True
          controls.sm.logMonoTime['carControl'] = now - 2_000_000
          controls.sm.recv_time['carControl'] = (now - 1_000_000) / 1e9
          card.controls_update(out, cc.as_reader())
        age = now - ci.CS.pedal_sensor_ts_nanos
        active = (cc.longActive and ci.CS.pedal_sensor_healthy and ci.CS.pedal_sensor_ts_nanos > 0 and 0 <= age <= 100_000_000 and
                  out.gearShifter == structs.CarState.GearShifter.low and not out.gasPressed and not out.brakePressed and
                  not out.regenBraking and (not controls.longitudinal_inputs.gm_start_enabled or
                    (out.cruiseState.available and not out.cruiseState.enabled and 0 <= now - ci.CS.stock_acc_status_ts_nanos <= 300_000_000)))
        accel = cc.actuators.accel
        law.update_hold(accel, out.vEgo, active)
        self.assertEqual(ci.CC.bolt_regen_hold, law.hold)
        if tick == 1 and speed == 12.:
          self.assertTrue(law.hold)
        if tick == 4 and speed == 12. and not controls.longitudinal_inputs.gm_start_enabled:
          self.assertTrue(law.hold)
          self.assertGreater(accel, linear(out.vEgo, [0, 4, 12, 25], [-.90, -.82, -.72, -.65]))
        if tick % 4:
          continue
        previous_pressed = law.pressed
        law.update_paddle(accel, out.aEgo, out.vEgo, active)
        self.assertEqual(ci.CC.regen_paddle_pressed, law.pressed)
        pressed_seen |= law.pressed
        if tick == 200:
          self.assertTrue(law.pressed)
        if active:
          target = pedal_target(accel, out.vEgo, law.pressed)
          steady = pedal_step(target, steady, accel, out.vEgo) if previous_active and not (law.pressed != previous_pressed and out.vEgo > 1) else target
        else:
          steady = 0.
        previous_active = active
        frames = sent[-1][0]
        self.assertEqual(next(m[1] for m in frames if m[0] == 0x200), pedal_wire(steady, tick // 4))
        for address, length in ((0xbd, 7), (0x1f5, 8)):
          emitted = [m[1] for m in frames if m[0] == address]
          if not emitted:
            self.assertTrue(not cc.enabled or out.regenBraking)
            continue
          pressed = law.pressed and out.vEgo > 2.68
          expected = (bytes([32 if pressed else 0]) + bytes(6) if length == 7 else
                      bytes((12, 12, 0, (5 if gen2 else 7) if pressed else 6, 0, 2 if pressed else 0, 1, 0)))
          self.assertEqual(emitted, [expected])
      self.assertTrue(pressed_seen)
