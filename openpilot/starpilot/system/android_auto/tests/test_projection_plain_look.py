"""The car screen's camera look follows the shader's current uniforms (color_strength and road_camera)."""
from types import SimpleNamespace
from unittest.mock import Mock

from openpilot.starpilot.system.android_auto.projection_onroad import apply_plain_camera_look


def test_car_screen_uses_the_plain_non_road_path_with_the_current_shader_uniforms():
  rl = SimpleNamespace(set_shader_value=Mock(), ShaderUniformDataType=SimpleNamespace(SHADER_UNIFORM_FLOAT='float', SHADER_UNIFORM_INT='int'))
  camera = SimpleNamespace(shader='shader', _color_strength_val=[0.2], _color_strength_loc=3, _road_camera_val=[1], _road_camera_loc=4)
  apply_plain_camera_look(camera, rl)
  assert camera._color_strength_val == [1.0] and camera._road_camera_val == [0]
  assert [call.args for call in rl.set_shader_value.call_args_list] == [
    ('shader', 3, [1.0], 'float'), ('shader', 4, [0], 'int')]


def test_it_needs_none_of_the_removed_engaged_uniform():
  rl = SimpleNamespace(set_shader_value=Mock(), ShaderUniformDataType=SimpleNamespace(SHADER_UNIFORM_FLOAT='float', SHADER_UNIFORM_INT='int'))
  camera = SimpleNamespace(shader='shader', _color_strength_val=[0.0], _color_strength_loc=3, _road_camera_val=[1], _road_camera_loc=4)
  assert not hasattr(camera, '_engaged_val')
  apply_plain_camera_look(camera, rl)
