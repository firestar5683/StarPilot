import copy
from cereal import custom
from opendbc.can import CANDefine, CANParser
from opendbc.car import Bus, create_button_events, structs
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.interfaces import CarStateBase
from opendbc.car.gm.values import (
  ALT_ACCS,
  ASCM_INT,
  CAMERA_ACC_CAR,
  CAR,
  CC_ONLY_CAR,
  CC_REGEN_PADDLE_CAR,
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

BUTTONS_DICT = {CruiseButtons.RES_ACCEL: ButtonType.accelCruise, CruiseButtons.DECEL_SET: ButtonType.decelCruise,
                CruiseButtons.MAIN: ButtonType.mainCruise, CruiseButtons.CANCEL: ButtonType.cancel}

# OPGM variables
GearShifter = structs.CarState.GearShifter
BOLT_GEN1_CANCEL_PERSONALITY_CARS = {
  CAR.CHEVROLET_BOLT_CC_2017,
  CAR.CHEVROLET_BOLT_CC_2018_2021,
}


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

    # OPGM variables
    self.single_pedal_mode = False

    self.pedal_steady = 0
    self.ecm_cruise_control_ts_nanos = 0
    self.accelerator_pedal2_ts_nanos = 0
    self.moving_backward = False
    self.lkas_previously_enabled = 0
    self.lkas_enabled = 0
    self.pcm_acc_status = AccState.OFF

  def update_button_enable(self, buttonEvents: list[structs.CarState.ButtonEvent]):
    if not self.CP.pcmCruise:
      for b in buttonEvents:
        # The ECM allows enabling on falling edge of set, but only rising edge of resume
        if (b.type == ButtonType.accelCruise and b.pressed) or \
          (b.type == ButtonType.decelCruise and not b.pressed):
          return True
    return False

  def update(self, can_parsers, frogpilot_toggles) -> structs.CarState:
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
    prev_distance_button = self.distance_button
    if not sdgm_non_volt:
      self.cruise_buttons = pt_cp.vl["ASCMSteeringButton"]["ACCButtons"]
      self.distance_button = pt_cp.vl["ASCMSteeringButton"]["DistanceButton"]
      self.buttons_counter = pt_cp.vl["ASCMSteeringButton"]["RollingCounter"]
      self.steering_button_checksum = pt_cp.vl["ASCMSteeringButton"]["SteeringButtonChecksum"]
      self.steering_button_ts_nanos = pt_cp.ts_nanos["ASCMSteeringButton"]["ACCButtons"]
      acc_always_one = pt_cp.vl["ASCMSteeringButton"]["ACCAlwaysOne"]
      acc_hidden_bit = pt_cp.vl["ASCMSteeringButton"].get("ACCHiddenBit", 0)
      self.steering_button_prefix = (int(acc_always_one) & 1) | ((int(acc_hidden_bit) & 1) << 6)
    else:
      self.cruise_buttons = cam_cp.vl["ASCMSteeringButton"]["ACCButtons"]
      self.distance_button = cam_cp.vl["ASCMSteeringButton"]["DistanceButton"]
      self.buttons_counter = cam_cp.vl["ASCMSteeringButton"]["RollingCounter"]
      self.steering_button_ts_nanos = cam_cp.ts_nanos["ASCMSteeringButton"]["ACCButtons"]
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
    ret.vEgoCluster = ret.vEgo * getattr(frogpilot_toggles, "cluster_offset", 1.0)
    # standstill=True if ECM allows engagement with brake.
    ret.standstill = abs(pt_cp.vl["EBCMWheelSpdRear"]["RLWheelSpd"]) <= STANDSTILL_THRESHOLD and \
                     abs(pt_cp.vl["EBCMWheelSpdRear"]["RRWheelSpd"]) <= STANDSTILL_THRESHOLD

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

    if self.CP.carFingerprint in {CAR.CHEVROLET_MALIBU_CC} or (self.CP.carFingerprint == CAR.CHEVROLET_BLAZER and not no_accel_pos):
      ret.brakePressed = ret.brake >= 8
    elif (self.CP.flags & GMFlags.FORCE_BRAKE_C9.value) or ((self.CP.networkLocation == NetworkLocation.fwdCamera) and (self.CP.carFingerprint != CAR.CHEVROLET_BLAZER)):
      ret.brakePressed = pt_cp.vl["ECMEngineStatus"]["BrakePressed"] != 0
    else:
      # Some Volt 2016-17 have loose brake pedal push rod retainers which causes the ECM to believe
      # that the brake is being intermittently pressed without user interaction.
      # To avoid a cruise fault we need to use a conservative brake position threshold
      # https://static.nhtsa.gov/odi/tsbs/2017/MC-10137629-9999.pdf
      analog_thresh = 0.10 if no_accel_pos else 8
      ret.brakePressed = ret.brake >= analog_thresh

    # Regen braking is braking
    if self.CP.transmissionType == TransmissionType.direct:
      ret.regenBraking = pt_cp.vl["EBCMRegenPaddle"]["RegenPaddle"] != 0
      self.single_pedal_mode = (ret.gearShifter == GearShifter.low or
                                pt_cp.vl["EVDriveMode"]["SinglePedalModeActive"] == 1 or
                                (ret.regenBraking and ret.gearShifter == GearShifter.manumatic) or
                                (self.CP.carFingerprint in {
                                  CAR.CHEVROLET_BOLT_ACC_2022_2023,
                                  CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
                                  CAR.CHEVROLET_BOLT_CC_2022_2023,
                                } and self.CP.enableGasInterceptorDEPRECATED))

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
    if self.CP.networkLocation == NetworkLocation.fwdCamera and not self.CP.flags & GMFlags.NO_CAMERA.value:
      if self.CP.carFingerprint not in CC_ONLY_CAR:
        ret.cruiseState.speed = cam_cp.vl["ASCMActiveCruiseControlStatus"]["ACCSpeedSetpoint"] * CV.KPH_TO_MS

      if self.CP.carFingerprint not in (SDGM_CAR | ASCM_INT):
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

    remap_cancel_to_distance = bool(self.CP.alternativeExperience & ALTERNATIVE_EXPERIENCE.GM_REMAP_CANCEL_TO_DISTANCE)
    if not remap_cancel_to_distance:
      remap_cancel_to_distance = (
        getattr(frogpilot_toggles, "remap_cancel_to_distance", False) and
        self.CP.openpilotLongitudinalControl and
        bool(self.CP.flags & GMFlags.PEDAL_LONG.value) and
        self.CP.carFingerprint in (BOLT_GEN1_CANCEL_PERSONALITY_CARS | {CAR.CHEVROLET_MALIBU_HYBRID_CC})
      )
    malibu_cancel_passthrough = (
      remap_cancel_to_distance and
      self.CP.carFingerprint == CAR.CHEVROLET_MALIBU_HYBRID_CC and
      self.CP.openpilotLongitudinalControl and
      bool(self.CP.flags & GMFlags.PEDAL_LONG.value)
    )
    bolt_cancel_personality = (
      remap_cancel_to_distance and
      self.CP.carFingerprint in BOLT_GEN1_CANCEL_PERSONALITY_CARS and
      self.CP.openpilotLongitudinalControl and
      bool(self.CP.flags & GMFlags.PEDAL_LONG.value)
    )

    cruise_button_map = BUTTONS_DICT
    if malibu_cancel_passthrough or bolt_cancel_personality:
      cruise_button_map = {k: v for k, v in BUTTONS_DICT.items() if k != CruiseButtons.CANCEL}

    cruise_events = create_button_events(
      self.cruise_buttons, prev_cruise_buttons, cruise_button_map, unpressed_btn=CruiseButtons.UNPRESS
    )
    cancel_gap_events = []
    if bolt_cancel_personality and self.cruise_buttons != prev_cruise_buttons:
      if prev_cruise_buttons == CruiseButtons.CANCEL:
        cancel_gap_events.append(structs.CarState.ButtonEvent(pressed=False, type=ButtonType.gapAdjustCruise))
      if self.cruise_buttons == CruiseButtons.CANCEL:
        cancel_gap_events.append(structs.CarState.ButtonEvent(pressed=True, type=ButtonType.gapAdjustCruise))

    suppress_malibu_side_buttons = malibu_cancel_passthrough and (
      self.cruise_buttons in (CruiseButtons.CANCEL, CruiseButtons.MAIN) or
      prev_cruise_buttons in (CruiseButtons.CANCEL, CruiseButtons.MAIN)
    )
    suppress_bolt_cancel_lkas = bolt_cancel_personality and (
      self.cruise_buttons == CruiseButtons.CANCEL or
      prev_cruise_buttons == CruiseButtons.CANCEL
    )
    distance_events = [] if suppress_malibu_side_buttons else create_button_events(
      self.distance_button, prev_distance_button, {1: ButtonType.gapAdjustCruise}
    )
    lkas_events = [] if (suppress_malibu_side_buttons or suppress_bolt_cancel_lkas) else create_button_events(
      self.lkas_enabled, self.lkas_previously_enabled, {1: ButtonType.lkas}
    )

    # Don't add events if transitioning from INIT, unless it's to an actual button.
    if self.cruise_buttons != CruiseButtons.UNPRESS or prev_cruise_buttons != CruiseButtons.INIT:
      ret.buttonEvents = [
        *cruise_events,
        *cancel_gap_events,
        *distance_events,
        *lkas_events,
      ]

    if ret.vEgo < self.CP.minSteerSpeed:
      ret.lowSpeedAlert = True

    fp_ret = custom.FrogPilotCarState.new_message()
    if bolt_cancel_personality and self.cruise_buttons == CruiseButtons.CANCEL:
      # Feed long-press personality logic as if distance is held while CANCEL is held.
      fp_ret.distancePressed = True
    fp_ret.sportGear = pt_cp.vl["SportMode"]["SportMode"] == 1

    return ret, fp_ret

  @staticmethod
  def get_can_parsers(CP):
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
        pt_messages.append(("BCMBlindSpotMonitor", 10))

    if CP.networkLocation == NetworkLocation.fwdCamera:
      pt_messages += [
        ("ASCMLKASteeringCmd", 0),
      ]
      if CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG.value:
        if ("ECMAcceleratorPos", 80) in pt_messages:
          pt_messages.remove(("ECMAcceleratorPos", 80))
        pt_messages.append(("EBCMBrakePedalPosition", 100))

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
          cam_messages.append(("BCMBlindSpotMonitor", 10))
      elif CP.carFingerprint not in (SDGM_CAR | ASCM_INT):
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

    return {
      Bus.pt: CANParser(DBC[CP.carFingerprint][Bus.pt], pt_messages, CanBus.POWERTRAIN),
      Bus.cam: CANParser(DBC[CP.carFingerprint][Bus.pt], cam_messages, CanBus.CAMERA),
      Bus.loopback: CANParser(DBC[CP.carFingerprint][Bus.pt], loopback_messages, CanBus.LOOPBACK),
    }
