#!/usr/bin/env python3
import numpy as np
from abc import ABC, abstractmethod

from openpilot.common.realtime import DT_HW
from openpilot.common.swaglog import cloudlog
from openpilot.common.pid import PIDController
from openpilot.system.hardware import HARDWARE

# comma 3/3X (tici/tizi) run a more aggressive, cooler-targeting curve than comma 4 (mici)
IS_MICI = HARDWARE.get_device_type() == "mici"
OFFSET = 0 if IS_MICI else -5
K_P = 0 if IS_MICI else 1.0
FF_LOW = 60.0 if IS_MICI else 55.0
FF_HIGH = 100.0 if IS_MICI else 80.0

class BaseFanController(ABC):
  @abstractmethod
  def update(self, cur_temp: float, ignition: bool) -> int:
    pass


class TiciFanController(BaseFanController):
  def __init__(self) -> None:
    super().__init__()
    cloudlog.info("Setting up TICI fan handler")

    self.last_ignition = False
    self.controller = PIDController(k_p=K_P, k_i=4e-3, rate=(1 / DT_HW))

  def update(self, cur_temp: float, ignition: bool) -> int:
    self.controller.pos_limit = 100 if ignition else 30
    self.controller.neg_limit = 30 if ignition else 0

    if ignition != self.last_ignition:
      self.controller.reset()

    error = cur_temp - (75 + OFFSET)
    fan_pwr_out = int(self.controller.update(
                      error=error,
                      feedforward=np.interp(cur_temp, [FF_LOW, FF_HIGH], [0, 100])
                    ))

    self.last_ignition = ignition
    return fan_pwr_out
