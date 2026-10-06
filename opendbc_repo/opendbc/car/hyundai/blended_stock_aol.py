from opendbc.car import structs
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.classic_scc_aol import ClassicSccLkasSources

AOL_EXPERIENCE = 32
WORDS = frozenset((0x2000,))


def qualified(cp, *, marked_only=False):
  if cp.carFingerprint != CAR.HYUNDAI_PALISADE_2023 or cp.brand != 'hyundai':
    return False
  declared = int(CAR.HYUNDAI_PALISADE_2023.config.flags)
  dynamic = int(HyundaiFlags.CANFD_LKA_STEER_MSG | HyundaiFlags.HAS_LDA_BUTTON | HyundaiFlags.USE_FCA | HyundaiFlags.SEND_LFA)
  if (
    int(cp.flags) & ~dynamic != declared
    or cp.passive
    or cp.notCar
    or cp.dashcamOnly
    or cp.openpilotLongitudinalControl
    or not cp.pcmCruise
    or cp.steerControlType != structs.CarParams.SteerControlType.torque
    or len(cp.safetyConfigs) != 1
    or cp.alternativeExperience not in ((AOL_EXPERIENCE,) if marked_only else (0, AOL_EXPERIENCE))
  ):
    return False
  hda2 = bool(cp.flags & HyundaiFlags.CANFD_LKA_STEER_MSG)
  if hda2:
    return False
  bus = CanBus(cp)
  return (
    (bus.ECAN, bus.ACAN, bus.CAM) == (0, 1, 2)
    and cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.hyundai
    and cp.safetyConfigs[0].safetyParam == 0x2000
  )


class MixedStockLkasSources(ClassicSccLkasSources):
  def __init__(self, cp):
    super().__init__(cp.carFingerprint)
    self.cp = cp
    self.bus = CanBus(cp).ECAN

  @property
  def active(self):
    return qualified(self.cp, marked_only=True) or qualified_alpha(self.cp, marked_only=True)

  def update(self, packets):
    if not self.active:
      return
    selected = [(stamp, [(address, data, 0) for address, data, bus in frames if bus == self.bus]) for stamp, frames in packets]
    super().update(selected)


ALPHA_WORDS = frozenset((0x2004,))


def qualified_alpha(cp, *, marked_only=False):
  from opendbc.car.hyundai.blended_longitudinal import hdai_startup_qualified
  return (hdai_startup_qualified(cp, allow_marked=True) and cp.alphaLongitudinalAvailable and
          cp.openpilotLongitudinalControl and not cp.pcmCruise and
          cp.safetyConfigs[0].safetyParam == 0x2004 and
          cp.alternativeExperience in ((32,) if marked_only else (0, 32)))
