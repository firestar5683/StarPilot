"""Observe Tesla wheel presses for the display without changing vehicle button events."""
from opendbc.can import CANParser
from opendbc.car import Bus
from opendbc.car.tesla.values import CANBUS, CAR, DBC


MAX_SAMPLE_AGE_NS = 2_000_000_000
UI_WARNING_ADDRESS = 0x311
UI_WARNING_SIZE = 7


def tesla_button_dbc(cp) -> str | None:
  if cp.brand != "tesla" or cp.carFingerprint not in (CAR.TESLA_MODEL_3, CAR.TESLA_MODEL_Y):
    return None
  dbc = DBC[cp.carFingerprint][Bus.party]
  return dbc if dbc == "tesla_model3_party" else None


class TeslaStandbyButtonObserver:
  def __init__(self, dbc: str):
    self._parser = CANParser(dbc, [("UI_warning", 0)], CANBUS.party)
    self._pressed: bool | None = None
    self._last_sample_ns: int | None = None

  def update(self, messages, now_ns: int) -> int:
    """Return the latest fresh press's CAN boot-clock timestamp, or zero."""
    if self._last_sample_ns is not None and not 0 <= now_ns - self._last_sample_ns < MAX_SAMPLE_AGE_NS:
      self._pressed = None

    pressed_at = 0
    for message in messages:
      timestamp = int(message.logMonoTime)
      if not message.valid or not 0 <= now_ns - timestamp < MAX_SAMPLE_AGE_NS:
        continue
      if self._last_sample_ns is not None and timestamp <= self._last_sample_ns:
        continue
      frames = [(frame.address, frame.dat, frame.src) for frame in message.can
                if frame.address == UI_WARNING_ADDRESS and frame.src == CANBUS.party and len(frame.dat) == UI_WARNING_SIZE]
      if not frames:
        continue
      self._parser.update([(timestamp, frames)])
      values = self._parser.vl_all["UI_warning"]["scrollWheelPressed"]
      if not values:
        continue
      if self._last_sample_ns is not None and timestamp - self._last_sample_ns >= MAX_SAMPLE_AGE_NS:
        self._pressed = None
      for value in values:
        pressed = bool(value)
        if self._pressed is False and pressed:
          pressed_at = timestamp
        self._pressed = pressed
      self._last_sample_ns = timestamp
    return pressed_at
