from __future__ import annotations
import pyray as rl
from collections.abc import Callable
from openpilot.system.ui.lib.application import gui_app, FontWeight, MousePos
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget, DialogResult

def hex_to_color(hex_str: str) -> rl.Color:
  hex_str = hex_str.lstrip('#')
  return rl.Color(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16), 255)

class MetroTile(Widget):
  def __init__(self, bg_color: rl.Color | str = rl.Color(54, 77, 239, 255), on_click: Callable | None = None):
    super().__init__()
    self.bg_color = hex_to_color(bg_color) if isinstance(bg_color, str) else bg_color
    self.on_click = on_click
    self._is_pressed = False

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if rl.check_collision_point_rec(mouse_pos, self._rect):
      self._is_pressed = True

  def _handle_mouse_release(self, mouse_pos: MousePos):
    if self._is_pressed:
      if rl.check_collision_point_rec(mouse_pos, self._rect) and self.on_click:
        self.on_click()
      self._is_pressed = False

  def _draw_text_fit(self, font: rl.Font, text: str, pos: rl.Vector2, max_width: float, font_size: float, align_right: bool = False):
    """Draws text scaled down to fit within max_width if necessary."""
    size = measure_text_cached(font, text, int(font_size))
    actual_font_size = font_size
    if size.x > max_width:
      actual_font_size = font_size * (max_width / size.x)
      render_width = max_width
    else:
      render_width = size.x
    
    nudge_y = (font_size - actual_font_size) / 2
    draw_x = pos.x
    if align_right:
      draw_x = pos.x + max_width - render_width
      
    rl.draw_text_ex(font, text, rl.Vector2(draw_x, pos.y + nudge_y), actual_font_size, 0, rl.WHITE)

  def _draw_watermark(self, rect: rl.Rectangle, icon: rl.Texture2D | None):
    if not icon:
      return
    rl.begin_scissor_mode(int(rect.x), int(rect.y), int(rect.width), int(rect.height))
    w_scale = 1.6 
    iw, ih = icon.width * w_scale, icon.height * w_scale
    ix = rect.x + rect.width - iw - 15
    iy = rect.y + rect.height - ih - 15
    rl.draw_texture_pro(icon, rl.Rectangle(0, 0, icon.width, icon.height), rl.Rectangle(ix, iy, iw, ih), rl.Vector2(0, 0), 0, rl.Color(255, 255, 255, 80))
    rl.end_scissor_mode()

  def _render(self, rect: rl.Rectangle):
    pass


class HubTile(MetroTile):
  def __init__(self, title: str, desc: str, icon_path: str, on_click: Callable | None = None, starpilot_icon: bool = False, bg_color: rl.Color | str | None = None):
    if bg_color:
      super().__init__(bg_color=bg_color, on_click=on_click)
    else:
      super().__init__(on_click=on_click)
    self.title = title
    self.desc = desc
    if icon_path:
      if starpilot_icon: self._icon = gui_app.starpilot_texture(icon_path, 100, 100)
      else: self._icon = gui_app.texture(icon_path, 100, 100)
    else: self._icon = None
    self._font_title = gui_app.font(FontWeight.BOLD)
    self._font_desc = gui_app.font(FontWeight.NORMAL)

  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)
    r, g, b = max(0, self.bg_color.r - 20), max(0, self.bg_color.g - 20), max(0, self.bg_color.b - 20)
    color = rl.Color(r, g, b, 255) if self._is_pressed else self.bg_color
    rl.draw_rectangle_rounded(rect, 0.15, 10, color)
    self._draw_watermark(rect, self._icon)
    padding = 30
    if self._icon:
      siw, sih = self._icon.width * 0.45, self._icon.height * 0.45
      rl.draw_texture_pro(self._icon, rl.Rectangle(0, 0, self._icon.width, self._icon.height), rl.Rectangle(rect.x + padding, rect.y + padding, siw, sih), rl.Vector2(0, 0), 0, rl.WHITE)
    title_x = rect.x + padding + (65 if self._icon else 0)
    max_title_width = rect.width - (title_x - rect.x) - padding
    self._draw_text_fit(self._font_title, self.title, rl.Vector2(title_x, rect.y + padding + 3), max_title_width, 42)


class ToggleTile(MetroTile):
  def __init__(self, title: str, get_state: Callable[[], bool], set_state: Callable[[bool], None], icon_path: str | None = None, bg_color: rl.Color | str | None = None):
    if bg_color: super().__init__(bg_color=bg_color)
    else: super().__init__(bg_color=rl.Color(0, 163, 0, 255))
    self.title = title
    self.get_state = get_state
    self.set_state = set_state
    self._icon = gui_app.starpilot_texture(icon_path, 80, 80) if icon_path else None
    self._font = gui_app.font(FontWeight.BOLD)
    self._active_color = self.bg_color
    self._inactive_color = rl.Color(120, 120, 120, 255)

  def _handle_mouse_release(self, mouse_pos: MousePos):
    if self._is_pressed:
      if rl.check_collision_point_rec(mouse_pos, self._rect):
        self.set_state(not self.get_state())
      self._is_pressed = False

  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)
    active = self.get_state()
    base_color = self._active_color if active else self._inactive_color
    r, g, b = max(0, base_color.r - 20), max(0, base_color.g - 20), max(0, base_color.b - 20)
    color = rl.Color(r, g, b, 255) if self._is_pressed else base_color
    rl.draw_rectangle_rounded(rect, 0.15, 10, color)
    self._draw_watermark(rect, self._icon)
    padding = 25
    if self._icon:
      siw, sih = self._icon.width * 0.45, self._icon.height * 0.45
      rl.draw_texture_pro(self._icon, rl.Rectangle(0, 0, self._icon.width, self._icon.height), rl.Rectangle(rect.x + padding, rect.y + padding, siw, sih), rl.Vector2(0, 0), 0, rl.WHITE)
    title_x = rect.x + padding + (55 if self._icon else 0)
    max_title_width = rect.width - (title_x - rect.x) - padding
    self._draw_text_fit(self._font, self.title, rl.Vector2(title_x, rect.y + padding + 2), max_title_width, 35)
    state_text = tr("ON") if active else tr("OFF")
    ts = measure_text_cached(self._font, state_text, 30)
    rl.draw_text_ex(self._font, state_text, rl.Vector2(rect.x + rect.width - ts.x - padding, rect.y + rect.height - 50), 30, 0, rl.WHITE)


class ValueTile(MetroTile):
  def __init__(self, title: str, get_value: Callable[[], str], on_click: Callable, icon_path: str | None = None, bg_color: rl.Color | str | None = None):
    super().__init__(bg_color=bg_color, on_click=on_click)
    self.title = title
    self.get_value = get_value
    self._icon = gui_app.starpilot_texture(icon_path, 80, 80) if icon_path else None
    self._font = gui_app.font(FontWeight.BOLD)

  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)
    r, g, b = max(0, self.bg_color.r - 20), max(0, self.bg_color.g - 20), max(0, self.bg_color.b - 20)
    color = rl.Color(r, g, b, 255) if self._is_pressed else self.bg_color
    rl.draw_rectangle_rounded(rect, 0.15, 10, color)
    self._draw_watermark(rect, self._icon)
    padding = 25
    if self._icon:
      siw, sih = self._icon.width * 0.45, self._icon.height * 0.45
      rl.draw_texture_pro(self._icon, rl.Rectangle(0, 0, self._icon.width, self._icon.height), rl.Rectangle(rect.x + padding, rect.y + padding, siw, sih), rl.Vector2(0, 0), 0, rl.WHITE)
    title_x = rect.x + padding + (55 if self._icon else 0)
    max_title_width = rect.width - (title_x - rect.x) - padding
    self._draw_text_fit(self._font, self.title, rl.Vector2(title_x, rect.y + padding + 2), max_title_width, 35)
    
    val_text = self.get_value()
    # Bottom value: scale to fit if it's too long (common for Car Models)
    max_val_width = rect.width - 2 * padding
    val_pos = rl.Vector2(rect.x + padding, rect.y + rect.height - 55)
    self._draw_text_fit(self._font, val_text, val_pos, max_val_width, 35, align_right=True)


class MetroSlider(Widget):
  def __init__(self, min_val: float, max_val: float, step: float, current_val: float, on_change: Callable[[float], None], unit: str = "", labels: dict[float, str] | None = None, color: rl.Color = rl.Color(54, 77, 239, 255)):
    super().__init__()
    self.min_val, self.max_val, self.step, self.current_val = min_val, max_val, step, current_val
    self.on_change, self.unit, self.labels, self.color = on_change, unit, labels or {}, color
    self._is_dragging = False
    self._font = gui_app.font(FontWeight.BOLD)

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if rl.check_collision_point_rec(mouse_pos, self._rect):
      self._is_dragging = True
      self._update_val_from_mouse(mouse_pos)

  def _handle_mouse_release(self, mouse_pos: MousePos):
    self._is_dragging = False

  def _update_val_from_mouse(self, mouse_pos: MousePos):
    rel_x = max(0, min(1, (mouse_pos.x - self._rect.x) / self._rect.width))
    val = self.min_val + rel_x * (self.max_val - self.min_val)
    snapped = max(self.min_val, min(self.max_val, self.min_val + round((val - self.min_val) / self.step) * self.step))
    if snapped != self.current_val:
      self.current_val = snapped
      self.on_change(self.current_val)

  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)
    if self._is_dragging: self._update_val_from_mouse(rl.get_mouse_position())
    track_h = 20
    track_rect = rl.Rectangle(rect.x, rect.y + (rect.height - track_h) / 2, rect.width, track_h)
    rl.draw_rectangle_rounded(track_rect, 1.0, 10, rl.Color(60, 60, 60, 255))
    fill_w = ((self.current_val - self.min_val) / (self.max_val - self.min_val)) * rect.width
    rl.draw_rectangle_rounded(rl.Rectangle(rect.x, rect.y + (rect.height - track_h) / 2, fill_w, track_h), 1.0, 10, self.color)
    thumb_w, thumb_h = 40, 60
    thumb_x, thumb_y = rect.x + fill_w - thumb_w / 2, rect.y + (rect.height - thumb_h) / 2
    rl.draw_rectangle_rounded(rl.Rectangle(thumb_x, thumb_y, thumb_w, thumb_h), 0.2, 10, rl.WHITE)
    val_str = self.labels.get(self.current_val, f"{self.current_val:.2f}".rstrip('0').rstrip('.') + self.unit)
    ts = measure_text_cached(self._font, val_str, 35)
    rl.draw_text_ex(self._font, val_str, rl.Vector2(thumb_x + (thumb_w - ts.x) / 2, thumb_y - 45), 35, 0, rl.WHITE)


class SliderDialog(Widget):
  def __init__(self, title: str, min_val: float, max_val: float, step: float, current_val: float, on_close: Callable, unit: str = "", labels: dict[float, str] | None = None, color: rl.Color | str = "#FF0097"):
    super().__init__()
    self.title, self._user_callback = title, on_close
    self._color = hex_to_color(color) if isinstance(color, str) else color
    self._font_title, self._font_btn = gui_app.font(FontWeight.BOLD), gui_app.font(FontWeight.BOLD)
    self._slider = MetroSlider(min_val, max_val, step, current_val, self._on_slider_change, unit, labels, self._color)
    self._current_val, self._is_pressed_ok, self._is_pressed_cancel = current_val, False, False

  def _on_slider_change(self, val):
    self._current_val = val

  def _handle_mouse_press(self, mouse_pos: MousePos):
    self._slider._handle_mouse_press(mouse_pos)
    if rl.check_collision_point_rec(mouse_pos, self._ok_rect): self._is_pressed_ok = True
    if rl.check_collision_point_rec(mouse_pos, self._cancel_rect): self._is_pressed_cancel = True

  def _handle_mouse_release(self, mouse_pos: MousePos):
    self._slider._handle_mouse_release(mouse_pos)
    if self._is_pressed_ok:
      if rl.check_collision_point_rec(mouse_pos, self._ok_rect):
        self._user_callback(DialogResult.CONFIRM, self._current_val)
        gui_app.set_modal_overlay(None)
      self._is_pressed_ok = False
    if self._is_pressed_cancel:
      if rl.check_collision_point_rec(mouse_pos, self._cancel_rect):
        self._user_callback(DialogResult.CANCEL, self._current_val)
        gui_app.set_modal_overlay(None)
      self._is_pressed_cancel = False

  def _render(self, rect: rl.Rectangle):
    rl.draw_rectangle(0, 0, gui_app.width, gui_app.height, rl.Color(0, 0, 0, 160))
    dialog_w, dialog_h = 1000, 500
    dx, dy = rect.x + (rect.width - dialog_w) / 2, rect.y + (rect.height - dialog_h) / 2
    self._ok_rect = rl.Rectangle(dx + dialog_w - 450, dy + dialog_h - 120, 350, 80)
    self._cancel_rect = rl.Rectangle(dx + 100, dy + dialog_h - 120, 350, 80)
    
    d_rect = rl.Rectangle(dx, dy, dialog_w, dialog_h)
    rl.draw_rectangle_rounded(d_rect, 0.05, 10, rl.Color(30, 30, 30, 255))
    rl.draw_rectangle_rounded_lines(d_rect, 0.05, 10, self._color)
    ts = measure_text_cached(self._font_title, self.title, 50)
    rl.draw_text_ex(self._font_title, self.title, rl.Vector2(dx + (dialog_w - ts.x) / 2, dy + 40), 50, 0, rl.WHITE)
    
    slider_rect = rl.Rectangle(dx + 100, dy + 200, dialog_w - 200, 100)
    self._slider.render(slider_rect)
    
    # Cancel Button
    c_color = rl.Color(60, 60, 60, 255) if not self._is_pressed_cancel else rl.Color(40, 40, 40, 255)
    rl.draw_rectangle_rounded(self._cancel_rect, 0.2, 10, c_color)
    cts = measure_text_cached(self._font_btn, tr("CANCEL"), 35)
    rl.draw_text_ex(self._font_btn, tr("CANCEL"), rl.Vector2(self._cancel_rect.x + (350 - cts.x) / 2, self._cancel_rect.y + (80 - cts.y) / 2), 35, 0, rl.WHITE)
    
    # OK Button
    ok_color = self._color if not self._is_pressed_ok else rl.Color(max(0, self._color.r-40), max(0, self._color.g-40), max(0, self._color.b-40), 255)
    rl.draw_rectangle_rounded(self._ok_rect, 0.2, 10, ok_color)
    ots = measure_text_cached(self._font_btn, tr("OK"), 35)
    rl.draw_text_ex(self._font_btn, tr("OK"), rl.Vector2(self._ok_rect.x + (350 - ots.x) / 2, self._ok_rect.y + (80 - ots.y) / 2), 35, 0, rl.WHITE)
    
    return DialogResult.NO_ACTION


class RadioTileGroup(Widget):
  def __init__(self, title: str, options: list[str], current_index: int, on_change: Callable):
    super().__init__()
    self.title, self.options, self.current_index, self.on_change = title, options, current_index, on_change
    self._font, self._font_title = gui_app.font(FontWeight.BOLD), gui_app.font(FontWeight.NORMAL)
    self._bg_color, self._active_color, self._inactive_color = rl.Color(41, 41, 41, 255), rl.Color(54, 77, 239, 255), rl.Color(80, 80, 80, 255)
    self._pressed_index, self._option_rects = -1, []

  def set_index(self, index: int): self.current_index = index

  def _handle_mouse_press(self, mouse_pos: MousePos):
    for i, r in enumerate(self._option_rects):
      if rl.check_collision_point_rec(mouse_pos, r): self._pressed_index = i; return

  def _handle_mouse_release(self, mouse_pos: MousePos):
    if self._pressed_index != -1:
      if rl.check_collision_point_rec(mouse_pos, self._option_rects[self._pressed_index]):
        if self.current_index != self._pressed_index: self.current_index = self._pressed_index; self.on_change(self.current_index)
      self._pressed_index = -1

  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)
    self._option_rects.clear()
    title_size = measure_text_cached(self._font_title, self.title, 40)
    rl.draw_text_ex(self._font_title, self.title, rl.Vector2(rect.x, rect.y + (rect.height - title_size.y) / 2), 40, 0, rl.WHITE)
    padding, option_w = 20, 200
    start_x = rect.x + rect.width - (len(self.options) * (option_w + padding))
    for i, opt in enumerate(self.options):
      r = rl.Rectangle(start_x + i * (option_w + padding), rect.y, option_w, rect.height)
      self._option_rects.append(r)
      is_active = i == self.current_index
      color = self._active_color if is_active else self._inactive_color
      if i == self._pressed_index: color = rl.Color(max(0, color.r-20), max(0, color.g-20), max(0, color.b-20), 255)
      rl.draw_rectangle_rounded(r, 0.15, 10, color)
      ts = measure_text_cached(self._font, opt, 35)
      rl.draw_text_ex(self._font, opt, rl.Vector2(r.x + (r.width - ts.x) / 2, r.y + (r.height - ts.y) / 2), 35, 0, rl.WHITE)


class TileGrid(Widget):
  def __init__(self, columns: int | None = None, padding: int = 20):
    super().__init__()
    self._columns, self.padding, self.tiles = columns, padding, []
  def add_tile(self, tile: Widget): self.tiles.append(tile)
  def clear(self): self.tiles.clear()
  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)
    if not self.tiles: return
    
    # Snapshot the tiles list to prevent IndexError if on_click modifies self.tiles mid-loop
    tiles_to_render = list(self.tiles)
    count = len(tiles_to_render)
    
    if self._columns is not None: cols = self._columns
    else:
      if count == 1: cols = 1
      elif count == 2: cols = 2
      elif count == 3: cols = 3
      elif count == 4: cols = 2
      elif count <= 6: cols = 3
      else: cols = 4
    rows = (count + cols - 1) // cols
    tile_h = (rect.height - (self.padding * (rows - 1))) / rows
    
    tile_idx = 0
    for r in range(rows):
      remaining = count - tile_idx
      if remaining <= 0: break
      items_in_row = min(cols, remaining)
      row_tile_w = (rect.width - (self.padding * (items_in_row - 1))) / items_in_row
      for c in range(items_in_row):
        tile = tiles_to_render[tile_idx]
        tile.render(rl.Rectangle(rect.x + c * (row_tile_w + self.padding), rect.y + r * (tile_h + self.padding), row_tile_w, tile_h))
        tile_idx += 1
