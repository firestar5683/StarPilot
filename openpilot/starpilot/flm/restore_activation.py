"""Restore-only fixed-map declaration; no finite differences or live authority."""

from typing import TypedDict, cast


from dataclasses import asdict, dataclass
import hashlib
import json

from openpilot.starpilot.flm.clipping_quality import (
  FIXED_MAP_IDENTIFICATION, RESTORE_ACTIVATION_VERSION, RESTORE_AGGREGATE_ACTIVATION_VERSION, RESTORE_ZERO_REFERENCE_VERSION,
  restore_policy, restore_quality,
)
from openpilot.starpilot.flm.event_activation import EventActivationPlan, EXACT_EMISSION_ACTIVATION_VERSION, build_activation_plan
from openpilot.starpilot.flm.full_surface_profile import FullSurfaceEnvelope


class _ActivationFields(TypedDict):
  version: str
  identity: str
  baseline_revision: str
  source_epoch: str
  physical_context: str
  calibration_train_blocks: tuple[str, ...]
  calibration_heldout_blocks: tuple[str, ...]
  cutoff_ns: int
  stage_blocks: tuple[str, ...]
  windows: tuple[tuple[int, int, int, int], ...]


def restore_envelope_digest(envelope):
  if type(envelope) is not FullSurfaceEnvelope or envelope.operation != 'restore' or envelope.version != 2:
    raise ValueError('typed full-map historical restore envelope')
  envelope.validate()
  return hashlib.sha256(json.dumps(asdict(envelope), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class WholeMapRestorePlan(EventActivationPlan):
  restore_envelope_sha256: str

  def validate(self):
    versions = (RESTORE_ACTIVATION_VERSION, RESTORE_AGGREGATE_ACTIVATION_VERSION, RESTORE_ZERO_REFERENCE_VERSION)
    if (self.version not in versions or type(self.restore_envelope_sha256) is not str or
        len(self.restore_envelope_sha256) != 64 or any(c not in '0123456789abcdef' for c in self.restore_envelope_sha256)):
      raise ValueError('whole-map restore plan version/envelope')
    # Reuse only the chronology/lineage validator; never decode this as a trial.
    fields = {name: getattr(self, name) for name in EventActivationPlan.__dataclass_fields__}
    EventActivationPlan(**cast(_ActivationFields, {**fields, 'version': EXACT_EMISSION_ACTIVATION_VERSION})).validate()
    return self

  @property
  def clipping_quality(self):
    self.validate()
    return restore_quality(6 if self.version == RESTORE_ZERO_REFERENCE_VERSION else 4)

  @property
  def identification_policy(self):
    self.validate()
    return FIXED_MAP_IDENTIFICATION


def restore_plan_from_dict(value):
  if type(value) is not dict or set(value) != set(WholeMapRestorePlan.__dataclass_fields__):
    raise ValueError('whole-map restore plan report fields')
  copied = dict(value)
  for name in ('calibration_train_blocks', 'calibration_heldout_blocks', 'stage_blocks'):
    copied[name] = tuple(copied[name])
  copied['windows'] = tuple(tuple(row) for row in copied['windows'])
  return WholeMapRestorePlan(**copied).validate()


def restore_plan_matches(plan, envelope):
  return bool(type(plan) is WholeMapRestorePlan and plan.validate() and
    plan.restore_envelope_sha256 == restore_envelope_digest(envelope) and
    plan.baseline_revision == envelope.selected_baseline_revision and plan.source_epoch == envelope.source_epoch)


def build_restore_plan(engine, *, model, cutoff_ns, stage_events, physical_context, envelope, restore_version=4):
  if type(restore_version) is not int or restore_version not in (4, 5, 6):
    raise ValueError('explicit whole-map restore support version')
  policy = restore_policy(restore_version)
  digest = restore_envelope_digest(envelope)
  if engine.restore_envelope is None or restore_envelope_digest(engine.restore_envelope) != digest:
    raise ValueError('whole-map restore declaration changed transaction')
  original = build_activation_plan(engine, model=model, cutoff_ns=cutoff_ns, stage_events=stage_events,
    physical_context=physical_context, quality_contract=restore_quality(restore_version))
  return WholeMapRestorePlan(**{**asdict(original), 'version': policy},
    restore_envelope_sha256=digest).validate()
