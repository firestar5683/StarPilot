from __future__ import annotations

import json
import platform
import time
import weakref

import pyray as rl

from msgq.visionipc import VisionIpcClient, VisionStreamType
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.starpilot.common.vision_bsm import get_fresh_vasm_state
from openpilot.system.ui.widgets import Widget

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
uniform int uFlipX;
out vec4 fragColor;

const float BUBBLE_REFRACTION = 0.016;
const float BUBBLE_EDGE_DARKEN = 0.15;
const float BUBBLE_HIGHLIGHT = 0.12;
const float BUBBLE_RIM = 0.10;
const float BUBBLE_EDGE_TRANSPARENCY = 0.12;

void main() {
  // Calculate the mask before sampling: fragments outside the bubble do no texture work.
  vec2 p = fragTexCoord * 2.0 - 1.0;
  float radius = length(p);
  float aa = max(fwidth(radius), 0.00001);
  float alpha = 1.0 - smoothstep(1.0 - aa, 1.0 + aa, radius);
  if (radius > 1.0 + aa) {
    discard;
  }

  // A shallow hemisphere gives the image a convex bubble surface without a mesh or pass.
  float z = sqrt(max(0.0, 1.0 - dot(p, p)));
  vec2 sampleCoord = clamp(
    fragTexCoord + p * BUBBLE_REFRACTION * (1.0 - z),
    0.001,
    0.999
  );

  vec2 cropCoord = sampleCoord;
  if (uFlipX == 1) {
    cropCoord.x = 1.0 - cropCoord.x;
  }
  vec2 uv = uCropMin + cropCoord * uCropSize;
  float y = texture(texture0, uv).r;
  vec2 c = texture(texture1, uv).ra - 0.5;
  vec3 rgb = vec3(y + 1.402 * c.y, y - 0.344 * c.x - 0.714 * c.y, y + 1.772 * c.x);

  // Keep the interior gradient and use cheap analytic lighting instead of specular math.
  float edgeShade = smoothstep(0.22, 0.98, radius);
  rgb *= mix(1.0, 1.0 - BUBBLE_EDGE_DARKEN, edgeShade);

  vec2 highlightOffset = p - vec2(-0.28, -0.34);
  float highlight = 1.0 - smoothstep(0.0, 0.22, dot(highlightOffset, highlightOffset));
  rgb += vec3(1.0) * highlight * z * BUBBLE_HIGHLIGHT;

  // Let the rim blend into the camera image and the UI underneath it.
  float rim = smoothstep(0.60, 0.99, radius);
  rgb = mix(rgb, vec3(0.48, 0.70, 1.0), rim * BUBBLE_RIM);
  float surfaceAlpha = alpha * (1.0 - rim * BUBBLE_EDGE_TRANSPARENCY);
  fragColor = vec4(rgb, surfaceAlpha);
}
"""

# curved-rectangle variant for the mici display.
PIP_CURVED_FRAGMENT_SHADER = PIP_SHADER_VERSION + """
in vec2 fragTexCoord;
uniform sampler2D texture0;
uniform sampler2D texture1;
uniform vec2 uCropMin;
uniform vec2 uCropSize;
uniform int uFlipX;
uniform vec2 uRectSize;
out vec4 fragColor;

const float CORNER_RADIUS_FRACTION = 0.22;
const float CURVE_AMOUNT = 0.07;
const float EDGE_DARKEN = 0.14;
const float RIM_BLEND = 0.06;

void main() {
  vec2 p = fragTexCoord * 2.0 - 1.0;
  float halfW = uRectSize.x * 0.5;
  float halfH = uRectSize.y * 0.5;
  float radius = CORNER_RADIUS_FRACTION * min(uRectSize.x, uRectSize.y);

  // Rounded-rectangle SDF in pixel space; mask before sampling.
  vec2 q = abs(vec2(p.x * halfW, p.y * halfH)) - (vec2(halfW, halfH) - radius);
  float dist = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;
  float aa = max(fwidth(dist), 0.00001);
  float alpha = 1.0 - smoothstep(-aa, aa, dist);
  if (dist > aa) {
    discard;
  }

  // Gentle convex curvature along both axes to mimic the curved OLED panel.
  float curve = CURVE_AMOUNT * (1.0 - p.x * p.x) * (1.0 - p.y * p.y);
  vec2 sampleCoord = clamp(fragTexCoord + curve * vec2(0.0, 0.5), 0.001, 0.999);

  // The saved mask is a square crop, but the curved panel is wider than tall.
  // Sample an aspect-matched horizontal band of that square (centered) instead
  // of stretching it, so the image is never distorted. The circle's diameter
  // (the square crop) becomes the panel's length; the height follows the aspect.
  float aspect = uRectSize.x / max(uRectSize.y, 0.0001);
  vec2 cropCoord = sampleCoord;
  if (aspect >= 1.0) {
    cropCoord.y = 0.5 + (sampleCoord.y - 0.5) / aspect;
  } else {
    cropCoord.x = 0.5 + (sampleCoord.x - 0.5) * aspect;
  }
  if (uFlipX == 1) {
    cropCoord.x = 1.0 - cropCoord.x;
  }
  vec2 uv = uCropMin + cropCoord * uCropSize;
  float y = texture(texture0, uv).r;
  vec2 c = texture(texture1, uv).ra - 0.5;
  vec3 rgb = vec3(y + 1.402 * c.y, y - 0.344 * c.x - 0.714 * c.y, y + 1.772 * c.x);

  // Let the rim blend into the camera image and the UI underneath it.
  float edgeShade = smoothstep(-radius, 0.0, dist);
  rgb *= mix(1.0, 1.0 - EDGE_DARKEN, edgeShade);
  float rim = smoothstep(radius * 0.55, radius, radius - dist);
  rgb = mix(rgb, vec3(0.48, 0.70, 1.0), rim * RIM_BLEND);

  fragColor = vec4(rgb, alpha);
}
"""

UNIFORM_VEC2 = rl.ShaderUniformDataType.SHADER_UNIFORM_VEC2
UNIFORM_INT = rl.ShaderUniformDataType.SHADER_UNIFORM_INT

IMAGE_TO_VEHICLE_SIDE = {
  "left": "right",
  "right": "left",
}

CONNECTION_RETRY_INTERVAL = 0.2
PARAM_REFRESH_INTERVAL = 2.0

# Bubble geometry
BUBBLE_RADIUS_FRACTION = 0.3
BUBBLE_RADIUS_MIN = 180
BUBBLE_RADIUS_MAX = 420
BUBBLE_MARGIN = 24

class PipSideCamera(Widget):
  """Overlays the adjacent side window from the dcamera.

  Drawn as a circular bubble on the big screen (shape="bubble") or as a
  curved rectangle filling the whole road preview on the C4 (shape="curved").
  """
  def __init__(self, shape: str = "bubble"):
    super().__init__()
    if shape not in ("bubble", "curved"):
      raise ValueError(f"Unknown PipSideCamera shape: {shape!r}")
    self._shape = shape

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
    self._side_activation_time: dict[str, float] = {}
    self._active_sides: set[str] = set()

    self.shader = rl.load_shader_from_memory(PIP_VERTEX_SHADER, PIP_FRAGMENT_SHADER)
    self._texture1_loc = rl.get_shader_location(self.shader, "texture1")
    self._crop_min_loc = rl.get_shader_location(self.shader, "uCropMin")
    self._crop_size_loc = rl.get_shader_location(self.shader, "uCropSize")
    self._flip_x_loc = rl.get_shader_location(self.shader, "uFlipX")
    self._flip_x_value = rl.ffi.new("int[1]", [1])

    self.curved_shader = rl.load_shader_from_memory(PIP_VERTEX_SHADER, PIP_CURVED_FRAGMENT_SHADER)
    self._curved_texture1_loc = rl.get_shader_location(self.curved_shader, "texture1")
    self._curved_crop_min_loc = rl.get_shader_location(self.curved_shader, "uCropMin")
    self._curved_crop_size_loc = rl.get_shader_location(self.curved_shader, "uCropSize")
    self._curved_flip_x_loc = rl.get_shader_location(self.curved_shader, "uFlipX")
    self._curved_rect_size_loc = rl.get_shader_location(self.curved_shader, "uRectSize")

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
    if getattr(self, "_closed", False):
      return
    self._closed = True
    if getattr(self, "_offroad_transition_callback", None) is not None:
      ui_state.remove_offroad_transition_callback(self._offroad_transition_callback)
      self._offroad_transition_callback = None
    self._clear_textures()
    if (shader := getattr(self, "shader", None)) is not None and shader.id:
      rl.unload_shader(shader)
      shader.id = 0
    if (curved := getattr(self, "curved_shader", None)) is not None and curved.id:
      rl.unload_shader(curved)
      curved.id = 0
    self.frame = None
    self.client = None

  def __del__(self):
    self.close()

  def _refresh_config(self, force: bool = False):
    now = time.monotonic()
    if not force and now - self._last_param_refresh < PARAM_REFRESH_INTERVAL:
      return
    self._last_param_refresh = now
    self._enabled = self._params.get_bool("PIPPreviewEnabled") and self._params.get_bool("GalaxyDeveloperMode")
    self._show_on_blinker = self._params.get_bool("PIPPreviewShowOnBlinker")
    self._show_on_bsm = self._params.get_bool("PIPPreviewShowOnBSM")
    self._flip_x_value[0] = 1 if self._params.get_bool("PIPPreviewInvert") else 0
    try:
      raw = self._params.get("PIPPreviewMask")
      if isinstance(raw, (bytes, str)):
        raw = json.loads(raw)
      self._mask = raw if isinstance(raw, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
      self._mask = {}

  def active_sides(self) -> list[str]:
    """Return vehicle-side keys whose preview bubble should show.

    The driver camera is not mirrored in the Galaxy snapshot. Its image-left
    side is the vehicle's right side, so translate the image-relative mask
    keys before applying vehicle signals and blind-spot state.
    """
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
    for image_side, vehicle_side, blinker, blindspot in (
      ("left", IMAGE_TO_VEHICLE_SIDE["left"], right_blinker, right_bsm),
      ("right", IMAGE_TO_VEHICLE_SIDE["right"], left_blinker, left_bsm),
    ):
      if self._mask.get(f"center_{image_side}") and (
        (self._show_on_blinker and blinker) or (self._show_on_bsm and blindspot)
      ):
        sides.append(vehicle_side)
    return sides

  def _crop_rect(self, vehicle_side: str) -> rl.Rectangle | None:
    image_side = IMAGE_TO_VEHICLE_SIDE[vehicle_side]
    center = self._mask.get(f"center_{image_side}")
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

  def _acquire_frame(self) -> bool:
    """Ensure connection and refresh the Y/UV textures from the latest driver frame."""
    if not self._ensure_connection():
      return False

    buffer = self.client.recv(timeout_ms=0)
    if buffer:
      self.frame = buffer
      self._last_frame_id = int(getattr(buffer, "frame_id", -1))
      self._texture_needs_update = True
    if self.frame is None:
      return False

    if not self.texture_y or not self.texture_uv:
      return False

    if self._texture_needs_update:
      y_data = self.frame.data[: self.frame.uv_offset]
      uv_data = self.frame.data[self.frame.uv_offset:]
      rl.update_texture(self.texture_y, rl.ffi.cast("void *", rl.ffi.from_buffer(y_data)))
      rl.update_texture(self.texture_uv, rl.ffi.cast("void *", rl.ffi.from_buffer(uv_data)))
      self._texture_needs_update = False
    return True

  def _render(self, content_rect: rl.Rectangle):
    """Fetch the current driver frame, then draw it for the configured shape."""
    if not ui_state.started:
      return None

    sides = self.active_sides()
    if not sides or not self._acquire_frame():
      return None

    if self._shape == "curved":
      # C4: one crop fills the whole road preview as a curved rectangle.
      side = self._pick_side(sides)
      if side is not None:
        crop = self._crop_rect(side)
        if crop is not None:
          self._draw_curved(content_rect, crop)
    else:
      # Raybig: one circular bubble per active side.
      for side in sides:
        crop = self._crop_rect(side)
        if crop is None:
          continue
        bubble = self._bubble_rect(content_rect, side)
        self._draw_bubble(bubble, crop)
    return None

  def _pick_side(self, sides: list[str]) -> str | None:
    """Return the active side whose blinker/BSM most recently turned on.

    Only a rising edge (inactive -> active) refreshes the timestamp
    """
    now = time.monotonic()
    active = set(sides)
    for side in active - self._active_sides:
      self._side_activation_time[side] = now
    self._active_sides = active
    if not sides:
      return None
    return max(sides, key=lambda side: self._side_activation_time.get(side, 0.0))

  def _draw_bubble(self, bubble: rl.Rectangle, crop: rl.Rectangle):
    tex_w = float(self.texture_y.width)
    tex_h = float(self.texture_y.height)
    crop_min = rl.Vector2(crop.x / tex_w, crop.y / tex_h)
    crop_size = rl.Vector2(crop.width / tex_w, crop.height / tex_h)

    src_rect = rl.Rectangle(0, 0, tex_w, tex_h)
    dst_rect = rl.Rectangle(bubble.x, bubble.y, bubble.width, bubble.height)

    rl.begin_shader_mode(self.shader)
    rl.set_shader_value(self.shader, self._crop_min_loc, crop_min, UNIFORM_VEC2)
    rl.set_shader_value(self.shader, self._crop_size_loc, crop_size, UNIFORM_VEC2)
    rl.set_shader_value(self.shader, self._flip_x_loc, self._flip_x_value, UNIFORM_INT)
    rl.set_shader_value_texture(self.shader, self._texture1_loc, self.texture_uv)
    rl.draw_texture_pro(self.texture_y, src_rect, dst_rect, rl.Vector2(0, 0), 0.0, rl.WHITE)
    rl.end_shader_mode()

  def _draw_curved(self, content_rect: rl.Rectangle, crop: rl.Rectangle):
    tex_w = float(self.texture_y.width)
    tex_h = float(self.texture_y.height)
    crop_min = rl.Vector2(crop.x / tex_w, crop.y / tex_h)
    crop_size = rl.Vector2(crop.width / tex_w, crop.height / tex_h)
    rect_size = rl.Vector2(content_rect.width, content_rect.height)

    src_rect = rl.Rectangle(0, 0, tex_w, tex_h)
    dst_rect = rl.Rectangle(content_rect.x, content_rect.y, content_rect.width, content_rect.height)

    rl.begin_shader_mode(self.curved_shader)
    rl.set_shader_value(self.curved_shader, self._curved_crop_min_loc, crop_min, UNIFORM_VEC2)
    rl.set_shader_value(self.curved_shader, self._curved_crop_size_loc, crop_size, UNIFORM_VEC2)
    rl.set_shader_value(self.curved_shader, self._curved_flip_x_loc, self._flip_x_value, UNIFORM_INT)
    rl.set_shader_value(self.curved_shader, self._curved_rect_size_loc, rect_size, UNIFORM_VEC2)
    rl.set_shader_value_texture(self.curved_shader, self._curved_texture1_loc, self.texture_uv)
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
    if (texture_y := getattr(self, "texture_y", None)) is not None and texture_y.id:
      rl.unload_texture(texture_y)
      self.texture_y = None
    if (texture_uv := getattr(self, "texture_uv", None)) is not None and texture_uv.id:
      rl.unload_texture(texture_uv)
      self.texture_uv = None
