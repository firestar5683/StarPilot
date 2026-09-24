from collections import deque

from openpilot.common.constants import CV
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.latcontrol_vehicle_tunes import IONIQ_6_CARS

# Near-straight highway smoothing of the model's desired curvature.
#
# Once the Ioniq 6 torque tune followed the model ~1:1 (SteerLatAccel 4.0), the remaining
# highway weave was the model's own action.desiredCurvature wobbling at 0.35-1.4 Hz and
# controlsd passing it straight through (corr +0.84..+1.00, drive 00000b20). OEM LFA on the
# same car showed ~half that weave on straights (drive 00000b23), largely by not chasing it.
#
# A first-order low-pass (tau 0.3 s) removes ~1/3 of that band on straights while keeping
# ~94% of the slow 0.1-0.35 Hz lane-keeping content (open-loop replay of af3/b20/b0a/aee).
#
# Gating is on an envelope of the raw commanded lateral accel -- the max over the last
# ENVELOPE_HOLD seconds, with a rate-limited release -- not on the raw value: the smoother
# releases the instant a curve begins (0 ms added onset delay across 51 highway curve onsets,
# zero deviation once |lat accel| > 0.6), but the weave itself cannot modulate the weight at
# its own frequency -- the gain-scheduled-on-the-oscillating-signal mistake behind the 0.67 Hz
# taper limit cycle (drive 00000ade). The window must outlast the spacing between |weave|
# peaks (0.35 Hz -> 1.4 s); a plain linear release sagged between peaks and still swung the
# weight ~5% at the weave frequency.
ENABLED = True                            # A/B switch; restart-only, no rebuild
SMOOTH_TAU = 0.3                          # s
SPEED_OFF = 40.0 * CV.MPH_TO_MS
SPEED_ON = 50.0 * CV.MPH_TO_MS
LAT_ACCEL_ON = 0.25                       # m/s^2, envelope below this: full smoothing
LAT_ACCEL_OFF = 0.6                       # m/s^2, envelope above this: no smoothing
ENVELOPE_HOLD = 2.0                       # s, sliding-max window
ENVELOPE_RELEASE_RATE = 0.3               # m/s^2 per second, after the hold
BYPASS_FADE_RATE = 2.0                    # per second: blinker/override fade in/out over 0.5 s


def _smoothstep(x: float, lo: float, hi: float) -> float:
  t = min(max((x - lo) / (hi - lo), 0.0), 1.0)
  return t * t * (3.0 - 2.0 * t)


class HighwayCurvatureSmoother:
  def __init__(self, CP):
    self.enabled = ENABLED and CP.carFingerprint in IONIQ_6_CARS
    self.alpha = DT_CTRL / (SMOOTH_TAU + DT_CTRL)
    self.reset()

  def reset(self, curvature: float = 0.0) -> None:
    self.filtered = curvature
    self.envelope = 0.0
    self.frame = 0
    self.peaks: deque[tuple[int, float]] = deque()  # monotonic (frame, lat accel) for the sliding max
    self.bypass_weight = 0.0
    self.weight = 0.0

  def update(self, curvature: float, v_ego: float, lat_active: bool, bypass: bool) -> float:
    if not self.enabled or not lat_active:
      self.reset(curvature)
      return curvature

    # The filter always tracks the raw command, so fading back in never steps the output.
    self.filtered += self.alpha * (curvature - self.filtered)

    lat_accel = abs(curvature) * v_ego ** 2
    self.frame += 1
    while self.peaks and self.peaks[-1][1] <= lat_accel:
      self.peaks.pop()
    self.peaks.append((self.frame, lat_accel))
    while self.peaks[0][0] <= self.frame - ENVELOPE_HOLD / DT_CTRL:
      self.peaks.popleft()
    self.envelope = max(self.peaks[0][1], self.envelope - ENVELOPE_RELEASE_RATE * DT_CTRL)

    # Only the bypass part is rate limited: the envelope part is already continuous, and
    # limiting it would keep smoothing into the start of a curve.
    step = BYPASS_FADE_RATE * DT_CTRL
    self.bypass_weight += min(max((0.0 if bypass else 1.0) - self.bypass_weight, -step), step)

    self.weight = (self.bypass_weight * _smoothstep(v_ego, SPEED_OFF, SPEED_ON) *
                   (1.0 - _smoothstep(self.envelope, LAT_ACCEL_ON, LAT_ACCEL_OFF)))
    return curvature + self.weight * (self.filtered - curvature)
