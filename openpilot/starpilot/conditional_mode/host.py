"""CEM/CCM proposal host; selfdrived remains the sole effective mode owner."""

from __future__ import annotations

from dataclasses import dataclass

from openpilot.starpilot.conditional_mode.policy import ConditionalModePolicy, Decision, ManualIntent, ModeChoice, ModeSettings
from openpilot.starpilot.conditional_mode.preferences import ManualState, ModeSelection
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner
from openpilot.starpilot.conditional_mode.projection import ConditionalOwnerContext, ObservedBool, ProjectedScene, SOURCE_MAX_AGE_NS, SceneProjector


@dataclass(frozen=True)
class HostProposal:
  choice: ModeChoice
  projected: ProjectedScene | None
  decision: Decision | None
  override_experimental: bool | None
  status: str
  settings_revision: int | None = None


def _fresh_flag(source: ObservedBool | None, *, now_ns: int, barrier_ns: int) -> bool | None:
  if not isinstance(source, ObservedBool) or type(source.value) is not bool or type(source.observed_mono_ns) is not int:
    return None
  if not barrier_ns < source.observed_mono_ns <= now_ns or now_ns - source.observed_mono_ns > SOURCE_MAX_AGE_NS:
    return None
  return source.value


class ConditionalModeHost:
  """One drive/session, no subscriptions, writes, or actuator authority."""

  def __init__(self):
    self.drive_id = 0
    self.choice = ModeChoice.STOCK
    self.projector = SceneProjector()
    self.policy = ConditionalModePolicy()

  def reset(self) -> None:
    self.drive_id = 0
    self.choice = ModeChoice.STOCK
    self.projector = SceneProjector()
    self.policy.reset()

  def sample(
    self,
    sm,
    cp,
    *,
    now_mono_ns: int,
    now_boot_ns: int,
    sample_skew_ns: int,
    drive_id: int,
    selection: ModeSelection | None = None,
    manual: ManualState | None = None,
    safe_mode: ObservedBool | None = None,
    owner_context: ConditionalOwnerContext | None = None,
    selected_t_follow_s: float | None = None,
    selected_t_follow_observed_mono_ns: int | None = None,
    settings_owner: ConditionalSettingsOwner | None = None,
  ) -> HostProposal:
    signal_options = None
    settings_revision = None
    if settings_owner is not None:
      if not isinstance(settings_owner, ConditionalSettingsOwner) or selection is not None or safe_mode is not None:
        self.reset()
        return HostProposal(ModeChoice.STOCK, None, None, None, 'ambiguous_settings_owner')
      snapshot = settings_owner.refresh(now_mono_ns)
      verdict = settings_owner.verdict(snapshot, now_mono_ns=now_mono_ns, drive_id=drive_id)
      settings_revision = verdict.revision
      if verdict.status not in ('ready',) or verdict.selection is None or verdict.safe_mode is None:
        self.reset()
        return HostProposal(ModeChoice.STOCK, None, None, None, verdict.status, settings_revision)
      selection = verdict.selection
      signal_options = verdict.cem
      # Current owner affirmation is configuration authority, not a new
      # observation timestamp for a car/model sensor.
      safe_mode = ObservedBool(verdict.safe_mode, now_mono_ns)
    # Absence and malformed selection preserve selfdrived's existing stock
    # ExperimentalMode owner without even creating a diagnostic override.
    if selection is None:
      self.reset()
      return HostProposal(ModeChoice.STOCK, None, None, None, 'stock', settings_revision)
    if not isinstance(selection, ModeSelection):
      self.reset()
      return HostProposal(ModeChoice.STOCK, None, None, None, 'invalid_selection', settings_revision)
    if selection.choice is ModeChoice.STOCK:
      self.reset()
      return HostProposal(ModeChoice.STOCK, None, None, None, 'stock', settings_revision)
    if (
      not isinstance(selection.choice, ModeChoice)
      or not isinstance(selection.settings, ModeSettings)
      or type(drive_id) is not int
      or drive_id <= 0
      or type(selection.drive_id) is not int
      or selection.drive_id != drive_id
      or type(now_mono_ns) is not int
      or now_mono_ns <= 0
    ):
      self.reset()
      return HostProposal(ModeChoice.STOCK, None, None, None, 'invalid_selection', settings_revision)
    if self.drive_id != drive_id or self.choice is not selection.choice:
      self.reset()
      self.drive_id = drive_id
      self.choice = selection.choice
    safe_value = _fresh_flag(safe_mode, now_ns=now_mono_ns, barrier_ns=self.projector.barrier_mono_ns)
    barrier_before = self.projector.barrier_mono_ns
    projected = self.projector.project(
      sm,
      cp,
      now_mono_ns=now_mono_ns,
      now_boot_ns=now_boot_ns,
      sample_skew_ns=sample_skew_ns,
      safe_mode=safe_value,
      selected_t_follow_s=selected_t_follow_s,
      selected_t_follow_observed_mono_ns=selected_t_follow_observed_mono_ns,
      owner_context=owner_context,
      signal_options=signal_options,
    )
    authority = projected.authority
    manual_valid = (
      isinstance(manual, ManualState)
      and isinstance(manual.intent, ManualIntent)
      and manual.drive_id == drive_id
      and type(manual.observed_mono_ns) is int
      and drive_id <= manual.observed_mono_ns <= now_mono_ns
    )
    if (
      safe_value is None
      or safe_value is True
      or not self.projector.barrier_mono_ns < safe_mode.observed_mono_ns
      or not manual_valid
      or (authority is not None and (not authority.fresh or not authority.system_long_capable or authority.safe_mode))
    ):
      self.policy.reset()
      return HostProposal(selection.choice, projected, None, None, 'authority_unavailable', settings_revision)
    if authority is None:
      # A missing required 100 Hz sample cannot authorize an override. Keep the
      # existing policy hold for a brief transport gap; step() expires it after
      # SCENE_MAX_AGE_S, while explicit unsafe authority above resets it now.
      missing_required = not {'carState', 'carControl', 'selfdriveState'} <= projected.fresh_services
      cp_capable = (type(getattr(cp, 'openpilotLongitudinalControl', None)) is bool
                    and cp.openpilotLongitudinalControl
                    and type(getattr(cp, 'pcmCruise', None)) is bool)
      car_invalid = 'carState' in projected.fresh_services and projected.scene.speed_mps is None
      try:
        control_invalid = 'carControl' in projected.fresh_services and any(
          type(getattr(sm['carControl'], field, None)) is not bool for field in ('longActive', 'latActive'))
        selfdrive_invalid = ('selfdriveState' in projected.fresh_services
                             and type(getattr(sm['selfdriveState'], 'enabled', None)) is not bool)
      except (KeyError, TypeError, ValueError, RuntimeError):
        control_invalid = selfdrive_invalid = True
      if not (missing_required and cp_capable and not (car_invalid or control_invalid or selfdrive_invalid)
              and self.projector.barrier_mono_ns == barrier_before):
        self.policy.reset()
      return HostProposal(selection.choice, projected, None, None, 'authority_unavailable', settings_revision)
    assert manual is not None
    decision = self.policy.step(now_mono_ns / 1e9, selection.choice, manual.intent, authority, projected.scene, selection.settings)
    if not decision.qualified:
      return HostProposal(selection.choice, projected, decision, None, 'invalid_preferences', settings_revision)
    override = decision.requested_experimental if decision.qualified and authority.driving_enabled and authority.long_active else None
    return HostProposal(selection.choice, projected, decision, override, 'proposed' if override is not None else 'inactive_axis', settings_revision)
