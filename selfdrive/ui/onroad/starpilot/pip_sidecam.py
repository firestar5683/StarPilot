from __future__ import annotations

import json
import platform
import time
import weakref

import pyray as rl

from msgq.visionipc import VisionIpcClient, VisionStreamType
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.starpilot.common.vision_bsm import get_fresh_vasm_state

PIP_SHADER_VERSION = """
#version 300 es
precision mediump float;
"""
if platform.system() == "Darwin":
  PIP_SHADER_VERSION = """
    #version 330 core
  """

PIP_VERTEX_SHADER = PIP_SHADER_VERSION + """
in vec3 vertexPosition;
in vec2 vertexTexCoord;
in vec3 vertexNormal;
in vec4 vertexColor;
uniform mat4 mvp;
out vec2 fragTexCoord;
out vec4 fragColor;
void main() {
  fragTexCoord = vertexTexCoord;
  fragColor = vertexColor;
  gl_Position = mvp * vec4(vertexPosition, 1.0);
}
"""

PIP_FRAGMENT_SHADER = PIP_SHADER_VERSION + """
in vec2 fragTexCoord;
uniform sampler2D texture0;
uniform sampler2D texture1;
uniform vec2 uCropMin;
uniform vec2 uCropSize;
out vec4 fragColor;
void main() {
  vec2 uv = uCropMin + fragTexCoord * uCropSize;
  float y = texture(texture0, uv).r;
  vec2 c = texture(texture1, uv).ra - 0.5;
  vec3 rgb = vec3(y + 1.402 * c.y, y - 0.344 * c.x - 0.714 * c.y, y + 1.772 * c.x);

  vec2 p = fragTexCoord - 0.5;
  float dist = length(p);
  float edge = 0.02;
  float alpha = 1.0 - smoothstep(0.5 - edge, 0.5, dist);

  fragColor = vec4(rgb, alpha);
}
"""

UNIFORM_VEC2 = rl.ShaderUniformDataType.SHADER_UNIFORM_VEC2

CONNECTION_RETRY_INTERVAL = 0.2
PARAM_REFRESH_INTERVAL = 2.0

# Bubble geometry
BUBBLE_RADIUS_FRACTION = 0.3
BUBBLE_RADIUS_MIN = 180
BUBBLE_RADIUS_MAX = 420
BUBBLE_MARGIN = 24


class PipSideCamera:
  """Renders a circular pip bubble of the adjacent side window from the dcamera."""
  def __init__(self):
    self._params = ui_state.params
    self._params_memory = ui_state.params_memory

    self.client = VisionIpcClient("camerad", VisionStreamType.VISION_STREAM_DRIVER, conflate=True)
    self._stream_type = VisionStreamType.VISION_STREAM_DRIVER
    self._last_connection_attempt = 0.0
    self.frame = None
    self._last_frame_id = -1
    self._texture_needs_update = True
    self.texture_y: rl.Texture | None = None
    self.texture_uv: rl.Texture | None = None
    self._closed = False

    self._enabled = False
    self._show_on_blinker = False
    self._show_on_bsm = False
    self._mask = {}
    self._last_param_refresh = 0.0

    self.shader = rl.load_shader_from_memory(PIP_VERTEX_SHADER, PIP_FRAGMENT_SHADER)
    self._texture1_loc = rl.get_shader_location(self.shader, "texture1")
    self._crop_min_loc = rl.get_shader_location(self.shader, "uCropMin")
    self._crop_size_loc = rl.get_shader_location(self.shader, "uCropSize")

    self_ref = weakref.ref(self)

    def offroad_transition_callback():
      if (ref := self_ref()) is not None:
        ref._offroad_transition()

    self._offroad_transition_callback = offroad_transition_callback
    ui_state.add_offroad_transition_callback(self._offroad_transition_callback)

  def _offroad_transition(self):
    self._clear_textures()
    self.frame = None
    self._last_frame_id = -1
    self._last_connection_attempt = 0.0
    self.client = VisionIpcClient("camerad", self._stream_type, conflate=True)

  def close(self):
    if self._closed:
      return
    self._closed = True
    if getattr(self, "_offroad_transition_callback", None) is not None:
      ui_state.remove_offroad_transition_callback(self._offroad_transition_callback)
      self._offroad_transition_callback = None
    self._clear_textures()
    if self.shader and self.shader.id:
      rl.unload_shader(self.shader)
      self.shader.id = 0
    self.frame = None
    self.client = None

  def __del__(self):
    self.close()

  def _refresh_config(self, force: bool = False):
    now = time.monotonic()
    if not force and now - self._last_param_refresh < PARAM_REFRESH_INTERVAL:
      return
    self._last_param_refresh = now
    self._enabled = self._params.get_bool("PIPPreviewEnabled")
    self._show_on_blinker = self._params.get_bool("PIPPreviewShowOnBlinker")
    self._show_on_bsm = self._params.get_bool("PIPPreviewShowOnBSM")
    try:
      raw = self._params.get("PIPPreviewMask")
      if isinstance(raw, (bytes, str)):
        raw = json.loads(raw)
      self._mask = raw if isinstance(raw, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
      self._mask = {}

  def active_sides(self) -> list[str]:
    """Return the car-side keys ('left'/'right') whose preview bubble should show."""
    if not ui_state.started:
      return []
    self._refresh_config()
    if not self._enabled or not self._mask:
      return []

    car_state = ui_state.sm["carState"] if ui_state.sm.valid.get("carState", False) else None
    if car_state is None:
      return []

    vasm_left, vasm_right = get_fresh_vasm_state(self._params_memory)

    left_blinker = bool(car_state.leftBlinker)
    right_blinker = bool(car_state.rightBlinker)
    left_bsm = bool(car_state.leftBlindspot) or vasm_left
    right_bsm = bool(car_state.rightBlindspot) or vasm_right

    sides = []
    if self._mask.get("center_left") and ((self._show_on_blinker and left_blinker) or (self._show_on_bsm and left_bsm)):
      sides.append("left")
    if self._mask.get("center_right") and ((self._show_on_blinker and right_blinker) or (self._show_on_bsm and right_bsm)):
      sides.append("right")
    return sides

  def _crop_rect(self, side: str) -> rl.Rectangle | None:
    center = self._mask.get(f"center_{side}")
    size = self._mask.get("crop_size")
    if not center or len(center) < 2 or not size:
      return None
    try:
      cx, cy = float(center[0]), float(center[1])
      half = float(size) / 2.0
    except (TypeError, ValueError):
      return None
    if half <= 0:
      return None
    return rl.Rectangle(cx - half, cy - half, size, size)

  def _bubble_rect(self, content_rect: rl.Rectangle, side: str) -> rl.Rectangle:
    radius = int(min(content_rect.width, content_rect.height) * BUBBLE_RADIUS_FRACTION)
    radius = max(BUBBLE_RADIUS_MIN, min(radius, BUBBLE_RADIUS_MAX))
    margin = BUBBLE_MARGIN
    cx = content_rect.x + margin + radius if side == "left" else content_rect.x + content_rect.width - margin - radius
    cy = content_rect.y + content_rect.height - margin - radius
    return rl.Rectangle(cx - radius, cy - radius, radius * 2, radius * 2)

  def render(self, content_rect: rl.Rectangle):
    if not ui_state.started:
      return

    sides = self.active_sides()
    if not sides:
      return

    if not self._ensure_connection():
      return

    buffer = self.client.recv(timeout_ms=0)
    if buffer:
      self.frame = buffer
      self._last_frame_id = int(getattr(buffer, "frame_id", -1))
      self._texture_needs_update = True
    if self.frame is None:
      return

    if not self.texture_y or not self.texture_uv:
      return

    if self._texture_needs_update:
      y_data = self.frame.data[: self.frame.uv_offset]
      uv_data = self.frame.data[self.frame.uv_offset:]
      rl.update_texture(self.texture_y, rl.ffi.cast("void *", rl.ffi.from_buffer(y_data)))
      rl.update_texture(self.texture_uv, rl.ffi.cast("void *", rl.ffi.from_buffer(uv_data)))
      self._texture_needs_update = False

    for side in sides:
      crop = self._crop_rect(side)
      if crop is None:
        continue
      bubble = self._bubble_rect(content_rect, side)
      self._draw_bubble(bubble, crop)

  def _draw_bubble(self, bubble: rl.Rectangle, crop: rl.Rectangle):
    cx = bubble.x + bubble.width / 2
    cy = bubble.y + bubble.height / 2
    radius = bubble.width / 2

    rl.draw_circle(int(round(cx)), int(round(cy)), radius, rl.BLACK)
    rl.draw_circle_lines(int(round(cx)), int(round(cy)), radius, rl.Color(255, 255, 255, 120))

    tex_w = float(self.texture_y.width)
    tex_h = float(self.texture_y.height)
    crop_min = rl.Vector2(crop.x / tex_w, crop.y / tex_h)
    crop_size = rl.Vector2(crop.width / tex_w, crop.height / tex_h)

    src_rect = rl.Rectangle(0, 0, tex_w, tex_h)
    dst_rect = rl.Rectangle(bubble.x, bubble.y, bubble.width, bubble.height)

    rl.begin_shader_mode(self.shader)
    rl.set_shader_value(self.shader, self._crop_min_loc, crop_min, UNIFORM_VEC2)
    rl.set_shader_value(self.shader, self._crop_size_loc, crop_size, UNIFORM_VEC2)
    rl.set_shader_value_texture(self.shader, self._texture1_loc, self.texture_uv)
    rl.draw_texture_pro(self.texture_y, src_rect, dst_rect, rl.Vector2(0, 0), 0.0, rl.WHITE)
    rl.end_shader_mode()

  def _ensure_connection(self) -> bool:
    if not self.client.is_connected():
      self.frame = None
      self._last_frame_id = -1

      now = rl.get_time()
      if now - self._last_connection_attempt < CONNECTION_RETRY_INTERVAL:
        return False
      self._last_connection_attempt = now

      self._clear_textures()
      if not self.client.connect(False) or not self.client.num_buffers:
        return False
      self._initialize_textures()
    return True

  def _initialize_textures(self):
    self._clear_textures()
    self.texture_y = rl.load_texture_from_image(rl.Image(None, int(self.client.stride),
      int(self.client.height), 1, rl.PixelFormat.PIXELFORMAT_UNCOMPRESSED_GRAYSCALE))
    self.texture_uv = rl.load_texture_from_image(rl.Image(None, int(self.client.stride // 2),
      int(self.client.height // 2), 1, rl.PixelFormat.PIXELFORMAT_UNCOMPRESSED_GRAY_ALPHA))

  def _clear_textures(self):
    if self.texture_y and self.texture_y.id:
      rl.unload_texture(self.texture_y)
      self.texture_y = None
    if self.texture_uv and self.texture_uv.id:
      rl.unload_texture(self.texture_uv)
      self.texture_uv = None