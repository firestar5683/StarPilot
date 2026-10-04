from dataclasses import dataclass

from opendbc.car.gm.startup_preferences import prepare_disable_longitudinal
from opendbc.car.toyota.interface import apply_toyota_auto_hold
from opendbc.car.toyota.values import ToyotaFlags
from openpilot.starpilot.saved_source import read_saved


def bolt_disable_supported(cp) -> bool:
  from opendbc.car.gm.values import is_bolt_cc_profile, is_bolt_pedal_profile, is_bolt_pedal_stock_denied
  identities = ("CHEVROLET_BOLT_CC_2017", "CHEVROLET_BOLT_CC_2018_2021", "CHEVROLET_BOLT_CC_2022_2023",
                "CHEVROLET_BOLT_ACC_2022_2023_PEDAL")
  return cp.carFingerprint in identities and (is_bolt_cc_profile(cp) or is_bolt_pedal_profile(cp) or
                                               is_bolt_pedal_profile(cp, stock_only=True) or is_bolt_pedal_stock_denied(cp))


@dataclass(frozen=True)
class VehicleStartupPreferences:
  toyota_auto_hold: bool = False
  turn_assist: bool = False
  gm_long_pitch: bool = True
  disable_bolt_long: bool = False
  honda_bosch_a_radar: bool = True

  @classmethod
  def read(cls, params, *, enabled: bool):
    try:
      raw_radar, radar_readable = read_saved(params, "HondaBoschARadar", 8)
      honda_radar = radar_readable and raw_radar in (None, b"1")
    except (OSError, TypeError, ValueError):
      honda_radar = False
    try:
      raw, readable = read_saved(params, "DisableOpenpilotLongitudinal", 8)
      disable_bolt = not readable or raw not in (None, b"0")
    except (OSError, TypeError, ValueError):
      disable_bolt = True
    try:
      requested = read_saved(params, "ToyotaAutoHold", 8) == (b"1", True)
      safe, readable = read_saved(params, "SafeMode", 8)
      toyota = bool(enabled and requested and readable and safe in (None, b"0"))
    except (OSError, TypeError, ValueError):
      return cls(disable_bolt_long=disable_bolt, honda_bosch_a_radar=honda_radar)
    try:
      pitch, pitch_readable = read_saved(params, "LongPitch", 8)
      pitch_enabled = not (enabled and pitch_readable and pitch == b"0" and readable and safe in (None, b"0"))
    except (OSError, TypeError, ValueError):
      pitch_enabled = True
    try:
      assist = read_saved(params, "TurnAssist", 8) == (b"1", True)
    except (OSError, TypeError, ValueError):
      assist = False
    return cls(toyota_auto_hold=toyota, turn_assist=bool(enabled and assist and readable and safe in (None, b"0")),
               gm_long_pitch=pitch_enabled, disable_bolt_long=disable_bolt, honda_bosch_a_radar=honda_radar)

  def _prepare_honda_radar(self, cp) -> None:
    if cp.brand != "honda":
      return
    from opendbc.car.honda.bosch_a_radar import VERIFIED_BOSCH_A_CARS
    from opendbc.car.honda.values import HondaFlags
    if (cp.brand == "honda" and cp.carFingerprint in VERIFIED_BOSCH_A_CARS and cp.flags & HondaFlags.BOSCH and
        not cp.flags & (HondaFlags.BOSCH_RADARLESS | HondaFlags.BOSCH_CANFD | HondaFlags.BOSCH_ALT_RADAR)):
      cp.radarUnavailable = not self.honda_bosch_a_radar

  def _prepare_bolt(self, cp, fingerprints=None) -> None:
    if self.disable_bolt_long and bolt_disable_supported(cp):
      from opendbc.car.gm.values import CAR, GMSafetyFlags, is_bolt_pedal_profile, is_bolt_pedal_stock_denied
      from opendbc.car.structs import CarParams
      pedal = is_bolt_pedal_profile(cp) or is_bolt_pedal_profile(cp, stock_only=True) or is_bolt_pedal_stock_denied(cp)
      stock_qualified = is_bolt_pedal_profile(cp, stock_only=True)
      denied = is_bolt_pedal_stock_denied(cp)
      cp.openpilotLongitudinalControl = False
      if pedal:
        cp.pcmCruise = True
        if cp.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
          if stock_qualified or denied:
            return
          camera = fingerprints.get(2, {}) if isinstance(fingerprints, dict) else {}
          length = camera.get(0x180) if isinstance(camera, dict) else None
          if type(length) is int and length == 4:
            cp.safetyConfigs[0].safetyParam = int(GMSafetyFlags.HW_CAM | GMSafetyFlags.EV)
          else:
            safety = CarParams.SafetyConfig()
            safety.safetyModel = CarParams.SafetyModel.noOutput
            cp.safetyConfigs = [safety]
            cp.passive = True
            cp.dashcamOnly = True

  def prepare(self, cp, *, fingerprints=None):
    self._prepare_honda_radar(cp)
    self._prepare_bolt(cp, fingerprints)
    prepare_disable_longitudinal(cp, self.disable_bolt_long)
    if cp.brand == "toyota":
      apply_toyota_auto_hold(cp, self.toyota_auto_hold)
    return cp

  def finalize(self, cp) -> None:
    self._prepare_honda_radar(cp)
    self._prepare_bolt(cp)
    prepare_disable_longitudinal(cp, self.disable_bolt_long)
    if cp.brand == "toyota":
      admitted = bool(cp.flags & ToyotaFlags.AUTO_BRAKE_HOLD)
      apply_toyota_auto_hold(cp, self.toyota_auto_hold and admitted)

  def configure_controller(self, ci) -> None:
    from opendbc.car.gm.values import CAR, is_bolt_euv_longitudinal, is_volt_longitudinal
    cp = ci.CP
    if ci.CC is not None and (is_bolt_euv_longitudinal(cp) or is_volt_longitudinal(cp) or cp.carFingerprint == CAR.CHEVROLET_SUBURBAN):
      ci.CC.long_pitch = self.gm_long_pitch
