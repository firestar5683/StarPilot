from cereal import car
from types import SimpleNamespace
from openpilot.common.realtime import DT_CTRL
from openpilot.common.numpy_fast import interp
from openpilot.common.params import Params
from openpilot.selfdrive.car.hyundai.values import CarControllerParams


LongCtrlState = car.CarControl.Actuators.LongControlState
class JerkLimiter:
  def __init__(self):
    self.using_e2e = False
    # Initialize limited_accel related variables
    self.brake_ramp = 0.0
    self.accel_last = 0.0
    self.accel_last_jerk = 0.0
    self.accel_raw = 0.0

    # Initialize jerk related variables
    self.jerk = 0.0
    self.jerk_count = 0.0
    self.jerk_upper_limit = 0.0
    self.jerk_lower_limit = 0.0

    # Constants
    self.DT_CTRL = DT_CTRL
    self.param_s = Params()
    self.hkg_tuning = self.param_s.get_bool('HKGtuning')


  def cal_jerk(self, accel, actuators):
    self.accel_raw = accel

    if actuators.longControlState in (LongCtrlState.off, LongCtrlState.stopping):
        accel_diff = 0.0
    elif accel < 0:  # Braking
            accel_diff = (self.accel_raw - self.accel_last_jerk) * 0.8
    # Reduced jerk when transitioning from braking to acceleration
    elif self.accel_last_jerk < 0 and accel > self.accel_last_jerk:
        accel_diff = (self.accel_raw - self.accel_last_jerk) * 0.7
    else:
        accel_diff = self.accel_raw - self.accel_last_jerk

    # Apply time-based smoothing
    accel_diff /= self.DT_CTRL
    self.jerk = self.jerk * 0.95 + accel_diff * 0.05
    self.accel_last_jerk = self.accel_raw
    return self.jerk


  def make_jerk(self, CS, accel, actuators):
    jerk = self.cal_jerk(accel, actuators)
    jerk += (accel - CS.out.aEgo) * 2.0
    mode = actuators.longControlState


    if self.hkg_tuning:
      if mode in [LongCtrlState.pid, self.using_e2e]:
        # Jerk Limits
        startingJerk = 0.5
        jerkLimit = 3.0
        self.jerk_count += self.DT_CTRL
        jerk_max = interp(self.jerk_count, [0, 1.5, 2.5], [startingJerk, startingJerk, jerkLimit])

        if actuators.longControlState == LongCtrlState.off:
            self.jerk_upper_limit = self.jerk_lower_limit = jerkLimit
            self.jerk_count = 0
        elif accel < 0:  # Braking
            # Progressive braking - gentler as we get closer to stop
            stopping_factor = interp(CS.out.vEgo,
                [0.0, 0.5, 1.0, 1.5, 2.0],
                [0.2, 0.3, 0.4, 0.7, 1.0])

            self.jerk_upper_limit = jerkLimit * 2.0 # Still allow for quick stops
            self.jerk_lower_limit = min(max(jerkLimit * 0.2, jerkLimit * stopping_factor), jerkLimit)
        elif CS.out.vEgo < 3.57:  # Low speed acceleration (under 8-ish mph)
            self.jerk_upper_limit = min(max(0.5, jerk * 2.0), jerk_max)
            self.jerk_lower_limit = min(max(0.9, -jerk * 2.0), jerkLimit)
        else:  # Normal driving
            self.jerk_upper_limit = jerkLimit * 3.0
            self.jerk_lower_limit = jerkLimit * 0.9
      else:
          # Default limits
          self.jerk_upper_limit = 3 if actuators.longControlState == LongCtrlState.pid else 2.0
          self.jerk_lower_limit = 3

      return jerk


  def calculate_limited_accel(self, accel, actuators, CS, LongCtrlState, interp, clip):
    """Limit acceleration based on jerk limits"""

    self.make_jerk(CS, accel, actuators)
    accel_delta = accel - self.accel_last
    brake_aggressiveness = 0.0
    ramp_rate = 0.7

    if accel < 0:
      brake_ratio = clip(abs(accel / CarControllerParams.ACCEL_MIN), 0.0, 1.0)
      brake_aggressiveness = brake_ratio ** 1.5
      ramp_rate = interp(brake_aggressiveness,
                        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                        [0.2, 0.3, 0.4, 0.6, 0.9, 1.2])

      if brake_ratio > 0.8:
            ramp_rate *= 0.8

      if self.accel_last >= 0:  # Transitioning into braking
        self.brake_ramp = 0.0
        ramp_rate *= 0.5

    self.brake_ramp = min(1.0, self.brake_ramp + (ramp_rate * self.DT_CTRL))

    abs_accel = clip(abs(accel), 0.0, 2.0)
    smooth_factor = interp(abs_accel,
                          [0.0, 0.3, 0.6, 1.0, 1.5, 2.0],  # breakpoints
                          [0.95, 0.85, 0.75, 0.65, 0.55, 0.45])  # Smoothing factors

    if accel < 0 and brake_aggressiveness > 0.8:
      smooth_factor *= 0.8

    if abs_accel < 0.5:
      smooth_factor *= interp(abs_accel,
                              [0.0, 0.5],
                              [1.3, 1.0])

    accel_delta *= (smooth_factor * self.brake_ramp)

    if abs(accel_delta) > 0.5:  # For large mph changes
      damping = interp(abs(accel_delta),
                      [0.5, 1.0, 1.5, 2.0],
                      [0.90, 0.80, 0.70, 0.60])
      accel_delta *= damping

    jerk_limit_factor = interp(abs(accel),
                              [0.0, 1.0, 2.0, 3.0],
                              [1.0, 0.8, 0.6, 0.5])
    limited_accel_delta =clip(accel_delta,
                             -self.jerk_lower_limit * self.DT_CTRL * jerk_limit_factor,
                             self.jerk_upper_limit * self.DT_CTRL * jerk_limit_factor)

    if accel < 0 and self.accel_last > 0:
      transition_factor = interp(abs(accel),
                               [0, 0.5, 1.0, 1.5, 2.0],
                               [0.3, 0.4, 0.5, 0.6, 0.7])
      limited_accel_delta *= transition_factor

    accel = self.accel_last + limited_accel_delta
    self.accel_last = accel

    return accel




class ParamManager:
  def __init__(self):
    self._params_list: SimpleNamespace = self._create_namespace({
      "hyundai_radar_tracks_available": False,
      "hyundai_radar_tracks_available_cache": False,
    })

  @staticmethod
  def _create_namespace(data: dict) -> SimpleNamespace:
    return SimpleNamespace(**data)

  def get_params(self) -> SimpleNamespace:
    return self._params_list

  def update(self, params: Params) -> None:
    self._params_list = self._create_namespace({
      "hyundai_radar_tracks_available": params.get_bool("HyundaiRadarTracksAvailable"),
      "hyundai_radar_tracks_available_cache": params.get_bool("HyundaiRadarTracksAvailableCache"),
    })
