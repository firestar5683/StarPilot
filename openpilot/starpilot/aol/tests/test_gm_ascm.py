"""Independent axes use the finalized ordinary ASCM vehicle owner."""

import unittest

from opendbc.car.gm.aol import qualified_gm
from opendbc.car.gm.tests.test_ascm_intercept import params
from opendbc.car.gm.values import ORDINARY_ASCM_CAR
from openpilot.starpilot.aol.vehicle import policy_for, create_intent
from openpilot.starpilot.aol.intent import AolSettings


class TestGmAscmAol(unittest.TestCase):
  def test_actual_finalized_cp_and_default_off(self):
    settings = AolSettings(False, 0., 0, 0, (0, 0, 0), (0, 0, 0))
    for identity in ORDINARY_ASCM_CAR:
      for release in (False, True):
        for alpha in (False, True):
          for c9 in (False, True):
            for radar in (False, True):
              cp = params(identity, sascm=True, alpha=alpha, release=release, accelerator=not c9, radar=radar)
              self.assertTrue(qualified_gm(cp))
              self.assertEqual(cp.alternativeExperience, 0)
              policy = policy_for(cp)
              self.assertTrue(policy.normal_runtime_supported)
              intent = create_intent(cp, settings, policy)
              self.assertFalse(intent.allowed_latch)
              cp.alternativeExperience = 32
              self.assertTrue(qualified_gm(cp))
              cp.alternativeExperience = 33
              self.assertFalse(qualified_gm(cp))

  def test_profile_integrity_and_finite_tune_boundaries(self):
    for identity in ORDINARY_ASCM_CAR:
      cp = params(identity, sascm=True)
      for field in ('passive', 'dashcamOnly', 'notCar'):
        setattr(cp, field, True)
        self.assertFalse(qualified_gm(cp))
        setattr(cp, field, False)
      cp.safetyConfigs[0].safetyParam |= 4
      self.assertFalse(qualified_gm(cp))
      cp = params(identity, sascm=True)
      if cp.lateralTuning.which() == 'torque':
        cp.lateralTuning.torque.friction = float('nan')
      else:
        cp.lateralTuning.pid.kpV = [float('nan')]
      self.assertFalse(qualified_gm(cp))

  def test_actual_controller_cruise_off_lateral_only_and_default_off(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus, structs
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.tests.test_volt_camera_control import feed_camera
    from opendbc.car.gm.values import DBC
    for identity in ORDINARY_ASCM_CAR:
      for alpha in (False, True):
        for alternative in (0, 32):
          cp = params(identity, sascm=True, alpha=alpha)
          cp.alternativeExperience = alternative
          ci = CarInterface(cp)
          packer = CANPacker(DBC[identity][Bus.pt])
          observed = []
          for tick in range(6):
            now = 1_000_000_000 + tick * 40_000_000
            out, sources = feed_camera(ci, packer, now, counter=tick % 4, active=False)
            sources = [packet for packet in sources if packet[0] != 0x370]
            sources.append(packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCruiseState': 0}))
            out = ci.update([(now + 1, sources)])
            now += 1
            self.assertTrue(out.canValid)
            self.assertTrue(out.cruiseState.available)
            self.assertFalse(out.cruiseState.enabled)
            command = structs.CarControl(enabled=False, latActive=alternative == 32, longActive=False)
            command.actuators.torque = .1
            _, packets = ci.apply(command.as_reader(), now)
            observed.extend(packet for packet in packets if packet[0] == 0x180)
          self.assertTrue(observed)
          nonneutral = any(((packet[1][0] & 7) << 8 | packet[1][1]) != 0 for packet in observed)
          self.assertEqual(nonneutral, alternative == 32)
