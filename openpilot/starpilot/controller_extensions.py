import math
import time

import numpy as np

import openpilot.cereal.messaging as messaging
from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.common.swaglog import cloudlog

from openpilot.starpilot.controllers.toyota_cruise import ToyotaCruisePreference, capability as toyota_cruise_capability

from opendbc.car.ford.values import CAR, FordFlags


class ManualTurnInputs:
  def __init__(self, params, *, track_assist_permission: bool = False):
    self.params = params
    self.track_assist_permission = track_assist_permission
    self.sm = messaging.SubMaster(["modelV2", "lateralDelay"] + (["pandaStates"] if track_assist_permission else []))
    self.enabled = bool(self.params.get("FordHumanTurnDetection", return_default=True))
    self.frames = 0
    self.blend_settings = self._read_blend_settings()
    self._applied_blends = {}

  def _read_blend_settings(self):
    settings = []
    for key, default, low, high in (("FordCurvatureBlendLow", 0.4, 0.0, 1.0),
                                    ("FordCurvatureBlendHigh", 0.4, 0.0, 1.0),
                                    ("FordCurvatureLaneChangeFactor", 0.85, 0.5, 1.25)):
      try:
        value = float(self.params.get(key, return_default=True))
        if not math.isfinite(value):
          value = default
      except (TypeError, ValueError, OverflowError, RuntimeError):
        value = default
      settings.append(float(np.clip(value, low, high)))
    return tuple(settings)

  def apply_blend_settings(self, controller):
    for name in ("mache_lateral", "classic_lateral"):
      owner = getattr(controller, name, None)
      if owner is not None and self._applied_blends.get(owner) != self.blend_settings:
        owner.set_blend_settings(*self.blend_settings)
        self._applied_blends[owner] = self.blend_settings

  def update(self):
    self.sm.update(0)
    if self.frames % 100 == 0:
      self.enabled = bool(self.params.get("FordHumanTurnDetection", return_default=True))
      self.blend_settings = self._read_blend_settings()
    self.frames += 1
    state = self.sm["modelV2"].meta.laneChangeState
    model_ready = self.sm.alive["modelV2"] and self.sm.valid["modelV2"]
    return self.enabled, int(getattr(state, "raw", state)) in (1, 2, 3), model_ready


  def preview_curvature(self, speed: float) -> float | None:
    try:
      now = time.monotonic_ns()
      stamp = self.sm.logMonoTime["modelV2"]
      if (not self.sm.alive["modelV2"] or not self.sm.valid["modelV2"] or
          not 0 < stamp <= now <= stamp + 100_000_000 or not math.isfinite(speed) or speed < 0.1):
        return None
      yaw = tuple(self.sm["modelV2"].orientationRate.z)
      if len(yaw) != len(ModelConstants.T_IDXS) or not all(math.isfinite(value) for value in yaw):
        return None
      delay = 0.2
      delay_stamp = self.sm.logMonoTime["lateralDelay"]
      if (self.sm.alive["lateralDelay"] and self.sm.valid["lateralDelay"] and
          0 < delay_stamp <= now <= delay_stamp + 1_000_000_000):
        measured_delay = float(self.sm["lateralDelay"].lateralDelay)
        if math.isfinite(measured_delay):
          delay = float(np.clip(measured_delay, 0.2, 0.4))
      return float(np.interp(delay, ModelConstants.T_IDXS, yaw)) / speed
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      return None

  def lateral_snapshot(self, speed: float):
    if self.preview_curvature(speed) is None:
      return None
    delay = 0.2
    now = time.monotonic_ns()
    stamp = self.sm.logMonoTime["lateralDelay"]
    if (self.sm.alive["lateralDelay"] and self.sm.valid["lateralDelay"] and
        0 < stamp <= now <= stamp + 1_000_000_000):
      value = float(self.sm["lateralDelay"].lateralDelay)
      if math.isfinite(value):
        delay = float(np.clip(value, 0.2, 0.4))
    return self.sm["modelV2"], ModelConstants.T_IDXS, delay, self.enabled

  def assist_permission(self):
    if not self.track_assist_permission:
      return (), False
    return self.sm["pandaStates"], self.sm.all_checks(["pandaStates"])


class ResumePlanInputs:
  """Card-owned fresh plan evidence, independent of Controls' saved preference snapshot."""
  def __init__(self):
    from openpilot.starpilot.longitudinal.inputs import ResumeFreshness
    self.sm = messaging.SubMaster(["deviceState", "carState", "longitudinalPlan"], frequency=25)
    self.freshness = ResumeFreshness()

  def update(self, now_ns):
    self.sm.update(0)
    return (type(now_ns) is int and abs(time.monotonic_ns() - now_ns) <= 150_000_000 and
            self.freshness.current(self.sm) and not self.sm['longitudinalPlan'].shouldStop)


def configure_controller(CI, params):
  cp = CI.CP
  controller = CI.CC
  from opendbc.car.gm.values import is_volt_auto_hold
  if controller is not None and is_volt_auto_hold(cp) and controller.gm_auto_hold:
    from openpilot.starpilot.car.gm.auto_hold import AutoHoldPreference
    controller.gm_auto_hold_input = AutoHoldPreference(cp, params)
  from opendbc.car.gm.values import is_volt_longitudinal
  if controller is not None and is_volt_longitudinal(cp) and controller.volt_sng:
    try:
      controller.volt_sng_plan_input = ResumePlanInputs()
    except OSError:
      controller.volt_sng_plan_input = None
      cloudlog.exception('Optional Volt resume input transport unavailable')
  if controller is not None and toyota_cruise_capability(cp) is not None:
    controller.reverse_cruise_input = ToyotaCruisePreference(cp, params)
  if (controller is not None and cp.brand == "ford" and cp.carFingerprint == CAR.FORD_MUSTANG_MACH_E_MK1 and
      not cp.flags & FordFlags.LKA_STEERING and not cp.passive and not cp.dashcamOnly and not cp.notCar and
      getattr(controller, "manual_turn", None) is not None):
    controller.manual_turn_inputs = ManualTurnInputs(params, track_assist_permission=bool(cp.flags & FordFlags.CANFD))

  from opendbc.car.ford.classic_lateral import qualified as classic_qualified
  from opendbc.car.ford.generic_canfd_lateral import qualified as generic_canfd_qualified
  if controller is not None and (classic_qualified(cp) or generic_canfd_qualified(cp)) and getattr(controller, "classic_lateral", None) is not None:
    controller.manual_turn_inputs = ManualTurnInputs(params)

  if controller is not None and cp.brand == "ford" and getattr(controller, "manual_turn_inputs", None) is not None:
    controller.manual_turn_inputs.apply_blend_settings(controller)

  if controller is not None and cp.brand == "honda" and getattr(controller, "nidec_interceptor", None) is not None:
    from openpilot.starpilot.car.honda.longitudinal import BoschLearningParams
    controller.interceptor_learning_params = BoschLearningParams(params, controller.nidec_interceptor)

  if controller is not None and cp.brand == "honda" and getattr(controller, "bosch_longitudinal", None) is not None:
    from openpilot.starpilot.car.honda.longitudinal import BoschLearningParams
    controller.bosch_learning_params = BoschLearningParams(params, controller.bosch_longitudinal)

  from opendbc.car.hyundai.g90_lead import eligible as g90_lead_eligible
  if controller is not None and g90_lead_eligible(cp):
    from openpilot.starpilot.longitudinal.g90_lead import G90LeadInputs
    try:
      controller.g90_lead_inputs = G90LeadInputs()
    except OSError:
      controller.g90_lead_inputs = None
      cloudlog.exception('Optional G90 lead input transport unavailable')

  from opendbc.car.hyundai.gv70_camera_lead import eligible as gv70_lead_eligible
  if controller is not None and gv70_lead_eligible(cp):
    from openpilot.starpilot.longitudinal.gv70_lead import GV70LeadInputs
    try:
      controller.gv70_lead_inputs = GV70LeadInputs()
    except OSError:
      controller.gv70_lead_inputs = None
      cloudlog.exception('Optional GV70 lead input transport unavailable')

  from opendbc.car.hyundai.ev9_longitudinal import qualified as ev9_long_qualified
  if controller is not None and ev9_long_qualified(cp):
    from openpilot.starpilot.longitudinal.canfd_lead import CANFDLeadInputs
    try:
      controller.ev9_lead_inputs = CANFDLeadInputs()
    except OSError:
      controller.ev9_lead_inputs = None
      cloudlog.exception('Optional EV9 lead input transport unavailable')

  if controller is not None and getattr(controller, 'ioniq6_longitudinal', None) is not None:
    from openpilot.starpilot.longitudinal.canfd_lead import CANFDLeadInputs
    try:
      controller.ioniq6_lead_inputs = CANFDLeadInputs()
    except OSError:
      controller.ioniq6_lead_inputs = None
      cloudlog.exception('Optional Ioniq 6 lead input transport unavailable')

  if controller is not None and getattr(controller, 'torque_ev_scc_enabled', False):
    from openpilot.starpilot.longitudinal.canfd_lead import CANFDLeadInputs
    try:
      controller.torque_ev_lead_inputs = CANFDLeadInputs()
    except OSError:
      controller.torque_ev_lead_inputs = None
      cloudlog.exception('Optional torque EV lead input transport unavailable')
