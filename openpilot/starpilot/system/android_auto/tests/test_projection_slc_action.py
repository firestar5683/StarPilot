import tempfile
from pathlib import Path

from openpilot.starpilot.system.android_auto.projection_slc_action import SlcActionReceiver, SlcActionSender
from openpilot.starpilot.ui.onroad_state import SlcActionKind, SlcUiRequest


def test_request_round_trips_and_malformed_input_is_dropped():
  # AF_UNIX paths are short on macOS; pytest's tmp_path is not.
  path = Path(tempfile.mkdtemp(dir='/tmp')) / 's.sock'
  receiver, sender = SlcActionReceiver(path), SlcActionSender(path)
  try:
    request = SlcUiRequest(SlcActionKind.ADOPT, 'drive-1', 7, 9, 22.0)
    assert sender.send(request)
    sender.sock.sendto(b'not json', str(path))
    sender.sock.sendto(b'{"kind": "explode"}', str(path))
    assert receiver.drain() == [request]
    assert receiver.drain() == []
  finally:
    sender.close()
    receiver.close()


def test_experimental_request_round_trips_and_rejects_malformed_values():
  from openpilot.starpilot.ui.onroad_state import OnroadRequest
  path = Path(tempfile.mkdtemp(dir='/tmp')) / 's.sock'
  receiver, sender = SlcActionReceiver(path), SlcActionSender(path)
  try:
    # The native token is not visible to the projection and is not sent.
    assert sender.send(OnroadRequest('set_experimental', True, 'projection-token'))
    assert not sender.send(OnroadRequest('set_experimental', None))
    assert not sender.send(OnroadRequest('open_settings', True))
    sender.sock.sendto(b'{"kind": "set_experimental", "value": "yes"}', str(path))
    sender.sock.sendto(b'{"kind": "set_experimental"}', str(path))
    sender.sock.sendto(b'[1]', str(path))
    assert receiver.drain() == [OnroadRequest('set_experimental', True)]
  finally:
    sender.close()
    receiver.close()


def _native_session(experimental_enabled, binding):
  from types import SimpleNamespace as NS
  from unittest.mock import Mock
  from openpilot.starpilot.favorites.actions import EXPERIMENTAL
  from openpilot.starpilot.ui import runtime_app
  session = runtime_app.StarShellSession.__new__(runtime_app.StarShellSession)
  session.snapshot = Mock(return_value=NS(onroad=NS(experimental_enabled=experimental_enabled)))
  session._native_favorite_actions = lambda: {EXPERIMENTAL: binding} if binding is not None else {}
  session._unavailable = Mock()
  session.slc_actions = Mock()
  return session


def _binding(available=True, result=True):
  from types import SimpleNamespace as NS
  from unittest.mock import Mock
  return NS(available=available, invoke=Mock(return_value=result), token='native')


def test_native_applies_projection_experimental_tap_only_against_live_state():
  binding = _binding()
  session = _native_session(False, binding)
  session._projection_experimental(True)
  binding.invoke.assert_called_once_with()
  session._unavailable.assert_not_called()

  # Already in the requested state (a stale or duplicate tap): no second toggle.
  binding = _binding()
  session = _native_session(True, binding)
  session._projection_experimental(True)
  binding.invoke.assert_not_called()
  session._unavailable.assert_called_once()

  for binding in (None, _binding(available=False), _binding(result=False)):
    session = _native_session(False, binding)
    session._projection_experimental(True)
    session._unavailable.assert_called_once()


def test_native_poll_routes_experimental_and_speed_limit_requests(monkeypatch):
  from types import SimpleNamespace as NS
  from unittest.mock import Mock
  from openpilot.starpilot.ui import runtime_app
  from openpilot.starpilot.ui.onroad_state import OnroadRequest
  slc = SlcUiRequest(SlcActionKind.ACCEPT, 'drive-1', 7, 9, 22.0)
  session = _native_session(False, _binding())
  session._projection_slc = NS(drain=lambda: [OnroadRequest('set_experimental', True), slc])
  session._projection_experimental = Mock()
  monkeypatch.setattr(runtime_app, 'ui_state', NS(started=True, replay_clock=None))
  session._poll_projection_slc(0)
  session._projection_experimental.assert_called_once_with(True)
  session.slc_actions.dispatch.assert_called_once_with(slc)

  session._projection_experimental.reset_mock()
  monkeypatch.setattr(runtime_app, 'ui_state', NS(started=False, replay_clock=None))
  session._poll_projection_slc(0)
  session._projection_experimental.assert_not_called()


def test_projected_wheel_tap_hits_the_drawn_wheel_on_a_1280x720_head_unit():
  from dataclasses import replace
  from openpilot.starpilot.system.android_auto.projection_geometry import projection_geometry
  from openpilot.starpilot.system.android_auto.projection_layout import default_layout_for_viewport, projection_customization
  from openpilot.starpilot.ui.onroad_customization import default_document, offset, widget_size
  from openpilot.starpilot.ui.onroad_state import OnroadInput, OnroadRequest, OnroadState, SpeedLimitObservation
  geometry = projection_geometry(1280, 720)
  width = geometry.logical_width
  assert width == 1920
  customization = projection_customization(default_layout_for_viewport((width, geometry.logical_height)), default_document())
  state = replace(OnroadState(True, True, 15, 80, SpeedLimitObservation()), customization=customization,
                  experimental_available=True, viewport_width=width)
  # Where SteeringWheelWidget.render draws it on a canvas `width` wide.
  dx, dy = offset(customization, 'large', 'steering_wheel')
  size, _ = widget_size(customization, 'large', 'steering_wheel')
  x, y = width - 146 - 96 + dx + size / 2, 45 + dy + size / 2
  emitted = []
  gesture = OnroadInput(emitted.append)
  gesture.press(x, y, state)
  assert gesture.claimed
  gesture.release(x, y, state)
  assert emitted == [OnroadRequest('set_experimental', True, '')]
  # The comma's default width put the target off the drawn wheel.
  gesture.press(x, y, replace(state, viewport_width=2160.0))
  assert not gesture.claimed
