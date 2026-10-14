"""Large speed stack dimensions shared by rendering, input and layout metadata."""
from functools import lru_cache

WIDTH = 320
MAX_ROW_HEIGHT = 210
LIMIT_ROW_HEIGHT = 260
CARD_HEIGHT = MAX_ROW_HEIGHT + LIMIT_ROW_HEIGHT
ACTION_HEIGHT = 108
ACTION_X = 88
ACTION_Y = 75 + CARD_HEIGHT + 22
ACTION_HEADER_HEIGHT = 44
GAP = 8
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


def source_panel_bounds(state, height, viewport):
  """Prefer the aligned column; move the popup only for constrained saved layouts."""
  from openpilot.starpilot.ui.onroad_customization import placement, PROFILES, widget_size, CAMERA_WIDGETS
  from openpilot.starpilot.ui.unified_speed_presentation import resolve_unified_speed

  card = placement(state.customization, 'large', 'cruise_limits')
  height_of_card = card_height(resolve_unified_speed(state).mode)
  # The panel opens from the card itself; there is no on-screen toggle row any more.
  left, top, right, bottom = card['x'], card['y'], card['x'] + WIDTH, card['y'] + height_of_card
  occupied = [(left, top, right, bottom)]
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
      if key == 'cem_gauge':
        from openpilot.starpilot.ui.onroad_cem_gauge import gauge_data
        if gauge_data(state) is None:
          continue
      width, widget_height = (placement_size(key, widget, saved) if projected else widget_size(state.customization, 'large', key))
      native = PROFILES['large']['widgets'].get(key)
      dx = widget['default']['x'] - native['default']['x'] if projected and native else 0
      dy = widget['default']['y'] - native['default']['y'] if projected and native else 0
      x, y = saved['x'] + dx, saved['y'] + dy
      occupied.append((x, y, x + width, y + widget_height))
  candidates = [(left, bottom + GAP), (left, top - GAP - height),
                (left, card['y'] - GAP - height), (right + GAP, top), (left - GAP - WIDTH, top),
                (right + GAP, top - GAP - height), (left - GAP - WIDTH, top - GAP - height)]
  # Keep the aligned choices first; another saved widget can fill that column.
  # Its edges supply further columns using the same popup gap and clip checks.
  for occupied_left, _, occupied_right, _ in occupied:
    candidates.extend(((occupied_right + GAP, top), (occupied_left - GAP - WIDTH, top),
                       (occupied_right + GAP, top - GAP - height), (occupied_left - GAP - WIDTH, top - GAP - height)))
  for x, y in candidates:
    y = min(max(y, viewport.y), viewport.y + viewport.height - height)
    if not viewport.x <= x <= viewport.x + viewport.width - WIDTH:
      continue
    if all(x + WIDTH <= l or x >= r or y + height <= t or y >= b for l, t, r, b in occupied):
      return x, y, WIDTH, height
  return None
