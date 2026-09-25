"""Exact main-only classic ICE Kona independent lateral identity."""
from opendbc.car.structs import CarParams
from opendbc.car.hyundai.values import CAR, HyundaiFlags

# Exact classic namespace, independently distinct from Forte1400/1c00.
KONA_AOL_MARKER = 0x0400
KONA_STOCK_WORD = 0x1040
KONA_AOL_WORD = 0x1440
KONA_AOL_EXPERIENCE = 32


def qualified(cp):
  allowed = (HyundaiFlags.NON_SCC | HyundaiFlags.ALT_LIMITS | HyundaiFlags.NON_SCC_RADAR_FCA |
             HyundaiFlags.USE_FCA | HyundaiFlags.SEND_LFA)
  required = HyundaiFlags.NON_SCC | HyundaiFlags.ALT_LIMITS
  return (cp.carFingerprint == CAR.HYUNDAI_KONA_NON_SCC and cp.brand == 'hyundai' and
          cp.alternativeExperience in (0, KONA_AOL_EXPERIENCE) and
          not cp.passive and not cp.dashcamOnly and not cp.notCar and
          not cp.openpilotLongitudinalControl and cp.pcmCruise and
          int(cp.flags) & int(required) == int(required) and not int(cp.flags) & ~int(allowed) and
          len(cp.safetyConfigs) == 1 and cp.safetyConfigs[0].safetyModel == CarParams.SafetyModel.hyundai and
          cp.safetyConfigs[0].safetyParam in (KONA_STOCK_WORD, KONA_AOL_WORD))


def allow_lateral_onset(*, permitted, normal_enabled, steering_pressed, previous_active):
  """Preserve original retry-on-grip-release, after actual native permission."""
  return bool(permitted and not (not normal_enabled and not previous_active and steering_pressed))
