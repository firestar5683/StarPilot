"""Bookmark taps reach the existing native UI action, without duplicate IPC publishers."""
import ast
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import pytest

from openpilot.starpilot.favorites.actions import BOOKMARK
from openpilot.starpilot.system.android_auto.projection_bookmark import BookmarkReceiver, BookmarkSender, MAX_AGE_NS


@pytest.fixture
def transport():
  # macOS Unix sockets have a short path limit; pytest's per-test paths exceed it.
  with tempfile.TemporaryDirectory(prefix='aa-bm-', dir='/tmp') as directory:
    path = Path(directory) / 'bookmark.sock'
    receiver, sender = BookmarkReceiver(path), BookmarkSender(path)
    try:
      yield receiver, sender
    finally:
      sender.close()
      receiver.close()
    assert not path.exists()


def native_poll():
  # Exercise the production native dispatch without loading device-only UI/IPC libraries.
  source = Path(__file__).parents[3] / 'ui/runtime_app.py'
  tree = ast.parse(source.read_text())
  method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == '_poll_projection_bookmark')
  namespace = {'BOOKMARK': BOOKMARK, 'ui_state': NS(started=True, started_frame=1, sm=NS(logMonoTime={'carState': 50})),
               'current_message': Mock(return_value=object())}
  exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
  return namespace


def test_request_dispatches_only_the_native_bookmark_action(transport):
  receiver, sender = transport
  namespace = native_poll()
  invoke = Mock(return_value=True)
  session = NS(_projection_bookmarks=receiver, _favorite_authority=lambda: True,
               _native_favorite_actions=lambda: {BOOKMARK: NS(available=True, invoke=invoke)})
  with patch('time.monotonic_ns', return_value=100):
    assert sender.send(50)
  namespace['_poll_projection_bookmark'](session, 101)
  invoke.assert_called_once_with()
  namespace['_poll_projection_bookmark'](session, 102)
  invoke.assert_called_once_with()


@pytest.mark.parametrize('block', ['offroad', 'authority', 'stale_car', 'unavailable_action'])
def test_native_ui_rechecks_authority_and_consumes_blocked_requests(transport, block):
  receiver, sender = transport
  namespace = native_poll()
  invoke = Mock()
  session = NS(_projection_bookmarks=receiver, _favorite_authority=lambda: block != 'authority',
               _native_favorite_actions=lambda: {BOOKMARK: NS(available=block != 'unavailable_action', invoke=invoke)})
  namespace['ui_state'].started = block != 'offroad'
  if block == 'stale_car':
    namespace['current_message'].return_value = None
  with patch('time.monotonic_ns', return_value=100):
    assert sender.send(50)
  namespace['_poll_projection_bookmark'](session, 101)
  invoke.assert_not_called()
  assert receiver.drain(102, 50, authorized=True) == 0


def test_stale_future_duplicate_and_malformed_requests_are_dropped(transport):
  receiver, sender = transport
  now = 2 * MAX_AGE_NS
  for raw in (b'bad', b'1:2:3', f'{now - MAX_AGE_NS - 1}:50'.encode(), f'{now + 1}:50'.encode(),
              f'{now}:{50 + MAX_AGE_NS + 1}'.encode(), f'{now}:{50 - MAX_AGE_NS - 1}'.encode()):
    sender.sock.sendto(raw, sender.path)
  assert receiver.drain(now, 50, authorized=True) == 0
  with patch('time.monotonic_ns', return_value=now):
    assert sender.send(50)
    assert sender.send(50)
  assert receiver.drain(now, 50, authorized=True) == 1
  assert receiver.drain(now, 50, authorized=True) == 0


def test_small_car_state_skew_between_renderers_does_not_lose_tap(transport):
  receiver, sender = transport
  with patch('time.monotonic_ns', return_value=100):
    assert sender.send(60)
  assert receiver.drain(101, 50, authorized=True) == 1


def test_sender_is_best_effort_when_native_ui_unavailable(tmp_path):
  sender = BookmarkSender(tmp_path / 'missing.sock')
  try:
    assert not sender.send(0)
    assert not sender.send(True)
    assert not sender.send(50)
  finally:
    sender.close()
