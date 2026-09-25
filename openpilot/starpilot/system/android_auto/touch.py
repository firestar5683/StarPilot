"""Car touchscreen input: decode Android Auto input events and map them onto the projected UI.

The head unit reports touches in its touchscreen coordinate space (advertised in
service discovery). They are mapped to the encoded video frame, then to the
visible content area inside the receiver's margins, and delivered as normalized
``(0..1, 0..1)`` single-pointer events. Only the first pointer is used: the
StarPilot UI is a single-touch interface.

Wire facts: mrmees/open-android-auto ``oaa/input`` (reference only), pinned at
61eab61c5f9968154ff1a80faa8c0a427b208479.
"""

from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass

from openpilot.starpilot.system.android_auto.wire import one, parse_fields

ACTION_PRESS = 0
ACTION_RELEASE = 1
ACTION_DRAG = 2
ACTION_POINTER_DOWN = 5
ACTION_POINTER_UP = 6
MAX_INPUT_BYTES = 16 * 1024
MAX_KEYCODES = 256
DEFAULT_TOUCH_SOCKET = "/tmp/starpilot-android-auto-touch.sock"


@dataclass(frozen=True)
class TouchEvent:
  kind: str   # "down", "move", "up", "cancel"
  x: float    # normalized within the visible content area
  y: float


@dataclass(frozen=True)
class InputConfig:
  keycodes: tuple[int, ...] = ()
  touch_width: int = 0
  touch_height: int = 0


def packed_varints(values) -> list[int]:
  """Protobuf repeated varints, packed or not."""
  result: list[int] = []
  for value in values:
    if isinstance(value, int):
      result.append(value)
      continue
    pos = 0
    while pos < len(value):
      number, shift = 0, 0
      while True:
        if pos >= len(value) or shift > 63:
          raise ValueError("Truncated packed varint")
        byte = value[pos]
        pos += 1
        number |= (byte & 127) << shift
        shift += 7
        if byte < 128:
          break
      result.append(number)
    if len(result) > MAX_KEYCODES:
      raise ValueError("Too many input keycodes")
  return result


def parse_input_config(data: bytes) -> InputConfig:
  fields = parse_fields(data)
  keycodes = tuple(packed_varints(fields.get(1, [])))[:MAX_KEYCODES]
  width = height = 0
  touch = one(fields, 2)
  if isinstance(touch, bytes):
    screen = parse_fields(touch)
    width, height = int(one(screen, 1, 0) or 0), int(one(screen, 2, 0) or 0)
  return InputConfig(keycodes, width, height)


class TouchMapper:
  """Stateful single-pointer decoder for one projection session."""

  def __init__(self, config: InputConfig, video_width: int, video_height: int, margin_width: int, margin_height: int):
    self.touch_width = config.touch_width or video_width
    self.touch_height = config.touch_height or video_height
    self.video_width, self.video_height = video_width, video_height
    self.left, self.top = margin_width // 2, margin_height // 2
    self.content_width, self.content_height = video_width - margin_width, video_height - margin_height
    self.pointer: int | None = None

  def _normalize(self, x: int, y: int) -> tuple[float, float]:
    vx = x * self.video_width / self.touch_width
    vy = y * self.video_height / self.touch_height
    nx = (vx - self.left) / self.content_width
    ny = (vy - self.top) / self.content_height
    return min(max(nx, 0.0), 1.0), min(max(ny, 0.0), 1.0)

  def _inside(self, x: int, y: int) -> bool:
    vx = x * self.video_width / self.touch_width
    vy = y * self.video_height / self.touch_height
    return self.left <= vx < self.left + self.content_width and self.top <= vy < self.top + self.content_height

  def reset(self) -> list[TouchEvent]:
    """Focus loss or session end: withdraw a held touch rather than clicking."""
    if self.pointer is None:
      return []
    self.pointer = None
    return [TouchEvent("cancel", 0.0, 0.0)]

  def decode(self, data: bytes) -> list[TouchEvent]:
    if len(data) > MAX_INPUT_BYTES:
      raise ValueError("Input message exceeds limit")
    touch = one(parse_fields(data), 3)
    if not isinstance(touch, bytes):
      return []  # buttons, rotary and touchpad are not used by the projected UI
    fields = parse_fields(touch)
    locations = []
    for raw in fields.get(1, [])[:10]:
      if isinstance(raw, bytes):
        loc = parse_fields(raw)
        locations.append((int(one(loc, 3, 0) or 0), int(one(loc, 1, 0) or 0), int(one(loc, 2, 0) or 0)))
    action = one(fields, 3, ACTION_DRAG)
    index = int(one(fields, 2, 0) or 0)
    if not locations:
      return []
    events: list[TouchEvent] = []
    if action == ACTION_PRESS and self.pointer is None:
      pointer, x, y = locations[0]
      if self._inside(x, y):
        self.pointer = pointer
        events.append(TouchEvent("down", *self._normalize(x, y)))
    elif self.pointer is not None:
      tracked = next(((x, y) for pointer, x, y in locations if pointer == self.pointer), None)
      lifted = action == ACTION_RELEASE or (action == ACTION_POINTER_UP and index < len(locations) and
                                            locations[index][0] == self.pointer)
      if tracked is None:
        events.extend(self.reset())
      elif lifted:
        self.pointer = None
        events.append(TouchEvent("up", *self._normalize(*tracked)))
      elif action in (ACTION_DRAG, ACTION_POINTER_DOWN, ACTION_POINTER_UP):
        events.append(TouchEvent("move", *self._normalize(*tracked)))
    return events


class TouchSender:
  """android_autod side: best-effort datagrams to the car-UI renderer."""

  def __init__(self, path: str = DEFAULT_TOUCH_SOCKET):
    self.path = path
    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    self.sock.setblocking(False)

  def send(self, events: list[TouchEvent]) -> None:
    for event in events:
      try:
        self.sock.sendto(json.dumps({"kind": event.kind, "x": event.x, "y": event.y}).encode(), self.path)
      except OSError:
        pass  # renderer not listening (mirror view or restarting): input is dropped, never queued

  def close(self) -> None:
    self.sock.close()


class TouchReceiver:
  """Renderer side: drain queued touches without blocking the render loop."""

  def __init__(self, path: str = DEFAULT_TOUCH_SOCKET):
    self.path = path
    try:
      os.unlink(path)
    except FileNotFoundError:
      pass
    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    self.sock.bind(path)
    os.chmod(path, 0o600)
    self.sock.setblocking(False)

  def drain(self, limit: int = 64) -> list[TouchEvent]:
    events = []
    while len(events) < limit:
      try:
        data = self.sock.recv(512)
      except BlockingIOError:
        break
      try:
        raw = json.loads(data)
        kind, x, y = str(raw["kind"]), float(raw["x"]), float(raw["y"])
      except (ValueError, KeyError, TypeError):
        continue
      if kind in ("down", "move", "up", "cancel") and 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
        events.append(TouchEvent(kind, x, y))
    return events

  def close(self) -> None:
    self.sock.close()
    try:
      os.unlink(self.path)
    except FileNotFoundError:
      pass
