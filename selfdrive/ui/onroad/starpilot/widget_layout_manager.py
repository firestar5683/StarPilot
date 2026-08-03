import pyray as rl
from openpilot.selfdrive.ui.onroad.starpilot.widgets.base import LayoutWidget

class WidgetLayoutManager:
  def __init__(self, content_rect: rl.Rectangle):
    self.content_rect = content_rect
    self.zones = {
      "left": [],
      "bottom": [],
      "right": []
    }
    self.spacing = 15  # Spacing between widgets

  def register_widget(self, zone: str, widget: LayoutWidget):
    """Register a widget in a specific zone."""
    self.zones[zone].append(widget)
    self.zones[zone].sort(key=lambda w: w.priority)

  def update_layout(self, content_rect: rl.Rectangle, is_rhd: bool = False):
    """Calculate and apply positions of all active widgets in all zones."""
    self.content_rect = content_rect
    self._layout_left()
    self._layout_bottom(is_rhd)
    self._layout_right()

  def _layout_left(self):
    active_widgets = [w for w in self.zones["left"] if w.is_visible]

    # Left zone stacks vertically from the top-left offset
    # X anchor is set speed box center (around 160 pixels from left edge)
    center_x = self.content_rect.x + 60 + 172 // 2  # default set_speed center
    current_y = self.content_rect.y + 45

    for widget in active_widgets:
      w, h = widget.get_size()
      widget.set_rect(rl.Rectangle(center_x - w / 2, current_y, w, h))
      current_y += h + self.spacing

  def _layout_bottom(self, is_rhd: bool):
    active_widgets = [w for w in self.zones["bottom"] if w.is_visible]
    if not active_widgets:
      return

    # Total width of active widgets including spacing
    total_w = sum(w.get_size()[0] for w in active_widgets) + self.spacing * (len(active_widgets) - 1)
    bottom_y = self.content_rect.y + self.content_rect.height - 146

    if not is_rhd:
      # LHD: stack from left to right starting at x = 146
      current_x = self.content_rect.x + 146
      for widget in active_widgets:
        w, h = widget.get_size()
        widget.set_rect(rl.Rectangle(current_x - w / 2, bottom_y - h / 2, w, h))
        current_x += w + self.spacing
    else:
      # RHD: stack from left to right starting such that the last widget is at width - 146
      current_x = self.content_rect.x + self.content_rect.width - 146 - (total_w - active_widgets[-1].get_size()[0])
      for widget in active_widgets:
        w, h = widget.get_size()
        widget.set_rect(rl.Rectangle(current_x - w / 2, bottom_y - h / 2, w, h))
        current_x += w + self.spacing

  def _layout_right(self):
    active_widgets = [w for w in self.zones["right"] if w.is_visible]
    center_x = self.content_rect.x + self.content_rect.width - 146
    current_y = self.content_rect.y + 45
    for widget in active_widgets:
      w, h = widget.get_size()
      widget.set_rect(rl.Rectangle(center_x - w / 2, current_y, w, h))
      current_y += h + self.spacing

  def render_widgets(self, exclude: set[str] | None = None):
    """Render all visible registered widgets in their layout positions."""
    skip = exclude or set()
    for zone in self.zones.values():
      for widget in zone:
        if widget.is_visible and widget.name not in skip:
          widget.render(widget.rect)
