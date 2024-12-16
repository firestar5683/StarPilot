import cereal.messaging as messaging
from cereal import car, custom
from panda import Panda
from openpilot.common.params import Params
from openpilot.common.numpy_fast import interp
from openpilot.selfdrive.car.hyundai.fingerprinting import can_fingerprint, get_one_can
from openpilot.selfdrive.car.hyundai.enable_radar_tracks import enable_radar_tracks
from openpilot.selfdrive.car.hyundai.hyundaicanfd import CanBus
from openpilot.selfdrive.car.hyundai.values import HyundaiFlags, HyundaiFlagsFP, CAR, DBC, CANFD_CAR, CAMERA_SCC_CAR, CANFD_RADAR_SCC_CAR, \
                                         CANFD_UNSUPPORTED_LONGITUDINAL_CAR, EV_CAR, HYBRID_CAR, LEGACY_SAFETY_MODE_CAR, \
                                         UNSUPPORTED_LONGITUDINAL_CAR, Buttons
from openpilot.selfdrive.car.hyundai.radar_interface import RADAR_START_ADDR
from openpilot.selfdrive.car import create_button_events, get_safety_config
from openpilot.selfdrive.car.interfaces import CarInterfaceBase
from openpilot.selfdrive.car.disable_ecu import disable_ecu

from openpilot.selfdrive.frogpilot.frogpilot_variables import params

Ecu = car.CarParams.Ecu
ButtonType = car.CarState.ButtonEvent.Type
FrogPilotButtonType = custom.FrogPilotCarState.ButtonEvent.Type
EventName = car.CarEvent.EventName
GearShifter = car.CarState.GearShifter
ENABLE_BUTTONS = (Buttons.RES_ACCEL, Buttons.SET_DECEL, Buttons.CANCEL)
BUTTONS_DICT = {Buttons.RES_ACCEL: ButtonType.accelCruise, Buttons.SET_DECEL: ButtonType.decelCruise,
                Buttons.GAP_DIST: ButtonType.gapAdjustCruise, Buttons.CANCEL: ButtonType.cancel}


class CarInterface(CarInterfaceBase):
  @staticmethod
  def _get_params(ret, candidate, fingerprint, car_fw, disable_openpilot_long, experimental_long, docs):
    use_new_api = params.get_bool("NewLongAPI")

    ret.carName = "hyundai"
    ret.radarUnavailable = RADAR_START_ADDR not in fingerprint[1] or DBC[ret.carFingerprint]["radar"] is None

    # These cars have been put into dashcam only due to both a lack of users and test coverage.
    # These cars likely still work fine. Once a user confirms each car works and a test route is
    # added to selfdrive/car/tests/routes.py, we can remove it from this list.
    # FIXME: the Optima Hybrid 2017 uses a different SCC12 checksum
    ret.dashcamOnly = candidate in {CAR.KIA_OPTIMA_H, }

    hda2 = Ecu.adas in [fw.ecu for fw in car_fw]
    CAN = CanBus(None, hda2, fingerprint)

    if candidate in CANFD_CAR:
      # detect if car is hybrid
      if 0x105 in fingerprint[CAN.ECAN]:
        ret.flags |= HyundaiFlags.HYBRID.value
      elif candidate in EV_CAR:
        ret.flags |= HyundaiFlags.EV.value

      # detect HDA2 with ADAS Driving ECU
      if hda2:
        ret.flags |= HyundaiFlags.CANFD_HDA2.value
        if 0x110 in fingerprint[CAN.CAM]:
          ret.flags |= HyundaiFlags.CANFD_HDA2_ALT_STEERING.value
      else:
        # non-HDA2
        if 0x1cf not in fingerprint[CAN.ECAN]:
          ret.flags |= HyundaiFlags.CANFD_ALT_BUTTONS.value
        # ICE cars do not have 0x130; GEARS message on 0x40 or 0x70 instead
        if 0x130 not in fingerprint[CAN.ECAN]:
          if 0x40 not in fingerprint[CAN.ECAN]:
            ret.flags |= HyundaiFlags.CANFD_ALT_GEARS_2.value
          else:
            ret.flags |= HyundaiFlags.CANFD_ALT_GEARS.value
        if candidate not in CANFD_RADAR_SCC_CAR:
          ret.flags |= HyundaiFlags.CANFD_CAMERA_SCC.value
    else:
      # TODO: detect EV and hybrid
      if candidate in HYBRID_CAR:
        ret.flags |= HyundaiFlags.HYBRID.value
      elif candidate in EV_CAR:
        ret.flags |= HyundaiFlags.EV.value

      # Send LFA message on cars with HDA
      if 0x485 in fingerprint[2]:
        ret.flags |= HyundaiFlags.SEND_LFA.value

      # These cars use the FCA11 message for the AEB and FCW signals, all others use SCC12
      if 0x38d in fingerprint[0] or 0x38d in fingerprint[2]:
        ret.flags |= HyundaiFlags.USE_FCA.value

      if 0x53E in fingerprint[2]:
        ret.fpFlags |= HyundaiFlagsFP.FP_LKAS12.value

    ret.steerActuatorDelay = 0.1  # Default delay
    ret.steerLimitTimer = 0.4
    CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    if candidate == CAR.KIA_OPTIMA_G4_FL:
      ret.steerActuatorDelay = 0.2

    # *** longitudinal control ***
    # Determine if candidate is in CANFD_CAR
    is_canfd_car = candidate in CANFD_CAR

    # Set FP_CAMERA_SCC_LEAD flag if applicable
    if (is_canfd_car and ret.flags & HyundaiFlags.CANFD_CAMERA_SCC and not hda2) or \
      (not is_canfd_car and candidate in CAMERA_SCC_CAR):
        ret.fpFlags |= HyundaiFlagsFP.FP_CAMERA_SCC_LEAD.value

    # Configure longitudinal tuning
    if params.get_bool("HKGtuning"):
        ret.longitudinalTuning.deadzoneBP = [0.0]
        ret.longitudinalTuning.deadzoneV = [0.0]
        ret.longitudinalTuning.kpBP = [0.0]
        ret.longitudinalTuning.kiBP = [0.0]
        ret.longitudinalTuning.kiV = [0.0]
        ret.vEgoStopping = 0.12
        ret.vEgoStarting = 0.15

        if ret.flags & (HyundaiFlags.HYBRID | HyundaiFlags.EV):
            ret.startingState = False
            ret.longitudinalActuatorDelay = 0.2
        else:
            ret.startingState = True
            ret.startAccel = 1.0
            ret.longitudinalActuatorDelay = 0.25

        if is_canfd_car:
            ret.longitudinalTuning.kpV = [0.1]
            ret.stoppingDecelRate = 0.15
        else:
            ret.longitudinalTuning.kpV = [0.5]
            ret.stoppingDecelRate = 0.1
    else:
        ret.longitudinalTuning.deadzoneBP = [0.0]
        ret.longitudinalTuning.deadzoneV = [0.0]
        ret.longitudinalTuning.kpV = [0.1] if is_canfd_car else [0.5]
        ret.longitudinalTuning.kiV = [0.0]

    # Configure API-specific longitudinal tuning
    if use_new_api:
        # New API tuning parameters
        if is_canfd_car:
            ret.longitudinalTuning.kpV = [0.1]
            ret.stoppingDecelRate = 0.1
        else:
            ret.longitudinalTuning.kpV = [0.5]
            ret.stoppingDecelRate = 0.1
    else:
        # Old API tuning parameters (already handled above)
        pass

    # Determine experimental longitudinal availability
    unsupported_long_cars = (
        CANFD_UNSUPPORTED_LONGITUDINAL_CAR | CANFD_RADAR_SCC_CAR
        if is_canfd_car
        else UNSUPPORTED_LONGITUDINAL_CAR
    )
    ret.experimentalLongitudinalAvailable = candidate not in unsupported_long_cars

    # Configure longitudinal control flags
    ret.openpilotLongitudinalControl = experimental_long and ret.experimentalLongitudinalAvailable
    ret.pcmCruise = not ret.openpilotLongitudinalControl
    ret.stoppingControl = True

    # Configure radar settings
    if DBC[ret.carFingerprint]["radar"] is None and ret.fpFlags & HyundaiFlagsFP.FP_CAMERA_SCC_LEAD.value:
        ret.radarTimeStep = 0.02
        ret.radarUnavailable = False

    # *** feature detection ***
    if candidate in CANFD_CAR:
      ret.enableBsm = 0x1e5 in fingerprint[CAN.ECAN]

      if 0x1fa in fingerprint[CAN.ECAN]:
        ret.flags |= HyundaiFlags.NAV_MSG.value
    else:
      ret.enableBsm = 0x58b in fingerprint[0]

      if 0x544 in fingerprint[0]:
        ret.flags |= HyundaiFlags.NAV_MSG.value

      if ret.flags & HyundaiFlags.MANDO_RADAR and ret.radarUnavailable:
        ret.fpFlags |= HyundaiFlagsFP.FP_RADAR_TRACKS.value
        if Params().get_bool("HyundaiRadarTracksAvailable"):
          ret.radarUnavailable = False

    # *** panda safety config ***
    if candidate in CANFD_CAR:
      cfgs = [get_safety_config(car.CarParams.SafetyModel.hyundaiCanfd), ]
      if CAN.ECAN >= 4:
        cfgs.insert(0, get_safety_config(car.CarParams.SafetyModel.noOutput))
      ret.safetyConfigs = cfgs

      if ret.flags & HyundaiFlags.CANFD_HDA2:
        ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_CANFD_HDA2
        if ret.flags & HyundaiFlags.CANFD_HDA2_ALT_STEERING:
          ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_CANFD_HDA2_ALT_STEERING
      if ret.flags & HyundaiFlags.CANFD_ALT_BUTTONS:
        ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_CANFD_ALT_BUTTONS
      if ret.flags & HyundaiFlags.CANFD_CAMERA_SCC:
        ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_CAMERA_SCC
    else:
      if candidate in LEGACY_SAFETY_MODE_CAR:
        # these cars require a special panda safety mode due to missing counters and checksums in the messages
        ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.hyundaiLegacy)]
      else:
        ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.hyundai, 0)]

      if candidate in CAMERA_SCC_CAR:
        ret.safetyConfigs[0].safetyParam |= Panda.FLAG_HYUNDAI_CAMERA_SCC

      if 0x391 in fingerprint[0]:
        ret.flags |= HyundaiFlags.CAN_LFA_BTN.value
        ret.safetyConfigs[0].safetyParam |= Panda.FLAG_HYUNDAI_LFA_BTN

    if ret.openpilotLongitudinalControl:
      ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_LONG
    if ret.flags & HyundaiFlags.HYBRID:
      ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_HYBRID_GAS
    elif ret.flags & HyundaiFlags.EV:
      ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_EV_GAS

    if candidate in (CAR.HYUNDAI_KONA, CAR.HYUNDAI_KONA_EV, CAR.HYUNDAI_KONA_HEV, CAR.HYUNDAI_KONA_EV_2022):
      ret.flags |= HyundaiFlags.ALT_LIMITS.value
      ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_ALT_LIMITS

    ret.centerToFront = ret.wheelbase * 0.4

    # Detect smartMDPS
    if 0x2AA in fingerprint[0]:
      ret.minSteerSpeed = 0.

    return ret

  #Initialize radar tracks if enabled in FrogPilot Variables.
  @staticmethod
  def initialize_radar_tracks(CP, logcan, sendcan):
    if not (CP.fpFlags & HyundaiFlagsFP.FP_RADAR_TRACKS):
        return

    params = Params()
    if not params.get_bool("HyundaiRadarTracks"):
        return

    # Enable radar tracks config
    enable_radar_tracks(logcan, sendcan,
                       bus=0,
                       addr=0x7d0,
                       config_data_id=b'\x01\x42')

    # Handle radar tracks availability status
    CarInterface.update_radar_tracks_availability(params, logcan, CP)

  @staticmethod
  def update_radar_tracks_availability(params, logcan, CP):
    rt_avail = params.get_bool("HyundaiRadarTracksAvailable")
    rt_avail_persist = params.get_bool("HyundaiRadarTracksAvailablePersistent")

    # Cache current availability
    params.put_bool_nonblocking("HyundaiRadarTracksAvailableCache", rt_avail)

    # Only update persistent status if not already set
    if not rt_avail_persist:
        messaging.drain_sock_raw(logcan)
        fingerprint = can_fingerprint(lambda: get_one_can(logcan))
        radar_unavailable = RADAR_START_ADDR not in fingerprint[1] or DBC[CP.carFingerprint]["radar"] is None

        params.put_bool_nonblocking("HyundaiRadarTracksAvailable", not radar_unavailable)
        params.put_bool_nonblocking("HyundaiRadarTracksAvailablePersistent", True)

  @staticmethod
  def init(CP, logcan, sendcan):
    CarInterface.initialize_radar_tracks(CP, logcan, sendcan)
    if CP.openpilotLongitudinalControl and not (CP.flags & (HyundaiFlags.CANFD_CAMERA_SCC | HyundaiFlags.CAMERA_SCC)):
      addr, bus = 0x7d0, CanBus(CP).ECAN if CP.carFingerprint in CANFD_CAR else 0
      if CP.flags & HyundaiFlags.CANFD_HDA2.value:
        addr, bus = 0x730, CanBus(CP).ECAN
      disable_ecu(logcan, sendcan, bus=bus, addr=addr, com_cont_req=b'\x28\x83\x01')

    # for blinkers
    if CP.flags & HyundaiFlags.ENABLE_BLINKERS:
      disable_ecu(logcan, sendcan, bus=CanBus(CP).ECAN, addr=0x7B1, com_cont_req=b'\x28\x83\x01')

  def _update(self, c, frogpilot_toggles):
    ret, fp_ret = self.CS.update(self.cp, self.cp_cam, frogpilot_toggles)

    if self.CS.CP.openpilotLongitudinalControl:
      ret.buttonEvents = [
        *create_button_events(self.CS.cruise_buttons[-1], self.CS.prev_cruise_buttons, BUTTONS_DICT),
        *create_button_events(self.CS.lkas_enabled, self.CS.lkas_previously_enabled, {1: FrogPilotButtonType.lkas}),
      ]


    # On some newer model years, the CANCEL button acts as a pause/resume button based on the PCM state
    # To avoid re-engaging when openpilot cancels, check user engagement intention via buttons
    # Main button also can trigger an engagement on these cars
    allow_enable = any(btn in ENABLE_BUTTONS for btn in self.CS.cruise_buttons) or any(self.CS.main_buttons)
    events = self.create_common_events(ret, extra_gears=[GearShifter.sport, GearShifter.manumatic],
                                       pcm_enable=self.CS.CP.pcmCruise, allow_enable=allow_enable)

    # low speed steer alert hysteresis logic (only for cars with steer cut off above 10 m/s)
    if ret.vEgo < (self.CP.minSteerSpeed + 2.) and self.CP.minSteerSpeed > 10.:
      self.low_speed_alert = True
    if ret.vEgo > (self.CP.minSteerSpeed + 4.):
      self.low_speed_alert = False
    if self.low_speed_alert:
      events.add(car.CarEvent.EventName.belowSteerSpeed)

    if frogpilot_toggles.hyundai_radar_tracks and self.CS.params_list.hyundai_radar_tracks_available \
    and not self.CS.params_list.hyundai_radar_tracks_available_cache:
      events.add(car.CarEvent.EventName.hyundaiRadarTracksAvailable)

    ret.events = events.to_msg()

    return ret, fp_ret
