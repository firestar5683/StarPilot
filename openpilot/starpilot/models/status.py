"""Pure projection of requested model, loaded identity, and fresh modeld output."""

from dataclasses import dataclass
from enum import StrEnum

from openpilot.starpilot.models.catalog import BUNDLED_CURRENT, BY_ID, resolve_selection


OUTPUT_MAX_AGE_NS = 250_000_000


class ModelHealth(StrEnum):
  UNAVAILABLE = "unavailable"
  LOADING = "loading"
  IDENTITY_UNAVAILABLE = "identity-unavailable"
  ACTIVE = "active"
  STALE = "stale"
  FAILED = "failed"


class ModelVariant(StrEnum):
  SMALL = "small"
  CHESTNUT = "chestnut"


@dataclass(frozen=True)
class ModelProcess:
  pid: int
  start_ticks: int
  running: bool


@dataclass(frozen=True)
class ModelLoad:
  """Identity recorded only after ModelState has loaded and initialized a runner."""
  pid: int
  process_start_ticks: int
  loaded_mono_ns: int
  model_id: str
  variant: ModelVariant
  artifact_sha256: str
  fallback_reason: str | None = None


@dataclass(frozen=True)
class ModelOutput:
  model_v2_mono_ns: int
  model_v2_valid: bool
  driving_data_mono_ns: int
  driving_data_valid: bool
  model_v2_big: bool
  chestnut_active: bool | None


@dataclass(frozen=True)
class ModelStatus:
  requested_id: str
  loaded_id: str | None
  variant: ModelVariant | None
  health: ModelHealth
  pending_next_start: bool
  fallback_reason: str | None
  artifact_sha256: str | None


def project_status(requested_id: str | None, process: ModelProcess | None, load: ModelLoad | None,
                   output: ModelOutput | None, now_mono_ns: int) -> ModelStatus:
  """Keep saved intent distinct from actual modeld identity and output health.

  The caller must obtain process and load records from the same owner. A stale
  load receipt cannot make a new modeld process appear active. An output older
  than the load boundary cannot establish health after a restart.
  """
  requested = resolve_selection(requested_id).model_id
  if not isinstance(now_mono_ns, int) or isinstance(now_mono_ns, bool) or now_mono_ns <= 0:
    raise ValueError("invalid model-status clock")

  if process is None or not process.running or process.pid <= 0:
    return ModelStatus(requested, None, None, ModelHealth.UNAVAILABLE, False, None, None)
  if process.start_ticks <= 0:
    return ModelStatus(requested, None, None, ModelHealth.IDENTITY_UNAVAILABLE, False, None, None)
  output_is_fresh = (output is not None and output.model_v2_valid and output.driving_data_valid and
                     all(isinstance(stamp, int) and not isinstance(stamp, bool) and 0 < stamp <= now_mono_ns and
                         now_mono_ns - stamp <= OUTPUT_MAX_AGE_NS
                         for stamp in (output.model_v2_mono_ns, output.driving_data_mono_ns)))
  if load is None:
    health = ModelHealth.IDENTITY_UNAVAILABLE if output_is_fresh else ModelHealth.LOADING
    return ModelStatus(requested, None, None, health, False, None, None)
  if (load.pid != process.pid or load.process_start_ticks != process.start_ticks or
      load.loaded_mono_ns <= 0 or load.loaded_mono_ns > now_mono_ns or
      load.model_id not in BY_ID or not isinstance(load.variant, ModelVariant) or
      not isinstance(load.artifact_sha256, str) or len(load.artifact_sha256) != 64 or
      any(c not in "0123456789abcdef" for c in load.artifact_sha256)):
    health = ModelHealth.IDENTITY_UNAVAILABLE if output_is_fresh else ModelHealth.LOADING
    return ModelStatus(requested, None, None, health, False, None, None)

  if load.model_id != BUNDLED_CURRENT and BY_ID[load.model_id].uses_external_gpu != (load.variant is ModelVariant.CHESTNUT):
    return ModelStatus(requested, None, None, ModelHealth.IDENTITY_UNAVAILABLE, False, None, None)
  pending = requested != load.model_id
  common = (requested, load.model_id, load.variant, pending, load.fallback_reason, load.artifact_sha256)
  if output is None:
    return ModelStatus(common[0], common[1], common[2], ModelHealth.LOADING, *common[3:])
  stamps = (output.model_v2_mono_ns, output.driving_data_mono_ns)
  if (any(not isinstance(stamp, int) or isinstance(stamp, bool) or stamp < load.loaded_mono_ns or stamp > now_mono_ns
          for stamp in stamps) or
      not output.model_v2_valid or not output.driving_data_valid):
    return ModelStatus(common[0], common[1], common[2], ModelHealth.STALE, *common[3:])
  if any(now_mono_ns - stamp > OUTPUT_MAX_AGE_NS for stamp in stamps):
    return ModelStatus(common[0], common[1], common[2], ModelHealth.STALE, *common[3:])
  if output.model_v2_big != (load.variant is ModelVariant.CHESTNUT):
    return ModelStatus(common[0], common[1], common[2], ModelHealth.FAILED, *common[3:])
  return ModelStatus(common[0], common[1], common[2], ModelHealth.ACTIVE, *common[3:])
