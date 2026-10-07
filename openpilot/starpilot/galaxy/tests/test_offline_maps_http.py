import json
from pathlib import Path
import tempfile
import threading
import unittest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.remote import RemotePairing
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.galaxy.tests import test_navigation_http as navigation_http
from openpilot.starpilot.navigation.offline_owner import OfflineMapsOwner
from openpilot.starpilot.navigation.offline_roads import OfflineState
from openpilot.starpilot.navigation.owner import NavigationOwner

AREA = {"latitude": 36.1147, "longitude": -115.1728, "radiusKm": 25, "name": "Las Vegas"}


class OfflineMapsHttpTest(unittest.TestCase):
  request = navigation_http.NavigationHttpTest.request

  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    base = Path(temporary.name)
    self.access = GalaxyAccessOwner(base / "access")
    self.pairing = RemotePairing(base / "pairing")
    self.navigation = NavigationOwner(base / "navigation", runtime_source=lambda: None, transient_root=base / "boot-navigation")
    self.root = base / "roads"
    self.wall = [1_790_000_000.0]
    self.offline = OfflineMapsOwner(self.root, position=lambda: {"latitude": 36.1, "longitude": -115.2}, wall=lambda: self.wall[0])
    self.local = make_server(port=0, owner=self.access, remote_pairing=self.pairing, navigation=self.navigation,
                             offline_maps=self.offline, parked=lambda: True)
    self.remote = None
    self.slug = "unused"
    thread = threading.Thread(target=self.local.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
    thread.start()

    def close():
      self.local.shutdown()
      thread.join(timeout=2)
      self.local.server_close()
    self.addCleanup(close)
    self.local_cookie = self.request()[2]["Set-Cookie"].split(";", 1)[0]
    self.access.configure("password123", lambda: True)
    status, _, _ = self.request("/api/auth/login", payload={"password": "password123"}, cookie=self.local_cookie)
    assert status == 200, status

  def test_requires_a_session(self):
    status, body, _ = self.request("/api/navigation/offline")
    self.assertEqual(status, 401)
    status, _, _ = self.request("/api/navigation/offline", payload={"action": "addArea", "area": AREA})
    self.assertEqual(status, 401)
    self.assertEqual(OfflineState(self.root).areas(), [])

  def test_add_list_and_delete_areas(self):
    status, body, _ = self.request("/api/navigation/offline", cookie=self.local_cookie)
    self.assertEqual(status, 200)
    self.assertEqual(body["areas"], [])
    self.assertEqual(body["position"], {"latitude": 36.1, "longitude": -115.2})
    self.assertFalse(body["service"]["running"])
    self.assertEqual(body["constants"]["maxRadiusKm"], 200.0)
    status, body, _ = self.request("/api/navigation/offline", payload={"action": "addArea", "area": AREA}, cookie=self.local_cookie)
    self.assertEqual(status, 200)
    [area] = body["areas"]
    self.assertEqual((area["name"], area["radiusKm"], area["progress"]), ("Las Vegas", 25.0, None))
    status, body, _ = self.request("/api/navigation/offline", payload={"action": "deleteArea", "id": area["id"]}, cookie=self.local_cookie)
    self.assertEqual((status, body["areas"]), (200, []))

  def test_settings_and_invalid_requests(self):
    status, body, _ = self.request("/api/navigation/offline", payload={"action": "settings", "patch": {"saveDriven": False}},
                                   cookie=self.local_cookie)
    self.assertEqual((status, body["settings"]), (200, {"saveDriven": False}))
    for payload in ({"action": "addArea", "area": {**AREA, "radiusKm": 900}}, {"action": "deleteArea", "id": "../x"},
                    {"action": "nope"}, {"action": "settings", "patch": {"saveDriven": 1}},
                    {"action": "addArea", "area": AREA, "extra": True}, []):
      status, body, _ = self.request("/api/navigation/offline", payload=payload, cookie=self.local_cookie)
      self.assertEqual(status, 400, payload)
      self.assertIn("error", body)

  def test_progress_comes_from_a_live_downloader_only(self):
    self.request("/api/navigation/offline", payload={"action": "addArea", "area": AREA}, cookie=self.local_cookie)
    [area] = OfflineState(self.root).areas()
    status = {"heartbeat": self.wall[0] - 2, "network": "wifi", "failure": None, "hasKey": True,
              "areas": {area["id"]: {"state": "downloading", "total": 400, "done": 120, "failed": 0}},
              "bytes": {"saved": 1, "driven": 2, "cache": 3}, "usage": {"tiles": 9, "freeTiles": 200000}}
    OfflineState(self.root).write_status(status)
    _, body, _ = self.request("/api/navigation/offline", cookie=self.local_cookie)
    self.assertTrue(body["service"]["running"])
    self.assertEqual(body["areas"][0]["progress"]["done"], 120)
    self.assertEqual(body["usage"]["tiles"], 9)
    self.wall[0] += 60
    _, body, _ = self.request("/api/navigation/offline", cookie=self.local_cookie)
    self.assertFalse(body["service"]["running"])
    self.assertIsNone(body["areas"][0]["progress"], "a stale status is not presented as progress")


class OfflineOwnerTest(unittest.TestCase):
  def test_bad_position_source_is_ignored(self):
    with tempfile.TemporaryDirectory() as root:
      owner = OfflineMapsOwner(root, position=lambda: {"latitude": "x"})
      self.assertIsNone(owner.snapshot()["position"])
      owner = OfflineMapsOwner(root, position=None)
      self.assertEqual(json.loads(json.dumps(owner.snapshot()))["areas"], [])

