"""GM live FLM source binding; numerical overlay only, never axis authority."""
import math
import time

from openpilot.starpilot.flm.torque_surface import GmSurface as GmSurface, SurfaceInput
from openpilot.starpilot.saved_source import read_saved


def gm_capability(cp, controller):
  from openpilot.starpilot.lateral.controller_selection import policy_for
  from openpilot.starpilot.lateral.torque_runtime import gm_manual_supported_cp
  from openpilot.starpilot.lateral.bolt_policy import BOLT_GENERATIONS
  if controller not in ('standard', 'starpilot') or not gm_manual_supported_cp(cp):
    return None
  policy = policy_for(cp)
  if policy is None:
    return None
  tune = cp.lateralTuning.torque
  # Rich Bolt stages belong to its selected custom law. STANDARD retains its
  # standard law plus the neutral universal surface rather than importing a
  # rich default law from a different selected controller.
  profile = ('gm_bolt_2022_2023' if controller == 'starpilot' and policy == 'bolt' and
             BOLT_GENERATIONS[cp.carFingerprint] == 2022 else 'torque_universal')
  return {'fingerprint': str(cp.carFingerprint), 'controller': str(controller), 'policy': policy,
          'basis': (float(tune.latAccelFactor), float(tune.latAccelOffset), float(tune.friction)), 'profile': profile}


def binding_matches(profile, capability):
  return (profile is not None and capability is not None and profile.basis == capability['basis'] and
          profile.flm is not None and profile.flm.controller == capability['controller'] and
          profile.flm.policy == capability['policy'] and profile.flm.basis == capability['basis'] and
          all(surface.profile == capability['profile'] for _, _, surface in profile.flm.saved))


class GmLiveSource:
  def __init__(self, cp, controller, params=None):
    self.cp = cp
    self.capability = gm_capability(cp, controller)
    if params is None and self.capability is not None:
      from openpilot.common.params import Params
      params = Params()
    self.params = params
    self.surface = None
    self.last_ns = None

  def sample(self, *, active, speed, now_ns=None):
    from openpilot.starpilot.lateral.controller_selection import DOCUMENT_KEY as SELECTION_KEY, selection_from_bytes
    from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, MAX_DOCUMENT_BYTES, parse_document
    now_ns = time.monotonic_ns() if now_ns is None else now_ns
    if not active or self.capability is None:
      self.surface = None
      self.last_ns = None
      return None
    if type(now_ns) is not int or now_ns <= 0 or self.last_ns is not None and now_ns < self.last_ns:
      self.surface = None
      self.last_ns = None
      return None
    if self.last_ns is not None and now_ns - self.last_ns < 1_000_000_000:
      return self._frame_surface(speed)
    self.last_ns = now_ns
    self.surface = None
    # Complete reader, no prefix, global legacy keys, bootstrap or writer.
    raw, readable = read_saved(self.params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    if not readable or raw is None:
      return None
    try:
      selected_raw, selected_readable = read_saved(self.params, SELECTION_KEY, 4096)
      selected = selection_from_bytes(self.cp, selected_raw) if selected_readable else None
      if selected is None or selected.source == 'invalid' or str(selected.mode) != self.capability['controller']:
        return None
      profiles = parse_document(raw)
      profile = profiles.get(self.capability['fingerprint'])
      if binding_matches(profile, self.capability):
        self.surface = profile.flm.selected()
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
      pass
    return self._frame_surface(speed)

  def _frame_surface(self, speed):
    if self.surface is None or not math.isfinite(speed) or not 0. <= speed <= 90.:
      return None
    try:
      self.surface.base_threshold(speed)
    except (ValueError, OverflowError):
      return None
    return self.surface


def frame(surface, cs, setpoint, jerk, output=0., desired_angle=0., actual_angle=0.):
  if surface is None:
    return None
  try:
    return SurfaceInput(float(cs.vEgo), float(setpoint), float(jerk), float(desired_angle), float(actual_angle),
                        float(output), bool(cs.steeringPressed), 1.)
  except (ValueError, OverflowError, TypeError):
    return None


def deadband(surface, speed):
  return 0. if surface is None or not math.isfinite(speed) or not 0. <= speed <= 90. else surface.deadband(speed)


def base_threshold(surface, speed, fallback):
  if surface is None or surface.base_values is None:
    return fallback
  try:
    return surface.base_threshold(speed)
  except (ValueError, OverflowError):
    return fallback


def scaled_threshold(surface, speed, threshold, source_base):
  if surface is None or surface.base_values is None:
    return threshold
  candidate = (threshold / source_base) * base_threshold(surface, speed, source_base)
  return candidate if math.isfinite(candidate) and candidate > 0. else threshold


def stages(surface, cs, setpoint, jerk, ff, threshold, *, rich=False, rich_input=None):
  sample = frame(surface, cs, setpoint, jerk)
  if sample is None:
    return ff, threshold
  try:
    return surface.stages(sample, ff if rich_input is None else rich_input, threshold, rich=rich)
  except (ValueError, OverflowError):
    return ff, threshold


def angle_assist(surface, cs, vm, params, curvature, setpoint, jerk, output):
  if surface is None or cs.steeringPressed:
    return output
  try:
    desired = math.degrees(vm.get_steer_from_curvature(-curvature, cs.vEgo, params.roll))
    actual = cs.steeringAngleDeg - params.angleOffsetDeg
  except (ValueError, OverflowError, TypeError):
    return output
  sample = frame(surface, cs, setpoint, jerk, output, desired, actual)
  if sample is None:
    return output
  return surface.angle_assist(sample)
