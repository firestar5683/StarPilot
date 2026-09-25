"""Native Quick Select gestures and presentation over supplied owner snapshots."""

from dataclasses import dataclass
import math
from collections.abc import Callable

import pyray as rl

from openpilot.starpilot.ui.appearance_preferences import CameraViewChoice
from openpilot.starpilot.ui.onroad_state import AlertSize
from openpilot.starpilot.ui.presentation import FontRole, Profile


@dataclass(frozen=True)
class FavoriteRequest:
  kind: str
  index: int
  key: str | None
  revision: str


class OnroadFavorites:
  def __init__(self, fonts, emit: Callable[[FavoriteRequest], bool]):
    self.fonts = fonts
    self.profile = fonts.profile
    self.emit = emit
    self.data = {"revision": "", "slots": [], "options": []}
    self.mode = "collapsed"
    self.selected = None
    self.editing = None
    self.page = 0
    self.press_target = None
    self.press_pos = None
    self.press_time = 0.0
    self.max_travel = 0.0
    self.last_interaction = 0.0
    self.last_activation = {}
    self.feedback = None
    self.feedback_text = ("", "")
    self.feedback_at = 0.0
    self.enabled = False
    self.rect = (30, 30, 1800, 1020) if self.profile == Profile.LARGE else (0, 0, 476, 240)

  @property
  def is_open(self):
    return self.mode != "collapsed"

  @property
  def scale(self):
    return max(0.35, min(self.rect[2] / 2160, self.rect[3] / 1080))

  def update(self, state, data, now):
    changed = data.get("revision") != self.data.get("revision")
    self.data = data
    camera = state.appearance.camera_view
    self.enabled = state.camera_available and state.alert.size == AlertSize.NONE
    if self.profile == Profile.COMPACT:
      self.enabled = self.enabled and (camera in (CameraViewChoice.NONE, CameraViewChoice.DRIVER) or
                                      not getattr(state, "reversing", False))
    if not self.enabled:
      self.cancel()
    elif changed:
      self.press_target, self.press_pos = None, None
    if self.is_open and now - self.last_interaction >= (30 if self.mode == "picker" else 6):
      self.cancel()
    if (self.press_target and self.press_target[0] == "slot" and self.profile == Profile.LARGE and
        self.mode == "radial" and now - self.press_time >= 0.60 and self.configured(self.press_target[1])):
      self.editing = self.press_target[1]

  def cancel(self):
    self.mode = "collapsed"
    self.selected = None
    self.editing = None
    self.press_target = None
    self.press_pos = None
    self.max_travel = 0.0
    self.feedback = None

  def slots(self):
    return self.data.get("slots", [])

  def configured(self, index):
    slots = self.slots()
    return index < len(slots) and bool(slots[index].get("enabled") and slots[index].get("show_onroad") and slots[index].get("key"))

  def corner(self):
    x, y, _, height = self.rect
    size = 180 * self.scale
    return x, y + height - size, size, size

  def blades(self):
    x, y, _, height = self.rect
    s = self.scale
    origin = (x + 48 * s, y + height - 48 * s)
    result = []
    for angle in (66, 40, 18):
      cx = origin[0] + math.cos(math.radians(angle)) * 515 * s
      cy = origin[1] - math.sin(math.radians(angle)) * 515 * s
      result.append(((cx - 52 * s, cy - 52 * s, 450 * s, 104 * s), (cx, cy)))
    return result

  def picker_geometry(self):
    x, y, width, height = self.rect
    s = self.scale
    panel = (x + 76 * s, y + 66 * s, width - 152 * s, height - 132 * s)
    px, py, pw, ph = panel
    close = (px + pw - 186 * s, py, 150 * s, 152 * s)
    grid_w, grid_h = pw - 72 * s, ph - (152 + 168 + 36) * s
    cw, ch = (grid_w - 72 * s) / 4, (grid_h - 24 * s) / 2
    cells = [(px + 36 * s + col * (cw + 24 * s), py + 170 * s + row * (ch + 24 * s), cw, ch)
             for row in range(2) for col in range(4)]
    cy = py + ph - 168 * s + 36 * s
    nxt = (px + pw - 236 * s, cy, 200 * s, 96 * s)
    prev = (nxt[0] - 224 * s, cy, 200 * s, 96 * s)
    return panel, close, cells, prev, nxt

  @staticmethod
  def contains(rect, x, y):
    return rect[0] <= x <= rect[0] + rect[2] and rect[1] <= y <= rect[1] + rect[3]

  def target_at(self, x, y):
    if self.profile == Profile.COMPACT:
      if not self.contains(self.rect, x, y):
        return None
      index = min(2, int((x - self.rect[0]) / (self.rect[2] / 3)))
      return ("slot", index) if self.configured(index) else None
    if self.mode == "collapsed":
      return ("corner", None) if self.contains(self.corner(), x, y) else None
    if self.mode == "picker":
      _, close, cells, prev, nxt = self.picker_geometry()
      if self.contains(close, x, y):
        return "close", None
      for kind, rect in (("previous", prev), ("next", nxt)):
        if self.contains((rect[0] - 10 * self.scale, rect[1] - 28 * self.scale,
                          rect[2] + 20 * self.scale, rect[3] + 56 * self.scale), x, y):
          return kind, None
      for index, cell in enumerate(cells):
        option = self.page * 8 + index
        if option < len(self.data.get("options", [])) and self.contains(cell, x, y):
          return "option", option
      return None
    for index, (blade, _) in enumerate(self.blades()):
      if self.editing == index:
        cx, cy = blade[0] + blade[2] - 2 * self.scale, blade[1] + 2 * self.scale
        if self.contains((cx - 32 * self.scale, cy - 32 * self.scale, 64 * self.scale, 64 * self.scale), x, y):
          return "unassign", index
      if self.contains((blade[0] - 12 * self.scale, blade[1] - 8 * self.scale,
                        blade[2] + 24 * self.scale, blade[3] + 16 * self.scale), x, y):
        return "slot", index
    return None

  def press(self, x, y, now):
    if not self.enabled:
      return False
    self.press_target = self.target_at(x, y)
    if self.press_target is None and not self.is_open:
      return False
    self.press_pos, self.press_time = (x, y), now
    self.max_travel = 0.0
    self.last_interaction = now
    if self.profile == Profile.COMPACT:
      self.feedback = None
    return True

  def move(self, x, y):
    if self.press_pos is not None:
      self.max_travel = max(self.max_travel, math.hypot(x - self.press_pos[0], y - self.press_pos[1]))

  def release(self, x, y, now):
    if self.press_pos is None:
      return False
    self.move(x, y)
    target, start = self.press_target, self.press_pos
    self.press_target, self.press_pos = None, None
    if not self.enabled:
      return True
    if target == ("corner", None):
      dx, dy = x - start[0], y - start[1]
      if (math.hypot(dx, dy) <= 36 * self.scale or
          (dx >= 55 * self.scale and dy <= -55 * self.scale and 0.35 <= dx / max(1, abs(dy)) <= 2.8)):
        self.mode = "radial"
        self.last_interaction = now
      return True
    limit = 24 if self.profile == Profile.COMPACT else 36 * self.scale
    if self.max_travel > limit:
      self.feedback = None
      self.editing = None
      return True
    if self.profile == Profile.LARGE and target and target[0] == "slot" and now - self.press_time >= 0.60 and self.configured(target[1]):
      self.editing = target[1]
      self.last_interaction = now
      return True
    if target is None or target != self.target_at(x, y):
      if self.is_open:
        self.cancel()
      self.feedback = None
      return True
    kind, index = target
    if kind == "slot":
      if self.editing is not None:
        self.editing = None
      elif self.configured(index):
        if self.profile == Profile.COMPACT or now - self.last_activation.get(index, -math.inf) >= 0.28:
          self.last_activation[index] = now
          success = self._emit("activate", index, self.slots()[index]["key"])
          self.feedback, self.feedback_at = (index if success else None), now
          if success:
            slot = self.slots()[index]
            self.feedback_text = (slot.get("label") or slot["key"], slot.get("state_label", "Done"))
      else:
        self.mode, self.selected, self.page = "picker", index, 0
    elif kind == "unassign":
      self._emit("unassign", index, None)
      self.editing = None
    elif kind == "close":
      self.mode, self.selected, self.page = "radial", None, 0
    elif kind == "previous":
      self.page = max(0, self.page - 1)
    elif kind == "next":
      if (self.page + 1) * 8 < len(self.data.get("options", [])):
        self.page += 1
    elif kind == "option":
      if self._emit("assign", self.selected, self.data["options"][index]["key"]):
        self.mode, self.selected, self.page = "radial", None, 0
    self.last_interaction = now
    return True

  def _emit(self, kind, index, key):
    if kind in ("assign", "unassign") and not self.data.get("configurable", False):
      return False
    return self.emit(FavoriteRequest(kind, index, key, self.data.get("revision", "")))

  def _text(self, text, size, x, y, color, *, role=FontRole.SEMI_BOLD):
    self.fonts.draw(text, role, max(10, int(size)), x, y, color)

  def _fit(self, text, size, width):
    original = text
    while text and self.fonts.measure(text, FontRole.SEMI_BOLD, max(10, int(size))).width > width:
      text = text[:-1]
    if text != original:
      while text and self.fonts.measure(text + "...", FontRole.SEMI_BOLD, max(10, int(size))).width > width:
        text = text[:-1]
      text += "..."
    return text

  def _wrapped_label(self, text, size, width):
    lines = []
    current = ""
    for word in text.split():
      candidate = f"{current} {word}".strip()
      if current and self.fonts.measure(candidate, FontRole.SEMI_BOLD, size).width > width:
        lines.append(current)
        current = word
      else:
        current = candidate
    if current:
      lines.append(current)
    if len(lines) > 3:
      lines = lines[:2] + [" ".join(lines[2:])]
    return [self._fit(line, size, width) for line in lines]

  def render(self, now):
    if not self.enabled:
      return
    if self.profile == Profile.COMPACT:
      self._compact_feedback(now)
    elif self.mode == "radial":
      self._radial(now)
    elif self.mode == "picker":
      self._picker()

  def _compact_feedback(self, now):
    if self.feedback is None or not self.configured(self.feedback):
      return
    held = self.press_target == ("slot", self.feedback)
    elapsed = max(0, now - self.feedback_at)
    alpha = 1 if held or elapsed < 2 else max(0, 3 - elapsed)
    if alpha == 0:
      self.feedback = None
      return
    width = self.rect[2] / 3
    panel = rl.Rectangle(self.rect[0] + self.feedback * width + 12, self.rect[1] + self.rect[3] / 4,
                         max(96, width - 24), min(132, self.rect[3] / 2))
    progress = 1 - (1 - min(1, elapsed / 0.65)) ** 3
    accent = rl.Color(round(188 + 67 * progress), round(132 + 123 * progress), 255, round(255 * alpha))
    for expansion, opacity in ((8, 22), (4, 44)):
      glow = rl.Rectangle(panel.x - expansion, panel.y - expansion,
                          panel.width + 2 * expansion, panel.height + 2 * expansion)
      rl.draw_rectangle_rounded_lines_ex(glow, 0.16, 12, 2,
                                         rl.Color(188, 132, 255, round(opacity * (1 - progress) * alpha)))
    rl.draw_rectangle_rounded(panel, 0.16, 12, rl.Color(0, 0, 0, round(178 * alpha)))
    rl.draw_rectangle_rounded_lines_ex(panel, 0.16, 12, 3, accent)
    label, value = self.feedback_text
    size = 18
    for candidate in range(30, 17, -1):
      if any(self.fonts.measure(word, FontRole.SEMI_BOLD, candidate).width > panel.width - 20 for word in label.split()):
        continue
      lines = self._wrapped_label(label, candidate, panel.width - 20)
      if len(lines) * candidate * 1.12 <= panel.height - 46:
        size = candidate
        break
    lines = self._wrapped_label(label, size, panel.width - 20)
    text_y = panel.y + 12 + (panel.height - 42 - len(lines) * size * 1.08) / 2
    for index, label in enumerate(lines):
      measured = self.fonts.measure(label, FontRole.SEMI_BOLD, size)
      self._text(label, size, panel.x + (panel.width - measured.width) / 2, text_y + index * size * 1.08, accent)
    value = value.upper()
    measured = self.fonts.measure(value, FontRole.SEMI_BOLD, 20)
    self._text(value, 20, panel.x + (panel.width - measured.width) / 2, panel.y + panel.height - 30,
               rl.Color(255, 255, 255, round(210 * alpha)))

  def _radial(self, now):
    s = self.scale
    origin = rl.Vector2(self.rect[0] + 48 * s, self.rect[1] + self.rect[3] - 48 * s)
    for inset, alpha in ((8, 24), (4, 58), (1.8, 140)):
      rl.draw_ring(origin, (460 - inset) * s, (460 + inset) * s, 289, 348, 44, rl.Color(161, 112, 255, alpha))
    for index, (blade, center) in enumerate(self.blades()):
      configured = self.configured(index)
      rect = rl.Rectangle(*blade)
      rl.draw_rectangle_rounded(rect, 0.45, 14, rl.Color(14, 10, 26, 255) if configured else rl.Color(12, 10, 22, 255))
      rl.draw_rectangle_rounded_lines_ex(rect, 0.45, 14, max(1, round(1.8 * s)), rl.Color(161, 112, 255, 140 if configured else 80))
      c = rl.Vector2(*center)
      rl.draw_circle_v(c, 64 * s, rl.Color(161, 112, 255, 22))
      rl.draw_circle_v(c, 57 * s, rl.Color(161, 112, 255, 48))
      rl.draw_circle_v(c, 52 * s, rl.Color(13, 11, 23, 236))
      rl.draw_circle_v(c, 49.5 * s, rl.Color(32, 23, 54, 250))
      slot = self.slots()[index] if index < len(self.slots()) else {}
      on = configured and slot.get("kind") == "toggle" and slot.get("state_label") == "On"
      rl.draw_ring(c, (47.5 if on else 49) * s, 52 * s, 0, 360, 40,
                   rl.Color(214, 192, 255, 255) if on else rl.Color(161, 112, 255, 235 if configured else 160))
      glyph = str(index + 1) if configured else "+"
      measured = self.fonts.measure(glyph, FontRole.SEMI_BOLD, int(48 * s))
      self._text(glyph, 48 * s, center[0] - measured.width / 2, center[1] - 26 * s, rl.WHITE)
      label = slot.get("label") or slot.get("key") if configured else f"Add Favorite {index + 1}"
      value = slot.get("state_label", "PRESS") if configured else "Tap to configure"
      self._text(self._fit(label, 32 * s, 318 * s), 32 * s, center[0] + 78 * s, center[1] - 29 * s, rl.Color(255, 255, 255, 245))
      self._text(self._fit(value, 24 * s, 318 * s), 24 * s, center[0] + 78 * s, center[1] + 10 * s, rl.Color(214, 192, 255, 230))
      if self.editing == index:
        cx, cy = blade[0] + blade[2] - 2 * s, blade[1] + 2 * s
        rl.draw_circle_v(rl.Vector2(cx, cy), 19 * s, rl.Color(198, 36, 62, 245))
        self._text("×", 30 * s, cx - 10 * s, cy - 18 * s, rl.WHITE)
      if self.feedback == index and 0 <= now - self.feedback_at < 0.18:
        elapsed = (now - self.feedback_at) / 0.18
        rl.draw_ring(c, 52 * s, (52 + 24 * elapsed) * s, 0, 360, 32, rl.Color(214, 192, 255, round(180 * (1 - elapsed))))

  def _picker(self):
    s = self.scale
    panel, close, cells, prev, nxt = self.picker_geometry()
    rl.draw_rectangle_rec(rl.Rectangle(*self.rect), rl.Color(4, 4, 10, 188))
    rect = rl.Rectangle(*panel)
    rl.draw_rectangle_rounded(rect, min(1, 68 * s / min(rect.width, rect.height)), 16, rl.Color(13, 11, 23, 236))
    rl.draw_rectangle_rounded_lines_ex(rect, 0.08, 16, 2 * s, rl.Color(214, 192, 255, 166))
    self._text(f"Assign Favorite {self.selected + 1}", 50 * s, panel[0] + 36 * s, panel[1] + 26 * s, rl.WHITE)
    self._text("×", 50 * s, close[0] + 50 * s, close[1] + 38 * s, rl.WHITE)
    options = self.data.get("options", [])
    for index, cell in enumerate(cells):
      option = self.page * 8 + index
      if option >= len(options):
        break
      r = rl.Rectangle(*cell)
      rl.draw_rectangle_rounded(r, 0.1, 16, rl.Color(24, 18, 40, 255))
      rl.draw_rectangle_rounded_lines_ex(r, 0.1, 16, 2 * s, rl.Color(161, 112, 255, 100))
      self._text(self._fit(options[option]["label"], 32 * s, r.width - 32 * s), 32 * s, r.x + 16 * s, r.y + 24 * s, rl.WHITE)
    for label, rect in (("Previous", prev), ("Next", nxt)):
      rl.draw_rectangle_rounded(rl.Rectangle(*rect), 0.18, 16, rl.Color(42, 28, 64, 255))
      self._text(label, 28 * s, rect[0] + 20 * s, rect[1] + 28 * s, rl.WHITE)
