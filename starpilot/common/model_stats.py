"""Passive, stdlib-only measurement policy v2. No Params or control writes.

Total distance is assisted forward distance only. Rates are exposure / episode
count, not averages of completed intervals. Unknown intervals are never bridged.
"""
from dataclasses import asdict, dataclass
import json
import math

DEFINITION_VERSION = 2
MAX_GAP = 0.25
RELEASE_SECONDS = 2.0
COUNTERS = ('assistedMeters', 'interventionMeters', 'disengagementMeters',
            'interventions', 'disengagements', 'steering', 'brake', 'gas')


def empty_stats(status='not_started'):
  return dict.fromkeys(COUNTERS, 0) | {'available': status == 'ok', 'status': status,
                                    'incomplete': False, 'milesPerIntervention': None, 'milesPerDisengagement': None}


def measurement_policy(state):
  """Untagged historical snapshots used v1; unknown policies stay unknown."""
  version = state.get('definitionVersion', 1)
  release = state.get('interventionReleaseSeconds', 0.5)
  if type(version) is int and type(release) in (int, float) and (version, release) in ((1, 0.5), (2, 2.0)):
    return (version, release)
  return None


def apply_definition_policy(stats, policies):
  policies = set(policies)
  known = policies - {None}
  comparable = len(policies) == 1 and None not in policies
  status = ('unknown' if not policies or None in policies else 'mixed' if len(policies) > 1
            else 'current' if next(iter(policies))[0] == DEFINITION_VERSION else 'historical')
  stats.update(definitionVersions=sorted(p[0] for p in known), definitionStatus=status,
               definitionVersion=next(iter(policies))[0] if comparable else None,
               interventionReleaseSeconds=next(iter(policies))[1] if comparable else None,
               eventRatesComparable=comparable)
  return stats


def rates(stats):
  for count, distance, field in [('interventions', 'interventionMeters', 'milesPerIntervention'),
                                ('disengagements', 'disengagementMeters', 'milesPerDisengagement')]:
    stats[field] = stats[distance] / 1609.344 / stats[count] if stats[count] and stats.get('eventRatesComparable', True) else None
  return stats


def parse_identity(text):
  """Only accept output provenance, never model-selection Params."""
  try:
    if not isinstance(text, str) or len(text) > 4096:
      return None
    obj = json.loads(text)
    roles = obj['roles']
    if obj['version'] != 1 or not isinstance(roles, list) or not 1 <= len(roles) <= 2:
      return None
    for role in roles:
      if not isinstance(role, dict):
        return None
      if not all(isinstance(role.get(k), str) and 0 < len(role[k]) <= 512
                 for k in ('modelId', 'artifact', 'backend')):
        return None
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))
  except (ValueError, TypeError, KeyError):
    return None


@dataclass(frozen=True)
class Sample:
  t: float
  owner: str | None
  speed: float
  enabled: bool = False
  aol: bool = False
  lat: bool = False
  long: bool = False
  steering: bool = False
  brake: bool = False
  gas: bool = False
  valid: bool = True
  reverse: bool = False
  onroad: bool = True

  @property
  def inputs(self):
    return {k for k in ('steering', 'brake', 'gas') if getattr(self, k)}

  @property
  def mode(self):
    return 'full' if self.enabled else ('aol' if self.aol else 'manual')

  @property
  def session(self):
    return self.enabled or self.aol

  @property
  def assisted(self):
    return self.session and (self.lat or self.long)

  @property
  def usable(self):
    return (self.valid and self.onroad and self.owner is not None and not self.reverse
            and math.isfinite(self.t) and math.isfinite(self.speed) and 0 <= self.speed <= 100)


class Reducer:
  def __init__(self):
    self.previous = None
    self.metrics = {}
    self.gaps = 0
    self.episode = None
    self.release_at = None
    self.blocked = True
    self.sequence = 0
    self.last_t = None
    self.in_gap = False

  def row(self, owner, mode):
    key = (owner, mode)
    return self.metrics.setdefault(key, dict.fromkeys(COUNTERS, 0))

  def break_stream(self):
    if not self.in_gap:
      self.gaps += 1
      self.sequence += 1  # semantic revision, not telemetry freshness
    self.in_gap = True
    self.previous = None
    self.episode = None
    self.release_at = None
    self.blocked = True

  def update(self, sample):
    p = self.previous
    if not math.isfinite(sample.t) or (self.last_t is not None and sample.t <= self.last_t):
      return  # duplicate/out-of-order samples must not reset edge detection
    self.last_t = sample.t
    self.sequence += 1
    if not sample.usable:
      self.break_stream()
      return
    if p is not None and sample.t - p.t > MAX_GAP:
      self.break_stream()
      p = None
    if p is None:
      self.previous = sample
      self.blocked = bool(sample.inputs)
      self.in_gap = False
      return

    same_owner = sample.owner == p.owner
    # Never charge an ambiguous model switch interval or takeover to fallback.
    if same_owner:
      row = self.row(p.owner, p.mode)
      distance = (sample.t - p.t) * (sample.speed + p.speed) / 2
      if p.assisted:
        row['assistedMeters'] += distance
        if not self.episode and not p.inputs and not self.blocked:
          row['interventionMeters'] += distance
      if p.session:
        row['disengagementMeters'] += distance
      if p.enabled and not sample.enabled:
        row['disengagements'] += 1
      elif not p.enabled and p.aol and not sample.enabled and not sample.aol:
        row['disengagements'] += 1
    else:
      self.gaps += 1
      self.episode = None
      self.release_at = None
      self.blocked = bool(sample.inputs)

    if sample.inputs:
      self.release_at = None
      rising = sample.inputs - p.inputs
      if not self.episode and not self.blocked and rising and same_owner:
        if p.session or sample.session:
          owner_mode = (p.owner, p.mode) if p.session else (sample.owner, sample.mode)
          self.episode = (owner_mode, set())
          self.row(*owner_mode)['interventions'] += 1
        else:
          self.blocked = True  # input begun manually cannot become an intervention
      if self.episode:
        owner_mode, types = self.episode
        for kind in sample.inputs - types:
          self.row(*owner_mode)[kind] += 1
        types.update(sample.inputs)
    elif self.episode or self.blocked:
      if self.release_at is None:
        self.release_at = sample.t
      if sample.t - self.release_at >= RELEASE_SECONDS:
        self.episode = None
        self.blocked = False
        self.release_at = None
    self.previous = sample

  def snapshot(self):
    return {'definitionVersion': DEFINITION_VERSION, 'interventionReleaseSeconds': RELEASE_SECONDS,
            'sequence': self.sequence, 'gaps': self.gaps, 'lastTime': self.last_t,
            'previous': asdict(self.previous) if self.previous else None,
            'blocked': self.blocked, 'releaseAt': self.release_at,
            'episode': [list(self.episode[0]), sorted(self.episode[1])] if self.episode else None,
            'metrics': [{'owner': owner, 'mode': mode, **values} for (owner, mode), values in self.metrics.items()]}
