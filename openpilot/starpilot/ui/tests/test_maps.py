"""Offline map status is read-only and never blocks a render frame on the socket."""

import threading
import unittest
from types import SimpleNamespace
from typing import cast
from unittest import mock

from openpilot.starpilot.ui.feature_settings_state import FeatureInput
from openpilot.starpilot.ui.maps_compact import MapsCompact, _MapsPage
from openpilot.starpilot.ui.maps_state import MapStatusSource, map_page


STATUS = {"schemaVersion": 1, "ownerSession": "session", "operationId": "session:1",
          "state": "transferring", "regionToken": "us_state.IL", "bounds": [36, -92, 44, -86],
          "completedGroups": 3, "totalGroups": 12, "transferredBytes": 100,
          "transferBudgetBytes": 8589934592, "preparedGeneration": None,
          "selectedGeneration": "a" * 64, "errorCode": None,
          "selectedForNextShadowStart": False}


class TestMaps(unittest.TestCase):
  def test_read_only_states_and_selection_claim(self):
    page = map_page(STATUS)
    self.assertEqual(page.rows[0].value, "Transferring")
    self.assertEqual(page.rows[1].value, "a" * 12 + "…")
    self.assertIn("does not prove", page.rows[1].reason)
    self.assertEqual(page.rows[2].value, "3 / 12 groups")
    self.assertTrue(all(not row.available and not row.page for row in page.rows))
    self.assertIsNone(FeatureInput.target(1980, 150, page))
    self.assertEqual(map_page({**STATUS, "state": "unknown"}).rows[0].value, "Unavailable")
    self.assertEqual(map_page({**STATUS, "selectedGeneration": "x"}).rows[0].value, "Unavailable")
    self.assertEqual(map_page({**STATUS, "state": "idle", "selectedGeneration": ""}).rows[1].value, "None")

  def test_background_socket_read_is_bounded_and_failure_clears_status(self):
    wait = threading.Event()
    calls = []
    now = [0]
    def request():
      calls.append(1)
      wait.wait(1)
      if len(calls) == 1:
        return STATUS
      raise OSError("socket down")
    source = MapStatusSource(request=request, clock=lambda: now[0])
    try:
      self.assertEqual(source.snapshot().rows[0].value, "Unavailable")
      wait.set()
      source.pending.result(timeout=1)
      self.assertEqual(source.snapshot().rows[0].value, "Transferring")
      self.assertEqual(len(calls), 1)
      now[0] = source.REFRESH_NS
      source.snapshot()
      with self.assertRaises(OSError):
        source.pending.result(timeout=1)
      self.assertEqual(source.snapshot().rows[0].value, "Unavailable")
    finally:
      source.close()

  def test_compact_hidden_does_not_poll_and_rows_have_no_actions(self):
    session = mock.Mock()
    session.map_snapshot.side_effect = [map_page(STATUS)]
    now = [0.0]
    compact = MapsCompact(session, clock=lambda: now[0])
    page = cast(_MapsPage, SimpleNamespace(current=map_page(None), next_refresh=.5, _scroller=mock.Mock(items=[])))
    with mock.patch("openpilot.starpilot.ui.maps_compact.GreyBigButton", side_effect=lambda *args: args), \
         mock.patch("openpilot.starpilot.ui.maps_compact.gui_app.get_active_widget", return_value=object()) as visible:
      now[0] = 1
      compact.refresh_visible(page)
      session.map_snapshot.assert_not_called()
      visible.return_value = page
      compact.refresh_visible(page)
      self.assertEqual(page.current.rows[0].value, "Transferring")
      self.assertIn("open galaxy", page._scroller.add_widgets.call_args.args[0][-1][1])

  def test_large_system_includes_owner_status_without_map_actions(self):
    from openpilot.starpilot.ui.runtime_app import StarShellSession
    from openpilot.starpilot.ui.presentation import Profile
    session = StarShellSession.__new__(StarShellSession)
    session.profile = Profile.LARGE
    session.display_owner = mock.Mock(snapshot=mock.Mock(return_value=map_page(None)))
    session.power_owner = mock.Mock(snapshot=mock.Mock(return_value=map_page(None)))
    session.map_source = mock.Mock(snapshot=mock.Mock(return_value=map_page(STATUS)))
    result = session.system_snapshot()
    self.assertIn("offline map", result.subtitle)
    self.assertIn("Transferring", [row.value for row in result.rows])
    self.assertTrue(all(not row.available for row in result.rows))
    session.map_source.snapshot.assert_called_once()


if __name__ == "__main__":
  unittest.main()
