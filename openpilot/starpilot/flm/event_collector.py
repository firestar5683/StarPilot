"""Bounded storage transport for whole-event fitting, using original joins."""
from collections import deque

from openpilot.starpilot.flm.fullrate_collector import FullrateCollector
from openpilot.starpilot.flm.adaptive_profile import replay_accepts


class EventFullrateCollector(FullrateCollector):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # At most5,120 sealed endpoints plus80 current and39 pending;
    # whole events are selected before the
    # child12,000-frame/24-event export budget, never by arbitrary packet tail.
    self.blocks = deque(self.blocks, maxlen=64)
    # At most39 already-qualified endpoints awaiting a storage packet. These
    # never retain an active join, physical freshness or independent episode.
    self._pending_storage = ()
    self._pending_storage_lineage = None
    self._storage_lineage = None
    self.snapshot_attempts = self.snapshot_declines = 0
    self.snapshot_readiness = None
    self.snapshot_readiness_context = None

  def _snapshot_context(self):
    return (self.context, self.physical_context, getattr(self.adapter, 'key', None),
            getattr(getattr(self.adapter, 'envelope', None), 'prior_full_profile_sha256', None))

  def _clear_snapshot_readiness(self):
    self.snapshot_readiness = self.snapshot_readiness_context = None
    self.adapter.snapshot_readiness = None

  def snapshot_readiness_report(self):
    # A rotating objective/source/physical/prior cannot inherit another one's
    # counts during the60-second cooldown. No regroup or source read occurs.
    if self.snapshot_readiness is not None and self.snapshot_readiness_context != self._snapshot_context():
      return {'reason': 'snapshot_context_changed'}
    return dict(self.snapshot_readiness or {'reason': 'snapshot_not_attempted'})

  def _discard_storage(self, reason):
    self._clear_snapshot_readiness()
    self._pending_storage = ()
    self._pending_storage_lineage = None
    self._storage_lineage = None
    super().split(reason, reset=True)

  def _seal_raw(self):
    if len(self._pending_storage) > 39 or len(self.raw_points) > 80:
      self._discard_storage('event_storage_pending_bound')
      return
    lineage = (self.context, self.physical_context, getattr(self.adapter, 'actual_target_sha256', None))
    if self.context is None or self.physical_context is None:
      self._pending_storage = ()
      self._pending_storage_lineage = None
      return
    if self._pending_storage_lineage != lineage:
      # A new source/physical/accepted-target boundary cannot carry old rows.
      self._pending_storage = ()
    rows = self._pending_storage + tuple(self.raw_points)
    previous, seen = None, set()
    if self._storage_lineage == lineage and self.blocks and self.blocks[-1].samples:
      tail = self.blocks[-1].samples[-1]
      previous = tail.control_ns, tail.apply_ns, tail.mono_ns
      seen.add(previous)
    for point in rows:
      clocks = point.control_ns, point.apply_ns, point.mono_ns
      if (any(type(stamp) is not int or stamp <= 0 for stamp in clocks) or
          clocks in seen or previous is not None and
          (clocks[0] < previous[0] or clocks[1] < previous[1] or clocks[2] <= previous[2]) or
          point.physical_context != self.physical_context):
        self._discard_storage('event_storage_lineage_or_chronology')
        return
      seen.add(clocks)
      previous = clocks
    self._pending_storage = ()
    self._pending_storage_lineage = None
    self.raw_points.clear()
    while len(rows) >= 40:
      count = min(80, len(rows))
      self.raw_points.extend(rows[:count])
      # Original packet writer preserves each RawPoint and its original clocks.
      super()._seal_raw()
      rows = rows[count:]
    self._pending_storage = rows  # Immutable remainder, strictly fewer than40.
    self._pending_storage_lineage = lineage if rows else None
    self._storage_lineage = lineage

  def split(self, reason, *, reset=False):
    if reset:
      self._clear_snapshot_readiness()
      self._pending_storage = ()
      self._pending_storage_lineage = None
      self._storage_lineage = None
    else:
      self._seal_raw()
    # Original split still clears ready/current rows/active/physical freshness.
    # Storage is not episode independence: child complete windows decide support.
    super().split(reason, reset=reset)

  def physical(self, value, now_ns):
    accepted = super().physical(value, now_ns)
    if self.sealed:
      # An80-point packet is storage only, never a physical independent event.
      # Keep recording the unmodified chronological trace; child reconstruction
      # alone groups complete cycles/turns into independent fit episodes.
      self.sealed = False
    return accepted

  def _retains_controller_chatter(self, value):
    # Capture the symptom under its existing child TRIAL contract. Original
    # evidence flags and every current/application exclusion remain unchanged.
    from openpilot.starpilot.flm.event_objective import EffectObjective
    try:
      objective = self.adapter.event_objective
      return bool(isinstance(objective, EffectObjective) and
        objective.context_key == value.source_epoch and
        objective.retains_controller_chatter and self.adapter.restore_envelope is None)
    except (AttributeError, TypeError, ValueError):
      return False

  def _accepted_fit_target(self, value):
    """A known accepted result changes collection lineage, not live health."""
    try:
      trace = value.effect_trace
      profile = self.fit_result.profile
      trace.validate()
      previous = self.ready[-1][0]
      return bool(trace.qualified and trace.envelope == profile.effect_envelope and
        replay_accepts(self.fit_validation, profile) and self.physical_context is not None and
        self.context == (value.identity, value.generation, value.domain, value.stage_revision,
          value.response_revision, value.source_epoch, value.controller_mode, value.policy,
          value.baseline_revision, value.controller_revision, value.turn_assist) and
        previous.native_identity == value.native_identity and
        self.adapter.fit_profile == profile)
    except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
      return False

  def _rollover_training(self):
    self._clear_snapshot_readiness()
    # The original active/native/source chronology remains intact. Training
    # endpoints and pending joins cannot cross an accepted target change.
    self.training_interruptions['accepted_full_effect_target_changed'] += 1
    self.controls.clear()
    self.applied.clear()
    self.recent_controls.clear()
    self.recent_applied.clear()
    self.ready.clear()
    self.points.clear()
    self.raw_points.clear()
    self._pending_storage = ()
    self._pending_storage_lineage = None
    self._storage_lineage = None
    self.blocks.clear()
    self.cohort = None
    self.sealed = False
    self.model_block_sequence += 1
    self.model_points = 0
    self.model_sealed = False
    self.fit_block_sequence = self.block_sequence
    self.result = self.last_validation = None
    # Retaining the immutable fit NEVER retains a current physical admission.
    # A genuinely new pose and the normal current controller/native probe are
    # mandatory before the parent can renew its original bounded lease.
    self.last_qualified_response = 0
    self.adapter.current_physical_valid = False
    self.adapter.last_physical_ns = 0

  def control(self, value, now_ns):
    rollover = self.adapter.target_changed
    if rollover:
      if self._accepted_fit_target(value):
        self._rollover_training()
      else:
        self.split('accepted_full_effect_target_changed', reset=True)
      self.adapter.target_changed = False
    accepted = super().control(value, now_ns)
    if rollover and not accepted:
      # Invalid, stale or faulted first-target evidence cannot preserve a fit.
      self.split('unqualified_accepted_target', reset=True)
    return accepted

  def job_snapshot(self, now_ns):
    # Guards are cheap. Whole-event reconstruction stays at the original60s
    # cadence, including unsuccessful selections; reports only reuse its result.
    if self.snapshot_readiness_context != self._snapshot_context():
      self._clear_snapshot_readiness()
    reason = ('no_current_collection_context' if self.context is None else
              'unchanged_storage_since_submission' if self.block_sequence == self.fit_block_sequence else
              'event_storage_packet_support' if len(self.blocks) < 8 else
              'no_current_controller_evidence' if not self.ready else
              'no_current_physical_context' if self.physical_context is None else None)
    if reason is not None:
      self.snapshot_readiness = {'reason': reason, 'storageBlocks': len(self.blocks), 'requiredStorageBlocks': 8}
      self.snapshot_readiness_context = self._snapshot_context()
      return None
    if self.last_fit and now_ns - self.last_fit < 60_000_000_000:
      return None
    control, output = self.ready[-1]
    self.sequence += 1
    self.snapshot_attempts += 1
    self.last_fit = now_ns
    try:
      snapshot = self.adapter.fit_job_snapshot(tuple(self.blocks), now_ns=now_ns, sequence=self.sequence,
        prior=self.prior_coefficients, control=control, output=output, physical_context=self.physical_context)
      self.snapshot_readiness = dict(getattr(self.adapter, 'snapshot_readiness', None) or
        {'reason': 'snapshot_ready' if snapshot is not None else 'event_snapshot_unavailable'})
    except (ValueError, TypeError, OverflowError, MemoryError):
      self.reason = 'event_snapshot_unavailable'
      self.snapshot_readiness = dict(getattr(self.adapter, 'snapshot_readiness', None) or {})
      self.snapshot_readiness['reason'] = self.reason
      snapshot = None
    if snapshot is None:
      self.snapshot_declines += 1
    self.snapshot_readiness_context = self._snapshot_context()
    self.snapshot_readiness.update(observedMonoTime=now_ns, objective=str(getattr(self.adapter, 'key', ''))[:128])
    return snapshot
