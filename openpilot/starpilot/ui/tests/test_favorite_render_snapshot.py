"""Render-only empty-slot omission never replaces the current action owner."""
import json
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import pytest

from openpilot.starpilot.favorites.actions import BOOKMARK
from openpilot.starpilot.favorites.owner import FAVORITE_SLOTS_PARAM, FavoritesOwner, default_slots
from openpilot.starpilot.favorites.state import FavoriteAction
from openpilot.starpilot.ui import runtime_app
from openpilot.starpilot.ui.appearance_preferences import CameraViewChoice
from openpilot.starpilot.ui.onroad_favorites import FavoriteRequest, OnroadFavorites
from openpilot.starpilot.ui.onroad_state import AlertSize
from openpilot.starpilot.ui.presentation import Profile


class FileParams:
  def __init__(self, root):
    self.directory = root / 'd'
    self.directory.mkdir()

  def get_param_path(self, key):
    return str(self.directory / key)


def owner_fixture(tmp_path):
  params = FileParams(tmp_path)
  invoke = Mock(return_value=True)
  action = FavoriteAction(BOOKMARK, 'Bookmark', available=True, token='fresh', invoke=invoke)
  actions = Mock(return_value={BOOKMARK: action})
  configurable = Mock(return_value=True)
  owner = FavoritesOwner(params, actions, configurable)
  return owner, actions, invoke, tmp_path / 'd' / FAVORITE_SLOTS_PARAM


@pytest.mark.parametrize('raw', [None, b'[]', b'{"slots":[]}', b'not-json'])
def test_empty_render_slots_skip_catalog_but_preserve_saved_state(tmp_path, raw):
  owner, actions, invoke, path = owner_fixture(tmp_path)
  if raw is not None:
    path.write_bytes(raw)
  full = owner.snapshot()
  assert actions.call_count == 1 and len(full.options) == 1
  rendered = owner.snapshot(include_options=False)
  assert actions.call_count == 1
  assert rendered.slots == full.slots and rendered.revision == full.revision
  assert (rendered.configurable, rendered.valid) == (full.configurable, full.valid)
  assert rendered.options == ()
  assert not path.exists() if raw is None else path.read_bytes() == raw
  invoke.assert_not_called()


def test_unreadable_empty_render_preserves_refusal_and_does_not_write(tmp_path):
  owner, actions, invoke, path = owner_fixture(tmp_path)
  path.mkdir()
  full = owner.snapshot()
  rendered = owner.snapshot(include_options=False)
  assert not rendered.valid and not rendered.configurable
  assert rendered.slots == full.slots and rendered.revision == full.revision
  assert rendered.options == () and actions.call_count == 1 and path.is_dir()
  invoke.assert_not_called()


@pytest.mark.parametrize('enabled,shown,key', [(True, True, BOOKMARK), (False, False, BOOKMARK),
                                              (False, False, 'RetiredUnsupportedControl')])
def test_any_saved_key_keeps_full_current_resolution(tmp_path, enabled, shown, key):
  owner, actions, invoke, path = owner_fixture(tmp_path)
  slots = default_slots()
  slots[1] = {'enabled': enabled, 'show_onroad': shown, 'key': key, 'label': 'Keep label'}
  path.write_text(json.dumps(slots))
  rendered = owner.snapshot(include_options=False)
  full = owner.snapshot()
  assert rendered == full and actions.call_count == 2
  invoke.assert_not_called()


def test_render_request_still_rechecks_current_authority_token_and_saved_revision(tmp_path):
  owner, actions, invoke, path = owner_fixture(tmp_path)
  slots = default_slots()
  slots[0] = {'enabled': True, 'show_onroad': True, 'key': BOOKMARK, 'label': 'Bookmark'}
  raw = json.dumps(slots).encode()
  path.write_bytes(raw)
  request = owner.snapshot(include_options=False).slots[0].request
  assert request is not None
  actions.return_value = {BOOKMARK: FavoriteAction(BOOKMARK, 'Bookmark', available=False, token='fresh', invoke=invoke)}
  assert not owner.invoke(request).success
  actions.return_value = {BOOKMARK: FavoriteAction(BOOKMARK, 'Bookmark', available=True, token='changed', invoke=invoke)}
  assert not owner.invoke(request).success
  actions.return_value = {BOOKMARK: FavoriteAction(BOOKMARK, 'Bookmark', available=True, token='fresh', invoke=invoke)}
  path.write_bytes(raw + b'\n')
  assert not owner.invoke(request).success
  invoke.assert_not_called()


def session_fixture(owner):
  session = runtime_app.StarShellSession.__new__(runtime_app.StarShellSession)
  session._favorite_read_at = None
  session._favorite_snapshot = session._favorite_data = None
  session.favorites_owner = owner
  session._favorite_authority = Mock(return_value=True)
  session.favorites = OnroadFavorites(NS(profile=Profile.LARGE), session._favorite_request)
  state = NS(viewport_width=2160, camera_available=True, alert=NS(size=AlertSize.NONE),
             appearance=NS(camera_view=CameraViewChoice.NONE))
  return session, state


def test_picker_open_forces_catalog_before_one_second_and_closed_empty_resumes_omission(tmp_path):
  owner, actions, invoke, path = owner_fixture(tmp_path)
  session, state = session_fixture(owner)
  session._update_favorites(state, 10.)
  assert actions.call_count == 0 and session.favorites.data['options'] == ()
  session.favorites.mode, session.favorites.last_interaction = 'radial', 10.1
  session._update_favorites(state, 10.2)
  assert actions.call_count == 0
  session.favorites.mode, session.favorites.last_interaction = 'picker', 10.3
  session._update_favorites(state, 10.3)
  assert actions.call_count == 1 and session.favorites.data['options'][0]['key'] == BOOKMARK
  assert session._favorite_include_options
  session._update_favorites(state, 10.4)
  assert actions.call_count == 1
  session.favorites.mode = 'collapsed'
  session._update_favorites(state, 11.4)
  assert actions.call_count == 1 and session.favorites.data['options'] == ()
  assert not session._favorite_include_options
  session.favorites.mode, session.favorites.last_interaction = 'picker', 11.5
  session._update_favorites(state, 11.5)
  assert actions.call_count == 2
  invoke.assert_not_called()
  assert not path.exists()


def test_successful_assignment_retains_full_postaction_snapshot_and_current_revision(tmp_path):
  owner, actions, invoke, path = owner_fixture(tmp_path)
  session, state = session_fixture(owner)
  session._update_favorites(state, 10.)
  revision = session._favorite_snapshot.revision
  request = FavoriteRequest('assign', 0, BOOKMARK, revision)
  with patch.object(runtime_app.time, 'monotonic', return_value=10.2):
    assert session._favorite_request(request)
  assert session._favorite_include_options and session._favorite_snapshot.options
  assert session.favorites.data['options'][0]['key'] == BOOKMARK
  assert session._favorite_snapshot.revision != revision and path.is_file()
  assert not session._favorite_request(request)
  invoke.assert_not_called()
