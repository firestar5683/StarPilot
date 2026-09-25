from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tinygrad.runtime.support.am import startup_trace as trace


class TestStartupTrace(unittest.TestCase):
  def setUp(self):
    self.packets = []
    for name, replacement in (("ENABLED", True), ("REPORT", self.packets.append), ("_short_reads", 0)):
      override = patch.object(trace, name, replacement)
      override.start()
      self.addCleanup(override.stop)

  def test_entries_and_poll_samples_are_bounded(self):
    dev = SimpleNamespace()
    for result in range(10000):
      self.assertEqual(trace.value(dev, "cp_status", result), result)
    for index in range(100):
      trace.note(dev, "stage", index=index)
      trace.value(dev, f"extra_{index}", index)
    trace.emit(dev, "complete")
    entries = self.packets[0]["entries"]
    self.assertEqual(len(entries), 64)
    self.assertEqual((entries[0]["first"], entries[0]["last"], entries[0]["reads"]), (0, 9999, 10000))
    self.assertNotIn("_startup_trace_entries", dev.__dict__)

  def test_ack_mask_read_count_and_first_gc_only(self):
    dev = SimpleNamespace()
    reads = []
    values = iter((0x80, 0x82, 0x84, 0x84))
    returned = object()

    def read_ack():
      raw = next(values)
      reads.append(raw)
      return raw

    def wait(read, **kwargs):
      self.assertEqual(kwargs, {"value": 4, "msg": "flush_tlb timeout"})
      while read() != kwargs["value"]:
        pass
      return returned

    for _ in range(2):
      self.assertIs(trace.wait_tlb(dev, "GC", 1, 123, 2, wait, read_ack), returned)
    self.assertEqual(reads, [0x80, 0x82, 0x84, 0x84])
    self.assertEqual(len(self.packets), 1)
    self.assertEqual(self.packets[0]["outcome"], "first_gc_acknowledged")
    sample = self.packets[0]["entries"][-1]
    self.assertEqual((sample["reads"], sample["first"], sample["last"]), (3, 0x80, 0x84))

  def test_non_gc_and_disabled_trace_preserve_wait(self):
    for ip, enabled in (("MM", True), ("GC", False)):
      with self.subTest(ip=ip, enabled=enabled), patch.object(trace, "ENABLED", enabled):
        dev = SimpleNamespace()
        reads = []

        def read_ack(reads=reads):
          reads.append(9)
          return 9

        def wait(read, **kwargs):
          self.assertEqual(kwargs, {"value": 1, "msg": "flush_tlb timeout"})
          return read()

        self.assertEqual(trace.wait_tlb(dev, ip, 0, 123, 0, wait, read_ack), 1)
        self.assertEqual(reads, [9])
        self.assertEqual(dev.__dict__, {})
    self.assertEqual(self.packets, [])

  def test_wait_failure_preserves_exception_and_observed_reads(self):
    error = TimeoutError("original timeout")

    def wait(read, **kwargs):
      self.assertEqual(read(), 0)
      self.assertEqual(read(), 0)
      raise error

    with self.assertRaises(TimeoutError) as caught:
      trace.wait_tlb(SimpleNamespace(), "GC", 0, 123, 0, wait, lambda: 0x80)
    self.assertIs(caught.exception, error)
    self.assertEqual(self.packets[0]["outcome"], "first_gc_failure")
    sample = self.packets[0]["entries"][-1]
    self.assertEqual((sample["reads"], sample["first"], sample["last"]), (2, 0x80, 0x80))

  def test_callback_failure_does_not_replace_result_or_exception(self):
    error = RuntimeError("original initialization failure")
    returned = object()

    @trace.initialization
    def initialize(dev, fail):
      if fail:
        raise error
      return returned

    def broken_report(packet):
      raise OSError("logger unavailable")

    with patch.object(trace, "REPORT", broken_report):
      self.assertIs(initialize(SimpleNamespace(), False), returned)
      with self.assertRaises(RuntimeError) as caught:
        initialize(SimpleNamespace(), True)
      self.assertIs(caught.exception, error)
      self.assertEqual(trace.wait_tlb(SimpleNamespace(), "GC", 0, 123, 0, lambda read, **kwargs: read(), lambda: 1), 1)
      trace.short_read(0x1000, 4, 0)

  def test_short_read_reports_are_bounded(self):
    for _ in range(100):
      trace.short_read(0x1000, 4, 2)
    self.assertEqual(len(self.packets), 8)
    self.assertEqual([packet["sample"] for packet in self.packets], list(range(1, 9)))
    self.assertTrue(all((packet["address"], packet["expected"], packet["actual"]) == (0x1000, 4, 2)
                        for packet in self.packets))
    with patch.object(trace, "ENABLED", False), patch.object(trace, "_short_reads", 0):
      trace.short_read(0x1000, 4, 0)
    self.assertEqual(len(self.packets), 8)


if __name__ == "__main__":
  unittest.main()
