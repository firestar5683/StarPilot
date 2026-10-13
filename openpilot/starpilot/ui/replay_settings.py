"""Native route picker and passive replay viewer; the shared owner runs playback."""

from concurrent.futures import ThreadPoolExecutor
from html import escape, unescape
import math
import time
import uuid

import pyray as rl

from openpilot.selfdrive.ui.mici.widgets.button import BigButton, GreyBigButton
from openpilot.selfdrive.ui.ui_state import device, ui_state
from openpilot.starpilot.ui.clip import placed_at
from openpilot.starpilot.ui.feature_settings import FeatureSettingsView
from openpilot.starpilot.ui.feature_settings_state import FeatureInput, FeatureRow, FeatureSettingsState, FeatureUiAction, feature_scroll
from openpilot.starpilot.ui.presentation import FontRole, Profile
from openpilot.starpilot.ui.settings_geometry import (ACCENT, CONTROL_BG, CONTROL_BORDER, CONTROL_PRESSED_BG,
                                                     PANEL_BG, TEXT_MUTED, TEXT_PRIMARY, draw_rounded_fill,
                                                     draw_rounded_stroke, draw_settings_header, elide_text)
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.widgets.nav_widget import NavWidget
from openpilot.system.ui.widgets.scroller import Scroller


ACTIVE_STATES = frozenset(('preparing', 'playing', 'paused', 'seeking', 'buffering', 'ended', 'stopping'))


def _request(payload):
  from openpilot.starpilot.replay.client import request_operation
  return request_operation(payload)


def _reader(path, session_id, profile):
  from openpilot.starpilot.replay.frames import ReplayFrameReader
  return ReplayFrameReader(path, session_id, profile=profile)


def duration(value):
  if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
    return 'Unavailable'
  minutes, seconds = divmod(round(value), 60)
  return f'{minutes}:{seconds:02d}'


class ReplayController:
  """One bounded worker for IPC and frame copies; graphics stay on the UI thread."""

  def __init__(self, requester=_request, reader_factory=_reader, clock=time.monotonic):
    self.requester, self.reader_factory, self.clock = requester, reader_factory, clock
    self.client_id = uuid.uuid4().hex
    self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='native-replay')
    self.pending = None
    self.pending_op = ''
    self.queued = None
    self.status = {}
    self.routes = []
    self.detail = None
    self.error = ''
    self.source_warnings = []
    self.frame = None
    self.autoplay_at = None
    self.own_session = None
    self.selected_route = None
    self.reader = None
    self.reader_key = None
    self.reader_generation = 0
    self.closed = False
    self.catalog_loaded = False
    self.next_status = self.next_catalog = self.next_frame = 0.0
    self.status_at = None

  @property
  def busy(self):
    return self.queued is not None or self.pending is not None and self.pending_op in ('detail', 'start', 'control', 'stop')

  @property
  def active(self):
    return bool(self.own_session and self.status.get('sessionId') == self.own_session and
                self.status.get('state') in ACTIVE_STATES)

  @property
  def available(self):
    return bool(self.status.get('ownerId') and self.status.get('offroad') is True and self.status_at is not None and
                0 <= self.clock() - self.status_at < 2.0)

  def submit(self, payload):
    if self.closed:
      return False
    if self.pending is not None:
      if self.pending_op in ('frame', 'status', 'catalog') and self.queued is None:
        self.queued = payload
        return True
      return False
    self.pending_op = payload['op']
    self.pending = self.executor.submit(self.requester, payload)
    return True

  def select(self, route):
    if self.busy:
      return False
    self.selected_route = route['routeId']
    self.detail = route
    self.error = ''
    self.source_warnings = []
    return self.submit({'op': 'detail', 'routeId': self.selected_route})

  def start(self, segment=None):
    if (not self.available or self.status.get('state') in ACTIVE_STATES or self.selected_route is None or
        not (self.detail or {}).get('playable')):
      return False
    self.error = ''
    payload = {'op': 'start', 'routeId': self.selected_route, 'target': 'native',
               'clientId': self.client_id, 'requestId': uuid.uuid4().hex, 'expectedOwnerId': self.status['ownerId']}
    if segment is not None:
      payload['segment'] = segment
    submitted = self.submit(payload)
    if submitted:
      self.autoplay_at = math.inf  # Wait for the first accepted frame before starting the delay.
    return submitted

  def control(self, action, **value):
    if not self.available or not self.active or self.status.get('state') not in ('playing', 'paused', 'buffering', 'ended'):
      return False
    submitted = self.submit({'op': 'control', 'sessionId': self.own_session, 'clientId': self.client_id,
                             'expectedRevision': self.status['revision'], 'requestId': uuid.uuid4().hex,
                             'action': action, **value})
    if submitted:
      self.autoplay_at = None
    return submitted

  def seek(self, position):
    if type(position) not in (int, float) or not math.isfinite(position):
      return False
    start, end = self.status.get('start'), self.status.get('end')
    if type(start) not in (int, float) or type(end) not in (int, float) or end <= start:
      return False
    position = max(start, min(end, position))
    ranges = self.status.get('seekRanges')
    if ranges and not any(left <= position <= right for left, right in ranges):
      position = min((point for bounds in ranges for point in bounds), key=lambda point: abs(point - position))
      self.error = 'Unavailable gap; seeking to available footage'
    return self.control('seek', position=position)

  def stop(self):
    self.autoplay_at = None
    if not self.own_session:
      return False
    return self.submit(self._stop_payload(self.own_session))

  def _stop_payload(self, session):
    return {'op': 'stop', 'sessionId': session, 'clientId': self.client_id, 'requestId': uuid.uuid4().hex}

  def _read_frame(self, key):
    if key != self.reader_key:
      self._close_reader()
      self.reader = self.reader_factory(*key[:3])
      self.reader_key = key
    return self.reader.latest()

  def _close_reader(self):
    if self.reader is not None:
      self.reader.close()
    self.reader = self.reader_key = None

  def tick(self):
    if self.closed:
      return
    now = self.clock()
    if self.pending is not None and self.pending.done():
      future, operation = self.pending, self.pending_op
      self.pending, self.pending_op = None, ''
      try:
        response = future.result()
        if operation == 'frame':
          if response is not None:
            if response.session_id == self.own_session and response.epoch == self.status.get('epoch'):
              self.frame = response
              if self.autoplay_at == math.inf:
                self.autoplay_at = now + 1.0
            else:
              self.frame = None
              self.next_status = 0.0
        elif response.get('ok') is not True:
          self.error = response.get('error', {}).get('message', 'Replay unavailable')
          self.next_status = 0.0
        else:
          result = response['result']
          if operation == 'catalog':
            self.routes = result['routes']
            self.catalog_loaded = True
          elif operation == 'detail':
            self.detail = result
          else:
            if result.get('schemaVersion') != 1 or type(result.get('revision')) is not int:
              raise ValueError('Invalid replay status')
            if operation == 'start' or result.get('owned') is True:
              self.own_session = result['sessionId']
            if (result.get('sessionId'), result.get('epoch'), result.get('frameReady')) != (
                self.status.get('sessionId'), self.status.get('epoch'), self.status.get('frameReady')):
              self.frame = None
              self.reader_generation += 1
            if operation == 'start' or result.get('owned') is True and result.get('sessionId'):
              self.source_warnings = result.get('sourceWarnings', [])
            self.status, self.status_at = result, now
            self.error = result.get('errorCode') or ''
            if result.get('paused') is False or result.get('state') in ('ended', 'failed'):
              self.autoplay_at = None
            if not self.active or result.get('offroad') is not True or not result.get('frameReady'):
              self.frame = None
      except Exception as error:
        self.error = 'Replay frame unavailable' if operation == 'frame' else str(error) or 'Replay service unavailable'
        if operation == 'frame':
          self.frame = None
        else:
          self.status_at = None
    if self.pending is not None:
      return
    if self.queued is not None:
      payload, self.queued = self.queued, None
      self.submit(payload)
    elif (self.autoplay_at is not None and now >= self.autoplay_at and self.frame is not None and
          self.available and self.active and self.status.get('state') == 'paused' and not self.error):
      self.control('pause', paused=False)
    elif now >= self.next_catalog and not self.active:
      self.next_catalog = now + 5.0
      self.submit({'op': 'catalog'})
    elif now >= self.next_status:
      self.next_status = now + 0.25
      self.submit({'op': 'status', 'clientId': self.client_id})
    elif self.active and self.status.get('frameReady') and self.status.get('framePath') and now >= self.next_frame:
      # Sample faster than the producer's 20 Hz cadence; unchanged slots do not copy pixels.
      self.next_frame = now + 0.025
      key = (self.status['framePath'], self.own_session, self.status.get('profile'), self.reader_generation)
      self.pending_op = 'frame'
      self.pending = self.executor.submit(self._read_frame, key)

  def close(self):
    if self.closed:
      return
    self.closed = True
    self.autoplay_at = None
    if self.pending_op == 'start' or self.pending_op == 'status' and not self.own_session:
      def stop_late_start(future):
        try:
          response = future.result()
          if (response.get('ok') is True and response['result'].get('sessionId') and
              response['result'].get('owned') is True):
            self.requester(self._stop_payload(response['result']['sessionId']))
        except Exception:
          pass  # The owner also expires the native lease after disconnect.
      self.pending.add_done_callback(stop_late_start)
    elif self.own_session:
      self.executor.submit(self.requester, self._stop_payload(self.own_session))
    self.executor.submit(self._close_reader)
    self.executor.shutdown(wait=False)
    self.frame = None


class ReplayPage(Widget):
  def __init__(self, session, on_close, controller=None):
    super().__init__()
    self.fonts, self.profile = session.fonts, session.profile
    self.controller = controller or ReplayController()
    self.on_close = on_close
    self.page = 'routes'
    self.scroll = 0
    self.view = FeatureSettingsView(self.fonts) if self.profile == Profile.LARGE else None
    self.input = FeatureInput(self._action)
    if self.view:
      self.view.pressed_action = self.input.pressed_action
    self.cards = self._child(Scroller(snap_items=True)) if self.profile == Profile.COMPACT else None
    if self.cards:
      self.cards.set_enabled(lambda: self.enabled)
    self.card_signature = None
    self.route_rows = ()
    self.route_source = None
    self.texture = None
    self.frame_key = None
    self.press = None
    self.seek_preview = None
    self.controls = True
    self.last_touch = time.monotonic()
    self.stopping = False
    self._epoch = None
    self.stack_widget = self

  def show_event(self):
    super().show_event()
    gui_app.add_nav_stack_tick(self._tick)

  def hide_event(self):
    gui_app.remove_nav_stack_tick(self._tick)
    self.controller.close()
    self._clear_frame()
    self.input.cancel()
    self.press = self.seek_preview = None
    super().hide_event()

  def _tick(self):
    self.controller.tick()
    if self.controller.active and self.controller.available and self.controller.status.get('paused') is False:
      device._reset_interactive_timeout()
    if ui_state.started and gui_app.widget_in_stack(self.stack_widget):
      self.on_close()

  def _clear_frame(self):
    if self.texture is not None:
      rl.unload_texture(self.texture)
    self.texture = self.frame_key = None

  def _update_state(self):
    self.controller.tick()
    epoch = (self.controller.status.get('sessionId'), self.controller.status.get('epoch'))
    if epoch != self._epoch:
      self.press = self.seek_preview = None
      self.input.cancel()
      self._epoch = epoch
    if self.controller.active and not self.stopping:
      self.page = 'viewer'
    elif self.page == 'viewer' and self.controller.own_session and not self.controller.busy:
      self.page = 'detail'
      self.stopping = False
    if not self.controller.active and not self.controller.busy:
      self.stopping = False
    if self.controller.frame is None or not self.controller.available or ui_state.started:
      self._clear_frame()

  def _rows(self):
    owner = self.controller
    if self.route_source is not owner.routes:
      self.route_source = owner.routes
      self.route_rows = tuple(FeatureRow(route['routeId'], route.get('displayName', route['routeId']),
                                        f"{route.get('segmentCount', 0)} segments", available=True,
                                        reason=route.get('reason') or route.get('availability', ''), actions=(('DETAILS', True),))
                              for route in owner.routes)
    return self.route_rows or (FeatureRow('', 'No recorded routes' if owner.catalog_loaded else 'Loading recorded routes', ''),)

  def _warnings(self):
    return tuple(dict.fromkeys([*(self.controller.detail or {}).get('warnings', []), *self.controller.source_warnings]))

  def _play_available(self):
    owner = self.controller
    return owner.available and not owner.busy and bool((owner.detail or {}).get('playable')) and owner.status.get('state') not in ACTIVE_STATES

  def _segments(self):
    return [segment for segment in (self.controller.detail or {}).get('segments', [])
            if (segment['files']['rlog'] or segment['files']['qlog']) and (segment['files']['fcamera'] or segment['files']['qcamera'])]

  def _show_warnings(self):
    warnings = self._warnings()
    if not warnings:
      return
    if self.profile == Profile.COMPACT:
      from openpilot.selfdrive.ui.mici.widgets.dialog import SettingDescriptionDialog
      dialog = SettingDescriptionDialog('warnings', '\n'.join(str(warning) for warning in warnings))
      dialog._scroller.items.pop(0)  # Show the first warning instead of the help cover card.
      gui_app.push_widget(dialog)
      return
    from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
    dialog = ConfirmDialog(''.join(f'<p>{escape(str(warning))}</p>' for warning in warnings), 'Close', cancel_text='', rich=True)
    for element in dialog._html_renderer.elements:
      element.content = unescape(element.content)
    gui_app.push_widget(dialog)

  def _choose_segment(self):
    if not self._play_available():
      return
    options = {f"Segment {segment['number']}": segment['number'] for segment in self._segments()}
    if not options:
      return
    route_id = self.controller.selected_route
    def play_segment(number):
      if (self.page == 'detail' and self.controller.selected_route == route_id and
          gui_app.get_active_widget() is self.stack_widget):
        self.controller.start(segment=number)
    if self.profile == Profile.COMPACT:
      from openpilot.system.ui.widgets.scroller import NavScroller
      picker = NavScroller()
      def selected_segment(number):
        if gui_app.get_active_widget() is picker:
          gui_app.pop_widget()
          play_segment(number)
      for label, number in options.items():
        button = BigButton(label.lower(), 'play from this segment')
        button.set_click_callback(lambda number=number: selected_segment(number))
        picker._scroller.add_widgets([button])
      gui_app.push_widget(picker)
      return
    from openpilot.system.ui.widgets import DialogResult
    from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
    def selected(result):
      if result == DialogResult.CONFIRM and picker.selection in options:
        play_segment(options[picker.selection])
    picker = MultiOptionDialog('Play from segment', list(options), callback=selected)
    picker.select_button.set_text('Play')
    gui_app.push_widget(picker)

  def _detail_buttons(self):
    count = (self.controller.detail or {}).get('segmentCount', 0)
    warnings = len(self._warnings())
    available = self._play_available()
    if self.profile == Profile.COMPACT:
      return (('< Back', (12, 22, 88, 42), True, self._back),
              (f'{count} segments', (12, 84, 248, 52), available and bool(self._segments()), self._choose_segment),
              (f'Warnings ({warnings})' if warnings else 'No warnings', (276, 84, 248, 52), bool(warnings), self._show_warnings),
              ('Play', (12, 184, 512, 48), available, self.controller.start))
    return (('< Back', (20, 12, 208, 88), True, self._back),
            (f'{count} segments - Choose segment', (72, 350, 2016, 136), available and bool(self._segments()), self._choose_segment),
            (f'Warnings ({warnings})' if warnings else 'No warnings', (72, 518, 2016, 136), bool(warnings), self._show_warnings),
            ('Play', (72, 916, 2016, 128), available, self.controller.start))

  def _render_detail(self):
    owner = self.controller
    route = owner.detail or {}
    large = self.profile == Profile.LARGE
    if large:
      draw_settings_header(self.fonts, False, 'Replay', 'Recorded Routes', back=True)
    title = route.get('displayName', owner.selected_route or 'Recorded route')
    size, width, x, y = (58, 2016, 72, 180) if large else (22, 412, 112, 30)
    self.fonts.draw(elide_text(self.fonts, title, FontRole.SEMI_BOLD, size, width), FontRole.SEMI_BOLD, size, x, y, TEXT_PRIMARY)
    reason = owner.error or route.get('reason') or ('Loading route details...' if owner.busy else '')
    if not reason and not self._play_available():
      reason = 'Replay is available while offroad and no other player is active'
    size, width, x, y = (32, 2016, 72, 834) if large else (16, 512, 12, 146)
    self.fonts.draw(elide_text(self.fonts, reason, FontRole.NORMAL, size, width), FontRole.NORMAL, size, x, y, TEXT_MUTED)
    for label, bounds, enabled, _ in self._detail_buttons()[1 if large else 0:]:
      self._button(label, bounds, enabled)

  def _state(self):
    rows = self._rows()
    self.scroll = feature_scroll(self.scroll, 0, len(rows))
    return FeatureSettingsState(page=f'replay:{self.page}:{self.controller.selected_route}', title='Replay',
                                parent_title='Device' if self.page == 'routes' else 'Recorded Routes', rows=rows,
                                subtitle=self.controller.error, sidebar_expanded=False, scroll=self.scroll,
                                save_hint='Recorded driving routes on this device')

  def _action(self, action):
    if action.kind == 'back':
      self._back()
    elif action.kind == 'scroll':
      self.scroll = feature_scroll(self.scroll, action.direction, len(self._rows()))
    elif action.row in self._rows() and action.kind == 'action':
      route = next((route for route in self.controller.routes if route['routeId'] == action.row.key), None)
      if route is not None and self.controller.select(route):
        self.page, self.scroll = 'detail', 0
    self.input.cancel()

  def _back(self):
    self.press = self.seek_preview = None
    self.input.cancel()
    if self.page == 'viewer':
      if self.controller.stop():
        self.stopping = True
        self.page = 'detail'
        self._clear_frame()
    elif self.page == 'detail':
      self.page, self.scroll = 'routes', 0
    else:
      self.on_close()

  def _compact_cards(self):
    rows = self._rows()
    signature = (self.page, rows, self.controller.busy, self.controller.error)
    if signature == self.card_signature or any(event.left_down for event in gui_app.mouse_events):
      return
    self.card_signature = signature
    cards = []
    for row in rows:
      detail = ' - '.join(part for part in (row.value, row.reason) if part).lower()
      if row.actions:
        button = BigButton(row.label.lower(), detail, scroll=True)
        button.set_enabled(row.available and not self.controller.busy)
        button.set_click_callback(lambda row=row: self._action(FeatureUiAction('action', row=row)))
      else:
        button = GreyBigButton(row.label.lower(), detail)
      cards.append(button)
    if self.controller.error:
      cards.append(GreyBigButton('replay unavailable', self.controller.error))
    self.cards._scroller.items.clear()
    self.cards._scroller.add_widgets(cards)

  def _render(self, rect):
    if self.profile == Profile.COMPACT and self.page == 'routes':
      self._compact_cards()
      self.cards.render(rect)
      return
    with placed_at(rect, self._parent_rect):
      rl.draw_rectangle(0, 0, *self.profile.size, PANEL_BG)
      if self.page == 'viewer':
        self._render_viewer()
      elif self.page == 'detail':
        self._render_detail()
      elif self.profile == Profile.LARGE:
        self.view.render(self._state(), self.input.drag_x)

  def _button(self, label, bounds, enabled=True):
    rect = rl.Rectangle(*bounds)
    held = self.press is not None and self.press[2] == label
    draw_rounded_fill(rect, CONTROL_PRESSED_BG if held else CONTROL_BG if self.controls else rl.Color(8, 8, 10, 210))
    draw_rounded_stroke(rect, ACCENT if held else CONTROL_BORDER)
    size = (48 if self.page == 'detail' else 38) if self.profile == Profile.LARGE else 22
    size = min(size, size * (rect.width - 12) / max(1, self.fonts.measure(label, FontRole.MEDIUM, size).width))
    measured = self.fonts.measure(label, FontRole.MEDIUM, size)
    self.fonts.draw(label, FontRole.MEDIUM, size, rect.x + (rect.width - measured.width) / 2,
                    rect.y + (rect.height - measured.height) / 2, TEXT_PRIMARY if enabled else TEXT_MUTED)

  def _transport(self):
    large = self.profile == Profile.LARGE
    timeline = (100, 916, 1960, 48) if large else (16, 64, 504, 48)
    state = self.controller.status
    labels = ('-10 s' if large else '-10', 'Play' if state.get('paused') else 'Pause',
              '+10 s' if large else '+10', f"{state.get('rate', 1):g}x", 'Stop')
    return timeline, tuple((label, (100 + index * 400, 976, 360, 84) if large else
                                    (16 + index * 102, 132, 96, 76)) for index, label in enumerate(labels))

  def _collapsed_stop_bounds(self):
    return (1950, 16, 180, 76) if self.profile == Profile.LARGE else (448, 8, 80, 44)

  def _render_viewer(self):
    owner = self.controller
    large = self.profile == Profile.LARGE
    bounds = rl.Rectangle(0, 0, *self.profile.size)
    frame = owner.frame
    if frame is not None and owner.available and not ui_state.started:
      key = (frame.session_id, frame.epoch, frame.frame_id)
      if key != self.frame_key:
        if self.frame_key is None:
          self.last_touch = time.monotonic()
        if self.texture is None or (self.texture.width, self.texture.height) != (frame.width, frame.height):
          self._clear_frame()
          self.texture = rl.load_texture_from_image(rl.Image(rl.ffi.NULL, frame.width, frame.height, 1,
                                                            rl.PixelFormat.PIXELFORMAT_UNCOMPRESSED_R8G8B8A8))
          rl.set_texture_filter(self.texture, rl.TextureFilter.TEXTURE_FILTER_BILINEAR)
        rl.update_texture(self.texture, rl.ffi.cast('void *', rl.ffi.from_buffer(frame.data)))
        self.frame_key = key
      rl.draw_texture_pro(self.texture, rl.Rectangle(0, 0, frame.width, frame.height), bounds, rl.Vector2(0, 0), 0, rl.WHITE)
    self.controls = ((large or frame is not None) and
                     (owner.status.get('state') != 'playing' or time.monotonic() - self.last_touch < 3))
    if self.press:
      self.controls = self.press[4]
    self.fonts.draw('REPLAY', FontRole.SEMI_BOLD, 36 if large else 18, 30 if large else 12, 30 if large else 12, ACCENT)
    if not self.controls:
      self._button('Stop', self._collapsed_stop_bounds(), not owner.busy)
      self._render_loading()
      return
    rl.draw_rectangle(0, 872 if large else 32, self.profile.size[0], 208, rl.Color(8, 8, 10, 190))
    timeline, buttons = self._transport()
    x, y, width, height = timeline
    start, end, position = (owner.status.get(key) or 0 for key in ('start', 'end', 'position'))
    displayed = self.seek_preview if self.seek_preview is not None else position
    amount = max(0, min(1, (displayed - start) / (end - start))) if end > start else 0
    rl.draw_rectangle(round(x), round(y + height / 2 - 3), round(width), 6, CONTROL_BG)
    ranges = owner.status.get('seekRanges') or ((start, end),)
    if end > start:
      for left, right in ranges:
        left_x = round(x + width * (left - start) / (end - start))
        rl.draw_rectangle(left_x, round(y + height / 2 - 3),
                          max(1, round(width * (right - left) / (end - start))), 6, CONTROL_BORDER)
        progress = max(0, min(right, displayed) - left)
        rl.draw_rectangle(left_x, round(y + height / 2 - 3), round(width * progress / (end - start)), 6, ACCENT)
    rl.draw_circle(round(x + width * amount), round(y + height / 2), 9 if large else 7, ACCENT)
    timing = f'{duration(displayed)} / {duration(end)}' if end > start else ''
    if end > start and not any(left <= displayed <= right for left, right in ranges):
      timing += ' - Unavailable gap'
    self.fonts.draw(timing, FontRole.MEDIUM, 26 if large else 18,
                    x, y - 26 if large else 36, TEXT_PRIMARY)
    enabled = owner.available and not owner.busy and owner.status.get('state') in ('playing', 'paused', 'buffering', 'ended')
    for label, button in buttons:
      self._button(label, button, not owner.busy if label == 'Stop' else enabled)
    self._render_loading()

  def _render_loading(self):
    owner = self.controller
    if owner.frame is not None and owner.available and not ui_state.started:
      return
    large = self.profile == Profile.LARGE
    size, radius = (32, 40) if large else (18, 14)
    center = rl.Vector2(self.profile.size[0] / 2, self.profile.size[1] / 2)
    loading = not owner.error and owner.available and owner.status.get('state') in ('preparing', 'seeking', 'buffering', 'playing', 'paused')
    message = owner.error or f"Replay {owner.status.get('state', 'unavailable')}"
    if loading:
      angle = time.monotonic() * 240 % 360
      rl.draw_ring(center, radius - (5 if large else 3), radius, angle, angle + 270, 48, TEXT_PRIMARY)
      message = 'Replay preparing' if owner.status.get('state') == 'preparing' else 'Replay loading'
    message = elide_text(self.fonts, message, FontRole.MEDIUM, size, self.profile.size[0] - 40)
    width = self.fonts.measure(message, FontRole.MEDIUM, size).width
    self.fonts.draw(message, FontRole.MEDIUM, size, center.x - width / 2,
                    center.y + radius + (20 if large else 8) if loading else center.y, TEXT_PRIMARY)

  @staticmethod
  def _inside(x, y, bounds):
    left, top, width, height = bounds
    return left <= x <= left + width and top <= y <= top + height

  def _target(self, x, y):
    if self.page == 'detail':
      return next((label for label, bounds, enabled, _ in self._detail_buttons() if enabled and self._inside(x, y, bounds)), None)
    if self.page != 'viewer':
      return None
    if not self.controls:
      return 'Stop' if self._inside(x, y, self._collapsed_stop_bounds()) else 'show'
    timeline, buttons = self._transport()
    if self._inside(x, y, timeline):
      return 'seek'
    return next((label for label, bounds in buttons if self._inside(x, y, bounds)), 'show')

  def _handle_mouse_press(self, pos):
    x, y = pos.x - self.rect.x, pos.y - self.rect.y
    self.last_touch = time.monotonic()
    if self.page in ('viewer', 'detail'):
      self.press = (x, y, self._target(x, y), self.controller.status.get('epoch'), self.controls)
      self._move_seek(x)
    elif self.view:
      self.input.press(x, y, self._state())

  def _move_seek(self, x):
    if self.press and self.press[2] == 'seek':
      left, _, width, _ = self._transport()[0]
      start, end = self.controller.status.get('start') or 0, self.controller.status.get('end') or 0
      self.seek_preview = start + max(0, min(1, (x - left) / width)) * (end - start)

  def _handle_mouse_event(self, event):
    if event.left_released and not rl.check_collision_point_rec(event.pos, self._hit_rect):
      self.press = self.seek_preview = None
      self.input.cancel()
    if event.left_down:
      x, y = event.pos.x - self.rect.x, event.pos.y - self.rect.y
      if self.press:
        px, py, target, epoch, _ = self.press
        tolerance = 36 if self.profile == Profile.LARGE else 5
        if epoch != self.controller.status.get('epoch') or (target != 'seek' and math.hypot(x - px, y - py) > tolerance):
          self.press = self.seek_preview = None
        else:
          self._move_seek(x)
      elif self.view:
        self.input.move(x, y, self._state(), event.t)

  def _handle_mouse_release(self, pos):
    x, y = pos.x - self.rect.x, pos.y - self.rect.y
    if self.page == 'detail':
      held, self.press = self.press, None
      if held and held[3] == self.controller.status.get('epoch') and held[2] == self._target(x, y):
        for label, _, enabled, callback in self._detail_buttons():
          if enabled and label == held[2]:
            callback()
            break
      return
    if self.page != 'viewer':
      if self.view:
        self.input.release(x, y, self._state(), time.monotonic())
      return
    held, self.press = self.press, None
    if held and held[3] == self.controller.status.get('epoch'):
      self.last_touch = time.monotonic()
      target = held[2]
      if target == 'seek' and self.seek_preview is not None:
        self.controller.seek(self.seek_preview)
      elif target == 'show':
        self.last_touch = -math.inf if held[4] else time.monotonic()
      elif target == self._target(x, y):
        state = self.controller.status
        if target == 'Stop':
          self._back()
        elif target in ('Play', 'Pause'):
          self.controller.control('pause', paused=not bool(state.get('paused')))
        elif target.startswith(('-10', '+10')):
          self.controller.seek(state.get('position', 0) + (-10 if target.startswith('-') else 10))
        elif target.endswith('x'):
          rates = (0.5, 1, 2)
          self.controller.control('rate', rate=rates[(rates.index(state.get('rate', 1)) + 1) % len(rates)])
    self.seek_preview = None


class ReplayCompactPage(NavWidget):
  def __init__(self, session, controller=None):
    super().__init__()
    self.content = self._child(ReplayPage(session, self.dismiss, controller))
    self.content.set_enabled(lambda: self.enabled and not self.is_dismissing)
    self.content.stack_widget = self

  def _back_enabled(self):
    return self.content.page != 'viewer'

  def _handle_mouse_event(self, event):
    was_dismissing = self._playing_dismiss_animation
    super()._handle_mouse_event(event)
    if event.left_released and not was_dismissing and self._playing_dismiss_animation and self.content.page == 'detail':
      self._playing_dismiss_animation = False
      self.content._back()

  def _render(self, rect):
    self.content.render(rect)


def open_replay(session):
  page = ReplayCompactPage(session) if session.profile == Profile.COMPACT else ReplayPage(session, gui_app.pop_widget)
  page.set_rect(rl.Rectangle(0, 0, *session.profile.size))
  gui_app.push_widget(page)


def replay_entry(session):
  button = BigButton('replay', 'recorded driving routes on this device')
  button.set_click_callback(lambda: open_replay(session))
  return button
