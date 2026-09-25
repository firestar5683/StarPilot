"""Immutable captured status shared by exact first-generation ADRV senders."""
from dataclasses import dataclass

from opendbc.car.can_definitions import CanData
from opendbc.car.crc import CRC16_XMODEM


def _checksum(data: bytes | bytearray) -> int:
  crc = 0
  for byte in data[2:]:
    crc = ((crc << 8) ^ CRC16_XMODEM[(crc >> 8) ^ byte]) & 0xFFFF
  for byte in (0x51, 0):
    crc = ((crc << 8) ^ CRC16_XMODEM[(crc >> 8) ^ byte]) & 0xFFFF
  return crc ^ 0x9F5B


@dataclass(frozen=True)
class CapturedADRVTemplate:
  data: bytes

  def __post_init__(self):
    if not isinstance(self.data, bytes) or len(self.data) != 32:
      raise ValueError('Captured ADRV template requires immutable 32-byte capture')
    if not any(self.data[3:]):
      raise ValueError('Captured ADRV capture has no opaque status body')
    if int.from_bytes(self.data[:2], 'little') != _checksum(self.data):
      raise ValueError('Captured ADRV capture checksum is invalid')

  @classmethod
  def capture(cls, data: bytes):
    return cls(data)

  @property
  def counter(self) -> int:
    return self.data[2]

  def _frame_data(self, frame: int, drive_gear: bool, bus: int) -> bytearray:
    if type(frame) is not int or frame < 0:
      raise ValueError('Captured ADRV frame must be a nonnegative integer')
    if type(drive_gear) is not bool or type(bus) is not int or bus != 0:
      raise ValueError('Captured ADRV requires physical Drive state and A-CAN bus zero')
    data = bytearray(self.data)
    data[2] = (self.counter + frame + 1) & 0xFF
    data[3] = (data[3] & ~1) | int(drive_gear)
    return data

  @staticmethod
  def _finish(data: bytearray, bus: int) -> CanData:
    data[:2] = _checksum(data).to_bytes(2, 'little')
    return CanData(0x51, bytes(data), bus)

  def frame(self, frame: int, drive_gear: bool, bus: int = 0) -> CanData:
    return self._finish(self._frame_data(frame, drive_gear, bus), bus)
