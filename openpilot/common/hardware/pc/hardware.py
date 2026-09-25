import os
import re

from openpilot.cereal import log
from openpilot.common.hardware.base import HardwareBase

class HardwarePc(HardwareBase):
  def get_device_type(self):
    recorded = os.getenv("SP_REPLAY_DEVICE_TYPE", "")
    if (os.getenv("SP_HOST_RUNTIME") == "1" and recorded in ("tici", "tizi", "mici") and
        re.fullmatch(r"replay-[A-Za-z0-9_-]{1,48}", os.getenv("OPENPILOT_PREFIX", ""))):
      return recorded
    return "pc"

  def get_network_type(self):
    # some stuff is gated on wifi, so just assume for now
    return log.DeviceState.NetworkType.wifi
