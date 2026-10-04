import unittest
from unittest.mock import Mock, patch

from openpilot.system.manager import process


class Child:
  def __init__(self, **kwargs):
    self.exitcode = None
    self.pid = 123
    self.joined = False

  def start(self):
    pass

  def join(self):
    self.joined = True

  def is_alive(self):
    return self.exitcode is None


class TestProcessRecovery(unittest.TestCase):
  def setUp(self):
    self.now = 100.0
    self.enterContext(patch.object(process, "Process", Child))
    self.enterContext(patch.object(process.time, "monotonic", lambda: self.now))
    self.enterContext(patch.object(process, "cloudlog"))
    self.enterContext(patch.object(process.os, "kill"))
    self.enterContext(patch.object(process, "join_process", lambda p, timeout: setattr(p, "exitcode", 0)))

  def make_process(self, restart=True):
    return process.PythonProcess("ui", "ui", lambda started, params, cp: started, restart_on_exit=restart)

  def step(self, p, started=True, ignored=None):
    process.ensure_running({p.name: p}.values(), started, Mock(), None, not_run=ignored)

  def test_crash_restarts_after_delay_and_reaps_child(self):
    p = self.make_process()
    self.step(p)
    old = p.proc
    old.exitcode = 1
    self.step(p)
    self.assertIs(p.proc, old)
    self.now += 0.99
    self.step(p)
    self.assertIs(p.proc, old)
    self.now += 0.02
    self.step(p)
    self.assertIsNot(p.proc, old)
    self.assertTrue(old.joined)

  def test_backoff_caps_and_stable_run_resets(self):
    p = self.make_process()
    self.step(p)
    for delay in (1, 2, 4, 8, 16, 30, 30):
      p.proc.exitcode = 1
      self.step(p)
      self.assertEqual(p.restart_at - self.now, delay)
      self.now += delay
      self.step(p)
    self.now += 60
    self.step(p)
    self.assertEqual(p.restart_failures, 0)
    p.proc.exitcode = 0
    self.step(p)
    self.assertEqual(p.restart_at - self.now, 1)

  def test_gates_cancel_pending_restart(self):
    for reason in ("predicate", "disabled", "ignored"):
      with self.subTest(reason=reason):
        p = self.make_process()
        self.step(p)
        p.proc.exitcode = 1
        self.step(p)
        p.enabled = reason != "disabled"
        started = reason != "predicate"
        ignored = ["ui"] if reason == "ignored" else None
        self.step(p, started, ignored)
        self.assertIsNone(p.proc)
        self.assertEqual(p.restart_at, 0)
        self.now += 40
        self.step(p, started, ignored)
        self.assertIsNone(p.proc)

  def test_other_processes_do_not_restart(self):
    p = self.make_process(restart=False)
    self.step(p)
    old = p.proc
    old.exitcode = 1
    self.now += 100
    self.step(p)
    self.assertIs(p.proc, old)

  def test_intentional_stop_is_not_crash(self):
    p = self.make_process()
    self.step(p)
    p.stop(block=False)
    self.assertTrue(p.shutting_down)
    p.proc.exitcode = 0
    self.step(p)
    self.assertEqual(p.restart_failures, 0)
    self.assertEqual(p.restart_at, 0)
