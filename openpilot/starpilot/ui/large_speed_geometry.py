"""Large speed stack dimensions shared by rendering, input and layout metadata."""
from functools import lru_cache

WIDTH = 344
MAX_ROW_HEIGHT = 210
LIMIT_ROW_HEIGHT = 260
CARD_HEIGHT = MAX_ROW_HEIGHT + LIMIT_ROW_HEIGHT
ACTION_HEIGHT = 108
ACTION_X = 88
ACTION_Y = 75 + CARD_HEIGHT + 22
ACTION_HEADER_HEIGHT = 44
GAP = 8
TOGGLE_HEIGHT = 44
SOURCE_ROW_HEIGHT = 56
PADDING = 24


def card_height(mode):
  return CARD_HEIGHT if mode == 'split' else LIMIT_ROW_HEIGHT if mode == 'limit_only' else MAX_ROW_HEIGHT


@lru_cache(maxsize=8)
def _projection_widgets(width, height):
  from openpilot.starpilot.system.android_auto.projection_layout import layout_metadata_for_viewport
  return layout_metadata_for_viewport((width, height))['widgets']


def _action_regions(state):
  from openpilot.starpilot.ui.onroad_customization import placement
  from openpilot.starpilot.ui.onroad_state import slc_controls
  from openpilot.starpilot.ui.presentation import Profile

  header = ACTION_HEADER_HEIGHT if state.speed_limit.pending_speed_limit_mps is not None or state.speed_limit.action_feedback else 0
  regions = [(l, t - header, r, b) for l, t, r, b in
             (control.bounds for control in slc_controls(Profile.LARGE, state))]
  saved = placement(state.customization, 'large', 'speed_limit_actions')
  if not regions and state.speed_limit.action_feedback and saved['enabled']:
    regions.append((saved['x'], saved['y'], saved['x'] + WIDTH, saved['y'] + ACTION_HEADER_HEIGHT))
  return regions


def source_toggle_bounds(state):
  from openpilot.starpilot.ui.onroad_customization import placement
  from openpilot.starpilot.ui.unified_speed_presentation import resolve_unified_speed

  card = placement(state.customization, 'large', 'cruise_limits')
  shown = resolve_unified_speed(state)
  height = card_height(shown.mode)
  top = card['y'] + height + 22
  for left, action_top, right, bottom in _action_regions(state):
    if left < card['x'] + WIDTH and right > card['x'] and action_top < top + TOGGLE_HEIGHT and bottom > top:
      top = bottom + 22
  if top + TOGGLE_HEIGHT > 1050:
    top = card['y'] - GAP - TOGGLE_HEIGHT
  return card['x'], top, card['x'] + WIDTH, top + TOGGLE_HEIGHT


def source_panel_bounds(state, height, viewport):
  """Prefer the aligned column; move the popup only for constrained saved layouts."""
  from openpilot.starpilot.ui.onroad_customization import placement, PROFILES, widget_size, CAMERA_WIDGETS
  from openpilot.starpilot.ui.unified_speed_presentation import resolve_unified_speed

  card = placement(state.customization, 'large', 'cruise_limits')
  height_of_card = card_height(resolve_unified_speed(state).mode)
  left, top, right, bottom = source_toggle_bounds(state)
  occupied = [(card['x'], card['y'], card['x'] + WIDTH, card['y'] + height_of_card), (left, top, right, bottom)]
  occupied.extend(_action_regions(state))
  layouts = state.customization['layouts']['large']
  projected = 'nav_card' in layouts
  if projected:
    from openpilot.starpilot.system.android_auto.projection_layout import placement_size
    widgets = _projection_widgets(round(viewport.width + 60), round(viewport.height + 60))
  else:
    widgets = PROFILES['large']['widgets']
  for key, widget in widgets.items():
    if key in ('cruise_limits', 'speed_limit_actions', *CAMERA_WIDGETS):
      continue
    saved = layouts.get(key)
    if saved is None:
      continue
    if saved['enabled']:
      width, widget_height = (placement_size(key, widget, saved) if projected else widget_size(state.customization, 'large', key))
      native = PROFILES['large']['widgets'].get(key)
      dx = widget['default']['x'] - native['default']['x'] if projected and native else 0
      dy = widget['default']['y'] - native['default']['y'] if projected and native else 0
      x, y = saved['x'] + dx, saved['y'] + dy
      occupied.append((x, y, x + width, y + widget_height))
  candidates = [(left, bottom + GAP), (left, top - GAP - height),
                (left, card['y'] - GAP - height), (right + GAP, top), (left - GAP - WIDTH, top),
                (right + GAP, top - GAP - height), (left - GAP - WIDTH, top - GAP - height)]
  for x, y in candidates:
    y = min(max(y, viewport.y), viewport.y + viewport.height - height)
    if not viewport.x <= x <= viewport.x + viewport.width - WIDTH:
      continue
    if all(x + WIDTH <= l or x >= r or y + height <= t or y >= b for l, t, r, b in occupied):
      return x, y, WIDTH, height
  return None
