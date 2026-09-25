"""Explicit conventional-cruise interceptor startup and physical command owner."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.gmcan import pedal_crc, create_buttons
from opendbc.car.gm.values import CAR, DBC, ORDINARY_CC_CAR, is_conventional_cc_pedal_profile
from opendbc.car.gm.startup_preferences import prepare_disable_longitudinal
from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames


def params(identity, *, disabled=False, removed=False, release=False, enabled=True, sensor=True, analog=True):
  fp = gen_empty_fingerprint()
  fp[0].update({0xF1: 6, 0xBE: 6, 0xC9: 8, 0x3D1: 8, 0x1E1: 7})
  if not analog:
    fp[0].pop(0xBE)
  if sensor:
    fp[0][0x201] = 6
  if not removed:
    fp[2][0x320] = 6
  cp = CarInterface.get_params(identity, fp, [], False, release, False)
  prepare_disable_longitudinal(cp, disabled)
  return cp


def pedal_frames(packer, counter, pressed=False, *, removed=False, bad_crc=False):
  sensor = packer.make_can_msg('GAS_SENSOR', 0, {
    'INTERCEPTOR_GAS': 30 if pressed else 0, 'INTERCEPTOR_GAS2': 30 if pressed else 0,
    'STATE': 0, 'COUNTER_PEDAL': counter % 16,
  })
  data = bytearray(sensor[1])
  data[5] = pedal_crc(data) ^ int(bad_crc)
  frames = [(sensor[0], bytes(data), sensor[2]),
            packer.make_can_msg("ASCMLKASteeringCmd", 128, {"RollingCounter": counter % 4}),
            packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': 0})]
  if not removed:
    frames += [packer.make_can_msg('ASCMLKASteeringCmd', 2, {'RollingCounter': counter % 4}),
               packer.make_can_msg('AEBCmd', 2, {})]
  return frames


class TestConventionalPedal(unittest.TestCase):
  def test_explicit_startup_profile_and_disabled_policy(self):
    from opendbc.car.gm.conventional_pedal import policy_for
    for identity in ORDINARY_CC_CAR:
      for removed in (False, True):
        for release in (False, True):
          for disabled in (False, True):
            cp = params(identity, removed=removed, release=release, disabled=disabled)
            self.assertTrue(is_conventional_cc_pedal_profile(cp))
            self.assertFalse(cp.pcmCruise)
            self.assertEqual(cp.openpilotLongitudinalControl, not disabled)
            self.assertEqual(cp.safetyConfigs[0].safetyParam, (0xC186 if disabled else 0xC180) + int(removed))
            self.assertEqual(cp.minEnableSpeed, -1.)
            self.assertEqual(policy_for(cp) is not None, not disabled)
            if not disabled:
              self.assertEqual(policy_for(cp).starting_speed, .75 if identity == CAR.CHEVROLET_MALIBU_CC else .5)
            self.assertEqual(cp.stopAccel, -1.5 if identity == CAR.CHEVROLET_MALIBU_CC else -2.)
        self.assertTrue(is_conventional_cc_pedal_profile(params(identity, removed=removed, enabled=False)))
        self.assertFalse(is_conventional_cc_pedal_profile(params(identity, removed=removed, sensor=False)))

  def test_actual_sensor_threshold_and_stock_source_are_independent(self):
    for identity in ORDINARY_CC_CAR:
      cp = params(identity)
      ci = CarInterface(cp)
      packer = CANPacker(DBC[identity][Bus.pt])
      for tick in range(24):
        now = 1_000_000_000 + tick * 10_000_000
        frames = pt_frames(packer, cruise=False, acc_cruise=2, counter=tick % 4)
        frames += pedal_frames(packer, tick, pressed=tick >= 12)
        out = ci.update([(now, frames)])
        self.assertTrue(out.canValid)
        self.assertFalse(out.cruiseState.enabled)
        self.assertFalse(out.cruiseState.nonAdaptive)
        self.assertEqual(out.gasPressed, tick >= 12)
        self.assertTrue(ci.CS.pedal_sensor_healthy)

  def test_actual_pedal_counter_cancel_and_disabled_takeover(self):
    for identity in ORDINARY_CC_CAR:
      for removed in (False, True):
        for disabled in (False, True):
          cp = params(identity, removed=removed, disabled=disabled)
          ci = CarInterface(cp)
          packer = CANPacker(DBC[identity][Bus.pt])
          seen_cancel = False
          for tick in range(40):
            now = 1_000_000_000 + tick * 10_000_000
            cruise = tick < 25
            frames = [message for message in pt_frames(packer, cruise=cruise, counter=tick % 4) if message[0] != 0x1E1]
            frames.append(create_buttons(packer, 0, tick % 4, 1))
            frames += pedal_frames(packer, tick, removed=removed)
            out = ci.update([(now, frames)])
            self.assertTrue(out.canValid)
            cc = structs.CarControl(enabled=True, latActive=True, longActive=True)
            cc.actuators.torque = .1
            cc.actuators.accel = 1.
            cc.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
            _, messages = ci.apply(cc.as_reader(), now)
            self.assertFalse(any(message[0] in (0x2CB, 0x315, 0x370, 0x2CD, 0x3D1, 0xBD, 0x1F5) for message in messages))
            pedal = [message for message in messages if message[0] == 0x200]
            cancel = [message for message in messages if message[0] == 0x1E1]
            if disabled:
              self.assertFalse(pedal or cancel)
            else:
              if pedal:
                self.assertEqual(pedal[0][2], 0)
                self.assertEqual(pedal[0][1][4] & 0xF, (tick // 4) % 4)
              if cancel:
                seen_cancel = True
                self.assertTrue(cruise)
                self.assertEqual(cancel[0][2], 0)
                if any(message[0] == 0x184 for message in messages):
                  ids = [message[0] for message in messages]
                  self.assertLess(ids.index(0x1E1), ids.index(0x184))
            self.assertEqual(any(message[0] == 0x184 for message in messages), tick % 10 == 0)
          if not disabled:
            self.assertTrue(seen_cancel)

  def test_sensor_crc_and_timeout_clear_actual_pedal_output(self):
    identity = next(iter(ORDINARY_CC_CAR))
    cp = params(identity, removed=True)
    ci = CarInterface(cp)
    packer = CANPacker(DBC[identity][Bus.pt])
    cc = structs.CarControl(enabled=True, latActive=True, longActive=True)
    cc.actuators.accel = 1.
    for tick in range(24):
      now = 1_000_000_000 + tick * 10_000_000
      ci.update([(now, pt_frames(packer, cruise=False, counter=tick % 4) + pedal_frames(packer, tick, removed=True))])
      ci.apply(cc.as_reader(), now)
    self.assertGreater(ci.CC.pedal_steady, 0)
    ci.update([(now + 10_000_000, pt_frames(packer, cruise=False) + pedal_frames(packer, 24, removed=True, bad_crc=True))])
    ci.CC.frame = 24
    ci.apply(cc.as_reader(), now + 10_000_000)
    self.assertEqual(ci.CC.pedal_steady, 0)

  def test_actual_packed_commands_match_registered_native_owner(self):
    from opendbc.car.gm.gmcan import create_buttons
    from opendbc.car.gm.tests.test_bolt_cc import setup, native
    from opendbc.safety.tests.libsafety import libsafety_py
    safety = libsafety_py.libsafety
    for removed in (False, True):
      cp = params(CAR.CADILLAC_CT6_CC, removed=removed)
      ci = CarInterface(cp)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      setup(cp)
      for tick in range(24):
        now = 1_000_000_000 + tick * 20_000_000
        frames = pt_frames(packer, cruise=tick < 12, counter=tick % 4)
        frames = [message for message in frames if message[0] != 0x1E1]
        frames += pedal_frames(packer, tick, removed=removed)
        frames.append(create_buttons(packer, 0, tick % 4, 1))
        out = ci.update([(now, frames)])
        self.assertTrue(out.canValid)
        for message in frames:
          if message[2] != 128:  # Host loopback is not a physical CAN bus.
            native('rx', message, now // 1000)
        if tick == 1:
          native('rx', create_buttons(packer, 0, tick % 4, 2), now // 1000)
        if tick == 2:
          native('rx', create_buttons(packer, 0, tick % 4, 1), now // 1000)
        safety.safety_tick()
        self.assertTrue(safety.safety_config_valid())
        cc = structs.CarControl(enabled=True, latActive=True, longActive=tick >= 3)
        cc.actuators.accel = 1.
        cc.actuators.torque = .01
        cc.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
        _, emitted = ci.apply(cc.as_reader(), now)
        for message in emitted:
          self.assertTrue(native('tx', message, now // 1000), hex(message[0]))

  def test_active_cancel_uses_neutral_single_use_credit_and_native_ttl(self):
    from opendbc.car.gm.gmcan import create_buttons
    from opendbc.car.gm.tests.test_silverado_cc_pedal import params as silverado_params
    from opendbc.safety.tests.libsafety import libsafety_py
    safety = libsafety_py.libsafety
    for silverado, disabled in ((False, False), (True, False), (True, True)):
      for removed in (False, True):
        cp = (silverado_params(removed=removed, disabled=disabled) if silverado else
              params(CAR.CADILLAC_CT6_CC, removed=removed))
        ci = CarInterface(cp)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        safety.set_alternative_experience(0)
        self.assertEqual(safety.set_safety_hooks(int(cp.safetyConfigs[0].safetyModel.raw), cp.safetyConfigs[0].safetyParam), 0)
        safety.init_tests()
        counter = 0
        accepted_credit = set()
        cancelled = []
        for tick in range(90):
          now = 1_000_000_000 + tick * 10_000_000
          if (tick < 50 or tick >= 70) and tick % 3 == 0 or tick == 50:
            counter = (counter + 1) % 4
          button = 3 if 30 <= tick < 40 else 1
          frames = [m for m in pt_frames(packer, cruise=True, counter=counter) if m[0] != 0x1E1]
          frames += pedal_frames(packer, tick, removed=removed)
          if 40 <= tick < 66:
            frames = [m for m in frames if m[0] != 0x1C4]
          frames.append(create_buttons(packer, 0, counter, button))
          out = ci.update([(now, frames)])
          self.assertTrue(out.canValid)
          safety.set_timer(now // 1000)
          for address, data, bus in frames:
            if bus != 128:
              self.assertTrue(safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data)))
          safety.safety_tick()
          self.assertTrue(safety.safety_config_valid())
          # Proactive cancellation is independent of software engagement.
          cc = structs.CarControl(enabled=False, latActive=False, longActive=False)
          cc.cruiseControl.cancel = disabled
          _, messages = ci.apply(cc.as_reader(), now)
          cancels = [m for m in messages if m[0] == 0x1E1]
          if 30 <= tick < 40 or 50 <= tick < 66 or silverado and 66 <= tick < 70:
            self.assertFalse(cancels, (silverado, removed, tick))
          for message in messages:
            self.assertTrue(safety.safety_tx_hook(libsafety_py.make_CANPacket(message[0], message[2], message[1])),
                            (silverado, removed, tick, message))
          for message in cancels:
            credit = ci.CS.conventional_cancel_credit
            self.assertEqual(message, create_buttons(packer, 2 if disabled else 0,
                                                      credit.counter if disabled else (credit.counter + 1) % 4, 6))
            self.assertNotIn(credit.credit_ns, accepted_credit)
            accepted_credit.add(credit.credit_ns)
            self.assertLessEqual(now - credit.credit_ns, 100_000_000 if silverado else 300_000_000)
            cancelled.append(tick)
        self.assertTrue(any(tick < 30 for tick in cancelled))
        self.assertTrue(any(40 <= tick < 50 for tick in cancelled), 'fresh neutral recovers after physical SET')
        self.assertTrue(any(tick >= 70 for tick in cancelled), 'new neutral restores cancellation after stale credit')
        self.assertTrue(all(right - left > 4 for left, right in zip(cancelled, cancelled[1:], strict=False)))
        if not silverado:
          self.assertTrue(any(66 <= tick < 70 for tick in cancelled), 'ordinary 300ms credit remains eligible')

  def test_malibu_selected_analog_brake_source_and_alternate_threshold(self):
    from opendbc.car.gm.values import GMFlags
    for analog in (False, True):
      for removed in (False, True):
        cp = params(CAR.CHEVROLET_MALIBU_CC, analog=analog, removed=removed)
        self.assertTrue(is_conventional_cc_pedal_profile(cp))
        self.assertEqual(bool(cp.flags & GMFlags.NO_ACCELERATOR_POS_MSG), not analog)
        ci = CarInterface(cp)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        for tick in range(32):
          pressed = tick >= 16
          frames = [m for m in pt_frames(packer, cruise=False, brake=not pressed, counter=tick % 4)
                    if m[0] not in (0xBE, 0xF1)]
          frames += pedal_frames(packer, tick, removed=removed)
          frames = [m for m in frames if m[0] != 0xF1]
          frames += [packer.make_can_msg('EBCMBrakePedalPosition', 0,
                     {'BrakePedalPosition': 21 if pressed else 20})]
          if analog:
            frames += [packer.make_can_msg('ECMAcceleratorPos', 0, {'BrakePedalPos': 8 if pressed else 7})]
          out = ci.update([(1_000_000_000 + tick * 10_000_000, frames)])
          self.assertTrue(out.canValid)
          self.assertEqual(out.brakePressed, pressed)
