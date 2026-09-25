"""Advisory SLC experimental-fallback evidence from one completed planner cycle.

This module does not select a driving mode. The future CEM owner must separately
validate its own authority, preference revision, and scene freshness.
"""

from dataclasses import dataclass
from enum import StrEnum

from openpilot.starpilot.speed_limits import acceptance as acc
from openpilot.starpilot.speed_limits.runtime import Output, Runtime
from openpilot.starpilot.speed_limits.runtime_settings import Settings


class Reason(StrEnum):
  QUALIFIED_ABSENCE = "qualified_absence"
  CURRENT_LIMIT = "current_limit"
  SOURCE_UNKNOWN = "source_unknown"
  SOURCE_STALE = "source_stale"
  DISABLED = "disabled"
  DISPLAY_ONLY = "display_only"
  INVALID_SETTINGS = "invalid_settings"
  OTHER_FALLBACK = "other_fallback"
  INVALID_FALLBACK = "invalid_fallback"
  INCONSISTENT_CYCLE = "inconsistent_cycle"


@dataclass(frozen=True)
class Diagnostic:
  # True is a source-level CEM proposal, never longitudinal permission.
  proposed_experimental: bool | None
  reason: Reason
  observation_kind: acc.ObservationKind | None
  historical_accepted: bool
  pending: bool
  current_control_target_mps: float | None
  effective_cap_mps: float | None
  session_id: str | None
  frame_mono_ns: int | None


def evaluate(output: Output, settings: Settings) -> Diagnostic:
  """Evaluate frozen SLCFallback=1 against a real same-cycle Runtime output.

  0 selects set-speed fallback and 2 selects previous accepted limit in the
  saved setting. This pure projection is for analysis; a live caller should use
  evaluate_runtime to bind the output to the producing Runtime's current state.
  """
  result = output.result
  state = result.state
  selection = result.selection
  decision = result.acceptance
  message = output.message
  record = message.slcState
  accepted = state.acceptance.accepted is not None
  pending = state.acceptance.pending is not None
  target = decision.control_target_mps if decision is not None else None
  cap = result.ceiling.speed_mps if result.ceiling is not None else None
  kind = selection.observation.kind if selection is not None else None

  def diagnostic(proposal: bool | None, reason: Reason) -> Diagnostic:
    return Diagnostic(proposal, reason, kind, accepted, pending, target, cap,
                      state.session_id, state.last_now_ns)

  if not isinstance(settings, Settings) or settings.errors:
    return diagnostic(None, Reason.INVALID_SETTINGS)
  if type(settings.fallback_choice) is not int or settings.fallback_choice not in (0, 1, 2):
    return diagnostic(None, Reason.INVALID_FALLBACK)
  if not settings.enabled:
    return diagnostic(False, Reason.DISPLAY_ONLY if settings.display else Reason.DISABLED)
  if settings.fallback_choice != 1:
    return diagnostic(False, Reason.OTHER_FALLBACK)
  if settings.acceptance.display_only or settings.acceptance.fallback_previous:
    return diagnostic(None, Reason.INCONSISTENT_CYCLE)
  if (result.errors or selection is None or decision is None or decision.errors or selection.errors or
      state.last_now_ns is None or decision.state != state.acceptance or decision.policy != settings.acceptance or
      bool(message.valid) is not True or str(record.sessionId) != state.session_id or
      int(record.frameMonoTime) != state.last_now_ns or int(message.logMonoTime) != state.last_now_ns or
      bool(record.enabled) != settings.enabled or bool(record.displayOnly) or
      str(record.observationKind) != selection.observation.kind.value or
      str(record.source) != (selection.selected_source.value if selection.selected_source is not None else "none") or
      bool(record.hasAccepted) != accepted or bool(record.hasPending) != pending or
      bool(record.hasCeiling) != (result.ceiling is not None) or str(record.status) != result.status):
    return diagnostic(None, Reason.INCONSISTENT_CYCLE)

  if kind is acc.ObservationKind.VALID:
    return diagnostic(False, Reason.CURRENT_LIMIT)
  if kind is acc.ObservationKind.STALE:
    return diagnostic(None, Reason.SOURCE_STALE)
  if kind is not acc.ObservationKind.ABSENT:
    return diagnostic(None, Reason.SOURCE_UNKNOWN)
  # Selection's ABSENT means every considered source was qualified absent (or
  # a valid sign below the minimum). A missing producer remains UNKNOWN.
  if (not selection.considered or selection.selected_source is not None or
      any(unavailable_kind is not acc.ObservationKind.ABSENT for _, unavailable_kind in selection.unavailable) or
      len(selection.unavailable) != len(selection.considered) or
      decision.basis != acc.ObservationKind.ABSENT.value or target is not None or pending or cap is not None):
    return diagnostic(None, Reason.INCONSISTENT_CYCLE)
  return diagnostic(True, Reason.QUALIFIED_ABSENCE)


def evaluate_runtime(runtime: Runtime, output: Output) -> Diagnostic:
  """Give the future mode owner an advisory snapshot for the current SLC tick.

  A prior tick or another Runtime cannot renew fallback. This does not validate
  conditional-mode settings or grant effective longitudinal mode ownership.
  """
  evidence = evaluate(output, runtime.settings)
  if (output.result.state is not runtime.state or output.result.state.session_id != runtime.session_id or
      output.settings is not runtime.settings):
    return Diagnostic(None, Reason.INCONSISTENT_CYCLE, evidence.observation_kind,
                      evidence.historical_accepted, evidence.pending, evidence.current_control_target_mps,
                      evidence.effective_cap_mps, evidence.session_id, evidence.frame_mono_ns)
  return evidence
