"""Local crash reader and authenticated HTTP adapter with disposable files."""

import base64
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.crash_reports import CrashChanged, CrashMissing, CrashReports, CrashUnavailable, MAX_PREVIEW, MAX_SCAN
from openpilot.starpilot.galaxy.server import make_server


class CrashReaderTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name) / "crash"
    self.root.mkdir()
    self.reader = CrashReports(self.root)

  def test_listing_selection_truncation_and_changed_identity(self):
    report = self.root / "2026-09-23_crash"
    report.write_text("first report")
    result = self.reader.list()
    self.assertFalse(result["scanIncomplete"])
    self.assertFalse(result["listLimited"])
    token = result["reports"][0]["id"]
    self.assertEqual(self.reader.preview(token)["text"], "first report")
    report.write_bytes(b"x" * (MAX_PREVIEW + 10))
    with self.assertRaises(CrashChanged):
      self.reader.preview(token)
    large = self.reader.preview(self.reader.list()["reports"][0]["id"])
    self.assertTrue(large["truncated"])
    self.assertEqual(len(large["text"]), MAX_PREVIEW)
    report.unlink()
    with self.assertRaises(CrashMissing):
      self.reader.preview(token)

  def test_symlink_traversal_and_root_swap(self):
    outside = self.root.parent / "secret"
    outside.write_text("private")
    (self.root / "linked").symlink_to(outside)
    self.assertEqual(self.reader.list()["reports"], [])
    report = self.root / "ordinary"
    report.write_text("safe")
    token = self.reader.list()["reports"][0]["id"]
    report.unlink()
    report.symlink_to(outside)
    with self.assertRaises(CrashChanged):
      self.reader.preview(token)
    self.assertNotIn("private", str(self.reader.list()))
    with self.assertRaises(CrashMissing):
      self.reader.preview("Li4vLi4vc2VjcmV0")
    self.root.rename(self.root.parent / "old_crash")
    self.root.mkdir()
    with self.assertRaises(CrashChanged):
      self.reader.preview(token)

  def test_invalid_and_deep_tokens_fail_closed(self):
    for token in ("A", "..", base64.urlsafe_b64encode(b"[" * 1500).decode().rstrip("=")):
      with self.subTest(token_length=len(token)), self.assertRaises(CrashMissing):
        self.reader.preview(token)

  def test_incomplete_listing_never_claims_global_newest(self):
    for index in range(MAX_SCAN + 1):
      (self.root / f"report-{index:04}").write_text("x")
    listed = self.reader.list()
    self.assertTrue(listed["scanIncomplete"])
    self.assertTrue(listed["listLimited"])
    self.assertEqual(len(listed["reports"]), 200)

  def test_report_mutated_during_read_is_rejected(self):
    for replacement in ("", "changed after read"):
      with self.subTest(replacement=replacement):
        report = self.root / "changing"
        report.write_text("original")
        token = self.reader.list()["reports"][0]["id"]
        original_read = os.read
        def changed(fd, count, original_read=original_read, report=report, replacement=replacement):
          content = original_read(fd, count)
          report.write_text(replacement)
          return content
        with mock.patch("openpilot.starpilot.galaxy.crash_reports.os.read", side_effect=changed):
          with self.assertRaises(CrashChanged):
            self.reader.preview(token)

  def test_selected_name_replaced_during_read_is_rejected(self):
    report = self.root / "selected"
    report.write_text("original file")
    token = self.reader.list()["reports"][0]["id"]
    original_read = os.read
    def replaced(fd, count):
      content = original_read(fd, count)
      report.rename(self.root / "moved")
      report.write_text("replacement file")
      return content
    with mock.patch("openpilot.starpilot.galaxy.crash_reports.os.read", side_effect=replaced):
      with self.assertRaises(CrashChanged):
        self.reader.preview(token)

  def test_absent_and_unreadable_directory(self):
    self.root.rmdir()
    self.assertEqual(self.reader.list()["reports"], [])
    self.root.write_text("not a directory")
    with self.assertRaises(CrashUnavailable):
      self.reader.list()


class CrashHTTPTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    root = Path(temporary.name)
    self.reports = root / "crash"
    self.reports.mkdir()
    (self.reports / "test_report").write_text("synthetic crash text")
    self.owner = GalaxyAccessOwner(root / "access")
    self.reader = CrashReports(self.reports)
    self.server = make_server(port=0, owner=self.owner, crashes=self.reader)
    self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    self.thread.start()
    self.addCleanup(self.close_server)

  def close_server(self):
    self.server.shutdown()
    self.thread.join(timeout=2)
    self.server.server_close()

  def request(self, path, *, method="GET", body=None, headers=None):
    # Exercise the password-backed forwarded path.
    connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
    try:
      connection.request(method, path, body=body, headers={'Forwarded': 'for=203.0.113.8', **(headers or {})})
      response = connection.getresponse()
      return response.status, response.read(), dict(response.getheaders())
    finally:
      connection.close()

  def login(self):
    payload = json.dumps({"password": "password123"})
    status, _, headers = self.request("/api/auth/login", method="POST", body=payload,
                                    headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.server.server_port}"})
    self.assertEqual(status, 200)
    return headers["Set-Cookie"].split(";", 1)[0]

  def test_auth_before_list_open_and_read_only_routes(self):
    with mock.patch.object(self.reader, "list", wraps=self.reader.list) as scan, \
         mock.patch.object(self.reader, "preview", wraps=self.reader.preview) as open_report:
      self.assertEqual(self.request("/api/crash-reports")[0], 503)
      self.assertEqual(self.request("/api/crash-reports/A")[0], 503)
      self.assertTrue(self.owner.configure("password123", lambda: True))
      self.assertEqual(self.request("/api/crash-reports")[0], 401)
      self.assertEqual(self.request("/api/crash-reports/A")[0], 401)
      scan.assert_not_called()
      open_report.assert_not_called()
    cookie = self.login()
    status, body, headers = self.request("/api/crash-reports", headers={"Cookie": cookie})
    self.assertEqual(status, 200)
    self.assertEqual(headers["Cache-Control"], "no-store")
    selected = json.loads(body)["reports"][0]
    self.assertEqual(self.request("/api/crash-reports/" + selected["id"], headers={"Cookie": cookie})[0], 200)
    self.assertEqual(json.loads(self.request("/api/crash-reports/" + selected["id"], headers={"Cookie": cookie})[1])["text"], "synthetic crash text")
    self.assertEqual(self.request("/api/crash-reports/A", headers={"Cookie": cookie})[0], 404)
    origin = f"http://127.0.0.1:{self.server.server_port}"
    self.assertEqual(self.request("/api/crash-reports", method="DELETE", headers={"Cookie": cookie, "Origin": origin})[0], 405)
    self.assertEqual(self.request("/api/crash-reports", headers={"Cookie": cookie, "Host": "evil.example"})[0], 403)
    self.assertTrue(self.owner.remove(lambda: True))
    self.assertEqual(self.request("/api/crash-reports", headers={"Cookie": cookie})[0], 503)

  def test_changed_report_cannot_serve_earlier_identity(self):
    self.owner.configure("password123", lambda: True)
    cookie = self.login()
    selected = json.loads(self.request("/api/crash-reports", headers={"Cookie": cookie})[1])["reports"][0]
    (self.reports / "test_report").write_text("replacement")
    self.assertEqual(self.request("/api/crash-reports/" + selected["id"], headers={"Cookie": cookie})[0], 409)

  def test_logout_during_scan_and_credential_removal_during_open_return_no_data(self):
    self.owner.configure("password123", lambda: True)
    cookie = self.login()
    selected = json.loads(self.request("/api/crash-reports", headers={"Cookie": cookie})[1])["reports"][0]

    for operation in ("list", "preview"):
      with self.subTest(operation=operation):
        entered, release = threading.Event(), threading.Event()
        original = getattr(self.reader, operation)
        def paused(*args, entered=entered, release=release, original=original):
          entered.set()
          if not release.wait(2):
            raise TimeoutError("fixture release missing")
          return original(*args)
        path = "/api/crash-reports" if operation == "list" else "/api/crash-reports/" + selected["id"]
        with mock.patch.object(self.reader, operation, side_effect=paused), ThreadPoolExecutor(max_workers=1) as pool:
          pending = pool.submit(self.request, path, headers={"Cookie": cookie})
          self.assertTrue(entered.wait(1))
          if operation == "list":
            origin = f"http://127.0.0.1:{self.server.server_port}"
            self.assertEqual(self.request("/api/auth/logout", method="POST", body="{}",
                                          headers={"Cookie": cookie, "Origin": origin, "Content-Type": "application/json"})[0], 200)
          else:
            self.assertTrue(self.owner.remove(lambda: True))
          release.set()
          status, body, _ = pending.result(timeout=2)
        self.assertEqual(status, 401 if operation == "list" else 503)
        self.assertNotIn(b"synthetic crash text", body)
        self.assertNotIn(b"test_report", body)
        if operation == "list":
          cookie = self.login()
