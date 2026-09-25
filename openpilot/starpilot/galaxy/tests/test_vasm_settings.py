"""Actual Params, one-use Galaxy intent, and local HTTP V-ASM editor tests."""

from pathlib import Path
import fcntl
import http.client
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

from openpilot.common.params import Params
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.galaxy.settings import AuthorityContext, SettingsChanged, SettingsGateway
from openpilot.starpilot.spot_monitor.actions import commit
from openpilot.starpilot.spot_monitor.preferences import KEY, Preferences, decode, encode, read_preferences
from openpilot.starpilot.ui.vasm_owner import VASMOwner


DRAFT = {"version": 1, "width": 1344, "height": 760,
         "poly_left": [], "poly_right": [[100, 200], [320, 200], [320, 400], [100, 400]]}


class Context:
  def __init__(self):
    self.value = AuthorityContext(True, None, None)

  def sample(self):
    return self.value


class VasmSavedSettingsTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.context = Context()
    self.gateway = SettingsGateway(self.params, self.context)

  def preview(self, page, index, draft=None):
    return self.gateway.preview(page["view"], index, 0, "session", b"generation", draft=draft)

  def confirm(self, intent):
    return self.gateway.confirm(intent["intent"], "session", b"generation")

  def test_one_side_annotation_then_enable_and_exact_source_cas(self):
    path = Path(self.params.get_param_path(KEY))
    page = self.gateway.page("vasm", "session", b"generation")
    self.assertFalse(path.exists())
    self.assertFalse(page["rows"][0]["available"])
    self.assertTrue(all("source" not in row and "related_source" not in row for row in page["rows"]))
    self.assertEqual(page["editorRow"], 3)
    self.assertEqual(page["editor"]["cameraLeft"], [])
    intent = self.preview(page, page["editorRow"], DRAFT)
    self.assertIn("camera right / vehicle left (4 points)", intent["question"])
    self.assertFalse(path.exists())
    self.assertTrue(self.confirm(intent))
    with self.assertRaises(SettingsChanged):
      self.confirm(intent)
    saved = read_preferences(self.params)
    self.assertTrue(saved.valid)
    self.assertFalse(saved.preferences.enabled)
    self.assertEqual(saved.preferences.annotation.configured_sides, ("right",))
    page = self.gateway.page("vasm", "session", b"generation")
    self.assertEqual(page["editor"]["cameraRight"], DRAFT["poly_right"])
    enable = self.gateway.preview(page["view"], 0, 1, "session", b"generation")
    path.write_bytes(encode(Preferences(False, saved.preferences.annotation, 0.95, 0.2)))
    self.assertFalse(self.confirm(enable))
    self.assertFalse(read_preferences(self.params).preferences.enabled)
    page = self.gateway.page("vasm", "session", b"generation")
    enable = self.gateway.preview(page["view"], 0, 1, "session", b"generation")
    self.assertIn("as On?", enable["question"])
    self.assertTrue(self.confirm(enable))
    self.assertTrue(read_preferences(self.params).preferences.enabled)

  def test_corrupt_reset_source_change_lock_and_postrename_uncertainty(self):
    path = Path(self.params.get_param_path(KEY))
    path.write_bytes(b'{"version":9}')
    page = self.gateway.page("vasm", "session", b"generation")
    self.assertEqual(len(page["rows"]), 2)
    reset = self.preview(page, 1)
    path.write_bytes(b'{"version":8}')
    self.assertFalse(self.confirm(reset))
    self.assertEqual(path.read_bytes(), b'{"version":8}')
    page = self.gateway.page("vasm", "session", b"generation")
    reset = self.preview(page, 1)
    self.context.value = AuthorityContext(False, None, None)
    with self.assertRaises(SettingsChanged):
      self.confirm(reset)
    self.assertEqual(path.read_bytes(), b'{"version":8}')
    self.context.value = AuthorityContext(True, None, None)
    page = self.gateway.page("vasm", "session", b"generation")
    reset = self.preview(page, 1)
    lock = os.open(path.parent.parent / ".lock", os.O_CREAT | os.O_RDONLY, 0o775)
    try:
      fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
      self.assertFalse(self.confirm(reset))
      self.assertEqual(path.read_bytes(), b'{"version":8}')
    finally:
      os.close(lock)
    page = self.gateway.page("vasm", "session", b"generation")
    reset = self.preview(page, 1)
    real_fsync = os.fsync
    calls = 0
    def uncertain(fd):
      nonlocal calls
      calls += 1
      if calls == 2:
        raise OSError("directory sync unavailable")
      return real_fsync(fd)
    with mock.patch("openpilot.starpilot.saved_document.os.fsync", side_effect=uncertain):
      self.assertFalse(self.confirm(reset))
    self.assertEqual(decode(path.read_bytes()), Preferences())
    path.write_bytes(b'{"version":7}')
    calls = 0
    with mock.patch("openpilot.starpilot.saved_document.os.fsync", side_effect=uncertain):
      outcome = commit(self.params, encode(Preferences()), b'{"version":7}', lambda: True)
    self.assertTrue(outcome.committed)
    self.assertFalse(outcome.verified)

  def test_invalid_geometry_and_unreadable_source_never_write(self):
    path = Path(self.params.get_param_path(KEY))
    page = self.gateway.page("vasm", "session", b"generation")
    crossed = {**DRAFT, "poly_right": [[100, 100], [300, 300], [100, 300], [300, 100]]}
    with self.assertRaises(SettingsChanged):
      self.preview(page, page["editorRow"], crossed)
    self.assertFalse(path.exists())
    path.write_bytes(b"x" * 8193)
    page = self.gateway.page("vasm", "session", b"generation")
    self.assertEqual(page["rows"][0]["value"], "Unavailable")
    self.assertEqual(path.read_bytes(), b"x" * 8193)

  def test_page_rejects_editor_rows_from_different_saved_revision(self):
    path = Path(self.params.get_param_path(KEY))
    path.write_bytes(encode(Preferences()))
    original = VASMOwner.editor_with_source
    def changed(owner):
      path.write_bytes(b'{"version":9}')
      return original(owner)
    with mock.patch.object(VASMOwner, "editor_with_source", changed):
      with self.assertRaises(SettingsChanged):
        self.gateway.page("vasm", "session", b"generation")
    self.assertEqual(len(self.gateway.views), 0)


class VasmHttpTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.context = Context()
    self.gateway = SettingsGateway(self.params, self.context)
    self.access = GalaxyAccessOwner(Path(temporary.name) / "access")
    self.assertTrue(self.access.configure("password123", lambda: True))
    self.server = make_server(port=0, owner=self.access, settings=self.gateway)
    self.worker = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    self.worker.start()
    self.addCleanup(self.stop)

  def stop(self):
    self.server.shutdown()
    self.worker.join(timeout=2)
    self.server.server_close()

  def request(self, path, *, payload=None, cookie=""):
    connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
    headers = {"Cookie": cookie}
    if payload is not None:
      headers.update({"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.server.server_port}"})
    try:
      connection.request("POST" if payload is not None else "GET", path,
                         body=json.dumps(payload) if payload is not None else None, headers=headers)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()

  def test_authenticated_draft_preview_confirm_logout_and_parked_loss(self):
    with mock.patch.object(self.gateway, "page", wraps=self.gateway.page) as read:
      self.assertEqual(self.request("/api/settings/pages/vasm")[0], 401)
      read.assert_not_called()
    status, _, headers = self.request("/api/auth/login", payload={"password": "password123"})
    self.assertEqual(status, 200)
    # Calibration stills use browser-only object URLs; never a server upload.
    self.assertIn("img-src 'self' data: blob:", headers["Content-Security-Policy"])
    cookie = headers["Set-Cookie"].split(";", 1)[0]
    status, page, _ = self.request("/api/settings/pages/vasm", cookie=cookie)
    self.assertEqual(status, 200)
    payload = {"view": page["view"], "row": page["editorRow"], "direction": 0, "draft": DRAFT}
    status, preview, _ = self.request("/api/settings/preview", cookie=cookie, payload=payload)
    self.assertEqual(status, 200)
    self.assertFalse(Path(self.params.get_param_path(KEY)).exists())
    self.context.value = AuthorityContext(False, None, None)
    self.assertEqual(self.request("/api/settings/confirm", cookie=cookie,
                                  payload={"intent": preview["intent"], "confirmed": True})[0], 409)
    self.assertFalse(Path(self.params.get_param_path(KEY)).exists())
    self.context.value = AuthorityContext(True, None, None)
    page = self.request("/api/settings/pages/vasm", cookie=cookie)[1]
    preview = self.request("/api/settings/preview", cookie=cookie,
                           payload={**payload, "view": page["view"]})[1]
    self.assertEqual(self.request("/api/settings/confirm", cookie=cookie,
                                  payload={"intent": preview["intent"], "confirmed": True})[0], 200)
    self.assertEqual(read_preferences(self.params).preferences.annotation.configured_sides, ("right",))
    page = self.request("/api/settings/pages/vasm", cookie=cookie)[1]
    preview = self.request("/api/settings/preview", cookie=cookie,
                           payload={"view": page["view"], "row": 0, "direction": 1})[1]
    self.assertEqual(self.request("/api/auth/logout", cookie=cookie, payload={})[0], 200)
    self.assertEqual(self.request("/api/settings/confirm", cookie=cookie,
                                  payload={"intent": preview["intent"], "confirmed": True})[0], 401)
    self.assertFalse(read_preferences(self.params).preferences.enabled)

  def test_mid_page_source_change_returns_refreshable_conflict(self):
    status, _, headers = self.request("/api/auth/login", payload={"password": "password123"})
    self.assertEqual(status, 200)
    cookie = headers["Set-Cookie"].split(";", 1)[0]
    path = Path(self.params.get_param_path(KEY))
    path.write_bytes(encode(Preferences()))
    original = VASMOwner.editor_with_source
    def changed(owner):
      path.write_bytes(b'{"version":9}')
      return original(owner)
    with mock.patch.object(VASMOwner, "editor_with_source", changed):
      self.assertEqual(self.request("/api/settings/pages/vasm", cookie=cookie)[0], 409)
