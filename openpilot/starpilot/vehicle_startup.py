"""Generic lifetime holder for a car-owned prepublication startup transaction."""
import threading


class VehicleStartupOwner:
  def __init__(self, owner=None):
    # Explicit-CI callers may supply an already prepared car-owned decision.
    self.owner = owner
    self.send_lock = threading.Lock()

  def prepare(self, cp, interface, callbacks, *, requested, admission):
    factory = getattr(interface, 'startup_owner', None)
    if factory is None:
      return cp
    recv, send = callbacks
    def locked_send(frames):
      with self.send_lock:
        send(frames)
    owner = factory(cp, (recv, locked_send), requested=requested)
    if owner is None:
      return cp
    # Register before any ECU request so a partially constructed Card can close.
    self.owner = owner
    return owner.prepare(admission=admission)

  def configure(self, ci):
    required = getattr(type(ci), 'startup_required', None)
    if required is not None and required(ci.CP):
      matches = getattr(self.owner, 'prepared_for', None)
      if matches is None or not matches(ci.CP):
        raise RuntimeError('Car interface requires a matching prepared startup owner')
    if self.owner is not None:
      self.owner.configure(ci)

  def finalize_aol_configuration(self, ci):
    finalize = getattr(self.owner, 'finalize_aol_configuration', None)
    if finalize is not None:
      finalize(ci)

  def seal_publication(self):
    if self.owner is not None:
      self.owner.seal_publication()

  def check(self):
    if self.owner is not None:
      self.owner.check()

  def after_state(self, **context):
    if self.owner is not None:
      self.owner.after_state(**context)

  def consume_cruise_resume(self):
    return self.owner.consume_cruise_resume() if self.owner is not None else None

  def before_control(self, *, configured, ci, now_ns, control_current):
    return self.owner is None or self.owner.before_control(
      configured=configured, sources_current=self.owner.sources_current(ci, now_ns), control_current=control_current)

  def maintain(self, *, configured):
    if self.owner is not None:
      self.owner.maintain(configured=configured)

  def sent(self, frames, *, valid):
    if self.owner is not None:
      self.owner.sent(frames, valid=valid)

  def close(self):
    if self.owner is not None:
      self.owner.close()
