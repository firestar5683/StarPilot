"""Startup clock/sender checks without threads, receive callbacks or sleeps."""
import unittest
from opendbc.car.hyundai.ev9_keeper import EV9Keeper


class TestEV9Keeper(unittest.TestCase):
  def test_original_one_hz_cadence_and_software_deadline(self):
    now, sent = [0.0], []
    keeper = EV9Keeper(lambda: sent.append(now[0]), clock=lambda: now[0])
    for value in (0.0, 0.2, 0.999, 1.0, 1.1, 2.0):
      now[0] = value
      self.assertTrue(keeper.tick())
    self.assertEqual(sent, [0.0, 1.0, 2.0])
    now[0] = 60.0
    self.assertFalse(keeper.tick())
    self.assertIsNotNone(keeper.abort_reason)
    self.assertEqual(sent, [0.0, 1.0, 2.0])

  def test_send_failure_only_marks_abort_no_receive_or_restore(self):
    calls = []
    def send():
      calls.append('send')
      raise OSError('transport')
    keeper = EV9Keeper(send, clock=lambda: 0.0)
    self.assertFalse(keeper.tick())
    self.assertEqual(calls, ['send'])
    self.assertEqual(keeper.abort_reason, 'startup tester send failed')
    self.assertFalse(keeper.tick())
    self.assertEqual(calls, ['send'])

  def test_stop_sets_event_before_join_without_sender_lock(self):
    operations = []
    class Event:
      stopped = False
      def is_set(self):
        return self.stopped
      def set(self):
        self.stopped = True
        operations.append('stop')
    event = Event()
    keeper = EV9Keeper(lambda: None, clock=lambda: 0.0, event=event)
    class Thread:
      def join(self):
        if not event.stopped:
          raise AssertionError('join before event')
        operations.append('join')
    keeper.thread = Thread()
    keeper.stop()
    self.assertEqual(operations, ['stop', 'join'])
    self.assertFalse(keeper.tick())
