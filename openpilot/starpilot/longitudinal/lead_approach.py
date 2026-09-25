"""Rate-limited following-distance buffer for approaching leads."""

from dataclasses import dataclass
import math

from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState


SOURCES = ('modelV2', 'carState', 'radarState', 'carControl', 'controlsState', 'selfdriveState')
MAX_SOURCE_AGE_NS = 250_000_000
MAX_MODEL_GAP_NS = 150_000_000
TRIGGER_TIME = 4.5
FULL_TIME = 1.5
MAX_DELTA = 0.162
MAX_CLOSING_SPEED = 6.0
MAX_LEAD_BRAKE = 2.5
MIN_CLOSING_SPEED = 0.75
MIN_LEAD_BRAKE = 0.2
WINDOW_MIN = 6.0
WINDOW_GAIN = 0.35
RATE_UP = 1.0
RATE_DOWN = 0.60
VISION_MAX_EXTRA_DELTA = 0.216
VISION_SLOW_LEAD_SPEED = 20.0
VISION_GAP_BUFFER_MIN = 8.0
VISION_GAP_BUFFER_GAIN = 0.35
VISION_MIN_MODEL_PROB = 0.85
COMFORT_BRAKE = 2.5
STOP_DISTANCE = 6.0


@dataclass(frozen=True)
class LeadApproachKey:
  settings_fingerprint: str
  drive_id: int


@dataclass(frozen=True)
class ApproachLead:
  status: bool
  radar: bool
  model_prob: float
  distance: float
  speed: float
  acceleration: float


@dataclass(frozen=True)
class ApproachFrame:
  now_ns: int
  model_ns: int
  speed: float
  lead: ApproachLead | None


def _clip(value: float, low: float, high: float) -> float:
  return min(max(value, low), high)


def _valid_key(key: LeadApproachKey | None) -> bool:
  return (type(key) is LeadApproachKey and type(key.settings_fingerprint) is str and
          bool(key.settings_fingerprint) and type(key.drive_id) is int and key.drive_id > 0)


def _valid_lead(lead: ApproachLead | None) -> bool:
  return (lead is None or (type(lead) is ApproachLead and type(lead.status) is bool and
          type(lead.radar) is bool and all(type(value) in (float, int) and math.isfinite(value) for value in
                                          (lead.model_prob, lead.distance, lead.speed, lead.acceleration)) and
          0.0 <= lead.model_prob <= 1.0 and lead.distance >= 0.0))


def project(sm, cp, now_ns: int, key: LeadApproachKey | None) -> ApproachFrame | None:
  try:
    if not _valid_key(key) or key is None or type(now_ns) is not int or now_ns <= key.drive_id:
      return None
    for name in SOURCES:
      stamp = sm.logMonoTime[name]
      if (sm.valid[name] is not True or sm.alive[name] is not True or type(stamp) is not int or
          not key.drive_id < stamp <= now_ns or now_ns - stamp > MAX_SOURCE_AGE_NS):
        return None
    car = sm['carState']
    if (cp.openpilotLongitudinalControl is not True or cp.passive is not False or cp.dashcamOnly is not False or
        cp.notCar is not False or sm['carControl'].longActive is not True or
        sm['selfdriveState'].enabled is not True or sm['controlsState'].longControlState == LongCtrlState.off or
        car.canValid is not True or car.canTimeout is not False or car.gasPressed or car.brakePressed or
        car.standstill or sm['controlsState'].forceDecel or sm['modelV2'].action.shouldStop):
      return None
    lead_one = sm['radarState'].leadOne
    lead = (ApproachLead(bool(lead_one.present), bool(lead_one.radar), float(lead_one.modelProb),
                         float(lead_one.dRel), float(lead_one.vLead), float(lead_one.aLeadK))
            if lead_one.present else None)
    speed = float(car.vEgo)
    if not math.isfinite(speed) or speed < 0 or not _valid_lead(lead):
      return None
    return ApproachFrame(now_ns, sm.logMonoTime['modelV2'], speed, lead)
  except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
    return None


class LeadApproach:
  def __init__(self, nominal_dt: float = 0.05, actuator_delay: float = 0.0):
    if (not all(type(value) in (float, int) and math.isfinite(value) and value >= 0 for value in
                (nominal_dt, actuator_delay)) or nominal_dt <= 0):
      raise ValueError('Invalid lead approach timing')
    self.nominal_dt = float(nominal_dt)
    self.actuator_delay = float(actuator_delay)
    self.reset()

  def reset(self) -> None:
    self.key: LeadApproachKey | None = None
    self.previous: ApproachFrame | None = None
    self.effective: float | None = None

  def _target(self, lead: ApproachLead | None, speed: float, base_follow: float) -> float:
    target = base_follow
    if lead is not None and lead.status and (lead.radar or lead.model_prob >= VISION_MIN_MODEL_PROB):
      lead_brake = max(0.0, -lead.acceleration)
      closing_speed = max(0.0, speed - lead.speed)
      if closing_speed >= MIN_CLOSING_SPEED or lead_brake >= MIN_LEAD_BRAKE:
        desired_gap = speed ** 2 / (2 * COMFORT_BRAKE) + base_follow * speed + STOP_DISTANCE - lead.speed ** 2 / (2 * COMFORT_BRAKE)
        approach_window = max(WINDOW_MIN, WINDOW_GAIN * speed)
        if lead.distance <= desired_gap + approach_window:
          reaction_t = max(self.actuator_delay, self.nominal_dt)
          projected_closing_speed = closing_speed + 0.5 * lead_brake * reaction_t
          gap_to_follow = max(lead.distance - desired_gap, 0.0)
          time_to_follow = gap_to_follow / max(projected_closing_speed, 0.1)
          time_factor = _clip((TRIGGER_TIME - time_to_follow) / (TRIGGER_TIME - FULL_TIME), 0.0, 1.0)
          closing_factor = _clip(closing_speed / MAX_CLOSING_SPEED, 0.0, 1.0)
          brake_factor = _clip(lead_brake / MAX_LEAD_BRAKE, 0.0, 1.0)
          target_delta = MAX_DELTA * _clip(0.55 * time_factor + 0.25 * closing_factor + 0.20 * brake_factor, 0.0, 1.0)
          if not lead.radar:
            gap_deficit = max(desired_gap - lead.distance, 0.0)
            gap_buffer = max(VISION_GAP_BUFFER_MIN, VISION_GAP_BUFFER_GAIN * speed)
            gap_factor = _clip(gap_deficit / gap_buffer, 0.0, 1.0)
            slow_lead_factor = _clip((VISION_SLOW_LEAD_SPEED - lead.speed) / VISION_SLOW_LEAD_SPEED, 0.0, 1.0)
            vision_extra = VISION_MAX_EXTRA_DELTA * _clip(
              0.40 * time_factor + 0.30 * gap_factor + 0.20 * slow_lead_factor + 0.10 * closing_factor, 0.0, 1.0)
            target_delta += vision_extra
          target = base_follow + target_delta
    return min(3.0, target)

  def step(self, key: LeadApproachKey | None, frame: ApproachFrame | None, base_follow: float,
           blocked: bool = False) -> float | None:
    if (not _valid_key(key) or key is None or type(frame) is not ApproachFrame or blocked is not False or
        type(base_follow) not in (float, int) or not math.isfinite(base_follow) or not 0.75 <= base_follow <= 3.0 or
        type(frame.now_ns) is not int or type(frame.model_ns) is not int or
        not key.drive_id < frame.model_ns <= frame.now_ns or frame.now_ns - frame.model_ns > MAX_SOURCE_AGE_NS or
        type(frame.speed) not in (float, int) or not math.isfinite(frame.speed) or frame.speed < 0 or
        not _valid_lead(frame.lead)):
      self.reset()
      return None
    if key != self.key:
      self.reset()
    previous = self.previous
    if previous is not None and (not 0 < frame.model_ns - previous.model_ns <= MAX_MODEL_GAP_NS or
                                 not 0 < frame.now_ns - previous.now_ns <= MAX_MODEL_GAP_NS):
      self.reset()
      return None
    dt = self.nominal_dt if previous is None else (frame.model_ns - previous.model_ns) / 1e9
    self.key = key
    self.previous = frame
    current = max(base_follow, self.effective if self.effective is not None else base_follow)
    target = self._target(frame.lead, frame.speed, base_follow)
    rate = RATE_UP if target > current else RATE_DOWN
    self.effective = max(base_follow, _clip(target, current - rate * dt, current + rate * dt))
    return self.effective if self.effective > base_follow else None
