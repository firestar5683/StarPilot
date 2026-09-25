"""Current-drive tracked-lead cost projection, independent of Curve preferences."""
from openpilot.starpilot.curve_speed.host import CLOCK_PAIR_MAX_SKEW_NS, clock_pair_ns, _fresh
from openpilot.starpilot.curve_speed.runtime import INPUT_MAX_AGE_NS, MODEL_MAX_AGE_NS
from openpilot.starpilot.lead_tracking import LeadDetector
from openpilot.starpilot.longitudinal.vehicle_policy import tracked_lead_scale

SOURCES = ('modelV2', 'carState', 'radarState', 'carControl', 'controlsState', 'selfdriveState')


class FollowJerk:
  def __init__(self, cp, *, clock_pair=clock_pair_ns):
    self.scale = tracked_lead_scale(cp)
    self.clock_pair = clock_pair
    self.detector = LeadDetector()
    self.offset_ns = None
    self.floor_ns = 0
    self.drive_id = 0

  def sample(self, sm, cp, now_ns, follow_seconds, stop_plan, *, active, drive_id):
    if self.scale == 1.0:
      return 1.0
    if not active or type(drive_id) is not int or drive_id <= 0:
      self.detector.reset()
      return 1.0
    try:
      pair = self.clock_pair()
      if pair is None or any(type(value) is not int or value <= 0 for value in pair):
        self.offset_ns = None
        self.detector.reset()
        return 1.0
      offset = pair[1] - pair[0]
      if self.offset_ns is None or abs(offset - self.offset_ns) > CLOCK_PAIR_MAX_SKEW_NS or self.drive_id != drive_id:
        self.offset_ns, self.drive_id = offset, drive_id
        self.floor_ns = max(pair[0], drive_id)
        self.detector.reset()
        return 1.0
      model = sm['modelV2']
      car = sm['carState']
      current = (0 <= pair[0] - now_ns <= INPUT_MAX_AGE_NS and
                 all(_fresh(sm, name, pair[0]) and sm.logMonoTime[name] > self.floor_ns for name in SOURCES) and
                 type(model.timestampEof) is int and 0 < model.timestampEof <= pair[1] and
                 pair[1] - model.timestampEof <= MODEL_MAX_AGE_NS and car.canValid and not car.canTimeout and
                 not car.gasPressed and not car.brakePressed and not sm['controlsState'].forceDecel)
      if not current:
        self.detector.reset()
        return 1.0
      observation = self.detector.step(sm['radarState'].leadOne, model, speed_mps=car.vEgo,
                                       t_follow_s=follow_seconds, standstill=car.standstill,
                                       observed_mono_s=sm.logMonoTime['modelV2'] / 1e9, now_mono_s=pair[0] / 1e9,
                                       radar_fresh=True, model_fresh=True, car_fresh=True, headway_fresh=True)
      return self.scale if observation.tracked is True and not stop_plan.forcing and stop_plan.approach_distance_m <= 0 else 1.0
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError, OSError):
      self.detector.reset()
      return 1.0
