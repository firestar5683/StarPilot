from collections import deque
import copy
import math

from cereal import custom
from opendbc.can import CANDefine, CANParser
from opendbc.car import Bus, create_button_events, structs
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.values import HyundaiFlags, HyundaiStarPilotFlags, HyundaiStarPilotSafetyFlags, CAR, DBC, Buttons, CarControllerParams, \
                                       hyundai_cancel_button_enables_cruise, ALT_BUS_LDA_BUTTON_CARS, ALT_BUS_LDA_BUTTON_SWL_STAT_CARS
from opendbc.car.interfaces import CarStateBase

ButtonType = structs.CarState.ButtonEvent.Type

PREV_BUTTON_SAMPLES = 8
CLUSTER_SAMPLE_RATE = 20  # frames
STANDSTILL_THRESHOLD = 12 * 0.03125

# Cancel button can sometimes be ACC pause/resume button, main button can also enable on some cars
ENABLE_BUTTONS = (Buttons.RES_ACCEL, Buttons.SET_DECEL, Buttons.CANCEL)
BUTTONS_DICT = {Buttons.RES_ACCEL: ButtonType.accelCruise, Buttons.SET_DECEL: ButtonType.decelCruise,
                Buttons.GAP_DIST: ButtonType.gapAdjustCruise, Buttons.CANCEL: ButtonType.cancel}

IONIQ_6_BLINDSPOT_RIGHT_MASK = 0x08
IONIQ_6_BLINDSPOT_LEFT_MASK = 0x10
CANFD_CAMERA_LEAD_MIN_DISTANCE = 0.1
ALT_BUS_LDA_BUTTON_BURST_DEBOUNCE_NS = int(1.3e9)


def get_non_scc_cruise_signals(CP) -> tuple[str, str, str, str, str, str]:
  if CP.flags & HyundaiFlags.EV:
    return "LABEL11", "CC_React", "EMS12", "ACC_ACT", "E_EMS11", "Cruise_Limit_Target"
  if CP.flags & HyundaiFlags.HYBRID:
    return "E_CRUISE_CONTROL", "CRUISE_LAMP_M", "E_CRUISE_CONTROL", "CRUISE_LAMP_S", "ELECT_GEAR", "SLC_SET_SPEED"
  return "EMS16", "CRUISE_LAMP_M", "EMS16", "CRUISE_LAMP_S", "LVR12", "CF_Lvr_CruiseSet"


def calculate_canfd_speed_limit(CP, FPCP, cp, cp_cam, speed_factor):
  if not (FPCP.flags & HyundaiStarPilotFlags.SPEED_LIMIT_AVAILABLE):
    return 0.0

  speed_limit_bus = cp if CP.flags & HyundaiFlags.CANFD_LKA_STEERING else cp_cam
  try:
    speed_limit = speed_limit_bus.vl["FR_CMR_02_100ms"]["ISLW_SpdCluMainDis"]
    return speed_limit * speed_factor if 1 <= speed_limit <= 252 else 0.0
  except (KeyError, ValueError):
    return 0.0


def decode_ioniq_6_blindspot_radar_state(state: int) -> tuple[bool, bool]:
  state_int = int(state)
  return bool(state_int & IONIQ_6_BLINDSPOT_LEFT_MASK), bool(state_int & IONIQ_6_BLINDSPOT_RIGHT_MASK)


def decode_canfd_camera_lead(distance: float, rel_speed: float) -> tuple[bool, float, float]:
  lead_distance = float(distance)
  lead_visible = lead_distance > CANFD_CAMERA_LEAD_MIN_DISTANCE
  if not lead_visible:
    return False, 0.0, 0.0
  return True, lead_distance, float(rel_speed)


class CarState(CarStateBase):
  @staticmethod
  def get_canfd_blinker_sig_names(car_fingerprint, use_alt_lamp: bool) -> tuple[str, str]:
    if use_alt_lamp or car_fingerprint == CAR.HYUNDAI_KONA_EV_2ND_GEN:
      return "LEFT_LAMP_ALT", "RIGHT_LAMP_ALT"
    return "LEFT_LAMP", "RIGHT_LAMP"

  def __init__(self, CP, FPCP):
    super().__init__(CP, FPCP)
    can_define = CANDefine(DBC[CP.carFingerprint][Bus.pt])

    self.cruise_buttons: deque = deque([Buttons.NONE] * PREV_BUTTON_SAMPLES, maxlen=PREV_BUTTON_SAMPLES)
    self.main_buttons: deque = deque([Buttons.NONE] * PREV_BUTTON_SAMPLES, maxlen=PREV_BUTTON_SAMPLES)
    self.lda_button = 0
    self.lda_button_raw = 0
    self.lda_button_raw_initialized = False
    self.lda_button_last_raw_rise_ts_nanos = 0
    self.left_paddle = 0
    self.mode_button = 0
    self.custom_button = 0
    self.cancel_button_enable_in_progress = False
    self.cruise_buttons_msg = {}
    self.redneck_send_button = Buttons.NONE
    self.redneck_v_target = 0

    self.gear_msg_canfd = "ACCELERATOR" if CP.flags & HyundaiFlags.EV else \
                          "GEAR_ALT" if CP.flags & HyundaiFlags.CANFD_ALT_GEARS else \
                          "GEAR_ALT_2" if CP.flags & HyundaiFlags.CANFD_ALT_GEARS_2 else \
                          "GEAR_SHIFTER"
    if CP.flags & HyundaiFlags.CANFD:
      self.shifter_values = can_define.dv[self.gear_msg_canfd]["GEAR"]
    elif CP.flags & (HyundaiFlags.HYBRID | HyundaiFlags.EV):
      self.shifter_values = can_define.dv["ELECT_GEAR"]["Elect_Gear_Shifter"]
    elif self.CP.flags & HyundaiFlags.CLUSTER_GEARS:
      self.shifter_values = can_define.dv["CLU15"]["CF_Clu_Gear"]
    elif self.CP.flags & HyundaiFlags.TCU_GEARS:
      self.shifter_values = can_define.dv["TCU12"]["CUR_GR"]
    elif CP.flags & HyundaiFlags.FCEV:
      self.shifter_values = can_define.dv["EMS20"]["HYDROGEN_GEAR_SHIFTER"]
    else:
      self.shifter_values = can_define.dv["LVR12"]["CF_Lvr_Gear"]

    self.accelerator_msg_canfd = "ACCELERATOR" if CP.flags & HyundaiFlags.EV else \
                                 "ACCELERATOR_ALT" if CP.flags & HyundaiFlags.HYBRID else \
                                 "ACCELERATOR_BRAKE_ALT"
    self.cruise_btns_msg_canfd = "CRUISE_BUTTONS_ALT" if CP.flags & HyundaiFlags.CANFD_ALT_BUTTONS else \
                                 "CRUISE_BUTTONS"
    self.is_metric = False
    self.buttons_counter = 0

    self.cruise_info = {}
    self.msg_161 = {}
    self.msg_162 = {}
    self.msg_1b5 = {}
    self.msg_364 = {}
    self.stock_lkas_msg = {}
    self.stock_lfa_msg = {}
    self.stock_lfahda_cluster_msg = {}
    self.stock_camera_lead_visible = False
    self.stock_camera_lead_distance = 0.0
    self.stock_camera_lead_rel_speed = 0.0
    self.stock_camera_lead_ts = 0
    self.stock_blinker_stalks_ts = 0
    self.blindspots_rear_corners = {}
    self.blindspots_front_corner_1 = {}
    self.blindspots_rear_corners_ts = 0
    self.blindspots_front_corner_1_ts = 0
    self.left_blindspot_from_radar = False
    self.right_blindspot_from_radar = False

    # On some cars, CLU15->CF_Clu_VehicleSpeed can oscillate faster than the dash updates. Sample at 5 Hz
    self.cluster_speed = 0
    self.cluster_speed_counter = CLUSTER_SAMPLE_RATE

    self.params = CarControllerParams(CP)

  def recent_button_interaction(self) -> bool:
    # On some newer model years, the CANCEL button acts as a pause/resume button based on the PCM state
    # To avoid re-engaging when openpilot cancels, check user engagement intention via buttons
    # Main button also can trigger an engagement on these cars
    return any(btn in ENABLE_BUTTONS for btn in self.cruise_buttons) or any(self.main_buttons)

  def create_cruise_button_events(self, cur_button: int, prev_button: int) -> list[structs.CarState.ButtonEvent]:
    if cur_button != prev_button and prev_button != Buttons.CANCEL and cur_button == Buttons.CANCEL:
      self.cancel_button_enable_in_progress = (
        self.CP.openpilotLongitudinalControl and
        hyundai_cancel_button_enables_cruise(self.CP.carFingerprint) and
        not self.out.cruiseState.enabled
      )

    buttons_dict = BUTTONS_DICT
    if self.cancel_button_enable_in_progress:
      buttons_dict = BUTTONS_DICT | {Buttons.CANCEL: ButtonType.accelCruise}

    events = create_button_events(cur_button, prev_button, buttons_dict)

    if cur_button != Buttons.CANCEL:
      self.cancel_button_enable_in_progress = False

    return events

  def update_button_enable(self, buttonEvents: list[structs.CarState.ButtonEvent]):
    if super().update_button_enable(buttonEvents):
      return True

    if not self.CP.pcmCruise and hyundai_cancel_button_enables_cruise(self.CP.carFingerprint):
      for b in buttonEvents:
        # Some Palisade 2023 routes still surface the pause/resume interaction as a
        # plain cancel event even though stock ACC engages on the release edge.
        if b.type == ButtonType.cancel and not b.pressed and not self.out.cruiseState.enabled:
          return True

    return False

  def get_alt_bus_lda_button_raw_state(self, cp_source: CANParser) -> tuple[int, int]:
    if self.CP.carFingerprint in ALT_BUS_LDA_BUTTON_SWL_STAT_CARS:
      return int(cp_source.vl["CLU13"]["CF_Clu_SWL_Stat"] == 4), cp_source.ts_nanos["CLU13"]["CF_Clu_SWL_Stat"]
    return int(cp_source.vl["CLU13"]["CF_Clu_LdwsLkasSW"]), cp_source.ts_nanos["CLU13"]["CF_Clu_LdwsLkasSW"]

  def create_alt_bus_lda_button_events(self, cp_source: CANParser) -> list[structs.CarState.ButtonEvent]:
    raw_lda_button, raw_lda_button_ts_nanos = self.get_alt_bus_lda_button_raw_state(cp_source)
    button_events: list[structs.CarState.ButtonEvent] = []

    if not self.lda_button_raw_initialized:
      self.lda_button_raw_initialized = True
      self.lda_button_raw = raw_lda_button
      return button_events

    # Some alt-bus LKAS button layouts pulse several times per physical press burst.
    # Collapse each burst into a single synthetic press/release pair.
    if raw_lda_button and not self.lda_button_raw:
      if self.lda_button_last_raw_rise_ts_nanos == 0 or \
          raw_lda_button_ts_nanos - self.lda_button_last_raw_rise_ts_nanos > ALT_BUS_LDA_BUTTON_BURST_DEBOUNCE_NS:
        button_events = [
          structs.CarState.ButtonEvent(pressed=True, type=ButtonType.lkas),
          structs.CarState.ButtonEvent(pressed=False, type=ButtonType.lkas),
        ]
      self.lda_button_last_raw_rise_ts_nanos = raw_lda_button_ts_nanos

    self.lda_button_raw = raw_lda_button
    return button_events

  def create_lkas_button_events(self, cp: CANParser, prev_lda_button: int) -> list[structs.CarState.ButtonEvent]:
    if self.CP.carFingerprint == CAR.HYUNDAI_SONATA_HYBRID and cp.ts_nanos["BCM_PO_11"]["LDA_BTN"] > 0:
      # Route-proven: late-model Sonata Hybrid publishes a live LKAS button on BCM_PO_11
      # while CLU13 is present on the main bus but does not carry the LKAS state.
      self.lda_button = int(cp.vl["BCM_PO_11"]["LDA_BTN"])
    # Some classic HKG platforms publish the LKAS button on the cluster bus instead of BCM_PO_11.
    elif cp.ts_nanos["CLU13"]["CF_Clu_LdwsLkasSW"] > 0:
      self.lda_button = int(cp.vl["CLU13"]["CF_Clu_LdwsLkasSW"])
    elif cp.ts_nanos["BCM_PO_11"]["LDA_BTN"] > 0:
      self.lda_button = int(cp.vl["BCM_PO_11"]["LDA_BTN"])
    else:
      self.lda_button = 0

    return create_button_events(self.lda_button, prev_lda_button, {1: ButtonType.lkas})

  def update(self, can_parsers, starpilot_toggles) -> structs.CarState:
    cp = can_parsers[Bus.pt]
    cp_cam = can_parsers[Bus.cam]
    cp_alt = can_parsers.get(Bus.alt)

    if self.CP.flags & HyundaiFlags.CANFD:
      return self.update_canfd(can_parsers)

    ret = structs.CarState()
    cp_cruise = cp_cam if self.CP.flags & HyundaiFlags.CAMERA_SCC else cp
    self.is_metric = cp.vl["CLU11"]["CF_Clu_SPEED_UNIT"] == 0
    speed_conv = CV.KPH_TO_MS if self.is_metric else CV.MPH_TO_MS

    ret.doorOpen = any([cp.vl["CGW1"]["CF_Gway_DrvDrSw"], cp.vl["CGW1"]["CF_Gway_AstDrSw"],
                        cp.vl["CGW2"]["CF_Gway_RLDrSw"], cp.vl["CGW2"]["CF_Gway_RRDrSw"]])

    ret.seatbeltUnlatched = cp.vl["CGW1"]["CF_Gway_DrvSeatBeltSw"] == 0

    self.parse_wheel_speeds(ret,
      cp.vl["WHL_SPD11"]["WHL_SPD_FL"],
      cp.vl["WHL_SPD11"]["WHL_SPD_FR"],
      cp.vl["WHL_SPD11"]["WHL_SPD_RL"],
      cp.vl["WHL_SPD11"]["WHL_SPD_RR"],
    )
    ret.standstill = cp.vl["WHL_SPD11"]["WHL_SPD_FL"] <= STANDSTILL_THRESHOLD and cp.vl["WHL_SPD11"]["WHL_SPD_RR"] <= STANDSTILL_THRESHOLD

    self.cluster_speed_counter += 1
    if self.cluster_speed_counter > CLUSTER_SAMPLE_RATE:
      self.cluster_speed = cp.vl["CLU15"]["CF_Clu_VehicleSpeed"]
      self.cluster_speed_counter = 0

      # Mimic how dash converts to imperial.
      # Sorento is the only platform where CF_Clu_VehicleSpeed is already imperial when not is_metric
      # TODO: CGW_USM1->CF_Gway_DrLockSoundRValue may describe this
      if not self.is_metric and self.CP.carFingerprint not in (CAR.KIA_SORENTO,):
        self.cluster_speed = math.floor(self.cluster_speed * CV.KPH_TO_MPH + CV.KPH_TO_MPH)

    ret.vEgoCluster = self.cluster_speed * speed_conv

    ret.steeringAngleDeg = cp.vl["SAS11"]["SAS_Angle"]
    ret.steeringRateDeg = cp.vl["SAS11"]["SAS_Speed"]
    ret.leftBlinker, ret.rightBlinker = self.update_blinker_from_lamp(
      50, cp.vl["CGW1"]["CF_Gway_TurnSigLh"], cp.vl["CGW1"]["CF_Gway_TurnSigRh"])
    ret.steeringTorque = cp.vl["MDPS12"]["CR_Mdps_StrColTq"]
    ret.steeringTorqueEps = cp.vl["MDPS12"]["CR_Mdps_OutTq"]
    ret.steeringPressed = self.update_steering_pressed(abs(ret.steeringTorque) > self.params.STEER_THRESHOLD, 5)
    ret.steerFaultTemporary = cp.vl["MDPS12"]["CF_Mdps_ToiUnavail"] != 0 or cp.vl["MDPS12"]["CF_Mdps_ToiFlt"] != 0

    # cruise state
    no_scc = bool(self.CP.flags & HyundaiFlags.NON_SCC)
    if self.CP.openpilotLongitudinalControl:
      # These are not used for engage/disengage since openpilot keeps track of state using the buttons
      ret.cruiseState.available = cp.vl["TCS13"]["ACCEnable"] == 0
      ret.cruiseState.enabled = cp.vl["TCS13"]["ACC_REQ"] == 1
      ret.cruiseState.standstill = False
      ret.cruiseState.nonAdaptive = False
    elif no_scc:
      cruise_available_msg, cruise_available_sig, cruise_enabled_msg, cruise_enabled_sig, cruise_speed_msg, cruise_speed_sig = get_non_scc_cruise_signals(self.CP)
      ret.cruiseState.available = cp.vl[cruise_available_msg][cruise_available_sig] != 0
      ret.cruiseState.enabled = cp.vl[cruise_enabled_msg][cruise_enabled_sig] != 0
      ret.cruiseState.standstill = False
      ret.cruiseState.nonAdaptive = False
      ret.cruiseState.speed = cp.vl[cruise_speed_msg][cruise_speed_sig] * speed_conv
    else:
      scc_msg = "SCC12" if self.CP.flags & HyundaiFlags.CAN_CANFD_BLENDED else "SCC11"
      ret.cruiseState.available = cp_cruise.vl[scc_msg]["MainMode_ACC"] == 1
      ret.cruiseState.enabled = cp_cruise.vl["SCC12"]["ACCMode"] != 0
      ret.cruiseState.standstill = cp_cruise.vl[scc_msg]["SCCInfoDisplay"] == 4.
      ret.cruiseState.nonAdaptive = cp_cruise.vl[scc_msg]["SCCInfoDisplay"] == 2.  # Shows 'Cruise Control' on dash
      ret.cruiseState.speed = cp_cruise.vl[scc_msg]["VSetDis"] * speed_conv

    if self.CP.flags & HyundaiFlags.CAN_CANFD_BLENDED:
      self.msg_364 = copy.copy(cp_cam.vl["ALERTS_364"])

    # TODO: Find brake pressure
    ret.brake = 0
    ret.brakePressed = cp.vl["TCS13"]["DriverOverride"] == 2  # 2 includes regen braking by user on HEV/EV
    ret.brakeHoldActive = cp.vl["TCS15"]["AVH_LAMP"] == 2  # 0 OFF, 1 ERROR, 2 ACTIVE, 3 READY
    ret.parkingBrake = cp.vl["TCS13"]["PBRAKE_ACT"] == 1
    ret.espDisabled = cp.vl["TCS11"]["TCS_PAS"] == 1
    ret.espActive = cp.vl["TCS11"]["ABS_ACT"] == 1
    ret.accFaulted = False if no_scc else cp.vl["TCS13"]["ACCEnable"] != 0  # 0 ACC CONTROL ENABLED, 1-3 ACC CONTROL DISABLED

    if self.CP.flags & (HyundaiFlags.HYBRID | HyundaiFlags.EV | HyundaiFlags.FCEV):
      if self.CP.flags & HyundaiFlags.FCEV:
        ret.gasPressed = cp.vl["FCEV_ACCELERATOR"]["ACCELERATOR_PEDAL"] > 0
      elif self.CP.flags & HyundaiFlags.HYBRID:
        ret.gasPressed = cp.vl["E_EMS11"]["CR_Vcu_AccPedDep_Pos"] > 0
      else:
        ret.gasPressed = cp.vl["E_EMS11"]["Accel_Pedal_Pos"] > 0
    else:
      ret.gasPressed = bool(cp.vl["EMS16"]["CF_Ems_AclAct"])

    # Gear Selection via Cluster - For those Kia/Hyundai which are not fully discovered, we can use the Cluster Indicator for Gear Selection,
    # as this seems to be standard over all cars, but is not the preferred method.
    if self.CP.flags & (HyundaiFlags.HYBRID | HyundaiFlags.EV):
      gear = cp.vl["ELECT_GEAR"]["Elect_Gear_Shifter"]
    elif self.CP.flags & HyundaiFlags.FCEV:
      gear = cp.vl["EMS20"]["HYDROGEN_GEAR_SHIFTER"]
    elif self.CP.flags & HyundaiFlags.CLUSTER_GEARS:
      gear = cp.vl["CLU15"]["CF_Clu_Gear"]
    elif self.CP.flags & HyundaiFlags.TCU_GEARS:
      gear = cp.vl["TCU12"]["CUR_GR"]
    else:
      gear = cp.vl["LVR12"]["CF_Lvr_Gear"]

    ret.gearShifter = self.parse_gear_shifter(self.shifter_values.get(gear))

    if (not self.CP.openpilotLongitudinalControl or self.CP.flags & HyundaiFlags.CAMERA_SCC) and \
        not (self.CP.flags & HyundaiFlags.CAN_CANFD_BLENDED):
      if no_scc:
        if not (self.CP.flags & HyundaiFlags.NON_SCC_NO_FCA):
          cp_fca = cp if self.CP.flags & HyundaiFlags.NON_SCC_RADAR_FCA else cp_cam
          aeb_warning = cp_fca.vl["FCA11"]["CF_VSM_Warn"] != 0
          aeb_braking = cp_fca.vl["FCA11"]["CF_VSM_DecCmdAct"] != 0 or cp_fca.vl["FCA11"]["FCA_CmdAct"] != 0
          ret.stockFcw = aeb_warning and not aeb_braking
          ret.stockAeb = aeb_warning and aeb_braking
      else:
        aeb_src = "FCA11" if self.CP.flags & HyundaiFlags.USE_FCA.value else "SCC12"
        aeb_sig = "FCA_CmdAct" if self.CP.flags & HyundaiFlags.USE_FCA.value else "AEB_CmdAct"
        aeb_warning = cp_cruise.vl[aeb_src]["CF_VSM_Warn"] != 0
        scc_warning = cp_cruise.vl["SCC12"]["TakeOverReq"] == 1
        aeb_braking = cp_cruise.vl[aeb_src]["CF_VSM_DecCmdAct"] != 0 or cp_cruise.vl[aeb_src][aeb_sig] != 0
        ret.stockFcw = (aeb_warning or scc_warning) and not aeb_braking
        ret.stockAeb = aeb_warning and aeb_braking

    if self.CP.enableBsm:
      ret.leftBlindspot = cp.vl["LCA11"]["CF_Lca_IndLeft"] != 0
      ret.rightBlindspot = cp.vl["LCA11"]["CF_Lca_IndRight"] != 0

    # save the entire LKAS11 and CLU11
    self.lkas11 = copy.copy(cp_cam.vl["LKAS11"])
    self.clu11 = copy.copy(cp.vl["CLU11"])
    self.steer_state = cp.vl["MDPS12"]["CF_Mdps_ToiActive"]  # 0 NOT ACTIVE, 1 ACTIVE
    prev_cruise_buttons = self.cruise_buttons[-1]
    prev_main_buttons = self.main_buttons[-1]
    prev_lda_button = self.lda_button
    lkas_button_events = []
    self.cruise_buttons.extend(cp.vl_all["CLU11"]["CF_Clu_CruiseSwState"])
    self.main_buttons.extend(cp.vl_all["CLU11"]["CF_Clu_CruiseSwMain"])
    if self.CP.carFingerprint in ALT_BUS_LDA_BUTTON_CARS and cp_alt is not None and self.get_alt_bus_lda_button_raw_state(cp_alt)[1] > 0:
      lkas_button_events = self.create_alt_bus_lda_button_events(cp_alt)
    else:
      lkas_button_events = self.create_lkas_button_events(cp, prev_lda_button)

    ret.buttonEvents = [*self.create_cruise_button_events(self.cruise_buttons[-1], prev_cruise_buttons),
                        *create_button_events(self.main_buttons[-1], prev_main_buttons, {1: ButtonType.mainCruise}),
                        *lkas_button_events]

    ret.blockPcmEnable = not self.recent_button_interaction()

    # low speed steer alert hysteresis logic (only for cars with steer cut off above 10 m/s)
    if ret.vEgo < (self.CP.minSteerSpeed + 2.) and self.CP.minSteerSpeed > 10.:
      self.low_speed_alert = True
    if ret.vEgo > (self.CP.minSteerSpeed + 4.):
      self.low_speed_alert = False
    ret.lowSpeedAlert = self.low_speed_alert

    fp_ret = custom.StarPilotCarState.new_message()

    return ret, fp_ret

  def update_canfd(self, can_parsers) -> structs.CarState:
    cp = can_parsers[Bus.pt]
    cp_cam = can_parsers[Bus.cam]

    ret = structs.CarState()

    self.is_metric = cp.vl["CRUISE_BUTTONS_ALT"]["DISTANCE_UNIT"] != 1
    speed_factor = CV.KPH_TO_MS if self.is_metric else CV.MPH_TO_MS

    if self.CP.flags & (HyundaiFlags.EV | HyundaiFlags.HYBRID):
      ret.gasPressed = cp.vl[self.accelerator_msg_canfd]["ACCELERATOR_PEDAL"] > 1e-5
    else:
      ret.gasPressed = bool(cp.vl[self.accelerator_msg_canfd]["ACCELERATOR_PEDAL_PRESSED"])

    ret.brakePressed = cp.vl["TCS"]["DriverBraking"] == 1

    ret.doorOpen = cp.vl["DOORS_SEATBELTS"]["DRIVER_DOOR"] == 1
    ret.seatbeltUnlatched = cp.vl["DOORS_SEATBELTS"]["DRIVER_SEATBELT"] == 0

    gear = cp.vl[self.gear_msg_canfd]["GEAR"]
    ret.gearShifter = self.parse_gear_shifter(self.shifter_values.get(gear))

    # TODO: figure out positions
    self.parse_wheel_speeds(ret,
      cp.vl["WHEEL_SPEEDS"]["WHL_SpdFLVal"],
      cp.vl["WHEEL_SPEEDS"]["WHL_SpdFRVal"],
      cp.vl["WHEEL_SPEEDS"]["WHL_SpdRLVal"],
      cp.vl["WHEEL_SPEEDS"]["WHL_SpdRRVal"],
    )
    ret.standstill = cp.vl["WHEEL_SPEEDS"]["WHL_SpdFLVal"] <= STANDSTILL_THRESHOLD and cp.vl["WHEEL_SPEEDS"]["WHL_SpdFRVal"] <= STANDSTILL_THRESHOLD and \
                     cp.vl["WHEEL_SPEEDS"]["WHL_SpdRLVal"] <= STANDSTILL_THRESHOLD and cp.vl["WHEEL_SPEEDS"]["WHL_SpdRRVal"] <= STANDSTILL_THRESHOLD

    ret.steeringRateDeg = cp.vl["STEERING_SENSORS"]["STEERING_RATE"]
    ret.steeringAngleDeg = cp.vl["STEERING_SENSORS"]["STEERING_ANGLE"]
    ret.steeringTorque = cp.vl["MDPS"]["STEERING_COL_TORQUE"]
    ret.steeringTorqueEps = cp.vl["MDPS"]["STEERING_OUT_TORQUE"]
    ret.steeringPressed = self.update_steering_pressed(abs(ret.steeringTorque) > self.params.STEER_THRESHOLD, 5)
    ret.steerFaultTemporary = cp.vl["MDPS"]["LKA_FAULT"] != 0

    ccnc_non_hda2 = self.CP.flags & HyundaiFlags.CCNC and not self.CP.flags & HyundaiFlags.CANFD_LKA_STEERING
    if ccnc_non_hda2:
      self.msg_161 = copy.copy(cp_cam.vl["CCNC_0x161"])
      self.msg_162 = copy.copy(cp_cam.vl["CCNC_0x162"])
      self.msg_1b5 = copy.copy(cp_cam.vl["FR_CMR_03_50ms"])
      cp_cruise_info = cp_cam if self.CP.flags & HyundaiFlags.CANFD_CAMERA_SCC else cp
      self.cruise_info = copy.copy(cp_cruise_info.vl["SCC_CONTROL"])

    use_alt_lamp = cp.vl["BLINKERS"]["USE_ALT_LAMP"] == 1 or bool(self.CP.flags & HyundaiFlags.CCNC)
    left_blinker_sig, right_blinker_sig = self.get_canfd_blinker_sig_names(self.CP.carFingerprint, use_alt_lamp)
    ret.leftBlinker, ret.rightBlinker = self.update_blinker_from_lamp(50, cp.vl["BLINKERS"][left_blinker_sig],
                                                                      cp.vl["BLINKERS"][right_blinker_sig])
    self.left_blindspot_from_radar = False
    self.right_blindspot_from_radar = False
    if self.CP.carFingerprint == CAR.HYUNDAI_IONIQ_6:
      self.left_blindspot_from_radar, self.right_blindspot_from_radar = decode_ioniq_6_blindspot_radar_state(
        cp.vl["BLINDSPOTS_FRONT_CORNER_2"]["SIDE_DETECT_STATE"])
    if self.CP.enableBsm:
      if self.CP.carFingerprint == CAR.HYUNDAI_IONIQ_6:
        ret.leftBlindspot = (bool(cp.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_LtIndSta"]) or
                             self.left_blindspot_from_radar)
        ret.rightBlindspot = (bool(cp.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_RtIndSta"]) or
                              self.right_blindspot_from_radar)
      elif self.CP.flags & HyundaiFlags.CCNC:
        ret.leftBlindspot = bool(cp.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_LtIndSta"])
        ret.rightBlindspot = bool(cp.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_RtIndSta"])
      else:
        ret.leftBlindspot = bool(cp.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_LtIndSta"])
        ret.rightBlindspot = bool(cp.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_RtIndSta"])

    if self.CP.carFingerprint == CAR.HYUNDAI_IONIQ_6:
      self.blindspots_rear_corners = copy.copy(cp.vl["BLINDSPOTS_REAR_CORNERS"])
      self.blindspots_front_corner_1 = copy.copy(cp.vl["BLINDSPOTS_FRONT_CORNER_1"])
      self.blindspots_rear_corners_ts = cp.ts_nanos["BLINDSPOTS_REAR_CORNERS"]["CHECKSUM"]
      self.blindspots_front_corner_1_ts = cp.ts_nanos["BLINDSPOTS_FRONT_CORNER_1"]["CHECKSUM"]

    # cruise state
    # CAN FD cars enable on main button press, set available if no TCS faults preventing engagement
    ret.cruiseState.available = cp.vl["TCS"]["ACCEnable"] == 0
    if self.CP.openpilotLongitudinalControl and not self.CP.pcmCruise:
      # These are not used for engage/disengage since openpilot keeps track of state using the buttons
      ret.cruiseState.enabled = cp.vl["TCS"]["ACC_REQ"] == 1
      ret.cruiseState.standstill = False
    else:
      cp_cruise_info = cp_cam if self.CP.flags & HyundaiFlags.CANFD_CAMERA_SCC else cp
      ret.cruiseState.available = cp_cruise_info.vl["SCC_CONTROL"]["MainMode_ACC"] == 1
      ret.cruiseState.enabled = cp_cruise_info.vl["SCC_CONTROL"]["ACCMode"] in (1, 2)
      ret.cruiseState.standstill = cp_cruise_info.vl["SCC_CONTROL"]["CRUISE_STANDSTILL"] == 1
      ret.cruiseState.speed = cp_cruise_info.vl["SCC_CONTROL"]["VSetDis"] * speed_factor
      self.cruise_info = copy.copy(cp_cruise_info.vl["SCC_CONTROL"])

    # Manual Speed Limit Assist is a feature that replaces non-adaptive cruise control on EV CAN FD platforms.
    # It limits the vehicle speed, overridable by pressing the accelerator past a certain point.
    # The car will brake, but does not respect positive acceleration commands in this mode
    # TODO: find this message on ICE & HYBRID cars + cruise control signals (if exists)
    if self.CP.flags & HyundaiFlags.EV:
      ret.cruiseState.nonAdaptive = cp.vl["MANUAL_SPEED_LIMIT_ASSIST"]["MSLA_ENABLED"] == 1
    prev_cruise_buttons = self.cruise_buttons[-1]
    prev_main_buttons = self.main_buttons[-1]
    prev_lda_button = self.lda_button
    prev_left_paddle = self.left_paddle
    self.cruise_buttons.extend(cp.vl_all[self.cruise_btns_msg_canfd]["CRUISE_BUTTONS"])
    self.main_buttons.extend(cp.vl_all[self.cruise_btns_msg_canfd]["ADAPTIVE_CRUISE_MAIN_BTN"])
    self.lda_button = cp.vl[self.cruise_btns_msg_canfd]["LDA_BTN"]
    self.left_paddle = 0
    if self.CP.carFingerprint == CAR.HYUNDAI_IONIQ_6:
      self.cruise_buttons_msg = copy.copy(cp.vl["CRUISE_BUTTONS"])
      self.left_paddle = cp.vl["CRUISE_BUTTONS"]["LEFT_PADDLE"]
    self.buttons_counter = cp.vl[self.cruise_btns_msg_canfd]["COUNTER"]
    ret.accFaulted = cp.vl["TCS"]["ACCEnable"] != 0  # 0 ACC CONTROL ENABLED, 1-3 ACC CONTROL DISABLED

    if self.CP.flags & HyundaiFlags.CANFD_LKA_STEERING:
      lkas_msg = "LKAS_ALT" if self.CP.flags & HyundaiFlags.CANFD_LKA_STEERING_ALT else "LKAS"
      self.lfa_block_msg = copy.copy(cp_cam.vl["CAM_0x362"] if self.CP.flags & HyundaiFlags.CANFD_LKA_STEERING_ALT
                                          else cp_cam.vl["CAM_0x2a4"])
      if cp_cam.ts_nanos[lkas_msg]["CHECKSUM"] > 0:
        self.stock_lkas_msg = copy.copy(cp_cam.vl[lkas_msg])
    lead_cp = cp if self.CP.flags & HyundaiFlags.CANFD_LKA_STEERING else cp_cam
    if lead_cp.ts_nanos["FR_CMR_03_50ms"]["FR_CMR_Crc3Val"] > 0:
      self.stock_camera_lead_ts = lead_cp.ts_nanos["FR_CMR_03_50ms"]["FR_CMR_Crc3Val"]
      self.stock_camera_lead_visible, self.stock_camera_lead_distance, self.stock_camera_lead_rel_speed = decode_canfd_camera_lead(
        lead_cp.vl["FR_CMR_03_50ms"]["Longitudinal_Distance"],
        lead_cp.vl["FR_CMR_03_50ms"]["Relative_Velocity"],
      )
    if cp.ts_nanos["LFA"]["CHECKSUM"] > 0:
      self.stock_lfa_msg = copy.copy(cp.vl["LFA"])
    if cp.ts_nanos["LFAHDA_CLUSTER"]["CHECKSUM"] > 0:
      self.stock_lfahda_cluster_msg = copy.copy(cp.vl["LFAHDA_CLUSTER"])
    if cp.ts_nanos["BLINKER_STALKS"]["CHECKSUM_MAYBE"] > 0:
      self.stock_blinker_stalks_ts = cp.ts_nanos["BLINKER_STALKS"]["CHECKSUM_MAYBE"]

    ret.buttonEvents = [*self.create_cruise_button_events(self.cruise_buttons[-1], prev_cruise_buttons),
                        *create_button_events(self.main_buttons[-1], prev_main_buttons, {1: ButtonType.mainCruise}),
                        *create_button_events(self.lda_button, prev_lda_button, {1: ButtonType.lkas}),
                        *create_button_events(self.left_paddle, prev_left_paddle, {1: ButtonType.altButton2})]

    ret.blockPcmEnable = not self.recent_button_interaction()

    fp_ret = custom.StarPilotCarState.new_message()
    fp_ret.dashboardSpeedLimit = calculate_canfd_speed_limit(self.CP, self.FPCP, cp, cp_cam, speed_factor)

    if self.CP.flags & HyundaiFlags.EV:
      drive_mode = cp.vl["DRIVE_MODE_EV"]["DRIVE_MODE"]
      fp_ret.ecoGear = (drive_mode == 4)
      fp_ret.sportGear = (drive_mode == 5)

    self.mode_button = cp.vl["STEERING_WHEEL_MEDIA_BUTTONS"]["MODE_BUTTON"]
    self.custom_button = cp.vl["STEERING_WHEEL_MEDIA_BUTTONS"]["CUSTOM_BUTTON"]
    fp_ret.modePressed = bool(self.mode_button)
    fp_ret.customPressed = bool(self.custom_button)

    # ADAS camera dashboard stop-sign signal (CANFD HKG only). Registered as optional
    # (freq=0); cars without it never publish, so the read returns 0 and the field stays 0.
    fp_ret.dashboardStopSign = 1 if bool(cp_cam.vl["ADAS_0x380"]["STOP_SIGN"]) else 0

    return ret, fp_ret

  def get_can_parsers_canfd(self, CP):
    msgs = []
    cam_msgs = []
    if not (CP.flags & HyundaiFlags.CANFD_ALT_BUTTONS):
      # TODO: this can be removed once we add dynamic support to vl_all
      msgs += [
        # this message is 50Hz but the ECU frequently stops transmitting for ~0.5s
        ("CRUISE_BUTTONS", 1)
      ]
    if CP.flags & HyundaiFlags.CANFD_LKA_STEERING:
      msgs.append(("FR_CMR_02_100ms", 10))
      msgs.append(("FR_CMR_03_50ms", 0))
      cam_msgs.append(("LKAS_ALT" if CP.flags & HyundaiFlags.CANFD_LKA_STEERING_ALT else "LKAS", 0))
    else:
      cam_msgs.append(("FR_CMR_02_100ms", 0))  # optional: not all non-LKA CANFD cars have this on CAM bus
      cam_msgs.append(("FR_CMR_03_50ms", 0))  # optional: camera lead/cipv data is not present on every CAN-FD trim
      if CP.flags & HyundaiFlags.CCNC:
        cam_msgs += [
          ("CCNC_0x161", 0),
          ("CCNC_0x162", 0),
        ]
    msgs += [
      ("LFA", 0),             # optional: may stop once OP takes over, but preserve stock UI fields when present
      ("LFAHDA_CLUSTER", 0),  # optional: carries cluster icon state on some variants
      ("BLINKER_STALKS", 0),  # optional: some trims publish live stalk/light state on ECAN during turn camera events
    ]
    if CP.flags & HyundaiFlags.EV:
      msgs.append(("DRIVE_MODE_EV", 0))  # optional: not all CAN-FD EV variants publish drive mode
      msgs.append(("MANUAL_SPEED_LIMIT_ASSIST", 0))  # optional: used for non-adaptive cruise state and Ioniq 6 i-Pedal latch detection
    msgs.append(("STEERING_WHEEL_MEDIA_BUTTONS", 0))  # optional: absent or slower on some CAN-FD variants
    cam_msgs.append(("ADAS_0x380", 0))  # optional: dashboard stop-sign signal, only on ADAS-equipped HKG CANFD
    return {
      Bus.pt: CANParser(DBC[CP.carFingerprint][Bus.pt], msgs, CanBus(CP).ECAN),
      Bus.cam: CANParser(DBC[CP.carFingerprint][Bus.pt], cam_msgs, CanBus(CP).CAM),
    }

  def get_can_parsers(self, CP):
    if CP.flags & HyundaiFlags.CANFD:
      return self.get_can_parsers_canfd(CP)

    msgs = [
      ("BCM_PO_11", 0),
      ("CLU13", 0),
    ]
    if CP.flags & HyundaiFlags.NON_SCC and not (CP.flags & HyundaiFlags.NON_SCC_NO_FCA):
      msgs.append(("FCA11", 0))  # Non-SCC trims can stop publishing FCA11; don't let it poison canValid

    parsers = {
      Bus.pt: CANParser(DBC[CP.carFingerprint][Bus.pt], msgs, 0),
      Bus.cam: CANParser(DBC[CP.carFingerprint][Bus.pt], [], 2),
    }
    if CP.carFingerprint in ALT_BUS_LDA_BUTTON_CARS:
      parsers[Bus.alt] = CANParser(DBC[CP.carFingerprint][Bus.pt], [("CLU13", 0)], 1)
    return parsers
