"""Selected-vehicle canonical manual snapshots for FLM trials."""

def manual_snapshot(profile, fingerprint):
  from dataclasses import replace
  from openpilot.starpilot.lateral.torque_settings import serialize_document
  # A trial owns canonical per-vehicle intent, not any global preference.
  return serialize_document({fingerprint: replace(profile, flm=None)}).decode('utf-8')


def manual_profile(raw, fingerprint, basis):
  from openpilot.starpilot.lateral.torque_settings import parse_document, bounds, gain_bounds
  if type(raw) is not str or len(raw.encode('utf-8')) > 4096:
    raise ValueError('Malformed FLM manual snapshot')
  profiles = parse_document(raw.encode('utf-8'))
  if set(profiles) != {fingerprint}:
    raise ValueError('Wrong FLM manual vehicle')
  profile = profiles[fingerprint]
  if profile.flm is not None or profile.basis != basis:
    raise ValueError('Wrong FLM manual basis')
  for name in ('factor', 'friction'):
    choice = getattr(profile, name)
    if choice.mode == 'custom':
      low, high = bounds(basis, name, fingerprint=fingerprint)
      if not low <= choice.custom_value <= high:
        raise ValueError('Out-of-range FLM manual choice')
  if profile.gain_basis is not None:
    if profile.gain_basis.torque_basis != basis:
      raise ValueError('Wrong FLM gain basis')
    low, high = gain_bounds(fingerprint, profile.gain_basis)
    if profile.proportional_gain.mode == 'custom':
      value = profile.proportional_gain.custom_value
      if value is None or not low <= value <= high:
        raise ValueError('Out-of-range FLM gain')
  return profile


def manual_preconditions(params, cp, controller, profile):
  from openpilot.starpilot.lateral.gm_geometry_runtime import geometry_basis
  from openpilot.starpilot.lateral.torque_supported import BOLT_VEHICLES
  from openpilot.starpilot.saved_source import read_saved
  reasons = []
  if profile.gain_basis is not None:
    from openpilot.starpilot.lateral.torque_settings import GainBasis
    if controller == 'starpilot':
      table = ((0,), (.6,))
    else:
      from openpilot.selfdrive.controls.lib.latcontrol_torque import INTERP_SPEEDS, KP_INTERP
      table = (tuple(INTERP_SPEEDS), tuple(KP_INTERP))
    tune = cp.lateralTuning.torque
    expected = GainBasis(controller, table, (tune.latAccelFactor, tune.latAccelOffset, tune.friction))
    if profile.gain_basis != expected:
      raise ValueError('Wrong FLM selected gain basis')
  if profile.geometry is not None and profile.geometry.basis != geometry_basis(cp):
    raise ValueError('Wrong FLM geometry basis')
  if str(cp.carFingerprint) in BOLT_VEHICLES and profile.proportional_gain.mode == 'custom':
    advanced, readable = read_saved(params, 'AdvancedLateralTune', 64)
    if not readable or advanced != b'1':
      reasons.append('Enable Advanced Lateral Tune in settings before applying this saved custom KP. FLM does not change that preference.')
  if profile.geometry is not None and profile.geometry.learning == 'force_auto':
    off, readable = read_saved(params, 'ForceAutoTuneOff', 1)
    if not readable or off not in (None, b'0', b'1'):
      reasons.append('Force Auto Tune Off is unreadable; resolve that preference before applying this tune.')
    elif off == b'1':
      reasons.append('Force Auto Tune Off remains enabled and takes precedence. Disable it explicitly in settings to use this saved Force Auto choice.')
  return reasons
