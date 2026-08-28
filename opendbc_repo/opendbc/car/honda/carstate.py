import numpy as np
from collections import defaultdict

from cereal import custom
from opendbc.can import CANDefine, CANParser
from opendbc.car import Bus, DT_CTRL, create_button_events, structs
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.honda.hondacan import CanBus
from opendbc.car.honda.values import CAR, DBC, STEER_THRESHOLD, HONDA_BOSCH, HONDA_BOSCH_ALT_RADAR, HONDA_BOSCH_CANFD, \
                                                 HONDA_NIDEC_ALT_SCM_MESSAGES, HONDA_BOSCH_RADARLESS, HONDA_BOSCH_TJA_CONTROL, \
                                                 HondaFlags, CruiseButtons, CruiseSettings, GearShifter, CarControllerParams, HondaStarPilotFlags
from opendbc.car.interfaces import CarStateBase

TransmissionType = structs.CarParams.TransmissionType
ButtonType = structs.CarState.ButtonEvent.Type

BUTTONS_DICT = {CruiseButtons.RES_ACCEL: ButtonType.accelCruise, CruiseButtons.DECEL_SET: ButtonType.decelCruise,
                CruiseButtons.MAIN: ButtonType.mainCruise, CruiseButtons.CANCEL: ButtonType.cancel}
SETTINGS_BUTTONS_DICT = {CruiseSettings.DISTANCE: ButtonType.gapAdjustCruise, CruiseSettings.LKAS: ButtonType.lkas}


# Dashboard Speed Limit / Traffic Sign Recognition (TSR) for Speed Limit Controller (SLC)
def calculate_speed_limit(CP, FPCP, cp, cp_cam):
  if not (FPCP.flags & HondaStarPilotFlags.HAS_CAMERA_MESSAGES):
    return 0.0
  speed_bus = cp if (CP.carFingerprint in (HONDA_BOSCH - HONDA_BOSCH_RADARLESS - HONDA_BOSCH_CANFD)) else cp_cam
  try:
    speed_limit_raw = speed_bus.vl["CAMERA_MESSAGES"]["SPEED_LIMIT_SIGN"] % 32
    return speed_limit_raw * 5.0 * CV.MPH_TO_MS if 1 <= speed_limit_raw <= 17 else 0.0
  except (KeyError, ValueError):
    return 0.0


class CarState(CarStateBase):
  def __init__(self, CP, FPCP):
    super().__init__(CP, FPCP)
    can_define = CANDefine(DBC[CP.carFingerprint][Bus.pt])

    if CP.transmissionType != TransmissionType.manual:
      self.gearbox_msg = "GEARBOX_AUTO"
      if CP.transmissionType == TransmissionType.cvt:
        self.gearbox_msg = "GEARBOX_CVT"
      self.shifter_values = can_define.dv[self.gearbox_msg]["GEAR_SHIFTER"]

    self.car_state_scm_msg = "SCM_FEEDBACK"
    if CP.carFingerprint in HONDA_NIDEC_ALT_SCM_MESSAGES:
      self.car_state_scm_msg = "SCM_BUTTONS"

    self.brake_error_msg = "HYBRID_BRAKE_ERROR" if CP.flags & HondaFlags.HYBRID else "STANDSTILL"

    self.steer_status_values = defaultdict(lambda: "UNKNOWN", can_define.dv["STEER_STATUS"]["STEER_STATUS"])

    self.brake_switch_prev = False
    self.brake_switch_active = False
    self.low_speed_alert = False

    self.dynamic_v_cruise_units = self.CP.carFingerprint in (HONDA_BOSCH_RADARLESS | HONDA_BOSCH_ALT_RADAR |
                                                             HONDA_BOSCH_TJA_CONTROL | HONDA_BOSCH_CANFD)
    self.cruise_setting = 0
    self.v_cruise_pcm_prev = 0

    # When available we use cp.vl["CAR_SPEED"]["ROUGH_CAR_SPEED_2"] to populate vEgoCluster
    # However, on cars without a digital speedometer this is not always present (HRV, FIT, CRV 2016, ILX and RDX)
    self.dash_speed_seen = False
    self.is_metric = False
    self.v_cruise_factor = 1.

    self.initial_accFault_cleared = False
    self.initial_accFault_cleared_timer = int(10 / DT_CTRL)

    # CAN-FD deferred radar handover state. The stock radar remains responsible for ACC_CONTROL
    # until the relay is open and the controller has silenced it; radar reference/tick messages are
    # used to keep the replacement radar look-alikes on the stock cadence after the handover.
    self.radar_ref_counter = 0
    self.radar_5hz_tick_counter = 0
    self.radar_5hz_tick = False
    self.supp_tick_counter = 0
    self.supp_tick = False
    self.hud_tick_counter = 0
    self.hud_tick = False
    self.radar_50hz_tick_counter = 0
    self.radar_50hz_tick = False
    self.scm_ambient_light = 0
    self.stock_acc_counter = 0
    self.stock_acc_alive = False
    self.camera_steer_counter = 0
    self.camera_steer_seen = False
    self.canfd_frames = 0
    self.canfd_relay_open = False

  def update(self, can_parsers, starpilot_toggles) -> structs.CarState:
    cp = can_parsers[Bus.pt]
    cp_cam = can_parsers[Bus.cam]
    if self.CP.enableBsm:
      cp_body = can_parsers[Bus.body]
    if self.CP.carFingerprint == CAR.HONDA_ACCORD_11G:
      cp_radar = can_parsers[Bus.radar]

    ret = structs.CarState()

    # car params
    v_weight_v = [0., 1.]  # don't trust smooth speed at low values to avoid premature zero snapping
    v_weight_bp = [1., 6.]   # smooth blending, below ~0.6m/s the smooth speed snaps to zero

    # update prevs, update must run once per loop
    prev_cruise_buttons = self.cruise_buttons
    prev_cruise_setting = self.cruise_setting
    self.cruise_setting = cp.vl["SCM_BUTTONS"]["CRUISE_SETTING"]
    self.cruise_buttons = cp.vl["SCM_BUTTONS"]["CRUISE_BUTTONS"]
    if self.CP.carFingerprint in (HONDA_BOSCH_RADARLESS | {CAR.HONDA_ACCORD_11G}):
      # The camera consumes this byte in SCM_BUTTONS too (adaptive high beam); preserve it when
      # openpilot temporarily takes over SCM_BUTTONS toward the camera.
      self.scm_ambient_light = cp.vl["SCM_BUTTONS"]["AMBIENT_LIGHT_MAYBE"]

    # used for car hud message
    self.is_metric = self.CP.carFingerprint in (CAR.HONDA_ODYSSEY_TWN,) or not cp.vl["CAR_SPEED"]["IMPERIAL_UNIT"]
    self.v_cruise_factor = CV.MPH_TO_MS if self.dynamic_v_cruise_units and not self.is_metric else CV.KPH_TO_MS

    # ******************* parse out can *******************

    # blend in transmission speed at low speed, since it has more low speed accuracy
    # STANDSTILL->WHEELS_MOVING bit can be noisy around zero, so use XMISSION_SPEED
    lowspeed_source = cp.vl["CAR_SPEED"]["CAR_SPEED"] if self.CP.carFingerprint == CAR.ACURA_INTEGRA else cp.vl["ENGINE_DATA"]["XMISSION_SPEED"]
    v_wheel = sum([cp.vl["WHEEL_SPEEDS"][f"WHEEL_SPEED_{s}"] for s in ("FL", "FR", "RL", "RR")]) / 4.0 * CV.KPH_TO_MS
    v_weight = float(np.interp(v_wheel, v_weight_bp, v_weight_v))
    ret.vEgoRaw = (1. - v_weight) * lowspeed_source * CV.KPH_TO_MS * self.CP.wheelSpeedFactor + v_weight * v_wheel
    ret.vEgo, ret.aEgo = self.update_speed_kf(ret.vEgoRaw)
    ret.standstill = lowspeed_source < 1e-5

    # doorOpen is true if we can find any door open, but signal locations vary, and we may only see the driver's door
    # TODO: Test the eight Nidec cars without SCM signals for driver's door state, may be able to consolidate further
    if self.CP.flags & HondaFlags.HAS_ALL_DOOR_STATES:
      ret.doorOpen = any([cp.vl["DOORS_STATUS"]["DOOR_OPEN_FL"], cp.vl["DOORS_STATUS"]["DOOR_OPEN_FR"],
                          cp.vl["DOORS_STATUS"]["DOOR_OPEN_RL"], cp.vl["DOORS_STATUS"]["DOOR_OPEN_RR"]])
    elif "DRIVERS_DOOR_OPEN" in cp.vl["SCM_BUTTONS"]:
      ret.doorOpen = bool(cp.vl["SCM_BUTTONS"]["DRIVERS_DOOR_OPEN"])
    else:
      ret.doorOpen = bool(cp.vl["SCM_FEEDBACK"]["DRIVERS_DOOR_OPEN"])

    ret.seatbeltUnlatched = bool(cp.vl["SEATBELT_STATUS"]["SEATBELT_DRIVER_LAMP"] or not cp.vl["SEATBELT_STATUS"]["SEATBELT_DRIVER_LATCHED"])

    steer_status = self.steer_status_values[cp.vl["STEER_STATUS"]["STEER_STATUS"]]
    ret.steerFaultPermanent = steer_status not in ("NORMAL", "NO_TORQUE_ALERT_1", "NO_TORQUE_ALERT_2", "LOW_SPEED_LOCKOUT", "TJA_LOW_SPEED_LOCKOUT",
                                                   "TMP_FAULT")
    if self.CP.carFingerprint in (HONDA_BOSCH_ALT_RADAR | {CAR.HONDA_ACCORD_11G}):
      # MVL treats CAN-FD low-speed lockout as an expected EPS state too.
      min_steer_speed = max(CarControllerParams.STEER_GLOBAL_MIN_SPEED, self.CP.minSteerSpeed)
      expected_low_speed_lockout = steer_status == "LOW_SPEED_LOCKOUT" and ret.vEgo < min_steer_speed
      ret.steerFaultTemporary = steer_status != "NORMAL" and not expected_low_speed_lockout
    else:
      # LOW_SPEED_LOCKOUT is not worth a warning
      # NO_TORQUE_ALERT_2 can be caused by bump or steering nudge from driver
      # FIXME: the stock camera stops steering on NO_TORQUE_ALERT_1
      ret.steerFaultTemporary = steer_status not in ("NORMAL", "LOW_SPEED_LOCKOUT", "TJA_LOW_SPEED_LOCKOUT", "NO_TORQUE_ALERT_2")

    if self.CP.carFingerprint == CAR.ACURA_MDX_4G and steer_status == "TJA_LOW_SPEED_LOCKOUT":
      ret.steerFaultPermanent = False
      ret.steerFaultTemporary = False

    # All Honda EPS cut off slightly above standstill, some much higher
    # Don't alert in the near-standstill range, but alert for per-vehicle configured minimums above that
    if CarControllerParams.STEER_GLOBAL_MIN_SPEED < ret.vEgo < (self.CP.minSteerSpeed + 0.5):
      self.low_speed_alert = True
    elif ret.vEgo > (self.CP.minSteerSpeed + 1.):
      # TODO: better handle delayed steering enablement on ALT_RADAR cars
      self.low_speed_alert = False
    ret.lowSpeedAlert = self.low_speed_alert

    if self.CP.carFingerprint not in HONDA_BOSCH:
      ret.carFaultedNonCritical = bool(cp_cam.vl["ACC_HUD"]["ACC_PROBLEM"] or cp_cam.vl["LKAS_HUD"]["LKAS_PROBLEM"])
    elif self.CP.carFingerprint in HONDA_BOSCH_RADARLESS:
      ret.accFaulted = bool(cp.vl["CRUISE_FAULT_STATUS"]["CRUISE_FAULT"])
    elif self.CP.openpilotLongitudinalControl:
      if self.CP.carFingerprint in (HONDA_BOSCH_CANFD | HONDA_BOSCH_TJA_CONTROL) and (self.CP.flags & HondaFlags.BOSCH_ALT_BRAKE):
        ret.accFaulted = bool(cp.vl["BRAKE_MODULE"]["CRUISE_FAULT"])
      else:
        ret.accFaulted = bool(cp.vl[self.brake_error_msg]["BRAKE_ERROR_1"] or cp.vl[self.brake_error_msg]["BRAKE_ERROR_2"])

    ret.espDisabled = cp.vl["VSA_STATUS"]["ESP_DISABLED"] != 0

    if self.CP.carFingerprint not in (CAR.HONDA_ODYSSEY_TWN,):
      self.dash_speed_seen = self.dash_speed_seen or cp.vl["CAR_SPEED"]["ROUGH_CAR_SPEED_2"] > 1e-3
      if self.dash_speed_seen:
        conversion = CV.KPH_TO_MS if self.is_metric else CV.MPH_TO_MS
        ret.vEgoCluster = cp.vl["CAR_SPEED"]["ROUGH_CAR_SPEED_2"] * conversion

    ret.steeringAngleDeg = cp.vl["STEERING_SENSORS"]["STEER_ANGLE"]
    ret.steeringRateDeg = cp.vl["STEERING_SENSORS"]["STEER_ANGLE_RATE"]

    ret.leftBlinker, ret.rightBlinker = self.update_blinker_from_stalk(
      250, cp.vl["SCM_FEEDBACK"]["LEFT_BLINKER"], cp.vl["SCM_FEEDBACK"]["RIGHT_BLINKER"])
    ret.brakeHoldActive = cp.vl["VSA_STATUS"]["BRAKE_HOLD_ACTIVE"] == 1
    ret.parkingBrake = bool(cp.vl[self.car_state_scm_msg]["PARKING_BRAKE_ON"])

    if self.CP.transmissionType == TransmissionType.manual:
      ret.gearShifter = GearShifter.reverse if bool(cp.vl[self.car_state_scm_msg]["REVERSE_LIGHT"]) else GearShifter.drive
    else:
      gear_position = self.shifter_values.get(cp.vl[self.gearbox_msg]["GEAR_SHIFTER"], None)
      ret.gearShifter = self.parse_gear_shifter(gear_position)

    if self.CP.enableGasInterceptorDEPRECATED:
      gas = (cp.vl["GAS_SENSOR"]["INTERCEPTOR_GAS"] + cp.vl["GAS_SENSOR"]["INTERCEPTOR_GAS2"]) / 2.
      ret.gasPressed = gas > 492
    else:
      ret.gasPressed = cp.vl["POWERTRAIN_DATA"]["PEDAL_GAS"] > 1e-5

    ret.steeringTorque = cp.vl["STEER_STATUS"]["STEER_TORQUE_SENSOR"]
    ret.steeringPressed = abs(ret.steeringTorque) > STEER_THRESHOLD.get(self.CP.carFingerprint, 1200)

    if self.CP.carFingerprint in HONDA_BOSCH:
      # The PCM always manages its own cruise control state, but doesn't publish it
      if self.CP.carFingerprint in HONDA_BOSCH_RADARLESS:
        ret.cruiseState.nonAdaptive = cp_cam.vl["ACC_HUD"]["CRUISE_CONTROL_LABEL"] != 0

      if not self.CP.openpilotLongitudinalControl:
        # ACC_HUD is on camera bus on radarless cars
        acc_hud = cp_cam.vl["ACC_HUD"] if self.CP.carFingerprint in HONDA_BOSCH_RADARLESS else cp.vl["ACC_HUD"]
        ret.cruiseState.nonAdaptive = acc_hud["CRUISE_CONTROL_LABEL"] != 0
        ret.cruiseState.standstill = acc_hud["CRUISE_SPEED"] == 252.

        # On set, cruise set speed pulses between 254~255 and the set speed prev is set to avoid this.
        ret.cruiseState.speed = self.v_cruise_pcm_prev if acc_hud["CRUISE_SPEED"] > 160.0 else acc_hud["CRUISE_SPEED"] * self.v_cruise_factor
        self.v_cruise_pcm_prev = ret.cruiseState.speed
    else:
      ret.cruiseState.speed = cp.vl["CRUISE"]["CRUISE_SPEED_PCM"] * CV.KPH_TO_MS

    if self.CP.flags & HondaFlags.BOSCH_ALT_BRAKE:
      ret.brakePressed = cp.vl["BRAKE_MODULE"]["BRAKE_PRESSED"] != 0
    else:
      powertrain_data = cp.vl["POWERTRAIN_DATA"]
      # brake switch has shown some single time step noise, so only considered when
      # switch is on for at least 2 consecutive CAN samples
      # brake switch rises earlier than brake pressed but is never 1 when in park
      brake_switch_vals = cp.vl_all["POWERTRAIN_DATA"]["BRAKE_SWITCH"]
      if len(brake_switch_vals):
        brake_switch = powertrain_data["BRAKE_SWITCH"] != 0
        if len(brake_switch_vals) > 1:
          self.brake_switch_prev = brake_switch_vals[-2] != 0
        self.brake_switch_active = brake_switch and self.brake_switch_prev
        self.brake_switch_prev = brake_switch
      ret.brakePressed = (powertrain_data["BRAKE_PRESSED"] != 0) or self.brake_switch_active

    ret.brake = cp.vl["VSA_STATUS"]["USER_BRAKE"]
    ret.cruiseState.enabled = cp.vl["POWERTRAIN_DATA"]["ACC_STATUS"] != 0
    ret.cruiseState.available = bool(cp.vl[self.car_state_scm_msg]["MAIN_ON"])

    if ret.accFaulted:
      if self.CP.carFingerprint in HONDA_BOSCH and not self.initial_accFault_cleared:
        ret.accFaulted = False
        ret.cruiseState.available = False
    elif self.initial_accFault_cleared_timer == 0:
      self.initial_accFault_cleared = True

    if self.initial_accFault_cleared_timer > 0:
      self.initial_accFault_cleared_timer -= 1

    # Gets rid of Pedal Grinding noise when brake is pressed at slow speeds for some models
    if self.CP.carFingerprint in (CAR.HONDA_PILOT, CAR.HONDA_RIDGELINE):
      if ret.brake > 0.1:
        ret.brakePressed = True

    if self.CP.carFingerprint in HONDA_BOSCH:
      # TODO: find the radarless AEB_STATUS bit and make sure ACCEL_COMMAND is correct to enable AEB alerts
      if self.CP.carFingerprint not in HONDA_BOSCH_RADARLESS:
        ret.stockAeb = (not self.CP.openpilotLongitudinalControl) and bool(cp.vl["ACC_CONTROL"]["AEB_STATUS"] and cp.vl["ACC_CONTROL"]["ACCEL_COMMAND"] < -1e-5)
    else:
      ret.stockAeb = bool(cp_cam.vl["BRAKE_COMMAND"]["AEB_REQ_1"] and cp_cam.vl["BRAKE_COMMAND"]["COMPUTER_BRAKE"] > 1e-5)

    self.acc_hud = False
    self.lkas_hud = False
    if self.CP.carFingerprint not in HONDA_BOSCH:
      ret.stockFcw = cp_cam.vl["BRAKE_COMMAND"]["FCW"] != 0
      self.acc_hud = cp_cam.vl["ACC_HUD"]
      self.stock_brake = cp_cam.vl["BRAKE_COMMAND"]
    if self.CP.carFingerprint in (HONDA_BOSCH_RADARLESS | HONDA_BOSCH_CANFD):
      self.lkas_hud = cp_cam.vl["LKAS_HUD"]

    if self.CP.carFingerprint == CAR.HONDA_ACCORD_11G:
      # Phase replacement radar messages from the stock radar's tick references. CarState reads the
      # tick in one 100 Hz cycle and CarController transmits on the next, so pulse one frame before
      # the expected next stock tick.
      self.radar_ref_counter = cp.vl["RADAR_REFERENCE"]["COUNTER"]

      ref_tick_vals = cp.vl_all.get("RADAR_REFERENCE", {}).get("COUNTER", [])
      if len(ref_tick_vals) > 0:
        self.radar_5hz_tick_counter = 0
      else:
        self.radar_5hz_tick_counter += 1
      self.radar_5hz_tick = self.radar_5hz_tick_counter == 11

      supp_tick_vals = cp_radar.vl_all.get("RADAR_SUPP_TICK_REFERENCE", {}).get("IGNORE", [])
      if len(supp_tick_vals) > 0:
        self.supp_tick_counter = 0
      else:
        self.supp_tick_counter += 1
      self.supp_tick = self.supp_tick_counter == 99

      hud_tick_vals = cp_radar.vl_all.get("RADAR_HUD_TICK_REFERENCE", {}).get("IGNORE", [])
      if len(hud_tick_vals) > 0:
        self.hud_tick_counter = 0
      else:
        self.hud_tick_counter += 1
      self.hud_tick = self.hud_tick_counter == 9

      tick_50hz_vals = cp_radar.vl_all.get("RADAR_50HZ_TICK_REFERENCE", {}).get("IGNORE", [])
      if len(tick_50hz_vals) > 0:
        self.radar_50hz_tick_counter = 0
      else:
        self.radar_50hz_tick_counter += 1
      self.radar_50hz_tick = self.radar_50hz_tick_counter == 1

      # ACC_CONTROL is normally present every 2 frames. Keep treating the stock radar as alive until
      # four consecutive frames have passed without it, preventing overlap between stock and OP ACC.
      self.canfd_frames += 1
      if len(cp.vl_all.get("ACC_CONTROL", {}).get("COUNTER", [])) > 0:
        self.stock_acc_counter = 0
      else:
        self.stock_acc_counter += 1
      self.stock_acc_alive = self.stock_acc_counter < 4

      # Before the relay opens, the camera's STEERING_CONTROL is physically visible on PT. Once the
      # relay opens it disappears. Fallback to 5 seconds in case the camera frame was never observed.
      if len(cp.vl_all.get("STEERING_CONTROL", {}).get("COUNTER", [])) > 0:
        self.camera_steer_counter = 0
        self.camera_steer_seen = True
      else:
        self.camera_steer_counter += 1
      self.canfd_relay_open = (self.camera_steer_seen and self.camera_steer_counter >= 5) or self.canfd_frames >= 500
    else:
      self.supp_tick = False
      self.hud_tick = False
      self.radar_5hz_tick = False
      self.radar_50hz_tick = False

    if self.CP.enableBsm:
      # BSM messages are on B-CAN, requires a panda forwarding B-CAN messages to CAN 0
      # more info here: https://github.com/commaai/openpilot/pull/1867
      ret.leftBlindspot = cp_body.vl["BSM_STATUS_LEFT"]["BSM_ALERT"] == 1
      ret.rightBlindspot = cp_body.vl["BSM_STATUS_RIGHT"]["BSM_ALERT"] == 1

    ret.buttonEvents = [
      *create_button_events(self.cruise_buttons, prev_cruise_buttons, BUTTONS_DICT),
      *create_button_events(self.cruise_setting, prev_cruise_setting, SETTINGS_BUTTONS_DICT),
    ]

    fp_ret = custom.StarPilotCarState.new_message()

    fp_ret.dashboardSpeedLimit = calculate_speed_limit(self.CP, self.FPCP, cp, cp_cam)
    if self.FPCP.flags & HondaStarPilotFlags.HAS_CAMERA_MESSAGES:
      sign_bus = cp if (self.CP.carFingerprint in (HONDA_BOSCH - HONDA_BOSCH_RADARLESS - HONDA_BOSCH_CANFD)) else cp_cam
      fp_ret.dashboardStopSign = 1 if sign_bus.vl["CAMERA_MESSAGES"]["ROAD_SIGN"] == 89 else 0

    return ret, fp_ret

  def get_can_parsers(self, CP):
    pt_messages = [("GAS_SENSOR", 0)] if CP.enableGasInterceptorDEPRECATED else []
    enable_can_valid_diagnostics = CP.carFingerprint == CAR.HONDA_ACCORD_11G
    if CP.carFingerprint == CAR.HONDA_ACCORD_11G:
      # Both deliberately go silent during the handover, so skip alive/timeout checks.
      pt_messages += [("ACC_CONTROL", float("nan")), ("STEERING_CONTROL", float("nan"))]

    pt_parser = CANParser(DBC[CP.carFingerprint][Bus.pt], pt_messages, CanBus(CP).pt, enable_can_valid_diagnostics=enable_can_valid_diagnostics)
    if CP.enableGasInterceptorDEPRECATED:
      pt_parser.message_states[0x201].ignore_checksum = True
      pt_parser.message_states[0x201].ignore_counter = True

    parsers = {
      Bus.pt: pt_parser,
      Bus.cam: CANParser(DBC[CP.carFingerprint][Bus.pt], [], CanBus(CP).camera, enable_can_valid_diagnostics=enable_can_valid_diagnostics),
    }
    if CP.enableBsm:
      parsers[Bus.body] = CANParser(DBC[CP.carFingerprint][Bus.body], [], CanBus(CP).radar, enable_can_valid_diagnostics=enable_can_valid_diagnostics)
    if CP.carFingerprint == CAR.HONDA_ACCORD_11G:
      parsers[Bus.radar] = CANParser(DBC[CP.carFingerprint][Bus.radar], [
        ("RADAR_SUPP_TICK_REFERENCE", 0),
        ("RADAR_HUD_TICK_REFERENCE", 0),
        ("RADAR_50HZ_TICK_REFERENCE", 0),
      ], CanBus(CP).radar, enable_can_valid_diagnostics=enable_can_valid_diagnostics)

    return parsers
