"""Original carState companions from Card's nonconflating intent transport."""
from dataclasses import replace

from openpilot.cereal import messaging
from openpilot.starpilot.aol.runtime import INTENT_MAX_AGE_NS
from openpilot.starpilot.aol.wire import INTENT_SERVICE, decode_intent

MAX_COMPANIONS = 16
MAX_DRAIN = 32


class IntentCompanion:
  def __init__(self, sock):
    self.sock = sock
    self.samples = {}
    self.latest = None
    self.session = None
    self.sequence = -1
    self.sequence_stamp = 0

  def _observe(self, stamp, valid, raw):
    stamp = int(stamp)
    intent = decode_intent(raw)
    valid = bool(valid and intent is not None and intent.carStateLogMonoTime == stamp)
    previous = self.samples.get(stamp)
    if self.latest is not None and stamp < self.latest[0] and previous is None:
      valid = False
    if intent is not None and (self.latest is None or stamp >= self.latest[0]):
      if self.session is not None and intent.producerSessionId != self.session:
        self.samples.clear()
        self.sequence = -1
        self.sequence_stamp = 0
      self.session = intent.producerSessionId
    if previous is not None:
      valid = bool(valid and previous[1] and previous[2] == intent)
    if valid and intent is not None:
      if (stamp > self.sequence_stamp and intent.producerSessionId == self.session and
          intent.sequence <= self.sequence):
        valid = False
      for other_stamp, other_valid, other in self.samples.values():
        if other_valid and other is not None and other.producerSessionId == intent.producerSessionId and (
            other_stamp < stamp and other.sequence >= intent.sequence or
            other_stamp > stamp and other.sequence <= intent.sequence):
          valid = False
    if valid and intent is not None and (self.latest is None or stamp >= self.latest[0]):
      self.sequence = max(self.sequence, intent.sequence)
      self.sequence_stamp = max(self.sequence_stamp, stamp)
    sample = (stamp, valid, intent)
    self.samples[stamp] = sample
    if self.latest is None or stamp >= self.latest[0]:
      self.latest = sample
    while len(self.samples) > MAX_COMPANIONS:
      del self.samples[min(self.samples)]

  @staticmethod
  def _fresh(sample, now_ns):
    stamp, valid, intent = sample
    return bool(valid and intent is not None and intent.settingsQualified and intent.producerSessionId and
                0 < stamp <= now_ns and now_ns - stamp <= INTENT_MAX_AGE_NS and
                intent.observedMonoTime <= now_ns <= intent.validUntilMonoTime and
                now_ns - intent.observedMonoTime <= INTENT_MAX_AGE_NS)

  def current(self, sm, *, source_ns, now_ns):
    for _ in range(MAX_DRAIN):
      message = messaging.recv_one_or_none(self.sock)
      if message is None:
        break
      self._observe(message.logMonoTime, message.valid, message.aolIntentWire)
    else:
      self.samples.clear()
      if self.latest is not None:
        self.latest = (self.latest[0], False, self.latest[2])
        self.samples[self.latest[0]] = self.latest
      return None
    if sm.seen.get(INTENT_SERVICE, False):
      self._observe(sm.logMonoTime[INTENT_SERVICE], sm.valid.get(INTENT_SERVICE, False), sm[INTENT_SERVICE])
    for stamp in tuple(self.samples):
      if not 0 < stamp <= now_ns or now_ns - stamp > INTENT_MAX_AGE_NS:
        del self.samples[stamp]
    if not (sm.seen.get(INTENT_SERVICE, False) and sm.valid.get(INTENT_SERVICE, False) and
            sm.alive.get(INTENT_SERVICE, False)):
      return None
    pair = self.samples.get(source_ns)
    sm_sample = self.samples.get(int(sm.logMonoTime[INTENT_SERVICE]))
    if pair is None or self.latest is None or sm_sample is None:
      return None
    if not all(self._fresh(sample, now_ns) for sample in (pair, self.latest, sm_sample)):
      return None
    intent = pair[2]
    for sample in (self.latest, sm_sample):
      stamp, _, latest = sample
      if stamp < source_ns or latest.producerSessionId != intent.producerSessionId:
        return None
      intent = replace(intent, allowedLatch=intent.allowedLatch and latest.allowedLatch,
                       pauseLateral=intent.pauseLateral or latest.pauseLateral,
                       pauseLongitudinal=intent.pauseLongitudinal or latest.pauseLongitudinal,
                       lateralArmed=intent.lateralArmed and latest.lateralArmed,
                       optionalSetRelease=intent.optionalSetRelease and latest.optionalSetRelease)
    return intent
