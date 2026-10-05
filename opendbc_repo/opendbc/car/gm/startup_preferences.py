from opendbc.car.gm.values import gm_control_word, is_volt_one_pedal, camera_acc_pedal_profile, ALT_ACCS
"""Finalized GM speed-control choices; existing native envelopes are retained."""

from opendbc.car.gm.values import (is_volt_gateway_profile, is_volt_cc_profile, is_ordinary_cc_profile,
                                  is_conventional_cc_pedal_profile, is_silverado_cc_pedal_profile, SILVERADO_CC_PEDAL_WORDS,
                                  CONVENTIONAL_CC_PEDAL_STOCK_WORDS, GMFlags)
from opendbc.car.gm.values import (is_volt_ascm_longitudinal, is_volt_camera_longitudinal, is_volt_sdgm_profile,
                                  is_volt_camera_removed, is_lacrosse_gateway_profile, GMSafetyFlags)


def disable_long_supported(cp) -> bool:
  return (camera_acc_pedal_profile(cp) is not None or is_conventional_cc_pedal_profile(cp) or
          is_ordinary_cc_profile(cp) or is_volt_gateway_profile(cp) or is_volt_cc_profile(cp) or
          is_volt_ascm_longitudinal(cp) or is_volt_camera_longitudinal(cp) or is_volt_sdgm_profile(cp, longitudinal=True) or
          is_volt_camera_removed(cp, longitudinal=True) or is_lacrosse_gateway_profile(cp))


def prepare_disable_longitudinal(cp, requested: bool) -> None:
  profile = camera_acc_pedal_profile(cp)
  if requested and profile is not None:
    stock_words = {0xE100: 0xE110, 0xE101: 0xE111, 0xE102: 0xE112, 0xE103: 0xE113}
    if profile.volt:
      stock_words.update({start + index: 0xE210 + index for start in (0xE200, 0xE220, 0xE240, 0xE260) for index in range(4)})
    cp.safetyConfigs[0].safetyParam = stock_words.get(int(cp.safetyConfigs[0].safetyParam), int(cp.safetyConfigs[0].safetyParam))
    cp.openpilotLongitudinalControl = False
    cp.pcmCruise = True
    cp.autoResumeSng = False
    cp.minEnableSpeed = -1. if profile.volt or cp.carFingerprint in ALT_ACCS else 5. / 3.6
    return
  if requested and is_volt_one_pedal(cp):
    cp.safetyConfigs[0].safetyParam = gm_control_word(cp)
  if requested and is_volt_camera_removed(cp, longitudinal=True):
    cp.safetyConfigs[0].safetyParam = 0xC150
    cp.openpilotLongitudinalControl = False
    cp.pcmCruise = True
    return
  if requested and (is_volt_ascm_longitudinal(cp) or is_volt_camera_longitudinal(cp) or is_volt_sdgm_profile(cp, longitudinal=True)):
    # Withdraw into the corresponding existing camera stock owner before CI construction.
    cp.safetyConfigs[0].safetyParam &= ~int(GMSafetyFlags.HW_CAM_LONG | GMSafetyFlags.VOLT_LONG | GMSafetyFlags.VOLT_AUTO_HOLD)
    cp.openpilotLongitudinalControl = False
    cp.pcmCruise = True
    return
  if requested and disable_long_supported(cp):
    if is_lacrosse_gateway_profile(cp):
      cp.safetyConfigs[0].safetyParam = 0
    silverado = is_silverado_cc_pedal_profile(cp)
    ordinary_pedal = is_conventional_cc_pedal_profile(cp) and not silverado
    cp.openpilotLongitudinalControl = False
    if silverado:
      cp.safetyConfigs[0].safetyParam = SILVERADO_CC_PEDAL_WORDS[1][bool(cp.flags & GMFlags.NO_CAMERA)]
    elif ordinary_pedal:
      cp.safetyConfigs[0].safetyParam = CONVENTIONAL_CC_PEDAL_STOCK_WORDS[bool(cp.flags & GMFlags.NO_CAMERA)]


def gateway_sources_current(source_ns, now_ns: int) -> bool:
  # The selected brake is supplied by the exact finalized gateway profile.
  limits = (300_000_000, 300_000_000, 100_000_000, 100_000_000, 100_000_000, 100_000_000, 100_000_000)
  return (isinstance(source_ns, tuple) and len(source_ns) == len(limits) and
          all(source > 0 and 0 <= now_ns - source <= limit for source, limit in zip(source_ns, limits, strict=True)))
