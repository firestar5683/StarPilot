"""Bounded EV9 startup tester sender; never receives CAN or restores ECUs."""
import threading
import time

STARTUP_DEADLINE_S = 60.0  # Shared software guard convention, not measured ECU timing.
TESTER_PERIOD_S = 1.0  # Original controller sends Tester Present every100 control frames.


class EV9Keeper:
  def __init__(self, send, *, clock=time.monotonic, event=None, thread_factory=threading.Thread):
    self.send = send
    self.clock = clock
    self.event = event if event is not None else threading.Event()
    self.thread_factory = thread_factory
    self.thread = None
    self.started = None
    self.next_send = None
    self.abort_reason = None

  def tick(self):
    if self.event.is_set() or self.abort_reason is not None:
      return False
    now = self.clock()
    if self.started is None:
      self.started = now
      self.next_send = now
    if now < self.started or now - self.started >= STARTUP_DEADLINE_S:
      self.abort_reason = 'startup software deadline or clock reversal'
      self.event.set()
      return False
    if now >= self.next_send:
      try:
        self.send()
      except Exception:
        self.abort_reason = 'startup tester send failed'
        self.event.set()
        return False
      self.next_send = now + TESTER_PERIOD_S
    return True

  def start(self):
    if self.thread is not None:
      raise RuntimeError('EV9 keeper already started')
    self.started = self.clock()
    self.next_send = self.started
    def loop():
      while self.tick():
        self.event.wait(TESTER_PERIOD_S)
    self.thread = self.thread_factory(target=loop, name='ev9-startup-tester', daemon=True)
    self.thread.start()

  def stop(self):
    self.event.set()
    # Called outside VehicleStartupOwner.send_lock; the sender may hold it.
    if self.thread is not None:
      self.thread.join()
      self.thread = None
