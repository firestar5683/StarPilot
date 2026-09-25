"""Fresh current-drive inputs for the Electrified GV70's cost projection."""
import math
from opendbc.car.hyundai.gv70_costs import CostContext, project
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL
from openpilot.starpilot.curve_speed.host import _fresh, clock_pair_ns, CLOCK_PAIR_MAX_SKEW_NS
from openpilot.starpilot.curve_speed.runtime import INPUT_MAX_AGE_NS, MODEL_MAX_AGE_NS
from openpilot.starpilot.longitudinal.follow_jerk import SOURCES


class GV70CostContext:
  def __init__(self, *, clock_pair=clock_pair_ns):
    self.clock_pair = clock_pair
    self.reset()

  def reset(self):
    self.drive_id = 0
    self.offset_ns = None
    self.floor_ns = 0
    self.distance = None
    self.last_model_ns = 0
    self.uncertainty = FirstOrderFilter(0., 1.6, DT_MDL)

  def sample(self, sm, now_ns, *, active, drive_id, mode, acceleration_factor,
             speed_factor, danger_factor, stop_plan, follow_scale, prev_accel_constraint):
    if mode != 'acc' or not active or type(drive_id) is not int or drive_id <= 0:
      self.reset()
      return None
    try:
      pair = self.clock_pair()
      if pair is None or any(type(v) is not int or v <= 0 for v in pair):
        self.reset()
        return None
      offset = pair[1] - pair[0]
      if self.offset_ns is None or abs(offset - self.offset_ns) > CLOCK_PAIR_MAX_SKEW_NS or self.drive_id != drive_id:
        self.reset()
        self.offset_ns, self.drive_id = offset, drive_id
        self.floor_ns = max(pair[0], drive_id)
        return None
      model_ns = sm.logMonoTime['modelV2']
      model = sm['modelV2']
      car = sm['carState']
      if (not 0 <= pair[0] - now_ns <= INPUT_MAX_AGE_NS or
          any(not _fresh(sm, name, pair[0]) or sm.logMonoTime[name] <= self.floor_ns for name in SOURCES) or
          type(model.timestampEof) is not int or not 0 < model.timestampEof <= pair[1] or
          pair[1] - model.timestampEof > MODEL_MAX_AGE_NS or
          not car.canValid or car.canTimeout or car.gasPressed or car.brakePressed or
          sm['controlsState'].forceDecel or model_ns < self.last_model_ns):
        self.reset()
        return None
      new_model = model_ns != self.last_model_ns
      self.last_model_ns = model_ns
      lead = sm['radarState'].leadOne
      active_lead = lead.present
      distance = float(lead.dRel) if active_lead else 50.
      if not math.isfinite(distance):
        self.reset()
        return None
      alpha = max(.02, min(.15, .05 + .002 * car.vEgo))
      if new_model:
        self.distance = distance if self.distance is None else self.distance + alpha * (distance - self.distance)
      meta = sm['modelV2'].meta
      probabilities = tuple(float(v) for v in meta.desirePrediction)
      brakes = tuple(float(v) for v in meta.disengagePredictions.brakePressProbs)
      if any(not math.isfinite(v) or v < 0 for v in (*probabilities, *brakes)):
        self.reset()
        return None
      total = sum(probabilities)
      entropy = 0.
      if len(probabilities) > 1 and total > 1e-6:
        normalized = tuple(v / total for v in probabilities)
        entropy = -sum(v * math.log(v + 1e-10) for v in normalized) / max(math.log(len(normalized)), 1e-6)
      brake_scale = .5 if brakes and max(brakes) < .015 else 1.
      risk = max((v * brake_scale * math.exp(-.6 * i * DT_MDL) for i, v in enumerate(brakes)), default=0.)
      if new_model:
        self.uncertainty.update(entropy + risk)
      context = CostContext(car.vEgo, self.distance if active_lead else 50., self.uncertainty.x, mode,
                            acceleration_factor, speed_factor, danger_factor,
                            stop_plan.forcing or stop_plan.approach_distance_m > 0., follow_scale == 1.75,
                            prev_accel_constraint)
      return project(context)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      self.reset()
      return None
