# Ford-specific additions first imported in StarPilot 3f6ccd104e substantially adapt BluePilot
# bp-7.0 vehicle-state work, including a sunnypilot extension with the Haibin Wen/contributors
# notice retained in THIRD_PARTY_NOTICES.md. See the repository root CREDITS.md for provenance.
from cereal import custom
from opendbc.can import CANDefine, CANParser
from opendbc.car import Bus, create_button_events, structs
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.ford.fordcan import CanBus
from opendbc.car.ford.values import DBC, CarControllerParams, FordFlags
from opendbc.car.gps import get_car_gps_config
from opendbc.car.interfaces import CarStateBase

ButtonType = structs.CarState.ButtonEvent.Type
GearShifter = structs.CarState.GearShifter
TransmissionType = structs.CarParams.TransmissionType


class CarState(CarStateBase):
  def __init__(self, CP, FPCP):
    super().__init__(CP, FPCP)
    can_define = CANDefine(DBC[CP.carFingerprint][Bus.pt])
    if CP.transmissionType == TransmissionType.automatic:
      if CP.flags & FordFlags.CANFD:
        self.shifter_values = can_define.dv["Gear_Shift_by_Wire_FD1"]["TrnRng_D_RqGsm"]
      elif CP.flags & FordFlags.ALT_STEER_ANGLE:
        self.shifter_values = can_define.dv["TransGearData"]["GearLvrPos_D_Actl"]
      else:
        self.shifter_values = can_define.dv["PowertrainData_10"]["TrnRng_D_Rq"]

    self.distance_button = 0
    self.lc_button = 0
    self.lkas_available = False
    self.lateral_motion_control = None
    self.lateral_control_status = None
    self.steering_angle_offset_deg = 0.0
    self.car_gps_config = get_car_gps_config(CP)
    self.car_gps_supported = self.car_gps_config is not None
    self.car_gps = None
    self._car_gps_timestamp_nanos = 0

  def _update_car_gps(self, cp) -> None:
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
      self.car_gps = gps
      self._car_gps_timestamp_nanos = timestamp_nanos

  def get_car_gps(self):
    return self.car_gps

  def update(self, can_parsers, starpilot_toggles) -> structs.CarState:
    cp = can_parsers[Bus.pt]
    cp_cam = can_parsers[Bus.cam]

    self._update_car_gps(cp)

    ret = structs.CarState()

    if self.CP.flags & FordFlags.ALT_STEER_ANGLE:
      sensors_valid = (
        int((cp.vl["ParkAid_Data"]["ExtSteeringAngleReq2"] + 1000) * 10) not in (32766, 32767)
        and cp.vl["ParkAid_Data"]["EPASExtAngleStatReq"] == 0
        and cp.vl["ParkAid_Data"]["ApaSys_D_Stat"] in (0, 1)
      )
      ret.vehicleSensorsInvalid = not sensors_valid
    else:
      # The ABS can recalibrate the steering pinion offset briefly after startup.
      ret.vehicleSensorsInvalid = cp.vl["SteeringPinion_Data"]["StePinCompAnEst_D_Qf"] != 3

    # car speed
    ret.vEgoRaw = cp.vl["BrakeSysFeatures"]["Veh_V_ActlBrk"] * CV.KPH_TO_MS
    ret.vEgo, ret.aEgo = self.update_speed_kf(ret.vEgoRaw)
    if self.CP.flags & FordFlags.CANFD:
      ret.vEgoCluster = ((cp.vl["Cluster_Info_3_FD1"]["DISPLAY_SPEED_SCALING"] / 100) *
                         cp.vl["EngVehicleSpThrottle2"]["Veh_V_ActlEng"] +
                         cp.vl["Cluster_Info_3_FD1"]["DISPLAY_SPEED_OFFSET"]) * CV.KPH_TO_MS
    ret.yawRate = cp.vl["Yaw_Data_FD1"]["VehYaw_W_Actl"]
    ret.standstill = cp.vl["DesiredTorqBrk"]["VehStop_D_Stat"] == 1

    # gas pedal
    ret.gasPressed = cp.vl["EngVehicleSpThrottle"]["ApedPos_Pc_ActlArb"] / 100. > 1e-6

    # brake pedal
    ret.brake = cp.vl["BrakeSnData_4"]["BrkTot_Tq_Actl"] / 32756.  # torque in Nm
    ret.brakePressed = cp.vl["EngBrakeData"]["BpedDrvAppl_D_Actl"] == 2
    ret.parkingBrake = cp.vl["DesiredTorqBrk"]["PrkBrkStatus"] in (1, 2)

    # steering wheel
    if self.CP.flags & FordFlags.ALT_STEER_ANGLE:
      steering_angle_init = cp.vl["SteeringPinion_Data_Alt"]["StePinRelInit_An_Sns"]
      if not ret.vehicleSensorsInvalid:
        steering_angle_est = cp.vl["ParkAid_Data"]["ExtSteeringAngleReq2"]
        self.steering_angle_offset_deg = steering_angle_est - steering_angle_init
      ret.steeringAngleDeg = steering_angle_init + self.steering_angle_offset_deg
    else:
      ret.steeringAngleDeg = cp.vl["SteeringPinion_Data"]["StePinComp_An_Est"]
    ret.steeringTorque = cp.vl["EPAS_INFO"]["SteeringColumnTorque"]
    ret.steeringPressed = self.update_steering_pressed(abs(ret.steeringTorque) > CarControllerParams.STEER_DRIVER_ALLOWANCE, 5)
    ret.steerFaultTemporary = cp.vl["EPAS_INFO"]["EPAS_Failure"] == 1
    ret.steerFaultPermanent = cp.vl["EPAS_INFO"]["EPAS_Failure"] in (2, 3)
    ret.espDisabled = cp.vl["Cluster_Info1_FD1"]["DrvSlipCtlMde_D_Rq"] != 0  # 0 is default mode

    if self.CP.flags & FordFlags.CANFD:
      # this signal is always 0 on non-CAN FD cars
      self.lateral_control_status = int(cp.vl["Lane_Assist_Data3_FD1"]["LatCtlSte_D_Stat"])
      ret.steerFaultTemporary |= self.lateral_control_status not in (1, 2, 3)

    # cruise state
    is_metric = cp.vl["INSTRUMENT_PANEL"]["METRIC_UNITS"] == 1 if not self.CP.flags & FordFlags.CANFD else \
      cp_cam.vl["IPMA_Data2"]["IsaVLimUnit_D_Rq"] == 1
    ret.cruiseState.speed = cp.vl["EngBrakeData"]["Veh_V_DsplyCcSet"] * (CV.KPH_TO_MS if is_metric else CV.MPH_TO_MS)
    ret.cruiseState.enabled = cp.vl["EngBrakeData"]["CcStat_D_Actl"] in (4, 5)
    ret.cruiseState.available = cp.vl["EngBrakeData"]["CcStat_D_Actl"] in (3, 4, 5)
    ret.cruiseState.nonAdaptive = cp.vl["Cluster_Info1_FD1"]["AccEnbl_B_RqDrv"] == 0
    ret.cruiseState.standstill = cp.vl["EngBrakeData"]["AccStopMde_D_Rq"] == 3
    ret.accFaulted = cp.vl["EngBrakeData"]["CcStat_D_Actl"] in (1, 2)
    if not self.CP.openpilotLongitudinalControl:
      ret.accFaulted = ret.accFaulted or cp_cam.vl["ACCDATA"]["CmbbDeny_B_Actl"] == 1

    # gear
    if self.CP.transmissionType == TransmissionType.automatic:
      if self.CP.flags & FordFlags.CANFD:
        gear = self.shifter_values.get(cp.vl["Gear_Shift_by_Wire_FD1"]["TrnRng_D_RqGsm"])
      elif self.CP.flags & FordFlags.ALT_STEER_ANGLE:
        gear = self.shifter_values.get(cp.vl["TransGearData"]["GearLvrPos_D_Actl"])
      else:
        gear = self.shifter_values.get(cp.vl["PowertrainData_10"]["TrnRng_D_Rq"])
      ret.gearShifter = self.parse_gear_shifter(gear)
    elif self.CP.transmissionType == TransmissionType.manual:
      if bool(cp.vl["BCM_Lamp_Stat_FD1"]["RvrseLghtOn_B_Stat"]):
        ret.gearShifter = GearShifter.reverse
      else:
        ret.gearShifter = GearShifter.drive

    # safety
    ret.stockFcw = bool(cp_cam.vl["ACCDATA_3"]["FcwVisblWarn_B_Rq"])
    ret.stockAeb = bool(cp_cam.vl["ACCDATA_2"]["CmbbBrkDecel_B_Rq"])

    # button presses
    ret.leftBlinker = cp.vl["Steering_Data_FD1"]["TurnLghtSwtch_D_Stat"] == 1
    ret.rightBlinker = cp.vl["Steering_Data_FD1"]["TurnLghtSwtch_D_Stat"] == 2
    # TODO: block this going to the camera otherwise it will enable stock TJA
    ret.genericToggle = bool(cp.vl["Steering_Data_FD1"]["TjaButtnOnOffPress"])
    prev_distance_button = self.distance_button
    prev_lc_button = self.lc_button
    self.distance_button = cp.vl["Steering_Data_FD1"]["AccButtnGapTogglePress"]
    self.lc_button = bool(cp.vl["Steering_Data_FD1"]["TjaButtnOnOffPress"])

    # lock info
    ret.doorOpen = any([cp.vl["BodyInfo_3_FD1"]["DrStatDrv_B_Actl"], cp.vl["BodyInfo_3_FD1"]["DrStatPsngr_B_Actl"],
                        cp.vl["BodyInfo_3_FD1"]["DrStatRl_B_Actl"], cp.vl["BodyInfo_3_FD1"]["DrStatRr_B_Actl"]])
    ret.seatbeltUnlatched = cp.vl["RCMStatusMessage2_FD1"]["FirstRowBuckleDriver"] == 2

    # blindspot sensors
    if self.CP.enableBsm:
      cp_bsm = cp_cam if self.CP.flags & FordFlags.CANFD else cp
      ret.leftBlindspot = cp_bsm.vl["Side_Detect_L_Stat"]["SodDetctLeft_D_Stat"] != 0
      ret.rightBlindspot = cp_bsm.vl["Side_Detect_R_Stat"]["SodDetctRight_D_Stat"] != 0

    # Stock steering buttons so that we can passthru blinkers etc.
    self.buttons_stock_values = cp.vl["Steering_Data_FD1"]
    # Stock values from IPMA so that we can retain some stock functionality
    self.acc_tja_status_stock_values = cp_cam.vl["ACCDATA_3"]
    self.lkas_status_stock_values = cp_cam.vl["IPMA_Data"]
    if self.CP.flags & FordFlags.LKA_STEERING:
      try:
        self.lkas_available = cp.vl["Lane_Assist_Data3_FD1"]["LaActAvail_D_Actl"] == 3
      except KeyError:
        self.lkas_available = False
      try:
        self.lateral_motion_control = cp_cam.vl["LateralMotionControl"]
      except KeyError:
        self.lateral_motion_control = None

    ret.buttonEvents = [
      *create_button_events(self.distance_button, prev_distance_button, {1: ButtonType.gapAdjustCruise}),
      *create_button_events(self.lc_button, prev_lc_button, {1: ButtonType.lkas}),
    ]

    fp_ret = custom.StarPilotCarState.new_message()
    fp_ret.brakeLights = ret.brakePressed
    try:
      fp_ret.brakeLights = bool(cp.vl["BCM_Lamp_Stat_FD1"]["StopLghtOn_B_Stat"])
    except (KeyError, AttributeError):
      try:
        fp_ret.brakeLights = cp.vl["BrakeSysFeatures_2"]["BrkLamp_B_Rq"] == 1
      except (KeyError, AttributeError):
        pass

    try:
      speed_limit = cp_cam.vl["Traffic_RecognitnData"]["TsrVLim1MsgTxt_D_Rq"]
      speed_limit_unit = cp_cam.vl["Traffic_RecognitnData"]["TsrVlUnitMsgTxt_D_Rq"]
      speed_factor = CV.MPH_TO_MS if speed_limit_unit == 2 else CV.KPH_TO_MS if speed_limit_unit == 1 else 0.0
      fp_ret.dashboardSpeedLimit = speed_limit * speed_factor if speed_limit not in (0, 255) else 0.0
    except (KeyError, AttributeError):
      fp_ret.dashboardSpeedLimit = 0.0

    return ret, fp_ret

  @staticmethod
  def get_can_parsers(CP):
    gps_config = get_car_gps_config(CP)
    gps_messages = [(name, 0) for name in gps_config.messages] if gps_config is not None else []

    pt_messages = [
      ("BrakeSysFeatures", 50),
      ("Yaw_Data_FD1", 100),
      ("DesiredTorqBrk", 50),
      ("EngVehicleSpThrottle", 100),
      ("EngVehicleSpThrottle2", 50),
      ("BrakeSnData_4", 50),
      ("EngBrakeData", 10),
      ("EPAS_INFO", 50),
      ("Cluster_Info1_FD1", 10),
      ("Steering_Data_FD1", 10),
      ("BodyInfo_3_FD1", 2),
      ("RCMStatusMessage2_FD1", 10),
      ("BCM_Lamp_Stat_FD1", 0),
      *gps_messages,
    ]

    if CP.flags & FordFlags.ALT_STEER_ANGLE:
      pt_messages += [
        ("SteeringPinion_Data_Alt", 100),
        ("ParkAid_Data", 50),
      ]
    else:
      pt_messages += [("SteeringPinion_Data", 100)]

    if CP.flags & FordFlags.CANFD:
      pt_messages += [
        ("Lane_Assist_Data3_FD1", 33),
        ("Cluster_Info_3_FD1", 10),
      ]
    else:
      pt_messages += [("INSTRUMENT_PANEL", 1)]

    if CP.transmissionType == TransmissionType.automatic:
      if CP.flags & FordFlags.CANFD:
        pt_messages += [("Gear_Shift_by_Wire_FD1", 10)]
      elif CP.flags & FordFlags.ALT_STEER_ANGLE:
        pt_messages += [("TransGearData", 10)]
      else:
        pt_messages += [("PowertrainData_10", 10)]

    if CP.enableBsm and not (CP.flags & FordFlags.CANFD):
      pt_messages += [
        ("Side_Detect_L_Stat", 5),
        ("Side_Detect_R_Stat", 5),
      ]

    cam_messages = [
      ("ACCDATA", 50),
      ("ACCDATA_2", 50),
      ("ACCDATA_3", 5),
      ("IPMA_Data", 1),
    ]

    if CP.flags & FordFlags.CANFD:
      cam_messages += [
        ("Traffic_RecognitnData", 1),
        ("IPMA_Data2", 1),
      ]
    else:
      cam_messages += [("Traffic_RecognitnData", 0)]

    if CP.enableBsm and CP.flags & FordFlags.CANFD:
      cam_messages += [
        ("Side_Detect_L_Stat", 5),
        ("Side_Detect_R_Stat", 5),
      ]

    if CP.flags & FordFlags.LKA_STEERING:
      cam_messages += [("LateralMotionControl", 20)]

    return {
      Bus.pt: CANParser(DBC[CP.carFingerprint][Bus.pt], pt_messages, CanBus(CP).main),
      Bus.cam: CANParser(DBC[CP.carFingerprint][Bus.pt], cam_messages, CanBus(CP).camera),
    }
