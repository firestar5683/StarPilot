"""Optional, source-timed lane-change follow adjustment within the native MPC range."""

import math
from dataclasses import dataclass

from openpilot.starpilot.lateral.lane_change_preferences import LaneChangePolicy, read_saved

MAX_SOURCE_AGE_NS = 250_000_000
MAX_MODEL_GAP_NS = 150_000_000
RAMP_IN_PER_SECOND = 0.6
RAMP_OUT_PER_SECOND = 4.0
LEAD_BRAKE_ABORT_MPS2 = 0.8


@dataclass(frozen=True)
class GapFrame:
  now_ns: int
  model_ns: int
  car_ns: int
  radar_ns: int
  authority_stamps: tuple[int, int, int]
  speed_mps: float
  lane_state: str
  direction: str
  standstill: bool
  left_blindspot: bool
  right_blindspot: bool
  lead_present: bool
  lead_accel_mps2: float
  force_decel: bool
  gas_pressed: bool
  brake_pressed: bool
  model_should_stop: bool


def project(sm, now_ns: int) -> GapFrame | None:
  try:
    if type(now_ns) is not int or now_ns <= 0:
      return None
    for name in ('modelV2', 'carState', 'radarState', 'carControl', 'controlsState', 'selfdriveState'):
      stamp = sm.logMonoTime[name]
      if (sm.valid[name] is not True or sm.alive[name] is not True or type(stamp) is not int or
          stamp <= 0 or stamp > now_ns or now_ns - stamp > MAX_SOURCE_AGE_NS):
        return None
    car = sm['carState']
    leads = (sm['radarState'].leadOne, sm['radarState'].leadTwo)
    present = tuple(lead for lead in leads if lead.present)
    lead_accelerations = tuple(float(lead.aLeadK) for lead in present)
    if not all(math.isfinite(acceleration) for acceleration in lead_accelerations):
      return None
    if not car.canValid or car.canTimeout:
      return None
    return GapFrame(now_ns, sm.logMonoTime['modelV2'], sm.logMonoTime['carState'], sm.logMonoTime['radarState'],
                    tuple(sm.logMonoTime[name] for name in ('carControl', 'controlsState', 'selfdriveState')),
                    float(car.vEgo), str(sm['modelV2'].meta.laneChangeState),
                    str(sm['modelV2'].meta.laneChangeDirection), bool(car.standstill),
                    bool(car.leftBlindspot), bool(car.rightBlindspot), bool(present),
                    min(lead_accelerations, default=0.0),
                    bool(sm['controlsState'].forceDecel), bool(car.gasPressed), bool(car.brakePressed),
                    bool(sm['modelV2'].action.shouldStop))
  except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
    return None


class LaneChangeGap:
  def __init__(self):
    self.last_model_ns: int | None = None
    self.last_policy: LaneChangePolicy | None = None
    self.ramped_follow: float | None = None

  def reset(self) -> None:
    self.last_model_ns = None
    self.last_policy = None
    self.ramped_follow = None

  def step(self, policy: LaneChangePolicy | None, frame: GapFrame | None, *, base_follow: float,
           long_active: bool) -> float | None:
    if (policy is None or not policy.enabled or not policy.close_gap or long_active is not True or frame is None or
        type(policy.minimum_speed_mps) not in (int, float) or not math.isfinite(policy.minimum_speed_mps) or
        policy.minimum_speed_mps < 0 or type(policy.close_gap_seconds) not in (int, float) or
        not math.isfinite(policy.close_gap_seconds) or not 0.75 <= policy.close_gap_seconds <= 1.0 or
        frame.force_decel or frame.gas_pressed or frame.brake_pressed or frame.model_should_stop or
        type(base_follow) not in (int, float) or not math.isfinite(base_follow) or not 0.75 <= base_follow <= 3.0 or
        type(frame.speed_mps) not in (int, float) or not math.isfinite(frame.speed_mps) or
        not math.isfinite(frame.lead_accel_mps2)):
      self.reset()
      return None
    if (type(frame.now_ns) is not int or any(type(stamp) is not int or not 0 < stamp <= frame.now_ns or
                                           frame.now_ns - stamp > MAX_SOURCE_AGE_NS
                                           for stamp in (frame.model_ns, frame.car_ns, frame.radar_ns,
                                                         *frame.authority_stamps))):
      self.reset()
      return None
    same_policy = self.last_policy == policy
    previous = self.last_model_ns if same_policy else None
    if (previous is not None and not 0 < frame.model_ns - previous <= MAX_MODEL_GAP_NS):
      self.reset()
      return None
    if not same_policy:
      self.reset()
    self.last_policy = policy
    self.last_model_ns = frame.model_ns
    current = min(base_follow, self.ramped_follow if self.ramped_follow is not None else base_follow)
    if (frame.standstill or (frame.direction == 'left' and frame.left_blindspot) or
        (frame.direction == 'right' and frame.right_blindspot) or
        (frame.lead_present and max(0.0, -frame.lead_accel_mps2) >= LEAD_BRAKE_ABORT_MPS2)):
      self.reset()
      return None
    safe = (frame.lane_state in ('preLaneChange', 'laneChangeStarting', 'laneChangeFinishing') and
            frame.direction in ('left', 'right') and
            frame.speed_mps >= policy.minimum_speed_mps and
            not frame.standstill)
    target = min(base_follow, policy.close_gap_seconds) if safe else base_follow
    dt = 0.0 if previous is None else (frame.model_ns - previous) / 1e9
    rate = RAMP_IN_PER_SECOND if target < current else RAMP_OUT_PER_SECOND
    step = rate * dt
    self.ramped_follow = min(base_follow, min(max(target, current - step), current + step))
    return self.ramped_follow if self.ramped_follow < base_follow else None


class LaneGapPreferences:
  REFRESH_NS = 1_000_000_000
  MAX_AGE_NS = 2_000_000_000

  def __init__(self, params):
    self.params = params
    self.policy: LaneChangePolicy | None = None
    self.last_attempt_ns = -self.REFRESH_NS
    self.last_success_ns = -1

  def sample(self, now_ns: int) -> LaneChangePolicy | None:
    if type(now_ns) is not int or now_ns <= 0:
      self.policy = None
      self.last_success_ns = -1
      self.last_attempt_ns = -self.REFRESH_NS
      return None
    if now_ns < self.last_attempt_ns:
      self.policy = None
      self.last_success_ns = -1
      self.last_attempt_ns = now_ns - self.REFRESH_NS
    if now_ns - self.last_attempt_ns >= self.REFRESH_NS:
      self.last_attempt_ns = now_ns
      saved = read_saved(self.params)
      self.policy = saved.policy if saved.readable and saved.valid and saved.policy.close_gap else None
      self.last_success_ns = now_ns if saved.readable else -1
    return self.policy if self.last_success_ns > 0 and now_ns - self.last_success_ns <= self.MAX_AGE_NS else None
