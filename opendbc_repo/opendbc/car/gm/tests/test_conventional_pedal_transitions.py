"""GM pedal state and caller transition boundaries."""

import unittest
from types import SimpleNamespace

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.gm.gmcan import create_pedal_command, pedal_crc
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.conventional_pedal import policy_for
from opendbc.car.gm.values import CAR, DBC, ORDINARY_CC_CAR
from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
from opendbc.car.gm.tests.test_conventional_pedal import params, pedal_frames


class TestConventionalPedalTransitions(unittest.TestCase):
  def test_actual_decoded_sensor_threshold_and_cruise_standstill(self):
    for identity in ORDINARY_CC_CAR:
      for removed in (False, True):
        for analog in (False, True):
          cp = params(identity, removed=removed, analog=analog)
          ci = CarInterface(cp)
          packer = CANPacker(DBC[identity][Bus.pt])
          for tick in range(24):
            level = (22., 23., 24.)[tick // 8]
            cruise = tick % 2 == 0
            frames = pt_frames(packer, cruise=cruise, acc_cruise=4, counter=tick % 4)
            if not analog:
              frames = [f for f in frames if f[0] != 0xBE]
            frames += pedal_frames(packer, tick, removed=removed)
            frames = [f for f in frames if f[0] != 0x201]
            sensor = packer.make_can_msg('GAS_SENSOR', 0, {'INTERCEPTOR_GAS': level,
                     'INTERCEPTOR_GAS2': level, 'STATE': 0, 'COUNTER_PEDAL': tick % 16})
            raw = bytearray(sensor[1])
            raw[-1] = pedal_crc(raw)
            frames.append((sensor[0], bytes(raw), sensor[2]))
            out = ci.update([(1_000_000_000 + tick * 10_000_000, frames)])
            self.assertTrue(out.canValid)
            self.assertTrue(ci.CS.pedal_sensor_healthy)
            decoded = ci.can_parsers[Bus.pt].vl['GAS_SENSOR']
            mean = (decoded['INTERCEPTOR_GAS'] + decoded['INTERCEPTOR_GAS2']) / 2.
            self.assertEqual(out.gasPressed, mean > 23.)
            self.assertEqual(mean > 23., level == 24.)
            self.assertEqual(out.cruiseState.enabled, cruise)
            self.assertTrue(out.cruiseState.standstill)

  @staticmethod
  def caller(identity, removed):
    cp = params(identity, removed=removed)
    ci = CarInterface(cp)
    packer = CANPacker(DBC[identity][Bus.pt])
    counter = [0]
    def step(accel=1.8, *, speed=0., active=True, stopping=False, resume=False, main=True, bad_crc=False, enabled=None):
      tick = counter[0]
      counter[0] += 1
      frames = pt_frames(packer, cruise=True, acc_cruise=4, counter=tick % 4, main=main)
      frames += pedal_frames(packer, tick, removed=removed, bad_crc=bad_crc)
      now = 1_000_000_000 + tick * 40_000_000
      out = ci.update([(now, frames)]).as_reader().as_builder()
      # Caller boundary fixture preserves actual parser freshness and cruise inputs.
      out.vEgo = speed
      out.standstill = speed == 0.
      ci.CS.out = out.as_reader()
      cc = structs.CarControl(enabled=active if enabled is None else enabled, latActive=True, longActive=active)
      cc.actuators.accel = accel
      cc.actuators.longControlState = (structs.CarControl.Actuators.LongControlState.stopping if stopping else
                                      structs.CarControl.Actuators.LongControlState.pid)
      cc.cruiseControl.resume = resume
      ci.CC.frame = tick * 4
      _, messages = ci.apply(cc.as_reader(), now)
      return next(m for m in messages if m[0] == 0x200), tick % 4
    for _ in range(24):
      step()
    return SimpleNamespace(cp=cp, ci=ci, packer=packer, step=step)

  def test_reached_stored_stop_limits_and_inactive_memory(self):
    for identity in ORDINARY_CC_CAR:
      for removed in (False, True):
        case = self.caller(identity, removed)
        malibu = identity == CAR.CHEVROLET_MALIBU_CC
        self.assertEqual((case.cp.stopAccel, case.ci.CC.conventional_pedal_command.start_speed,
                          case.ci.CC.conventional_pedal_command.stop_speed),
                         (-1.5, .75, .75) if malibu else (-2., .5, .5))
        self.assertEqual(case.ci.CC.conventional_pedal_command.start_speed, policy_for(case.cp).starting_speed)
        steady, active = case.ci.CC.pedal_steady, case.ci.CC.pedal_active_last
        emitted, counter = case.step(active=True, enabled=False)
        self.assertEqual(emitted, create_pedal_command(case.packer, 0., counter))
        self.assertEqual((case.ci.CC.pedal_steady, case.ci.CC.pedal_active_last), (steady, active))
        emitted, counter = case.step(active=False)
        self.assertEqual(emitted, create_pedal_command(case.packer, 0., counter))
        self.assertEqual((case.ci.CC.pedal_steady, case.ci.CC.pedal_active_last), (steady, active))
        emitted, counter = case.step(speed=.24, accel=-1., stopping=True)
        self.assertEqual(emitted, create_pedal_command(case.packer, 0., counter))
        self.assertEqual(case.ci.CC.apply_brake, 150 if malibu else 200)
        self.assertEqual((case.ci.CC.pedal_steady, case.ci.CC.pedal_active_last), (steady, active))
        emitted, counter = case.step(speed=.25, accel=-1., stopping=True)
        self.assertNotEqual(emitted, create_pedal_command(case.packer, 0., counter))
        self.assertLess(case.ci.CC.pedal_steady, steady)
        emitted, counter = case.step(speed=.24, accel=1.8, stopping=True, resume=True)
        self.assertNotEqual(emitted, create_pedal_command(case.packer, 0., counter))
        self.assertGreater(case.ci.CC.pedal_steady, steady)
        emitted, counter = case.step(speed=.24, accel=1.8)
        self.assertEqual(emitted, create_pedal_command(case.packer, 18. / 255., counter))
        emitted, counter = case.step(speed=.6, accel=1.8)
        if malibu:
          self.assertEqual(emitted, create_pedal_command(case.packer, 18. / 255., counter))
        else:
          self.assertNotEqual(emitted, create_pedal_command(case.packer, 18. / 255., counter))

  def test_invalid_sensor_recovery_bounds_final_sng_and_veto_zero(self):
    for identity in ORDINARY_CC_CAR:
      for removed in (False, True):
        case = self.caller(identity, removed)
        emitted, counter = case.step(bad_crc=True)
        self.assertEqual(emitted, create_pedal_command(case.packer, 0., counter))
        self.assertEqual((case.ci.CC.pedal_steady, case.ci.CC.pedal_active_last), (0., True))
        emitted, counter = case.step()
        self.assertEqual(emitted, create_pedal_command(case.packer, .0229, counter))
        emitted, counter = case.step(active=False)
        self.assertEqual(emitted, create_pedal_command(case.packer, 0., counter))
        emitted, counter = case.step()
        self.assertEqual(emitted, create_pedal_command(case.packer, .0229, counter))
        emitted, counter = case.step(active=False, main=False)
        self.assertEqual(emitted, create_pedal_command(case.packer, 0., counter))
