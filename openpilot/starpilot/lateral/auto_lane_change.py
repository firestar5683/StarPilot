"""Development-only Auto Lane Change qualification from one model frame."""

import math
import time
from dataclasses import replace

from openpilot.cereal import log
from openpilot.starpilot.lateral.adjacent_lane_evidence import adjacent_lane_available
from openpilot.starpilot.lateral.lane_change_preferences import LaneChangePolicy


MODEL_MAX_AGE_NS = 150_000_000  # camera EOF uses CLOCK_BOOTTIME
CAR_MAX_AGE_NS = 100_000_000
CONTROL_MAX_AGE_NS = 100_000_000
CALIBRATION_MAX_AGE_NS = 750_000_000
CLOCK_PAIR_MAX_SKEW_NS = 1_000_000


class ClockEpochGuard:
  """After a suspend offset jump, require new inputs in the resumed epoch."""

  def __init__(self, now_mono_ns: int, now_boot_ns: int, sample_skew_ns: int = 0):
    self.offset_ns = now_boot_ns - now_mono_ns
    self.sample_skew_ns = sample_skew_ns
    self.barrier_mono_ns = now_mono_ns if sample_skew_ns > CLOCK_PAIR_MAX_SKEW_NS else 0

  def ready(self, sm, now_mono_ns: int, now_boot_ns: int, sample_skew_ns: int = 0) -> bool:
    if sample_skew_ns < 0 or sample_skew_ns > CLOCK_PAIR_MAX_SKEW_NS:
      return False
    offset = now_boot_ns - now_mono_ns
    if abs(offset - self.offset_ns) > max(CLOCK_PAIR_MAX_SKEW_NS, sample_skew_ns + self.sample_skew_ns):
      self.offset_ns = offset
      self.sample_skew_ns = sample_skew_ns
      self.barrier_mono_ns = now_mono_ns
      return False
    self.sample_skew_ns = sample_skew_ns
    if self.barrier_mono_ns:
      try:
        services = ("carState", "carControl", "extrinsicsCalibration")
        if any(int(sm.logMonoTime[name]) <= self.barrier_mono_ns or
               int(sm.recv_time[name] * 1e9) <= self.barrier_mono_ns for name in services):
          return False
      except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
        return False
      self.barrier_mono_ns = 0
    return True


def session_policy(saved: LaneChangePolicy, development_opt_in: bool) -> LaneChangePolicy:
  """Modeld calls once at startup; saved On never implies running Auto."""
  return saved if development_opt_in else replace(saved, auto_lane_change=False)


def boottime_ns() -> int:
  return time.clock_gettime_ns(getattr(time, "CLOCK_BOOTTIME", time.CLOCK_MONOTONIC))


def paired_clocks_ns() -> tuple[int, int, int]:
  mono_before = time.monotonic_ns()
  boot = boottime_ns()
  mono_after = time.monotonic_ns()
  return (mono_before + mono_after) // 2, boot, mono_after - mono_before


def _fresh_submaster(sm, service: str, now_mono_ns: int, limit_ns: int) -> bool:
  try:
    observed = int(sm.logMonoTime[service])
    return (sm.seen[service] and sm.alive[service] and sm.valid[service] and
            0 < observed <= now_mono_ns and now_mono_ns - observed <= limit_ns - CLOCK_PAIR_MAX_SKEW_NS)
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return False


def current_calibration(sm, now_mono_ns: int) -> bool:
  if not _fresh_submaster(sm, "extrinsicsCalibration", now_mono_ns, CALIBRATION_MAX_AGE_NS):
    return False
  try:
    calibration = sm["extrinsicsCalibration"]
    return (calibration.calStatus == log.ExtrinsicsCalibration.Status.calibrated and
            len(calibration.rpyCalib) == 3 and all(math.isfinite(float(v)) for v in calibration.rpyCalib))
  except (AttributeError, TypeError, ValueError, OverflowError):
    return False


def auto_evidence(sm, model, direction: int, minimum_width_m: float, *, now_mono_ns: int,
                  now_boot_ns: int, model_valid: bool, vehicle_capable: bool) -> bool:
  """Qualify only the just-filled model, with each clock in its own domain."""
  try:
    if not model_valid or not vehicle_capable or int(model.frameAge) > 1:
      return False
    eof = int(model.timestampEof)
    if not 0 < eof <= now_boot_ns or now_boot_ns - eof > MODEL_MAX_AGE_NS:
      return False
    if not (_fresh_submaster(sm, "carState", now_mono_ns, CAR_MAX_AGE_NS) and
            _fresh_submaster(sm, "carControl", now_mono_ns, CONTROL_MAX_AGE_NS) and
            current_calibration(sm, now_mono_ns)):
      return False
    control = sm["carControl"]
    car_state = sm["carState"]
    return (bool(control.enabled and control.latActive and car_state.canValid and not car_state.canTimeout) and
            adjacent_lane_available(model, direction, minimum_width_m))
  except (AttributeError, TypeError, ValueError, OverflowError):
    return False
