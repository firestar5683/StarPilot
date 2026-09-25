"""Cabin-camera PiP selection and VisionIPC lifetime, independent of rendering.

The onroad view owns the renderer and supplies fresh vehicle signals. This
module never opens a camera until that view enables the PiP session.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
import time
from typing import Protocol

from openpilot.common.hardware import COMMA_HARDWARE


RETRY_SECONDS = 0.2
FRAME_STALE_SECONDS = 0.5
IMAGE_TO_VEHICLE_SIDE = {"left": "right", "right": "left"}


@dataclass(frozen=True)
class Crop:
  x: float
  y: float
  size: float


@dataclass(frozen=True)
class Rect:
  x: float
  y: float
  width: float
  height: float


def bubble_rect(content: Rect, side: str) -> Rect:
  """The frozen C3 bubble placement, in native onroad content coordinates."""
  if side not in ("left", "right") or content.width <= 0 or content.height <= 0:
    raise ValueError("invalid PiP content or side")
  radius = max(180, min(int(min(content.width, content.height) * 0.3), 420))
  x = content.x + 24 if side == "left" else content.x + content.width - 24 - 2 * radius
  y = content.y + content.height - 24 - 2 * radius
  return Rect(x, y, 2 * radius, 2 * radius)


def curved_crop(crop: Crop, panel: Rect) -> Rect:
  """C4 samples an aspect-matched band of the saved square without stretching."""
  if panel.width <= 0 or panel.height <= 0 or crop.size <= 0:
    raise ValueError("invalid PiP panel")
  aspect = panel.width / panel.height
  if aspect >= 1:
    height = crop.size / aspect
    return Rect(crop.x, crop.y + (crop.size - height) / 2, crop.size, height)
  width = crop.size * aspect
  return Rect(crop.x + (crop.size - width) / 2, crop.y, width, crop.size)


@dataclass(frozen=True)
class Mask:
  width: int
  height: int
  crop_size: float
  center_left: tuple[float, float] | None
  center_right: tuple[float, float] | None

  @classmethod
  def parse(cls, value: object) -> Mask | None:
    if not isinstance(value, dict) or set(value) != {"width", "height", "crop_size", "center_left", "center_right"}:
      return None
    width, height = value["width"], value["height"]
    if type(width) is not int or type(height) is not int or not (1 <= width <= 8192 and 1 <= height <= 8192):
      return None
    size = _finite(value["crop_size"])
    if size is None or not (1 <= size <= min(width, height)):
      return None

    def center(raw: object) -> tuple[float, float] | None:
      if raw is None:
        return None
      if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError("invalid center")
      x, y = _finite(raw[0]), _finite(raw[1])
      if x is None or y is None or x - size / 2 < 0 or x + size / 2 > width or y - size / 2 < 0 or y + size / 2 > height:
        raise ValueError("center outside image")
      return x, y

    try:
      left, right = center(value["center_left"]), center(value["center_right"])
    except ValueError:
      return None
    return cls(width, height, size, left, right)

  def for_frame(self, width: int, height: int) -> Mask | None:
    """Keep saved crop alignment when the cabin camera resolution changes."""
    if (width, height) == (self.width, self.height):
      return self
    formats = {(1928, 1208), (1344, 760)}
    if (self.width, self.height) not in formats or (width, height) not in formats:
      return None
    sx, sy = width / self.width, height / self.height
    def scaled(center):
      return None if center is None else [center[0] * sx, center[1] * sy]
    return Mask.parse({"width": width, "height": height, "crop_size": max(1.0, self.crop_size * min(sx, sy)),
                       "center_left": scaled(self.center_left), "center_right": scaled(self.center_right)})

  def crop(self, vehicle_side: str) -> Crop | None:
    image_side = IMAGE_TO_VEHICLE_SIDE.get(vehicle_side)
    if image_side is None:
      return None
    center = self.center_left if image_side == "left" else self.center_right
    return None if center is None else Crop(center[0] - self.crop_size / 2, center[1] - self.crop_size / 2, self.crop_size)


def _finite(value: object) -> float | None:
  if not isinstance(value, (int, float)) or isinstance(value, bool):
    return None
  try:
    result = float(value)
  except OverflowError:
    return None
  return result if math.isfinite(result) else None


@dataclass(frozen=True)
class Signals:
  """The caller has already checked carState and optional VASM freshness."""

  car_state_fresh: bool
  left_blinker: bool
  right_blinker: bool
  left_blindspot: bool
  right_blindspot: bool
  vasm_left: bool = False
  vasm_right: bool = False


def selected_sides(mask: Mask | None, signals: Signals, *, started: bool, enabled: bool,
                   on_blinker: bool, on_bsm: bool) -> tuple[str, ...]:
  """Select saved camera crops using PiP blinker and OEM blind-spot triggers."""
  if not (started and enabled and signals.car_state_fresh and mask is not None):
    return ()
  sides: list[str] = []
  for vehicle_side, blinker, blindspot in (
    ("right", signals.right_blinker, signals.right_blindspot),
    ("left", signals.left_blinker, signals.left_blindspot),
  ):
    if mask.crop(vehicle_side) is not None and ((on_blinker and blinker) or (on_bsm and blindspot)):
      sides.append(vehicle_side)
  return tuple(sides)


class _VisionClient(Protocol):
  num_buffers: int
  width: int
  height: int
  stride: int

  def is_connected(self) -> bool: ...
  def connect(self, block: bool) -> bool: ...
  def recv(self, timeout_ms: int) -> object | None: ...


def cabin_client() -> _VisionClient:
  """Use the actual camerad cabin stream; import only on onroad activation."""
  from msgq.visionipc import VisionIpcClient
  from openpilot.cereal.visionipc import VisionStreamType
  return VisionIpcClient("camerad", VisionStreamType.VISION_STREAM_CABIN, conflate=True)


class PiPStream:
  """One nonblocking cabin VisionIPC subscription with explicit expiry.

  A frame is borrowed only while this session retains its client. Rendering
  must happen synchronously after poll(); it must not keep VisionBuf pointers.
  """

  def __init__(self, client_factory: Callable[[], _VisionClient] = cabin_client, *,
               require_boot_eof: bool = COMMA_HARDWARE):
    self._factory = client_factory
    self._client: _VisionClient | None = None
    self._frame: object | None = None
    self._frame_id: int | None = None
    self._received_at: float | None = None
    self._capture_eof_ns: int | None = None
    self._last_attempt: float | None = None
    self._connected_at: float | None = None
    self._active = False
    self._require_boot_eof = require_boot_eof
    self._generation = 0
    self._retired_clients: list[_VisionClient] = []

  @property
  def generation(self) -> int:
    """Changes on every client loss or replacement, even within one poll."""
    return self._generation

  def release_retired(self) -> None:
    """The renderer calls this only after destroying the old GPU images."""
    self._retired_clients.clear()

  @property
  def connected(self) -> bool:
    return self._client is not None and self._client.is_connected()

  @property
  def frame_size(self) -> tuple[int, int] | None:
    if not self.connected or self._client is None:
      return None
    return self._client.width, self._client.height

  def set_active(self, active: bool) -> None:
    if not active:
      self.close()
    elif not self._active:
      self._active = True
      self._last_attempt = None

  def close(self) -> None:
    self._active = False
    self._release()
    self.release_retired()
    self._last_attempt = None

  def _release(self) -> None:
    if self._client is not None:
      self._retired_clients.append(self._client)
      self._generation += 1
    self._frame = None
    self._frame_id = None
    self._received_at = None
    self._capture_eof_ns = None
    self._connected_at = None
    self._client = None

  def poll(self, now: float, *, now_boot_ns: int | None = None) -> object | None:
    if not self._active or not math.isfinite(now):
      return None
    if self._require_boot_eof:
      if now_boot_ns is None and not hasattr(time, "CLOCK_BOOTTIME"):
        return None
      if now_boot_ns is not None and now_boot_ns <= 0:
        return None
    if self._client is not None and not self._client.is_connected():
      self._release()
    if self._client is None:
      if self._last_attempt is not None and 0 <= now - self._last_attempt < RETRY_SECONDS:
        return None
      self._last_attempt = now
      try:
        client = self._factory()
        if not client.connect(False) or client.num_buffers <= 0:
          return None
      except (OSError, RuntimeError):
        return None
      self._client = client
      self._connected_at = now
      self._generation += 1
    assert self._client is not None
    try:
      frame = self._client.recv(timeout_ms=0)
    except (OSError, RuntimeError):
      self._release()
      return None
    if frame is not None:
      frame_id = getattr(frame, "frame_id", None)
      if type(frame_id) is not int or frame_id < 0:
        self._release()
        return None
      if self._frame_id is not None and frame_id <= self._frame_id:
        # A restarted producer or duplicated delivery must reconnect, so the
        # old buffer and queued IPC data cannot be displayed as fresh.
        self._release()
        return None
      self._frame = frame
      self._frame_id = frame_id
      self._received_at = now
      if self._require_boot_eof:
        eof = getattr(self._client, "timestamp_eof", None)
        if type(eof) is not int or eof <= 0:
          self._release()
          return None
        self._capture_eof_ns = eof
    if self._received_at is None:
      # A new conflated subscriber has nothing queued until the next capture, so
      # an empty first recv is normal. Allow one staleness window for it to arrive.
      if self._connected_at is None or not 0 <= now - self._connected_at <= FRAME_STALE_SECONDS:
        self._release()
      return None
    # Connect and recv can cross a camera capture. Measure automatic BOOTTIME
    # only after receiving, so a newly captured frame is not misread as future.
    if self._require_boot_eof and now_boot_ns is None:
      now_boot_ns = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
      if now_boot_ns <= 0:
        self._release()
        return None
    if self._received_at is None or now < self._received_at or now - self._received_at > FRAME_STALE_SECONDS:
      self._release()
      return None
    if self._require_boot_eof and (self._capture_eof_ns is None or now_boot_ns is None or
                                   self._capture_eof_ns > now_boot_ns or
                                   now_boot_ns - self._capture_eof_ns > int(FRAME_STALE_SECONDS * 1e9)):
      self._release()
      return None
    return self._frame
