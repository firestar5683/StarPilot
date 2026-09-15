#!/usr/bin/env python3
import numpy as np
from abc import ABC, abstractmethod

from openpilot.common.realtime import DT_HW
from openpilot.common.swaglog import cloudlog
from openpilot.common.pid import PIDController
from openpilot.system.hardware import HARDWARE

# comma 4 (mici) always uses the stock curve; comma 3/3X (tici/tizi) can opt into a more
# aggressive, cooler-targeting curve via the "C3/C3X Aggressive Cooling" toggle
IS_MICI = HARDWARE.get_device_type() == "mici"

# original comma/sunnypilot curve: quieter on tici/tizi (higher setpoint) than on mici
STOCK_CURVE = dict(offset=0, k_p=0, ff_low=60.0, ff_high=100.0) if IS_MICI else \
              dict(offset=5, k_p=0, ff_low=65.0, ff_high=105.0)
AGGRESSIVE_CURVE = dict(offset=-5, k_p=1.0, ff_low=55.0, ff_high=80.0)

class BaseFanController(ABC):
  @abstractmethod
  def update(self, cur_temp: float, ignition: bool, aggressive_cooling: bool = False) -> int:
    pass


class TiciFanController(BaseFanController):
  def __init__(self) -> None:
    super().__init__()
    cloudlog.info("Setting up TICI fan handler")

    self.last_ignition = False
    self.last_aggressive_cooling = False
    self.controller = PIDController(k_p=STOCK_CURVE["k_p"], k_i=4e-3, rate=(1 / DT_HW))

  def update(self, cur_temp: float, ignition: bool, aggressive_cooling: bool = False) -> int:
    use_aggressive = aggressive_cooling and not IS_MICI
    curve = AGGRESSIVE_CURVE if use_aggressive else STOCK_CURVE

    self.controller.pos_limit = 100 if ignition else 30
    self.controller.neg_limit = 30 if ignition else 0
    self.controller._k_p = [[0], [curve["k_p"]]]

    if ignition != self.last_ignition or use_aggressive != self.last_aggressive_cooling:
      self.controller.reset()

    error = cur_temp - (75 + curve["offset"])
    fan_pwr_out = int(self.controller.update(
                      error=error,
                      feedforward=np.interp(cur_temp, [curve["ff_low"], curve["ff_high"]], [0, 100])
                    ))

    self.last_ignition = ignition
    self.last_aggressive_cooling = use_aggressive
    return fan_pwr_out
