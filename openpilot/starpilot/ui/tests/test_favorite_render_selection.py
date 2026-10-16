import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from openpilot.starpilot.favorites.actions import APPEARANCE_KEYS, BOOKMARK, FEATURE_KEYS, mapped_actions
from openpilot.starpilot.favorites.owner import FAVORITE_SLOTS_PARAM, FavoritesOwner, default_slots
from openpilot.starpilot.favorites.state import FavoriteAction
from openpilot.starpilot.ui.feature_settings_state import FeatureRow


@pytest.fixture
def selected_owner(tmp_path):
  path = tmp_path / FAVORITE_SLOTS_PARAM
  params = SimpleNamespace(get_param_path=lambda key: str(path))
  invoke = Mock(return_value=True)
  action = FavoriteAction(BOOKMARK, "Bookmark", available=True, token="fresh", invoke=invoke)
  catalog = Mock(return_value={BOOKMARK: action})
  selected = Mock(side_effect=lambda keys: {key: action for key, action in catalog.return_value.items() if key in keys})
  owner = FavoritesOwner(params, catalog, lambda: True, selected)
  return owner, catalog, selected, path, invoke


@pytest.mark.parametrize("keys", [(BOOKMARK,), (BOOKMARK, BOOKMARK), ("UnknownSavedControl",),
                                  (BOOKMARK, "UnknownSavedControl")])
@pytest.mark.parametrize("enabled", [False, True])
def test_selected_render_preserves_saved_slots_and_current_metadata(selected_owner, keys, enabled):
  owner, catalog, selected, path, invoke = selected_owner
  slots = default_slots()
  for index, key in enumerate(keys):
    slots[index].update(key=key, enabled=enabled, show_onroad=enabled, label="Saved label")
  raw = json.dumps(slots).encode()
  path.write_bytes(raw)
  full = owner.snapshot()
  rendered = owner.snapshot(include_options=False)
  assert rendered.slots == full.slots
  assert rendered.revision == full.revision
  assert (rendered.valid, rendered.configurable) == (full.valid, full.configurable)
  assert {action.key for action in rendered.options} == {action.key for action in full.options}.intersection(keys)
  selected.assert_called_once_with(frozenset(keys))
  assert catalog.call_count == 1
  assert path.read_bytes() == raw
  invoke.assert_not_called()


@pytest.mark.parametrize("raw", [None, b"[]", b"bad-json", b'{"slots":[]}'])
def test_empty_or_invalid_render_does_not_resolve_actions(selected_owner, raw):
  owner, catalog, selected, path, invoke = selected_owner
  if raw is not None:
    path.write_bytes(raw)
  rendered = owner.snapshot(include_options=False)
  assert rendered.options == ()
  catalog.assert_not_called()
  selected.assert_not_called()
  invoke.assert_not_called()
  assert not path.exists() if raw is None else path.read_bytes() == raw


def test_unreadable_render_keeps_refusal(selected_owner):
  owner, catalog, selected, path, invoke = selected_owner
  path.mkdir()
  rendered = owner.snapshot(include_options=False)
  assert not rendered.valid and not rendered.configurable
  catalog.assert_not_called()
  selected.assert_not_called()
  invoke.assert_not_called()
  assert path.is_dir()


def test_default_and_picker_snapshots_keep_full_catalog(selected_owner):
  owner, catalog, selected, _, _ = selected_owner
  assert owner.snapshot() == owner.snapshot(include_options=True)
  assert catalog.call_count == 2
  selected.assert_not_called()


def test_owner_without_selected_resolver_retains_full_render_options(selected_owner):
  owner, catalog, _, path, _ = selected_owner
  owner.render_actions = None
  slots = default_slots()
  slots[0].update(key=BOOKMARK)
  path.write_text(json.dumps(slots))
  assert owner.snapshot(include_options=False) == owner.snapshot()
  assert catalog.call_count == 2


def test_selected_render_request_rechecks_full_live_authority_token_and_revision(selected_owner):
  owner, catalog, selected, path, invoke = selected_owner
  slots = default_slots()
  slots[0].update(key=BOOKMARK, enabled=True, show_onroad=True)
  path.write_text(json.dumps(slots))
  request = owner.snapshot(include_options=False).slots[0].request
  assert request is not None
  catalog.return_value = {BOOKMARK: FavoriteAction(BOOKMARK, "Bookmark", available=False, token="fresh", invoke=invoke)}
  assert not owner.invoke(request).success
  catalog.return_value = {BOOKMARK: FavoriteAction(BOOKMARK, "Bookmark", available=True, token="changed", invoke=invoke)}
  assert not owner.invoke(request).success
  catalog.return_value = {BOOKMARK: FavoriteAction(BOOKMARK, "Bookmark", available=True, token="fresh", invoke=invoke)}
  path.write_bytes(path.read_bytes() + b"\n")
  assert not owner.invoke(request).success
  assert selected.call_count == 1
  assert catalog.call_count == 2
  invoke.assert_not_called()


def test_selected_resolver_errors_are_not_hidden(selected_owner):
  owner, catalog, selected, path, _ = selected_owner
  slots = default_slots()
  slots[0].update(key=BOOKMARK)
  path.write_text(json.dumps(slots))
  selected.side_effect = OSError("saved source unavailable")
  with pytest.raises(OSError, match="saved source unavailable"):
    owner.snapshot(include_options=False)
  catalog.assert_not_called()


@pytest.mark.parametrize("keys", [frozenset([BOOKMARK]), frozenset(["LaneCentering"]),
                                  frozenset(["CameraView"]), frozenset(["UnknownSavedControl"]),
                                  frozenset(["LaneCentering", "CameraView"])])
def test_mapped_selection_preserves_current_actions_and_skips_unrelated_pages(keys):
  def row(key):
    return FeatureRow(key, key, "Off", choices=("Off", "On"), available=True)
  pages = {page: SimpleNamespace(title=page, rows=tuple(row(key) for key in names))
           for page, names in FEATURE_KEYS.items()}
  feature = Mock(side_effect=lambda page: pages[page])
  appearance = Mock(return_value=SimpleNamespace(rows=tuple(row(key) for key in APPEARANCE_KEYS)))
  apply = Mock()
  full = mapped_actions(feature, apply, appearance, apply)
  feature.reset_mock()
  appearance.reset_mock()
  rendered = mapped_actions(feature, apply, appearance, apply, requested_keys=keys)
  assert set(rendered) == set(full).intersection(keys)
  for key, action in rendered.items():
    expected = full[key]
    assert (action.label, action.available, action.token, action.reason, action.state_label) == (
      expected.label, expected.available, expected.token, expected.reason, expected.state_label)
    assert (action.invoke is None) == (expected.invoke is None)
  assert feature.call_count == sum(bool(keys.intersection(names)) for names in FEATURE_KEYS.values())
  assert appearance.call_count == int(bool(keys.intersection(APPEARANCE_KEYS)))
  apply.assert_not_called()
