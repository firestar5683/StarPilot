import copy
import math
import time

from cereal import custom
from opendbc.can import CANParser
from opendbc.car import Bus, structs
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.tesla.preap.nap_params import NAPParamKeys
from opendbc.car.tesla.preap.engagement import PreAPEngagement
from opendbc.car.tesla.preap.nap_conf import PEDAL_DI_PRESSED, nap_conf
from opendbc.car.tesla.preap.pedal_feedback import PedalFeedback
from opendbc.car.tesla.values import CANBUS, DBC, GEAR_MAP, STEER_THRESHOLD

try:
  from openpilot.common.params import Params as _NAPParams
  _nap_params = _NAPParams()
except ImportError:
  _nap_params = None

_DOORS = ("DOOR_STATE_FL", "DOOR_STATE_FR", "DOOR_STATE_RL", "DOOR_STATE_RR", "DOOR_STATE_FrontTrunk", "BOOT_STATE")


def _current_time_millis() -> int:
  return int(round(time.time() * 1000))


def update_preap(cs, can_parsers):
  cp_ap_party = can_parsers[Bus.ap_party]
  cp_pt = can_parsers[Bus.pt]
  cp_chassis = can_parsers[Bus.chassis]
  ret = structs.CarState()
  fp_ret = custom.StarPilotCarState.new_message()

  ret.vEgoRaw = cp_chassis.vl["ESP_B"]["ESP_vehicleSpeed"] * CV.KPH_TO_MS
  ret.vEgo, ret.aEgo = cs.update_speed_kf(ret.vEgoRaw)
  ret.gasPressed = cp_pt.vl["DI_torque1"]["DI_pedalPos"] > PEDAL_DI_PRESSED
  real_brake_pressed = cp_chassis.vl["BrakeMessage"]["driverBrakeStatus"] == 2
  ret.brake = 0
  ret.brakePressed = real_brake_pressed

  epas_status = cp_chassis.vl["EPAS_sysStatus"]
  cs.hands_on_level = epas_status["EPAS_handsOnLevel"]
  ret.steeringAngleDeg = -epas_status["EPAS_internalSAS"]
  ret.steeringRateDeg = -cp_chassis.vl["STW_ANGLHP_STAT"]["StW_AnglHP_Spd"]
  ret.steeringTorque = -epas_status["EPAS_torsionBarTorque"]
  ret.steeringPressed = cs.update_steering_pressed(abs(ret.steeringTorque) > STEER_THRESHOLD, 5)

  eac_status = cs.can_define.dv["EPAS_sysStatus"]["EPAS_eacStatus"].get(int(epas_status["EPAS_eacStatus"]), None)
  ret.steerFaultPermanent = eac_status == "EAC_FAULT"
  ret.steerFaultTemporary = False

  eac_error_code = cs.can_define.dv["EPAS_sysStatus"]["EPAS_eacErrorCode"].get(int(epas_status["EPAS_eacErrorCode"]), None)
  ret.steeringDisengage = cs.hands_on_level >= 3 or (eac_status == "EAC_INHIBITED" and eac_error_code in (
    "EAC_ERROR_HIGH_ANGLE_REQ", "EAC_ERROR_HIGH_ANGLE_RATE_REQ", "EAC_ERROR_HIGH_ANGLE_SAFETY", "EAC_ERROR_HIGH_ANGLE_RATE_SAFETY",
  ))
  cs.engagement.handle_steering_disengage(ret.steeringDisengage)

  cruise_state = cs.can_define.dv["DI_state"]["DI_cruiseState"].get(int(cp_chassis.vl["DI_state"]["DI_cruiseState"]), None)
  cs.di_cruise_state = cruise_state or "OFF"
  speed_units = cs.can_define.dv["DI_state"]["DI_speedUnits"].get(int(cp_chassis.vl["DI_state"]["DI_speedUnits"]), None)
  if speed_units is not None:
    cs.speed_units = speed_units

  pedal_transform_valid = math.isfinite(nap_conf.pedal_factor) and abs(nap_conf.pedal_factor) > 1e-6
  use_pedal = nap_conf.use_pedal and cs.CP.openpilotLongitudinalControl and pedal_transform_valid
  pedal_long_allowed = use_pedal
  long_control_allowed = True if not use_pedal else pedal_long_allowed

  ret.cruiseState.available = True
  if cs.enableLongControl and use_pedal:
    ret.cruiseState.speed = cs.pedal_speed_kph * CV.KPH_TO_MS
  elif speed_units == "KPH":
    ret.cruiseState.speed = max(cp_chassis.vl["DI_state"]["DI_digitalSpeed"] * CV.KPH_TO_MS, 1e-3)
  elif speed_units == "MPH":
    ret.cruiseState.speed = max(cp_chassis.vl["DI_state"]["DI_digitalSpeed"] * CV.MPH_TO_MS, 1e-3)
  ret.cruiseState.standstill = False
  ret.standstill = cruise_state == "STANDSTILL"
  ret.accFaulted = cruise_state == "FAULT"

  ret.gearShifter = GEAR_MAP[cs.can_define.dv["DI_torque2"]["DI_gear"].get(int(cp_chassis.vl["DI_torque2"]["DI_gear"]), "DI_GEAR_INVALID")]
  ret.doorOpen = any((cs.can_define.dv["GTW_carState"][door].get(int(cp_chassis.vl["GTW_carState"][door]), "OPEN") == "OPEN") for door in _DOORS)
  ret.leftBlinker = cp_chassis.vl["GTW_carState"]["BC_indicatorLStatus"] == 1
  ret.rightBlinker = cp_chassis.vl["GTW_carState"]["BC_indicatorRStatus"] == 1
  ret.seatbeltUnlatched = False
  ret.stockAeb = False
  ret.stockLkas = False

  cs.prev_cruise_buttons = cs.cruise_buttons
  cs.cruise_buttons = int(cp_chassis.vl["STW_ACTN_RQ"]["SpdCtrlLvr_Stat"])
  cs.msg_stw_actn_req = copy.copy(cp_chassis.vl["STW_ACTN_RQ"])

  if _nap_params is not None:
    dtr_dist = int(cp_chassis.vl["STW_ACTN_RQ"]["DTR_Dist_Rq"])
    if dtr_dist != 255:
      stalk_follow = min((dtr_dist // 33) + 1, 7)
      if stalk_follow != cs.prev_stalk_follow:
        _nap_params.put_int(NAPParamKeys.FOLLOW_DISTANCE, stalk_follow)
        cs.prev_stalk_follow = stalk_follow

  curr_time_ms = _current_time_millis()
  ret.buttonEvents = cs.engagement.process_buttons(
    cs.cruise_buttons, cs.prev_cruise_buttons, curr_time_ms, ret.vEgo, cs.speed_units,
    use_pedal, pedal_long_allowed, long_control_allowed, real_brake_pressed, cs.di_cruise_state,
  )
  ret.brakePressed = False

  can_engage = cs.engagement.check_can_engage(ret.doorOpen, ret.gearShifter, ret.seatbeltUnlatched)
  ret.cruiseState.enabled = cs.engagement.cruiseEnabled and can_engage

  cs.cruiseEnabled = cs.engagement.cruiseEnabled
  cs.enableLongControl = cs.engagement.enableLongControl
  cs.enableJustCC = cs.engagement.enableJustCC
  cs.pedal_speed_kph = cs.engagement.pedal_speed_kph
  cs.preap_cc_cancel_needed = cs.engagement.preap_cc_cancel_needed
  cs.preap_cc_engage_needed = cs.engagement.preap_cc_engage_needed

  if nap_conf.use_pedal:
    gas_sensor = cp_ap_party.vl.get("GAS_SENSOR", {})
    cs.pedal.update(gas_sensor, curr_time_ms)
    cs.pedal.update_torque(cp_pt.vl.get("DI_torque1", {}))
    cs.pedal_interceptor_value = cs.pedal.interceptor_value
    cs.pedal_timeout = cs.pedal.timeout
    if use_pedal:
      ret.gasPressed = cs.pedal.gas_pressed

  cs.das_control = None
  cs.cruise_enabled_prev = ret.cruiseState.enabled
  fp_ret.pedalMaxRegen = cs.pccEvent == "pedalMaxRegen"
  fp_ret.teslaCCEngaged = cs.pccEvent == "teslaCCEngaged"
  fp_ret.teslaCCDisengaged = cs.pccEvent == "teslaCCDisengaged"
  fp_ret.teslaCCNotArmed = (
    not nap_conf.use_pedal and
    cs.cruiseEnabled and
    cs.enableLongControl and
    cs.di_cruise_state not in ("STANDBY", "ENABLED")
  )
  fp_ret.pedalLongActive = cs.enableLongControl and nap_conf.use_pedal
  return ret, fp_ret


def get_preap_can_parsers(CP):
  chassis_messages = [
    ("ESP_B", 0), ("BrakeMessage", 0), ("DI_state", 0), ("DI_torque2", 0),
    ("GTW_carState", 0), ("GTW_epasControl", 0), ("STW_ANGLHP_STAT", 0), ("EPAS_sysStatus", 0), ("STW_ACTN_RQ", 0),
  ]
  pt_messages = [("DI_torque1", 0)]
  pedal_messages = [("GAS_SENSOR", 50)] if nap_conf.use_pedal else []
  return {
    Bus.party: CANParser(DBC[CP.carFingerprint][Bus.party], [], CANBUS.party),
    Bus.ap_party: CANParser(DBC[CP.carFingerprint][Bus.party], pedal_messages, nap_conf.pedal_can_bus),
    Bus.pt: CANParser(DBC[CP.carFingerprint][Bus.pt], pt_messages, CANBUS.party),
    Bus.chassis: CANParser(DBC[CP.carFingerprint][Bus.chassis], chassis_messages, CANBUS.party),
  }
