"""The compact Bluetooth glyph follows a fresh powered adapter, not pairing."""

from concurrent.futures import Future
import subprocess
import unittest
from unittest.mock import patch

from openpilot.starpilot.ui.bluetooth_status import BluetoothStatusSource, read_adapter_powered


class FakeExecutor:
  def __init__(self):
    self.future = Future()
    self.calls = 0
    self.closed = False

  def submit(self, _fn):
    self.calls += 1
    return self.future

  def shutdown(self, *, wait, cancel_futures):
    self.closed = True


class TestBluetoothStatus(unittest.TestCase):
  def test_exact_bluez_power_response_only(self):
    for output, expected in (("b true\n", True), ("b false\n", False), ("s true\n", False), ("b true extra\n", False)):
      with self.subTest(output=output), patch("openpilot.starpilot.ui.bluetooth_status.subprocess.run",
                                               return_value=subprocess.CompletedProcess([], 0, output, "")) as run:
        self.assertIs(read_adapter_powered(), expected)
        self.assertEqual(run.call_args.kwargs["timeout"], 1.5)
    with patch("openpilot.starpilot.ui.bluetooth_status.subprocess.run",
               side_effect=subprocess.TimeoutExpired(["busctl"], 1.5)):
      self.assertFalse(read_adapter_powered())

  def test_pending_failure_and_stale_result_never_show_icon(self):
    clock = [10_000_000_000]
    source = BluetoothStatusSource(clock=lambda: clock[0])
    source.executor.shutdown(wait=False, cancel_futures=True)
    executor = FakeExecutor()
    self.enterContext(patch.object(source, "executor", executor))
    try:
      self.assertFalse(source.snapshot())  # schedules work without blocking the render
      self.assertEqual(executor.calls, 1)
      executor.future.set_result((True, clock[0]))
      self.assertTrue(source.snapshot())
      clock[0] += source.MAX_AGE_NS + 1
      self.assertFalse(source.snapshot())
      self.assertEqual(executor.calls, 2)
      source.close()
      self.assertFalse(source.snapshot())
      self.assertTrue(executor.closed)
    finally:
      source.close()

  def test_worker_rejects_failed_query(self):
    source = BluetoothStatusSource(request=lambda: (_ for _ in ()).throw(OSError("no adapter")), clock=lambda: 3)
    try:
      self.assertEqual(source._poll(), (False, 3))
    finally:
      source.close()


if __name__ == "__main__":
  unittest.main()
