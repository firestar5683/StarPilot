from opendbc.car.gm.values import is_volt_longitudinal, is_volt_auto_hold
import copy
from math import isfinite
from opendbc.can import CANDefine, CANParser, CANPacker
from opendbc.car import Bus, create_button_events, structs
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.interfaces import CarStateBase
from opendbc.car.gm.gmcan import pedal_crc
from opendbc.car.gm.cc_longitudinal import VoltCcPhysical
from opendbc.car.gm.ordinary_cc import PhysicalObservation
from opendbc.car.gm.conventional_pedal import CancelCredit
from opendbc.car.gm.values import (DBC, AccState, CruiseButtons, STEER_THRESHOLD, SDGM_CAR, ALT_ACCS,
                                   ASCM_INTERCEPT_CAR, ORDINARY_ASCM_CAR, ORDINARY_SDGM_CAR, GMFlags, GMSafetyFlags, NO_ACC_BOLT_CAR,
                                   CC_GATEWAY_STOCK_CAR, requires_camera_state_sources, is_conventional_cc_pedal_profile, is_silverado_cc_pedal_profile,
                                   is_volt_cc_profile, is_ordinary_cc_profile, VOLT_BSM_CAR, CAR,
                                   is_volt_gateway_profile, is_volt_gateway_alternate_brake, is_bolt_cc_profile, BOLT_CC_WORDS,
                                   is_bolt_pedal_profile, is_volt_camera_removed, is_ordinary_camera_profile, is_ordinary_camera_removed)

ButtonType = structs.CarState.ButtonEvent.Type
TransmissionType = structs.CarParams.TransmissionType
NetworkLocation = structs.CarParams.NetworkLocation

STANDSTILL_THRESHOLD = 10 * 0.0311
PEDAL_SENSOR_TIMEOUT_NS = 100_000_000  # Five expected 50 Hz frames.

BUTTONS_DICT = {CruiseButtons.RES_ACCEL: ButtonType.accelCruise, CruiseButtons.DECEL_SET: ButtonType.decelCruise,
                CruiseButtons.MAIN: ButtonType.mainCruise, CruiseButtons.CANCEL: ButtonType.cancel}


class CarState(CarStateBase):
  def __init__(self, CP):
    super().__init__(CP)
    self.stock_fcw_alert = 0
    self.ordinary_removed_sources = ()
    self.volt_removed_sources = ()
    self.volt_removed_credit_ns = 0
    self.volt_removed_button_ns = 0
    self.volt_removed_counter = None
    can_define = CANDefine(DBC[CP.carFingerprint][Bus.pt])
    self.shifter_values = can_define.dv["ECMPRDNL2"]["PRNDL2"]
    self.cluster_speed_hyst_gap = CV.KPH_TO_MS / 2.
    self.cluster_min_speed = CV.KPH_TO_MS / 2.

    self.loopback_lka_steering_cmd_updated = False
    self.loopback_lka_steering_cmd_ts_nanos = 0
    self.pt_lka_steering_cmd_counter = 0
    self.cam_lka_steering_cmd_counter = 0
    self.buttons_counter = 0

    self.distance_button = 0
    self.pedal_sensor_healthy = False
    self.pedal_sensor_ts_nanos = 0
    self.pedal_sensor_counter = None
    self.pedal_packer = CANPacker(DBC[CP.carFingerprint][Bus.pt]) if CP.flags & GMFlags.PEDAL_LONG.value else None
    self.stock_acc_status_ts_nanos = 0
    self.volt_cc_physical = None
    self.volt_cc_button_counter = None
    self.volt_cc_button_source_ns = self.volt_cc_button_credit_ns = 0
    self.volt_gateway_source_ns = ()
    self.volt_sng_sources = ()
    self.gm_auto_hold_sources = ()
    self.gm_auto_hold_brake = 0.
    self.gm_auto_hold_forward = self.gm_auto_hold_moving = False
    self.gm_auto_hold_wheel_ns = 0
    self.gm_auto_hold_unavailable = True
    self.gm_auto_hold_engaged = False
    self.cc_gateway_cruise_ts_nanos = 0
    self.cc_gateway_buttons_ts_nanos = 0
    self.camera_stock_status_ts_nanos = 0
    self.camera_stock_sources_valid = False
    self.conventional_pedal_sources = ()
    self.conventional_cancel_credit = CancelCredit()
    self.silverado_pedal_sources = ()
    self.bolt_cc_profile = is_bolt_cc_profile(CP)
    self.bolt_cc_removed = self.bolt_cc_profile and CP.safetyConfigs[0].safetyParam == BOLT_CC_WORDS[CP.carFingerprint][1]
    self.bolt_cc_sources = ()

  def update_button_enable(self, buttonEvents: list[structs.CarState.ButtonEvent]):
    if not self.CP.pcmCruise:
      for b in buttonEvents:
        # The ECM allows enabling on falling edge of set, but only rising edge of resume
        if (b.type == ButtonType.accelCruise and b.pressed) or \
          (b.type == ButtonType.decelCruise and not b.pressed):
          return True
    return False

  def update(self, can_parsers) -> structs.CarState:
    pt_cp = can_parsers[Bus.pt]
    cam_cp = can_parsers[Bus.cam]
    loopback_cp = can_parsers[Bus.loopback]

    ret = structs.CarState()
    pedal_stock_no_acc = self.CP.carFingerprint in NO_ACC_BOLT_CAR and is_bolt_pedal_profile(self.CP, stock_only=True)

    if is_conventional_cc_pedal_profile(self.CP) and not is_silverado_cc_pedal_profile(self.CP):
      source_fields = (("PSCMStatus", "LKATorqueDelivered"), ("EBCMBrakePedalPosition", "BrakePedalPosition"),
                       ("ECMEngineStatus", "CruiseMainOn"), ("ECMCruiseControl", "CruiseActive"),
                       ("ASCMSteeringButton", "RollingCounter"), ("AcceleratorPedal2", "CruiseState"),
                       ("ECMPRDNL2", "PRNDL2"), ("GAS_SENSOR", "COUNTER_PEDAL"))
      self.conventional_pedal_sources = tuple(pt_cp.ts_nanos[name][field] for name, field in source_fields)
      if self.CP.carFingerprint == CAR.CHEVROLET_MALIBU_CC and not self.CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG:
        self.conventional_pedal_sources += (pt_cp.ts_nanos["ECMAcceleratorPos"]["BrakePedalPos"],)

    if is_silverado_cc_pedal_profile(self.CP):
      analog = (("EBCMBrakePedalPosition", "BrakePedalPosition") if self.CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG else
                ("ECMAcceleratorPos", "BrakePedalPos"))
      source_fields = (("PSCMStatus", "LKATorqueDelivered"), analog, ("ECMEngineStatus", "CruiseMainOn"),
                       ("ECMCruiseControl", "CruiseActive"), ("ASCMSteeringButton", "RollingCounter"),
                       ("AcceleratorPedal2", "CruiseState"), ("ECMPRDNL2", "PRNDL2"), ("GAS_SENSOR", "COUNTER_PEDAL"))
      self.silverado_pedal_sources = tuple(pt_cp.ts_nanos[name][field] for name, field in source_fields)
      self.silverado_brake_analog = pt_cp.vl[analog[0]][analog[1]] / (208. if self.CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG else 1.)
      self.pt_lka_steering_cmd_counter = pt_cp.vl["ASCMLKASteeringCmd"]["RollingCounter"]

    prev_cruise_buttons = self.cruise_buttons
    prev_distance_button = self.distance_button
    self.cruise_buttons = pt_cp.vl["ASCMSteeringButton"]["ACCButtons"]
    self.distance_button = pt_cp.vl["ASCMSteeringButton"]["DistanceButton"]
    self.buttons_counter = pt_cp.vl["ASCMSteeringButton"]["RollingCounter"]
    if (self.CP.carFingerprint in CC_GATEWAY_STOCK_CAR or self.CP.carFingerprint == CAR.CHEVROLET_VOLT_CC):
      self.cc_gateway_buttons_ts_nanos = pt_cp.ts_nanos["ASCMSteeringButton"]["RollingCounter"]
      self.cc_gateway_cruise_ts_nanos = pt_cp.ts_nanos["ECMCruiseControl"]["CruiseActive"]
    if is_ordinary_camera_removed(self.CP):
      names = (("PSCMStatus", "LKATorqueDelivered"), ("EBCMBrakePedalPosition", "BrakePedalPosition"),
               ("ECMEngineStatus", "CruiseMainOn"), ("AcceleratorPedal2", "CruiseState"),
               ("ASCMSteeringButton", "RollingCounter"), ("ECMPRDNL2", "PRNDL2"))
      self.ordinary_removed_sources = tuple(pt_cp.ts_nanos[name][field] for name, field in names)

    if is_volt_camera_removed(self.CP):
      names = (("PSCMStatus", "LKATorqueDelivered"), ("EBCMWheelSpdRear", "RLWheelSpd"),
               ("AcceleratorPedal2", "CruiseState"), ("ECMEngineStatus", "CruiseMainOn"),
               ("ASCMSteeringButton", "RollingCounter"), ("EBCMRegenPaddle", "RegenPaddle"))
      self.volt_removed_sources = tuple(pt_cp.ts_nanos[name][field] for name, field in names)
      button = pt_cp.vl["ASCMSteeringButton"]
      stamp = pt_cp.ts_nanos["ASCMSteeringButton"]["RollingCounter"]
      counter = int(button["RollingCounter"])
      neutral = (button["ACCButtons"] == CruiseButtons.UNPRESS and button["ACCAlwaysOne"] == 1 and
                 button["DistanceButton"] == 0 and button["LKAButton"] == 0 and button["DriveModeButton"] == 0 and
                 button["SteeringButtonChecksum"] == 0xFF + counter * 0x4EF)
      if stamp != self.volt_removed_button_ns:
        timely = 0 < stamp - self.volt_removed_button_ns <= 100_000_000
        first = self.volt_removed_counter is None
        if neutral and (first or timely and counter == (self.volt_removed_counter + 1) % 4):
          self.volt_removed_credit_ns = stamp
        elif not neutral or not timely or counter != self.volt_removed_counter:
          self.volt_removed_credit_ns = 0
        self.volt_removed_counter, self.volt_removed_button_ns = counter, stamp
    if requires_camera_state_sources(self.CP) and not pedal_stock_no_acc and not is_ordinary_camera_removed(self.CP):
      self.camera_stock_status_ts_nanos = cam_cp.ts_nanos["ASCMActiveCruiseControlStatus"]["ACCCruiseState"]
      self.camera_stock_sources_valid = pt_cp.can_valid and cam_cp.can_valid
    if is_volt_cc_profile(self.CP) or is_ordinary_cc_profile(self.CP):
      button = pt_cp.vl["ASCMSteeringButton"]
      button_ns = pt_cp.ts_nanos["ASCMSteeringButton"]["RollingCounter"]
      counter = int(button["RollingCounter"])
      neutral = bool(button["ACCButtons"] == CruiseButtons.UNPRESS and button["ACCAlwaysOne"] == 1 and
                     button["DistanceButton"] == 0 and button["LKAButton"] == 0 and button["DriveModeButton"] == 0)
      if button_ns != self.volt_cc_button_source_ns:
        first = self.volt_cc_button_counter is None
        timely = 0 < button_ns - self.volt_cc_button_source_ns <= 100_000_000
        forward = not first and counter == (self.volt_cc_button_counter + 1) % 4
        duplicate = not first and counter == self.volt_cc_button_counter
        if neutral and (first or (timely and forward)):
          self.volt_cc_button_credit_ns = button_ns
        elif not neutral or not timely or not duplicate:
          self.volt_cc_button_credit_ns = 0
        self.volt_cc_button_counter, self.volt_cc_button_source_ns = counter, button_ns
      physical_type = PhysicalObservation if is_ordinary_cc_profile(self.CP) else VoltCcPhysical
      source_ns = (
        pt_cp.ts_nanos["ECMCruiseControl"]["CruiseActive"],
         pt_cp.ts_nanos["ASCMSteeringButton"]["RollingCounter"],
         pt_cp.ts_nanos["ECMEngineStatus"]["CruiseMainOn"],
         pt_cp.ts_nanos["ECMAcceleratorPos"]["BrakePedalPos"],
         pt_cp.ts_nanos["ECMPRDNL2"]["PRNDL2"],
         pt_cp.ts_nanos["AcceleratorPedal2"]["AcceleratorPedal2"])
      if is_volt_cc_profile(self.CP):
        source_ns += (pt_cp.ts_nanos["EBCMRegenPaddle"]["RegenPaddle"],)
      self.volt_cc_physical = physical_type(
        pt_cp.ts_nanos["EBCMWheelSpdRear"]["RLWheelSpd"], source_ns, neutral,
        bool(pt_cp.vl["EBCMWheelSpdRear"]["RLWheelDir"] == 1 and pt_cp.vl["EBCMWheelSpdRear"]["RRWheelDir"] == 1),
        self.volt_cc_button_credit_ns)
    if is_volt_gateway_profile(self.CP) and not self.CP.openpilotLongitudinalControl:
      brake_name, brake_signal = (("EBCMBrakePedalPosition", "BrakePedalPosition")
                                  if is_volt_gateway_alternate_brake(self.CP) else ("ECMAcceleratorPos", "BrakePedalPos"))
      # Card can finalize the preference after the CI has already been created.
      # Observe the same physical messages before reading their lazy timestamps.
      for name in ("PSCMStatus", "EBCMWheelSpdRear", "ASCMSteeringButton", brake_name,
                   "AcceleratorPedal2", "ECMEngineStatus", "EBCMRegenPaddle"):
        pt_cp.vl[name]
      self.volt_gateway_source_ns = (
        pt_cp.ts_nanos["PSCMStatus"]["LKADriverAppldTrq"],
        pt_cp.ts_nanos["EBCMWheelSpdRear"]["RLWheelSpd"],
        pt_cp.ts_nanos["ASCMSteeringButton"]["RollingCounter"],
        pt_cp.ts_nanos[brake_name][brake_signal],
        pt_cp.ts_nanos["AcceleratorPedal2"]["AcceleratorPedal2"],
        pt_cp.ts_nanos["ECMEngineStatus"]["CruiseMainOn"],
        pt_cp.ts_nanos["EBCMRegenPaddle"]["RegenPaddle"])
    if is_volt_longitudinal(self.CP):
      # Observe only actual resume/driver sources, using the finalized brake owner.
      alternate = is_volt_gateway_alternate_brake(self.CP) or (
        is_volt_camera_removed(self.CP) and bool(self.CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG))
      c9 = self.CP.networkLocation == NetworkLocation.fwdCamera and not (
        self.CP.safetyConfigs[0].safetyParam & (GMSafetyFlags.ASCM_INTERCEPT | GMSafetyFlags.SDGM) and
        not self.CP.safetyConfigs[0].safetyParam & GMSafetyFlags.BRAKE_C9)
      brake = (("EBCMBrakePedalPosition", "BrakePedalPosition") if alternate else
               ("ECMEngineStatus", "BrakePressed") if c9 else ("ECMAcceleratorPos", "BrakePedalPos"))
      names = (("AcceleratorPedal2", "CruiseState", 100_000_000),
               ("ECMPRDNL2", "PRNDL2", 300_000_000),
               ("ECMEngineStatus", "BrakePressed", 100_000_000),
               ("EBCMRegenPaddle", "RegenPaddle", 100_000_000),
               (*brake, 300_000_000))
      for name, _, _ in names:
        pt_cp.vl[name]
      self.volt_sng_sources = tuple((pt_cp.ts_nanos[name][signal], limit) for name, signal, limit in names)
      if requires_camera_state_sources(self.CP):
        cam_cp.vl["ASCMActiveCruiseControlStatus"]
        self.volt_sng_sources += ((cam_cp.ts_nanos["ASCMActiveCruiseControlStatus"]["ACCCruiseState"], 100_000_000),)
    if is_volt_auto_hold(self.CP):
      alternate = is_volt_gateway_alternate_brake(self.CP)
      c9 = self.CP.networkLocation == NetworkLocation.fwdCamera and (
        not self.CP.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_INTERCEPT or
        bool(self.CP.safetyConfigs[0].safetyParam & GMSafetyFlags.BRAKE_C9))
      brake_name, brake_signal = (("EBCMBrakePedalPosition", "BrakePedalPosition") if alternate else
                                  ("ECMEngineStatus", "BrakePressed") if c9 else ("ECMAcceleratorPos", "BrakePedalPos"))
      names = (("ECMEngineStatus", "CruiseMainOn"), ("ECMPRDNL2", "PRNDL2"), (brake_name, brake_signal),
               ("AcceleratorPedal2", "CruiseState"), ("EBCMWheelSpdRear", "RLWheelSpd"),
               ("EBCMRegenPaddle", "RegenPaddle"), ("EBCMFrictionBrakeStatus", "FrictionBrakeUnavailable"))
      for name, _ in names:
        pt_cp.vl[name]
      self.gm_auto_hold_sources = tuple((pt_cp.ts_nanos[name][signal], 300_000_000) for name, signal in names)
      # C9 is the pressed authority, never an analog force estimate. The absent-BE
      # SASCM factory branch retains the original zero estimate (minimum hold80).
      absent_be = c9 and bool(self.CP.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_INTERCEPT)
      if alternate:
        self.gm_auto_hold_brake = pt_cp.vl[brake_name][brake_signal] / 208.
      else:
        self.gm_auto_hold_brake = 0. if absent_be else pt_cp.vl["ECMAcceleratorPos"]["BrakePedalPos"]
        if c9 and not absent_be:
          self.gm_auto_hold_sources += ((pt_cp.ts_nanos["ECMAcceleratorPos"]["BrakePedalPos"], 300_000_000),)
      gear = pt_cp.vl["ECMPRDNL2"]["PRNDL2"]
      self.gm_auto_hold_forward = gear in (4, 6) or (4 <= gear <= 7 and pt_cp.vl["ECMPRDNL2"]["ManualMode"] == 1)
      wheels = pt_cp.vl["EBCMWheelSpdRear"]
      self.gm_auto_hold_moving = wheels["RLWheelSpd"] >= 12 * .0311 and wheels["RRWheelSpd"] >= 12 * .0311
      self.gm_auto_hold_wheel_ns = pt_cp.ts_nanos["EBCMWheelSpdRear"]["RLWheelSpd"]
      self.gm_auto_hold_unavailable = bool(pt_cp.vl["EBCMFrictionBrakeStatus"]["FrictionBrakeUnavailable"])
    self.pscm_status = copy.copy(pt_cp.vl["PSCMStatus"])

    # Variables used for avoiding LKAS faults
    self.loopback_lka_steering_cmd_updated = len(loopback_cp.vl_all["ASCMLKASteeringCmd"]["RollingCounter"]) > 0
    if self.loopback_lka_steering_cmd_updated:
      self.loopback_lka_steering_cmd_ts_nanos = loopback_cp.ts_nanos["ASCMLKASteeringCmd"]["RollingCounter"]
    if self.CP.networkLocation == NetworkLocation.fwdCamera and not (is_conventional_cc_pedal_profile(self.CP) and self.CP.flags & GMFlags.NO_CAMERA):
      if not is_conventional_cc_pedal_profile(self.CP):
        self.pt_lka_steering_cmd_counter = pt_cp.vl["ASCMLKASteeringCmd"]["RollingCounter"]
      if not self.bolt_cc_removed and not is_volt_camera_removed(self.CP) and not is_ordinary_camera_removed(self.CP):
        self.cam_lka_steering_cmd_counter = cam_cp.vl["ASCMLKASteeringCmd"]["RollingCounter"]

    # This is to avoid a fault where you engage while still moving backwards after shifting to D.
    # An Equinox has been seen with an unsupported status (3), so only check if either wheel is in reverse (2)
    left_whl_sign = -1 if pt_cp.vl["EBCMWheelSpdRear"]["RLWheelDir"] == 2 else 1
    right_whl_sign = -1 if pt_cp.vl["EBCMWheelSpdRear"]["RRWheelDir"] == 2 else 1
    self.parse_wheel_speeds(ret,
      left_whl_sign * pt_cp.vl["EBCMWheelSpdFront"]["FLWheelSpd"],
      right_whl_sign * pt_cp.vl["EBCMWheelSpdFront"]["FRWheelSpd"],
      left_whl_sign * pt_cp.vl["EBCMWheelSpdRear"]["RLWheelSpd"],
      right_whl_sign * pt_cp.vl["EBCMWheelSpdRear"]["RRWheelSpd"],
    )
    # sample rear wheel speeds to match the safety which only uses the rear CAN message
    # standstill=True if ECM allows engagement with brake
    ret.standstill = abs(pt_cp.vl["EBCMWheelSpdRear"]["RLWheelSpd"]) <= STANDSTILL_THRESHOLD and \
                     abs(pt_cp.vl["EBCMWheelSpdRear"]["RRWheelSpd"]) <= STANDSTILL_THRESHOLD

    if pt_cp.vl["ECMPRDNL2"]["ManualMode"] == 1:
      ret.gearShifter = self.parse_gear_shifter("T")
    else:
      ret.gearShifter = self.parse_gear_shifter(self.shifter_values.get(pt_cp.vl["ECMPRDNL2"]["PRNDL2"], None))

    source_be_brake = (self.CP.safetyConfigs[0].safetyParam &
                       (GMSafetyFlags.ASCM_INTERCEPT | GMSafetyFlags.SDGM).value and
                       not self.CP.safetyConfigs[0].safetyParam & GMSafetyFlags.BRAKE_C9.value)
    if is_conventional_cc_pedal_profile(self.CP) and self.CP.carFingerprint == CAR.CHEVROLET_MALIBU_CC:
      ret.brakePressed = (pt_cp.vl["EBCMBrakePedalPosition"]["BrakePedalPosition"] / 0xD0 >= .10
                          if self.CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG else
                          pt_cp.vl["ECMAcceleratorPos"]["BrakePedalPos"] >= 8)
    elif is_volt_camera_removed(self.CP):
      ret.brakePressed = pt_cp.vl["ECMEngineStatus"]["BrakePressed"] != 0
    elif is_volt_gateway_alternate_brake(self.CP):
      pedal_position = pt_cp.vl["EBCMBrakePedalPosition"]["BrakePedalPosition"]
      ret.brakePressed = pedal_position >= 6
    elif self.CP.networkLocation == NetworkLocation.fwdCamera and not source_be_brake:
      ret.brakePressed = pt_cp.vl["ECMEngineStatus"]["BrakePressed"] != 0
    else:
      # Some Volt 2016-17 have loose brake pedal push rod retainers which causes the ECM to believe
      # that the brake is being intermittently pressed without user interaction.
      # To avoid a cruise fault we need to use a conservative brake position threshold
      # https://static.nhtsa.gov/odi/tsbs/2017/MC-10137629-9999.pdf
      ret.brakePressed = pt_cp.vl["ECMAcceleratorPos"]["BrakePedalPos"] >= 8

    # Regen braking is braking
    if self.CP.transmissionType == TransmissionType.direct:
      ret.regenBraking = pt_cp.vl["EBCMRegenPaddle"]["RegenPaddle"] != 0

    ret.gasPressed = pt_cp.vl["AcceleratorPedal2"]["AcceleratorPedal2"] / 254. > 1e-5

    if self.CP.flags & GMFlags.PEDAL_LONG.value:
      sensor = pt_cp.vl["GAS_SENSOR"]
      sensor_ts = pt_cp.ts_nanos["GAS_SENSOR"]["COUNTER_PEDAL"]
      counter = int(sensor["COUNTER_PEDAL"])
      new_sample = sensor_ts > self.pedal_sensor_ts_nanos
      counter_changed = self.pedal_sensor_counter is None or counter != self.pedal_sensor_counter
      tracks = (sensor["INTERCEPTOR_GAS"], sensor["INTERCEPTOR_GAS2"])
      # Half of the coarser track's 0.251976 step permits encoded zero/full quantization.
      tracks_valid = all(isfinite(x) and -0.126 <= x <= 255.126 for x in tracks) and abs(tracks[0] - tracks[1]) <= 2.0
      sensor_bytes = self.pedal_packer.make_can_msg("GAS_SENSOR", 0, {
        "INTERCEPTOR_GAS": tracks[0], "INTERCEPTOR_GAS2": tracks[1],
        "STATE": sensor["STATE"], "COUNTER_PEDAL": counter,
      })[1]
      checksum_valid = int(sensor["CHECKSUM_PEDAL"]) == pedal_crc(sensor_bytes)
      if new_sample:
        self.pedal_sensor_ts_nanos = sensor_ts
        self.pedal_sensor_counter = counter
        self.pedal_sensor_healthy = bool(counter_changed and sensor["STATE"] == 0 and tracks_valid and checksum_valid)
      elif sensor_ts < self.pedal_sensor_ts_nanos:
        self.pedal_sensor_healthy = False
        self.pedal_sensor_ts_nanos = 0
        self.pedal_sensor_counter = None
      if self.pedal_sensor_healthy:
        ret.gasPressed = sum(tracks) / 2. > 23.0

    ret.steeringAngleDeg = pt_cp.vl["PSCMSteeringAngle"]["SteeringWheelAngle"]
    ret.steeringRateDeg = pt_cp.vl["PSCMSteeringAngle"]["SteeringWheelRate"]
    ret.steeringTorque = pt_cp.vl["PSCMStatus"]["LKADriverAppldTrq"]
    ret.steeringTorqueEps = pt_cp.vl["PSCMStatus"]["LKATorqueDelivered"]
    ret.steeringPressed = abs(ret.steeringTorque) > STEER_THRESHOLD

    # 0 inactive, 1 active, 2 temporarily limited, 3 failed
    self.lkas_status = pt_cp.vl["PSCMStatus"]["LKATorqueDeliveredStatus"]
    ret.steerFaultTemporary = self.lkas_status == 2
    ret.steerFaultPermanent = self.lkas_status == 3

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
    ret.cruiseState.available = pt_cp.vl["ECMEngineStatus"]["CruiseMainOn"] != 0
    ret.espDisabled = pt_cp.vl["ESPStatus"]["TractionControlOn"] != 1
    ret.accFaulted = (pt_cp.vl["AcceleratorPedal2"]["CruiseState"] == AccState.FAULTED or
                      pt_cp.vl["EBCMFrictionBrakeStatus"]["FrictionBrakeUnavailable"] == 1)

    ret.cruiseState.enabled = pt_cp.vl["AcceleratorPedal2"]["CruiseState"] != AccState.OFF
    ret.cruiseState.standstill = pt_cp.vl["AcceleratorPedal2"]["CruiseState"] == AccState.STANDSTILL
    if (self.CP.carFingerprint in CC_GATEWAY_STOCK_CAR or self.CP.carFingerprint == CAR.CHEVROLET_VOLT_CC):
      # AcceleratorPedal2 CruiseState is an ACC state, not a conventional-cruise fault source.
      ret.accFaulted = False
      ret.cruiseState.enabled = pt_cp.vl["ECMCruiseControl"]["CruiseActive"] != 0
      if not is_conventional_cc_pedal_profile(self.CP):
        ret.cruiseState.standstill = False
      ret.cruiseState.speed = pt_cp.vl["ECMCruiseControl"]["CruiseSetSpeed"] * CV.KPH_TO_MS
      ret.cruiseState.nonAdaptive = not (is_ordinary_cc_profile(self.CP) or is_conventional_cc_pedal_profile(self.CP))
    if self.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL and self.CP.flags & GMFlags.PEDAL_LONG.value:
      self.stock_acc_status_ts_nanos = pt_cp.ts_nanos["AcceleratorPedal2"]["CruiseState"]
    if self.CP.carFingerprint in NO_ACC_BOLT_CAR and not self.bolt_cc_profile:
      ret.accFaulted = False
      ret.cruiseState.enabled = pt_cp.vl["ECMCruiseControl"]["CruiseActive"] != 0 if pedal_stock_no_acc else False
      ret.cruiseState.standstill = False
    if (self.CP.networkLocation == NetworkLocation.fwdCamera and not is_volt_camera_removed(self.CP)
        and not is_conventional_cc_pedal_profile(self.CP) and not is_ordinary_camera_removed(self.CP)):
      if (self.CP.carFingerprint not in ALT_ACCS or is_ordinary_camera_profile(self.CP) or
          is_ordinary_camera_profile(self.CP, longitudinal=True)) and not self.bolt_cc_profile and self.CP.carFingerprint not in NO_ACC_BOLT_CAR:
        ret.cruiseState.speed = cam_cp.vl["ASCMActiveCruiseControlStatus"]["ACCSpeedSetpoint"] * CV.KPH_TO_MS
        # This FCW signal only works for SDGM cars. CAM cars send FCW on GMLAN but this bit is always 0 for them
        ret.stockFcw = cam_cp.vl["ASCMActiveCruiseControlStatus"]["FCWAlert"] != 0
      else:
        ret.cruiseState.speed = pt_cp.vl["ECMCruiseControl"]["CruiseSetSpeed"] * CV.KPH_TO_MS
      if (self.CP.pcmCruise and self.CP.carFingerprint not in NO_ACC_BOLT_CAR and self.CP.carFingerprint not in ASCM_INTERCEPT_CAR and
          (self.CP.carFingerprint not in ALT_ACCS or is_ordinary_camera_profile(self.CP) or
               self.CP.carFingerprint == CAR.CHEVROLET_SUBURBAN_CAMERA)):
        # The alternate set-speed source still uses camera ACC state.
        ret.cruiseState.nonAdaptive = cam_cp.vl["ASCMActiveCruiseControlStatus"]["ACCCruiseState"] not in (2, 3)

      if self.CP.carFingerprint not in SDGM_CAR and not self.bolt_cc_removed:
        ret.stockAeb = cam_cp.vl["AEBCmd"]["AEBCmdActive"] != 0

    if pedal_stock_no_acc:
      ret.cruiseState.speed = pt_cp.vl["ECMCruiseControl"]["CruiseSetSpeed"] * CV.KPH_TO_MS
      ret.cruiseState.nonAdaptive = False
      ret.accFaulted = False

    if (self.CP.carFingerprint in (ORDINARY_ASCM_CAR | ORDINARY_SDGM_CAR) or
        is_ordinary_camera_profile(self.CP) or is_ordinary_camera_profile(self.CP, longitudinal=True) or
        self.CP.carFingerprint in (CAR.CHEVROLET_VOLT_CAMERA, CAR.CHEVROLET_VOLT_2019)) and not is_volt_camera_removed(self.CP) and \
        not is_ordinary_camera_removed(self.CP):
      self.stock_fcw_alert = int(cam_cp.vl["ASCMActiveCruiseControlStatus"]["FCWAlert"]) & 0x3
      ret.stockFcw = self.stock_fcw_alert != 0

    if self.bolt_cc_profile:
      ret.brakePressed = bool(pt_cp.vl["ECMEngineStatus"]["BrakePressed"])
      ret.accFaulted = False
      ret.cruiseState.enabled = (cam_cp.vl["ASCMActiveCruiseControlStatus"]["ACCCmdActive"] != 0
                                 if (self.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL and
                                     self.CP.safetyConfigs[0].safetyParam == 0xC140) else
                                 pt_cp.vl["ECMCruiseControl"]["CruiseActive"] != 0)
      ret.cruiseState.standstill = (pt_cp.vl["AcceleratorPedal2"]["CruiseState"] == AccState.STANDSTILL
                                    if self.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL else False)
      if (self.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL and
          self.CP.safetyConfigs[0].safetyParam == 0xC140):
        ret.stockFcw = cam_cp.vl["ASCMActiveCruiseControlStatus"]["FCWAlert"] != 0
      ret.cruiseState.speed = pt_cp.vl["ECMCruiseControl"]["CruiseSetSpeed"] * CV.KPH_TO_MS
      ret.cruiseState.nonAdaptive = False

    if self.CP.flags & GMFlags.HAS_BSM.value:
      ret.leftBlindspot = pt_cp.vl["BCMBlindSpotMonitor"]["LeftBSM"] == 1
      ret.rightBlindspot = pt_cp.vl["BCMBlindSpotMonitor"]["RightBSM"] == 1

    # Don't add event if transitioning from INIT, unless it's to an actual button
    if self.cruise_buttons != CruiseButtons.UNPRESS or prev_cruise_buttons != CruiseButtons.INIT:
      ret.buttonEvents = [
        *create_button_events(self.cruise_buttons, prev_cruise_buttons, BUTTONS_DICT,
                              unpressed_btn=CruiseButtons.UNPRESS),
        *create_button_events(self.distance_button, prev_distance_button,
                              {1: ButtonType.gapAdjustCruise})
      ]

    if ret.vEgo < self.CP.minSteerSpeed:
      ret.lowSpeedAlert = True

    hold_sources_current = (bool(self.gm_auto_hold_sources) and
                            all(0 < stamp <= pt_cp._last_update_nanos and pt_cp._last_update_nanos - stamp <= limit
                                for stamp, limit in self.gm_auto_hold_sources))
    hold_current = (is_volt_auto_hold(self.CP) and pt_cp.can_valid and not pt_cp.bus_timeout and
                    (not requires_camera_state_sources(self.CP) or cam_cp.can_valid and not cam_cp.bus_timeout) and
                    hold_sources_current and not self.gm_auto_hold_unavailable and self.gm_auto_hold_forward and
                    ret.cruiseState.available and ret.standstill and not ret.gasPressed and not ret.regenBraking)
    if not hold_current:
      self.gm_auto_hold_engaged = False
    ret.brakeHoldActive = bool(hold_current and self.gm_auto_hold_engaged)

    return ret

  @staticmethod
  def get_can_parsers(CP):
    bolt_pedal_profile = is_bolt_pedal_profile(CP) or is_bolt_pedal_profile(CP, stock_only=True)
    pt_messages = []
    if is_volt_gateway_profile(CP) and not CP.openpilotLongitudinalControl:
      pt_messages += [("PSCMStatus", 10), ("EBCMWheelSpdRear", 10), ("ASCMSteeringButton", 10),
                      ("AcceleratorPedal2", 10), ("ECMEngineStatus", 10), ("EBCMRegenPaddle", 40)]
      if not is_volt_gateway_alternate_brake(CP):
        pt_messages.append(("ECMAcceleratorPos", 10))
    if is_volt_gateway_alternate_brake(CP):
      pt_messages.append(("EBCMBrakePedalPosition", 100))
    if CP.carFingerprint in VOLT_BSM_CAR and CP.flags & GMFlags.HAS_BSM.value:
      pt_messages.append(("BCMBlindSpotMonitor", float('nan')))
    if CP.flags & GMFlags.PEDAL_LONG.value:
      pt_messages.append(("GAS_SENSOR", 50))
      if CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL and not bolt_pedal_profile:
        pt_messages.append(("AcceleratorPedal2", 10))
    if CP.networkLocation == NetworkLocation.fwdCamera and (not is_conventional_cc_pedal_profile(CP) or is_silverado_cc_pedal_profile(CP)):
      pt_messages += [
        ("ASCMLKASteeringCmd", float('nan')),
      ]
    if CP.carFingerprint in ORDINARY_SDGM_CAR:
      # Frozen SDGM PT subscriptions: steering, vehicle state, stock ACC and
      # driver input are required; the PT camera command remains optional.
      pt_messages += [
        ("PSCMStatus", 10), ("ESPStatus", 10),
        ("EBCMWheelSpdFront", 20), ("EBCMWheelSpdRear", 20),
        ("EBCMFrictionBrakeStatus", 20), ("PSCMSteeringAngle", 100),
        ("ECMPRDNL2", 10), ("AcceleratorPedal2", 33),
        ("ECMEngineStatus", 100), ("BCMTurnSignals", 1),
        ("BCMDoorBeltStatus", 10), ("BCMGeneralPlatformStatus", 10),
        ("ASCMSteeringButton", 33),
      ]
      if not CP.safetyConfigs[0].safetyParam & GMSafetyFlags.BRAKE_C9.value:
        pt_messages.append(("ECMAcceleratorPos", 80))
    if (CP.carFingerprint in CC_GATEWAY_STOCK_CAR or CP.carFingerprint == CAR.CHEVROLET_VOLT_CC):
      # No camera or ACC status dependency on this gateway conventional-cruise path.
      pt_messages += [
        ("PSCMStatus", 10), ("ESPStatus", 10),
        ("EBCMWheelSpdFront", 20), ("EBCMWheelSpdRear", 20),
        ("EBCMFrictionBrakeStatus", 20), ("PSCMSteeringAngle", 100),
        ("ECMPRDNL2", 10), ("AcceleratorPedal2", 33),
        ("ECMEngineStatus", 100), ("BCMTurnSignals", 1),
        ("BCMDoorBeltStatus", 10), ("BCMGeneralPlatformStatus", 10),
        ("ASCMSteeringButton", 33), ("ECMAcceleratorPos", 80),
        ("ECMCruiseControl", 10),
      ]
    if (requires_camera_state_sources(CP) or is_volt_camera_removed(CP) or bolt_pedal_profile) and CP.carFingerprint not in ORDINARY_SDGM_CAR:
      # Required stock signals are checked on their observed PT bus; the
      # camera command on PT is only a counter source and remains optional.
      pt_messages += [
        ("PSCMStatus", 10), ("ESPStatus", 10),
        ("EBCMWheelSpdFront", 20), ("EBCMWheelSpdRear", 20),
        ("EBCMFrictionBrakeStatus", 20), ("PSCMSteeringAngle", 100),
        ("ECMAcceleratorPos", 80), ("ECMPRDNL2", 10 if CP.carFingerprint == CAR.CHEVROLET_VOLT_CAMERA else 40),
        ("AcceleratorPedal2", 33), ("ECMEngineStatus", 100),
        ("BCMTurnSignals", 1), ("BCMDoorBeltStatus", 10),
        ("BCMGeneralPlatformStatus", 10), ("ASCMSteeringButton", 33),
      ]
      if CP.transmissionType == TransmissionType.direct:
        pt_messages.append(("EBCMRegenPaddle", 50 if CP.carFingerprint == CAR.CHEVROLET_VOLT_CAMERA else 40))
      if CP.carFingerprint in ALT_ACCS or bolt_pedal_profile:
        pt_messages.append(("ECMCruiseControl", 10))

    if is_ordinary_camera_profile(CP, longitudinal=CP.openpilotLongitudinalControl):
      pt_messages.append(("EBCMBrakePedalPosition", 10))

    if (is_volt_camera_removed(CP) or is_ordinary_camera_profile(CP, longitudinal=CP.openpilotLongitudinalControl)) and \
        CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG:
      pt_messages = [(name, frequency) for name, frequency in pt_messages if name != "ECMAcceleratorPos"]
      pt_messages = [(name, frequency) for name, frequency in pt_messages if name != "EBCMBrakePedalPosition"]
      pt_messages.append(("EBCMBrakePedalPosition", 100))

    if CP.carFingerprint == CAR.CHEVROLET_VOLT_CC:
      pt_messages.append(("EBCMRegenPaddle", 50))

    if is_bolt_cc_profile(CP):
      pt_messages += [("PSCMStatus", 10), ("ECMCruiseControl", 10), ("ASCMSteeringButton", 33),
                      ("ECMEngineStatus", 100), ("AcceleratorPedal2", 33), ("ECMPRDNL2", 10),
                      ("EBCMWheelSpdRear", 20), ("EBCMRegenPaddle", 40)]

    if CP.carFingerprint == CAR.CHEVROLET_VOLT_2019 and CP.safetyConfigs[0].safetyParam & GMSafetyFlags.BRAKE_C9.value:
      pt_messages = [(name, frequency) for name, frequency in pt_messages if name != "ECMAcceleratorPos"]

    if is_conventional_cc_pedal_profile(CP):
      pt_messages = [(name, frequency) for name, frequency in pt_messages
                     if name not in ("EBCMBrakePedalPosition", "ECMCruiseControl", "ECMPRDNL2")]
      pt_messages += [("EBCMBrakePedalPosition", 100 if CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG else 10),
                      ("ECMCruiseControl", 10), ("ECMPRDNL2", 40)]
      if CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG:
        pt_messages = [(name, frequency) for name, frequency in pt_messages if name != "ECMAcceleratorPos"]

    if is_silverado_cc_pedal_profile(CP) and not CP.flags & GMFlags.NO_ACCELERATOR_POS_MSG:
      pt_messages = [(name, frequency) for name, frequency in pt_messages if name != "EBCMBrakePedalPosition"]

    if is_ordinary_camera_removed(CP):
      pt_messages = [(name, frequency) for name, frequency in pt_messages if name != "ECMCruiseControl"]

    loopback_messages = [
      ("ASCMLKASteeringCmd", float('nan')),
    ]

    cam_messages = []
    if CP.carFingerprint in ASCM_INTERCEPT_CAR:
      # These camera messages are required except OEM AEB, which is not reliable at startup.
      cam_messages = [("ASCMLKASteeringCmd", 10), ("AEBCmd", float('nan')),
                      ("ASCMActiveCruiseControlStatus", 25)]
    elif CP.carFingerprint in ORDINARY_SDGM_CAR:
      cam_messages = [("ASCMLKASteeringCmd", 10), ("ASCMActiveCruiseControlStatus", 25)]
    elif requires_camera_state_sources(CP):
      cam_messages = [("ASCMLKASteeringCmd", 10), ("ASCMActiveCruiseControlStatus", 25)]
      if CP.carFingerprint != CAR.CHEVROLET_VOLT_2019:
        cam_messages.append(("AEBCmd", 10))

    if is_bolt_cc_profile(CP):
      removed = CP.safetyConfigs[0].safetyParam == BOLT_CC_WORDS[CP.carFingerprint][1]
      cam_messages = [] if removed else [("ASCMLKASteeringCmd", 10), ("AEBCmd", 10)]
      if CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL and not removed:
        cam_messages.append(("ASCMActiveCruiseControlStatus", 25))

    if bolt_pedal_profile:
      cam_messages = [("ASCMLKASteeringCmd", 10), ("AEBCmd", 10)]
      if CP.carFingerprint not in NO_ACC_BOLT_CAR:
        cam_messages.append(("ASCMActiveCruiseControlStatus", 25))

    if is_conventional_cc_pedal_profile(CP):
      cam_messages = [] if CP.flags & GMFlags.NO_CAMERA else [("ASCMLKASteeringCmd", 10), ("AEBCmd", 10)]

    if is_ordinary_camera_removed(CP):
      cam_messages = []

    return {
      Bus.pt: CANParser(DBC[CP.carFingerprint][Bus.pt], pt_messages, 0),
      Bus.cam: CANParser(DBC[CP.carFingerprint][Bus.pt], cam_messages, 2),
      Bus.loopback: CANParser(DBC[CP.carFingerprint][Bus.pt], loopback_messages, 128),
    }
