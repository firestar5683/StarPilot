import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from openpilot.starpilot.flm.learning_producer import AutomaticLearningProducer


class TestAutomaticLearningProducer(unittest.TestCase):
  def fixture(self):
    cp = SimpleNamespace(carFingerprint='fixture', lateralTuning=SimpleNamespace(torque=SimpleNamespace(latAccelFactor=3.0)))
    with patch('openpilot.starpilot.flm.learning_producer.interfaces', {'fixture': lambda cp: object()}):
      producer = AutomaticLearningProducer(cp, None)
    lc = SimpleNamespace(saturated=False, actualLateralAccel=.4, desiredLateralAccel=.4,
                         desiredLateralJerk=0., error=0., errorRate=0., p=0., i=0., d=0., f=0., output=.1)
    lateral = SimpleNamespace(which=lambda: 'torqueState', torqueState=lc)
    self.now = 10_000_000_000
    values = {
      'carState': SimpleNamespace(vEgo=20., steeringPressed=False, brakePressed=False, gasPressed=False,
                                 canValid=True, canTimeout=False, steeringAngleDeg=1., steeringTorque=0.),
      'carControl': SimpleNamespace(latActive=True, actuators=SimpleNamespace(torque=-.1)),
      'carOutput': SimpleNamespace(actuatorsOutput=SimpleNamespace(torque=-.1)),
      'controlsState': SimpleNamespace(lateralControlState=lateral),
      'deviceMotion': SimpleNamespace(timestamp=self.now, angularVelocityDevice=SimpleNamespace(valid=True),
                                     orientationNED=SimpleNamespace(valid=True), inputsOK=True, sensorsOK=True, posenetOK=True),
      'extrinsicsCalibration': SimpleNamespace(calStatus='calibrated'),
      'lateralDelay': SimpleNamespace(lateralDelay=0.),
    }
    class SM(dict):
      def all_checks(self, services):
        return True
    sm = SM(values)
    sm.seen = dict.fromkeys(sm, True)
    sm.updated = dict(sm.seen)
    sm.logMonoTime = dict.fromkeys(sm, self.now)
    producer.calibrator = Mock(feed_extrinsics_calibration=lambda msg: None,
      build_calibrated_pose=lambda pose: SimpleNamespace(angular_velocity=SimpleNamespace(yaw=.02)))
    return producer, sm

  def ticks(self, producer, sm, count):
    identity = {'basis': [3., 0., .1]}
    pose = SimpleNamespace(orientation=SimpleNamespace(roll=0.))
    with patch('openpilot.starpilot.flm.learning_producer.read_selection', return_value=SimpleNamespace(mode='standard')), \
         patch('openpilot.starpilot.flm.learning_producer.conversion_identity', return_value='linear'), \
         patch('openpilot.starpilot.flm.learning_producer.identity_for', return_value=(identity, True, False)), \
         patch('openpilot.starpilot.flm.learning_producer.Pose.from_device_motion', return_value=pose), \
         patch('openpilot.starpilot.flm.learning_producer.time.monotonic_ns', side_effect=lambda: self.now), \
         patch('openpilot.starpilot.flm.learning_producer.time.clock_gettime_ns', side_effect=lambda clock: self.now):
      for _ in range(count):
        self.now += 50_000_000
        sm.logMonoTime = dict.fromkeys(sm, self.now)
        sm['deviceMotion'].timestamp = self.now
        producer.update(sm, None)

  def test_one_block_per_continuous_maneuver_and_genuine_boundary(self):
    producer, sm = self.fixture()
    self.ticks(producer, sm, 800)
    self.assertEqual(producer.optional_errors, 0)
    self.assertEqual(len(producer.windows), 1)
    first = producer.windows[0]
    self.assertEqual(len(first.response), 240)
    self.assertLessEqual(first.active_since_ns + 2_000_000_000, first.response[0].mono_ns)
    self.ticks(producer, sm, 500)
    self.assertEqual(len(producer.windows), 1)
    sm['controlsState'].lateralControlState.torqueState.desiredLateralAccel = -.4
    sm['carOutput'].actuatorsOutput.torque = .1
    self.ticks(producer, sm, 300)
    self.assertEqual(len(producer.windows), 2)
    self.assertNotEqual(first.block_id, producer.windows[1].block_id)
    self.assertLess(first.response[-1].mono_ns, producer.windows[1].response[0].mono_ns)

  def test_override_discards_prebuffer_and_preserves_alignment_history(self):
    producer, sm = self.fixture()
    self.ticks(producer, sm, 140)
    self.assertGreater(len(producer.pending), 0)
    sm['carState'].steeringPressed = True
    self.ticks(producer, sm, 1)
    self.assertEqual(len(producer.pending), 0)
    self.assertEqual(len(producer.points), 0)
    self.assertIsNone(producer.active_since_ns)
    self.assertGreater(len(producer.torques), 100)
    sm['carState'].steeringPressed = False
    self.ticks(producer, sm, 19)
    self.assertIsNone(producer.active_since_ns)
    self.assertEqual(len(producer.points), 0)
    self.ticks(producer, sm, 300)
    self.assertEqual(producer.optional_errors, 0)
    self.assertEqual(len(producer.windows), 1)

  def test_optional_source_and_publication_errors_invalidate_without_raising(self):
    producer, sm = self.fixture()
    self.ticks(producer, sm, 400)
    self.assertEqual(len(producer.windows), 1)
    with patch.object(producer, '_update', side_effect=ValueError('malformed optional Params')):
      producer.update(sm, None)
    self.assertIsNone(producer.identity)
    self.assertEqual(len(producer.windows), 0)
    self.assertEqual(len(producer.torques), 0)
    with patch.object(producer, '_get_msg', side_effect=ValueError('optional encoding')):
      self.assertIsNone(producer.get_msg())
    self.assertEqual(producer.optional_errors, 2)

  def test_fit_only_new_blocks_and_minute_duty_limit(self):
    producer, _ = self.fixture()
    producer.identity = {'basis': [3., 0., .1]}
    window = SimpleNamespace(response=tuple(SimpleNamespace(mono_ns=i + 1) for i in range(240)))
    producer.windows.extend([window] * 24)
    producer.block = 24
    with patch('openpilot.starpilot.flm.learning_producer.evaluate_linear_factor', return_value=object()) as evaluate:
      producer.evaluate(100_000_000_000)
      producer.evaluate(200_000_000_000)
      self.assertEqual(evaluate.call_count, 1)
      producer.windows.append(window)
      producer.block += 1
      self.assertEqual(len(producer.windows), 24)
      producer.evaluate(120_000_000_000)
      self.assertEqual(evaluate.call_count, 1)
      producer.evaluate(160_000_000_000)
      self.assertEqual(evaluate.call_count, 2)

  def test_frozen_actual_calibration_and_invalid_reacquisition(self):
    producer, sm = self.fixture()
    with patch.object(producer.calibrator, 'feed_extrinsics_calibration', wraps=producer.calibrator.feed_extrinsics_calibration) as feed:
      self.ticks(producer, sm, 400)
      self.assertEqual(feed.call_count, 1)
      self.assertEqual(len(producer.windows), 1)
      sm['extrinsicsCalibration'].calStatus = 'uncalibrated'
      self.ticks(producer, sm, 1)
      self.assertEqual(len(producer.windows), 0)
      self.assertFalse(producer.calibration_frozen)
      self.assertIsNone(producer.result)
      sm['extrinsicsCalibration'].calStatus = 'calibrated'
      self.ticks(producer, sm, 1)
      self.assertEqual(feed.call_count, 2)
      self.assertTrue(producer.calibration_frozen)

  def test_pose_payload_future_or_stale_cannot_become_evidence(self):
    producer, sm = self.fixture()
    self.ticks(producer, sm, 140)
    for bad_stamp in (self.now + 1, self.now - 100_000_001):
      sm['deviceMotion'].timestamp = bad_stamp
      with patch('openpilot.starpilot.flm.learning_producer.time.monotonic_ns', return_value=self.now), \
           patch('openpilot.starpilot.flm.learning_producer.time.clock_gettime_ns', return_value=self.now):
        producer.update(sm, None)
      self.assertEqual(producer.reason, 'pose_source_age')
      self.assertEqual(len(producer.pending), 0)
      self.assertEqual(len(producer.points), 0)
      self.assertIsNone(producer.active_since_ns)
      self.assertEqual(producer.optional_errors, 0)


if __name__ == '__main__':
  unittest.main()
