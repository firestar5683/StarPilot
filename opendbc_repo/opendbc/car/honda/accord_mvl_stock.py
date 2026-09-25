from opendbc.car import structs
from opendbc.car.honda import hondacan
from opendbc.car.honda.values import CAR, CruiseSettings, HondaFlags


def qualified(cp):
  return (cp.carFingerprint == CAR.HONDA_ACCORD_11G and cp.brand == "honda" and
          not cp.passive and not cp.dashcamOnly and not cp.notCar and
          cp.transmissionType in (structs.CarParams.TransmissionType.automatic, structs.CarParams.TransmissionType.cvt) and
          cp.pcmCruise and not cp.openpilotLongitudinalControl and cp.alternativeExperience == 0 and
          len(cp.safetyConfigs) == 1 and cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.hondaBosch and
          cp.safetyConfigs[0].safetyParam == (80 | int(bool(cp.flags & HondaFlags.BOSCH_ALT_BRAKE))) and
          not int(cp.flags) & ~(int(CAR.HONDA_ACCORD_11G.config.flags) |
                                int(HondaFlags.BOSCH_ALT_BRAKE | HondaFlags.BOSCH_EXT_HUD | HondaFlags.HAS_BSM)))


class AccordMvlStock:
  def __init__(self):
    self.lkas_button_send_remaining = 0
    self.last_lkas_button_frame = 0

  def update(self, packer, can, cp, control, state, frame):
    if not control.enabled or frame % 4 or control.cruiseControl.cancel or control.cruiseControl.resume:
      return []
    if (self.lkas_button_send_remaining == 0 and state.lkas_hud["LKAS_READY"] and
        frame >= self.last_lkas_button_frame + 500):
      self.lkas_button_send_remaining = 3
    if self.lkas_button_send_remaining > 0:
      self.last_lkas_button_frame = frame
      self.lkas_button_send_remaining -= 1
      setting = CruiseSettings.LKAS
    elif state.cruise_setting == CruiseSettings.LKAS:
      setting = 0
    else:
      setting = state.cruise_setting
    return [hondacan.spam_buttons_command(packer, can, state.cruise_buttons, cp,
                                        cruise_setting=setting, ambient_light=state.scm_ambient_light, bus=can.camera)]
