"""Ioniq 6 AOL desire: a full engagement also arms LKAS-managed AOL."""
from openpilot.starpilot.aol.intent import AolCardIntent, AOL_TOGGLE


class Ioniq6CardIntent(AolCardIntent):
  def __init__(self, settings):
    super().__init__(settings, explicit_latch=True)
    self._engaged_previous = False

  def update(self, CS, *, consumed_buttons=frozenset(), fault_active=None, now_ns=0, native_rejection_ns=0,
             standard_enabled=False):
    super().update(CS, consumed_buttons=consumed_buttons, fault_active=fault_active, now_ns=now_ns,
                   native_rejection_ns=native_rejection_ns, standard_enabled=standard_enabled)
    # A stale carControl can drop standard_enabled for a frame while cruise stays
    # engaged; requiring both to fall keeps that from reading as a new engagement.
    engaged = bool(standard_enabled or CS.cruiseState.enabled)
    engagement_started = engaged and not self._engaged_previous
    self._engaged_previous = engaged
    if (engagement_started and self.settings.enabled and self.lkas_action == AOL_TOGGLE and
        CS.canValid and not CS.canTimeout and not CS.accFaulted and not self._fault_inhibit):
      # Full engagement means LAT and LONG: arm AOL so brake withdraws only LONG,
      # and LKAS can then drop the remaining LAT.
      self.allowed_latch = True
      self.pause_lateral = False
      self._last_latch_edge_ns = now_ns
