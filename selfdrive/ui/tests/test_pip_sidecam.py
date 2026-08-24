from openpilot.selfdrive.ui.onroad.starpilot.pip_sidecam import (
  IMAGE_TO_VEHICLE_SIDE,
  PIP_FRAGMENT_SHADER,
  PIP_CURVED_FRAGMENT_SHADER,
  PipSideCamera,
)


def test_pip_maps_raw_driver_image_sides_to_vehicle_sides():
  assert IMAGE_TO_VEHICLE_SIDE == {"left": "right", "right": "left"}

  camera = PipSideCamera.__new__(PipSideCamera)
  camera._closed = True
  camera._mask = {
    "center_left": [100, 200],
    "center_right": [900, 200],
    "crop_size": 100,
  }

  left_vehicle_crop = camera._crop_rect("left")
  right_vehicle_crop = camera._crop_rect("right")

  assert (left_vehicle_crop.x, left_vehicle_crop.y) == (850, 150)
  assert (right_vehicle_crop.x, right_vehicle_crop.y) == (50, 150)


def test_pip_driver_camera_shader_mirrors_the_crop():
  assert "uniform int uFlipX" in PIP_FRAGMENT_SHADER
  assert "cropCoord.x = 1.0 - cropCoord.x" in PIP_FRAGMENT_SHADER


class _FakeParams:
  def __init__(self, invert: bool = False):
    self._invert = invert

  def get_bool(self, key: str) -> bool:
    if key == "PIPPreviewInvert":
      return self._invert
    if key == "GalaxyDeveloperMode":
      return True
    return False

  def get(self, key: str):
    return None


def test_pip_flip_value_follows_invert_param():
  camera = PipSideCamera.__new__(PipSideCamera)
  camera._closed = True
  camera._last_param_refresh = 0.0
  camera._flip_x_value = __import__("pyray").ffi.new("int[1]", [1])
  camera._params = _FakeParams(invert=False)
  camera._mask = {}
  camera._refresh_config(force=True)
  assert camera._flip_x_value[0] == 0

  camera._params = _FakeParams(invert=True)
  camera._refresh_config(force=True)
  assert camera._flip_x_value[0] == 1


def test_pip_driver_camera_shader_masks_before_sampling_and_keeps_two_texture_reads():
  assert "fwidth(radius)" in PIP_FRAGMENT_SHADER
  assert "if (radius > 1.0 + aa)" in PIP_FRAGMENT_SHADER
  assert PIP_FRAGMENT_SHADER.index("if (radius > 1.0 + aa)") < PIP_FRAGMENT_SHADER.index("texture(texture0")
  assert PIP_FRAGMENT_SHADER.count("texture(texture0") == 1
  assert PIP_FRAGMENT_SHADER.count("texture(texture1") == 1


def test_pip_driver_camera_shader_uses_analytic_bubble_shading_without_new_uniforms():
  assert "float z = sqrt(max(0.0, 1.0 - dot(p, p)))" in PIP_FRAGMENT_SHADER
  assert "BUBBLE_REFRACTION" in PIP_FRAGMENT_SHADER
  assert "BUBBLE_EDGE_DARKEN" in PIP_FRAGMENT_SHADER
  assert "BUBBLE_HIGHLIGHT" in PIP_FRAGMENT_SHADER
  assert "BUBBLE_RIM" in PIP_FRAGMENT_SHADER
  assert "BUBBLE_EDGE_TRANSPARENCY" in PIP_FRAGMENT_SHADER
  assert "BUBBLE_BORDER_WIDTH" not in PIP_FRAGMENT_SHADER
  assert "rgb = mix(rgb, vec3(1.0)" not in PIP_FRAGMENT_SHADER
  assert "uniform sampler2D texture2" not in PIP_FRAGMENT_SHADER
  assert "uRefraction" not in PIP_FRAGMENT_SHADER


def test_pip_c4_curved_shader_masks_a_rounded_rectangle_before_sampling():
  assert "uRectSize" in PIP_CURVED_FRAGMENT_SHADER
  assert "CORNER_RADIUS_FRACTION" in PIP_CURVED_FRAGMENT_SHADER
  assert "CURVE_AMOUNT" in PIP_CURVED_FRAGMENT_SHADER
  assert "length(max(q, 0.0))" in PIP_CURVED_FRAGMENT_SHADER
  assert PIP_CURVED_FRAGMENT_SHADER.index("if (dist > aa)") < PIP_CURVED_FRAGMENT_SHADER.index("texture(texture0")
  assert PIP_CURVED_FRAGMENT_SHADER.count("texture(texture0") == 1
  assert PIP_CURVED_FRAGMENT_SHADER.count("texture(texture1") == 1
  assert "cropCoord.x = 1.0 - cropCoord.x" in PIP_CURVED_FRAGMENT_SHADER
  assert "y + 1.402 * c.y" in PIP_CURVED_FRAGMENT_SHADER
  assert "uRefraction" not in PIP_CURVED_FRAGMENT_SHADER


def test_pip_sidecam_is_a_widget_with_curved_and_bubble_shapes():
  bubble = PipSideCamera.__new__(PipSideCamera)
  bubble._closed = True
  assert isinstance(bubble, PipSideCamera)
  assert hasattr(bubble, "render")
  assert hasattr(bubble, "_draw_bubble")
  assert hasattr(bubble, "_draw_curved")
  curved = PipSideCamera.__new__(PipSideCamera)
  curved._closed = True
  curved._shape = "curved"
  assert curved._shape == "curved"


def test_pip_sidecam_rejects_unknown_shapes():
  camera = object.__new__(PipSideCamera)
  try:
    PipSideCamera.__init__(camera, shape="hexagon")
  except ValueError:
    pass
  else:
    raise AssertionError("expected ValueError for unknown shape")
