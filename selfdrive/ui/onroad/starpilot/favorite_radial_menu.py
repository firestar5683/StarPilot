"""Big UI's on-road entry point for the shared three-slot favorites system."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterable
from typing import Any

import pyray as rl

from openpilot.starpilot.common.controller_actions import CONTROLLER_ACTION_SET_SPEED
from openpilot.starpilot.common.favorite_slots import (
  FAVORITE_SLOT_COUNT,
  get_favorite_enum_state,
  get_param_enum_options,
  is_enum_param,
  is_favorite_action_key,
  load_favorite_slots,
  request_starpilot_toggle_refresh,
  save_favorite_slots,
  toggle_favorite_slot,
  unassign_favorite_slot,
)


class FavoriteRadialMenu:
  """Owns favorites input and rendering without competing with on-road widgets.

  StarPilotOnroadView calls ``process_mouse_events`` before rendering its other
  controls so the lower-left gesture has first claim on its pointer events,
  then calls ``render`` as the topmost on-road overlay.
  """

  STATE_COLLAPSED = "collapsed"
  STATE_RADIAL = "radial"
  STATE_PICKER = "picker"

  AUTO_COLLAPSE_SECONDS = 6.0
  PICKER_AUTO_COLLAPSE_SECONDS = 30.0
  LONG_PRESS_SECONDS = 0.60
  MAX_TAP_TRAVEL = 36.0
  SWIPE_MIN_TRAVEL = 55.0
  PICKER_COLUMNS = 4
  PICKER_ROWS = 2
  PICKER_PAGE_SIZE = PICKER_COLUMNS * PICKER_ROWS
  PICKER_HEADER_HEIGHT = 152.0
  PICKER_FOOTER_HEIGHT = 168.0
  PICKER_GRID_GAP = 24.0
  PICKER_CONTROL_HEIGHT = 96.0
  PICKER_CONTROL_HIT_PAD_Y = 28.0
  PICKER_CARD_PADDING = 26.0
  PICKER_CLOSE_SIZE = 72.0
  PICKER_CLOSE_HIT_SIZE = 150.0
  CORNER_HINT_OUTER_RADIUS = 62.0
  CORNER_HINT_RING_RADIUS = 42.0
  CORNER_HINT_EDGE_MARGIN = 6.0
  _ELLIPSIS = "..."

  _PURPLE = (161, 112, 255)
  _PANEL = rl.Color(13, 11, 23, 236)
  _PANEL_BORDER = rl.Color(214, 192, 255, 166)
  _TEXT = rl.Color(255, 255, 255, 245)
  _MUTED_TEXT = rl.Color(213, 202, 232, 216)
  _PICKER_SECTION_LABELS = {
    "Visual (Display & UI)": "Display & UI",
    "Longitudinal (Speed & Following)": "Speed & Following",
    "Lateral (Steering)": "Steering",
  }

  def __init__(self, params: Any, params_memory: Any,
               option_provider: Callable[[], Iterable[dict[str, Any]]], *,
               clock: Callable[[], float] = time.monotonic):
    self._params = params
    self._params_memory = params_memory
    self._option_provider = option_provider
    self._clock = clock

    self._state = self.STATE_COLLAPSED
    self._selected_slot: int | None = None
    self._editing_slot: int | None = None
    self._picker_options: list[dict[str, Any]] = []
    self._available_option_keys: set[str] | None = None
    self._available_option_labels: dict[str, str] = {}
    self._picker_page = 0
    self._last_interaction_at = float("-inf")
    self._last_slot_cycle_times: dict[int, float] = {}
    self._flash_slot: int | None = None
    self._flash_start_time: float = 0.0

    self._corner_press: Any | None = None
    self._pressed_target: tuple[str, int | None] | None = None
    self._press_start_time: float | None = None
    self._press_start_pos: Any | None = None
    self._long_press_fired = False

    self._rect = rl.Rectangle(0, 0, 0, 0)
    self._corner_zone = rl.Rectangle(0, 0, 0, 0)
    self._corner_touch_zone = rl.Rectangle(0, 0, 0, 0)
    self._slot_rects: list[tuple[int, rl.Rectangle, rl.Vector2, float]] = []
    self._slot_unassign_rects: list[tuple[int, rl.Rectangle]] = []
    self._drawer_rect = rl.Rectangle(0, 0, 0, 0)
    self._drawer_close_rect = rl.Rectangle(0, 0, 0, 0)
    self._drawer_close_hit_rect = rl.Rectangle(0, 0, 0, 0)
    self._drawer_prev_rect = rl.Rectangle(0, 0, 0, 0)
    self._drawer_prev_hit_rect = rl.Rectangle(0, 0, 0, 0)
    self._drawer_next_rect = rl.Rectangle(0, 0, 0, 0)
    self._drawer_next_hit_rect = rl.Rectangle(0, 0, 0, 0)
    self._option_rects: list[tuple[int, rl.Rectangle]] = []
    self._slots: list[dict[str, Any]] = []

    self._font_medium: Any | None = None
    self._font_bold: Any | None = None

  @property
  def state(self) -> str:
    return self._state

  @property
  def selected_slot(self) -> int | None:
    return self._selected_slot

  @property
  def editing_slot(self) -> int | None:
    return self._editing_slot

  @property
  def is_open(self) -> bool:
    return self._state != self.STATE_COLLAPSED

  @property
  def is_picker_open(self) -> bool:
    return self._state == self.STATE_PICKER

  def _reset_press_tracking(self) -> None:
    self._pressed_target = None
    self._press_start_time = None
    self._press_start_pos = None
    self._long_press_fired = False

  def collapse(self) -> None:
    self._state = self.STATE_COLLAPSED
    self._selected_slot = None
    self._editing_slot = None
    self._picker_options = []
    self._picker_page = 0
    self._corner_press = None
    self._reset_press_tracking()

  def corner_center(self, rect: rl.Rectangle) -> rl.Vector2:
    scale = self._scale_for(rect)
    inset = (self.CORNER_HINT_RING_RADIUS + self.CORNER_HINT_EDGE_MARGIN) * scale
    return rl.Vector2(rect.x + inset, rect.y + rect.height - inset)

  def slot_centers(self, rect: rl.Rectangle) -> list[rl.Vector2]:
    self._layout(rect)
    return [center for _index, _box, center, *_rest in self._slot_rects]

  def unassign_centers(self, rect: rl.Rectangle) -> list[rl.Vector2]:
    self._layout(rect)
    return [
      rl.Vector2(unassign_rect.x + unassign_rect.width / 2, unassign_rect.y + unassign_rect.height / 2)
      for _index, unassign_rect in self._slot_unassign_rects
    ]

  def option_centers(self, rect: rl.Rectangle) -> list[rl.Vector2]:
    self._layout(rect)
    return [rl.Vector2(option_rect.x + option_rect.width / 2, option_rect.y + option_rect.height / 2)
            for _index, option_rect in self._option_rects]

  def process_mouse_events(self, events: Iterable[Any], rect: rl.Rectangle) -> bool:
    """Process the current frame's mouse events and report whether they are claimed."""
    self._layout(rect)
    self._collapse_if_idle()
    claimed = self.is_open

    self._check_long_press_frame()

    for mouse_event in events:
      if getattr(mouse_event, "slot", 0) != 0:
        continue
      if getattr(mouse_event, "left_pressed", False):
        claimed = self._handle_press(mouse_event.pos) or claimed
      elif getattr(mouse_event, "left_released", False):
        claimed = self._handle_release(mouse_event.pos) or claimed

    self._check_long_press_frame()

    # A press can turn a radial menu into the drawer. Refresh hit targets for
    # the next frame before returning to the on-road view.
    self._layout(rect)
    return claimed or self.is_open or self._corner_press is not None

  def render(self, rect: rl.Rectangle) -> None:
    self._layout(rect)
    self._collapse_if_idle()
    if self._state == self.STATE_COLLAPSED:
      self._draw_corner_hint()
    elif self._state == self.STATE_RADIAL:
      self._draw_corner_hint()
      self._draw_radial_menu()
    else:
      self._draw_picker()

  def blocks_pointer(self, mouse_pos: Any) -> bool:
    """Whether a parent click at ``mouse_pos`` belongs to this menu."""
    return self.is_open or self._corner_press is not None or self._contains(self._corner_touch_zone, mouse_pos)

  def _touch(self) -> None:
    self._last_interaction_at = self._clock()

  def _collapse_if_idle(self) -> None:
    timeout = self.PICKER_AUTO_COLLAPSE_SECONDS if self.is_picker_open else self.AUTO_COLLAPSE_SECONDS
    if self.is_open and self._clock() - self._last_interaction_at >= timeout:
      self.collapse()

  @staticmethod
  def _contains(rect: rl.Rectangle, pos: Any) -> bool:
    return rect.x <= pos.x <= rect.x + rect.width and rect.y <= pos.y <= rect.y + rect.height

  @staticmethod
  def _roundness(rect: rl.Rectangle, radius: float) -> float:
    return min(1.0, radius / max(1.0, min(rect.width, rect.height) / 2.0))

  @staticmethod
  def _snap_render_rect(rect: rl.Rectangle) -> rl.Rectangle:
    left = round(rect.x)
    top = round(rect.y)
    right = round(rect.x + rect.width)
    bottom = round(rect.y + rect.height)
    return rl.Rectangle(
      float(left), float(top),
      float(right - left), float(bottom - top),
    )

  @staticmethod
  def _distance(a: Any, b: Any) -> float:
    return math.hypot(float(a.x - b.x), float(a.y - b.y))

  @staticmethod
  def _scale_for(rect: rl.Rectangle) -> float:
    return max(0.35, min(rect.width / 2160.0, rect.height / 1080.0))

  def _corner_zone_for(self, rect: rl.Rectangle) -> rl.Rectangle:
    size = 160.0 * self._scale_for(rect)
    return rl.Rectangle(rect.x, rect.y + rect.height - size, size, size)

  def _corner_touch_zone_for(self, rect: rl.Rectangle) -> rl.Rectangle:
    size = 180.0 * self._scale_for(rect)
    return rl.Rectangle(rect.x, rect.y + rect.height - size, size, size)

  def _layout(self, rect: rl.Rectangle) -> None:
    self._rect = rect
    self._corner_zone = self._corner_zone_for(rect)
    self._corner_touch_zone = self._corner_touch_zone_for(rect)
    self._slots = load_favorite_slots(self._params, eligible_keys=self._available_option_keys)
    for slot in self._slots:
      key = slot.get("key")
      if key in self._available_option_labels:
        slot["label"] = self._available_option_labels[key]
      if key == CONTROLLER_ACTION_SET_SPEED and slot.get("value") is not None:
        unit = "km/h" if self._params.get_bool("IsMetric") else "mph"
        slot["label"] = f"Set Speed To {slot['value']:g} {unit}"
    self._layout_slot_rects()
    self._layout_picker_rects()

  def _layout_slot_rects(self) -> None:
    scale = self._scale_for(self._rect)
    origin = self.corner_center(self._rect)
    orbit_radius = 515.0 * scale
    node_radius = 52.0 * scale
    slot_angles_deg = (66.0, 40.0, 18.0)
    blade_w = 450.0 * scale
    blade_h = 104.0 * scale

    self._slot_rects = []
    for index, angle_deg in enumerate(slot_angles_deg[:FAVORITE_SLOT_COUNT]):
      angle_rad = math.radians(angle_deg)
      center = rl.Vector2(
        origin.x + math.cos(angle_rad) * orbit_radius,
        origin.y - math.sin(angle_rad) * orbit_radius,
      )
      blade_x = center.x - node_radius
      blade_y = center.y - blade_h / 2.0
      blade_rect = rl.Rectangle(blade_x, blade_y, blade_w, blade_h)
      hit_box = rl.Rectangle(
        blade_x - 12.0 * scale,
        blade_y - 8.0 * scale,
        blade_w + 24.0 * scale,
        blade_h + 16.0 * scale,
      )
      self._slot_rects.append((index, hit_box, center, node_radius, angle_deg, blade_rect))

    self._slot_unassign_rects = []
    if self._editing_slot is not None and self._editing_slot < len(self._slot_rects):
      item = self._slot_rects[self._editing_slot]
      blade_rect = item[5]
      badge_touch_r = 32.0 * scale
      badge_center = rl.Vector2(
        blade_rect.x + blade_rect.width - 2.0 * scale,
        blade_rect.y + 2.0 * scale,
      )
      badge_box = rl.Rectangle(
        badge_center.x - badge_touch_r,
        badge_center.y - badge_touch_r,
        badge_touch_r * 2.0,
        badge_touch_r * 2.0,
      )
      self._slot_unassign_rects.append((self._editing_slot, badge_box))


  def _layout_picker_rects(self) -> None:
    self._option_rects = []
    self._drawer_rect = rl.Rectangle(0, 0, 0, 0)
    self._drawer_close_rect = rl.Rectangle(0, 0, 0, 0)
    self._drawer_close_hit_rect = rl.Rectangle(0, 0, 0, 0)
    self._drawer_prev_rect = rl.Rectangle(0, 0, 0, 0)
    self._drawer_prev_hit_rect = rl.Rectangle(0, 0, 0, 0)
    self._drawer_next_rect = rl.Rectangle(0, 0, 0, 0)
    self._drawer_next_hit_rect = rl.Rectangle(0, 0, 0, 0)
    if self._state != self.STATE_PICKER:
      return

    scale = self._scale_for(self._rect)
    margin_x = 76.0 * scale
    margin_y = 66.0 * scale
    self._drawer_rect = rl.Rectangle(
      self._rect.x + margin_x,
      self._rect.y + margin_y,
      self._rect.width - margin_x * 2,
      self._rect.height - margin_y * 2,
    )

    padding_x = 36.0 * scale
    header_height = self.PICKER_HEADER_HEIGHT * scale
    footer_height = self.PICKER_FOOTER_HEIGHT * scale
    gap_x = self.PICKER_GRID_GAP * scale
    gap_y = self.PICKER_GRID_GAP * scale
    gap_header_footer = 18.0 * scale

    # Close button visual & hit bounds
    close_size = self.PICKER_CLOSE_SIZE * scale
    self._drawer_close_rect = rl.Rectangle(
      self._drawer_rect.x + self._drawer_rect.width - padding_x - close_size,
      self._drawer_rect.y + (header_height - close_size) / 2,
      close_size,
      close_size,
    )
    self._drawer_close_hit_rect = rl.Rectangle(
      self._drawer_rect.x + self._drawer_rect.width - padding_x - self.PICKER_CLOSE_HIT_SIZE * scale,
      self._drawer_rect.y,
      self.PICKER_CLOSE_HIT_SIZE * scale,
      header_height,
    )

    # 4x2 Card Grid
    grid_top = self._drawer_rect.y + header_height + gap_header_footer
    grid_width = self._drawer_rect.width - padding_x * 2
    grid_height = self._drawer_rect.height - header_height - footer_height - gap_header_footer * 2
    card_width = (grid_width - gap_x * (self.PICKER_COLUMNS - 1)) / self.PICKER_COLUMNS
    card_height = (grid_height - gap_y * (self.PICKER_ROWS - 1)) / self.PICKER_ROWS

    page_start = self._picker_page * self.PICKER_PAGE_SIZE
    for offset, _option in enumerate(self._picker_options[page_start:page_start + self.PICKER_PAGE_SIZE]):
      row, column = divmod(offset, self.PICKER_COLUMNS)
      option_rect = rl.Rectangle(
        self._drawer_rect.x + padding_x + column * (card_width + gap_x),
        grid_top + row * (card_height + gap_y),
        card_width,
        card_height,
      )
      self._option_rects.append((page_start + offset, option_rect))

    # Pager buttons in footer
    control_width = 200.0 * scale
    control_height = self.PICKER_CONTROL_HEIGHT * scale
    controls_y = self._drawer_rect.y + self._drawer_rect.height - footer_height + (footer_height - control_height) / 2
    self._drawer_next_rect = rl.Rectangle(
      self._drawer_rect.x + self._drawer_rect.width - padding_x - control_width,
      controls_y,
      control_width,
      control_height,
    )
    self._drawer_next_hit_rect = rl.Rectangle(
      self._drawer_next_rect.x - 10.0 * scale,
      self._drawer_next_rect.y - self.PICKER_CONTROL_HIT_PAD_Y * scale,
      self._drawer_next_rect.width + 20.0 * scale,
      self._drawer_next_rect.height + self.PICKER_CONTROL_HIT_PAD_Y * scale * 2.0,
    )
    self._drawer_prev_rect = rl.Rectangle(
      self._drawer_next_rect.x - gap_x - control_width,
      controls_y,
      control_width,
      control_height,
    )
    self._drawer_prev_hit_rect = rl.Rectangle(
      self._drawer_prev_rect.x - 10.0 * scale,
      self._drawer_prev_rect.y - self.PICKER_CONTROL_HIT_PAD_Y * scale,
      self._drawer_prev_rect.width + 20.0 * scale,
      self._drawer_prev_rect.height + self.PICKER_CONTROL_HIT_PAD_Y * scale * 2.0,
    )

  def _handle_press(self, mouse_pos: Any) -> bool:
    if self._state == self.STATE_COLLAPSED:
      if self._contains(self._corner_touch_zone, mouse_pos):
        self._corner_press = mouse_pos
        return True
      return False

    target = self._target_at(mouse_pos)
    self._pressed_target = target
    self._press_start_time = self._clock()
    self._press_start_pos = mouse_pos
    self._long_press_fired = False
    self._touch()
    return True

  def _check_long_press_frame(self) -> None:
    if self._pressed_target is None or self._long_press_fired or self._press_start_time is None:
      return

    target_type, slot_idx = self._pressed_target
    if target_type != "slot" or slot_idx is None:
      return

    slot = self._slots[slot_idx] if slot_idx < len(self._slots) else {}
    if not self._slot_is_configured(slot):
      return

    if self._clock() - self._press_start_time >= self.LONG_PRESS_SECONDS:
      self._long_press_fired = True
      self._editing_slot = slot_idx
      self._touch()

  def _handle_release(self, mouse_pos: Any) -> bool:
    if self._state == self.STATE_COLLAPSED:
      if self._corner_press is None:
        return False

      start = self._corner_press
      self._corner_press = None
      dx = mouse_pos.x - start.x
      dy = mouse_pos.y - start.y
      is_tap = self._distance(start, mouse_pos) <= self.MAX_TAP_TRAVEL * self._scale_for(self._rect)
      is_diagonal_inward_swipe = (
        dx >= self.SWIPE_MIN_TRAVEL * self._scale_for(self._rect)
        and dy <= -self.SWIPE_MIN_TRAVEL * self._scale_for(self._rect)
        and 0.35 <= dx / max(1.0, abs(dy)) <= 2.8
      )
      if is_tap or is_diagonal_inward_swipe:
        self._open_radial()
      return True

    dragged_away = (
      self._press_start_pos is not None and
      self._distance(self._press_start_pos, mouse_pos) > self.MAX_TAP_TRAVEL * self._scale_for(self._rect)
    )
    if dragged_away:
      if self._long_press_fired:
        self._editing_slot = None
      self._reset_press_tracking()
      return True

    release_target = self._target_at(mouse_pos)

    is_long_press = self._long_press_fired or (
      self._press_start_time is not None and self._clock() - self._press_start_time >= self.LONG_PRESS_SECONDS
    )
    if is_long_press:
      if not self._long_press_fired and self._pressed_target is not None:
        target_type, slot_idx = self._pressed_target
        if target_type == "slot" and slot_idx is not None:
          slot = self._slots[slot_idx] if slot_idx < len(self._slots) else {}
          if self._slot_is_configured(slot):
            self._editing_slot = slot_idx
            self._touch()
      self._reset_press_tracking()
      return True

    if self._pressed_target is not None and release_target == self._pressed_target:
      self._activate_target(self._pressed_target)
    elif self._state == self.STATE_PICKER and not self._contains(self._drawer_rect, mouse_pos):
      self.collapse()
    elif self._state == self.STATE_RADIAL and not any(self._contains(box, mouse_pos) for _, box, *_ in self._slot_rects):
      self.collapse()

    self._reset_press_tracking()
    return True

  def _target_at(self, mouse_pos: Any) -> tuple[str, int | None] | None:
    if self._state == self.STATE_RADIAL:
      for index, unassign_box in self._slot_unassign_rects:
        bc_x = unassign_box.x + unassign_box.width / 2.0
        bc_y = unassign_box.y + unassign_box.height / 2.0
        b_r = unassign_box.width / 2.0
        dx = mouse_pos.x - bc_x
        dy = mouse_pos.y - bc_y
        if dx * dx + dy * dy <= b_r * b_r:
          return "unassign", index
      for index, box, center, _radius, *_rest in self._slot_rects:
        if self._contains(box, mouse_pos):
          return "slot", index
      return None

    if self._state == self.STATE_PICKER:
      if self._contains(self._drawer_close_hit_rect, mouse_pos):
        return "close", None
      if self._contains(self._drawer_prev_hit_rect, mouse_pos) and self._picker_page > 0:
        return "previous", None
      if self._contains(self._drawer_next_hit_rect, mouse_pos) and self._has_next_picker_page:
        return "next", None
      for index, option_rect in self._option_rects:
        if self._contains(option_rect, mouse_pos):
          return "option", index
    return None

  @property
  def _has_next_picker_page(self) -> bool:
    return (self._picker_page + 1) * self.PICKER_PAGE_SIZE < len(self._picker_options)

  def _activate_target(self, target: tuple[str, int | None]) -> None:
    action, value = target
    if action == "unassign" and value is not None:
      unassign_favorite_slot(
        value,
        self._params,
        self._params_memory,
        eligible_keys=self._available_option_keys,
      )
      self._editing_slot = None
      self._touch()
      return

    if action == "slot" and value is not None:
      if self._editing_slot is not None:
        self._editing_slot = None
        self._touch()
        return

      slot = self._slots[value] if value < len(self._slots) else {}
      if self._slot_is_configured(slot):
        now = self._clock()
        if now - self._last_slot_cycle_times.get(value, float("-inf")) < 0.28:
          return
        self._last_slot_cycle_times[value] = now
        self._flash_slot = value
        self._flash_start_time = now
        toggle_favorite_slot(
          value,
          self._params,
          self._params_memory,
          eligible_keys=self._available_option_keys,
        )
        self._touch()
      else:
        self._open_picker(value)
      return

    if action == "close":
      self._state = self.STATE_RADIAL
      self._selected_slot = None
      self._editing_slot = None
      self._picker_options = []
      self._picker_page = 0
      self._touch()
      return

    if action == "previous":
      self._picker_page = max(0, self._picker_page - 1)
      self._touch()
      return

    if action == "next":
      if self._has_next_picker_page:
        self._picker_page += 1
        self._touch()
      return

    if action == "option" and value is not None and value < len(self._picker_options):
      self._assign_option(self._picker_options[value])

  @staticmethod
  def _slot_is_configured(slot: dict[str, Any]) -> bool:
    return bool(slot.get("enabled") and slot.get("show_onroad") and slot.get("key"))

  def _open_radial(self) -> None:
    self._refresh_option_catalog()
    self._state = self.STATE_RADIAL
    self._selected_slot = None
    self._editing_slot = None
    self._picker_options = []
    self._picker_page = 0
    self._touch()

  def _open_picker(self, slot_index: int) -> None:
    options = self._refresh_option_catalog()
    # This on-road picker has no numeric editor. Keep speed actions in the
    # catalogue for activating saved slots, but configure their value in Galaxy.
    self._picker_options = [option for option in (options or []) if option.get("value_type") != "speed"]
    self._selected_slot = slot_index
    self._editing_slot = None
    self._picker_page = 0
    self._state = self.STATE_PICKER
    self._touch()

  def _assign_option(self, option: dict[str, Any]) -> None:
    if self._selected_slot is None or self._selected_slot >= FAVORITE_SLOT_COUNT:
      return

    key = str(option.get("key") or "").strip()
    if not key or key == CONTROLLER_ACTION_SET_SPEED or option.get("value_type") == "speed":
      return

    slots = load_favorite_slots(self._params, eligible_keys=self._available_option_keys)
    slots[self._selected_slot] = {
      "enabled": True,
      "show_onroad": True,
      "key": key,
      "label": str(option.get("label") or key),
    }
    save_favorite_slots(slots, self._params, eligible_keys=self._available_option_keys)
    request_starpilot_toggle_refresh(self._params_memory)
    self._state = self.STATE_RADIAL
    self._selected_slot = None
    self._picker_options = []
    self._picker_page = 0
    self._touch()

  def _refresh_option_catalog(self) -> list[dict[str, Any]] | None:
    try:
      options = [dict(option) for option in self._option_provider() if isinstance(option, dict) and option.get("key")]
    except Exception:
      return None

    options.sort(key=lambda option: (
      str(option.get("label") or option.get("key")).casefold(),
      str(option.get("key")).casefold(),
    ))
    self._available_option_keys = {str(option["key"]) for option in options}
    self._available_option_labels = {
      str(option["key"]): str(option.get("label") or option["key"])
      for option in options
    }
    return options

  def _font(self, *, bold: bool) -> Any:
    # Import GUI state only when an actual frame is being drawn. This keeps the
    # input controller usable in headless tests and tools.
    from openpilot.system.ui.lib.application import FontWeight, gui_app

    if bold:
      if self._font_bold is None:
        self._font_bold = gui_app.font(FontWeight.BOLD)
      return self._font_bold
    if self._font_medium is None:
      self._font_medium = gui_app.font(FontWeight.MEDIUM)
    return self._font_medium

  @staticmethod
  def _measure_text(font: Any, text: str, font_size: int):
    from openpilot.system.ui.lib.text_measure import measure_text_cached
    return measure_text_cached(font, text, font_size)

  @staticmethod
  def _draw_text(font: Any, text: str, pos: rl.Vector2, font_size: int, color: rl.Color) -> None:
    from openpilot.system.ui.lib.text_measure import draw_text_with_shadow
    draw_text_with_shadow(font, text, pos, font_size, color)

  @staticmethod
  def _semantic_split_label(label: str, max_chars: int = 18) -> tuple[str, str | None]:
    label = label.strip()
    if len(label) <= max_chars:
      return label, None
    words = label.split()
    if len(words) <= 1:
      return label, None
    line1_words: list[str] = []
    line2_words: list[str] = []
    for word in words:
      candidate = " ".join(line1_words + [word])
      if len(candidate) <= max_chars or not line1_words:
        line1_words.append(word)
      else:
        line2_words.append(word)
    if not line2_words:
      return label, None
    return " ".join(line1_words), " ".join(line2_words)

  @classmethod
  def _picker_section_label(cls, option: dict[str, Any]) -> str:
    section = str(option.get("section") or "Favorite").strip()
    return cls._PICKER_SECTION_LABELS.get(section, section)

  @staticmethod
  def _wrap_picker_text(font: Any, text: str, font_size: int, max_width: float,
                        max_lines: int = 2) -> list[str]:
    from openpilot.system.ui.lib.wrap_text import wrap_text

    text = " ".join(text.split())
    lines = list(wrap_text(font, text, font_size, int(max_width)))
    if len(lines) > max_lines:
      lines = lines[:max_lines]
      lines[-1] = FavoriteRadialMenu._append_ellipsis(font, lines[-1], font_size, max_width)
    return lines

  @staticmethod
  def _sample_aether_color(t: float, alpha: int) -> rl.Color:
    """Sample from the tri-stop Aether gradient (#C49EFF -> #AC7DFF -> #58329E)."""
    if t <= 0.5:
      w = t * 2.0
      r = int(196 - 24 * w)
      g = int(158 - 33 * w)
      b = 255
    else:
      w = (t - 0.5) * 2.0
      r = int(172 - 84 * w)
      g = int(125 - 75 * w)
      b = int(255 - 97 * w)
    return rl.Color(r, g, b, alpha)

  def _draw_corner_hint(self) -> None:
    scale = self._scale_for(self._rect)
    x0 = self._rect.x
    y0 = self._rect.y + self._rect.height
    is_pressed = self._corner_press is not None

    size = 150.0 * scale
    steps = 48

    # 1. Precompute edge vertices to minimize per-frame allocations
    v_origin = rl.Vector2(x0, y0)
    inv_steps = 1.0 / steps
    pts_top = [rl.Vector2(x0, y0 - size * (k * inv_steps)) for k in range(steps + 1)]
    pts_right = [rl.Vector2(x0 + size * (k * inv_steps), y0) for k in range(steps + 1)]

    # 2. Pass 0 (Smoked Obsidian Base) & Pass 1 (Tri-Stop Aether Gradient Mesh)
    # Borderless design: smooth monotonic decay into exact 0 alpha at hypotenuse
    base_max_alpha = 200 if is_pressed else 160
    purple_max_alpha = 145 if is_pressed else 105

    for i in range(steps):
      t_mid = (i + 0.5) * inv_steps
      v_ta, v_tb = pts_top[i], pts_top[i + 1]
      v_ra, v_rb = pts_right[i], pts_right[i + 1]

      base_a = int(base_max_alpha * ((1.0 - t_mid) ** 1.40))
      purple_a = int(purple_max_alpha * ((1.0 - t_mid) ** 1.75))

      for col in (rl.Color(8, 6, 18, base_a) if base_a > 0 else None,
                  self._sample_aether_color(t_mid, purple_a) if purple_a > 0 else None):
        if col is None:
          continue
        if i == 0:
          rl.draw_triangle(v_origin, v_rb, v_tb, col)
        else:
          rl.draw_triangle(v_ta, v_ra, v_tb, col)
          rl.draw_triangle(v_tb, v_ra, v_rb, col)

    # 3. Ultra-Polished Frosted-Glass Vector Arrow (Nestled deep in purple corner)
    cx = x0 + 34.0 * scale
    cy = y0 - 34.0 * scale

    tip = rl.Vector2(cx + 15.0 * scale, cy - 15.0 * scale)
    tail = rl.Vector2(cx - 15.0 * scale, cy + 15.0 * scale)
    wing1 = rl.Vector2(tip.x - 14.0 * scale, tip.y + 1.2 * scale)
    wing2 = rl.Vector2(tip.x - 1.2 * scale, tip.y + 14.0 * scale)

    line_w = 4.6 * scale

    # Tier 1: Deep Subsurface Ambient Occlusion Shadow
    s_off = 1.6 * scale
    s_tip = rl.Vector2(tip.x + s_off, tip.y + s_off)
    s_tail = rl.Vector2(tail.x + s_off, tail.y + s_off)
    s_w1 = rl.Vector2(wing1.x + s_off, wing1.y + s_off)
    s_w2 = rl.Vector2(wing2.x + s_off, wing2.y + s_off)
    shadow_w = line_w + 2.0 * scale
    shadow_col = rl.Color(8, 6, 16, 130 if is_pressed else 105)

    # Tier 2: Aether Violet Refractive Halo / Glass Bloom
    halo_w = line_w + 3.2 * scale
    halo_col = rl.Color(185, 145, 255, 75 if is_pressed else 55)

    # Tier 3: Radiant High-Luminance Frost White Body
    arrow_col = rl.Color(255, 255, 255, 245 if is_pressed else 225)

    # Tier 4: Specular Spine Highlight
    spec_w = 2.0 * scale
    spec_col = rl.Color(255, 255, 255, 255 if is_pressed else 240)

    # Render multi-pass optical stack
    layers = (
      (s_tail, s_tip, s_w1, s_w2, shadow_w, shadow_col),
      (tail, tip, wing1, wing2, halo_w, halo_col),
      (tail, tip, wing1, wing2, line_w, arrow_col),
      (tail, tip, wing1, wing2, spec_w, spec_col),
    )

    for p_tail, p_tip, p_w1, p_w2, width, col in layers:
      rl.draw_line_ex(p_tail, p_tip, width, col)
      rl.draw_line_ex(p_tip, p_w1, width, col)
      rl.draw_line_ex(p_tip, p_w2, width, col)
      r_cap = width * 0.5
      for pt in (p_tail, p_tip, p_w1, p_w2):
        rl.draw_circle_v(pt, r_cap, col)

  def _draw_radial_menu(self) -> None:
    scale = self._scale_for(self._rect)
    origin = self.corner_center(self._rect)
    purple = self._PURPLE

    rail_r = 460.0 * scale
    rail_start_rl = 289.0
    rail_end_rl = 348.0
    segments = 44

    # Outer atmospheric rail glow
    rl.draw_ring(origin, rail_r - 8.0 * scale, rail_r + 8.0 * scale,
                 rail_start_rl, rail_end_rl, segments, rl.Color(*purple, 24))
    # Mid-layer rail glow
    rl.draw_ring(origin, rail_r - 4.0 * scale, rail_r + 4.0 * scale,
                 rail_start_rl, rail_end_rl, segments, rl.Color(*purple, 58))
    # Crisp core rail
    rl.draw_ring(origin, rail_r - 1.8 * scale, rail_r + 1.8 * scale,
                 rail_start_rl, rail_end_rl, segments, rl.Color(214, 192, 255, 140))

    # 2. Orbital switch blade and node complication rendering
    for index, _hit_box, center, node_r, _deg, blade_rect in self._slot_rects:
      slot = self._slots[index] if index < len(self._slots) else {}
      configured = self._slot_is_configured(slot)
      accent_alpha = 235 if configured else 160
      accent = rl.Color(*purple, accent_alpha)

      # 1. Main Unified Blade Chassis
      is_pressed = (self._pressed_target == ("slot", index))
      chassis_rect = blade_rect
      if is_pressed:
        pad = 2.0 * scale
        chassis_rect = rl.Rectangle(blade_rect.x + pad, blade_rect.y + pad, blade_rect.width - pad * 2.0, blade_rect.height - pad * 2.0)

      draw_rect = self._snap_render_rect(chassis_rect)
      # Blades float over the animated road/model layers. Keep their chassis
      # opaque so bright path pixels cannot read as gaps at curved ends.
      if configured:
        rl.draw_rectangle_rounded(draw_rect, 0.45, 14, rl.Color(14, 10, 26, 255))
        border_col = rl.Color(214, 192, 255, 230) if is_pressed else rl.Color(161, 112, 255, 140)
        border_width = max(1, int(round(1.8 * scale)))
        rl.draw_rectangle_rounded_lines_ex(draw_rect, 0.45, 14, border_width, border_col)
      else:
        rl.draw_rectangle_rounded(draw_rect, 0.45, 14, rl.Color(12, 10, 22, 255))
        border_width = max(1, int(round(1.4 * scale)))
        rl.draw_rectangle_rounded_lines_ex(draw_rect, 0.45, 14, border_width, rl.Color(161, 112, 255, 80))

      # 2. Left Complication Hub Disc
      rl.draw_circle_v(center, node_r + 12.0 * scale, rl.Color(*purple, 22 if configured else 12))
      rl.draw_circle_v(center, node_r + 5.0 * scale, rl.Color(*purple, 48 if configured else 24))

      rl.draw_circle_v(center, node_r, self._PANEL)
      rl.draw_circle_v(center, node_r - 2.5 * scale, rl.Color(32, 23, 54, 250) if configured else rl.Color(20, 16, 32, 250))

      slot_key = str(slot.get("key") or "")
      is_action = is_favorite_action_key(slot_key)
      _curr_val, active_idx, active_label, enum_options = get_favorite_enum_state(slot_key, self._params) if configured else (None, 0, "", [])
      is_dropdown = bool(enum_options and len(enum_options) >= 2)
      is_toggle = configured and not is_action and not is_dropdown
      is_on = False
      if is_toggle:
        try:
          is_on = bool(self._params.get_bool(slot_key))
        except Exception:
          is_on = False

      if is_dropdown:
        total_opts = len(enum_options)

        # N-Segmented outer rim complication
        seg_gap = 6.0
        seg_span = (360.0 - total_opts * seg_gap) / total_opts
        for k in range(total_opts):
          start_deg = k * (seg_span + seg_gap) - 90.0
          end_deg = start_deg + seg_span
          if k == active_idx:
            rl.draw_ring(center, node_r - 4.5 * scale, node_r, start_deg, end_deg, 20, rl.Color(214, 192, 255, 255))
            rl.draw_ring(center, node_r - 5.5 * scale, node_r - 0.5 * scale, start_deg, end_deg, 20, rl.Color(161, 112, 255, 180))
          else:
            rl.draw_ring(center, node_r - 2.5 * scale, node_r - 0.5 * scale, start_deg, end_deg, 20, rl.Color(68, 44, 112, 140))
      elif is_toggle and is_on:
        # Glowing illuminated rim when toggle is active
        rl.draw_ring(center, node_r - 4.5 * scale, node_r, 0.0, 360.0, 40, rl.Color(214, 192, 255, 255))
        rl.draw_ring(center, node_r - 5.5 * scale, node_r - 0.5 * scale, 0.0, 360.0, 40, rl.Color(161, 112, 255, 180))
        rl.draw_ring(center, node_r - 3.5 * scale, node_r - 0.5 * scale, 220.0, 320.0, 20, rl.Color(255, 255, 255, 120))
      elif is_toggle and not is_on:
        # Resting muted rim when toggle is inactive
        rl.draw_ring(center, node_r - 2.5 * scale, node_r - 0.5 * scale, 0.0, 360.0, 40, rl.Color(68, 44, 112, 140))
        rl.draw_ring(center, node_r - 3.0 * scale, node_r, 0.0, 360.0, 40, rl.Color(161, 112, 255, 55))
      else:
        rl.draw_ring(center, node_r - 3.0 * scale, node_r, 0.0, 360.0, 40, accent)
        rl.draw_ring(center, node_r - 3.5 * scale, node_r - 0.5 * scale, 220.0, 320.0, 20, rl.Color(255, 255, 255, 75))

      # Center glyph / number
      if configured:
        num_color = self._TEXT if (not is_toggle or is_on) else rl.Color(213, 202, 232, 190)
        self._draw_centered_text(str(index + 1), center, int(48 * scale), self._font(bold=True), num_color)
      else:
        self._draw_centered_text("+", center, int(48 * scale), self._font(bold=True), self._TEXT)

      # 3. Label & Information Architecture in Blade
      text_x = center.x + node_r + 18.0 * scale
      max_text_w = (blade_rect.x + blade_rect.width - 18.0 * scale) - text_x

      if configured:
        if is_dropdown:
          title_text = str(slot.get("label") or slot.get("key") or "Favorite").replace('\\"', '"')
          fs_title = int(32 * scale)
          fs_sub = int(24 * scale)
          fitted_title = self._fit_text(self._font(bold=True), title_text, fs_title, max_text_w)
          self._draw_text(self._font(bold=True), fitted_title, rl.Vector2(text_x, center.y - 24.0 * scale), fs_title, self._TEXT)

          dim_val = self._measure_text(self._font(bold=False), active_label, fs_sub)
          self._draw_text(self._font(bold=False), active_label, rl.Vector2(text_x, center.y + 8.0 * scale), fs_sub, rl.Color(214, 192, 255, 240))

          # Hardware Capsule Pips
          pip_w = 14.0 * scale
          pip_h = 7.0 * scale
          pip_gap = 5.0 * scale
          pip_start_x = text_x + dim_val.x + 12.0 * scale
          for p in range(total_opts):
            pip_rect = rl.Rectangle(pip_start_x + p * (pip_w + pip_gap), center.y + 8.0 * scale + (dim_val.y - pip_h) / 2.0, pip_w, pip_h)
            if p == active_idx:
              rl.draw_rectangle_rounded(pip_rect, 0.4, 6, rl.Color(214, 192, 255, 255))
            else:
              rl.draw_rectangle_rounded(pip_rect, 0.4, 6, rl.Color(161, 112, 255, 75))
        elif is_toggle:
          raw_label = str(slot.get("label") or slot.get("key") or "Favorite").replace('\\"', '"')
          fs_title = int(32 * scale)
          fs_sub = int(24 * scale)
          fitted_title = self._fit_text(self._font(bold=True), raw_label, fs_title, max_text_w)
          self._draw_text(self._font(bold=True), fitted_title, rl.Vector2(text_x, center.y - 24.0 * scale), fs_title, self._TEXT)

          status_text = "ON" if is_on else "OFF"
          status_color = rl.Color(214, 192, 255, 255) if is_on else rl.Color(213, 202, 232, 160)
          self._draw_text(self._font(bold=True), status_text, rl.Vector2(text_x, center.y + 8.0 * scale), fs_sub, status_color)
        else:
          raw_label = str(slot.get("label") or slot.get("key") or "Favorite").replace('\\"', '"')
          label_font_size = int(34 * scale)
          text_dim = self._measure_text(self._font(bold=True), raw_label, label_font_size)

          if text_dim.x <= max_text_w:
            self._draw_text(self._font(bold=True), raw_label, rl.Vector2(text_x, center.y - text_dim.y / 2.0), label_font_size, self._TEXT)
          else:
            line1, line2 = self._semantic_split_label(raw_label, max_chars=18)
            if line2 is None:
              fitted_label = self._fit_text(self._font(bold=True), line1, label_font_size, max_text_w)
              dim = self._measure_text(self._font(bold=True), fitted_label, label_font_size)
              self._draw_text(self._font(bold=True), fitted_label, rl.Vector2(text_x, center.y - dim.y / 2.0), label_font_size, self._TEXT)
            else:
              fs_l1 = int(32 * scale)
              fs_l2 = int(24 * scale)
              fitted_l1 = self._fit_text(self._font(bold=True), line1, fs_l1, max_text_w)
              fitted_l2 = self._fit_text(self._font(bold=False), line2, fs_l2, max_text_w)
              dim1 = self._measure_text(self._font(bold=True), fitted_l1, fs_l1)
              dim2 = self._measure_text(self._font(bold=False), fitted_l2, fs_l2)
              total_h = dim1.y + dim2.y + 2.0 * scale
              start_y = center.y - total_h / 2.0
              self._draw_text(self._font(bold=True), fitted_l1, rl.Vector2(text_x, start_y), fs_l1, self._TEXT)
              self._draw_text(self._font(bold=False), fitted_l2, rl.Vector2(text_x, start_y + dim1.y + 2.0 * scale), fs_l2, rl.Color(214, 192, 255, 230))
      else:
        fs_title = int(32 * scale)
        fs_sub = int(24 * scale)
        title_text = f"Add Favorite {index + 1}"
        sub_text = "Tap to configure"
        dim_t = self._measure_text(self._font(bold=True), title_text, fs_title)
        dim_s = self._measure_text(self._font(bold=False), sub_text, fs_sub)
        total_h = dim_t.y + dim_s.y + 2.0 * scale
        start_y = center.y - total_h / 2.0
        self._draw_text(self._font(bold=True), title_text, rl.Vector2(text_x, start_y), fs_title, self._TEXT)
        self._draw_text(self._font(bold=False), sub_text, rl.Vector2(text_x, start_y + dim_t.y + 2.0 * scale), fs_sub, rl.Color(214, 192, 255, 230))

      # Wave flash animation
      if self._flash_slot == index:
        now = self._clock()
        dt = now - self._flash_start_time
        if 0.0 <= dt < 0.180:
          tau = max(0.0, min(1.0, dt / 0.180))
          ease = max(0.0, min(1.0, 1.0 - (1.0 - tau) ** 3))
          flash_a = int(180.0 * (1.0 - ease))
          flash_a = max(0, min(255, flash_a))
          if flash_a > 0 and ease > 0.01:
            rl.draw_ring(center, node_r, node_r + 24.0 * scale * ease, 0.0, 360.0, 32, rl.Color(214, 192, 255, flash_a))
        else:
          self._flash_slot = None

      # 4. Edit mode unassign badge on top-right corner of blade
      if self._editing_slot == index:
        badge_center = rl.Vector2(blade_rect.x + blade_rect.width - 2.0 * scale, blade_rect.y + 2.0 * scale)
        badge_r = 19.0 * scale
        rl.draw_circle_v(badge_center, badge_r + 4.0 * scale, rl.Color(255, 80, 110, 85))
        rl.draw_circle_v(badge_center, badge_r, rl.Color(198, 36, 62, 245))
        rl.draw_ring(badge_center, badge_r - 2.0 * scale, badge_r, 0, 360, 24, rl.Color(255, 145, 170, 235))
        hx = badge_r * 0.42
        rl.draw_line_ex(rl.Vector2(badge_center.x - hx, badge_center.y - hx),
                        rl.Vector2(badge_center.x + hx, badge_center.y + hx), 3.0 * scale, self._TEXT)
        rl.draw_line_ex(rl.Vector2(badge_center.x - hx, badge_center.y + hx),
                        rl.Vector2(badge_center.x + hx, badge_center.y - hx), 3.0 * scale, self._TEXT)

  def _draw_picker(self) -> None:
    scale = self._scale_for(self._rect)
    rl.draw_rectangle_rec(self._rect, rl.Color(4, 4, 10, 188))
    glow_rect = rl.Rectangle(
      self._drawer_rect.x - 12 * scale,
      self._drawer_rect.y - 12 * scale,
      self._drawer_rect.width + 24 * scale,
      self._drawer_rect.height + 24 * scale,
    )
    rl.draw_rectangle_rounded(glow_rect, self._roundness(glow_rect, 44 * scale), 16, rl.Color(*self._PURPLE, 28))
    rl.draw_rectangle_rounded(self._drawer_rect, self._roundness(self._drawer_rect, 34 * scale), 16, self._PANEL)
    rl.draw_rectangle_rounded_lines_ex(self._drawer_rect, self._roundness(self._drawer_rect, 34 * scale), 16,
                                       2 * scale, self._PANEL_BORDER)

    title = f"Assign Favorite {self._selected_slot + 1}" if self._selected_slot is not None else "Assign Favorite"
    title_pos = rl.Vector2(self._drawer_rect.x + 36 * scale, self._drawer_rect.y + 26 * scale)
    self._draw_text(self._font(bold=True), title, title_pos, int(50 * scale), self._TEXT)
    subtitle = "Set Speed: configure in New Galaxy"
    self._draw_text(
      self._font(bold=False), subtitle,
      rl.Vector2(title_pos.x, title_pos.y + 72 * scale), int(26 * scale), self._MUTED_TEXT,
    )

    self._draw_close_icon(self._drawer_close_rect, pressed=self._pressed_target == ("close", None))
    if not self._option_rects:
      empty_text = "No selectable favorites are available for this vehicle."
      self._draw_centered_text(
        empty_text,
        rl.Vector2(self._drawer_rect.x + self._drawer_rect.width / 2, self._drawer_rect.y + self._drawer_rect.height / 2),
        int(32 * scale), self._font(bold=False), self._MUTED_TEXT,
      )

    page_start = self._picker_page * self.PICKER_PAGE_SIZE
    for option_index, option_rect in self._option_rects:
      option = self._picker_options[option_index]
      self._draw_option_card(option_rect, option, scale,
                             pressed=self._pressed_target == ("option", option_index))

    self._draw_pager_button(
      self._drawer_prev_rect, "Previous", enabled=self._picker_page > 0, scale=scale,
      pressed=self._pressed_target == ("previous", None),
    )
    self._draw_pager_button(
      self._drawer_next_rect, "Next", enabled=self._has_next_picker_page, scale=scale,
      pressed=self._pressed_target == ("next", None),
    )
    first_option = page_start + 1 if self._picker_options else 0
    last_option = min(page_start + self.PICKER_PAGE_SIZE, len(self._picker_options))
    page_label = f"{first_option}–{last_option} of {len(self._picker_options)}"
    self._draw_centered_text(
      page_label,
      rl.Vector2(self._drawer_rect.x + self._drawer_rect.width / 2,
                 self._drawer_prev_rect.y + self._drawer_prev_rect.height / 2),
      int(26 * scale), self._font(bold=False), self._MUTED_TEXT,
    )

  def _draw_option_card(self, rect: rl.Rectangle, option: dict[str, Any], scale: float, *, pressed: bool = False) -> None:
    card_fill = rl.Color(43, 34, 62, 250) if pressed else rl.Color(27, 23, 40, 246)
    card_border = rl.Color(214, 192, 255, 220) if pressed else rl.Color(*self._PURPLE, 116)
    rl.draw_rectangle_rounded(rect, self._roundness(rect, 22 * scale), 12, card_fill)
    rl.draw_rectangle_rounded_lines_ex(rect, self._roundness(rect, 22 * scale), 12, 1.5 * scale,
                                       card_border)
    padding = self.PICKER_CARD_PADDING * scale

    key = str(option.get("key") or "")
    ui_type = str(option.get("ui_type") or "")
    raw_options = option.get("options")
    is_act = is_favorite_action_key(key)
    is_drop = (ui_type == "dropdown" and isinstance(raw_options, list) and len(raw_options) >= 2)

    if is_act:
      badge_label = "ACTION"
    elif is_drop:
      badge_label = f"{len(raw_options)} STATES"
    else:
      badge_label = "TOGGLE"

    badge_fs = int(18 * scale)
    badge_dim = self._measure_text(self._font(bold=True), badge_label, badge_fs)
    badge_pad_h = 10.0 * scale
    badge_pad_v = 5.0 * scale
    badge_w = badge_dim.x + badge_pad_h * 2.0
    badge_h = badge_dim.y + badge_pad_v * 2.0
    badge_x = rect.x + rect.width - padding - badge_w
    badge_y = rect.y + 20.0 * scale
    badge_rect = rl.Rectangle(badge_x, badge_y, badge_w, badge_h)

    badge_fill = rl.Color(68, 44, 112, 180) if (is_act or is_drop) else rl.Color(42, 28, 70, 180)
    badge_border = rl.Color(214, 192, 255, 140) if (is_act or is_drop) else rl.Color(161, 112, 255, 100)
    badge_text_col = rl.Color(214, 192, 255, 230) if (is_act or is_drop) else rl.Color(200, 172, 255, 200)

    rl.draw_rectangle_rounded(badge_rect, 0.45, 6, badge_fill)
    rl.draw_rectangle_rounded_lines_ex(badge_rect, 0.45, 6, 1.2 * scale, badge_border)
    self._draw_centered_text(
      badge_label,
      rl.Vector2(badge_x + badge_w / 2.0, badge_y + badge_h / 2.0),
      badge_fs,
      self._font(bold=True),
      badge_text_col,
    )

    content_w = rect.width - 2 * padding
    section_max_w = content_w - badge_w - 12.0 * scale
    section = self._fit_picker_text(self._font(bold=False), self._picker_section_label(option), int(22 * scale), section_max_w)
    self._draw_text(self._font(bold=False), section, rl.Vector2(rect.x + padding, rect.y + 24 * scale),
                    int(22 * scale), rl.Color(200, 172, 255, 214))

    raw_label = str(option.get("picker_label") or option.get("label") or option.get("key") or "Favorite").replace('\\"', '"')
    title_fs = int(36 * scale)
    title_dim = self._measure_text(self._font(bold=True), raw_label, title_fs)
    if title_dim.x <= content_w:
      self._draw_text(self._font(bold=True), raw_label, rl.Vector2(rect.x + padding, rect.y + 84 * scale),
                      title_fs, self._TEXT)
    else:
      title_lines = self._wrap_picker_text(self._font(bold=True), raw_label, title_fs, content_w)
      if len(title_lines) <= 1:
        fitted = self._fit_picker_text(self._font(bold=True), title_lines[0] if title_lines else raw_label, title_fs, content_w)
        self._draw_text(self._font(bold=True), fitted, rl.Vector2(rect.x + padding, rect.y + 84 * scale),
                        title_fs, self._TEXT)
      else:
        fs_l1 = int(34 * scale)
        fs_l2 = int(30 * scale)
        f_l1 = self._fit_picker_text(self._font(bold=True), title_lines[0], fs_l1, content_w)
        f_l2 = self._fit_picker_text(self._font(bold=True), title_lines[1], fs_l2, content_w)
        self._draw_text(self._font(bold=True), f_l1, rl.Vector2(rect.x + padding, rect.y + 76 * scale), fs_l1, self._TEXT)
        self._draw_text(self._font(bold=True), f_l2, rl.Vector2(rect.x + padding, rect.y + 118 * scale), fs_l2, rl.Color(255, 255, 255, 235))

    raw_desc = str(option.get("picker_description") or option.get("description") or "").replace('\\"', '"')
    desc_fs = int(26 * scale)
    if raw_desc:
      desc_font = self._font(bold=False)
      description_lines = self._wrap_picker_text(desc_font, raw_desc, desc_fs, content_w)
      desc_dim = self._measure_text(desc_font, "Ag", desc_fs)
      line_step = max(36.0 * scale, desc_dim.y + 8.0 * scale)
      last_y = rect.y + rect.height - padding - desc_dim.y
      first_y = last_y - line_step * (len(description_lines) - 1)
      for line_index, description_line in enumerate(description_lines):
        self._draw_text(
          desc_font,
          description_line,
          rl.Vector2(rect.x + padding, first_y + line_index * line_step),
          desc_fs,
          self._MUTED_TEXT,
        )

  def _draw_close_icon(self, rect: rl.Rectangle, *, pressed: bool = False) -> None:
    scale = self._scale_for(self._rect)
    background_alpha = 46 if pressed else 22
    rl.draw_rectangle_rounded(rect, self._roundness(rect, 18 * scale), 10, rl.Color(255, 255, 255, background_alpha))
    center = rl.Vector2(rect.x + rect.width / 2, rect.y + rect.height / 2)
    half = rect.width * 0.22
    color = rl.Color(255, 255, 255, 250 if pressed else 230)
    rl.draw_line_ex(rl.Vector2(center.x - half, center.y - half), rl.Vector2(center.x + half, center.y + half), 4.5 * scale, color)
    rl.draw_line_ex(rl.Vector2(center.x - half, center.y + half), rl.Vector2(center.x + half, center.y - half), 4.5 * scale, color)

  def _draw_pager_button(self, rect: rl.Rectangle, label: str, *, enabled: bool, scale: float,
                         pressed: bool = False) -> None:
    fill = rl.Color(94, 64, 148, 238) if pressed and enabled else (
      rl.Color(68, 44, 112, 225) if enabled else rl.Color(255, 255, 255, 14)
    )
    border = rl.Color(*self._PURPLE, 220 if pressed and enabled else (180 if enabled else 42))
    text_color = self._TEXT if enabled else rl.Color(255, 255, 255, 88)
    rl.draw_rectangle_rounded(rect, self._roundness(rect, 20 * scale), 10, fill)
    rl.draw_rectangle_rounded_lines_ex(rect, self._roundness(rect, 20 * scale), 10, 1.8 * scale, border)
    self._draw_centered_text(label, rl.Vector2(rect.x + rect.width / 2, rect.y + rect.height / 2),
                             int(28 * scale), self._font(bold=True), text_color)

  @staticmethod
  def _fit_text(font: Any, text: str, font_size: int, max_width: float) -> str:
    if max_width <= 0:
      return ""
    if FavoriteRadialMenu._measure_text(font, text, font_size).x <= max_width:
      return text
    ellipsis = FavoriteRadialMenu._ELLIPSIS
    if FavoriteRadialMenu._measure_text(font, ellipsis, font_size).x > max_width:
      return ""
    shortened = text
    while shortened and FavoriteRadialMenu._measure_text(font, f"{shortened}{ellipsis}", font_size).x > max_width:
      shortened = shortened[:-1]
    return f"{shortened}{ellipsis}" if shortened else ellipsis

  @staticmethod
  def _fit_picker_text(font: Any, text: str, font_size: int, max_width: float) -> str:
    if max_width <= 0:
      return ""
    if FavoriteRadialMenu._measure_text(font, text, font_size).x <= max_width:
      return text
    return FavoriteRadialMenu._append_ellipsis(font, text, font_size, max_width)

  @staticmethod
  def _append_ellipsis(font: Any, text: str, font_size: int, max_width: float) -> str:
    ellipsis = FavoriteRadialMenu._ELLIPSIS
    if max_width <= 0 or FavoriteRadialMenu._measure_text(font, ellipsis, font_size).x > max_width:
      return ""

    words = text.strip().rstrip(".…").split()
    while words:
      shortened = " ".join(words)
      if FavoriteRadialMenu._measure_text(font, f"{shortened}{ellipsis}", font_size).x <= max_width:
        return f"{shortened}{ellipsis}"
      words.pop()
    return ellipsis

  @staticmethod
  def _draw_centered_text(text: str, center: rl.Vector2, font_size: int, font: Any, color: rl.Color) -> None:
    size = FavoriteRadialMenu._measure_text(font, text, font_size)
    FavoriteRadialMenu._draw_text(font, text, rl.Vector2(center.x - size.x / 2, center.y - size.y / 2), font_size, color)
