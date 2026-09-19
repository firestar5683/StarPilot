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
    note = f'Job {elapsed:.1f}s elapsed' if elapsed is not None else 'New passage in progress'
  event = ''
  if state.get('turn_signal_music'):
    event = 'Signal percussion'
  elif state.get('gesture_active'):
    event = display_text(state['gesture_active'][0]).replace('_', ' ')
  elif state.get('gesture_queued'):
    event = 'Queued ' + display_text(state['gesture_queued'][0].get('kind')).replace('_', ' ')
  elif (lead := seconds(state.get('lead'))) is not None and lead > 0:
    event = f'Curve in {lead:.1f}s'
  return dict(profile=display_text(profile), section=section, backend=backend, activity=activity,
              buffered=seconds(state.get('buffered')), note=note, event=event,
              ready=readiness == 'READY' and not degraded, stored=stored)


def fit_text(text, max_width, measure):
  """Fit with the actual font metrics, using a supported ellipsis."""
  if measure(text) <= max_width + .01:
    return text
  while text and measure(text + '...') > max_width + .01:
    text = text[:-1]
  return text.rstrip() + '...' if text else ''


def draw_panel(rl, font, state, screen_width, screen_height):
  """A content-sized edge ribbon; leave the road and native right rail clear."""
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
    detail = view['event'].capitalize()
  elif view['activity'] == 'GENERATING':
    detail = view['note']
  else:
    detail = 'Archived playback' if view['stored'] else ' / '.join(filter(None, view['backend']))
  secondary = 'RoadScore' + (' / ' + detail if detail else '')
  buffer = view['buffered']
  reserve = '--' if buffer is None else f'{buffer:.0f}s'
  activity_width = measure(view['activity'], 9)
  max_width = min(300, screen_width * .64, screen_width - 24)
  width = min(max_width, max(210, measure(primary, 11) + activity_width + 38,
                             measure(secondary, 9) + measure(reserve, 9) + 30))
  x, y, height = 12, max(12, screen_height - 42), 34
  # One quiet translucent surface, with no enclosing badge or oversized title.
  rl.draw_rectangle_rounded(rl.Rectangle(x, y, width, height), .4, 8, rl.Color(8, 13, 18, 184))
  def text(label, left, top, size, tint, available):
    label = fit_text(label, max(0, available), lambda value: measure(value, size))
    rl.draw_text_ex(font, label, rl.Vector2(x + left, y + top), size, 0, tint)
  activity_left = width - activity_width - 9
  text(primary, 9, 5, 11, rl.WHITE, activity_left - 24)
  rl.draw_circle(int(x + activity_left - 7), int(y + 10), 2, accent)
  text(view['activity'], activity_left, 6, 9, accent, activity_width + 1)
  reserve_width = measure(reserve, 9)
  text(secondary, 9, 21, 9, accent if view['activity'] == 'DEGRADED' else muted,
       width - reserve_width - 29)
  text(reserve, width - reserve_width - 9, 21, 9, muted, reserve_width + 1)
  return view
