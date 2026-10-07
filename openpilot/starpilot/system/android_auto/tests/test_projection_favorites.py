"""Favorite actions use real navigation storage, layouts and the touch transport."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import pytest

from openpilot.starpilot.navigation.owner import NavigationOwner, destination
from openpilot.starpilot.system.android_auto.current_car_ui import projected_touches
from openpilot.starpilot.system.android_auto.projection_favorites import ProjectionFavorites
from openpilot.starpilot.system.android_auto.projection_geometry import projection_geometry
from openpilot.starpilot.system.android_auto.projection_layout import (
  FAVORITE_WIDGETS, default_layout_for_viewport, layout_metadata_for_viewport, projection_customization, validate_layout_for_viewport,
)
from openpilot.starpilot.system.android_auto.touch import InputConfig, TouchMapper, TouchReceiver, TouchSender
from openpilot.starpilot.system.android_auto.wire import field
from openpilot.starpilot.ui.onroad_customization import default_document

VIEWPORT = (2880, 1080)


@pytest.fixture
def favorites(tmp_path):
  owner = NavigationOwner(tmp_path, runtime_source=dict, transient_root=tmp_path / 'transient')
  owner._is_metric = lambda: True
  home = dict(destination({'name': 'My home', 'latitude': 36.1, 'longitude': -115.1}), label='home')
  work = dict(destination({'name': 'My work', 'latitude': 36.2, 'longitude': -115.2}), label='work')
  owner.path.write_text(json.dumps({'version': 1, 'revision': 'initial', 'enabled': True, 'token': 'test-token',
                                    'destination': None, 'favorites': [home, work], 'recents': []}))
  control = ProjectionFavorites(lambda: True, owner)
  control.refresh(force=True)
  yield control
  control.close()


def state(*, ordered=False):
  layout = default_layout_for_viewport(VIEWPORT)
  for key in FAVORITE_WIDGETS:
    layout['widgets'][key]['enabled'] = True
  if ordered:
    layout['widgetOrder'] = layout_metadata_for_viewport(VIEWPORT)['widgetOrder']
  return NS(customization=projection_customization(layout, default_document()), alert=NS(size='none'))


def point(state, key):
  placed = state.customization['layouts']['large'][key]
  return placed['x'] + 160, placed['y'] + 55


def tap(control, state, key):
  x, y = point(state, key)
  control.touch('down', x, y, state, 1)
  control.touch('up', x, y, state, 1)


@pytest.mark.parametrize('ordered', [True, False])
def test_home_work_start_replace_and_end_navigation(favorites, ordered):
  view = state(ordered=ordered)
  tap(favorites, view, 'nav_home')
  doc = favorites.owner.read()
  assert doc['destination']['name'] == 'My home'
  assert favorites.action('nav_home')[0] == 'end'
  assert favorites.action('nav_work')[0] == 'start'
  assert doc['recents'][0]['name'] == 'My home'
  tap(favorites, view, 'nav_work')
  assert favorites.owner.read()['destination']['name'] == 'My work'
  assert favorites.action('nav_home')[0] == 'start'
  tap(favorites, view, 'nav_work')
  assert favorites.owner.read()['destination'] is None
  assert favorites.action('nav_work')[0] == 'start'


@pytest.mark.parametrize('change', ['drag', 'cancel', 'offroad', 'drive', 'alert', 'remove', 'relabeled', 'external_route'])
def test_changed_or_cancelled_press_does_not_navigate(favorites, change):
  view = state()
  x, y = point(view, 'nav_home')
  favorites.touch('down', x, y, view, 1)
  if change == 'drag':
    favorites.touch('move', x + 40, y, view, 1)
  elif change == 'cancel':
    favorites.touch('cancel', 0, 0, view, 1)
  elif change == 'offroad':
    favorites.authorized = lambda: False
  elif change == 'alert':
    view.alert.size = 'full'
  elif change == 'remove':
    view.customization['layouts']['large']['nav_home']['enabled'] = False
  elif change == 'relabeled':
    favorites.owner.label_favorite(favorites.document['favorites'][0]['id'], None, 'initial', True)
  elif change == 'external_route':
    favorites.owner.select(favorites.document['favorites'][1], 'initial', True)
  expected = favorites.owner.read()
  favorites.touch('up', x, y, view, 2 if change == 'drive' else 1)
  assert favorites.owner.read() == expected


def test_unconfigured_and_disabled_navigation_do_not_write(favorites):
  view = state()
  for doc in [dict(favorites.document, enabled=False), dict(favorites.document, token=''), dict(favorites.document, favorites=[])]:
    favorites.owner.path.write_text(json.dumps(doc))
    tap(favorites, view, 'nav_home')
    assert favorites.owner.read()['destination'] is None
  # Ending a selected route still works after navigation has been disabled.
  doc = dict(favorites.document, favorites=[dict(destination({'name': 'Home', 'latitude': 1, 'longitude': 2}), label='home')])
  doc['destination'] = doc['favorites'][0]
  favorites.owner.path.write_text(json.dumps(doc))
  tap(favorites, view, 'nav_home')
  assert favorites.owner.read()['destination'] is None


def test_overlap_uses_saved_order_and_removed_widget_cannot_intercept(favorites):
  view = state(ordered=True)
  placements = view.customization['layouts']['large']
  placements['nav_work'].update(x=placements['nav_home']['x'], y=placements['nav_home']['y'])
  tap(favorites, view, 'nav_home')
  assert favorites.owner.read()['destination']['name'] == 'My work'
  order = view.customization['widgetOrder']['large']
  order.remove('nav_home')
  order.append('nav_home')
  tap(favorites, view, 'nav_home')
  assert favorites.owner.read()['destination']['name'] == 'My home'
  placements['nav_home']['enabled'] = False
  tap(favorites, view, 'nav_work')
  assert favorites.owner.read()['destination']['name'] == 'My work'


def test_old_layout_migrates_favorites_without_enabling_or_reordering_existing_widgets():
  layout = default_layout_for_viewport(VIEWPORT)
  layout['widgetOrder'] = layout_metadata_for_viewport(VIEWPORT)['widgetOrder']
  for key in FAVORITE_WIDGETS:
    layout['widgets'].pop(key)
    layout['widgetOrder'].remove(key)
  original = copy.deepcopy(layout)
  migrated = validate_layout_for_viewport(layout, VIEWPORT)
  assert migrated['widgetOrder'] == [*original['widgetOrder'], *FAVORITE_WIDGETS]
  assert all(not migrated['widgets'][key]['enabled'] for key in FAVORITE_WIDGETS)
  assert {key: placed for key, placed in migrated['widgets'].items() if key not in FAVORITE_WIDGETS} == original['widgets']
  assert layout == original
  migrated['widgets']['nav_home'].update(x=100, y=200, enabled=True)
  assert validate_layout_for_viewport(migrated, VIEWPORT) == migrated


def test_head_unit_touch_packet_reaches_real_navigation_owner(favorites):
  view = state()
  x, y = point(view, 'nav_home')
  # 1280x720 frame with 240 vertical margin -> a 2880x1080 scene.
  config = InputConfig(touch_width=1280, touch_height=720)
  mapper = TouchMapper(config, 1280, 720, 0, 240)
  geometry = projection_geometry(1280, 720, 0, 240)
  with tempfile.TemporaryDirectory(prefix='aa-touch-') as directory:
    path = str(Path(directory) / 'touch.sock')
    receiver, sender = TouchReceiver(path), TouchSender(path)
    try:
      for action in (0, 1):
        location = field(1, round(x / VIEWPORT[0] * 1280)) + field(2, round(y / VIEWPORT[1] * 480 + 120)) + field(3, 0)
        packet = field(3, field(1, location) + field(3, action))
        sender.send(mapper.decode(packet))
      for event in projected_touches(receiver.drain(), geometry):
        favorites.touch(event.kind, event.x * VIEWPORT[0], event.y * VIEWPORT[1], view, 1)
      assert favorites.owner.read()['destination']['name'] == 'My home'
    finally:
      sender.close()
      receiver.close()


def test_letterboxed_touches_map_to_scene_and_padding_cancels():
  from openpilot.starpilot.system.android_auto.touch import TouchEvent
  geometry = projection_geometry(1920, 1080, 1800, 0)  # bounded fallback canvas with vertical letterboxing
  events = projected_touches([TouchEvent('down', .5, .5), TouchEvent('down', .5, 0)], geometry)
  assert events == [TouchEvent('down', .5, .5), TouchEvent('cancel', 0, 0)]


def test_current_renderer_enables_touch_forwarding_on_custom_socket():
  from openpilot.starpilot.system.android_auto.view import ViewSource
  from openpilot.starpilot.system.android_auto.frame_source import FrameRequest
  from openpilot.starpilot.system.android_auto.touch import TouchEvent
  process = Mock(pid=123)
  process.poll.return_value = 0
  with patch('openpilot.starpilot.system.android_auto.view.subprocess.Popen', return_value=process) as popen, \
       patch.object(ViewSource, '_consumer', return_value=Mock()), \
       patch('openpilot.starpilot.system.android_auto.view.TouchSender') as sender:
    view = ViewSource('car', FrameRequest(1280, 720, 0, 240, 33333), Mock(), touch_path='/tmp/test-aa-touch')
    assert popen.call_args.args[0][-2:] == ['--touch', '/tmp/test-aa-touch']
    event = TouchEvent('down', .2, .3)
    view.send_touches([event])
    sender.return_value.send.assert_called_once_with([event])
    view.close()
    sender.return_value.close.assert_called_once()
