#!/usr/bin/env python3
import numpy as np

from openpilot.common.constants import CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL
from openpilot.starpilot.common.experimental_state import CEStatus


MODEL_STOP_TIME = 7.0
MODEL_STOP_ENTER = 0.63
MODEL_STOP_EXIT = 0.28
MODEL_STOP_FILTER_TIME = 0.35
SLOW_LEAD_FILTER_TIME = 0.35
TURN_VETO_MAX_SPEED = 15.0 * CV.MPH_TO_MS
TURN_VETO_MIN_STEERING_ANGLE = 45.0
MAX_STOP_DETECTION_SPEED = 75.0 * CV.MPH_TO_MS


class UnifiedLongitudinalIntent:
  """Small scene detector for continuous longitudinal planning.

  This class never selects a planner mode. It reports model stop intent and a
  UI reason while the longitudinal planner continuously considers cruise,
  model, curves, and both leads.
  """

  def __init__(self, starpilot_planner):
    self.starpilot_planner = starpilot_planner
    self.params_memory = starpilot_planner.params_memory
    self.stop_filter = FirstOrderFilter(0.0, MODEL_STOP_FILTER_TIME, DT_MDL)
    self.lead_filter = FirstOrderFilter(0.0, SLOW_LEAD_FILTER_TIME, DT_MDL)
    self.stop_detected = False
    self.status_value = CEStatus["OFF"]
    self._last_status = None

  @staticmethod
  def _committed_turn(v_ego, car_state, driving_in_curve):
    if car_state.standstill or v_ego > TURN_VETO_MAX_SPEED:
      return False
    if not (car_state.leftBlinker or car_state.rightBlinker):
      return False
    return abs(float(car_state.steeringAngleDeg)) >= TURN_VETO_MIN_STEERING_ANGLE or driving_in_curve

  def _model_stop_candidate(self, v_ego, sm):
    model = sm["modelV2"]
    if bool(getattr(model.action, "shouldStop", False)):
      return True
    if not len(model.position.x):
      return False

    model_length = max(float(model.position.x[-1]), 0.0)
    end_speed = float(model.velocity.x[-1]) if len(model.velocity.x) else v_ego
    stop_distance = max(v_ego * MODEL_STOP_TIME - 2.5, 0.0)
    return model_length < stop_distance and end_speed < max(2.0, 0.2 * v_ego)

  @staticmethod
  def _slow_lead_candidate(v_ego, sm):
    candidates = []
    for lead in (sm["radarState"].leadOne, sm["radarState"].leadTwo):
      if not bool(getattr(lead, "status", False)):
        continue
      d_rel = float(getattr(lead, "dRel", np.inf))
      v_lead = float(getattr(lead, "vLead", v_ego))
      model_prob = float(getattr(lead, "modelProb", 1.0 if getattr(lead, "radar", False) else 0.0))
      credible = bool(getattr(lead, "radar", False)) or model_prob >= 0.85
      if credible and d_rel < max(40.0, 3.0 * v_ego) and v_lead < v_ego - 0.75:
        candidates.append(lead)
    return bool(candidates)

  def update(self, v_ego, sm, starpilot_toggles):
    car_state = sm["carState"]
    force_stop = bool(getattr(self.starpilot_planner.starpilot_vcruise, "forcing_stop", False))
    stop_sign = bool(getattr(self.starpilot_planner.starpilot_vcruise, "stop_sign_confirmed", False))
    traffic_mode = bool(sm["starpilotCarState"].trafficModeEnabled)
    turn_veto = self._committed_turn(v_ego, car_state, self.starpilot_planner.driving_in_curve)

    model_stop = self._model_stop_candidate(v_ego, sm)
    model_stop &= not traffic_mode and not turn_veto and v_ego <= MAX_STOP_DETECTION_SPEED
    self.stop_filter.update(model_stop)

    if force_stop or stop_sign:
      self.stop_detected = True
      self.stop_filter.x = 1.0
    elif self.stop_detected:
      self.stop_detected = self.stop_filter.x > MODEL_STOP_EXIT
    else:
      self.stop_detected = self.stop_filter.x >= MODEL_STOP_ENTER

    slow_lead = self._slow_lead_candidate(v_ego, sm)
    self.lead_filter.update(slow_lead)
    slow_lead = self.lead_filter.x >= MODEL_STOP_ENTER

    signal = bool(car_state.leftBlinker or car_state.rightBlinker) and v_ego < 15.0
    curve = bool(self.starpilot_planner.road_curvature_detected or self.starpilot_planner.driving_in_curve)
    slc_request = bool(self.starpilot_planner.starpilot_vcruise.slc.experimental_mode)

    if self.stop_detected:
      status = CEStatus["STOP_LIGHT"]
    elif slow_lead:
      status = CEStatus["LEAD"]
    elif signal:
      status = CEStatus["SIGNAL"]
    elif curve:
      status = CEStatus["CURVATURE"]
    elif slc_request:
      status = CEStatus["SPEED_LIMIT"]
    elif bool(getattr(starpilot_toggles, "longitudinal_model_preference", False)):
      status = CEStatus["USER_OVERRIDDEN"]
    else:
      status = CEStatus["OFF"]

    self.status_value = status
    if status != self._last_status:
      self.params_memory.put_int("CEStatus", status)
      self._last_status = status
