"""Vehicle startup evidence for external model hardware."""

from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.values import CAR


def model_power_ready_bus(CP) -> int | None:
  # This car briefly interrupts accessory power when transitioning into READY.
  return CanBus(CP).ECAN if CP.carFingerprint == CAR.HYUNDAI_IONIQ_6 else None


def model_power_ready(messages, bus: int) -> bool | None:
  ready = None
  for message in messages:
    if message.address == 0x35 and message.src == bus and len(message.dat) == 32:
      ready = bool(message.dat[3] & 0x40)
  return ready
