import copy
import math
from datetime import UTC, datetime, timedelta
from collections.abc import Mapping
from cereal import custom
from opendbc.can import CANDefine, CANParser
from opendbc.car import Bus, create_button_events, structs
from opendbc.car import DT_CTRL
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gps import get_car_gps_config
from opendbc.car.interfaces import CarStateBase
from opendbc.car.gm.values import (
  ASCM_INT,
  CAMERA_ACC_CAR,
  CAR,
  CC_ONLY_CAR,
  DBC,
  AccState,
  CanBus,
  CruiseButtons,
  GMFlags,
  SDGM_CAR,
  STEER_THRESHOLD,
)
from opendbc.safety import ALTERNATIVE_EXPERIENCE

ButtonType = structs.CarState.ButtonEvent.Type
TransmissionType = structs.CarParams.TransmissionType
NetworkLocation = structs.CarParams.NetworkLocation

STANDSTILL_THRESHOLD = 10 * 0.0311
VOLT_EBCM_BRAKE_PRESSED_THRESHOLD = 6 / 0xd0
AUTO_HOLD_MIN_DRIVE_TIME_S = 3.0
AUTO_HOLD_REGEN_RELEASE_COOLDOWN_S = 1.0

BUTTONS_DICT = {CruiseButtons.RES_ACCEL: ButtonType.accelCruise, CruiseButtons.DECEL_SET: ButtonType.decelCruise,
                CruiseButtons.MAIN: ButtonType.mainCruise, CruiseButtons.CANCEL: ButtonType.cancel}
HARD_BUTTONS_DICT = {CruiseButtons.RES_ACCEL: ButtonType.accelCruise, CruiseButtons.DECEL_SET: ButtonType.decelCruise}
NORMAL_CRUISE_BUTTONS = (CruiseButtons.RES_ACCEL, CruiseButtons.DECEL_SET)

# Optional ~10 Hz CT6 PPS GPS messages on the powertrain bus.
PPS_GPS_MESSAGES = (
  "PPS_ElevHdSpd_FO",
  "PPS_PosLat_FO",
  "PPS_PosLong_FO",
  "PPS_Time_FO",
  "PPS_QualMetrics_FO",
)
# PPS_SigAcqTime_FO is omitted: its validity bit stays 1 even during valid fixes.


def pps_checksum_ok(data: bytes) -> bool:
  """Validate the 11-bit checksum used by the observed PPS frames."""
  if len(data) < 2:
    return False
  received = ((data[-2] & 0x07) << 8) | data[-1]
  expected = sum(data[:-2]) + (data[-2] >> 3) + 0x4C
  return (expected & 0x7FF) == received


def decode_gm_pps_gps(values: Mapping[str, Mapping[str, float]], raw: Mapping[str, bytes],
                      timestamp_nanos: int) -> dict | None:
  """Decode one coherent PPS bundle into the existing car-GPS sample shape."""
  if any(not pps_checksum_ok(raw.get(name, b"")) for name in PPS_GPS_MESSAGES):
    return None

  try:
    pos_lat = values["PPS_PosLat_FO"]
    pos_long = values["PPS_PosLong_FO"]
    timestamp_values = values["PPS_Time_FO"]
    quality = values["PPS_QualMetrics_FO"]
    if (int(pos_lat.get("PPSLatV", 1)) != 0 or
        int(pos_long.get("PPSLongV", 1)) != 0 or
        int(quality.get("PPS2DAbsPosErrEstmtV", 1)) != 0 or
        int(quality.get("PPSMdV", 1)) != 0 or
        int(quality.get("PPSPstnDilPrcsV", 1)) != 0 or
        int(timestamp_values.get("PPSTmdayV", 1)) != 0 or
        int(timestamp_values.get("PPSCldrDayV", 1)) != 0 or
        int(timestamp_values.get("PPSCldrYrV", 1)) != 0):
      return None
    # Reject mode 6 (dead reckoning only without GNSS).
    if int(quality["PPSMd"]) == 6:
      return None

    latitude = float(pos_lat["PPSLat"]) / 3_600_000.0
    longitude = float(pos_long["PPSLong"]) / 3_600_000.0
    if not (math.isfinite(latitude) and math.isfinite(longitude) and
            -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0 and
            (latitude != 0.0 or longitude != 0.0)):
      return None

    year = int(timestamp_values["PPSCldrYr"])
    day_of_year = int(timestamp_values["PPSCldrDay"])
    millis_of_day = int(timestamp_values["PPSTmday"])
    if not 2014 <= year <= 2141 or day_of_year < 1 or not 0 <= millis_of_day < 86_400_000:
      return None
    timestamp = datetime(year, 1, 1, tzinfo=UTC) + timedelta(days=day_of_year - 1, milliseconds=millis_of_day)
    if timestamp.year != year:
      return None

    elev = values["PPS_ElevHdSpd_FO"]
    speed = float(elev["PPSVel"]) * CV.KPH_TO_MS
    if int(elev.get("PPSVelV", 1)) != 0 or not math.isfinite(speed) or not 0.0 <= speed <= 200.0:
      speed = 0.0
    heading = float(elev["PPSHedng"])
    if (int(elev.get("PPSHedngV", 1)) != 0 or
        not math.isfinite(heading) or not 0.0 <= heading < 360.0):
      heading = 0.0

    altitude = float(elev["PPSElvtn"]) / 100.0
    if int(elev.get("PPSElvtnV", 1)) != 0 or not math.isfinite(altitude):
      altitude = 0.0

    horizontal_accuracy = float(quality["PPS2DAbsPosErrEstmt"])
    if not math.isfinite(horizontal_accuracy) or horizontal_accuracy < 0.0:
      horizontal_accuracy = 0.0

    vertical_accuracy = float(quality["PPS3DAbsPosErrEstmt"])
    if int(quality.get("PPS3DAbsPosErrEstmtV", 1)) != 0 or not math.isfinite(vertical_accuracy) or vertical_accuracy < 0.0:
      vertical_accuracy = 0.0

    bearing_accuracy = float(quality["PPSAbsHdngErrEstmt"])
    if int(quality.get("PPSAbsHdngErrEstmtV", 1)) != 0 or not math.isfinite(bearing_accuracy) or bearing_accuracy < 0.0:
      bearing_accuracy = 180.0
  except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
    return None

  heading_rad = math.radians(heading)
  return {
    "timestamp_nanos": timestamp_nanos,
    "latitude": latitude,
    "longitude": longitude,
    "altitude": altitude,
    "speed": speed,
    "bearingDeg": heading,
    "horizontalAccuracy": horizontal_accuracy,
    "unixTimestampMillis": round(timestamp.timestamp() * 1000),
    "verticalAccuracy": vertical_accuracy,
    "bearingAccuracyDeg": bearing_accuracy,
    # Velocity error units are undocumented in DBC; omit conversion.
    "speedAccuracy": 0.0,
    "hasFix": True,
    "satelliteCount": 0,
    "vNED": [speed * math.cos(heading_rad), speed * math.sin(heading_rad), 0.0],
  }


def get_hard_cruise_buttons(steering_button_msg: dict) -> int:
  return steering_button_msg.get("ACCButtonsHard", CruiseButtons.INIT)


GearShifter = structs.CarState.GearShifter
BOLT_GEN1_CANCEL_PERSONALITY_CARS = {
  CAR.CHEVROLET_BOLT_CC_2017,
  CAR.CHEVROLET_BOLT_CC_2018_2021,
}
BOLT_CANCEL_BUTTON_CARS = BOLT_GEN1_CANCEL_PERSONALITY_CARS | {
  CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  CAR.CHEVROLET_BOLT_CC_2022_2023,
}


def update_auto_hold_drive_timers(in_drive_for_hold: bool, moving_for_hold: bool,
                                  auto_hold_drive_time: float, one_pedal_drive_time: float) -> tuple[float, float]:
  if in_drive_for_hold:
    if moving_for_hold:
      auto_hold_drive_time = min(auto_hold_drive_time + DT_CTRL, AUTO_HOLD_MIN_DRIVE_TIME_S)
      one_pedal_drive_time = min(one_pedal_drive_time + DT_CTRL, AUTO_HOLD_MIN_DRIVE_TIME_S)
  else:
    auto_hold_drive_time = 0.0
    one_pedal_drive_time = 0.0

  return auto_hold_drive_time, one_pedal_drive_time


class CarState(CarStateBase):
  def __init__(self, CP, FPCP):
    super().__init__(CP, FPCP)
    can_define = CANDefine(DBC[CP.carFingerprint][Bus.pt])
    self.shifter_values = can_define.dv["ECMPRDNL2"]["PRNDL2"]
    self.cluster_speed_hyst_gap = CV.KPH_TO_MS / 2.
    self.cluster_min_speed = CV.KPH_TO_MS / 2.

    self.loopback_lka_steering_cmd_updated = False
    self.loopback_lka_steering_cmd_ts_nanos = 0
    self.pt_lka_steering_cmd_counter = 0
    self.cam_lka_steering_cmd_counter = 0
    self.buttons_counter = 0
    self.steering_button_checksum = 0
    self.steering_button_prefix = 0x01
    self.steering_button_ts_nanos = 0

    self.prev_distance_button = 0
    self.distance_button = 0
    self.hard_cruise_buttons = CruiseButtons.INIT
    self.force_reset_cruise_buttons = False

    self.single_pedal_mode = False
    self.auto_hold_armed = False
    self.auto_hold_engaged = False
    self.auto_hold_drive_time = 0.0
    self.one_pedal_drive_time = 0.0
    self.auto_hold_fault_suppression_timer = 0.0
    self.regen_release_timer = 0.0
    self.user_regen_paddle_pressed = False

    self.pedal_steady = 0
    self.ecm_cruise_control_ts_nanos = 0
    self.accelerator_pedal2_ts_nanos = 0
    self.moving_backward = False
    self.lkas_previously_enabled = 0
    self.lkas_enabled = 0
    self.pcm_acc_status = AccState.OFF
    self.stock_fcw_alert = 0
    self.car_gps_config = get_car_gps_config(CP)
    self.car_gps_supported = self.car_gps_config is not None
    self.car_gps = None
    self.onstar_gps = None
    self._car_gps_timestamp_nanos = 0
    self._prev_gps_lat = None
    self._prev_gps_lon = None
    self._last_gps_bearing = None

    self.pps_gps = None
    self._pps_gps_timestamp_nanos = 0

  def _update_car_gps(self, cp, v_ego: float = 0.0) -> None:
    if self.car_gps_config is None:
      return

    timestamps = [max(cp.ts_nanos[name].values(), default=0) for name in self.car_gps_config.messages]
    if not all(timestamps) or max(timestamps) - min(timestamps) > 2_000_000_000:
      return

    timestamp_nanos = max(timestamps)
    if timestamp_nanos <= self._car_gps_timestamp_nanos:
      return

    gps = self.car_gps_config.decoder(*(cp.vl[name] for name in self.car_gps_config.messages))
    if gps is not None:
      gps["timestamp_nanos"] = timestamp_nanos
      if gps["hasFix"]:
        lat, lon = gps["latitude"], gps["longitude"]
        if self._prev_gps_lat is not None and (lat, lon) != (self._prev_gps_lat, self._prev_gps_lon):
          d_lat = (lat - self._prev_gps_lat) * 111139.0
          d_lon = (lon - self._prev_gps_lon) * 111139.0 * math.cos(math.radians(lat))
          if math.hypot(d_lat, d_lon) > 1.5 and v_ego > 1.0 and not self.moving_backward:
            self._last_gps_bearing = math.degrees(math.atan2(d_lon, d_lat)) % 360.0

        self._prev_gps_lat, self._prev_gps_lon = lat, lon

        bearing = self._last_gps_bearing if self._last_gps_bearing is not None else 0.0
        gps["speed"] = max(0.0, v_ego)
        gps["bearingDeg"] = bearing
        gps["bearingAccuracyDeg"] = 5.0 if (v_ego > 1.0 and self._last_gps_bearing is not None) else 180.0
        heading_rad = math.radians(bearing)
        gps["vNED"] = [v_ego * math.cos(heading_rad), v_ego * math.sin(heading_rad), 0.0]
      else:
        self._prev_gps_lat = self._prev_gps_lon = None

      self.onstar_gps = gps
      self.car_gps = gps
      self._car_gps_timestamp_nanos = timestamp_nanos

  def _update_pps_gps(self, cp) -> None:
    """Decode a complete, checksum-valid PPS burst when one is available."""
    timestamps = [max(cp.ts_nanos[name].values(), default=0) for name in PPS_GPS_MESSAGES]
    if not all(timestamps):
      return

    timestamp_nanos = max(timestamps)
    if timestamp_nanos <= self._pps_gps_timestamp_nanos:
      return
    if timestamp_nanos - min(timestamps) > 100_000_000:
      return

    vl = cp.vl
    try:
      first_id = int(vl["PPS_ElevHdSpd_FO"]["PPSElvHedngSpdBrstID"])
      if not (first_id == int(vl["PPS_PosLat_FO"]["PPSLatBrstID"]) ==
              int(vl["PPS_PosLong_FO"]["PPSLongBrstID"]) ==
              int(vl["PPS_Time_FO"]["PPSTmBrstID"]) ==
              int(vl["PPS_QualMetrics_FO"]["PPSPosQltyMtcBrstID"])):
        return
    except (KeyError, ValueError, TypeError, OverflowError):
      return

    values = {name: cp.vl[name] for name in PPS_GPS_MESSAGES}
    raw = {name: cp.vl_raw[name] for name in PPS_GPS_MESSAGES}
    self.pps_gps = decode_gm_pps_gps(values, raw, timestamp_nanos)
    self._pps_gps_timestamp_nanos = timestamp_nanos

  def get_car_gps(self) -> dict | None:
    return self.car_gps

  def get_car_gps_sources(self) -> dict[str, dict | None]:
    return {
      "pps": self.pps_gps,
      "onstar": self.onstar_gps,
    }

  def update_button_enable(self, buttonEvents: list[structs.CarState.ButtonEvent]):
    if not self.CP.pcmCruise:
      for b in buttonEvents:
        # The ECM allows enabling on falling edge of set, but only rising edge of resume
        if (b.type == ButtonType.accelCruise and b.pressed) or \
          (b.type == ButtonType.decelCruise and not b.pressed):
          return True
    return False

  def update(self, can_parsers, starpilot_toggles) -> structs.CarState:
    pt_cp = can_parsers[Bus.pt]
    cam_cp = can_parsers[Bus.cam]
    loopback_cp = can_parsers[Bus.loopback]

    ret = structs.CarState()

    volt_like = {
      CAR.CHEVROLET_VOLT,
      CAR.CHEVROLET_VOLT_2019,
      CAR.CHEVROLET_VOLT_ASCM,
      CAR.CHEVROLET_VOLT_CAMERA,
      CAR.CHEVROLET_VOLT_CC,
    }
    kaofui_state_cars = volt_like | SDGM_CAR | ASCM_INT | {
      CAR.CHEVROLET_BLAZER,
      CAR.CHEVROLET_MALIBU_SDGM,
      CAR.CHEVROLET_MALIBU_HYBRID_CC,
    }
    sdgm_non_volt = self.CP.carFingerprint in SDGM_CAR and self.CP.carFingerprint not in kaofui_state_cars

    prev_cruise_buttons = self.cruise_buttons
    prev_hard_cruise_buttons = self.hard_cruise_buttons
    prev_distance_button = self.distance_button
    if not sdgm_non_volt:
      steering_button_msg = pt_cp.vl["ASCMSteeringButton"]
      self.cruise_buttons = steering_button_msg["ACCButtons"]
      self.hard_cruise_buttons = get_hard_cruise_buttons(steering_button_msg)
      self.distance_button = steering_button_msg["DistanceButton"]
      self.buttons_counter = steering_button_msg["RollingCounter"]
      self.steering_button_checksum = steering_button_msg["SteeringButtonChecksum"]
      self.steering_button_ts_nanos = pt_cp.ts_nanos["ASCMSteeringButton"]["ACCButtons"]
      acc_always_one = steering_button_msg["ACCAlwaysOne"]
      acc_hidden_bit = steering_button_msg.get("ACCHiddenBit", 0)
      self.steering_button_prefix = (int(acc_always_one) & 1) | ((int(acc_hidden_bit) & 1) << 6)
    else:
      steering_button_msg = cam_cp.vl["ASCMSteeringButton"]
      self.cruise_buttons = steering_button_msg["ACCButtons"]
      self.hard_cruise_buttons = get_hard_cruise_buttons(steering_button_msg)
      self.distance_button = steering_button_msg["DistanceButton"]
      self.buttons_counter = steering_button_msg["RollingCounter"]
      self.steering_button_ts_nanos = cam_cp.ts_nanos["ASCMSteeringButton"]["ACCButtons"]

    # A GM hard press keeps the normal cruise button signal active too. Suppress
    # the normal button until the wheel reports a different normal state.
    if self.hard_cruise_buttons != CruiseButtons.INIT and self.cruise_buttons in NORMAL_CRUISE_BUTTONS:
      self.force_reset_cruise_buttons = True
    if self.force_reset_cruise_buttons and self.cruise_buttons in NORMAL_CRUISE_BUTTONS:
      self.cruise_buttons = CruiseButtons.UNPRESS
    elif self.force_reset_cruise_buttons and self.cruise_buttons not in NORMAL_CRUISE_BUTTONS:
      self.force_reset_cruise_buttons = False

    self.pscm_status = copy.copy(pt_cp.vl["PSCMStatus"])
    self.moving_backward = (pt_cp.vl["EBCMWheelSpdRear"]["RLWheelDir"] == 2) or (pt_cp.vl["EBCMWheelSpdRear"]["RRWheelDir"] == 2)

    # Variables used for avoiding LKAS faults
    self.loopback_lka_steering_cmd_updated = len(loopback_cp.vl_all["ASCMLKASteeringCmd"]["RollingCounter"]) > 0
    if self.loopback_lka_steering_cmd_updated:
      self.loopback_lka_steering_cmd_ts_nanos = loopback_cp.ts_nanos["ASCMLKASteeringCmd"]["RollingCounter"]
    if self.CP.networkLocation == NetworkLocation.fwdCamera and not self.CP.flags & GMFlags.NO_CAMERA.value:
      self.pt_lka_steering_cmd_counter = pt_cp.vl["ASCMLKASteeringCmd"]["RollingCounter"]
      self.cam_lka_steering_cmd_counter = cam_cp.vl["ASCMLKASteeringCmd"]["RollingCounter"]

    # Sample rear wheel speeds to match the safety which only uses the rear CAN message.
    self.parse_wheel_speeds(ret,
      pt_cp.vl["EBCMWheelSpdFront"]["FLWheelSpd"],
      pt_cp.vl["EBCMWheelSpdFront"]["FRWheelSpd"],
      pt_cp.vl["EBCMWheelSpdRear"]["RLWheelSpd"],
      pt_cp.vl["EBCMWheelSpdRear"]["RRWheelSpd"],
    )
    ret.vEgoCluster = ret.vEgo * getattr(starpilot_toggles, "cluster_offset", 1.0)
    # standstill=True if ECM allows engagement with brake.
    ret.standstill = abs(pt_cp.vl["EBCMWheelSpdRear"]["RLWheelSpd"]) <= STANDSTILL_THRESHOLD and \
                     abs(pt_cp.vl["EBCMWheelSpdRear"]["RRWheelSpd"]) <= STANDSTILL_THRESHOLD

    self._update_car_gps(pt_cp, ret.vEgo)
    pps_cp = can_parsers.get(Bus.adas)
    if pps_cp is not None:
      self._update_pps_gps(pps_cp)

    if pt_cp.vl["ECMPRDNL2"]["ManualMode"] == 1:
      ret.gearShifter = self.parse_gear_shifter("T")
    else:
      ret.gearShifter = self.parse_gear_shifter(self.shifter_values.get(pt_cp.vl["ECMPRDNL2"]["PRNDL2"], None))

    no_accel_pos = bool(self.CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG.value)
    if no_accel_pos:
      if self.CP.carFingerprint in kaofui_state_cars:
        ret.brake = pt_cp.vl.get("EBCMBrakePedalPosition", {}).get("BrakePedalPosition", 0) / 0xd0
      else:
        ret.brake = pt_cp.vl["EBCMBrakePedalPosition"]["BrakePedalPosition"] / 0xd0
    else:
      if self.CP.carFingerprint in kaofui_state_cars:
        ret.brake = pt_cp.vl.get("ECMAcceleratorPos", {}).get("BrakePedalPos", 0)
      else:
        ret.brake = pt_cp.vl["ECMAcceleratorPos"]["BrakePedalPos"]

    if self.CP.carFingerprint == CAR.CHEVROLET_VOLT and no_accel_pos:
      ret.brakePressed = ret.brake >= VOLT_EBCM_BRAKE_PRESSED_THRESHOLD
    elif self.CP.carFingerprint in {CAR.CHEVROLET_MALIBU_CC} or (self.CP.carFingerprint == CAR.CHEVROLET_BLAZER and not no_accel_pos):
      ret.brakePressed = ret.brake >= 8
    elif (self.CP.flags & GMFlags.FORCE_BRAKE_C9.value) or (
      self.CP.networkLocation == NetworkLocation.fwdCamera and
      self.CP.carFingerprint not in (SDGM_CAR | ASCM_INT | {CAR.CHEVROLET_BLAZER})
    ):
      ret.brakePressed = pt_cp.vl["ECMEngineStatus"]["BrakePressed"] != 0
    else:
      # Some Volt 2016-17 have loose brake pedal push rod retainers which causes the ECM to believe
      # that the brake is being intermittently pressed without user interaction.
      # To avoid a cruise fault we need to use a conservative brake position threshold
      # https://static.nhtsa.gov/odi/tsbs/2017/MC-10137629-9999.pdf
      analog_thresh = 0.10 if no_accel_pos else 8
      ret.brakePressed = ret.brake >= analog_thresh

    in_drive_for_hold = ret.gearShifter in (GearShifter.drive, GearShifter.low, GearShifter.manumatic)
    self.auto_hold_drive_time, self.one_pedal_drive_time = update_auto_hold_drive_timers(
      in_drive_for_hold, ret.vEgo > 0.1, self.auto_hold_drive_time, self.one_pedal_drive_time
    )
    if not in_drive_for_hold:
      self.auto_hold_armed = False
      self.auto_hold_engaged = False

    # Regen braking is braking
    if self.CP.transmissionType == TransmissionType.direct:
      ret.regenBraking = pt_cp.vl["EBCMRegenPaddle"]["RegenPaddle"] != 0
      if not ret.regenBraking and self.user_regen_paddle_pressed:
        self.regen_release_timer = AUTO_HOLD_REGEN_RELEASE_COOLDOWN_S
      self.single_pedal_mode = (ret.gearShifter == GearShifter.low or
                                pt_cp.vl["EVDriveMode"]["SinglePedalModeActive"] == 1 or
                                (ret.regenBraking and ret.gearShifter == GearShifter.manumatic) or
                                (self.CP.carFingerprint in {
                                  CAR.CHEVROLET_BOLT_ACC_2022_2023,
                                  CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
                                  CAR.CHEVROLET_BOLT_CC_2022_2023,
                                } and self.CP.enableGasInterceptorDEPRECATED))
      self.user_regen_paddle_pressed = ret.regenBraking

    if self.regen_release_timer > 0.0:
      self.regen_release_timer = max(self.regen_release_timer - DT_CTRL, 0.0)

    if self.CP.enableGasInterceptorDEPRECATED:
      gas = (pt_cp.vl["GAS_SENSOR"]["INTERCEPTOR_GAS"] + pt_cp.vl["GAS_SENSOR"]["INTERCEPTOR_GAS2"]) / 2.
      # Panda 595 threshold ~= 23.65. Keep below to avoid interceptor faulting from blocked frames.
      threshold = 23 if self.CP.carFingerprint in CAMERA_ACC_CAR else 4
      ret.gasPressed = gas > threshold
    else:
      gas = pt_cp.vl["AcceleratorPedal2"]["AcceleratorPedal2"] / 254.
      ret.gasPressed = gas > 1e-5

    # Keep scalar pedal value for legacy consumers on schemas that removed CarState.gas.
    ret.gasDEPRECATED = gas

    ret.steeringAngleDeg = pt_cp.vl["PSCMSteeringAngle"]["SteeringWheelAngle"]
    ret.steeringRateDeg = pt_cp.vl["PSCMSteeringAngle"]["SteeringWheelRate"]
    ret.steeringTorque = pt_cp.vl["PSCMStatus"]["LKADriverAppldTrq"]
    ret.steeringTorqueEps = pt_cp.vl["PSCMStatus"]["LKATorqueDelivered"]
    ret.steeringPressed = abs(ret.steeringTorque) > STEER_THRESHOLD

    # 0 inactive, 1 active, 2 temporarily limited, 3 failed
    self.lkas_status = pt_cp.vl["PSCMStatus"]["LKATorqueDeliveredStatus"]
    ret.steerFaultTemporary = self.lkas_status == 2
    ret.steerFaultPermanent = self.lkas_status == 3

    if not sdgm_non_volt:
      # 1 - open, 0 - closed
      ret.doorOpen = (pt_cp.vl["BCMDoorBeltStatus"]["FrontLeftDoor"] == 1 or
                      pt_cp.vl["BCMDoorBeltStatus"]["FrontRightDoor"] == 1 or
                      pt_cp.vl["BCMDoorBeltStatus"]["RearLeftDoor"] == 1 or
                      pt_cp.vl["BCMDoorBeltStatus"]["RearRightDoor"] == 1)

      # 1 - latched
      ret.seatbeltUnlatched = pt_cp.vl["BCMDoorBeltStatus"]["LeftSeatBelt"] == 0
      ret.leftBlinker = pt_cp.vl["BCMTurnSignals"]["TurnSignals"] == 1
      ret.rightBlinker = pt_cp.vl["BCMTurnSignals"]["TurnSignals"] == 2
      ret.parkingBrake = pt_cp.vl["BCMGeneralPlatformStatus"]["ParkBrakeSwActive"] == 1
    else:
      # 1 - open, 0 - closed
      ret.doorOpen = (cam_cp.vl["BCMDoorBeltStatus"]["FrontLeftDoor"] == 1 or
                      cam_cp.vl["BCMDoorBeltStatus"]["FrontRightDoor"] == 1 or
                      cam_cp.vl["BCMDoorBeltStatus"]["RearLeftDoor"] == 1 or
                      cam_cp.vl["BCMDoorBeltStatus"]["RearRightDoor"] == 1)

      # 1 - latched
      ret.seatbeltUnlatched = cam_cp.vl["BCMDoorBeltStatus"]["LeftSeatBelt"] == 0
      ret.leftBlinker = cam_cp.vl["BCMTurnSignals"]["TurnSignals"] == 1
      ret.rightBlinker = cam_cp.vl["BCMTurnSignals"]["TurnSignals"] == 2
      ret.parkingBrake = cam_cp.vl["BCMGeneralPlatformStatus"]["ParkBrakeSwActive"] == 1

    ret.cruiseState.available = pt_cp.vl["ECMEngineStatus"]["CruiseMainOn"] != 0
    ret.espDisabled = pt_cp.vl["ESPStatus"]["TractionControlOn"] != 1
    ret.accFaulted = (pt_cp.vl["AcceleratorPedal2"]["CruiseState"] == AccState.FAULTED or
                      pt_cp.vl["EBCMFrictionBrakeStatus"]["FrictionBrakeUnavailable"] == 1)

    ret.cruiseState.enabled = pt_cp.vl["AcceleratorPedal2"]["CruiseState"] != AccState.OFF
    ret.cruiseState.standstill = pt_cp.vl["AcceleratorPedal2"]["CruiseState"] == AccState.STANDSTILL
    self.stock_fcw_alert = 0
    ret.stockFcw = False
    if self.CP.networkLocation == NetworkLocation.fwdCamera and not self.CP.flags & GMFlags.NO_CAMERA.value:
      has_acc_dashboard_status = self.CP.carFingerprint not in CC_ONLY_CAR or self.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL
      if has_acc_dashboard_status:
        acc_dashboard_status = cam_cp.vl["ASCMActiveCruiseControlStatus"]
        if self.CP.carFingerprint not in CC_ONLY_CAR:
          ret.cruiseState.speed = acc_dashboard_status["ACCSpeedSetpoint"] * CV.KPH_TO_MS
        # Preserve the stock camera FCW level from 0x370 so the controller can
        # replay it when that message is blocked and spoofed by openpilot long.
        self.stock_fcw_alert = int(acc_dashboard_status["FCWAlert"])
        ret.stockFcw = self.stock_fcw_alert != 0

      if self.CP.carFingerprint not in SDGM_CAR:
        ret.stockAeb = cam_cp.vl["AEBCmd"]["AEBCmdActive"] != 0
      else:
        ret.stockAeb = False

      # openpilot controls nonAdaptive when not pcmCruise
      if self.CP.pcmCruise and self.CP.carFingerprint not in ASCM_INT:
        ret.cruiseState.nonAdaptive = cam_cp.vl["ASCMActiveCruiseControlStatus"]["ACCCruiseState"] not in (2, 3)

    if self.CP.carFingerprint in CC_ONLY_CAR:
      self.ecm_cruise_control_ts_nanos = pt_cp.ts_nanos["ECMCruiseControl"]["CruiseActive"]
      self.accelerator_pedal2_ts_nanos = pt_cp.ts_nanos["AcceleratorPedal2"]["CruiseState"]
      ret.accFaulted = False
      ret.cruiseState.speed = pt_cp.vl["ECMCruiseControl"]["CruiseSetSpeed"] * CV.KPH_TO_MS
      if self.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
        try:
          ret.cruiseState.enabled = cam_cp.vl["ASCMActiveCruiseControlStatus"]["ACCCmdActive"] != 0
        except Exception:
          ret.cruiseState.enabled = pt_cp.vl["ECMCruiseControl"]["CruiseActive"] != 0
      else:
        try:
          ret.cruiseState.enabled = pt_cp.vl["ECMCruiseControl"]["CruiseActive"] != 0
        except Exception:
          ret.cruiseState.enabled = cam_cp.vl["ASCMActiveCruiseControlStatus"]["ACCCmdActive"] != 0
    else:
      self.ecm_cruise_control_ts_nanos = 0
      self.accelerator_pedal2_ts_nanos = 0

    if self.auto_hold_fault_suppression_timer > 0.0:
      self.auto_hold_fault_suppression_timer = max(self.auto_hold_fault_suppression_timer - DT_CTRL, 0.0)
      ret.accFaulted = False

    if self.CP.enableBsm and not sdgm_non_volt:
      ret.leftBlindspot = pt_cp.vl["BCMBlindSpotMonitor"]["LeftBSM"] == 1
      ret.rightBlindspot = pt_cp.vl["BCMBlindSpotMonitor"]["RightBSM"] == 1
    elif self.CP.enableBsm:
      ret.leftBlindspot = cam_cp.vl["BCMBlindSpotMonitor"]["LeftBSM"] == 1
      ret.rightBlindspot = cam_cp.vl["BCMBlindSpotMonitor"]["RightBSM"] == 1

    self.lkas_previously_enabled = self.lkas_enabled
    if sdgm_non_volt:
      self.lkas_enabled = cam_cp.vl["ASCMSteeringButton"]["LKAButton"]
    else:
      self.lkas_enabled = pt_cp.vl["ASCMSteeringButton"]["LKAButton"]
    self.pcm_acc_status = pt_cp.vl["AcceleratorPedal2"]["CruiseState"]

    # Only activate cancel remap when panda safety was configured for it at startup.
    remap_cancel_to_distance = bool(self.CP.alternativeExperience & ALTERNATIVE_EXPERIENCE.GM_REMAP_CANCEL_TO_DISTANCE)
    malibu_cancel_passthrough = (
      remap_cancel_to_distance and
      self.CP.carFingerprint == CAR.CHEVROLET_MALIBU_HYBRID_CC and
      self.CP.openpilotLongitudinalControl and
      bool(self.CP.flags & GMFlags.PEDAL_LONG.value)
    )
    bolt_cancel_button = (
      remap_cancel_to_distance and
      self.CP.carFingerprint in BOLT_CANCEL_BUTTON_CARS and
      self.CP.openpilotLongitudinalControl and
      bool(self.CP.flags & GMFlags.PEDAL_LONG.value)
    )
    bolt_cancel_lkas_conflict = bolt_cancel_button and self.CP.carFingerprint in BOLT_GEN1_CANCEL_PERSONALITY_CARS

    cruise_button_map = BUTTONS_DICT
    if malibu_cancel_passthrough or bolt_cancel_button:
      cruise_button_map = {k: v for k, v in BUTTONS_DICT.items() if k != CruiseButtons.CANCEL}

    cruise_events = create_button_events(
      self.cruise_buttons, prev_cruise_buttons, cruise_button_map, unpressed_btn=CruiseButtons.UNPRESS
    )
    suppress_malibu_side_buttons = malibu_cancel_passthrough and (
      self.cruise_buttons in (CruiseButtons.CANCEL, CruiseButtons.MAIN) or
      prev_cruise_buttons in (CruiseButtons.CANCEL, CruiseButtons.MAIN)
    )
    suppress_bolt_cancel_lkas = bolt_cancel_lkas_conflict and (
      self.cruise_buttons == CruiseButtons.CANCEL or
      prev_cruise_buttons == CruiseButtons.CANCEL
    )
    distance_events = [] if suppress_malibu_side_buttons else create_button_events(
      self.distance_button, prev_distance_button, {1: ButtonType.gapAdjustCruise}
    )
    lkas_events = [] if (suppress_malibu_side_buttons or suppress_bolt_cancel_lkas) else create_button_events(
      self.lkas_enabled, self.lkas_previously_enabled, {1: ButtonType.lkas}
    )
    hard_cruise_events = create_button_events(
      self.hard_cruise_buttons, prev_hard_cruise_buttons, HARD_BUTTONS_DICT, unpressed_btn=CruiseButtons.INIT
    )

    # Don't add events if transitioning from INIT, unless it's to an actual button.
    if (self.cruise_buttons != CruiseButtons.UNPRESS or prev_cruise_buttons != CruiseButtons.INIT or
        self.hard_cruise_buttons != CruiseButtons.INIT or prev_hard_cruise_buttons != CruiseButtons.INIT):
      ret.buttonEvents = [
        *cruise_events,
        *distance_events,
        *lkas_events,
        *hard_cruise_events,
      ]

    if ret.vEgo < self.CP.minSteerSpeed:
      ret.lowSpeedAlert = True

    fp_ret = custom.StarPilotCarState.new_message()
    fp_ret.accelHardCruise = self.hard_cruise_buttons == CruiseButtons.RES_ACCEL or prev_hard_cruise_buttons == CruiseButtons.RES_ACCEL
    fp_ret.decelHardCruise = self.hard_cruise_buttons == CruiseButtons.DECEL_SET or prev_hard_cruise_buttons == CruiseButtons.DECEL_SET
    if bolt_cancel_button and self.cruise_buttons == CruiseButtons.CANCEL:
      fp_ret.cancelPressed = True
    fp_ret.sportGear = pt_cp.vl["SportMode"]["SportMode"] == 1

    return ret, fp_ret

  @staticmethod
  def get_can_parsers(CP):
    gps_config = get_car_gps_config(CP)
    gps_messages = [(name, 0) for name in gps_config.messages] if gps_config is not None else []

    volt_like = {
      CAR.CHEVROLET_VOLT,
      CAR.CHEVROLET_VOLT_2019,
      CAR.CHEVROLET_VOLT_ASCM,
      CAR.CHEVROLET_VOLT_CAMERA,
      CAR.CHEVROLET_VOLT_CC,
    }
    kaofui_state_cars = volt_like | SDGM_CAR | ASCM_INT | {
      CAR.CHEVROLET_BLAZER,
      CAR.CHEVROLET_MALIBU_SDGM,
      CAR.CHEVROLET_MALIBU_HYBRID_CC,
    }
    sdgm_non_volt = CP.carFingerprint in SDGM_CAR and CP.carFingerprint not in kaofui_state_cars

    pt_messages = [
      ("PSCMStatus", 10),
      ("ESPStatus", 10),
      ("EBCMWheelSpdFront", 20),
      ("EBCMWheelSpdRear", 20),
      ("EBCMFrictionBrakeStatus", 20),
      ("PSCMSteeringAngle", 100),
      ("ECMAcceleratorPos", 80),
      ("SportMode", 0),
      *gps_messages,
    ]

    prndl2_rate = 10 if CP.carFingerprint in kaofui_state_cars else 40
    if sdgm_non_volt:
      pt_messages += [
        ("ECMPRDNL2", prndl2_rate),
        ("AcceleratorPedal2", 40),
        ("ECMEngineStatus", 80),
      ]
    else:
      pt_messages += [
        ("ECMPRDNL2", prndl2_rate),
        ("AcceleratorPedal2", 33),
        ("ECMEngineStatus", 100),
        ("BCMTurnSignals", 1),
        ("BCMDoorBeltStatus", 10),
        ("BCMGeneralPlatformStatus", 10),
        ("ASCMSteeringButton", 33),
      ]
      if CP.enableBsm:
        pt_messages.append(("BCMBlindSpotMonitor", 0))

    if CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG.value:
      if ("ECMAcceleratorPos", 80) in pt_messages:
        pt_messages.remove(("ECMAcceleratorPos", 80))
      pt_messages.append(("EBCMBrakePedalPosition", 100))

    if CP.networkLocation == NetworkLocation.fwdCamera:
      pt_messages += [
        ("ASCMLKASteeringCmd", 0),
      ]

    if CP.transmissionType == TransmissionType.direct:
      regen_paddle_rate = 50 if CP.carFingerprint in kaofui_state_cars else 40
      pt_messages += [
        ("EBCMRegenPaddle", regen_paddle_rate),
        ("EVDriveMode", 0),
      ]

    if CP.carFingerprint in CC_ONLY_CAR:
      pt_messages += [
        ("ECMCruiseControl", 10),
      ]

    if CP.enableGasInterceptorDEPRECATED:
      pt_messages += [
        ("GAS_SENSOR", 50),
      ]

    cam_messages = []
    if CP.networkLocation == NetworkLocation.fwdCamera and not CP.flags & GMFlags.NO_CAMERA.value:
      cam_messages += [
        ("ASCMLKASteeringCmd", 10),
      ]
      if sdgm_non_volt:
        cam_messages += [
          ("BCMTurnSignals", 1),
          ("BCMDoorBeltStatus", 10),
          ("BCMGeneralPlatformStatus", 10),
          ("ASCMSteeringButton", 33),
        ]
        if CP.enableBsm:
          cam_messages.append(("BCMBlindSpotMonitor", 0))
      elif CP.carFingerprint in ASCM_INT:
        # Volt/ASCM-int variants don't reliably have AEBCmd present at startup,
        # but when it appears we still want to surface OEM AEB state.
        cam_messages += [
          ("AEBCmd", 0),
        ]
      elif CP.carFingerprint not in SDGM_CAR:
        cam_messages += [
          ("AEBCmd", 10),
        ]
      if CP.carFingerprint not in CC_ONLY_CAR or CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
        cam_messages += [
          ("ASCMActiveCruiseControlStatus", 25),
        ]

    loopback_messages = [
      ("ASCMLKASteeringCmd", 0),
    ]

    parsers = {
      Bus.pt: CANParser(DBC[CP.carFingerprint][Bus.pt], pt_messages, CanBus.POWERTRAIN),
      Bus.cam: CANParser(DBC[CP.carFingerprint][Bus.pt], cam_messages, CanBus.CAMERA),
      Bus.loopback: CANParser(DBC[CP.carFingerprint][Bus.pt], loopback_messages, CanBus.LOOPBACK),
    }
    if getattr(CP, "brand", None) == "gm":
      # Optional CT6 PPS parser on Bus.adas; non-PPS vehicles remain CAN-valid.
      parsers[Bus.adas] = CANParser(
        "cadillac_ct6_object",
        [(name, 0) for name in PPS_GPS_MESSAGES],
        CanBus.POWERTRAIN,
      )
    return parsers
