import math

import numpy as np

from opendbc.car import structs
from opendbc.car.can_definitions import CanData
from opendbc.car.honda.values import CAR, HondaFlags

LongCtrlState = structs.CarControl.Actuators.LongControlState
NIDEC_INTERCEPTOR_CARS = frozenset((
  CAR.ACURA_ILX,
  CAR.HONDA_CRV,
  CAR.HONDA_CRV_EU,
  CAR.HONDA_CRV_SA,
  CAR.HONDA_FIT,
  CAR.HONDA_FREED,
  CAR.HONDA_HRV,
  CAR.HONDA_CLARITY,
  CAR.HONDA_ODYSSEY,
  CAR.HONDA_ODYSSEY_TWN,
  CAR.ACURA_RDX,
  CAR.HONDA_PILOT,
  CAR.HONDA_RIDGELINE,
  CAR.HONDA_CIVIC,
  CAR.HONDA_ACCORD_9G,
  CAR.ACURA_MDX_3G,
  CAR.ACURA_MDX_3G_MMR,
  CAR.ACURA_TLX_1G,
))


def qualified(cp):
  configs = [config for config in cp.safetyConfigs if config.safetyModel != structs.CarParams.SafetyModel.noOutput]
  return (cp.brand == "honda" and cp.carFingerprint in NIDEC_INTERCEPTOR_CARS and
          not cp.flags & HondaFlags.BOSCH and cp.flags & HondaFlags.GAS_INTERCEPTOR and
          cp.openpilotLongitudinalControl and not cp.pcmCruise and
          not cp.passive and not cp.dashcamOnly and not cp.notCar and len(configs) == 1 and
          configs[0].safetyModel == structs.CarParams.SafetyModel.hondaNidec and
          configs[0].safetyParam == (36 if cp.flags & HondaFlags.NIDEC_ALT_SCM_MESSAGES else 32))


def create_command(packer, gas_amount, counter):
  enabled = gas_amount > 0.001
  values = {"ENABLE": enabled, "COUNTER_PEDAL": counter & 0xF}
  if enabled:
    values.update(GAS_COMMAND=gas_amount * 255.0, GAS_COMMAND2=gas_amount * 255.0)
  message = packer.make_can_msg("GAS_COMMAND", 0, values)
  data = bytearray(message[1])
  data[5] = pedal_crc(data)
  return CanData(0x200, bytes(data), 0)


def pedal_crc(data):
  crc = 0xFF
  for byte in reversed(data[:5]):
    crc ^= byte
    for _ in range(8):
      crc = ((crc << 1) ^ (0xD5 if crc & 0x80 else 0)) & 0xFF
  return crc


class NidecInterceptor:
  def __init__(self, cp):
    if not qualified(cp):
      raise ValueError("Honda interceptor requires its admitted Nidec profile")
    self.command = 0.0
    self.set_factors(1.0, 1.0)

  def set_factors(self, gas, wind):
    self.bosch_gas_factor = float(gas) if math.isfinite(gas) and 0.1 <= gas <= 3.0 else 1.0
    self.bosch_wind_factor = float(wind) if math.isfinite(wind) and 0.1 <= wind <= 5.0 else 1.0
    self.bosch_wind_factor_before_brake = self.bosch_wind_factor

  def update(self, CC, CS, gas, brake, wind_brake):
    gas_error = CC.actuators.accel - CS.out.aEgo
    if not CS.out.gasPressed and CC.actuators.longControlState == LongCtrlState.pid:
      if gas_error != 0.0 and gas > 0.0:
        self.bosch_gas_factor = float(np.clip(self.bosch_gas_factor + gas_error / 150.0 * (gas * 4.8), 0.1, 3.0))
      if gas_error != 0.0 and not CS.out.brakePressed and CS.out.vEgo > 0.0:
        wind_adjust = 1.0 + (wind_brake * 4.8) / 1000.0
        if gas_error > 0.0:
          self.bosch_wind_factor = float(np.clip(self.bosch_wind_factor * wind_adjust, 0.1, 5.0))
        else:
          self.bosch_wind_factor = float(np.clip(self.bosch_wind_factor / wind_adjust, 0.1, 5.0))
      if gas <= 0.0:
        self.bosch_wind_factor = max(self.bosch_wind_factor, self.bosch_wind_factor_before_brake)
      else:
        self.bosch_wind_factor_before_brake = self.bosch_wind_factor
    gas_mult = float(np.interp(CS.out.vEgo, [0.0, 10.0], [0.4, 1.0]))
    self.command = float(np.clip(gas_mult * ((gas * self.bosch_gas_factor) - brake +
                                (wind_brake * self.bosch_wind_factor * 3.0 / 4.0)), 0.0, 1.0)) if CC.longActive else 0.0
    return self.command
