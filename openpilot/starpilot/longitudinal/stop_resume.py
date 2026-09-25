"""Fresh physical RES presses retained across the model planner's slower ticks."""

from opendbc.car.structs import car


BUTTONS = frozenset((car.CarState.ButtonEvent.Type.accelCruise, car.CarState.ButtonEvent.Type.resumeCruise))
MAX_AGE_NS = 150_000_000


class StopResume:
  def __init__(self):
    self.reset()

  def reset(self):
    self.drive_id = 0
    self.last_ns = 0
    self.held = set()
    self.pending_ns = 0
    self.ready = False

  def observe(self, event, *, now_ns: int, drive_id: int):
    if drive_id != self.drive_id:
      self.reset()
      self.drive_id = drive_id
    stamp = int(event.logMonoTime)
    state = event.carState
    if (not event.valid or not state.canValid or state.canTimeout or drive_id <= 0 or
        not drive_id < stamp <= now_ns or now_ns - stamp > MAX_AGE_NS):
      self.reset()
      return
    if stamp <= self.last_ns:
      return
    if self.last_ns and stamp - self.last_ns > MAX_AGE_NS:
      self.ready = False
      self.held.clear()
      self.pending_ns = 0
    self.last_ns = stamp
    events = [button for button in state.buttonEvents if button.type.raw in BUTTONS]
    if not self.ready:
      # A press already present when subscribing/recovering is not a new
      # gesture. Require its release before accepting another press.
      self.held.update(int(button.type.raw) for button in events if button.pressed)
      self.held.difference_update(int(button.type.raw) for button in events if not button.pressed)
      self.ready = not self.held
      return
    for button in events:
      if button.pressed:
        if int(button.type.raw) not in self.held:
          self.pending_ns = stamp
        self.held.add(int(button.type.raw))
      else:
        self.held.discard(int(button.type.raw))

  def consume(self, *, now_ns: int, drive_id: int, car_ns: int) -> bool:
    if (drive_id != self.drive_id or self.pending_ns <= drive_id or
        now_ns - self.pending_ns > MAX_AGE_NS):
      self.pending_ns = 0
      return False
    # A valid received edge may be newer than the planner's frozen frame.
    # Defer it until both that frame and its carState have caught up.
    if self.pending_ns > min(now_ns, car_ns):
      return False
    self.pending_ns = 0
    return True


def collect_resume(owner: StopResume, socket, receive, *, now_ns: int, drive_id: int, receive_clock=None):
  # Normally five 100 Hz messages arrive per model tick. A backlog cannot
  # turn old presses into a new driver override or monopolize plannerd.
  for _ in range(32):
    event = receive(socket)
    if event is None:
      return
    try:
      received_ns = receive_clock() if receive_clock is not None else now_ns
      owner.observe(event, now_ns=received_ns, drive_id=drive_id)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError, RuntimeError):
      owner.reset()
      return
  owner.reset()
