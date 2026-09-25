"""Process recovery requires established Big output and confirmed owner exit."""
import ast
from dataclasses import replace
from pathlib import Path
import unittest

from openpilot.starpilot.models.recovery import ModelRecoveryOwner, RecoveryEvidence

BASE = 10_000_000_000
IDENTITY = (123, 456)


def evidence(t, *, output=True, alive=True):
  now = BASE + int(t * 1e9)
  stamp = now if output else BASE + 2_000_000_000
  return RecoveryEvidence(now, BASE, IDENTITY if alive else None, alive, True, BASE,
                          stamp, stamp, output, True, ((now, int(t * 20)), (now, int(t * 20))))


def arm(owner):
  for t in (.1, .6, 1.1, 1.6, 2.):
    assert owner.step(evidence(t)) is None
  assert owner.armed


class TestModelRecovery(unittest.TestCase):
  def test_stall_escalates_once_and_small_waits_for_exit(self):
    owner = ModelRecoveryOwner()
    arm(owner)
    self.assertIsNone(owner.step(evidence(3., output=False)))
    self.assertEqual(owner.step(evidence(4., output=False)), 'interrupt')
    self.assertTrue(owner.small_only)
    self.assertIsNone(owner.step(evidence(4.2, output=False)))
    self.assertEqual(owner.step(evidence(4.5, output=False)), 'kill')
    self.assertEqual(owner.step(evidence(4.6, output=False, alive=False)), 'small')
    for t in (5., 10., 100.):
      self.assertIsNone(owner.step(evidence(t, output=False)))

  def test_separated_big_outputs_do_not_count_as_sustained_arming(self):
    owner = ModelRecoveryOwner()
    for t in (.1, 3., 6., 9.):
      self.assertIsNone(owner.step(evidence(t)))
      self.assertFalse(owner.armed)
    self.assertIsNone(owner.step(evidence(12., output=False)))
    self.assertFalse(owner.small_only)

  def test_uncertain_exit_blocks_small_and_new_drive(self):
    owner = ModelRecoveryOwner()
    arm(owner)
    self.assertEqual(owner.step(evidence(4., output=False)), 'interrupt')
    self.assertEqual(owner.step(evidence(4.5, output=False)), 'kill')
    self.assertEqual(owner.step(evidence(5.5, output=False)), 'failed')
    self.assertEqual(owner.phase, 'failed')
    self.assertIsNone(owner.step(replace(evidence(6.), drive_id=BASE + 1)))
    self.assertEqual(owner.phase, 'failed')

  def test_startup_small_wrong_receipt_old_output_cannot_arm(self):
    mutations = ({'big_receipt': False}, {'identity': None}, {'output_big': False},
                 {'loaded_ns': BASE - 1}, {'model_ns': BASE - 1}, {'driving_ns': BASE - 1},
                 {'output_valid': False})
    for mutation in mutations:
      owner = ModelRecoveryOwner()
      for t in (1., 2., 3., 10.):
        self.assertIsNone(owner.step(replace(evidence(t), **mutation)))
      self.assertFalse(owner.small_only)

  def test_camera_starvation_repeated_frame_and_frozen_timestamp_block_recovery(self):
    for cameras in ((), ((BASE, 1), (BASE, 1)), ((BASE + 4_000_000_000, 40),) * 2):
      owner = ModelRecoveryOwner()
      arm(owner)
      for t in (3., 4., 5.):
        self.assertIsNone(owner.step(replace(evidence(t, output=False), cameras=cameras)))
      self.assertFalse(owner.small_only)

  def test_camera_reacquisition_requires_sustained_progress_then_recovers(self):
    owner = ModelRecoveryOwner()
    arm(owner)
    self.assertIsNone(owner.step(replace(evidence(3., output=False), cameras=())))
    for t in (3.5, 4., 4.5, 5., 5.5):
      self.assertIsNone(owner.step(evidence(t, output=False)))
    self.assertEqual(owner.step(evidence(6., output=False)), 'interrupt')

  def test_owner_change_and_output_resume_rearm_cleanly(self):
    owner = ModelRecoveryOwner()
    arm(owner)
    changed = replace(evidence(4., output=False), identity=(124, 457), loaded_ns=BASE + 3_000_000_000)
    self.assertIsNone(owner.step(changed))
    self.assertFalse(owner.armed)
    owner = ModelRecoveryOwner()
    arm(owner)
    self.assertIsNone(owner.step(evidence(3., output=False)))
    self.assertIsNone(owner.step(evidence(3.5)))
    self.assertIsNone(owner.step(evidence(4., output=False)))

  def test_offroad_resets_after_failed_owner_exit(self):
    owner = ModelRecoveryOwner()
    arm(owner)
    owner.step(evidence(4., output=False))
    self.assertIsNone(owner.step(replace(evidence(4.1), drive_id=0)))
    self.assertTrue(owner.small_only)
    self.assertEqual(owner.step(replace(evidence(4.2, alive=False), drive_id=0)), 'exit')
    self.assertFalse(owner.small_only)
    self.assertEqual(owner.phase, 'monitor')

  def test_offroad_and_new_drive_keep_bounded_escalation(self):
    for drive in (0, BASE + 5_000_000_000):
      owner = ModelRecoveryOwner()
      arm(owner)
      owner.step(evidence(4., output=False))
      self.assertEqual(owner.step(replace(evidence(4.5, output=False), drive_id=drive)), 'kill')
      self.assertEqual(owner.step(replace(evidence(4.6, output=False, alive=False), drive_id=drive)), 'exit')
      self.assertFalse(owner.small_only)

  def test_real_child_exit_is_required_before_small_action(self):
    import subprocess
    import sys
    import signal
    import select
    child = subprocess.Popen([sys.executable, '-c',
                              'import signal,time; signal.signal(signal.SIGINT,signal.SIG_IGN); print("ready",flush=True); time.sleep(30)'],
                             stdout=subprocess.PIPE, text=True)
    try:
      assert child.stdout is not None
      self.assertTrue(select.select([child.stdout], [], [], 2)[0])
      self.assertEqual(child.stdout.readline().strip(), "ready")
      owner = ModelRecoveryOwner()
      arm(owner)
      self.assertEqual(owner.step(evidence(4., output=False)), 'interrupt')
      child.send_signal(signal.SIGINT)
      self.assertIsNone(child.poll())
      self.assertIsNone(owner.step(evidence(4.2, output=False)))
      self.assertEqual(owner.step(evidence(4.5, output=False)), "kill")
      child.send_signal(signal.SIGKILL)
      child.wait(timeout=2)
      assert child.poll() is not None
      self.assertEqual(owner.step(evidence(4.6, output=False, alive=False)), 'small')
    finally:
      if child.poll() is None:
        child.kill()
        child.wait(timeout=2)
      if child.stdout is not None:
        child.stdout.close()

  def test_child_restriction_precedes_amd_and_preserves_randomizer_selection(self):
    source = Path(__file__).parents[3] / 'selfdrive/modeld/modeld.py'
    tree = ast.parse(source.read_text())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    statements = [ast.unparse(n) for n in main.body]
    selection = next(s for s in statements if 'selection = resolve_runtime' in s)
    self.assertIn('not recovery_small_only', selection)
    self.assertIn('randomize=not recovery_small_only', selection)
    self.assertLess(next(i for i, s in enumerate(statements) if 'selection = resolve_runtime' in s),
                    next(i for i, s in enumerate(statements) if 'from tinygrad.runtime.ops_amd import AMDDevice' in s))
