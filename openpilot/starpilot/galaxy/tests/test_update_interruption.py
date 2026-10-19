"""Reconcile interrupted updater requests without bypassing update admission."""
from datetime import datetime
from typing import cast
import unittest
from unittest import mock
from openpilot.starpilot.galaxy.tests import test_software_operations as fixture
from openpilot.starpilot.galaxy.software_operations import SoftwareOperationError

RESTART_DETAIL = "Update process restarted before completion; check the installed version and retry."

class UpdateInterruptionTest(unittest.TestCase):
  def setUp(self):
    fixture.SoftwareOperationsTest.setUp(cast(fixture.SoftwareOperationsTest, self))
    self.identity = (100, 1000)
    self.process.current_identity = lambda: self.identity if self.process.running else None
    original_send = self.process.send
    def send(*args, **kwargs):
      original_send(*args, **kwargs)
      return self.identity
    self.process.send = send
    self.owner.clock = lambda: 1.0

  def start(self):
    result = self.owner.action("update", {"action": "update", "branch": "main"}, authorized=lambda: True)
    self.assertEqual(result["request"]["state"], "pending")
    self.assertEqual(self.owner._request_owner, (100, 1000))

  def restart_error(self):
    self.params.put("UpdaterFastState", {"version": 1, "stage": "error", "detail": RESTART_DETAIL}, block=True)
    self.params.put("UpdaterState", "idle", block=True)
    self.params.put("LastUpdateTime", datetime(2026, 10, 18, 23, 35, 14, 250113), block=True)

  def test_restarted_idle_owner_finishes_pending_and_allows_parked_retry(self):
    self.start()
    self.identity = (101, 2000)
    self.restart_error()
    before = dict(self.git)
    result = self.owner.snapshot(include_history=False)
    self.assertEqual(result["request"]["state"], "failed")
    self.assertIn("interrupted", result["request"]["error"])
    self.assertTrue(result["canFastUpdate"])
    self.assertEqual(self.git, before)
    self.assertFalse(self.params.get_bool("DoReboot"))
    retry = self.owner.action("update", {"action": "update", "branch": "main"}, authorized=lambda: True)
    self.assertEqual(retry["request"]["state"], "pending")
    self.assertEqual(self.owner._request_owner, (101, 2000))

  def test_stale_restart_error_does_not_abort_new_same_owner_request(self):
    self.restart_error()
    self.start()
    self.assertEqual(self.owner.snapshot(include_history=False)["request"]["state"], "pending")

  def test_busy_replacement_and_unavailable_owner_never_offer_retry(self):
    self.start()
    self.identity = (101, 2000)
    self.params.put("UpdaterState", "checking...", block=True)
    view = self.owner.snapshot(include_history=False)
    self.assertEqual(view["request"]["state"], "pending")
    self.assertFalse(view["canFastUpdate"])
    self.restart_error()
    self.process.running = False
    view = self.owner.snapshot(include_history=False)
    self.assertEqual(view["request"]["state"], "pending")
    self.assertFalse(view["canFastUpdate"])

  def test_reboot_pending_never_becomes_retry(self):
    self.start()
    self.identity = (101, 2000)
    self.restart_error()
    self.params.put_bool("DoReboot", True, block=True)
    view = self.owner.snapshot(include_history=False)
    self.assertEqual(view["request"]["state"], "pending")
    self.assertFalse(view["canFastUpdate"])

  def test_legacy_pending_requires_exact_restart_receipt_and_fresh_parked(self):
    self.start()
    self.owner._request_owner = None
    self.restart_error()
    self.params.put_bool("IsOffroad", False, block=True)
    view = self.owner.snapshot(include_history=False)
    self.assertEqual(view["request"]["state"], "pending")
    self.assertFalse(view["canFastUpdate"])
    self.params.put_bool("IsOffroad", True, block=True)
    self.owner.refresh = mock.Mock(return_value=False)
    self.assertEqual(self.owner.snapshot(include_history=False)["request"]["state"], "pending")
    self.owner.refresh = None
    self.params.put("UpdaterFastState", {"version": 1, "stage": "error", "detail": "different error"}, block=True)
    self.assertEqual(self.owner.snapshot(include_history=False)["request"]["state"], "pending")
    self.restart_error()
    view = self.owner.snapshot(include_history=False)
    self.assertEqual(view["request"]["state"], "failed")
    self.assertTrue(view["canFastUpdate"])

  def test_changed_success_without_fetch_still_times_out(self):
    self.start()
    self.params.put("LastUpdateTime", datetime(2026, 10, 18, 23, 35, 14, 250113), block=True)
    self.owner.clock = lambda: 902.0
    view = self.owner.snapshot(include_history=False)
    self.assertEqual(view["request"]["state"], "failed")
    self.assertEqual(view["request"]["error"], "Updater did not report completion")
    self.assertTrue(view["canFastUpdate"])

  def test_actual_completion_precedes_changed_owner(self):
    self.start()
    self.identity = (101, 2000)
    self.restart_error()
    self.params.put("UpdaterLastFetchTime", datetime(2026, 10, 18, 23, 35, 13, 440423), block=True)
    view = self.owner.snapshot(include_history=False)
    self.assertEqual(view["request"]["state"], "complete")
    self.assertEqual(view["request"]["outcome"], "up_to_date")

  def test_onroad_remains_blocked_even_after_owner_interruption_detected(self):
    self.start()
    self.identity = (101, 2000)
    self.restart_error()
    self.params.put_bool("IsOffroad", False, block=True)
    view = self.owner.snapshot(include_history=False)
    self.assertFalse(view["canFastUpdate"])
    with self.assertRaises(SoftwareOperationError):
      self.owner.action("update", {"action": "update", "branch": "main"}, authorized=lambda: True)
    self.assertEqual(self.process.sent, ["update"])

if __name__ == "__main__":
  unittest.main()
