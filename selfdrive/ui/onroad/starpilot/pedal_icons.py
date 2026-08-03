import pyray as rl
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.text_measure import measure_text_cached

_RADIUS = 36
_FONT_SIZE = 36

def render_pedal_icons(start_x: float, start_y: float, font):
  params = ui_state.ui_params
  if not params.get_bool("PedalsOnUI"):
    return

  car_state = ui_state.sm["carState"] if ui_state.sm.valid.get("carState", False) else None
  if not car_state:
    return

  standstill = getattr(car_state, "standstill", False)
  brake_lights = getattr(car_state, "brakeLights", False)
  acceleration_ego = getattr(car_state, "aEgo", 0.0)

  dynamic_pedals = params.get_bool("DynamicPedalsOnUI")
  static_pedals = params.get_bool("StaticPedalsOnUI")

  brake_opacity = 1.0
  gas_opacity = 1.0

  if dynamic_pedals:
    brake_opacity = 1.0 if standstill else min(1.0, max(0.25, abs(acceleration_ego))) if acceleration_ego < -0.25 else 0.25
    gas_opacity = min(1.0, max(0.25, acceleration_ego)) if acceleration_ego > 0.0 else 0.25
  elif static_pedals:
    brake_opacity = 1.0 if (standstill or brake_lights or acceleration_ego < -0.25) else 0.25
    gas_opacity = 1.0 if acceleration_ego > 0.25 else 0.25

  cx = start_x + 48
  cy = start_y + 48

  rl.draw_circle(int(cx), int(cy), _RADIUS, rl.Color(201, 34, 49, int(255 * brake_opacity)))
  rl.draw_circle_lines(int(cx), int(cy), _RADIUS, rl.Color(255, 255, 255, int(255 * brake_opacity)))

  sz = measure_text_cached(font, "B", _FONT_SIZE)
  rl.draw_text_ex(font, "B", rl.Vector2(int(cx - sz.x / 2), int(cy - sz.y / 2)), _FONT_SIZE, 0, rl.Color(255, 255, 255, int(255 * brake_opacity)))

  gx = cx + 96

  rl.draw_circle(int(gx), int(cy), _RADIUS, rl.Color(22, 127, 64, int(255 * gas_opacity)))
  rl.draw_circle_lines(int(gx), int(cy), _RADIUS, rl.Color(255, 255, 255, int(255 * gas_opacity)))

  sz = measure_text_cached(font, "G", _FONT_SIZE)
  rl.draw_text_ex(font, "G", rl.Vector2(int(gx - sz.x / 2), int(cy - sz.y / 2)), _FONT_SIZE, 0, rl.Color(255, 255, 255, int(255 * gas_opacity)))
