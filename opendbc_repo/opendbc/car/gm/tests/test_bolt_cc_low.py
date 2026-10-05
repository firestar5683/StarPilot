import unittest

from opendbc.car import structs
from opendbc.car.gm.bolt_cc import button_bytes
from opendbc.car.gm.tests.test_bolt_cc import BOLT_CC_WORDS, control, feed, fixture, native, setup
from opendbc.car.gm.values import CAR
from opendbc.safety.tests.libsafety import libsafety_py


class TestBoltCcLow(unittest.TestCase):
  def test_actual_low_parser_controller_and_native(self):
    for identity in BOLT_CC_WORDS:
      for removed in (False, True):
        for gear in (4, 6):
          for phase in ('active', 'gas', 'brake', 'cancel'):
            with self.subTest(identity=identity, gear=gear, phase=phase, removed=removed):
              cp, ci, packer = fixture(identity, removed=removed)
              now = 1_000_000_000
              _, frames = feed(ci, packer, now, gas=phase == 'gas', brake=phase == 'brake', camera=not removed)
              frames = [frame for frame in frames if frame[0] != 0x1F5]
              frames.append(packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': gear}))
              out = ci.update([(now + 100_000, frames)])
              self.assertTrue(out.canValid)
              self.assertEqual(out.gearShifter, structs.CarState.GearShifter.low if gear == 6 else structs.CarState.GearShifter.drive)
              setup(cp)
              for frame in sorted(frames, key=lambda frame: frame[0] == 0x3D1):
                if frame[0] in (0x184, 0x3D1, 0x1E1, 0xC9, 0x1C4, 0x1F5, 0x34A):
                  self.assertTrue(native('rx', frame, now // 1000))
              ci.CC.frame = 104
              cc = control(long_active=phase == 'active', enabled=phase != 'cancel')
              cc.latActive = phase not in ('brake', 'cancel')
              cc.cruiseControl.override = cc.enabled and not cc.longActive and cp.openpilotLongitudinalControl
              cc.cruiseControl.cancel = out.cruiseState.enabled and (not cc.enabled or not cp.pcmCruise)
              ci.CC.bolt_cc_owner.prev_enabled = phase == 'cancel'
              _, commands = ci.apply(cc.as_reader(), now + 1_000_000)
              buttons = [frame for frame in commands if frame[0] == 0x1E1]
              if phase == 'brake':
                self.assertFalse(buttons)
                self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
              else:
                expected = {'active': 2, 'gas': 3, 'cancel': 6}[phase]
                self.assertEqual([frame[1] for frame in buttons], [button_bytes(expected, 1)])
              for frame in commands:
                self.assertTrue(native('tx', frame, (now + 1_000_000) // 1000), hex(frame[0]))

  def test_other_gears_do_not_gain_button_demand(self):
    for gear in (1, 2, 3, 5, 7):
      cp, ci, packer = fixture(next(iter(BOLT_CC_WORDS)))
      now = 1_000_000_000
      _, frames = feed(ci, packer, now)
      frames = [frame for frame in frames if frame[0] != 0x1F5]
      frames.append(packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': gear}))
      ci.update([(now + 100_000, frames)])
      ci.CC.frame = 104
      _, commands = ci.apply(control().as_reader(), now + 1_000_000)
      self.assertFalse(any(frame[0] == 0x1E1 for frame in commands))

  def test_low_physical_set_release_host_state_remains_native_admitted(self):
    from openpilot.selfdrive.car.car_events import CarEvents
    from openpilot.selfdrive.selfdrived.events import ET
    from openpilot.selfdrive.selfdrived.state import StateMachine

    for removed in (False, True):
      cp, ci, packer = fixture(CAR.CHEVROLET_BOLT_CC_2018_2021, removed=removed)
      self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xC121 if removed else 0xC120)
      _, template = feed(ci, packer, 900_000_000, active=False, camera=not removed)
      setup(cp)
      state_machine = StateMachine()
      car_events = CarEvents(cp)
      previous_state = structs.CarState()
      previous_control = structs.CarControl()
      active_frames = 0
      overridden_frames = 0
      for tick in range(340):
        now = 1_000_000_000 + tick * 10_000_000
        gas = 120 <= tick < 150
        replacement = [
          packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 4 if 180 <= tick < 220 else 6}),
          packer.make_can_msg('ECMCruiseControl', 0, {'CruiseActive': int(tick >= 42), 'CruiseSetSpeed': 54}),
          packer.make_can_msg('AcceleratorPedal2', 0, {'AcceleratorPedal2': 30 if gas else 0}),
          (0x1E1, button_bytes(3 if 40 <= tick < 42 else 1, tick % 4), 0),
        ]
        addresses = {frame[0] for frame in replacement}
        frames = [frame for frame in template if frame[0] not in addresses] + replacement
        for frame in sorted(frames, key=lambda frame: frame[0] == 0x3D1):
          if frame[0] in (0x184, 0x3D1, 0x1E1, 0xC9, 0x1C4, 0x1F5, 0x34A):
            self.assertTrue(native('rx', frame, now // 1000))
        libsafety_py.libsafety.safety_tick()
        cs = ci.update([(now, frames)])
        self.assertTrue(cs.canValid)
        self.assertEqual(cs.gearShifter, structs.CarState.GearShifter.drive if 180 <= tick < 220 else structs.CarState.GearShifter.low)
        events = car_events.update(cs, previous_state, previous_control)
        enabled, active = state_machine.update(events)
        cc = structs.CarControl(enabled=enabled, latActive=active,
                                longActive=enabled and not events.contains(ET.OVERRIDE_LONGITUDINAL))
        cc.actuators.torque = .02 if cc.latActive else 0.
        cc.actuators.accel = 1. if cc.longActive else 0.
        cc.hudControl.setSpeed = 30.
        cc.cruiseControl.override = cc.enabled and not cc.longActive and cp.openpilotLongitudinalControl
        cc.cruiseControl.cancel = cs.cruiseState.enabled and (not cc.enabled or not cp.pcmCruise)
        _, commands = ci.apply(cc.as_reader(), now + 1_000_000)
        for frame in commands:
          self.assertTrue(native('tx', frame, (now + 1_000_000) // 1000), (tick, hex(frame[0])))
        if tick >= 45:
          self.assertTrue(enabled)
          self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
          active_frames += 1
        if gas:
          self.assertFalse(cc.longActive)
          overridden_frames += 1
        previous_state, previous_control = cs, cc
      self.assertGreater(active_frames, 200)
      self.assertEqual(overridden_frames, 30)
