"""Optional notification state; never supersedes driving alerts or starts inference."""


class GpuModelReadyChime:
  def __init__(self):
    self.ready = None
    self.pending_until = None

  def update(self, *, active, loading, onroad, enabled, now):
    ready = bool(onroad and active and not loading)
    # A soundd restart with an already-loaded model is not a loading event.
    if self.ready is False and ready and enabled:
      self.pending_until = now + 5.0
    self.ready = ready
    if not enabled or not ready or (self.pending_until is not None and now >= self.pending_until):
      self.pending_until = None
    return self.pending_until is not None

  def consume(self):
    self.pending_until = None
