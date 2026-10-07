"""Startup admission for saved optional driving features.

This decides which optional owners exist for a drive. It never grants control;
each owner still verifies current vehicle, source, clock, and axis authority.
"""

from collections.abc import Mapping
from dataclasses import replace

from opendbc.car.gm.feature_capabilities import longitudinal_supported as gm_long_supported, display_supported as gm_display_supported

from openpilot.starpilot.conditional_mode.preferences import PreferenceError, decode_preferences
from openpilot.starpilot.aol.intent import independent_axis_requested, read_settings as read_aol_settings
from openpilot.starpilot.aol.vehicle import policy_for as aol_policy_for
from openpilot.starpilot.longitudinal.ioniq6_start import eligible as ioniq6_long_eligible
from openpilot.starpilot.longitudinal.profile_runtime import read_settings as read_profile_settings, selected_profiles_requested, read_global_powertrain_preset
from openpilot.starpilot.longitudinal.profile_preferences import read_document_value
from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.speed_limits.runtime_settings import read_params as read_slc_settings
from openpilot.starpilot.speed_limits.selection import Source


def _read(params, key: str, limit: int = 4096) -> tuple[bytes | None, bool]:
  try:
    return read_saved(params, key, limit)
  except (OSError, TypeError, ValueError):
    return None, False


def requested(params, feature: str, *, include_auxiliary: bool = False) -> bool:
  """Read one feature request, including the readable factory CEM default."""
  if feature == 'conditional':
    raw, document_readable = _read(params, 'ConditionalModeConfig')
    safe, safe_readable = _read(params, 'SafeMode', 8)
    if not document_readable or not safe_readable or safe not in (None, b'0'):
      return False
    if raw is None:
      return True  # Readable absence selects the factory CEM choice.
    try:
      decode_preferences(raw)
      return True  # Stock still owns its optional wheel/session lifecycle.
    except PreferenceError:
      return False
  if feature == 'curve':
    return _read(params, 'CurveSpeedController', 8) == (b'1', True)
  if feature == 'aol':
    master, readable = _read(params, 'AlwaysOnLateral', 8)
    if not readable or master not in (None, b'0', b'1'):
      return False
    return independent_axis_requested(read_aol_settings(params), include_auxiliary=include_auxiliary)
  if feature == 'profile':
    document = read_document_value(params)
    return (read_profile_settings(params) is not None or
            (document.valid and isinstance(document.value, dict) and
             selected_profiles_requested(document.value)))
  if feature in ('slc', 'vision'):
    settings = read_slc_settings(params)
    return (settings.enabled or settings.display) if feature == 'slc' else (
      settings.display and Source.VISION in settings.selection.slots)
  raise ValueError('unknown optional feature')


def enabled(params, cp, feature: str, environment: Mapping[str, str]) -> bool:
  """Preserve explicit replay opt-ins and each vehicle capability."""
  flags = {'conditional': 'CONDITIONAL_MODE_REPLAY_RUNTIME', 'curve': 'CURVE_REPLAY_RUNTIME',
           'aol': 'AOL_REPLAY_RUNTIME',
           'slc': 'SLC_REPLAY_RUNTIME', 'vision': 'SLC_VISION_DEVELOPMENT',
           'profile': 'LONG_PLANNER_REPLAY_RUNTIME'}
  if feature not in flags:
    raise ValueError('unknown optional feature')
  if feature == 'aol':
    policy = aol_policy_for(cp)
    return bool(policy.runtime_supported and
                (environment.get(flags[feature]) == '1' or
                 (policy.normal_runtime_supported and (policy.full_axis_runtime_required or policy.physical_stalk_owner or requested(params, feature,
                    include_auxiliary=policy.intent_supported and not policy.explicit_latch)))))
  if feature == 'vision' and environment.get('SLC_REPLAY_RUNTIME') == '1' and environment.get(flags[feature]) == '1':
    return True
  if feature != 'vision' and environment.get(flags[feature]) == '1':
    return True
  capable = cp is not None and (ioniq6_long_eligible(cp) or
                                (feature in ('conditional', 'curve', 'slc', 'profile') and gm_long_supported(cp)) or
                                (feature in ('slc', 'vision') and gm_display_supported(cp)))
  powertrain_requested = (feature == 'profile' and cp is not None and gm_long_supported(cp) and
                          read_document_value(params).valid and read_global_powertrain_preset(params, cp) is not None)
  return bool(capable and (requested(params, feature) or powertrain_requested))


def slc_runtime_settings(params, cp, environment: Mapping[str, str]):
  """Stock display startup cannot inherit a saved speed-control request."""
  settings = read_slc_settings(params)
  if environment.get('SLC_REPLAY_RUNTIME') != '1' and gm_display_supported(cp) and not gm_long_supported(cp):
    return replace(settings, enabled=False, display=settings.display or settings.enabled, acceptance=replace(settings.acceptance, display_only=True))
  return settings


def vision_control_enabled(params, cp) -> bool:
  """Source selection never turns stock-cruise or display-only sessions into control."""
  settings = read_slc_settings(params)
  return bool(cp is not None and (ioniq6_long_eligible(cp) or gm_long_supported(cp)) and
              settings.enabled and Source.VISION in settings.selection.slots)
