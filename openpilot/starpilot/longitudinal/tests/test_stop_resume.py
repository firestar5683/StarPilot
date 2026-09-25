from collections import deque
import unittest

from openpilot.cereal import messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.longitudinal.stop_resume import StopResume, collect_resume

BASE = 100_000_000_000
DRIVE = BASE - 1_000_000_000


def event(tick, buttons=(), *, valid=True, can=True):
  message = messaging.new_message('carState', valid=valid)
  message.logMonoTime = BASE + tick * 10_000_000
  message.carState.canValid = can
  message.carState.buttonEvents = [{'type': kind, 'pressed': pressed} for kind, pressed in buttons]
  return message.as_reader()


class StopResumeTests(unittest.TestCase):
  def setUp(self):
    self.owner = StopResume()

  def observe(self, item, **changes):
    args = {'now_ns': int(item.logMonoTime) + 1, 'drive_id': DRIVE}
    args.update(changes)
    self.owner.observe(item, **args)

  def consume(self, tick, **changes):
    args = {'now_ns': BASE + tick * 10_000_000 + 1, 'drive_id': DRIVE, 'car_ns': BASE + tick * 10_000_000}
    args.update(changes)
    return self.owner.consume(**args)

  def test_between_model_ticks_press_survives_release_without_replay(self):
    queue = deque([event(0), event(1, [('accelCruise', True)]), event(2, [('accelCruise', False)]), event(3), event(4)])
    collect_resume(self.owner, None, lambda _: queue.popleft() if queue else None, now_ns=BASE + 50_000_000, drive_id=DRIVE)
    self.assertTrue(self.consume(5))
    self.assertFalse(self.consume(6))

  def test_held_repeat_duplicate_and_release_are_not_new_presses(self):
    self.observe(event(0))
    press = event(1, [('resumeCruise', True)])
    self.observe(press)
    self.assertTrue(self.consume(1))
    self.observe(press)
    self.observe(event(2, [('resumeCruise', True)]))
    self.assertFalse(self.consume(2))
    self.observe(event(3, [('resumeCruise', False)]))
    self.assertFalse(self.consume(3))
    self.observe(event(4, [('resumeCruise', True)]))
    self.assertTrue(self.consume(4))

  def test_startup_held_and_other_buttons_do_not_release(self):
    self.observe(event(0, [('accelCruise', True)]))
    self.observe(event(1, [('accelCruise', True)]))
    self.assertFalse(self.consume(1))
    self.observe(event(2, [('accelCruise', False)]))
    self.observe(event(3, [('decelCruise', True), ('cancel', True)]))
    self.assertFalse(self.consume(3))
    self.observe(event(4, [('accelCruise', True)]))
    self.assertTrue(self.consume(4))

  def test_invalid_stale_future_old_drive_and_gaps_clear_pending(self):
    for defect in ('invalid', 'can', 'stale', 'future', 'drive', 'gap'):
      with self.subTest(defect=defect):
        self.owner.reset()
        self.observe(event(0))
        self.observe(event(1, [('accelCruise', True)]))
        tick = 30 if defect == 'gap' else 2
        now = BASE + (200_000_000 if defect == 'stale' else 0 if defect == 'future' else tick * 10_000_000) + 1
        self.observe(event(tick, valid=defect != 'invalid', can=defect != 'can'), now_ns=now,
                     drive_id=BASE + 15_000_000 if defect == 'drive' else DRIVE)
        self.assertFalse(self.consume(tick))

  def test_expiry_and_newer_than_current_car_state(self):
    self.observe(event(0))
    self.observe(event(1, [('resumeCruise', True)]))
    self.assertFalse(self.consume(2, car_ns=BASE))
    self.assertTrue(self.consume(2))
    self.observe(event(3, [('resumeCruise', False)]))
    self.observe(event(4, [('resumeCruise', True)]))
    self.assertFalse(self.consume(20))

  def test_received_press_newer_than_planner_frame_waits_for_next_coherent_frame(self):
    self.observe(event(0))
    self.observe(event(2, [('resumeCruise', True)]))
    self.assertFalse(self.consume(1))
    self.assertEqual(self.owner.pending_ns, BASE + 20_000_000)
    self.assertFalse(self.consume(3, car_ns=BASE + 10_000_000))
    self.assertTrue(self.consume(3))
    self.assertFalse(self.consume(4))

  def test_concurrent_publish_during_drain_does_not_clear_valid_press(self):
    with OpenpilotPrefix():
      publisher = messaging.PubMaster(['carState'])
      receiver = messaging.sub_sock('carState', conflate=False, timeout=1000)
      publisher.send('carState', event(0).as_builder())
      queued = deque([event(1, [('resumeCruise', True)]), event(2, [('resumeCruise', False)])])
      received_ns = BASE + 1

      def receive(socket):
        nonlocal received_ns
        item = messaging.recv_one_or_none(socket)
        if item is not None:
          received_ns = int(item.logMonoTime) + 1
          if queued:
            publisher.send('carState', queued.popleft().as_builder())
        return item

      collect_resume(self.owner, receiver, receive, now_ns=BASE + 1, drive_id=DRIVE, receive_clock=lambda: received_ns)
      self.assertFalse(self.consume(0))
      self.assertTrue(self.consume(3))
      self.assertFalse(self.consume(4))

  def test_actual_future_timestamp_still_discards_pending_press(self):
    queue = deque([event(0), event(1, [('resumeCruise', True)]), event(3, [('resumeCruise', False)])])
    collect_resume(self.owner, None, lambda _: queue.popleft() if queue else None, now_ns=BASE + 1,
                   drive_id=DRIVE, receive_clock=lambda: BASE + 20_000_000)
    self.assertFalse(self.consume(4))
    self.assertEqual(self.owner.pending_ns, 0)

  def test_actual_card_stream_retains_fast_press_and_release(self):
    with OpenpilotPrefix():
      publisher = messaging.PubMaster(['carState'])
      receiver = messaging.sub_sock('carState', conflate=False, timeout=1000)
      for item in (event(0), event(1, [('resumeCruise', True)]), event(2, [('resumeCruise', False)])):
        publisher.send('carState', item.as_builder())
      collect_resume(self.owner, receiver, messaging.recv_one_or_none, now_ns=BASE + 30_000_000, drive_id=DRIVE)
      self.assertTrue(self.consume(3))
      self.assertFalse(self.consume(4))

  def test_malformed_queue_cannot_crash_planner_or_release(self):
    queue = deque([event(0), event(1, [('accelCruise', True)]), object()])
    collect_resume(self.owner, None, lambda _: queue.popleft() if queue else None, now_ns=BASE + 30_000_000, drive_id=DRIVE)
    self.assertFalse(self.consume(3))

  def test_queue_bound_discards_all_pending_override(self):
    queue = deque([event(tick, [('accelCruise', tick == 19)] if tick in (19, 20) else ()) for tick in range(33)])
    collect_resume(self.owner, None, lambda _: queue.popleft() if queue else None, now_ns=BASE + 320_000_000, drive_id=DRIVE)
    self.assertEqual(len(queue), 1)
    self.assertFalse(self.consume(32))
