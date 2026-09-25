import unittest

from openpilot.starpilot.lateral.low_speed_advisory import LowSpeedAdvisory


class TestLowSpeedAdvisory(unittest.TestCase):
  def test_startup_first_crossing_episode_and_later_crossings(self):
    owner = LowSpeedAdvisory()
    minimum = 10 / 3.6
    for speed in (0., 1., minimum - .001):
      self.assertFalse(owner.update(speed, minimum, drive_id=10))
    self.assertFalse(owner.update(minimum, minimum, drive_id=10))
    for speed in (minimum - .001, 0., 1., 0.):
      self.assertTrue(owner.update(speed, minimum, drive_id=10))
    self.assertFalse(owner.update(minimum, minimum, drive_id=10))
    for speed in (0., minimum + 1., 0.):
      self.assertFalse(owner.update(speed, minimum, drive_id=10))

  def test_confirmed_new_drive_and_process_reset(self):
    owner = LowSpeedAdvisory()
    owner.update(4., 3., drive_id=10)
    self.assertTrue(owner.update(2., 3., drive_id=10))
    self.assertTrue(owner.update(2., 3., drive_id=0))
    self.assertFalse(owner.update(2., 3., drive_id=20))
    self.assertFalse(owner.update(3., 3., drive_id=20))
    self.assertTrue(owner.update(2., 3., drive_id=20))
    self.assertFalse(LowSpeedAdvisory().update(2., 3., drive_id=20))

  def test_invalid_sample_cannot_create_or_erase_crossing(self):
    owner = LowSpeedAdvisory()
    for speed in (float('nan'), float('inf'), -float('inf')):
      self.assertFalse(owner.update(speed, 3., drive_id=10))
    self.assertFalse(owner.update(2., 3., drive_id=10))
    owner.update(4., 3., drive_id=10)
    self.assertTrue(owner.update(2., 3., drive_id=10))
    self.assertFalse(owner.update(float('nan'), 3., drive_id=0))
    self.assertTrue(owner.update(2., 3., drive_id=10))
    self.assertFalse(owner.update(2., 0., drive_id=10))

  def test_actual_selfdrived_event_hook_preserves_faults(self):
    from unittest.mock import patch
    from opendbc.car import gen_empty_fingerprint, structs
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.values import CAR
    from openpilot.cereal import messaging
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.selfdrived.events import ET, EventName
    from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD

    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x201] = 6
    fingerprint[2].update({0x180: 4, 0x320: 8})
    cp = CarInterface.get_params(CAR.CHEVROLET_BOLT_CC_2018_2021, fingerprint, [], False, False, False)
    self.assertEqual(cp.safetyConfigs[0].safetyParam, 0x9D)
    self.assertAlmostEqual(cp.minSteerSpeed, 10 / 3.6, delta=1e-6)
    with OpenpilotPrefix(), patch('openpilot.selfdrive.selfdrived.selfdrived.REPLAY', True):
      drive = SelfdriveD(CP=cp)
      drive.initialized = True
      device = messaging.new_message('deviceState', valid=True, logMonoTime=1_000_000_000)
      device.deviceState.started = True
      device.deviceState.startedMonoTime = 1_000_000_000
      device.deviceState.freeSpacePercent = 50.
      drive.sm.update_msgs(1., [device.as_reader()])
      state = structs.CarState()
      state.canValid = True
      state.gearShifter = structs.CarState.GearShifter.drive
      state.cruiseState.available = True
      state.vCruise = 40.

      def sample(speed, *, temporary=False, permanent=False, valid=True, timeout=False):
        state.vEgo = speed
        state.lowSpeedAlert = speed < cp.minSteerSpeed
        state.steerFaultTemporary = temporary
        state.steerFaultPermanent = permanent
        state.canValid, state.canTimeout = valid, timeout
        drive.update_events(state)
        drive.CS_prev = structs.CarState.new_message(**state.to_dict())
        return set(drive.events.names)

      for speed, expected in ((0., False), (cp.minSteerSpeed, False), (1., True),
                              (0., True), (cp.minSteerSpeed, False), (1., False)):
        with self.subTest(speed=speed, expected=expected):
          self.assertEqual(EventName.belowSteerSpeed in sample(speed), expected)
      # Actual CarEvents severity is retained, regardless of advisory suppression.
      temporary = sample(4., temporary=True)
      self.assertIn(EventName.steerTempUnavailableSilent, temporary)
      warning = next(event for event in drive.events.to_msg() if event.name == EventName.steerTempUnavailableSilent)
      self.assertTrue(warning.warning)
      self.assertFalse(warning.immediateDisable)
      permanent = sample(4., permanent=True)
      self.assertIn(EventName.steerUnavailable, permanent)
      self.assertTrue(drive.events.contains(ET.IMMEDIATE_DISABLE))
      self.assertIn(EventName.canError, sample(1., valid=False))
      self.assertIn(EventName.canBusMissing, sample(1., valid=False, timeout=True))
      device.deviceState.startedMonoTime = 2_000_000_000
      device.logMonoTime = 2_000_000_000
      drive.sm.update_msgs(2., [device.as_reader()])
      self.assertNotIn(EventName.belowSteerSpeed, sample(1.))
      self.assertNotIn(EventName.belowSteerSpeed, sample(cp.minSteerSpeed))
      self.assertIn(EventName.belowSteerSpeed, sample(1.))
