"""Source-bound low-speed stop and launch-assist evidence for Conditional Chill.

This module only reports scene evidence. It never selects a driving mode or
reads a service, Params, or vehicle signal on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from openpilot.common.realtime import DT_MDL


MPH_TO_MPS = 0.44704
LOW_SPEED_STOP_MAX_MPS = 18.0 * MPH_TO_MPS
LAUNCH_EXIT_MPS = 15.0 * MPH_TO_MPS
LAUNCH_ENTRY_MAX_MPS = 1.0
MAX_SOURCE_AGE_S = 0.25
MAX_FRAME_GAP_S = 2.0 * DT_MDL


@dataclass(frozen=True)
class ChillLead:
  present: bool | None
  distance_m: float | None = None
  speed_mps: float | None = None
  relative_speed_mps: float | None = None  # Raw lead.vRel; never inferred from vLead - vEgo.
  accel_mps2: float | None = None


@dataclass(frozen=True)
class ChillSceneFrame:
  observed_mono_s: float
  model_tick_mono_s: float
  now_mono_s: float
  speed_mps: float | None
  lead: ChillLead | None
  tracking_lead: bool | None
  raw_model_stopped: bool | None
  model_stopped: bool | None
  stop_light_model_detected: bool | None
  stop_light_detected: bool | None
  stop_sign_confirmed: bool | None
  forcing_stop: bool | None
  red_light: bool | None
  plan_forcing_stop: bool | None
  should_stop: bool | None
  allow_throttle: bool | None
  selfdrive_enabled: bool | None


@dataclass(frozen=True)
class ChillSceneObservation:
  low_speed_stop_scene: bool | None
  launch_candidate: bool | None
  forced_exit: bool
  launch_status: str | None  # "speed" or "lead" when candidate is true.
  speed_reason: str | None
  lead_reason: str | None


def _finite(value: object, low: float, high: float) -> float | None:
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    return None
  try:
    number = float(value)
  except (OverflowError, ValueError):
    return None
  return number if math.isfinite(number) and low <= number <= high else None


def _bool(value: object) -> bool | None:
  return value if type(value) is bool else None


class ChillSceneDetector:
  """One model-tick launch latch with immediate frozen exit conditions."""

  def __init__(self):
    self.reset()

  def reset(self) -> None:
    self.launch_active = False
    self.last_model_tick_mono_s: float | None = None

  @staticmethod
  def _low_speed_stop(frame: ChillSceneFrame, speed: float, lead: ChillLead | None) -> bool | None:
    if speed >= LOW_SPEED_STOP_MAX_MPS:
      return False
    if frame.raw_model_stopped or frame.model_stopped or frame.stop_light_model_detected:
      return True
    lead_stop = None
    if lead is not None and _bool(lead.present) is not None:
      if not lead.present:
        lead_stop = False
      else:
        distance = _finite(lead.distance_m, 0.0, 500.0)
        lead_speed = _finite(lead.speed_mps, -30.0, 100.0)
        if distance is not None and lead_speed is not None:
          lead_stop = distance < max(40.0, speed * 4.5) and lead_speed < max(6.0, speed + 0.5)
    if lead_stop:
      return True
    if (any(_bool(value) is None for value in (
      frame.raw_model_stopped, frame.model_stopped, frame.stop_light_model_detected,
    )) or lead_stop is None):
      return None
    return False

  @staticmethod
  def _eligible(frame: ChillSceneFrame, speed: float, lead: ChillLead, active: bool) -> tuple[bool, str, str]:
    if speed > LAUNCH_ENTRY_MAX_MPS and not active:
      return False, "above_entry_speed", "not_evaluated"
    if not frame.selfdrive_enabled:
      return False, "selfdrive_disabled", "not_evaluated"
    if (frame.stop_light_detected or frame.stop_light_model_detected or frame.raw_model_stopped or
        frame.model_stopped or frame.stop_sign_confirmed or frame.forcing_stop or frame.red_light or
        frame.plan_forcing_stop):
      return False, "stop_scene", "not_evaluated"
    if frame.should_stop or not frame.allow_throttle:
      return False, "longitudinal_stop", "not_evaluated"
    if not lead.present and not frame.tracking_lead:
      return True, "go", "no_lead"
    assert lead.speed_mps is not None and lead.relative_speed_mps is not None and lead.accel_mps2 is not None
    lead_delta = lead.speed_mps - speed
    closing_speed = max(0.0, speed - lead.speed_mps)
    departing = (
      lead.speed_mps >= 0.35 and lead_delta >= 0.2 and lead.relative_speed_mps >= 0.2 and
      lead.accel_mps2 >= 0.08 and max(0.0, -lead.accel_mps2) <= 0.2 and closing_speed <= 0.75
    )
    return departing, "go" if departing else "lead_not_departing", "departing" if departing else "not_departing"

  def step(self, frame: ChillSceneFrame) -> ChillSceneObservation:
    unknown = ChillSceneObservation(None, None, self.launch_active, None, "unavailable", "unavailable")
    observed = _finite(frame.observed_mono_s, 0.0, 1e12)
    tick = _finite(frame.model_tick_mono_s, 0.0, 1e12)
    now = _finite(frame.now_mono_s, 0.0, 1e12)
    speed = _finite(frame.speed_mps, 0.0, 80.0)
    lead = frame.lead
    if (observed is None or tick is None or now is None or
        not 0.0 <= now - observed <= MAX_SOURCE_AGE_S or not observed <= tick <= now or speed is None):
      self.reset()
      return unknown
    if self.last_model_tick_mono_s is not None:
      elapsed = tick - self.last_model_tick_mono_s
      if elapsed <= 0.0 or elapsed > MAX_FRAME_GAP_S:
        self.reset()
        return unknown
    self.last_model_tick_mono_s = tick
    low_speed_stop = self._low_speed_stop(frame, speed, lead)
    launch_inputs = (
      frame.raw_model_stopped, frame.model_stopped,
      frame.stop_light_model_detected, frame.stop_light_detected,
      frame.stop_sign_confirmed, frame.forcing_stop, frame.red_light,
      frame.plan_forcing_stop, frame.should_stop, frame.allow_throttle,
      frame.selfdrive_enabled,
    )
    if (lead is None or _bool(lead.present) is None or
        (not lead.present and _bool(frame.tracking_lead) is None) or
        any(_bool(value) is None for value in launch_inputs)):
      forced_exit = self.launch_active
      self.launch_active = False
      return ChillSceneObservation(low_speed_stop, None, forced_exit, None, "unavailable", "unavailable")
    if lead.present or frame.tracking_lead:
      if (_finite(lead.distance_m, 0.0, 500.0) is None or
          _finite(lead.speed_mps, -30.0, 100.0) is None or
          _finite(lead.relative_speed_mps, -100.0, 100.0) is None or
          _finite(lead.accel_mps2, -20.0, 20.0) is None):
        forced_exit = self.launch_active
        self.launch_active = False
        return ChillSceneObservation(low_speed_stop, None, forced_exit, None, "unavailable", "unavailable")
    if self.launch_active and speed >= LAUNCH_EXIT_MPS:
      self.launch_active = False
      return ChillSceneObservation(low_speed_stop, False, True, None, "exit_speed", "not_evaluated")
    eligible, speed_reason, lead_reason = self._eligible(frame, speed, lead, self.launch_active)
    if self.launch_active and not eligible:
      self.launch_active = False
      return ChillSceneObservation(low_speed_stop, False, True, None, speed_reason, lead_reason)
    self.launch_active = eligible
    status = ("lead" if lead.present or frame.tracking_lead else "speed") if eligible else None
    return ChillSceneObservation(low_speed_stop, eligible, False, status, speed_reason, lead_reason)
