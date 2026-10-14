"""Optional learner-only current native health; no Card/Controls revalidation."""


def current_native_health(sm, cp, control, now_ns):
  try:
    from openpilot.starpilot.flm.runtime_adapter_registry import current_authority

    allowed, state, identity = current_authority(sm, cp, now_ns=now_ns, required=control.native_required)
    if not control.native_required:
      return bool(allowed)
    return bool(
      allowed
      and state is not None
      and control.native_allowed
      and 0 < control.native_observed_ns <= control.control_ns <= now_ns <= control.native_expires_ns
      and identity == control.native_identity
    )
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return False


def current_ford_native_health(sm, cp, row, now_ns):
  """Original same-call public-native witness belongs to emitted announced CC."""
  try:
    from openpilot.starpilot.flm.runtime_adapter_registry import current_ford_authority

    allowed, identity = current_ford_authority(sm, cp, now_ns=now_ns)
    return bool(
      allowed
      and row.native_allowed
      and row.native_identity
      and identity == row.native_identity
      and 0 < row.native_observed_ns <= row.native_validated_ns <= row.event_ns <= now_ns <= row.native_expires_ns
      and row.native_command_ns == row.announced_control_ns
      and row.native_command_ns > 0
    )
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return False
