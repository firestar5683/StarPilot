"""GM longitudinal tuning on the acceleration interface."""

from dataclasses import dataclass, field
import math

import numpy as np

from opendbc.car.gm.values import (gm_control_word, CAR, GMFlags, GMSafetyFlags, PEDAL_BOLT_CAR, NO_ACC_BOLT_CAR, is_volt_longitudinal,
                                  is_volt_gateway_longitudinal, is_bolt_euv_longitudinal, is_ordinary_ascm_profile, is_ordinary_sdgm_profile)
from opendbc.car.structs import car


REGEN_SPEED = (0.0, 1.5, 4.0, 8.0, 15.0, 30.0)
REGEN_LIMIT = (-0.93, -1.28, -1.98, -2.58, -2.86, -2.95)
PEDAL_KP_BP = (0.0, 5.0, 15.0, 35.0)
PEDAL_KP_V = (0.095, 0.085, 0.065, 0.050)
PEDAL_FEEDFORWARD_GAIN = 0.20


@dataclass(frozen=True)
class PedalStartEvidence:
  drive_id: int
  observed_ns: int
  has_lead: bool
  traffic_mode: bool = False
  custom_acceleration: bool = False
  profile_max_accel: float | None = None


class GMPedalStartPolicy:
  def __init__(self):
    self.reset()

  def reset(self):
    self.handoff_frames = 0
    self.drive_id = None
    self.last_ns = None
    self.release_since_ns = None

  def transition(self, native, previous, active, cs, target, should_stop, evidence):
    states = car.CarControl.Actuators.LongControlState
    valid = (isinstance(evidence, PedalStartEvidence) and active and cs.canValid and not cs.canTimeout and
             not cs.brakePressed and not cs.gasPressed and math.isfinite(target) and math.isfinite(cs.vEgo) and
             evidence.drive_id > 0 and evidence.observed_ns > evidence.drive_id and
             (evidence.profile_max_accel is None or math.isfinite(evidence.profile_max_accel)))
    if not valid:
      self.reset()
      return states.pid if native == states.starting else native
    if (self.drive_id != evidence.drive_id or self.last_ns is None or
        not 0 < evidence.observed_ns - self.last_ns <= 20_000_000):
      self.release_since_ns = None
      self.handoff_frames = 0
    self.drive_id, self.last_ns = evidence.drive_id, evidence.observed_ns
    if should_stop:
      self.release_since_ns = None
      return states.stopping
    if previous == states.stopping:
      immediate = cs.vEgo > 0.35 or (evidence.has_lead and target > 0.15) or (target >= 0.45 and not cs.cruiseState.standstill)
      if target > 0.15:
        if self.release_since_ns is None:
          self.release_since_ns = evidence.observed_ns
      else:
        self.release_since_ns = None
      settled = self.release_since_ns is not None and evidence.observed_ns - self.release_since_ns >= 340_000_000
      return states.starting if immediate or settled else states.stopping
    self.release_since_ns = None
    if previous == states.off:
      return states.starting
    return states.pid if cs.vEgo > 0.35 else previous

  @staticmethod
  def output(target, evidence):
    if evidence.traffic_mode or evidence.custom_acceleration or (evidence.has_lead and target <= 0.25):
      return float(np.clip(target, 0.0, 0.55))
    if evidence.profile_max_accel is not None and evidence.profile_max_accel > 0.0:
      return min(0.55, evidence.profile_max_accel)
    return 0.55

  def handoff_output(self, output, last_output, target, speed, starting_handoff, should_stop, evidence):
    if evidence is None or self.last_ns != evidence.observed_ns:
      self.handoff_frames = 0
      return output
    if starting_handoff:
      self.handoff_frames = 75
    if not (self.handoff_frames > 0 and evidence.has_lead and not should_stop and target > 0.15 and speed < 1.25):
      self.handoff_frames = 0
      return output
    self.handoff_frames -= 1
    speed_floor = float(np.interp(speed, (0.0, 0.5, 1.25), (0.22, 0.18, 0.10)))
    target_floor = min(speed_floor, max(0.0, 0.4 * target))
    return max(output, min(last_output, target_floor))


def _interp(value, points, values):
  return float(np.interp(value, points, values))


@dataclass
class GMPedalLongitudinalPolicy:
  friction_variant: bool
  ignore_cruise_standstill: bool = False
  stopping_decel_rate: float = field(default=0.8, init=False)
  kp: tuple[tuple[float, ...], tuple[float, ...]] = (PEDAL_KP_BP, PEDAL_KP_V)
  last_a_target: float = field(default=0.0, init=False)
  integrator_hold_frames: int = field(default=0, init=False)

  def stopping_output(self, output: float, target: float, should_stop: bool, cs) -> float:
    return _moving_stop_target_follow(output, target, should_stop, cs)

  def reset(self) -> None:
    self.last_a_target = 0.0
    self.integrator_hold_frames = 0

  def prepare_pid(self, pid, target: float, error: float, speed: float,
                  last_output: float, accel_limits: tuple[float, float], *,
                  should_stop: bool = False, has_lead: bool | None = None) -> bool:
    if pid.i > 0.0 and target < -0.05 and error < -0.25 and not (speed <= 0.35 and target > -0.40):
      bleed = _interp(abs(error), (0.25, 0.75, 1.5), (0.55, 0.25, 0.0))
      pid.i *= bleed

    handoff_threshold = _interp(speed, (0.0, 4.0, 12.0, 25.0), (0.35, 0.45, 0.55, 0.70))
    hold_frames = int(round(_interp(speed, (0.0, 4.0, 12.0, 25.0), (25.0, 20.0, 14.0, 10.0))))
    if abs(target - self.last_a_target) > handoff_threshold:
      self.integrator_hold_frames = max(self.integrator_hold_frames, hold_frames)
    self.last_a_target = target
    if self.integrator_hold_frames > 0:
      self.integrator_hold_frames -= 1

    at_neg_sat = last_output <= accel_limits[0] + 0.03
    at_pos_sat = last_output >= accel_limits[1] - 0.03
    sat_pushing_lower = at_neg_sat and error < -0.05
    sat_pushing_upper = at_pos_sat and error > 0.05
    return self.integrator_hold_frames > 0 or sat_pushing_lower or sat_pushing_upper

  def feedforward(self, target: float, speed: float, last_output: float) -> float:
    gain = PEDAL_FEEDFORWARD_GAIN
    if self.friction_variant and target < 0.0:
      regen_limit = _interp(speed, REGEN_SPEED, REGEN_LIMIT)
      restore = 0.0
      if target < regen_limit:
        restore = _interp(regen_limit - target, (0.0, 0.25, 0.75), (0.0, 0.6, 1.0))
      if speed > 5.0 and target < -1.10:
        gap = max(0.0, abs(target) - abs(min(last_output, 0.0)))
        target_restore = _interp(abs(target), (1.1, 1.6, 2.2, 3.0), (0.0, 0.25, 0.55, 1.0))
        gap_restore = _interp(gap, (0.2, 0.6, 1.0, 1.6), (0.0, 0.25, 0.60, 1.0))
        speed_factor = _interp(speed, (5.0, 8.0, 12.0, 18.0), (0.0, 0.35, 0.75, 1.0))
        restore = max(restore, max(target_restore, gap_restore) * speed_factor)
      gain += (1.0 - gain) * float(np.clip(restore, 0.0, 1.0))
    return target * gain

  def shape_output(self, output: float, target: float, error: float, speed: float) -> float:
    if output > 0.0 and target < -0.10 and error < -0.35 and not (speed <= 0.35 and target > -0.40):
      positive_cap = _interp(target, (-1.5, -0.6, -0.1), (0.0, 0.0, 0.05))
      output = min(output, positive_cap)
    if output >= -0.05 or target >= -0.80 or speed <= 5.0:
      return output
    gap = max(0.0, abs(target) - abs(output))
    if self.friction_variant:
      bias = 0.0
      if gap > 0.25:
        speed_factor = _interp(speed, (5.0, 10.0, 15.0, 25.0), (0.0, 0.55, 0.85, 1.0))
        max_bias = _interp(abs(target), (0.8, 1.4, 2.2, 3.5), (0.0, 0.14, 0.42, 0.70))
        bias = min(gap * 0.30, max_bias) * speed_factor
      regen_limit = _interp(speed, REGEN_SPEED, REGEN_LIMIT)
      if target < regen_limit - 0.05:
        friction_request = max(0.0, regen_limit - target)
        if friction_request > 0.10:
          speed_factor = _interp(speed, (5.0, 8.0, 12.0, 18.0, 25.0), (0.0, 0.45, 0.75, 0.90, 1.0))
          demand_factor = _interp(friction_request, (0.10, 0.25, 0.50, 0.90, 1.30), (0.0, 0.22, 0.50, 0.78, 1.0))
          floor = regen_limit - friction_request * float(np.clip(speed_factor * demand_factor, 0.0, 1.0))
          bias = max(bias, output - floor)
      return output - max(bias, 0.0)
    if gap <= 0.40:
      return output
    speed_factor = _interp(speed, (5.0, 12.0, 25.0), (0.0, 0.7, 1.0))
    max_bias = _interp(abs(target), (0.8, 2.0, 3.5), (0.0, 0.10, 0.20))
    return output - min(gap * 0.12, max_bias) * speed_factor


class GMVoltLongitudinalPolicy:
  """Original Volt default law; optional test-ground tunes are excluded."""
  friction_variant = False
  stopping_decel_rate = 1.0
  starting_speed = 0.25
  kp = 0.0

  def __init__(self, gateway: bool = False):
    if gateway:
      self.stopping_decel_rate = 3.0
      self.starting_speed = 0.75

  def stop_policy(self):
    return GMVoltStopPolicy(self.starting_speed)

  def stopping_output(self, output: float, target: float, should_stop: bool, cs) -> float:
    return _moving_stop_target_follow(output, target, should_stop, cs, max(1.5, self.starting_speed + 1.0))

  def reset(self) -> None:
    pass

  def prepare_pid(self, pid, target: float, error: float, speed: float,
                  last_output: float, accel_limits: tuple[float, float], *,
                  should_stop: bool = False, has_lead: bool | None = None) -> bool:
    # Unknown transport must not look like an open road. Only qualified absence
    # permits releasing negative I during settled cruise.
    if (has_lead is False and not should_stop and speed >= 8.0 and
        abs(target) <= 0.12 and abs(error) <= 0.12 and pid.i < 0.0):
      pid.i *= 0.995
    if pid.i > 0.0 and target < -0.05 and error < -0.25 and not (speed <= 0.35 and target > -0.40):
      pid.i *= _interp(abs(error), (0.25, 0.75, 1.5), (0.55, 0.25, 0.0))
    return False

  def feedforward(self, target: float, speed: float, last_output: float) -> float:
    return target

  def shape_output(self, output: float, target: float, error: float, speed: float) -> float:
    if output > 0.0 and target < -0.10 and error < -0.35 and not (speed <= 0.35 and target > -0.40):
      return min(output, _interp(target, (-1.5, -0.6, -0.1), (0.0, 0.0, 0.05)))
    return output


def _moving_stop_target_follow(output: float, target: float, should_stop: bool, cs, min_speed: float = 1.5) -> float:
  if should_stop and not cs.brakePressed and cs.vEgo > min_speed and target < output - 0.25:
    step = _interp(cs.vEgo, (min_speed, 3.0, 6.0, 10.0), (0.02, 0.03, 0.05, 0.07))
    return max(target, output - step)
  return output


@dataclass(frozen=True)
class EuvLongitudinalEvidence:
  drive_id: int
  observed_ns: int
  has_lead: bool


@dataclass(frozen=True)
class VoltStopEvidence:
  drive_id: int
  observed_ns: int
  has_lead: bool


class _GMDefaultStopPolicy:
  """Default stop release with exact owner evidence and starting-speed contracts."""
  def __init__(self, starting_speed: float, evidence_type):
    self.starting_speed = starting_speed
    self.evidence_type = evidence_type
    self.reset()

  def reset(self):
    self.drive_id = None
    self.last_ns = None
    self.release_since_ns = None

  def transition(self, native, previous, active, cs, target, should_stop, evidence):
    states = car.CarControl.Actuators.LongControlState
    if not active:
      self.reset()
      return states.off
    valid = (isinstance(evidence, self.evidence_type) and cs.canValid and not cs.canTimeout and
             not cs.brakePressed and not cs.gasPressed and math.isfinite(target) and math.isfinite(cs.vEgo) and
             evidence.drive_id > 0 and evidence.observed_ns > evidence.drive_id and
             isinstance(evidence.has_lead, bool))
    if not valid:
      self.reset()
      # Missing transport is not evidence of an empty road or permission to leave a stop.
      return states.stopping if previous == states.stopping else native
    if (self.drive_id != evidence.drive_id or self.last_ns is None or
        not 0 < evidence.observed_ns - self.last_ns <= 20_000_000):
      self.release_since_ns = None
    self.drive_id, self.last_ns = evidence.drive_id, evidence.observed_ns
    if should_stop:
      self.release_since_ns = None
      return states.stopping
    if previous != states.stopping:
      self.release_since_ns = None
      return native
    immediate = (cs.vEgo > self.starting_speed or (evidence.has_lead and target > 0.15) or
                 (target >= 0.45 and not cs.cruiseState.standstill))
    if target > 0.15:
      if self.release_since_ns is None:
        self.release_since_ns = evidence.observed_ns
    else:
      self.release_since_ns = None
    settled = self.release_since_ns is not None and evidence.observed_ns - self.release_since_ns >= 340_000_000
    return states.pid if immediate or settled else states.stopping


class GMEuvStopPolicy(_GMDefaultStopPolicy):
  def __init__(self):
    super().__init__(0.25, EuvLongitudinalEvidence)


class GMVoltStopPolicy(_GMDefaultStopPolicy):
  def __init__(self, starting_speed: float):
    super().__init__(starting_speed, VoltStopEvidence)


class GMOrdinaryLongitudinalPolicy:
  """Common ordinary acceleration law; no pedal launch or optional profile shaping."""
  friction_variant = False
  stopping_decel_rate = 1.0
  kp = 0.0

  def reset(self) -> None:
    pass

  def prepare_pid(self, pid, target: float, error: float, speed: float,
                  last_output: float, accel_limits: tuple[float, float], *,
                  should_stop: bool = False, has_lead: bool | None = None) -> bool:
    if pid.i > 0.0 and target < -0.05 and error < -0.25 and not (speed <= 0.35 and target > -0.40):
      pid.i *= _interp(abs(error), (0.25, 0.75, 1.5), (0.55, 0.25, 0.0))
    return False

  def feedforward(self, target: float, speed: float, last_output: float) -> float:
    return target

  def shape_output(self, output: float, target: float, error: float, speed: float) -> float:
    if output > 0.0 and target < -0.10 and error < -0.35 and not (speed <= 0.35 and target > -0.40):
      return min(output, _interp(target, (-1.5, -0.6, -0.1), (0.0, 0.0, 0.05)))
    return output

  def stopping_output(self, output: float, target: float, should_stop: bool, cs) -> float:
    return _moving_stop_target_follow(output, target, should_stop, cs)


class GMEuvLongitudinalPolicy(GMOrdinaryLongitudinalPolicy):
  stop_policy = GMEuvStopPolicy


def euv_policy_for(cp) -> GMEuvLongitudinalPolicy | None:
  return GMEuvLongitudinalPolicy() if is_bolt_euv_longitudinal(cp) else None


def volt_policy_for(cp) -> GMVoltLongitudinalPolicy | None:
  """Admit only the exact restored Volt longitudinal topologies."""
  return GMVoltLongitudinalPolicy(is_volt_gateway_longitudinal(cp)) if is_volt_longitudinal(cp) else None


def policy_for(cp) -> GMPedalLongitudinalPolicy | None:
  """Admit only the already selected, exact GM Bolt interceptor path."""
  try:
    flags = gm_control_word(cp)
    required = int(GMSafetyFlags.PEDAL_LONG | GMSafetyFlags.PADDLE_SCHED)
    candidate = cp.carFingerprint
    return (GMPedalLongitudinalPolicy(candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
                                        ignore_cruise_standstill=candidate in NO_ACC_BOLT_CAR)
            if cp.brand == 'gm' and candidate in PEDAL_BOLT_CAR and
            cp.openpilotLongitudinalControl and not cp.pcmCruise and
            not cp.passive and not cp.dashcamOnly and not cp.notCar and
            int(cp.flags) & int(GMFlags.PEDAL_LONG) and flags & required == required and
            cp.safetyConfigs[0].safetyModel == car.CarParams.SafetyModel.gm and
            (bool(flags & int(GMSafetyFlags.BOLT_ACC_PEDAL)) ==
             (candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL))
            else None)
  except (AttributeError, IndexError, TypeError, ValueError):
    return None


@dataclass(frozen=True)
class AscmStopEvidence:
  drive_id: int
  observed_ns: int
  has_lead: bool


class GMAscmStopPolicy(_GMDefaultStopPolicy):
  def __init__(self):
    super().__init__(0.25, AscmStopEvidence)


class GMAscmLongitudinalPolicy(GMOrdinaryLongitudinalPolicy):
  """Ordinary ASCM acceleration law; no EV-specific settled-cruise recovery."""
  stop_policy = GMAscmStopPolicy


def ascm_policy_for(cp):
  return GMAscmLongitudinalPolicy() if is_ordinary_ascm_profile(cp, longitudinal=True) else None


class GMSdgmLongitudinalPolicy(GMOrdinaryLongitudinalPolicy):
  """Ordinary SDGM acceleration law with the reached vehicle tune."""
  def __init__(self, blazer):
    self.stop_policy = lambda: _GMDefaultStopPolicy(0.35 if blazer else 0.25, AscmStopEvidence)
    self.kp = ((0.0, 4.0, 12.0, 35.0), (0.09, 0.075, 0.055, 0.040)) if blazer else 0.0

def sdgm_policy_for(cp):
  return GMSdgmLongitudinalPolicy(cp.carFingerprint == CAR.CHEVROLET_BLAZER) if is_ordinary_sdgm_profile(cp, longitudinal=True) else None


def volt_sng_release(cp, requested, cc, cs, now_ns, *, plan_current=False):
  sources = getattr(cs, "volt_sng_sources", ())
  current = bool(sources) and all(source > 0 and 0 <= now_ns - source <= limit for source, limit in sources)
  return bool(requested and plan_current and is_volt_longitudinal(cp) and cc.enabled and cc.longActive and
              cc.cruiseControl.resume and cs.out.cruiseState.standstill and
              cs.out.canValid and not cs.out.canTimeout and not cs.out.gasPressed and not cs.out.brakePressed and
              not cs.out.regenBraking and cs.out.gearShifter in (car.CarState.GearShifter.drive, car.CarState.GearShifter.low) and
              current)


def volt_sng_resume_policy_for(cp):
  if not is_volt_longitudinal(cp):
    return None
  return lambda default, requested, fresh: default if not requested else bool(default and fresh)
