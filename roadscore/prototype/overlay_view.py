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


# Explicit presentation of scheduler kinds, ordered by brief event salience.
# These names describe existing gesture-bank actions, never inferred road input.
GESTURE_LABELS = {
  'arrival': ('Arrival', 'Arrival cue'),
  'curve_apex': ('Curve apex', 'Curve apex / impact'),
  'curve_prepare': ('Curve ahead', 'Curve ahead / build'),
  'navigation_turn': ('Navigation turn', 'Navigation turn / accent'),
  'arrival_prepare': ('Arrival ahead', 'Arrival ahead / build'),
  'lane_change': ('Lane change', 'Lane change / sweep'),
  'stop': ('Stop', 'Stop cue'),
  'resume': ('Resume', 'Resume cue'),
  'turn_signal': ('Turn signal', 'Turn signal / percussion'),
  'turn_signal_sustain': ('Turn signal', 'Turn signal / percussion'),
  'turn_signal_off': ('Signal ended', 'Signal ended / release'),
}


def gesture_view(state):
  active = state.get('gesture_active')
  active = [kind for kind in active if isinstance(kind, str)] if isinstance(active, (list, tuple)) else []
  queued = state.get('gesture_queued')
  queued = [item.get('kind') for item in queued if isinstance(item, dict) and isinstance(item.get('kind'), str)] if isinstance(queued, (list, tuple)) else []
  for kind, (_, label) in GESTURE_LABELS.items():
    if kind in active:
      return label, 'active', kind
  if active:
    return 'Music cue', 'active', None
  for kind in queued:
    if kind in GESTURE_LABELS:
      return 'Next: ' + GESTURE_LABELS[kind][0], 'queued', kind
  if queued:
    return 'Next: music cue', 'queued', None
  # This legacy flag can include queued cues; it does not prove audible playback.
  if state.get('turn_signal_music'):
    return 'Turn signal cue', 'reported', 'turn_signal'
  lead = seconds(state.get('lead'))
  if state.get('kind') == 'curve' and state.get('phase') == 'anticipation' and lead is not None and lead > 0:
    return f'Curve ahead / {lead:.1f}s', 'anticipated', 'curve_prepare'
  return '', '', None


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
    note = f'Job {elapsed:.1f}s elapsed' if elapsed is not None else 'New passage in progress'
  event, event_state, event_kind = gesture_view(state)
  return dict(profile=display_text(profile), section=section, backend=backend, activity=activity,
              buffered=seconds(state.get('buffered')), note=note, event=event, event_state=event_state, event_kind=event_kind,
              ready=readiness == 'READY' and not degraded, stored=stored)


def fit_text(text, max_width, measure):
  """Fit with the actual font metrics, using a supported ellipsis."""
  if measure(text) <= max_width + .01:
    return text
  while text and measure(text + '...') > max_width + .01:
    text = text[:-1]
  return text.rstrip() + '...' if text else ''


def hud_bounds(screen_width, screen_height):
  """Accessory slot below DM/speed, left of the native speed-limit sign."""
  width = min(286, screen_width - 64 - 144 - 16)
  if width < 230 or screen_height < 224:
    return None
  return (16, 88, width, 60)


def draw_panel(rl, font, state, screen_width, screen_height, emphasis_font=None):
  view = overlay_view(state)
  bounds = hud_bounds(screen_width, screen_height)
  if bounds is None:
    return view
  x, y, width, height = bounds
  title_font = emphasis_font or font
  accent = rl.Color(*({'READY': (123, 229, 193), 'GENERATING': (131, 192, 255),
                     'DEGRADED': (255, 197, 112), 'PREPARING': (196, 204, 214)}[view['activity']]), 255)
  muted = rl.Color(235, 239, 243, 255)
  section = view['section'].removeprefix('INTENT: ').split(' > ')[0].title()
  if section in ('Archived Score', 'Waiting For Score'):
    section = ''
  identity = 'Stored score' if view['stored'] else view['profile']
  subtitle = identity + (' / ' + section if section else '')
  title = 'RoadScore'
  if view['activity'] == 'DEGRADED':
    title = 'Music on hold' if state.get('holding_accepted_music') else ('Composer offline' if state.get('worker_failed') else 'Reserve in use')
    subtitle = 'DEGRADED / ' + identity
  elif view['event']:
    title, _, effect = view['event'].partition(' / ')
    subtitle = identity + (' / ' + effect.capitalize() if effect else '')
  elif view['activity'] == 'GENERATING':
    title = 'Composing'
  elif view['activity'] == 'PREPARING':
    title = 'Preparing music'
  # Match native icon/label groups: no enclosing dashboard panel.
  rl.draw_circle(int(x + 20), int(y + 28), 21, rl.Color(0, 0, 0, 150))
  icon_color = accent if view['activity'] == 'DEGRADED' else rl.WHITE
  rl.draw_circle(int(x + 12), int(y + 36), 4, icon_color)
  rl.draw_circle(int(x + 27), int(y + 32), 4, icon_color)
  for left, top, w, h in ((14, 16, 2.5, 20), (29, 12, 2.5, 20), (14, 12, 17.5, 3.5)):
    rl.draw_rectangle_rounded(rl.Rectangle(x + left, y + top, w, h), .2, 4, icon_color)
  def text(label, top, size, face, tint, available):
    label = fit_text(label, available, lambda value: rl.measure_text_ex(face, value, size, 0).x)
    # Native HUD text uses local shadows; avoid an opaque rectangle over the road.
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 2)):
      rl.draw_text_ex(face, label, rl.Vector2(x + 52 + dx, y + top + dy), size, 0, rl.Color(0, 0, 0, 210))
    rl.draw_text_ex(face, label, rl.Vector2(x + 52, y + top), size, 0, tint)
  text(title, 5, 20, title_font, accent if view['activity'] == 'DEGRADED' else rl.WHITE, width - 52)
  text(subtitle, 33, 14, font, muted, width - 52)
  return view
