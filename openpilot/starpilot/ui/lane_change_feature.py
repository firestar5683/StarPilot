"""Native saved Lane Change Assist rows and source-bound edits."""

from collections.abc import Callable
from dataclasses import replace
import json
import math
import os
import stat

from openpilot.common.constants import CV
from openpilot.starpilot.lateral.lane_change_preferences import (
  KEY, MAX_BYTES, MAX_SPEED_MPS, LaneChangePolicy, SavedLaneChange, read_saved, to_value,
)
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.ui.feature_settings_state import FeatureRow, FeatureSettingsRequest


ENABLED = "lane_change:enabled"
SPEED = "lane_change:speed"
ONE = "lane_change:one"
AUTO = "lane_change:auto"
DELAY = "lane_change:delay"
WIDTH = "lane_change:width"
CLOSE = "lane_change:close_gap"
GAP = "lane_change:close_gap_seconds"
PACE = "lane_change:pace"
RESET = "lane_change:reset"
KEYS = frozenset((ENABLED, SPEED, ONE, AUTO, DELAY, WIDTH, CLOSE, GAP, PACE, RESET))


def _unit_source(params) -> tuple[bytes | None, bool]:
  try:
    fd = os.open(params.get_param_path("IsMetric"), os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
  except FileNotFoundError:
    return None, True
  except (AttributeError, OSError, TypeError, ValueError):
    return None, False
  try:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
      return None, False
    raw = os.read(fd, 3)
  except OSError:
    return None, False
  finally:
    os.close(fd)
  return raw, raw in (b"0", b"1")


class LaneChangeFeature:
  def __init__(self, params, authority: Callable[[str], bool], fingerprint: Callable[[], str | None], vehicle_params: Callable[[], object | None]):
    self.params = params
    self.authority = authority
    self.fingerprint = fingerprint
    self.vehicle_params = vehicle_params

  def capability(self) -> tuple | None:
    cp = self.vehicle_params()
    try:
      if cp is None or cp.notCar or cp.passive or cp.dashcamOnly or not cp.carFingerprint:
        return None
      return (str(cp.carFingerprint), str(cp.brand), str(cp.steerControlType),
              bool(cp.notCar), bool(cp.passive), bool(cp.dashcamOnly), bool(cp.openpilotLongitudinalControl),
              str(cp.carVin) if getattr(cp, "carVin", None) else None)
    except (AttributeError, TypeError, ValueError):
      return None

  def rows(self, parked: bool) -> list[FeatureRow]:
    saved = read_saved(self.params)
    unit_raw, unit_valid = _unit_source(self.params)
    metric = unit_raw == b"1"
    unit = "km/h" if metric else "mph"
    multiplier = 3.6 if metric else 1 / CV.MPH_TO_MS
    capable = self.capability()
    allowed = capable is not None and self.authority("lane_change") and saved.readable
    fingerprint = self.fingerprint()
    common = FeatureRow("", "", "", source=saved.raw, vehicle_fingerprint=fingerprint, capability=capable)
    if not saved.valid:
      reason = "Saved preference cannot be read" if not saved.readable else "Invalid saved preferences; restore defaults"
      return [replace(common, key=RESET, label="Restore Lane Change defaults", value="StarPilot driver-nudged behavior",
                      available=parked and allowed and self.authority("parked_preferences"), reason=reason)]
    policy = saved.policy
    cp = self.vehicle_params()
    long_available = cp is not None and cp.openpilotLongitudinalControl is True
    inactive = "Saved for the next drive; driver nudge and blindspot checks remain available"
    speed = round(policy.minimum_speed_mps * multiplier, 3)
    return [replace(common, key=PACE, label="Lane Change Speed", value=str(round(1.0 + (8.0 - policy.duration_s) * 9.0 / 5.0, 2)),
                    step=1.0, minimum=1.0, maximum=10.0, unit="", available=allowed,
                    reason="Higher values change lanes more quickly; lower values make steering gentler. This does not change the delay after signaling."),
            replace(common, key=ENABLED, label="Allow lane changes", value="On" if policy.enabled else "Off",
                    choices=("Off", "On"), available=allowed, reason=inactive),
            replace(common, key=SPEED, label="Minimum lane-change speed", value=str(speed), step=1.0, minimum=0.0,
                    maximum=math.floor(MAX_SPEED_MPS * multiplier * 1000) / 1000,
                    unit=unit if unit_valid else "", available=allowed and unit_valid,
                    reason=inactive if unit_valid else "Saved speed units unavailable",
                    dependencies=(("IsMetric", unit_raw),), display_unit=unit if unit_valid else ""),
            replace(common, key=ONE, label="One change per signal", value="On" if policy.one_per_signal else "Off",
                    choices=("Off", "On"), available=allowed, reason=inactive),
            replace(common, key=AUTO, label="Automatic Lane Changes", value="On" if policy.auto_lane_change else "Off",
                    choices=("Off", "On"), available=allowed,
                    reason="Saved for the next drive; requires an enabled automatic-steering setup. Otherwise, a driver nudge is required."),
            replace(common, key=DELAY, label="Automatic lane-change delay", value=str(round(policy.auto_delay_s, 1)),
                    step=0.1, minimum=0.0, maximum=5.0, unit="s", available=allowed,
                    reason="Time to wait after signaling before an automatic lane change; lane and blindspot checks still apply"),
            replace(common, key=WIDTH, label="Minimum adjacent lane width", value=str(round(policy.minimum_lane_width_m / 0.3048, 1)),
                    step=0.1, minimum=0.0, maximum=15.0, unit="ft", available=allowed,
                    reason="Minimum detected adjacent lane width for an automatic lane change; narrower or uncertain lanes require a driver nudge"),
            replace(common, key=CLOSE, label="Close lane-change gap", value="On" if policy.close_gap else "Off",
                    choices=("Off", "On"), available=allowed and long_available,
                    reason="Temporarily reduces following time during a lane change when the lane and lead gap are clear; requires StarPilot speed control"),
            replace(common, key=GAP, label="Lane-change follow gap", value=str(round(policy.close_gap_seconds, 2)),
                    step=0.05, minimum=0.75, maximum=1.0, unit="s", available=allowed and long_available,
                    reason="Following time while Close lane-change gap is active. Higher values leave more space; returns to the normal gap afterward.")]

  def _fresh(self, request: FeatureSettingsRequest) -> SavedLaneChange | None:
    if (not request.vehicle_fingerprint or self.fingerprint() != request.vehicle_fingerprint or
        request.capability is None or self.capability() != request.capability or not self.authority("lane_change")):
      return None
    if request.key == RESET and not self.authority("parked_preferences"):
      return None
    saved = read_saved(self.params)
    if not saved.readable or saved.raw != request.expected:
      return None
    if request.key == SPEED:
      raw, valid = _unit_source(self.params)
      if not valid or request.dependencies != (("IsMetric", raw),) or request.display_unit != ("km/h" if raw == b"1" else "mph"):
        return None
    return saved

  @staticmethod
  def _desired(saved: SavedLaneChange, request: FeatureSettingsRequest) -> LaneChangePolicy | None:
    if request.key == RESET:
      return LaneChangePolicy() if not saved.valid and request.value == "confirm" else None
    if not saved.valid:
      return None
    if request.key in (ENABLED, ONE, AUTO, CLOSE) and request.value in ("On", "Off"):
      field = {ENABLED: "enabled", ONE: "one_per_signal", AUTO: "auto_lane_change", CLOSE: "close_gap"}[request.key]
      return replace(saved.policy, **{field: request.value == "On"})
    if request.key == PACE:
      try:
        value = float(request.value)
      except ValueError:
        return None
      return replace(saved.policy, duration_s=8.0 - (value - 1.0) * 5.0 / 9.0) if math.isfinite(value) and 1.0 <= value <= 10.0 else None
    if request.key == GAP:
      try:
        value = float(request.value)
      except ValueError:
        return None
      return replace(saved.policy, close_gap_seconds=value) if math.isfinite(value) and 0.75 <= value <= 1.0 else None
    if request.key in (DELAY, WIDTH):
      try:
        value = float(request.value)
      except ValueError:
        return None
      if math.isfinite(value) and 0 <= value <= (5 if request.key == DELAY else 15):
        return replace(saved.policy, **{("auto_delay_s" if request.key == DELAY else "minimum_lane_width_m"):
                                        value if request.key == DELAY else value * 0.3048})
    if request.key == SPEED:
      try:
        value = float(request.value)
      except ValueError:
        return None
      mps = value / 3.6 if request.display_unit == "km/h" else value * CV.MPH_TO_MS
      if math.isfinite(mps) and 0 <= mps <= MAX_SPEED_MPS:
        return replace(saved.policy, minimum_speed_mps=mps)
    return None

  def apply(self, request: FeatureSettingsRequest) -> bool:
    if request.key not in KEYS or not request.confirmation:
      return False
    if request.key == RESET and not self.authority("parked_preferences"):
      return False
    def authorized() -> bool:
      if request.key in (CLOSE, GAP):
        cp = self.vehicle_params()
        if cp is None or cp.openpilotLongitudinalControl is not True:
          return False
      return self._fresh(request) is not None

    if not authorized():
      return False
    saved = self._fresh(request)
    if saved is None:
      return False
    desired = self._desired(saved, request)
    if desired is None:
      return False
    try:
      raw = json.dumps(to_value(desired), separators=(",", ":"), sort_keys=True, allow_nan=False).encode()
    except (OverflowError, TypeError, ValueError):
      return False
    return commit_exact(self.params, key=KEY, max_bytes=MAX_BYTES, raw=raw, expected=request.expected,
                        authorized=authorized, temp_prefix=".lane-change-").verified
