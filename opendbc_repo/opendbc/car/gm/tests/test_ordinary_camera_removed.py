"""Observed PT source contract for ordinary GM camera-absent layouts."""
import unittest
import os
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import DBC, GMFlags, ORDINARY_CAMERA_CAR, ORDINARY_CAMERA_ALPHA_CAR, is_ordinary_camera_profile


def params(identity, *, alpha=False, release=False, analog=True):
  fp = gen_empty_fingerprint()
  fp[0].update({0xF1: 6, 0xC9: 8, 0x1C4: 8, 0x184: 8, 0x34A: 5, 0x1E1: 7})
  if analog:
    fp[0][0xBE] = 6
  return CarInterface.get_params(identity, fp, [], alpha, release, False)


def feed(ci, packer, now, *, cruise=True, main=True, gas=False, brake=False, counter=0):
  from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
  frames = pt_frames(packer, main=main, gas=gas, brake=brake, counter=counter, acc_cruise=2 if cruise else 0)
  if ci.CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG:
    frames = [message for message in frames if message[0] != 0xBE]
  frames.append(packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': 40 if brake else 0}))
  frames.append(packer.make_can_msg('ASCMLKASteeringCmd', 128, {'RollingCounter': counter}))
  return ci.update([(now, frames)]), frames


class TestOrdinaryCameraRemoved(unittest.TestCase):
  def test_final_profile_shared_owners_and_absent_camera_state(self):
    from opendbc.car.gm.aol import qualified_gm
    from opendbc.car.gm.lateral import lane_centering_supported
    from opendbc.car.gm.feature_capabilities import longitudinal_supported
    from openpilot.starpilot.lateral.controller_selection import policy_for
    for identity in ORDINARY_CAMERA_CAR:
      for analog in (False, True):
        for release in (False, True):
          for alpha in (False, True):
            cp = params(identity, alpha=alpha, release=release, analog=analog)
            long = alpha and not release and identity in ORDINARY_CAMERA_ALPHA_CAR
            self.assertTrue(is_ordinary_camera_profile(cp, longitudinal=long))
            self.assertTrue(cp.flags & GMFlags.NO_CAMERA)
            self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xC173 if long else 0xC172)
            self.assertEqual(cp.openpilotLongitudinalControl, long)
            self.assertTrue(qualified_gm(cp))
            self.assertTrue(lane_centering_supported(cp))
            self.assertEqual(longitudinal_supported(cp), long)
            self.assertIsNotNone(policy_for(cp))
            ci = CarInterface(cp)
            packer = CANPacker(DBC[identity][Bus.pt])
            for tick in range(12):
              out, _ = feed(ci, packer, 1_000_000_000 + tick * 10_000_000, counter=tick % 4)
            self.assertTrue(out.canValid)
            self.assertTrue(out.cruiseState.enabled)
            self.assertEqual(out.cruiseState.speed, 0.)
            self.assertFalse(out.stockAeb or out.stockFcw or out.cruiseState.nonAdaptive)

  def test_actual_card_and_malformed_or_missing_startup_sources(self):
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.car.card import Car
    from opendbc.car.gm.radar_interface import RadarInterface
    from opendbc.car.gm.values import is_ordinary_camera_removed
    self.assertFalse(is_ordinary_camera_removed(None))
    for identity in ORDINARY_CAMERA_CAR:
      with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        saved = Params()
        saved.put_bool('OpenpilotEnabledToggle', True, block=True)
        cp = params(identity, alpha=True)
        card = Car(CI=CarInterface(cp), RI=RadarInterface(cp))
        self.assertTrue(is_ordinary_camera_removed(card.CP))
        self.assertEqual(card.CP.safetyConfigs[0].safetyParam, cp.safetyConfigs[0].safetyParam)
      for missing in (0xF1, 0xC9, 0x1C4, 0x184, 0x34A, 0x1E1):
        fp = gen_empty_fingerprint()
        fp[0].update({0xF1: 6, 0xC9: 8, 0x1C4: 8, 0x184: 8, 0x34A: 5, 0x1E1: 7})
        fp[0].pop(missing)
        denied = CarInterface.get_params(identity, fp, [], True, False, False)
        self.assertTrue(denied.dashcamOnly)
      fp[0][missing] = 7
      fp[2][0x320] = 5
      self.assertTrue(CarInterface.get_params(identity, fp, [], True, False, False).dashcamOnly)

  def test_actual_controller_routes_and_source_withdrawal(self):
    for identity in ORDINARY_CAMERA_CAR:
      for alpha in (False, True):
        cp = params(identity, alpha=alpha)
        ci = CarInterface(cp)
        packer = CANPacker(DBC[identity][Bus.pt])
        seen_cancel = False
        for tick in range(112):
          now = 1_000_000_000 + tick * 10_000_000
          out, _ = feed(ci, packer, now, gas=tick >= 50, counter=tick % 4)
          self.assertTrue(out.canValid)
          cc = structs.CarControl(enabled=True, latActive=True, longActive=cp.openpilotLongitudinalControl)
          cc.actuators.torque = .1
          cc.actuators.accel = 1.
          cc.cruiseControl.cancel = True
          _, emitted = ci.apply(cc.as_reader(), now)
          ids = [m[0] for m in emitted]
          self.assertNotIn(0x2CD, ids)
          self.assertFalse(any(i in ids for i in (0x200, 0xBD, 0x1F5, 0x3D1)))
          self.assertEqual(any(i in ids for i in (0x409, 0x40A)), cp.openpilotLongitudinalControl and tick % 100 == 0)
          if 0x409 in ids:
            self.assertLess(ids.index(0x409), ids.index(0x184))
          for address, payload, bus in emitted:
            if address == 0x1E1:
              seen_cancel = True
              self.assertEqual(bus, 2)
              self.assertEqual(payload[4] & 3, tick % 4)
          if not cp.openpilotLongitudinalControl:
            self.assertFalse(any(i in ids for i in (0x2CB, 0x315, 0x370, 0x409, 0x40A)))
        self.assertEqual(seen_cancel, not cp.openpilotLongitudinalControl)
        ci.CS.ordinary_removed_sources = (0,) * 6
        ci.CC.frame = 112
        applied, _ = ci.apply(cc.as_reader(), now + 10_000_000)
        self.assertEqual(applied.torqueOutputCan, 0)
