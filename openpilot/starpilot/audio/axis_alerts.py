from openpilot.cereal import log
from openpilot.starpilot.aol.runtime import current_intent
from openpilot.starpilot.aol.wire import INTENT_SERVICE

AudibleAlert = log.SelfdriveState.AudibleAlert
COALESCE_NS = 250_000_000


class _Transition:
  def __init__(self):
    self.session = None
    self.sequence = 0
    self.active = False
    self.observed_at = 0

  def update(self, session, sequence: int, active: bool, now_ns: int) -> int:
    changed = 0
    if session is None:
      self.session = None
    elif session != self.session or now_ns - self.observed_at > COALESCE_NS:
      self.session, self.sequence, self.active, self.observed_at = session, sequence, active, now_ns
    elif sequence > self.sequence:
      changed = int(active) - int(self.active)
      self.sequence, self.active, self.observed_at = sequence, active, now_ns
    return changed


class AxisAlerts:
  def __init__(self):
    self.lateral = _Transition()
    self.longitudinal = _Transition()
    self.last_sound = AudibleAlert.none
    self.last_sound_at = 0
    self.native_sound = AudibleAlert.none

  def update(self, sm, native_sound: int, now_ns: int) -> int:
    intent = (current_intent(sm, car_state_ns=int(sm.logMonoTime[INTENT_SERVICE]), now_ns=now_ns)
              if INTENT_SERVICE in sm.logMonoTime else None)
    # Engagement is persistent driver intent. Temporary native permission loss,
    # pedal override and output suppression must not replay engagement sounds.
    state_ns = int(sm.logMonoTime.get('selfdriveState', 0))
    state_fresh = (state_ns > 0 and 0 <= now_ns - state_ns <= 100_000_000 and
                   sm.valid['selfdriveState'] and sm.alive['selfdriveState'])
    lateral_known = intent is not None and (intent.pauseLateral or intent.lateralArmed or state_fresh)
    lateral = self.lateral.update(intent.producerSessionId if lateral_known else None, intent.sequence if intent else 0,
                                  bool(intent and not intent.pauseLateral and
                                       (intent.lateralArmed or (state_fresh and sm['selfdriveState'].active))), now_ns)
    longitudinal = self.longitudinal.update(
      intent.producerSessionId if intent is not None and state_fresh else None,
      intent.sequence if intent is not None else 0,
      bool(intent is not None and state_fresh and sm['selfdriveState'].enabled and not intent.pauseLongitudinal), now_ns)
    extra_sound = (AudibleAlert.disengage if min(lateral, longitudinal) < 0 else
                   AudibleAlert.engage if max(lateral, longitudinal) > 0 else AudibleAlert.none)

    if native_sound != AudibleAlert.none:
      if native_sound != self.native_sound and native_sound in (AudibleAlert.engage, AudibleAlert.disengage):
        self.last_sound, self.last_sound_at = native_sound, now_ns
      self.native_sound = native_sound
      return native_sound

    self.native_sound = native_sound
    if extra_sound != AudibleAlert.none:
      if extra_sound == self.last_sound and now_ns - self.last_sound_at < COALESCE_NS:
        return AudibleAlert.none
      self.last_sound, self.last_sound_at = extra_sound, now_ns
    return extra_sound
