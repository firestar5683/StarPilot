import time
import json
from dataclasses import dataclass

from openpilot.common.params import Params
from openpilot.system.hardware import HARDWARE, PC
from openpilot.selfdrive.ui.ui_state import ui_state
from cereal import car, log, custom, messaging
from opendbc.car.gm.values import GMFlags
from opendbc.car.hyundai.values import HyundaiFlags

@dataclass
class StarPilotCarState:
    # ========== Car Type Detection ==========
    isGM: bool = False
    isHKG: bool = False
    isToyota: bool = False
    isSubaru: bool = False
    isVolt: bool = False
    isBolt: bool = False
    isAngleCar: bool = False
    isTorqueCar: bool = False
    isTSK: bool = False
    isHKGCanFd: bool = False
    
    # ========== Car Capabilities ==========
    hasBSM: bool = False
    hasRadar: bool = True
    hasPedal: bool = False
    hasSASCM: bool = False
    hasSNG: bool = False
    hasNNFFLog: bool = True
    hasAutoTune: bool = True
    hasOpenpilotLongitudinal: bool = True
    hasDashSpeedLimits: bool = True
    hasZSS: bool = False
    canUsePedal: bool = False
    canUseSDSU: bool = False

    # ========== Device/Car State ==========
    isFrogsGoMoo: bool = False
    hasPCMCruise: bool = False
    hasModeStarButtons: bool = False
    lkasAllowedForAOL: bool = False
    openpilotLongitudinalControlDisabled: bool = False
    hasAlphaLongitudinal: bool = False
    
    # ========== Car Values for Range Calculation ==========
    steerActuatorDelay: float = 0.0
    friction: float = 0.0
    steerKp: float = 1.0
    latAccelFactor: float = 0.0
    steerRatio: float = 0.0
    longitudinalActuatorDelay: float = 0.0
    startAccel: float = 0.0
    stopAccel: float = 0.0
    stoppingDecelRate: float = 0.0
    vEgoStarting: float = 0.0
    vEgoStopping: float = 0.0

class StarPilotState:
    _instance: 'StarPilotState | None' = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.params = Params()
        self.car_state = StarPilotCarState()
        self.tuning_level: int = 0
        self.toggle_levels: dict[str, int] = {}
        
        self._param_update_time = 0.0
        self.update()

    def _apply_manual_fingerprint(self, starpilot_toggles: dict):
        fallback_make = starpilot_toggles.get("car_make") or self.params.get("CarMake") or "gm"
        fallback_model = starpilot_toggles.get("car_model") or self.params.get("CarModel") or "CHEVROLET_BOLT_ACC_2022_2023"

        from openpilot.selfdrive.ui.lib.fingerprint_catalog import FINGERPRINT_MAKE_TO_VALUES_DIR
        fallback_make_lower = fallback_make.lower()
        brand = FINGERPRINT_MAKE_TO_VALUES_DIR.get(fallback_make_lower, fallback_make_lower)

        self.car_state.isBolt = fallback_model.startswith("CHEVROLET_BOLT")
        self.car_state.isGM = brand == "gm"
        self.car_state.isHKG = brand == "hyundai"
        self.car_state.isSubaru = brand == "subaru"
        self.car_state.isToyota = brand == "toyota"
        self.car_state.isVolt = fallback_model.startswith("CHEVROLET_VOLT")

        # Determine isHKGCanFd for manual selection
        is_canfd = False
        try:
            from opendbc.car.hyundai.values import CANFD_CAR
            is_canfd = any(fallback_model == getattr(c, "value", str(c)) for c in CANFD_CAR)
        except Exception:
            pass
        self.car_state.isHKGCanFd = self.car_state.isHKG and is_canfd

        self.car_state.hasModeStarButtons = self.car_state.isHKGCanFd
        self.car_state.hasPedal = starpilot_toggles.get("has_pedal", True)
        self.car_state.hasSASCM = starpilot_toggles.get("has_sascm", False)
        self.car_state.hasSDSU = starpilot_toggles.get("has_sdsu", False)
        self.car_state.hasZSS = starpilot_toggles.get("has_zss", False)
        self.car_state.canUsePedal = self.car_state.hasPedal or self.car_state.isBolt
        self.car_state.canUseSDSU = self.car_state.hasSDSU

    def _safe_get(self, obj, field: str, default=None):
        try:
            return getattr(obj, field)
        except Exception:
            return default

    def update(self, force: bool = False) -> None:
        # Throttle heavy param parsing to avoid slowing down UI
        current_time = time.monotonic()
        if not force and current_time - self._param_update_time < 2.0:
            return
            
        self._param_update_time = current_time

        self.tuning_level = self.params.get_int("TuningLevel")
        force_fingerprint = self.params.get_bool("ForceFingerprint")
        
        # Read starpilot_toggles from params memory or scene
        try:
            starpilot_toggles = json.loads(self.params.get("StarPilotToggles") or "{}")
        except:
            starpilot_toggles = {}

        # 1. Parse CarParamsPersistent
        cp_bytes = self.params.get("CarParamsPersistent")
        if cp_bytes is not None:
            CP = messaging.log_from_bytes(cp_bytes, car.CarParams)
            safety_configs = self._safe_get(CP, "safetyConfigs", [])
            safety_model = safety_configs[0].safetyModel if len(safety_configs) > 0 else None

            car_fingerprint = self._safe_get(CP, "carFingerprint", "")
            car_make = self._safe_get(CP, "brand", self._safe_get(CP, "carName", ""))
            
            # Map values
            if self._safe_get(CP, "lateralTuning", None) is not None and CP.lateralTuning.which() == 'torque':
                self.car_state.friction = self._safe_get(CP.lateralTuning.torque, "friction", self.car_state.friction)
                self.car_state.latAccelFactor = self._safe_get(CP.lateralTuning.torque, "latAccelFactor", self.car_state.latAccelFactor)
                self.car_state.isTorqueCar = True
            else:
                self.car_state.isTorqueCar = False
                
            self.car_state.hasAlphaLongitudinal = bool(self._safe_get(CP, "alphaLongitudinalAvailable", False))
            self.car_state.hasBSM = bool(self._safe_get(CP, "enableBsm", False))
            self.car_state.hasDashSpeedLimits = car_make in ("ford", "hyundai", "toyota")
            # hasNNFFLog is default True for now
            self.car_state.hasOpenpilotLongitudinal = bool(self._safe_get(CP, "openpilotLongitudinalControl", False))
            self.car_state.hasPCMCruise = bool(self._safe_get(CP, "pcmCruise", False))
            self.car_state.hasPedal = bool(self._safe_get(CP, "enableGasInterceptorDEPRECATED", False))
            self.car_state.hasSASCM = car_make == "gm" and bool(self._safe_get(CP, "flags", 0) & GMFlags.SASCM.value)
            self.car_state.hasRadar = not bool(self._safe_get(CP, "radarUnavailable", False))
            self.car_state.hasSDSU = starpilot_toggles.get("has_sdsu", False)
            self.car_state.hasSNG = bool(self._safe_get(CP, "autoResumeSng", False))
            self.car_state.hasZSS = starpilot_toggles.get("has_zss", False)
            self.car_state.isAngleCar = self._safe_get(CP, "steerControlType", None) == car.CarParams.SteerControlType.angle
            self.car_state.isBolt = car_fingerprint.startswith("CHEVROLET_BOLT")
            self.car_state.isGM = car_make == "gm"
            self.car_state.isHKG = car_make == "hyundai"
            self.car_state.isHKGCanFd = self.car_state.isHKG and safety_model == car.CarParams.SafetyModel.hyundaiCanfd
            self.car_state.isSubaru = car_make == "subaru"
            self.car_state.isToyota = car_make == "toyota"
            self.car_state.isTSK = bool(self._safe_get(CP, "secOcRequired", False))
            self.car_state.isVolt = car_fingerprint.startswith("CHEVROLET_VOLT")
            
            cp_flags = self._safe_get(CP, "flags", 0)
            self.car_state.hasModeStarButtons = car_make == "hyundai" and bool(cp_flags & HyundaiFlags.CANFD)
            self.car_state.lkasAllowedForAOL = (
                (car_make == "hyundai" and (bool(cp_flags & HyundaiFlags.CANFD) or starpilot_toggles.get("lkas_allowed_for_aol", False))) or
                car_make == "honda"
            )
            self.car_state.longitudinalActuatorDelay = float(self._safe_get(CP, "longitudinalActuatorDelay", self.car_state.longitudinalActuatorDelay))
            self.car_state.startAccel = float(self._safe_get(CP, "startAccel", self.car_state.startAccel))
            self.car_state.steerActuatorDelay = float(self._safe_get(CP, "steerActuatorDelay", self.car_state.steerActuatorDelay))
            self.car_state.steerRatio = float(self._safe_get(CP, "steerRatio", self.car_state.steerRatio))
            self.car_state.stopAccel = float(self._safe_get(CP, "stopAccel", self.car_state.stopAccel))
            self.car_state.stoppingDecelRate = float(self._safe_get(CP, "stoppingDecelRate", self.car_state.stoppingDecelRate))
            self.car_state.vEgoStarting = float(self._safe_get(CP, "vEgoStarting", self.car_state.vEgoStarting))
            self.car_state.vEgoStopping = float(self._safe_get(CP, "vEgoStopping", self.car_state.vEgoStopping))
            
            if (PC or force_fingerprint) and (car_make == "mock" or car_fingerprint == "MOCK"):
                self._apply_manual_fingerprint(starpilot_toggles)
            elif PC or force_fingerprint:
                self._apply_manual_fingerprint(starpilot_toggles)

        elif PC or force_fingerprint:
            self._apply_manual_fingerprint(starpilot_toggles)

        # 2. Parse StarPilotCarParamsPersistent
        fpcp_bytes = self.params.get("StarPilotCarParamsPersistent")
        if fpcp_bytes is not None:
            try:
                FPCP = messaging.log_from_bytes(fpcp_bytes, custom.StarPilotCarParams)
                self.car_state.canUsePedal = FPCP.canUsePedal
                self.car_state.canUseSDSU = FPCP.canUseSDSU
                self.car_state.openpilotLongitudinalControlDisabled = FPCP.openpilotLongitudinalControlDisabled
            except Exception:
                pass

        # 3. Parse LiveTorqueParameters
        ltp_bytes = self.params.get("LiveTorqueParameters")
        if ltp_bytes is not None:
            try:
                event = log.Event.from_bytes(ltp_bytes)
                self.car_state.hasAutoTune = event.liveTorqueParameters.useParams
            except Exception:
                pass

# Global instance
starpilot_state = StarPilotState()
