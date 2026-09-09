"""Passive controller receipts, scaled for comma 3/3X and comma 4."""
import json
from time import monotonic
import pyray as rl
from cereal import log, custom
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.starpilot.common.action_feedback import DISPLAY_SECONDS, visible_receipt


def toast_geometry(width, height):
  small = height < 500
  w, h = min(width - 32, 492 if small else 860), 104 if small else 196
  return ((width - w) / 2, height - h - (12 if small else 56), w, h, small)


class ControllerToast:
  def __init__(self, memory):
    self.memory = memory
    self._next_read = 0.0
    self._status = {}
    self._suppressed = None

  def render(self, state):
    now = monotonic()
    if now >= self._next_read:
      self._next_read = now + .1
      try:
        raw = self.memory.get('WheelControlStatus')
        self._status = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
      except (ValueError, TypeError, OSError):
        self._status = {}
    receipt = visible_receipt(self._status, now)
    if receipt is None:
      return
    identity = (receipt.get('id'), receipt.get('at'))
    # Never cover any driving alert or replay an old receipt after it clears.
    if state.started and (
      any(not state.sm.valid.get(service, False) or not state.sm.alive.get(service, False)
          for service in ('selfdriveState', 'starpilotSelfdriveState')) or
      state.sm['selfdriveState'].alertSize != log.SelfdriveState.AlertSize.none or
      state.sm['starpilotSelfdriveState'].alertSize != custom.StarPilotSelfdriveState.AlertSize.none
    ):
      self._suppressed = identity
      return
    if identity == self._suppressed:
      return
    gui_app.request_high_fps()
    draw_receipt(receipt, gui_app.width, gui_app.height, now,
                 traffic=state.traffic_mode_enabled and receipt['title'].startswith('Driving personality'))


def draw_receipt(receipt, width, height, now, *, traffic=False):
  x, y, w, h, small = toast_geometry(width, height)
  age = now - receipt['at']
  opacity = min(1.0, max(0.0, age / .12), max(0.0, (DISPLAY_SECONDS - age) / .35))
  def color(r, g, b, a=255):
    return rl.Color(r, g, b, int(a * opacity))
  confirmed = receipt['state'] == 'confirmed'
  warning = receipt['state'] in ('blocked', 'unconfirmed')
  accent = color(113, 224, 170) if confirmed else color(244, 194, 111) if warning else color(179, 164, 242)
  scale = 1 if small else 1.8
  pad = 16 * scale
  rect = rl.Rectangle(x, y, w, h)
  rl.draw_rectangle_rounded(rl.Rectangle(x, y + 4 * scale, w, h), .22, 12, color(0, 0, 0, 100))
  rl.draw_rectangle_rounded(rect, .22, 12, color(23, 26, 34, 248))
  rl.draw_rectangle_rounded_lines_ex(rect, .22, 12, scale, color(80, 88, 104, 200))
  rl.draw_rectangle_rounded(rl.Rectangle(x + 7 * scale, y + 17 * scale, 3 * scale, h - 34 * scale), 1, 6, accent)
  font = gui_app.font(FontWeight.MEDIUM)
  bold = gui_app.font(FontWeight.BOLD)
  def text(value, tx, ty, size, tint, maximum, selected_font=font):
    value = str(value).replace('\n', ' ')[:100]
    while size > 12 * scale and measure_text_cached(selected_font, value, int(size)).x > maximum:
      size -= 1
    while value and measure_text_cached(selected_font, value, int(size)).x > maximum:
      value = value[:-4].rstrip() + '...' if len(value) > 4 else ''
    rl.draw_text_ex(selected_font, value, rl.Vector2(tx, ty), int(size), 0, tint)
  title = 'Driving personality / Traffic override active' if traffic else receipt['title']
  text(title, x + pad, y + 10 * scale, 13 * scale, color(192, 201, 215), w - pad * 2 - 24 * scale)
  text(receipt['value'], x + pad, y + 31 * scale, 27 * scale, color(249, 250, 252), w - pad * 2, bold)
  # Small check mark only for an acknowledged result; requests get a neutral dot.
  cx, cy = x + w - pad, y + 19 * scale
  if confirmed:
    rl.draw_line_ex(rl.Vector2(cx - 7 * scale, cy), rl.Vector2(cx - 2 * scale, cy + 5 * scale), 2 * scale, accent)
    rl.draw_line_ex(rl.Vector2(cx - 2 * scale, cy + 5 * scale), rl.Vector2(cx + 7 * scale, cy - 6 * scale), 2 * scale, accent)
  else:
    rl.draw_circle_v(rl.Vector2(cx, cy), 3 * scale, accent)
  choices = receipt.get('choices', [])[:4]
  if choices:
    gap = 6 * scale
    cw = (w - 2 * pad - gap * (len(choices) - 1)) / len(choices)
    for i, label in enumerate(choices):
      active = i == receipt.get('selected')
      chip = rl.Rectangle(x + pad + i * (cw + gap), y + h - 29 * scale, cw, 21 * scale)
      rl.draw_rectangle_rounded(chip, .45, 8, accent if active else color(43, 48, 59))
      text(label, chip.x + 7 * scale, chip.y + 2 * scale, 12 * scale,
           color(17, 25, 24) if active else color(178, 189, 205), cw - 14 * scale, bold if active else font)
  else:
    footer = {'confirmed': 'Changed', 'requested': 'Request sent', 'pending': 'Waiting for confirmation',
              'blocked': 'No change made', 'unconfirmed': 'Check the current setting'}[receipt['state']]
    text(footer, x + pad, y + h - 25 * scale, 12 * scale, accent, w - 2 * pad)
