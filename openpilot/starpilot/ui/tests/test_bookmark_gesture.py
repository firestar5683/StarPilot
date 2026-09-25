from types import SimpleNamespace as NS
from unittest.mock import Mock, PropertyMock, patch

import pyray as rl
import pytest

from openpilot.selfdrive.ui.mici.onroad import augmented_road_view as road
from openpilot.system.ui.lib.application import MouseEvent, MousePos
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.widgets.scroller import Scroller
from openpilot.starpilot.ui.runtime_app import StarMiciMainLayout, StarShellPage
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.shell import ShellMode


class EmptyPage(Widget):
  def _render(self, rect):
    pass


@pytest.fixture
def navigation():
  callback = Mock()
  with patch.object(road.gui_app, 'texture', return_value=NS(width=180, height=180)):
    bookmark = road.BookmarkIcon(callback)
    session = NS(profile=Profile.COMPACT, camera_owner=NS(_bookmark_icon=bookmark), render=Mock(), cancel=Mock(),
                 press=Mock(), move=Mock(), release=Mock(return_value=False))
    page = StarShellPage(session, ShellMode.ONROAD)
    layout = StarMiciMainLayout.__new__(StarMiciMainLayout)
    Scroller.__init__(layout, snap_items=True, spacing=0, pad=0, scroll_indicator=False, edge_shadows=False)
  home = EmptyPage()
  bounds = rl.Rectangle(0, 0, 536, 240)
  for item in (layout, home, page):
    item.set_rect(bounds)
  layout._setup = True
  layout._alerts_layout = Mock()
  layout._car_onroad_layout = page
  layout._native_onroad = NS(_bookmark_icon=bookmark)
  layout._scroller.add_widgets([home, page])
  layout._scroller.set_scrolling_enabled(lambda: not bookmark.is_swiping_left())
  layout._scroller.scroll_panel.set_offset(-536)
  frame_number = 0
  def frame(*events):
    nonlocal frame_number
    frame_number += 1
    with patch.object(type(road.gui_app), 'frame', new_callable=PropertyMock, return_value=frame_number), \
         patch.object(type(road.gui_app), 'mouse_events', new_callable=PropertyMock, return_value=list(events)):
      layout.render()
  def event(x, y=100, *, pressed=False, down=False, released=False):
    return MouseEvent(MousePos(x, y), 0, pressed, released, down, frame_number / 60)
  with patch.object(road, 'ui_state', NS(started=True)), patch.object(bookmark, '_render'), \
       patch.object(rl, 'begin_scissor_mode'), patch.object(rl, 'end_scissor_mode'), \
       patch.object(rl, 'get_frame_time', return_value=1/60):
    frame()
    yield NS(frame=frame, event=event, callback=callback, page=page, layout=layout, bookmark=bookmark)


@pytest.mark.parametrize('batched', [False, True])
def test_deliberate_left_swipe_claims_before_real_scroller(navigation, batched):
  n = navigation
  events = [n.event(400, pressed=True, down=True), n.event(380, down=True), n.event(250, down=True), n.event(250, released=True)]
  if batched:
    n.frame(*events)
  else:
    for event in events:
      n.frame(event)
  n.callback.assert_called_once()
  assert n.page.rect.x == 0
  n.frame(n.event(250, released=True))
  n.callback.assert_called_once()


def test_menu_return_swipe_cannot_create_bookmark(navigation):
  n = navigation
  n.layout._scroller.scroll_panel.set_offset(0)
  n.frame()
  n.frame(n.event(400, pressed=True, down=True))
  n.frame(n.event(320, down=True))
  n.frame(n.event(150, down=True))
  n.frame(n.event(20, down=True))
  n.frame(n.event(20, released=True))
  for _ in range(120):
    n.frame()
  n.callback.assert_not_called()
  assert abs(n.page.rect.x) < 1


@pytest.mark.parametrize('cancel', ['hide', 'right', 'vertical', 'offroad', 'disabled', 'parent_disabled'])
def test_navigation_or_revoked_touch_cannot_finish_bookmark(navigation, cancel):
  n = navigation
  n.frame(n.event(400, pressed=True, down=True))
  if cancel == 'hide':
    n.page.hide_event()
  elif cancel == 'right':
    n.frame(n.event(440, down=True))
  elif cancel == 'vertical':
    n.frame(n.event(390, 40, down=True))
  elif cancel == 'offroad':
    road.ui_state.started = False
  elif cancel == 'disabled':
    n.bookmark.set_enabled(False)
  else:
    n.layout.set_enabled(False)
  n.frame(n.event(250, down=True))
  n.frame(n.event(250, released=True))
  n.callback.assert_not_called()
