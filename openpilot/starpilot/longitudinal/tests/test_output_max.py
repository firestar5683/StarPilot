"""Saved live ceiling and the actual final longitudinal controller boundary."""

from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.starpilot.longitudinal.output_max import KEY, OutputMaximum, read_maximum
from openpilot.starpilot.longitudinal.tests.test_gm_volt_long_policy import controls_fixture


class OutputMaximumTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.path = Path(self.params.get_param_path(KEY))

  def test_saved_range_factory_and_invalid_complete_sources(self):
    self.assertEqual(read_maximum(self.params).value, 4.0)
    for raw, expected in ((b"0.1", .1), (b"4.0", 4.0), (b"1.25", 1.25), (b"0.099", None),
                          (b"4.01", None), (b"nan", None), (b"inf", None), (b"", None), (b"broken", None)):
      with self.subTest(raw=raw):
        self.path.write_bytes(raw)
        self.assertEqual(read_maximum(self.params).value, expected)
    self.path.write_bytes(b"1" * 129)
    self.assertFalse(read_maximum(self.params).readable)
    self.path.unlink()
    self.path.symlink_to(self.path.parent / "missing")
    self.assertFalse(read_maximum(self.params).readable)

  def test_live_refresh_failure_keeps_last_valid_and_recovery_replaces(self):
    controls, _, _ = controls_fixture()
    owner = OutputMaximum(self.params, controls.CP)
    self.path.write_bytes(b"broken")
    self.assertEqual(owner.sample(0), 4.0)
    self.assertFalse(owner.saved.valid)
    self.path.write_bytes(b"0.5")
    self.assertEqual(owner.sample(1_000_000_000), .5)
    self.path.write_bytes(b"1.5")
    self.assertEqual(owner.sample(1_999_999_999), .5)
    self.assertEqual(owner.sample(2_000_000_000), 1.5)
    self.path.write_bytes(b"nan")
    self.assertEqual(owner.sample(3_000_000_000), 1.5)
    with patch("openpilot.starpilot.longitudinal.output_max.read_saved", side_effect=OSError("unreadable")):
      self.assertEqual(owner.sample(4_000_000_000), 1.5)
    self.path.write_bytes(b"0.1")
    self.assertEqual(owner.sample(5_000_000_000), .1)
    self.assertEqual(owner.sample(10), .1)  # Clock reversal permits a new attempt, never a tiny inferred cap.
    self.path.unlink()
    self.assertEqual(owner.sample(1_000_000_010), 4.0)

  def test_actual_controls_clamps_after_pid_preserving_history_braking_and_inactive(self):
    controls, now, offset = controls_fixture()
    reference, _, _ = controls_fixture()
    controls.longitudinal_output_maximum = OutputMaximum(self.params, controls.CP)
    self.path.write_bytes(b"0.25")
    for owner in (controls, reference):
      owner.sm['longitudinalPlan'].aTarget = .5
      owner.LoC.pid.i = .8
    with patch.dict(os.environ, {'REPLAY': '0'}), \
         patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now + offset)), \
         patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=now):
      actual, _ = controls.state_control()
      original, _ = reference.state_control()
      self.assertGreater(original.actuators.accel, .25)
      self.assertEqual(actual.actuators.accel, .25)
      self.assertEqual(controls.LoC.last_output_accel, reference.LoC.last_output_accel)
      self.assertEqual((controls.LoC.pid.p, controls.LoC.pid.i, controls.LoC.pid.f),
                       (reference.LoC.pid.p, reference.LoC.pid.i, reference.LoC.pid.f))
      for owner in (controls, reference):
        owner.sm['longitudinalPlan'].aTarget = -1.0
        owner.LoC.pid.i = 0.0
      actual, _ = controls.state_control()
      original, _ = reference.state_control()
      self.assertLess(actual.actuators.accel, 0)
      self.assertEqual(actual.actuators.accel, original.actuators.accel)
      self.assertEqual(controls.LoC.last_output_accel, reference.LoC.last_output_accel)
      controls.sm['selfdriveState'].enabled = False
      actual, _ = controls.state_control()
      self.assertEqual((actual.actuators.accel, controls.LoC.last_output_accel), (0., 0.))
