"""Native settings update/render lifecycle keeps one current projection per frame."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import pyray as rl

from openpilot.starpilot.ui import runtime_app
from openpilot.starpilot.ui.tests.test_runtime_snapshot import RuntimeSnapshotAdapter, ui_fake
from openpilot.starpilot.ui.settings_state import SettingsState, compact_menu
from openpilot.system.ui.lib.scroll_panel2 import ScrollState
from openpilot.system.ui import widgets


@pytest.fixture
def lifecycle(monkeypatch):
  ui = ui_fake()
  paired = [True]
  ui.prime_state.is_paired = lambda: paired[0]
  adapter = RuntimeSnapshotAdapter(ui)
  adapter.build = Mock(wraps=adapter.build)
  session = runtime_app.StarShellSession.__new__(runtime_app.StarShellSession)
  session.drive_state = SimpleNamespace(snapshot=lambda: {"mode": "auto", "revision": None, "available": False,
                                                  "effective": None, "overrideAllowed": False})
  session.adapter = adapter
  session.profile = runtime_app.Profile.COMPACT
  session.selected = runtime_app.Destination.STAR
  session.compact_y = session.compact_scroll_x = 0
  session.sidebar_expanded = True
  session._snapshot_cache = None
  session.favorites = Mock()
  session.pip_warning = Mock()
  session.view = Mock()
  session.notice = ""
  monkeypatch.setattr(runtime_app, "placed_at", lambda *_: nullcontext())
  monkeypatch.setattr(widgets, "device", SimpleNamespace(awake=True))
  monkeypatch.setattr(rl, "get_time", lambda: 100.0)
  monkeypatch.setattr(rl, "get_frame_time", lambda: 1 / 60)
  for name in ("draw_rectangle_rec", "draw_rectangle_rounded", "draw_rectangle_rounded_lines_ex"):
    monkeypatch.setattr(rl, name, lambda *_: None)
  monkeypatch.setattr(runtime_app.gui_app, "_mouse_events", [])
  monkeypatch.setattr(runtime_app.gui_app, "_show_touches", False)
  page = runtime_app.StarCompactSettings(session)
  page.set_rect(rl.Rectangle(0, 0, 536, 240))
  return page, session, ui, paired


@pytest.mark.parametrize("paired_value", [False, True])
@pytest.mark.parametrize("moving", [False, True])
def test_native_frame_projects_once_after_real_panel_update(lifecycle, paired_value, moving):
  page, session, ui, paired = lifecycle
  paired[0] = paired_value
  if moving:
    page._panel._state = ScrollState.AUTO_SCROLL
    page._panel._velocity = -1500
    page._panel.set_offset(-140)
  offsets = []
  for _ in range(60):
    ui.sm.frame += 1
    page.render()
    snapshot = session.view.render.call_args.args[0]
    assert snapshot.settings.compact_scroll_x == page._panel.get_offset()
    assert snapshot.settings.paired is paired_value
    offsets.append(page._panel.get_offset())
  assert session.adapter.build.call_count == 60
  assert session.adapter.build.call_args.kwargs["menu_only"] is True
  assert (len(set(offsets)) > 1) is moving
  assert page._panel._horizontal
  session.favorites.cancel.assert_called()


def test_pairing_changes_recompute_width_without_early_snapshot(lifecycle):
  page, session, ui, paired = lifecycle
  update = Mock(wraps=page._panel.update)
  page._panel.update = update
  for index, value in enumerate((True, False, True)):
    paired[0] = value
    ui.sm.frame += 1
    page._update_state()
    assert session.adapter.build.call_count == index
    assert update.call_args.args[1] == 20 + len(compact_menu(SettingsState(paired=value))) * 422
    page._render(page.rect)
    assert session.view.render.call_args.args[0].settings.paired is value
  assert session.adapter.build.call_count == 3


def test_hidden_settings_still_updates_navigation_but_does_not_project(lifecycle):
  page, session, _, _ = lifecycle
  page.set_visible(False)
  page._panel.set_offset(-140)
  page._panel._state = ScrollState.AUTO_SCROLL
  page._panel._velocity = -1500
  page.render()
  assert page._panel.get_offset() != -140
  session.adapter.build.assert_not_called()
  session.view.render.assert_not_called()


@pytest.mark.parametrize("mode,allowed,label,target", [
  ("auto", True, "Force Off-road", "offroad"),
  ("offroad", True, "Force On-road", "onroad"),
  ("onroad", True, "Return to Auto", "auto"),
  ("offroad", False, "Return to Auto", "auto"),
])
def test_force_menu_names_requested_action_with_supported_glyphs(lifecycle, mode, allowed, label, target):
  from pathlib import Path
  import re
  page, session, ui, _ = lifecycle
  revision = "actual-owner-revision"
  session.drive_state.snapshot = lambda: {"mode": mode, "revision": revision, "available": True,
                                        "effective": None, "overrideAllowed": allowed}
  view = session.snapshot(runtime_app.ShellMode.SETTINGS)
  assert view.settings.force_drive_label == label
  action = view.settings.destination(runtime_app.Destination.FORCE_DRIVE)
  assert (action.request_value, action.request_revision) == (target, revision)
  # The shipped bitmap font is the actual Small card's glyph source.
  font = Path(runtime_app.__file__).parent / "assets/fonts/Inter-Bold.fnt"
  glyphs = {int(value) for value in re.findall(r"char id=(\d+)", font.read_text())}
  assert all(ord(char) in glyphs for char in label)
  assert ord("→") not in glyphs
