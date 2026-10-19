"""Mapbox turn-by-turn reaches the car's own displays when the head unit offers the navigation service."""

import pytest

from openpilot.starpilot.system.android_auto import nav_status as ns
from openpilot.starpilot.system.android_auto.session import ProjectionSession
from openpilot.starpilot.system.android_auto.wire import field, parse_fields

GUIDING = {'state': 'guiding', 'metric': False, 'road': 'Main Street', 'type': 'turn', 'modifier': 'left',
           'distance': 400.0, 'remaining': 8000.0, 'duration': 800.0}


class Session:
  def __init__(self, services=(ns.NAVIGATION_SERVICE,), navigation=None):
    self.channels = [{'id': 4, 'services': [3]}, {'id': 12, 'services': list(services), 'navigation': navigation or {}}]
    self.sent = []
    self.focus_sent = []
  def send(self, channel, kind, body=b'', control=False):
    if channel == 0:
      self.focus_sent.append((channel, kind, body))
      return
    self.sent.append((channel, kind, body))


class Feed:
  def __init__(self): self.value, self.closed = None, False
  def snapshot(self): return self.value
  def close(self): self.closed = True


@pytest.fixture
def nav():
  session, feed, now = Session(), Feed(), [100.0]
  stream = ns.NavStatus.create(session, lambda *a, **k: None, feed=feed, clock=lambda: now[0])
  return stream, session, feed, now


def start(stream, session, now):
  stream.service()
  assert session.sent[-1][:2] == (12, ns.MSG_CHANNEL_OPEN_REQUEST)
  assert stream.handle(12, ns.MSG_CHANNEL_OPEN_RESPONSE, {1: [0]})
  assert stream.handle(12, ns.CLUSTER_START, {})
  session.sent.clear()


def tick(stream, now, seconds=1.0):
  now[0] += seconds
  stream.service()


@pytest.mark.parametrize('kind,modifier,expected', [
  ('turn', 'left', (ns.EVENT_TURN, ns.SIDE_LEFT)),
  ('turn', 'slightRight', (ns.EVENT_SLIGHT_TURN, ns.SIDE_RIGHT)),
  ('end of road', 'sharp left', (ns.EVENT_SHARP_TURN, ns.SIDE_LEFT)),
  ('turn', 'uturn', (ns.EVENT_U_TURN, ns.SIDE_UNSPECIFIED)),
  ('continue', 'straight', (ns.EVENT_STRAIGHT, ns.SIDE_UNSPECIFIED)),
  ('new name', 'none', (ns.EVENT_NAME_CHANGE, ns.SIDE_UNSPECIFIED)),
  ('off ramp', 'right', (ns.EVENT_OFF_RAMP, ns.SIDE_RIGHT)),
  ('on ramp', 'slight left', (ns.EVENT_ON_RAMP, ns.SIDE_LEFT)),
  ('merge', 'left', (ns.EVENT_MERGE, ns.SIDE_LEFT)),
  ('fork', 'right', (ns.EVENT_FORK, ns.SIDE_RIGHT)),
  ('roundabout', 'right', (ns.EVENT_ROUNDABOUT_ENTER_AND_EXIT, ns.SIDE_RIGHT)),
  ('exit roundabout', 'left', (ns.EVENT_ROUNDABOUT_EXIT, ns.SIDE_LEFT)),
  ('depart', 'none', (ns.EVENT_DEPART, ns.SIDE_UNSPECIFIED)),
  ('arrive', 'right', (ns.EVENT_DESTINATION, ns.SIDE_RIGHT)),
])
def test_mapbox_maneuvers_map_to_the_cars_events(kind, modifier, expected):
  assert ns.maneuver_event(kind, modifier) == expected


@pytest.mark.parametrize('meters,metric,expected', [
  (180, True, (175000, ns.UNIT_METERS)),
  (740, True, (750000, ns.UNIT_METERS)),
  (1540, True, (1500, ns.UNIT_KILOMETERS_P1)),
  (23000, True, (23000, ns.UNIT_KILOMETERS)),
  (60, False, (200000, ns.UNIT_FEET)),
  (4000, False, (2500, ns.UNIT_MILES_P1)),
  (40000, False, (25000, ns.UNIT_MILES)),
])
def test_distance_is_rounded_like_the_comma_card(meters, metric, expected):
  assert ns.display_distance(meters, metric) == expected


def test_head_unit_descriptor_is_parsed():
  raw = field(1, 500) + field(2, ns.TYPE_IMAGE) + field(3, field(1, 128) + field(2, 64) + field(3, 16))
  assert ns.parse_navigation(raw) == {'min_interval_ms': 500, 'type': ns.TYPE_IMAGE, 'image_width': 64,
                                      'image_height': 128, 'image_depth': 16}


def test_only_head_units_offering_the_service_get_it():
  assert ns.NavStatus.create(Session([3]), lambda *a, **k: None, feed=Feed()) is None


def test_rejected_or_silent_channel_stays_quiet(nav):
  stream, session, feed, now = nav
  stream.service()
  now[0] += ns.STEP_TIMEOUT + 1
  stream.service()
  assert stream.state == 'unavailable'
  feed.value = GUIDING
  tick(stream, now)
  assert len(session.sent) == 1


def test_nothing_is_sent_until_the_car_asks_or_the_grace_passes(nav):
  stream, session, feed, now = nav
  feed.value = GUIDING
  stream.service()
  stream.handle(12, ns.MSG_CHANNEL_OPEN_RESPONSE, {1: [0]})
  session.sent.clear()
  tick(stream, now, 0.5)
  assert session.sent == []
  tick(stream, now, ns.START_GRACE)
  assert [kind for _, kind, _ in session.sent] == [ns.NAV_STATUS, ns.NAV_TURN, ns.NAV_DISTANCE]


def test_a_car_that_stopped_the_cluster_is_not_fed_again(nav):
  stream, session, feed, now = nav
  start(stream, session, now)
  stream.handle(12, ns.CLUSTER_STOP, {})
  feed.value = GUIDING
  tick(stream, now, ns.START_GRACE + 1)
  assert session.sent == []
  stream.handle(12, ns.CLUSTER_START, {})
  tick(stream, now)
  assert [kind for _, kind, _ in session.sent] == [ns.NAV_STATUS, ns.NAV_TURN, ns.NAV_DISTANCE]


def test_route_guidance_then_updates_then_end(nav):
  stream, session, feed, now = nav
  start(stream, session, now)
  tick(stream, now)
  assert [(kind, parse_fields(body)) for _, kind, body in session.sent] == [(ns.NAV_STATUS, {1: [ns.STATUS_INACTIVE]})]
  session.sent.clear()
  feed.value = GUIDING
  tick(stream, now)
  status, turn, distance = session.sent
  assert (status[1], parse_fields(status[2])) == (ns.NAV_STATUS, {1: [ns.STATUS_ACTIVE]})
  assert turn[1] == ns.NAV_TURN
  assert parse_fields(turn[2]) == {1: [b'Main Street'], 2: [ns.SIDE_LEFT], 3: [ns.EVENT_TURN]}
  assert distance[1] == ns.NAV_DISTANCE
  assert parse_fields(distance[2]) == {1: [400], 2: [40], 3: [200], 4: [ns.UNIT_MILES_P1]}
  session.sent.clear()
  tick(stream, now)
  assert session.sent == []  # nothing changed
  feed.value = {**GUIDING, 'distance': 300.0}
  tick(stream, now)
  assert [kind for _, kind, _ in session.sent] == [ns.NAV_DISTANCE]
  session.sent.clear()
  feed.value = {**GUIDING, 'distance': 20.0, 'road': 'Elm Street', 'type': 'arrive', 'modifier': 'right'}
  tick(stream, now)
  assert [kind for _, kind, _ in session.sent] == [ns.NAV_TURN, ns.NAV_DISTANCE]
  session.sent.clear()
  feed.value = {'state': 'routing'}
  tick(stream, now)
  assert parse_fields(session.sent[-1][2]) == {1: [ns.STATUS_REROUTING]}
  feed.value = None
  tick(stream, now)
  tick(stream, now)
  assert parse_fields(session.sent[-1][2]) == {1: [ns.STATUS_INACTIVE]}
  assert [kind for _, kind, _ in session.sent].count(ns.NAV_STATUS) == 2


def test_distance_updates_respect_the_cars_minimum_interval():
  session, feed, now = Session(navigation={'min_interval_ms': 5000, 'type': ns.TYPE_ENUM}), Feed(), [100.0]
  stream = ns.NavStatus.create(session, lambda *a, **k: None, feed=feed, clock=lambda: now[0])
  start(stream, session, now)
  feed.value = GUIDING
  tick(stream, now)
  session.sent.clear()
  feed.value = {**GUIDING, 'distance': 300.0}
  tick(stream, now, 1.0)
  assert session.sent == []
  tick(stream, now, 5.0)
  assert [kind for _, kind, _ in session.sent] == [ns.NAV_DISTANCE]


def test_image_head_units_get_the_turn_arrow_at_their_size():
  session, feed, now = Session(navigation={'type': ns.TYPE_IMAGE, 'image_width': 64, 'image_height': 64}), Feed(), [100.0]
  stream = ns.NavStatus.create(session, lambda *a, **k: None, feed=feed, clock=lambda: now[0])
  start(stream, session, now)
  feed.value = GUIDING
  tick(stream, now)
  turn = parse_fields(next(body for _, kind, body in session.sent if kind == ns.NAV_TURN))
  assert turn[4][0].startswith(b'\x89PNG')


def test_enum_head_units_get_no_image(nav):
  stream, session, feed, now = nav
  start(stream, session, now)
  feed.value = GUIDING
  tick(stream, now)
  assert 4 not in parse_fields(next(body for _, kind, body in session.sent if kind == ns.NAV_TURN))


def test_session_hands_the_nav_channel_to_nav_status():
  session = ProjectionSession.__new__(ProjectionSession)
  session.audio, session.mode, session.input_channel = None, None, 3
  got = []
  session.nav = type('N', (), {'handle': lambda self, c, k, f: got.append((c, k)) or c == 12})()
  session.handle(12, ns.CLUSTER_START, b'')
  assert got == [(12, ns.CLUSTER_START)]


def test_focus_is_requested_before_cluster_start_and_released_at_route_end(nav):
  stream, session, feed, now = nav
  stream.service()
  stream.handle(12, ns.MSG_CHANNEL_OPEN_RESPONSE, {1: [0]})
  feed.value = GUIDING
  tick(stream, now, 0.25)
  assert session.focus_sent == [(0, 0x0d, b'\x08\x02')]
  assert not any(kind == ns.NAV_TURN for _, kind, _ in session.sent)
  stream.handle(0, 0x0e, {1: [2]})
  stream.handle(12, ns.CLUSTER_START, {})
  tick(stream, now)
  tick(stream, now)
  assert len(session.focus_sent) == 1
  feed.value = {'state': 'routing'}
  tick(stream, now)
  assert len(session.focus_sent) == 1
  feed.value = None
  tick(stream, now)
  assert session.focus_sent[-1] == (0, 0x0d, b'\x08\x01')
  feed.value = GUIDING
  tick(stream, now)
  assert session.focus_sent[-1] == (0, 0x0d, b'\x08\x02')


def test_native_focus_pauses_updates_and_projected_focus_resends(nav):
  stream, session, feed, now = nav
  start(stream, session, now)
  feed.value = GUIDING
  tick(stream, now)
  session.sent.clear()
  assert stream.handle(0, 0x0e, {1: [1]})
  feed.value = {**GUIDING, 'distance': 100.0}
  tick(stream, now)
  assert session.sent == []
  assert stream.handle(0, 0x0e, {1: [2]})
  tick(stream, now)
  assert [kind for _, kind, _ in session.sent] == [ns.NAV_STATUS, ns.NAV_TURN, ns.NAV_DISTANCE]


def test_repeated_cluster_start_resends_current_guidance(nav):
  stream, session, feed, now = nav
  start(stream, session, now)
  feed.value = GUIDING
  tick(stream, now)
  session.sent.clear()
  stream.handle(12, ns.CLUSTER_START, {})
  tick(stream, now)
  assert [kind for _, kind, _ in session.sent] == [ns.NAV_STATUS, ns.NAV_TURN, ns.NAV_DISTANCE]


def test_legacy_distance_matches_captured_phone_packet():
  assert ns.distance_message(13925, 517, True) == bytes.fromhex('08 e5 6c 10 85 04 18 b0 6d 20 02')


def test_non_square_cluster_image_uses_descriptor_width_and_height():
  import io
  from PIL import Image
  options = ns.parse_navigation(bytes.fromhex('08 f4 03 10 01 1a 05 08 40 10 80 01'))
  with Image.open(io.BytesIO(ns.turn_image('turn', 'left', options['image_width'], options['image_height']))) as icon:
    assert icon.size == (128, 64)


def test_projection_session_dispatches_navigation_focus(nav):
  stream, _, _, _ = nav
  session = ProjectionSession.__new__(ProjectionSession)
  session.audio, session.mode, session.nav = None, None, stream
  session.handle(0, 0x0e, b'\x08\x02')
  assert stream.focus == ns.FOCUS_PROJECTED
