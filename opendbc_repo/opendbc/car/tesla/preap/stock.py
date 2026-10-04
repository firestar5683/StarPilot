import copy
import math
from opendbc.can import CANDefine, CANParser, CANPacker
from opendbc.car import Bus, get_safety_config, structs
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.interfaces import CarStateBase, CarControllerBase
from opendbc.car.lateral import apply_steer_angle_limits_vm
from opendbc.car.tesla.values import DBC, GEAR_MAP, STEER_THRESHOLD, CarControllerParams
from opendbc.car.tesla.preap.engagement import PreAPEngagement
from opendbc.car.tesla.preap.aol import qualified
from opendbc.car.tesla.preap.can import TeslaCANPreAP
from opendbc.car.tesla.preap.stock_cc import StockCCSpoofer
from opendbc.car.vehicle_model import VehicleModel

_DOORS = ("DOOR_STATE_FL", "DOOR_STATE_FR", "DOOR_STATE_RL", "DOOR_STATE_RR", "DOOR_STATE_FrontTrunk", "BOOT_STATE")


def get_stock_params(ret):
  ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.teslaPreap, 0)]
  ret.steerLimitTimer = 0.4
  ret.steerActuatorDelay = 0.1
  ret.steerAtStandstill = True
  ret.steerControlType = structs.CarParams.SteerControlType.angle
  ret.radarUnavailable = True
  ret.alphaLongitudinalAvailable = False
  ret.openpilotLongitudinalControl = False
  ret.pcmCruise = True
  return ret


class PreAPStockCarState(CarStateBase):
  def __init__(self, CP):
    super().__init__(CP)
    self.can_define = CANDefine(DBC[CP.carFingerprint][Bus.party])
    self.engagement = PreAPEngagement(True, 500)
    self.hands_on_level = 0
    self.cruise_buttons = self.prev_cruise_buttons = 0
    self.speed_units = "MPH"
    self.cruiseEnabled = self.enableLongControl = self.enableJustCC = False
    self.preap_cc_cancel_needed = self.preap_cc_engage_needed = False
    self.pedal_speed_kph = 0.0
    self.di_cruise_state = "OFF"
    self.pccEvent = None
    self.preap_lateral_authorized = False
    self.das_control = {}
    self.can_now_ns = self.physical_stw_stamp_ns = 0
    self.echo_stamp_ns = 0
    self.cancel_echo_stamp_ns = 0
    self.pending_echo = None
    self.echo_packer = CANPacker(DBC[CP.carFingerprint][Bus.party])

  def update(self, can_parsers):
    return update_stock(self, can_parsers)


def update_stock(cs, can_parsers):
  cp_pt = can_parsers[Bus.pt]
  cp_chassis = can_parsers[Bus.chassis]
  ret = structs.CarState()
  ret.vEgoRaw = cp_chassis.vl["ESP_B"]["ESP_vehicleSpeed"] * CV.KPH_TO_MS
  ret.vEgo, ret.aEgo = cs.update_speed_kf(ret.vEgoRaw)
  ret.gasPressed = cp_pt.vl["DI_torque1"]["DI_pedalPos"] > 2.0
  real_brake_pressed = cp_chassis.vl["BrakeMessage"]["driverBrakeStatus"] == 2
  ret.brakePressed = cp_chassis.vl["BrakeMessage"]["driverBrakeStatus"] != 1

  epas_status = cp_chassis.vl["EPAS_sysStatus"]
  cs.hands_on_level = epas_status["EPAS_handsOnLevel"]
  ret.steeringAngleDeg = -epas_status["EPAS_internalSAS"]
  ret.steeringRateDeg = -cp_chassis.vl["STW_ANGLHP_STAT"]["StW_AnglHP_Spd"]
  ret.steeringTorque = -epas_status["EPAS_torsionBarTorque"]
  ret.steeringPressed = cs.update_steering_pressed(abs(ret.steeringTorque) > STEER_THRESHOLD, 5)

  eac_status = cs.can_define.dv["EPAS_sysStatus"]["EPAS_eacStatus"].get(int(epas_status["EPAS_eacStatus"]), None)
  ret.steerFaultPermanent = eac_status not in ("EAC_ACTIVE", "EAC_AVAILABLE", "EAC_INHIBITED")
  ret.steerFaultTemporary = eac_status == "EAC_INHIBITED"

  eac_error_code = cs.can_define.dv["EPAS_sysStatus"]["EPAS_eacErrorCode"].get(int(epas_status["EPAS_eacErrorCode"]), None)
  ret.steeringDisengage = cs.hands_on_level >= 3 or (eac_status == "EAC_INHIBITED" and eac_error_code in (
    "EAC_ERROR_HIGH_ANGLE_REQ", "EAC_ERROR_HIGH_ANGLE_RATE_REQ", "EAC_ERROR_HIGH_ANGLE_SAFETY", "EAC_ERROR_HIGH_ANGLE_RATE_SAFETY",
  ))
  if eac_error_code is None or eac_error_code == "SNA":
    ret.steerFaultPermanent = True
  cs.engagement.handle_steering_disengage(ret.steeringDisengage or ret.steerFaultPermanent)

  cruise_state = cs.can_define.dv["DI_state"]["DI_cruiseState"].get(int(cp_chassis.vl["DI_state"]["DI_cruiseState"]), None)
  cs.di_cruise_state = cruise_state or "OFF"
  speed_units = cs.can_define.dv["DI_state"]["DI_speedUnits"].get(int(cp_chassis.vl["DI_state"]["DI_speedUnits"]), None)
  if speed_units is not None:
    cs.speed_units = speed_units

  use_pedal = False
  pedal_long_allowed = False
  long_control_allowed = True

  ret.cruiseState.available = cruise_state in ("STANDBY", "ENABLED", "STANDSTILL", "OVERRIDE", "PRE_FAULT", "PRE_CANCEL")
  if speed_units == "KPH":
    ret.cruiseState.speed = max(cp_chassis.vl["DI_state"]["DI_digitalSpeed"] * CV.KPH_TO_MS, 1e-3)
  elif speed_units == "MPH":
    ret.cruiseState.speed = max(cp_chassis.vl["DI_state"]["DI_digitalSpeed"] * CV.MPH_TO_MS, 1e-3)
  ret.cruiseState.standstill = False
  ret.standstill = ret.vEgoRaw < 0.1
  ret.accFaulted = cruise_state == "FAULT"

  ret.gearShifter = GEAR_MAP[cs.can_define.dv["DI_torque2"]["DI_gear"].get(int(cp_chassis.vl["DI_torque2"]["DI_gear"]), "DI_GEAR_INVALID")]
  ret.doorOpen = any(int(cp_chassis.vl["GTW_carState"][door]) != 0 for door in _DOORS)
  ret.leftBlinker = cp_chassis.vl["GTW_carState"]["BC_indicatorLStatus"] == 1
  ret.rightBlinker = cp_chassis.vl["GTW_carState"]["BC_indicatorRStatus"] == 1
  _ = cp_chassis.vl["SDM1"]
  belt_time = cp_chassis.ts_nanos["SDM1"]["SDM_bcklDrivStatus"]
  ret.seatbeltUnlatched = not (belt_time and 0 <= cp_chassis._last_update_nanos - belt_time <= 1_000_000_000 and
                              cp_chassis.vl["SDM1"]["SDM_bcklDrivStatus"] == 1)
  ret.stockAeb = False
  ret.stockLkas = False

  cs.can_now_ns = cp_chassis._last_update_nanos
  current_stw = copy.copy(cp_chassis.vl["STW_ACTN_RQ"])
  stamp = cp_chassis.ts_nanos["STW_ACTN_RQ"]["SpdCtrlLvr_Stat"]
  received = cs.echo_packer.make_can_msg("STW_ACTN_RQ", 0, current_stw)[1]
  if cs.pending_echo is not None:
    expected, expires = cs.pending_echo
    if 0 < stamp <= cs.can_now_ns <= expires and received == expected:
      cs.echo_stamp_ns = stamp
      if int(current_stw["SpdCtrlLvr_Stat"]) == 1:
        cs.cancel_echo_stamp_ns = stamp
      cs.pending_echo = None
    elif cs.can_now_ns > expires:
      cs.pending_echo = None
  cs.prev_cruise_buttons = cs.cruise_buttons
  if stamp != 0 and stamp == cs.echo_stamp_ns:
    cs.cruise_buttons = cs.prev_cruise_buttons
  else:
    cs.cruise_buttons = int(current_stw["SpdCtrlLvr_Stat"])
    cs.msg_stw_actn_req = current_stw
    cs.physical_stw_stamp_ns = stamp

  curr_time_ms = cp_chassis._last_update_nanos // 1_000_000
  ret.buttonEvents = cs.engagement.process_buttons(
    cs.cruise_buttons, cs.prev_cruise_buttons, curr_time_ms, ret.vEgo, cs.speed_units,
    use_pedal, pedal_long_allowed, long_control_allowed, real_brake_pressed, cs.di_cruise_state,
  )

  can_engage = cs.engagement.check_can_engage(ret.doorOpen, ret.gearShifter, ret.seatbeltUnlatched)
  ret.cruiseState.enabled = can_engage and cruise_state in ("ENABLED", "STANDSTILL", "OVERRIDE", "PRE_FAULT", "PRE_CANCEL")

  cs.cruiseEnabled = cs.engagement.cruiseEnabled
  cs.enableLongControl = cs.engagement.enableLongControl
  cs.enableJustCC = cs.engagement.enableJustCC
  cs.pedal_speed_kph = cs.engagement.pedal_speed_kph
  cs.preap_cc_cancel_needed = cs.engagement.preap_cc_cancel_needed
  cs.preap_cc_engage_needed = cs.engagement.preap_cc_engage_needed
  ret.teslaStockCruiseEngaged = cs.di_cruise_state == "ENABLED"
  ret.teslaStockCruiseNotArmed = cs.cruiseEnabled and cs.enableLongControl and cs.di_cruise_state not in ("STANDBY", "ENABLED")

  return ret


def get_stock_parsers(CP):
  dbc = DBC[CP.carFingerprint][Bus.party]
  return {
    Bus.party: CANParser(dbc, [], 0),
    Bus.pt: CANParser(dbc, [("DI_torque1", 100)], 0),
    Bus.chassis: CANParser(dbc, [("ESP_B", 50), ("BrakeMessage", 50), ("DI_state", 10),
      ("DI_torque2", 100), ("GTW_carState", 10), ("STW_ANGLHP_STAT", 50),
      ("EPAS_sysStatus", 25), ("STW_ACTN_RQ", 10), ("SDM1", math.nan)], 0),
  }


class PreAPStockCarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.admitted = qualified(CP)
    self.codec = TeslaCANPreAP(CANPacker(dbc_names[Bus.party]))
    self.stock_cc = StockCCSpoofer()
    self.apply_angle_last = 0.0
    self.VM = VehicleModel(CP)

  def update(self, CC, CS, now_nanos):
    sends = []
    if not self.admitted:
      actuators = CC.actuators.as_builder()
      actuators.steeringAngleDeg = 0.0
      self.frame += 1
      return actuators, sends
    lat_active = CC.latActive and CS.hands_on_level < 3 and CS.preap_lateral_authorized
    if CC.cruiseControl.cancel and CS.cruiseEnabled:
      CS.cruiseEnabled = CS.enableLongControl = CS.enableJustCC = False
      CS.pedal_speed_kph = 0.0
      CS.preap_cc_cancel_needed = True
      CS.engagement.cruiseEnabled = CS.engagement.enableLongControl = CS.engagement.enableJustCC = False
      CS.engagement.pending_enable = False
      CS.engagement.pedal_speed_kph = 0.0
    if self.frame % 2 == 0:
      requested = max(CS.out.steeringAngleDeg - 20.0, min(CS.out.steeringAngleDeg + 20.0, CC.actuators.steeringAngleDeg))
      self.apply_angle_last = apply_steer_angle_limits_vm(requested, self.apply_angle_last, CS.out.vEgoRaw,
        CS.out.steeringAngleDeg, lat_active, CarControllerParams, self.VM)
      sends.append(self.codec.create_steering_control((self.frame // 2) % 16, self.apply_angle_last, lat_active))
      sends.append(self.codec.create_epas_control((self.frame // 2) % 16, 1))
    CS.pccEvent = None
    sends.extend(self.stock_cc.update(CS, self.frame, self.codec, 0))
    if self.stock_cc.pcc_event:
      CS.pccEvent = self.stock_cc.pcc_event
    actuators = CC.actuators.as_builder()
    actuators.steeringAngleDeg = self.apply_angle_last
    for address, data, bus in sends:
      if address == 0x45 and bus == 0:
        CS.pending_echo = (bytes(data), CS.can_now_ns + 100_000_000)
    self.frame += 1
    return actuators, sends
