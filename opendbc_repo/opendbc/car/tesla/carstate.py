import copy
from cereal import custom
from opendbc.can import CANDefine, CANParser
from opendbc.car import Bus, create_button_events, structs
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.interfaces import CarStateBase
from opendbc.car.tesla.values import (
  DBC, CANBUS, GEAR_MAP, STEER_DISENGAGE_THRESHOLD, STEER_THRESHOLD, TeslaSafetyFlags,
  CAR, LEGACY_CARS, TeslaFlags,
)
from opendbc.car.tesla.preap.carstate import get_preap_can_parsers, update_preap
from opendbc.car.tesla.preap.engagement import PreAPEngagement
from opendbc.car.tesla.preap.nap_conf import nap_conf
from opendbc.car.tesla.preap.pedal_feedback import PedalFeedback

ButtonType = structs.CarState.ButtonEvent.Type

TESLA_GAS_PRESS_ON = 0.8
TESLA_GAS_PRESS_OFF = 0.4


class TeslaScreenCANParser(CANParser):
  def __init__(self):
    super().__init__("tesla_model3_vehicle", [("UI_status2", 0)], CANBUS.vehicle)

  def update(self, strings, sendcan=False):
    if strings and not isinstance(strings[0], list | tuple):
      strings = [strings]
    # Match Panda's exact-length check before producing engagement button events.
    return super().update([
      (timestamp, [frame for frame in frames if frame[0] == 0x3DF and len(frame[1]) == 8])
      for timestamp, frames in strings
    ], sendcan)


def update_tesla_gas_pressed(previous: bool, pedal_position: float) -> bool:
  threshold = TESLA_GAS_PRESS_OFF if previous else TESLA_GAS_PRESS_ON
  return float(pedal_position) > threshold


class CarState(CarStateBase):
  def __init__(self, CP, FPCP):
    super().__init__(CP, FPCP)
    self.can_define = CANDefine(DBC[CP.carFingerprint][Bus.party])
    if CP.carFingerprint in LEGACY_CARS:
      self.can_define_party = CANDefine(DBC[CP.carFingerprint][Bus.party])
      self.can_define_pt = CANDefine(DBC[CP.carFingerprint][Bus.pt])
      self.can_define_chassis = CANDefine(DBC[CP.carFingerprint][Bus.chassis])
      self.can_defines = {
        **self.can_define_party.dv,
        **self.can_define_pt.dv,
        **self.can_define_chassis.dv,
      }
      self.shifter_values = self.can_defines["DI_torque2"]["DI_gear"]
    else:
      self.shifter_values = self.can_define.dv["DI_systemStatus"]["DI_gear"] if CP.carFingerprint != CAR.TESLA_MODEL_S_PREAP else \
                            self.can_define.dv["DI_torque2"]["DI_gear"]

    self.autopark = False
    self.autopark_prev = False
    self.cruise_enabled_prev = False

    self.hands_on_level = 0
    self.das_control = None
    self.cruise_buttons = 0
    self.prev_cruise_buttons = 0
    self.gas_pressed = False
    self.active_touch_points = None
    self.msg_stw_actn_req = None
    self.speed_units = "MPH"
    self.cooperative_steering = any(
      config.safetyParam & TeslaSafetyFlags.COOP_STEERING.value for config in CP.safetyConfigs
    )

    if CP.carFingerprint == CAR.TESLA_MODEL_S_PREAP:
      self.engagement = PreAPEngagement(nap_conf.double_pull_enabled, nap_conf.double_pull_window_ms)
      self.cruiseEnabled = False
      self.enableLongControl = False
      self.enableJustCC = False
      self.pedal_speed_kph = 0.0
      self.prev_stalk_follow = 0
      self.pccEvent = None
      self.preap_cc_cancel_needed = False
      self.preap_cc_engage_needed = False
      self.di_cruise_state = "OFF"
      self.pedal = PedalFeedback()
      self.pedal_interceptor_value = 0.0
      self.pedal_timeout = True

  def update_autopark_state(self, autopark_state: str, cruise_enabled: bool):
    autopark_now = autopark_state in ("ACTIVE", "COMPLETE", "SELFPARK_STARTED")
    if autopark_now and not self.autopark_prev and not self.cruise_enabled_prev:
      self.autopark = True
    if not autopark_now:
      self.autopark = False
    self.autopark_prev = autopark_now
    self.cruise_enabled_prev = cruise_enabled

  def update_button_enable(self, buttonEvents: list[structs.CarState.ButtonEvent]):
    if self.CP.carFingerprint == CAR.TESLA_MODEL_S_PREAP:
      return False
    return super().update_button_enable(buttonEvents)

  def update_screen_button(self, cp_vehicle):
    events = []
    for touch_points in cp_vehicle.vl_all["UI_status2"]["UI_activeTouchPoints"]:
      touch_points = int(touch_points)
      # Establish a baseline first; a touch already held during boot is not an engagement request.
      if self.active_touch_points is not None:
        events.extend(create_button_events(touch_points, self.active_touch_points, {3: ButtonType.lkas}))
      self.active_touch_points = touch_points
    return events

  def update(self, can_parsers, starpilot_toggles) -> structs.CarState:
    if self.CP.carFingerprint == CAR.TESLA_MODEL_S_PREAP:
      return update_preap(self, can_parsers)
    if self.CP.carFingerprint in LEGACY_CARS:
      return self.update_legacy(can_parsers)

    cp_party = can_parsers[Bus.party]
    cp_ap_party = can_parsers[Bus.ap_party]
    ret = structs.CarState()

    # Vehicle speed
    ret.vEgoRaw = cp_party.vl["DI_speed"]["DI_vehicleSpeed"] * CV.KPH_TO_MS
    ret.vEgo, ret.aEgo = self.update_speed_kf(ret.vEgoRaw)

    # Gas pedal
    self.gas_pressed = update_tesla_gas_pressed(
      self.gas_pressed,
      cp_party.vl["DI_systemStatus"]["DI_accelPedalPos"],
    )
    ret.gasPressed = self.gas_pressed

    # Brake pedal
    ret.brake = 0
    ret.brakePressed = cp_party.vl["IBST_status"]["IBST_driverBrakeApply"] == 2

    # Steering wheel
    epas_status = cp_party.vl["EPAS3S_sysStatus"]
    self.hands_on_level = epas_status["EPAS3S_handsOnLevel"]
    ret.steeringAngleDeg = -epas_status["EPAS3S_internalSAS"]
    ret.steeringRateDeg = -cp_ap_party.vl["SCCM_steeringAngleSensor"]["SCCM_steeringAngleSpeed"]
    ret.steeringTorque = -epas_status["EPAS3S_torsionBarTorque"]

    # stock handsOnLevel uses >0.5 for 0.25s, but is too slow
    ret.steeringPressed = self.update_steering_pressed(abs(ret.steeringTorque) > STEER_THRESHOLD, 5)

    eac_status = self.can_define.dv["EPAS3S_sysStatus"]["EPAS3S_eacStatus"].get(int(epas_status["EPAS3S_eacStatus"]), None)
    ret.steerFaultPermanent = eac_status == "EAC_FAULT"
    ret.steerFaultTemporary = eac_status == "EAC_INHIBITED"

    # FSD disengages using union of handsOnLevel (slow overrides) and high angle rate faults (fast overrides, high speed)
    eac_error_code = self.can_define.dv["EPAS3S_sysStatus"]["EPAS3S_eacErrorCode"].get(int(epas_status["EPAS3S_eacErrorCode"]), None)
    ret.steeringDisengage = (
      self.hands_on_level >= 3 or
      (eac_status == "EAC_INHIBITED" and eac_error_code == "EAC_ERROR_HIGH_ANGLE_RATE_SAFETY") or
      (self.cooperative_steering and abs(ret.steeringTorque) > STEER_DISENGAGE_THRESHOLD)
    )

    # Cruise state
    cruise_state = self.can_define.dv["DI_state"]["DI_cruiseState"].get(int(cp_party.vl["DI_state"]["DI_cruiseState"]), None)
    speed_units = self.can_define.dv["DI_state"]["DI_speedUnits"].get(int(cp_party.vl["DI_state"]["DI_speedUnits"]), None)

    autopark_state = self.can_define.dv["DI_state"]["DI_autoparkState"].get(int(cp_party.vl["DI_state"]["DI_autoparkState"]), None)
    cruise_enabled = cruise_state in ("ENABLED", "STANDSTILL", "OVERRIDE", "PRE_FAULT", "PRE_CANCEL")
    self.update_autopark_state(autopark_state, cruise_enabled)

    # Match panda safety cruise engaged logic
    ret.cruiseState.enabled = cruise_enabled and not self.autopark
    if speed_units == "KPH":
      ret.cruiseState.speed = max(cp_party.vl["DI_state"]["DI_digitalSpeed"] * CV.KPH_TO_MS, 1e-3)
    elif speed_units == "MPH":
      ret.cruiseState.speed = max(cp_party.vl["DI_state"]["DI_digitalSpeed"] * CV.MPH_TO_MS, 1e-3)
    ret.cruiseState.available = cruise_state == "STANDBY" or ret.cruiseState.enabled
    ret.cruiseState.standstill = False  # This needs to be false, since we can resume from stop without sending anything special
    ret.standstill = cp_party.vl["ESP_B"]["ESP_vehicleStandstillSts"] == 1
    ret.accFaulted = cruise_state == "FAULT"

    # Gear
    ret.gearShifter = GEAR_MAP[self.can_define.dv["DI_systemStatus"]["DI_gear"].get(int(cp_party.vl["DI_systemStatus"]["DI_gear"]), "DI_GEAR_INVALID")]

    # Doors
    ret.doorOpen = cp_party.vl["UI_warning"]["anyDoorOpen"] == 1

    # Blinkers
    ret.leftBlinker = cp_party.vl["UI_warning"]["leftBlinkerBlinking"] in (1, 2)
    ret.rightBlinker = cp_party.vl["UI_warning"]["rightBlinkerBlinking"] in (1, 2)

    # Seatbelt
    ret.seatbeltUnlatched = cp_party.vl["UI_warning"]["buckleStatus"] != 1

    # Blindspot
    ret.leftBlindspot = cp_ap_party.vl["DAS_status"]["DAS_blindSpotRearLeft"] != 0
    ret.rightBlindspot = cp_ap_party.vl["DAS_status"]["DAS_blindSpotRearRight"] != 0

    # AEB
    ret.stockAeb = cp_ap_party.vl["DAS_control"]["DAS_aebEvent"] == 1

    # LKAS
    ret.stockLkas = cp_ap_party.vl["DAS_steeringControl"]["DAS_steeringControlType"] == 2  # LANE_KEEP_ASSIST

    # Stock Autosteer should be off (includes FSD)
    if self.CP.carFingerprint in (CAR.TESLA_MODEL_3, CAR.TESLA_MODEL_Y):
      ret.invalidLkasSetting = cp_ap_party.vl["DAS_settings"]["DAS_autosteerEnabled"] != 0
    else:
      pass
    # Buttons # ToDo: add Gap adjust button
    if self.CP.flags & TeslaFlags.AOL_SCREEN_BUTTON:
      ret.buttonEvents = list(ret.buttonEvents) + self.update_screen_button(can_parsers[Bus.adas])

    # Messages needed by carcontroller
    self.das_control = copy.copy(cp_ap_party.vl["DAS_control"])

    fp_ret = custom.StarPilotCarState.new_message()

    return ret, fp_ret

  def update_legacy(self, can_parsers):
    cp_party = can_parsers[Bus.party]
    cp_ap_party = can_parsers[Bus.ap_party]
    cp_pt = can_parsers[Bus.pt]
    cp_ap_pt = can_parsers[Bus.ap_pt]
    cp_chassis = can_parsers[Bus.chassis]
    ret = structs.CarState()
    fp_ret = custom.StarPilotCarState.new_message()

    # Vehicle speed
    ret.vEgoRaw = cp_chassis.vl["ESP_B"]["ESP_vehicleSpeed"] * CV.KPH_TO_MS
    ret.vEgo, ret.aEgo = self.update_speed_kf(ret.vEgoRaw)

    # Gas and brake
    ret.gasPressed = cp_pt.vl["DI_torque1"]["DI_pedalPos"] > 0
    ret.brake = 0
    ret.brakePressed = cp_chassis.vl["BrakeMessage"]["driverBrakeStatus"] != 1

    # Steering wheel and EPAS status
    epas_status = cp_chassis.vl["EPAS_sysStatus"]
    self.hands_on_level = epas_status["EPAS_handsOnLevel"]
    ret.steeringAngleDeg = -epas_status["EPAS_internalSAS"]
    ret.steeringRateDeg = -cp_chassis.vl["STW_ANGLHP_STAT"]["StW_AnglHP_Spd"]
    ret.steeringTorque = -epas_status["EPAS_torsionBarTorque"]
    ret.steeringPressed = self.update_steering_pressed(abs(ret.steeringTorque) > STEER_THRESHOLD, 5)

    eac_status = self.can_defines["EPAS_sysStatus"]["EPAS_eacStatus"].get(int(epas_status["EPAS_eacStatus"]), None)
    ret.steerFaultPermanent = eac_status == "EAC_FAULT"
    ret.steerFaultTemporary = eac_status == "EAC_INHIBITED"
    eac_error_code = self.can_defines["EPAS_sysStatus"]["EPAS_eacErrorCode"].get(int(epas_status["EPAS_eacErrorCode"]), None)
    ret.steeringDisengage = self.hands_on_level >= 3 or (
      eac_status == "EAC_INHIBITED" and eac_error_code == "EAC_ERROR_HIGH_ANGLE_RATE_SAFETY"
    )

    # Cruise
    cruise_state = self.can_defines["DI_state"]["DI_cruiseState"].get(int(cp_chassis.vl["DI_state"]["DI_cruiseState"]), None)
    speed_units = self.can_defines["DI_state"]["DI_speedUnits"].get(int(cp_chassis.vl["DI_state"]["DI_speedUnits"]), None)
    cruise_enabled = cruise_state in ("ENABLED", "STANDSTILL", "OVERRIDE", "PRE_FAULT", "PRE_CANCEL")
    ret.cruiseState.enabled = cruise_enabled
    if speed_units == "KPH":
      ret.cruiseState.speed = max(cp_chassis.vl["DI_state"]["DI_hw1CruiseSet"] * CV.KPH_TO_MS, 1e-3)
    elif speed_units == "MPH":
      ret.cruiseState.speed = max(cp_chassis.vl["DI_state"]["DI_hw1CruiseSet"] * CV.MPH_TO_MS, 1e-3)
    ret.cruiseState.available = cruise_state == "STANDBY" or ret.cruiseState.enabled
    ret.cruiseState.standstill = False
    ret.standstill = ret.vEgoRaw < 0.1
    ret.accFaulted = cruise_state == "FAULT"

    # Gear, body state, and safety state
    ret.gearShifter = GEAR_MAP[self.can_defines["DI_torque2"]["DI_gear"].get(
      int(cp_chassis.vl["DI_torque2"]["DI_gear"]), "DI_GEAR_INVALID")]

    doors = ("DOOR_STATE_FL", "DOOR_STATE_FR", "DOOR_STATE_RL", "DOOR_STATE_RR", "DOOR_STATE_FrontTrunk", "BOOT_STATE")
    ret.doorOpen = any(
      self.can_defines["GTW_carState"][door].get(int(cp_chassis.vl["GTW_carState"][door]), "OPEN") == "OPEN"
      for door in doors
    )
    ret.leftBlinker = cp_chassis.vl["GTW_carState"]["BC_indicatorLStatus"] == 1
    ret.rightBlinker = cp_chassis.vl["GTW_carState"]["BC_indicatorRStatus"] == 1

    _ = cp_chassis.vl["SDM1"]
    _ = cp_chassis.vl["RCM_status"]
    sd_time = cp_chassis.ts_nanos["SDM1"]["SDM_bcklDrivStatus"]
    rcm_time = cp_chassis.ts_nanos["RCM_status"]["RCM_buckleDriverStatus"]
    if sd_time and cp_chassis._last_update_nanos - sd_time <= 1_000_000_000:
      ret.seatbeltUnlatched = cp_chassis.vl["SDM1"]["SDM_bcklDrivStatus"] != 1
    elif rcm_time and cp_chassis._last_update_nanos - rcm_time <= 1_000_000_000:
      ret.seatbeltUnlatched = cp_chassis.vl["RCM_status"]["RCM_buckleDriverStatus"] != 1
    else:
      ret.seatbeltUnlatched = True

    ret.stockAeb = cp_ap_pt.vl["DAS_control"]["DAS_aebEvent"] == 1
    ret.stockLkas = cp_ap_party.vl["DAS_steeringControl"]["DAS_steeringControlType"] == 2
    self.das_control = copy.copy(cp_ap_pt.vl["DAS_control"])
    return ret, fp_ret

  @staticmethod
  def get_can_parsers(CP):
    if CP.carFingerprint == CAR.TESLA_MODEL_S_PREAP:
      return get_preap_can_parsers(CP)
    if CP.carFingerprint in LEGACY_CARS:
      return {
        Bus.party: CANParser(DBC[CP.carFingerprint][Bus.party], [], CANBUS.party),
        Bus.ap_party: CANParser(DBC[CP.carFingerprint][Bus.party], [], CANBUS.autopilot_party),
        Bus.pt: CANParser(DBC[CP.carFingerprint][Bus.pt], [], CANBUS.party),
        Bus.ap_pt: CANParser(DBC[CP.carFingerprint][Bus.pt], [], CANBUS.autopilot_party),
        Bus.chassis: CANParser(DBC[CP.carFingerprint][Bus.chassis], [("SDM1", 0), ("RCM_status", 0)], CANBUS.party),
      }
    return {
      Bus.party: CANParser(DBC[CP.carFingerprint][Bus.party], [], CANBUS.party),
      Bus.ap_party: CANParser(DBC[CP.carFingerprint][Bus.party], [], CANBUS.autopilot_party),
      **({Bus.adas: TeslaScreenCANParser()}
         if CP.flags & TeslaFlags.AOL_SCREEN_BUTTON else {}),
    }
