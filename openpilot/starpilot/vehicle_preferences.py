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
  tesla_preap_stock: bool = True
  volt_sng: bool = False
  gm_auto_hold: bool = False
  volt_one_pedal: bool = False
  tesla_screen: bool = False
  tesla_screen_brake: bool = False
  gm_camera_pedal: bool = True
  toyota_filter: bool = True
  gm_longitudinal_tune: int = 0

  @classmethod
  def read(cls, params, *, enabled: bool):
    from openpilot.starpilot.car.gm.tune_preferences import selected_tune
    from openpilot.starpilot.car.tesla.preap_preferences import stock_configuration
    preap_stock = stock_configuration(params)
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
      volt_sng = bool(enabled and read_saved(params, "VoltSNG", 8) == (b"1", True) and
                      readable and safe in (None, b"0"))
      gm_auto_hold = bool(enabled and not disable_bolt and read_saved(params, "GMAutoHold", 8) == (b"1", True) and
                          readable and safe in (None, b"0"))
      volt_one_pedal = bool(enabled and not disable_bolt and read_saved(params, "VoltOnePedalMode", 8) == (b"1", True) and
                            readable and safe in (None, b"0"))
    except (OSError, TypeError, ValueError):
      return cls(disable_bolt_long=disable_bolt, honda_bosch_a_radar=honda_radar, tesla_preap_stock=preap_stock,
                 gm_camera_pedal=False, toyota_filter=False)
    try:
      pitch, pitch_readable = read_saved(params, "LongPitch", 8)
      pitch_enabled = not (enabled and pitch_readable and pitch == b"0" and readable and safe in (None, b"0"))
    except (OSError, TypeError, ValueError):
      pitch_enabled = True
    try:
      assist_raw, assist_readable = read_saved(params, "TurnAssist", 8)
      assist = assist_readable and assist_raw in (None, b"1")
    except (OSError, TypeError, ValueError):
      assist = False
    screen = bool(enabled and readable and safe in (None, b"0") and
                  read_saved(params, 'AlwaysOnLateral', 8) == (b'1', True) and
                  read_saved(params, 'TeslaAOLScreenTap', 8) == (b'1', True))
    screen_brake = read_saved(params, 'TeslaAOLDisengageOnBrake', 8) == (b'1', True)
    return cls(tesla_screen=screen, tesla_screen_brake=screen_brake, toyota_auto_hold=toyota,
               gm_longitudinal_tune=selected_tune(params, enabled=enabled),
               volt_sng=volt_sng, gm_auto_hold=gm_auto_hold, volt_one_pedal=volt_one_pedal,
               gm_camera_pedal=bool(enabled and not disable_bolt and readable and safe in (None, b"0")),
               toyota_filter=bool(enabled and not disable_bolt and readable and safe in (None, b"0")),
               turn_assist=bool(enabled and assist and readable and safe in (None, b"0")),
               gm_long_pitch=pitch_enabled, disable_bolt_long=disable_bolt, honda_bosch_a_radar=honda_radar, tesla_preap_stock=preap_stock)

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

  def _prepare_camera_pedal(self, cp) -> None:
    from opendbc.car.gm.values import camera_acc_pedal_profile, volt_cc_pedal_profile
    if not self.gm_camera_pedal and (camera_acc_pedal_profile(cp) is not None or volt_cc_pedal_profile(cp) is not None):
      prepare_disable_longitudinal(cp, True)

  def prepare(self, cp, *, fingerprints=None):
    from opendbc.car.gm.values import apply_gm_auto_hold, apply_volt_one_pedal
    from openpilot.starpilot.car.tesla.preap_preferences import prepare_stock
    prepare_stock(cp, self.tesla_preap_stock)
    from opendbc.car.tesla.screen_button import apply_screen_button
    apply_screen_button(cp, self.tesla_screen, self.tesla_screen_brake)
    self._prepare_honda_radar(cp)
    if not self.toyota_filter:
      from opendbc.car.toyota.prius_longitudinal import prepare_stock as prepare_prius_stock
      prepare_prius_stock(cp)
    self._prepare_bolt(cp, fingerprints)
    prepare_disable_longitudinal(cp, self.disable_bolt_long)
    self._prepare_camera_pedal(cp)
    apply_gm_auto_hold(cp, self.gm_auto_hold)
    apply_volt_one_pedal(cp, self.volt_one_pedal and not self.disable_bolt_long, self.gm_auto_hold)
    if cp.brand == "toyota":
      apply_toyota_auto_hold(cp, self.toyota_auto_hold)
    return cp

  def finalize(self, cp) -> None:
    from opendbc.car.gm.values import apply_gm_auto_hold, is_gm_auto_hold, apply_volt_one_pedal, is_volt_one_pedal
    admitted_one_pedal = is_volt_one_pedal(cp)
    admitted_hold = is_gm_auto_hold(cp)
    from openpilot.starpilot.car.tesla.preap_preferences import prepare_stock
    prepare_stock(cp, self.tesla_preap_stock)
    from opendbc.car.tesla.screen_button import apply_screen_button
    apply_screen_button(cp, self.tesla_screen, self.tesla_screen_brake)
    self._prepare_honda_radar(cp)
    if not self.toyota_filter:
      from opendbc.car.toyota.prius_longitudinal import prepare_stock as prepare_prius_stock
      prepare_prius_stock(cp)
    self._prepare_bolt(cp)
    prepare_disable_longitudinal(cp, self.disable_bolt_long)
    self._prepare_camera_pedal(cp)
    apply_gm_auto_hold(cp, self.gm_auto_hold and admitted_hold)
    apply_volt_one_pedal(cp, self.volt_one_pedal and admitted_one_pedal and not self.disable_bolt_long, self.gm_auto_hold and admitted_hold)
    if cp.brand == "toyota":
      admitted = bool(cp.flags & ToyotaFlags.AUTO_BRAKE_HOLD)
      apply_toyota_auto_hold(cp, self.toyota_auto_hold and admitted)

  def configure_controller(self, ci) -> None:
    from opendbc.car.gm.values import (CAR, is_bolt_euv_longitudinal, is_volt_longitudinal, is_gm_auto_hold,
                                     is_volt_one_pedal, camera_acc_pedal_profile, volt_cc_pedal_profile)
    cp = ci.CP
    if ci.CC is not None and is_volt_longitudinal(cp):
      ci.CC.volt_sng = self.volt_sng
    if ci.CC is not None and cp.brand == "gm":
      ci.CC.gm_auto_hold = self.gm_auto_hold and is_gm_auto_hold(cp)
      ci.CC.volt_one_pedal = self.volt_one_pedal and is_volt_one_pedal(cp)
    pedal = camera_acc_pedal_profile(cp) or volt_cc_pedal_profile(cp)
    if ci.CC is not None and (is_bolt_euv_longitudinal(cp) or is_volt_longitudinal(cp) or cp.carFingerprint == CAR.CHEVROLET_SUBURBAN or
                             pedal is not None and pedal.longitudinal):
      ci.CC.long_pitch = self.gm_long_pitch
