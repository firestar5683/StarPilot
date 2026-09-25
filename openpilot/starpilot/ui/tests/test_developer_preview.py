"""Private visual fixtures never stand in for control receipts."""

from dataclasses import FrozenInstanceError
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from openpilot.starpilot.ui.developer_preview import encode_flags, parse_flags, preview_at
from openpilot.starpilot.ui.onroad_state import OnroadState, SpeedLimitObservation


class DeveloperPreviewTests(unittest.TestCase):
  def test_frozen_cem_and_curve_cycles_have_exact_boundaries(self):
    flags = parse_flags("cem,csc")
    self.assertEqual(encode_flags(flags), "cem,csc")
    for elapsed, reason, curvature in ((0.0, "CURVE", 0.0), (1.999, "CURVE", 0.0),
                                       (2.0, "LEAD", .008), (4.0, "STOP LIGHT", .0115),
                                       (6.0, "SPEED", .0200), (8.0, "CURVE", 0.0)):
      with self.subTest(elapsed=elapsed):
        value = preview_at(flags, elapsed)
        self.assertEqual((value.cem_reason, value.curve_curvature), (reason, curvature))
        self.assertEqual(value.label, "SYNTHETIC REPLAY PREVIEW")
    self.assertIsNone(preview_at(frozenset(), 1.0))

  def test_source_state_remains_immutable_and_authority_absent(self):
    normal = OnroadState(False, False, None, None, SpeedLimitObservation())
    self.assertIsNone(normal.visual_preview)
    self.assertIsNone(normal.conditional_effective)
    self.assertIsNone(normal.curve)
    self.assertFalse(normal.longitudinal_active)
    value = preview_at(frozenset(("cem", "csc")), 3.0)
    with self.assertRaises(FrozenInstanceError):
      value.__setattr__("cem_reason", "ACTUAL")
    self.assertEqual(set(vars(value)), {"cem_reason", "curve_curvature", "label"})

  def test_invalid_or_duplicate_flags_and_time_rejected(self):
    for raw in ("cem,cem", "csc,bogus", "CEM", ",cem"):
      with self.subTest(raw=raw), self.assertRaises(ValueError):
        parse_flags(raw)
    for elapsed in (-1.0, float("nan"), float("inf")):
      with self.subTest(elapsed=elapsed), self.assertRaises(ValueError):
        preview_at(frozenset(("cem",)), elapsed)

  def test_runtime_snapshot_changes_only_private_visual_field(self):
    from openpilot.starpilot.ui import runtime_app
    from openpilot.starpilot.ui.settings_state import Destination, SettingsState
    from openpilot.starpilot.ui.shell import ShellMode, ShellSnapshot
    from openpilot.starpilot.ui.presentation import Profile
    from openpilot.starpilot.ui.home_state import HomeMode, HomeState

    onroad = OnroadState(False, False, None, None, SpeedLimitObservation())
    home = HomeState("7.0", "test", "today", "model", "description", HomeMode.CHILL, False, False, None)
    baseline = ShellSnapshot(ShellMode.ONROAD, home, SettingsState(), onroad)
    session = runtime_app.StarShellSession.__new__(runtime_app.StarShellSession)
    adapter = SimpleNamespace(ui_state=SimpleNamespace(sm=SimpleNamespace(frame=7)), build=Mock(return_value=baseline))
    self.enterContext(patch.object(session, "adapter", adapter, create=True))
    session.selected = Destination.STAR
    session.compact_y = 0.0
    session.compact_scroll_x = 0.0
    session.sidebar_expanded = True
    session.profile = Profile.LARGE
    session._snapshot_cache = None
    session._visual_preview_flags = frozenset()
    session._visual_preview_start_ns = 1_000_000_000
    with patch.object(runtime_app.time, "monotonic_ns", return_value=4_000_000_000):
      self.assertIs(session.snapshot(ShellMode.ONROAD), baseline)
      session._visual_preview_flags = frozenset(("cem", "csc"))
      session._snapshot_cache = None
      observed = session.snapshot(ShellMode.ONROAD)
      self.assertEqual(observed.onroad.visual_preview.cem_reason, "LEAD")
      self.assertEqual(observed.onroad.visual_preview.curve_curvature, .008)
      self.assertEqual(replace(observed, onroad=baseline.onroad), baseline)
      self.assertIsNone(baseline.onroad.visual_preview)


if __name__ == "__main__":
  unittest.main()
