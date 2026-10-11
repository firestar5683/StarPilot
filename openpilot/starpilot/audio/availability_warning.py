"""Bounded delivery of an already selected availability chime, independent of authority."""
MAX_DELIVERY_NS = 400_000_000

class AvailabilityWarningDelivery:
  def __init__(self):
    self.context = None
    self.until_ns = 0
    self.last_ns = 0

  def observe(self, *, session, drive, now_ns, selected, requested_until_ns):
    context = (session, drive) if session and drive > 0 else None
    if context != self.context or now_ns < self.last_ns or context is None:
      self.until_ns = 0
    self.context, self.last_ns = context, now_ns
    if context is not None and selected and now_ns <= requested_until_ns:
      self.until_ns = max(self.until_ns, min(requested_until_ns, now_ns + MAX_DELIVERY_NS))

  def pending(self, *, session, drive, now_ns, audible_none, priority, low_priority):
    return (self.context is not None and self.context == (session, drive) and drive > 0 and
            self.last_ns <= now_ns <= self.until_ns and
            audible_none and priority <= low_priority)
