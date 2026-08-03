from __future__ import annotations
import math
from dataclasses import dataclass
from collections.abc import Callable
from enum import Enum
import pyray as rl
from openpilot.selfdrive.ui import UI_BORDER_SIZE
from openpilot.starpilot.common.vision_bsm import get_fresh_vasm_state

from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.lib.starpilot_status import (
  CEM_OVERRIDE_COLOR, ENGAGED_COLOR, EXPERIMENTAL_COLOR, TRAFFIC_COLOR
)



class BorderLayer(Enum):
  BEHIND = 0
  OVERLAY = 1


@dataclass
class BorderEffect:
  render_fn: Callable[[rl.Rectangle, float], None]
  layer: BorderLayer
  name: str = ""


_GLOW_MAX_ALPHA = 200
_GLOW_BASE_INTENSITY = 0.70
_GLOW_SPAN = 2.5
_BREATHING_PERIOD = 4.5
_GLOW_FADE_IN_DURATION = 0.6

_CURVATURE_MIN = 0.0005
_CURVATURE_MAX = 0.02

_GREEN = rl.Color(34, 197, 94, 255)
_AMBER = rl.Color(251, 191, 36, 255)
_ORANGE = rl.Color(234, 88, 12, 255)
_RED = rl.Color(201, 34, 49, 255)

_last_was_active = False
_activation_start = 0.0
_fade_out_start = 0.0
_last_state = None


def _csc_state():
  sm = ui_state.sm
  if sm.recv_frame["starpilotPlan"] < ui_state.started_frame:
    return None
  if sm.recv_frame["carState"] < ui_state.started_frame:
    return None
  if sm.recv_frame["controlsState"] < ui_state.started_frame:
    return None

  plan = sm["starpilotPlan"]
  params = ui_state.ui_params
  if plan.speedLimitChanged or not params.get_bool("ShowCSCStatus"):
    return None

  car_state = sm["carState"]
  v_cruise = car_state.vCruiseCluster
  if v_cruise == 0.0:
    v_cruise = sm["controlsState"].vCruiseDEPRECATED
  is_cruise_set = 0 < v_cruise < 255

  if not is_cruise_set:
    return None

  return {
    'training': plan.cscTraining,
    'active': plan.cscControllingSpeed,
    'curvature': plan.roadCurvature,
  }


def _intensity(curvature: float) -> float:
  if abs(curvature) < _CURVATURE_MIN:
    return _GLOW_BASE_INTENSITY
  curve = min(1.0, (abs(curvature) - _CURVATURE_MIN) / (_CURVATURE_MAX - _CURVATURE_MIN))
  return _GLOW_BASE_INTENSITY + (1.0 - _GLOW_BASE_INTENSITY) * curve


def _glow_period(intensity: float) -> float:
  t = max(0.0, min(1.0, (intensity - _GLOW_BASE_INTENSITY) / (1.0 - _GLOW_BASE_INTENSITY)))
  return _BREATHING_PERIOD / (1.0 + 2.0 * t)


def _lerp_color(a: rl.Color, b: rl.Color, t: float) -> rl.Color:
  t = max(0.0, min(1.0, t))
  return rl.Color(
    a.r + int((b.r - a.r) * t),
    a.g + int((b.g - a.g) * t),
    a.b + int((b.b - a.b) * t),
    255)


def _glow_color(intensity: float) -> rl.Color:
  t = max(0.0, min(1.0, (intensity - _GLOW_BASE_INTENSITY) / (1.0 - _GLOW_BASE_INTENSITY)))
  if t < 0.5:
    return _lerp_color(_GREEN, _AMBER, t / 0.5)
  elif t < 0.6:
    return _lerp_color(_AMBER, _ORANGE, (t - 0.5) / 0.1)
  else:
    return _lerp_color(_ORANGE, _RED, (t - 0.6) / 0.4)


def _render_csc_glow(border_rect: rl.Rectangle, border_width: float = UI_BORDER_SIZE):
  global _last_was_active, _activation_start, _fade_out_start, _last_state

  state = _csc_state()
  now = rl.get_time()

  if state is None or not state['active']:
    if _last_was_active:
      _fade_out_start = now
      _last_was_active = False
    if _last_state is None:
      return
    fade_out = max(0.0, 1.0 - (now - _fade_out_start) / _GLOW_FADE_IN_DURATION)
    if fade_out <= 0:
      _last_state = None
      return
    intensity, period, color, t_norm = _last_state
    fade = fade_out
  else:
    if not _last_was_active:
      _activation_start = now
      _fade_out_start = 0.0
    _last_was_active = True

    intensity = _intensity(state['curvature'])
    period = _glow_period(intensity)
    color = _glow_color(intensity)
    t_norm = max(0.0, min(1.0, (intensity - _GLOW_BASE_INTENSITY) / (1.0 - _GLOW_BASE_INTENSITY)))
    _last_state = (intensity, period, color, t_norm)
    fade = min(1.0, (now - _activation_start) / _GLOW_FADE_IN_DURATION)

  elapsed = now - _activation_start
  phase = (elapsed % period) / period
  amplitude = 0.3 + 0.7 * t_norm
  breath_raw = 0.5 + amplitude * math.sin(phase * 2 * math.pi)
  breath = max(0.0, min(1.0, breath_raw))
  base_alpha = _GLOW_MAX_ALPHA * intensity * fade * (0.6 + 0.4 * breath)

  edge_alpha = min(255, max(1, int(base_alpha)))
  if edge_alpha < 2:
    return

  span = int(border_width * _GLOW_SPAN)
  if span < 1:
    return

  gx = int(border_rect.x)
  gy = int(border_rect.y)
  gw = int(border_rect.width)
  gh = int(border_rect.height)

  glow_rgba = rl.Color(color.r, color.g, color.b, edge_alpha)
  fade_rgba = rl.Color(color.r, color.g, color.b, 0)

  rl.draw_rectangle_gradient_v(gx, gy, gw, span, glow_rgba, fade_rgba)
  rl.draw_rectangle_gradient_v(gx, gy + gh - span, gw, span, fade_rgba, glow_rgba)
  rl.draw_rectangle_gradient_h(gx, gy, span, gh, glow_rgba, fade_rgba)
  rl.draw_rectangle_gradient_h(gx + gw - span, gy, span, gh, fade_rgba, glow_rgba)


_smoothed_steer = 0.0


def render_background_effects(rect: rl.Rectangle, border_width: float):
  global _smoothed_steer
  sm = ui_state.sm

  # 1. Turn Signal and Blind Spot indicators
  car_state = sm["carState"] if sm.valid.get("carState", False) else None
  if car_state:
    params = ui_state.ui_params
    show_signal = params.get_bool("SignalMetrics")
    show_blindspot = params.get_bool("BlindSpotMetrics")
    if show_signal or show_blindspot:
      left_blindspot = car_state.leftBlindspot
      right_blindspot = car_state.rightBlindspot
      if ui_state.starpilot_toggles.get("v_asm_enabled", False):
        vasm_left, vasm_right = get_fresh_vasm_state(ui_state.params_memory)
        left_blindspot = left_blindspot or vasm_left
        right_blindspot = right_blindspot or vasm_right
      left_blinker = car_state.leftBlinker
      right_blinker = car_state.rightBlinker

      if (show_signal and (left_blinker or right_blinker)) or (show_blindspot and (left_blindspot or right_blindspot)):
        interval = 250 if show_blindspot and (left_blindspot or right_blindspot) else 500
        flicker_active = (int(rl.get_time() * 1000) % (interval * 2)) < interval

        def get_half_border_color(blindspot, turn_signal):
          if turn_signal and show_signal:
            if blindspot:
              return TRAFFIC_COLOR if flicker_active else CEM_OVERRIDE_COLOR
            else:
              return CEM_OVERRIDE_COLOR if flicker_active else rl.Color(0, 0, 0, 0)
          elif blindspot and show_blindspot:
            return TRAFFIC_COLOR
          else:
            return rl.Color(0, 0, 0, 0)

        left_color = get_half_border_color(left_blindspot, left_blinker)
        right_color = get_half_border_color(right_blindspot, right_blinker)

        # Draw left side borders
        if left_color.a > 0:
          rl.begin_scissor_mode(int(rect.x), int(rect.y), int(rect.width // 2), int(rect.height))
          rl.draw_rectangle_rounded(rect, 0.12, 10, left_color)
          rl.end_scissor_mode()

        # Draw right side borders
        if right_color.a > 0:
          rl.begin_scissor_mode(int(rect.x + rect.width // 2), int(rect.y), int(rect.width // 2), int(rect.height))
          rl.draw_rectangle_rounded(rect, 0.12, 10, right_color)
          rl.end_scissor_mode()

  # 2. Steering Torque Border
  car_control = sm["carControl"] if sm.valid.get("carControl", False) else None
  if car_control:
    show_steering = ui_state.ui_params.get_bool("ShowSteering")
    if show_steering:
      torque = -car_control.actuators.torque
      abs_torque = abs(torque)

      _smoothed_steer = 0.25 * abs_torque + 0.75 * _smoothed_steer
      if abs(_smoothed_steer - abs_torque) < 0.01:
        _smoothed_steer = abs_torque

      visible_height = int(rect.height * _smoothed_steer)
      if visible_height > 0:
        if _smoothed_steer < 0.25:
          t = _smoothed_steer / 0.25
          col = rl.color_alpha_blend(ENGAGED_COLOR, CEM_OVERRIDE_COLOR, rl.Color(255, 255, 255, int(t * 255)))
        elif _smoothed_steer < 0.5:
          t = (_smoothed_steer - 0.25) / 0.25
          col = rl.color_alpha_blend(CEM_OVERRIDE_COLOR, EXPERIMENTAL_COLOR, rl.Color(255, 255, 255, int(t * 255)))
        else:
          t = min(1.0, (_smoothed_steer - 0.5) / 0.5)
          col = rl.color_alpha_blend(EXPERIMENTAL_COLOR, TRAFFIC_COLOR, rl.Color(255, 255, 255, int(t * 255)))

        y_pos = int(rect.y + rect.height - visible_height)
        if torque < 0:
          rl.begin_scissor_mode(int(rect.x), y_pos, int(border_width), int(visible_height))
        else:
          rl.begin_scissor_mode(int(rect.x + rect.width - border_width), y_pos, int(border_width), int(visible_height))

        rl.draw_rectangle_rounded(rect, 0.12, 10, col)
        rl.end_scissor_mode()


_effects: list[BorderEffect] = [
  BorderEffect(_render_csc_glow, BorderLayer.BEHIND, "csc_glow"),
]


def render_behind(border_rect: rl.Rectangle, border_width: float):
  for effect in _effects:
    if effect.layer == BorderLayer.BEHIND:
      effect.render_fn(border_rect, border_width)


def render_overlay(border_rect: rl.Rectangle, border_width: float):
  for effect in _effects:
    if effect.layer == BorderLayer.OVERLAY:
      effect.render_fn(border_rect, border_width)
