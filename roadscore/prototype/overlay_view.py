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


def draw_panel(rl, font, state, screen_width, screen_height):
  """A compact score ribbon centered over the camera, clear of the right rail."""
  view = overlay_view(state)
  color = {'READY': (123, 229, 193), 'GENERATING': (131, 192, 255),
           'DEGRADED': (255, 197, 112), 'PREPARING': (196, 204, 214)}[view['activity']]
  accent = rl.Color(*color, 255)
  muted = rl.Color(210, 218, 225, 255)
  measure = lambda label, size: rl.measure_text_ex(font, label, size, 0).x
  section = view['section'].removeprefix('INTENT: ')
  if section in ('ARCHIVED SCORE', 'WAITING FOR SCORE'):
    section = ''
  elif state.get('form_labels_are_intent'):
    section = 'intent ' + section.title()
  else:
    section = section.title()
  primary = view['profile'] + (' / ' + section if section else '')
  if view['activity'] == 'DEGRADED':
    detail = view['note']
  elif view['event']:
    detail = view['event']
  elif view['activity'] == 'GENERATING':
    detail = view['note']
  else:
    detail = 'Archived playback' if view['stored'] else ' / '.join(filter(None, view['backend']))
  secondary = detail if view['event'] or view['activity'] == 'DEGRADED' else 'RoadScore' + (' / ' + detail if detail else '')
  buffer = view['buffered']
  reserve = '--' if buffer is None else f'{buffer:.0f}s'
  activity_width = measure(view['activity'], 9)
  max_width = min(300, screen_width * .64, screen_width - 24)
  width = min(max_width, max(210, measure(primary, 11) + activity_width + 57,
                             measure(secondary, 10) + measure(reserve, 9) + 60))
  camera_width = screen_width - 64  # Native mici control rail stays unobstructed.
  x, y, height = max(12, (camera_width - width) / 2), 8, 34
  # One quiet translucent surface, with no enclosing badge or oversized title.
  rl.draw_rectangle_rounded(rl.Rectangle(x, y, width, height), .4, 8, rl.Color(8, 13, 18, 184))
  def text(label, left, top, size, tint, available):
    label = fit_text(label, max(0, available), lambda value: measure(value, size))
    rl.draw_text_ex(font, label, rl.Vector2(x + left, y + top), size, 0, tint)
  # Connected notes are a score identity mark, not an animated compute claim.
  rl.draw_circle(int(x + 11), int(y + 23), 2.5, muted)
  rl.draw_circle(int(x + 20), int(y + 21), 2.5, muted)
  for left, top, w, h in ((12, 10, 1.5, 13), (21, 8, 1.5, 13), (12, 8, 10.5, 2.5)):
    rl.draw_rectangle_rounded(rl.Rectangle(x + left, y + top, w, h), .2, 4, muted)
  activity_left = width - activity_width - 9
  text(primary, 30, 5, 11, rl.WHITE, activity_left - 45)
  rl.draw_circle(int(x + activity_left - 7), int(y + 10), 2, accent)
  text(view['activity'], activity_left, 6, 9, accent, activity_width + 1)
  reserve_width = measure(reserve, 9)
  text(secondary, 30, 21, 10, accent if view['activity'] == 'DEGRADED' or view['event_state'] == 'active' else muted,
       width - reserve_width - 62)
  # Three quiet queue bars distinguish buffered seconds from job elapsed time.
  for i, bar_height in enumerate((3, 5, 7)):
    rl.draw_rectangle_rounded(rl.Rectangle(x + width - reserve_width - 21 + i * 3,
                                         y + 29 - bar_height, 1.5, bar_height), .2, 4, muted)
  text(reserve, width - reserve_width - 9, 21, 9, muted, reserve_width + 1)
  return view
