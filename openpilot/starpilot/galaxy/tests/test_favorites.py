import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from openpilot.common.params import Params
from openpilot.starpilot.favorites.actions import BOOKMARK, SET_SPEED
from openpilot.starpilot.favorites.owner import FAVORITE_SLOTS_PARAM, default_slots
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.favorites import FavoritesGateway
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.galaxy.settings import AuthorityContext


class Context:
  def sample(self):
    return AuthorityContext(False, None, None)


class TestFavoritesHttp(unittest.TestCase):
  def setUp(self):
    directory = tempfile.TemporaryDirectory()
    self.addCleanup(directory.cleanup)
    self.params = Params(str(Path(directory.name) / "params"))
    self.gateway = FavoritesGateway(self.params, Context())
    self.server = make_server(port=0, owner=GalaxyAccessOwner(Path(directory.name) / "access"), favorites=self.gateway)
    self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
    self.thread.start()
    self.addCleanup(self.stop)

  def stop(self):
    self.server.shutdown()
    self.thread.join(timeout=2)
    self.server.server_close()

  def request(self, path="/api/favorites/slots", payload=None, cookie="", *, origin=None, raw=None):
    connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
    headers = {"Cookie": cookie}
    if payload is not None or raw is not None:
      headers.update({"Content-Type": "application/json", "Origin": origin or f"http://127.0.0.1:{self.server.server_port}"})
    try:
      connection.request("POST" if payload is not None or raw is not None else "GET", path,
                         body=raw if raw is not None else json.dumps(payload) if payload is not None else None, headers=headers)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()

  def login(self):
    code, _, headers = self.request("/api/auth/session")
    self.assertEqual(code, 200)
    return headers["Set-Cookie"].split(";", 1)[0]

  def test_config_allowed_without_parked_authority_but_does_not_invoke_control(self):
    self.assertEqual(self.request()[0], 401)
    cookie = self.login()
    code, data, _ = self.request(cookie=cookie)
    self.assertEqual(code, 200)
    self.assertTrue(data["editable"])
    self.assertEqual(data["slots"], default_slots())
    self.assertIn(BOOKMARK, {option["key"] for option in data["options"]})
    self.assertFalse(next(option["available"] for option in data["options"] if option["key"] == BOOKMARK))
    slots = data["slots"]
    slots[0] = {"enabled": True, "show_onroad": True, "key": BOOKMARK, "label": "Mark"}
    payload = {"revision": data["revision"], "slots": slots}
    code, saved, _ = self.request(payload=payload, cookie=cookie)
    self.assertEqual(code, 200)
    self.assertEqual(saved["slots"], slots)
    favorite_path = Path(self.params.get_param_path(FAVORITE_SLOTS_PARAM))
    self.assertEqual(list(favorite_path.parent.iterdir()), [favorite_path])
    self.assertEqual(self.request(payload=payload, cookie=cookie)[0], 409)
    self.assertEqual(self.request("/api/favorites/action", {"key": BOOKMARK}, cookie)[0], 405)

  def test_write_requires_session_origin_unique_fields_and_registered_control(self):
    cookie = self.login()
    _, data, _ = self.request(cookie=cookie)
    payload = {"revision": data["revision"], "slots": data["slots"]}
    self.assertEqual(self.request(payload=payload)[0], 401)
    self.assertEqual(self.request(payload=payload, cookie=cookie, origin="http://example.com")[0], 403)
    self.assertEqual(self.request(cookie=cookie, raw='{"revision":"a","revision":"b","slots":[]}')[0], 400)
    payload["slots"][0]["key"] = "ArbitraryParam"
    self.assertEqual(self.request(payload=payload, cookie=cookie)[0], 400)
    self.assertFalse(Path(self.params.get_param_path(FAVORITE_SLOTS_PARAM)).exists())

  def test_set_speed_preserved_for_device_execution_without_http_invocation(self):
    slots = default_slots()
    slots[1] = {"enabled": True, "show_onroad": True, "key": SET_SPEED, "label": "45 mph", "value": 45}
    Path(self.params.get_param_path(FAVORITE_SLOTS_PARAM)).write_text(json.dumps(slots))
    cookie = self.login()
    code, data, _ = self.request(cookie=cookie)
    self.assertEqual(code, 200)
    self.assertEqual(data["slots"], slots)
    self.assertFalse(data["states"][1]["available"])
    self.assertIn("Use the qualified control on the device", data["states"][1]["reason"])
    data["slots"][0] = {"enabled": True, "show_onroad": True, "key": BOOKMARK, "label": "Bookmark"}
    self.assertEqual(self.request(payload={"revision": data["revision"], "slots": data["slots"]}, cookie=cookie)[0], 200)
    self.assertEqual(json.loads(Path(self.params.get_param_path(FAVORITE_SLOTS_PARAM)).read_text())[1], slots[1])

  def test_speed_edit_persists_and_preserves_other_slots_with_revision_protection(self):
    slots = default_slots()
    slots[0] = {"enabled": True, "show_onroad": False, "key": SET_SPEED, "label": "Cruise", "value": 30}
    slots[1] = {"enabled": True, "show_onroad": True, "key": BOOKMARK, "label": "Mark"}
    slots[2] = {"enabled": False, "show_onroad": False, "key": "OldUnsupportedSetting", "label": "Keep me"}
    path = Path(self.params.get_param_path(FAVORITE_SLOTS_PARAM))
    path.write_text(json.dumps(slots))
    cookie = self.login()
    _, data, _ = self.request(cookie=cookie)
    data["slots"][0]["value"] = 45
    payload = {"revision": data["revision"], "slots": data["slots"]}
    code, saved, _ = self.request(payload=payload, cookie=cookie)
    self.assertEqual(code, 200)
    expected = [{**slots[0], "value": 45}, *slots[1:]]
    self.assertEqual(saved["slots"], expected)
    self.assertEqual(json.loads(path.read_text()), expected)
    code, reloaded, _ = self.request(cookie=cookie)
    self.assertEqual(code, 200)
    self.assertEqual(reloaded["slots"], expected)
    self.assertNotEqual(reloaded["revision"], payload["revision"])
    payload["slots"][0]["value"] = 60
    self.assertEqual(self.request(payload=payload, cookie=cookie)[0], 409)
    self.assertEqual(json.loads(path.read_text()), expected)
    self.assertEqual(self.request("/api/favorites/action", {"key": SET_SPEED}, cookie)[0], 405)


if __name__ == "__main__":
  unittest.main()
