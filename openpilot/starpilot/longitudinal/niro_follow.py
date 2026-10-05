"""First-generation Niro EV far-follow output comfort, with urgent bypass."""
import math

from opendbc.car.hyundai.values import CAR

SOURCE_MAX_AGE_NS = 250_000_000
SOURCES = ('carState', 'carControl', 'controlsState', 'selfdriveState', 'radarState', 'modelV2')


def eligible(cp):
  return bool(cp.brand == 'hyundai' and cp.carFingerprint == CAR.KIA_NIRO_EV and cp.openpilotLongitudinalControl and
              not cp.passive and not cp.dashcamOnly and not cp.notCar)


def close_fast(lead, speed, follow):
  closing = max(0., speed - lead.vLead)
  desired_gap = (speed * speed - lead.vLead * lead.vLead) / 5. + follow * speed + 6.
  # Do not soften braking inside the fast-closing follow window, even before
  # model confidence drops.
  return bool(closing >= max(2., .08 * speed) and lead.dRel <= desired_gap + max(8., .35 * speed))


class NiroFarFollow:
  def __init__(self, dt):
    if not math.isfinite(dt) or not 0 < dt <= .1:
      raise ValueError('invalid model interval')
    self.dt = dt
    self.reset()

  def reset(self):
    self.safe = False
    self.drive_id = 0
    self.last_model_ns = 0

  def sample(self, sm, *, now_ns, drive_id, active, target, previous_target, follow_seconds, blocked=False):
    try:
      if drive_id != self.drive_id:
        self.reset()
        self.drive_id = drive_id
      fresh = (type(drive_id) is int and drive_id > 0 and type(now_ns) is int and now_ns > drive_id and
               all(sm.valid[name] and sm.alive[name] and drive_id <= sm.logMonoTime[name] <= now_ns and
                   now_ns - sm.logMonoTime[name] <= SOURCE_MAX_AGE_NS for name in SOURCES))
      model_ns = sm.logMonoTime['modelV2']
      car = sm['carState']
      if (not fresh or not active or blocked or model_ns <= self.last_model_ns or
          not car.canValid or car.canTimeout or car.gasPressed or car.brakePressed or car.standstill or
          sm['controlsState'].forceDecel or sm['selfdriveState'].experimentalMode or not sm['selfdriveState'].enabled or
          not sm['carControl'].longActive or sm['modelV2'].action.shouldStop):
        self.safe = False
        return target
      if self.last_model_ns and model_ns - self.last_model_ns > SOURCE_MAX_AGE_NS:
        self.safe = False
      self.last_model_ns = model_ns
      speed = float(car.vEgo)
      if not all(math.isfinite(value) for value in (speed, target, previous_target, follow_seconds)) or not .5 <= follow_seconds <= 3:
        self.safe = False
        return target
      leads = [lead for lead in (sm['radarState'].leadOne, sm['radarState'].leadTwo) if lead.present]
      if not all(math.isfinite(float(getattr(lead, key))) for lead in leads for key in ('dRel', 'vLead', 'yRel')):
        self.safe = False
        return target
      centered = [lead for lead in leads if abs(lead.yRel) <= 1.5]
      safe = bool(centered and speed >= 5 and not any(close_fast(lead, speed, follow_seconds) for lead in leads))
      for lead in centered:
        closing = max(0., speed - lead.vLead)
        ttc = lead.dRel / max(closing, .1) if closing > .1 else math.inf
        safe &= bool(lead.dRel >= max(25., 1.35 * speed) and lead.dRel / max(speed, .001) >= 1.35 and ttc >= 8.)
      was_safe = self.safe
      self.safe = safe
      if not safe or not was_safe:
        return target
      return min(previous_target + 1.25 * self.dt, max(previous_target - 2. * self.dt, target))
    except (AttributeError, KeyError, ValueError, TypeError, OverflowError):
      self.safe = False
      return target
