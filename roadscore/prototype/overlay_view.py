"""Read-only presentation of RoadScore status; no runtime or device dependencies."""
import math
import unicodedata


def display_text(value):
  """The native bitmap font reliably supports ASCII; draw separators as shapes."""
  text = str(value or '').replace('→', ' > ').replace('·', ' / ').replace('—', '-').replace('–', '-')
  return ' '.join(unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().split())


def seconds(value):
  if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
    return max(0., float(value))
  return None


def overlay_view(state):
  readiness = str(state.get('readiness') or 'PREPARING').upper()
  degraded = readiness == 'DEGRADED' or any(state.get(k) for k in ('worker_failed', 'holding_accepted_music', 'quality_failures'))
  activity = 'DEGRADED' if degraded else ('GENERATING' if state.get('job_inflight') else readiness)
  if activity not in ('READY', 'GENERATING', 'DEGRADED'):
    activity = 'PREPARING'
  stored = state.get('compute') == 'none'
  composer = display_text(state.get('composer')).upper()
  backend = ('STORED SCORE', 'NO COMPUTE') if stored else ((composer, 'CHESTNUT') if composer in ('ACE', 'SA3') else ('LOCAL SCORE', ''))
  profile = state.get('style') or str(state.get('profile') or 'Preparing').title()
  section = display_text(state.get('section') or 'Waiting for score').upper()
  section = section.removesuffix(' / CONTINUOUS')
  if state.get('next_section'):
    section += ' > ' + display_text(state['next_section']).upper()
  if state.get('form_labels_are_intent'):
    section = 'INTENT: ' + section
  elapsed = seconds(state.get('generation_elapsed_seconds'))
  note = ''
  if state.get('holding_accepted_music'):
    note = 'Holding accepted music'
  elif state.get('worker_failed'):
    note = 'Composer unavailable'
  elif degraded:
    note = 'Quality check / reserve in use'
  elif state.get('job_inflight'):
    note = 'New passage' + (f' / {elapsed:.1f}s elapsed' if elapsed is not None else '')
  event = ''
  if state.get('turn_signal_music'):
    event = 'Signal percussion'
  elif state.get('gesture_active'):
    event = display_text(state['gesture_active'][0]).replace('_', ' ')
  elif state.get('gesture_queued'):
    event = 'Queued ' + display_text(state['gesture_queued'][0].get('kind')).replace('_', ' ')
  elif (lead := seconds(state.get('lead'))) is not None and lead > 0:
    event = f'Curve in {lead:.1f}s'
  if event:
    note = f'{note} / {event}' if note else event
  return dict(profile=display_text(profile), section=section, backend=backend, activity=activity,
              buffered=seconds(state.get('buffered')), note=note,
              ready=readiness == 'READY' and not degraded, stored=stored)


def fit_text(text, max_width, measure):
  """Fit with the actual font metrics, using a supported ellipsis."""
  if measure(text) <= max_width + .01:
    return text
  while text and measure(text + '...') > max_width + .01:
    text = text[:-1]
  return text.rstrip() + '...' if text else ''


def draw_panel(rl, font, state, screen_width, screen_height):
  view = overlay_view(state)
  width = min(340, screen_width - 24)
  height = 146 if view['note'] else 126
  x, y = 12, max(12, screen_height - height - 12)
  color = {'READY': (123, 229, 193), 'GENERATING': (131, 192, 255),
           'DEGRADED': (255, 197, 112), 'PREPARING': (180, 190, 204)}[view['activity']]
  accent = rl.Color(*color, 255)
  muted = rl.Color(180, 190, 204, 255)
  rl.draw_rectangle_rounded(rl.Rectangle(x, y, width, height), .12, 8, rl.Color(15, 22, 31, 235))

  def text(label, left, top, size=13, tint=rl.WHITE, available=None):
    available = width - left - 12 if available is None else available
    label = fit_text(label, available, lambda s: rl.measure_text_ex(font, s, size, 0).x)
    rl.draw_text_ex(font, label, rl.Vector2(x + left, y + top), size, 0, tint)

  badge_width = rl.measure_text_ex(font, view['activity'], 11, 0).x + 16
  rl.draw_rectangle_rounded(rl.Rectangle(x + width - badge_width - 10, y + 10, badge_width, 22), .4, 8, rl.Color(*color, 28))
  text(view['activity'], width - badge_width - 2, 15, 11, accent)
  text('RoadScore', 12, 12, 17, available=width - badge_width - 34)
  text(view['profile'], 12, 39, 17)
  text(view['section'], 12, 62, 12, muted)
  left, right = view['backend']
  text(left, 12, 83, 11, muted)
  if right:
    offset = 12 + rl.measure_text_ex(font, left, 11, 0).x
    # A geometric middle dot avoids missing-glyph boxes in the native font.
    rl.draw_circle(int(x + offset + 7), int(y + 89), 1.5, muted)
    text(right, offset + 15, 83, 11, muted)
  buffer = view['buffered']
  text('BUFFER', 12, 105, 11, muted)
  label = '--' if buffer is None else f'{buffer:.0f}s'
  label_width = rl.measure_text_ex(font, label, 13, 0).x
  text(label, width - label_width - 12, 103, 13, accent)
  if view['note']:
    text(view['note'], 12, 126, 11, accent)
  return view
