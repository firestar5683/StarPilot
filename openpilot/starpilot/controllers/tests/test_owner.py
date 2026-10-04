import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import dataclass

from openpilot.starpilot.controllers.owner import CONTROLLER_BINDINGS_PARAM, ControllerOwner
from openpilot.starpilot.favorites.state import FavoriteAction, FavoriteRequest, FavoriteResult, FavoriteSlot, FavoriteSnapshot


@dataclass(frozen=True)
class Press:
  device_id: str
  code: int
  timestamp_ns: int


class FileParams:
  def __init__(self, root):
    self.root = Path(root) / "params"
    self.root.mkdir()

  def get_param_path(self, key):
    return str(self.root / key)


class TestControllerOwner(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = FileParams(temporary.name)
    self.path = Path(self.params.get_param_path(CONTROLLER_BINDINGS_PARAM))
    self.now = 1_000_000_000
    self.parked = True
    self.available = True
    self.token = "original"
    self.calls = 0
    self.favorite_calls = []
    self.device: dict = {"id": "stable-device", "name": "Test pad", "bus": 3}
    self.owner = ControllerOwner(self.params, parked=lambda: self.parked, actions=self.actions,
                                 favorites=self.favorites, invoke_favorite=self.invoke_favorite, clock=lambda: self.now)
    self.owner.set_devices([self.device])

  def actions(self):
    return {"safe.action": FavoriteAction("safe.action", "Safe action", available=self.available,
                                           token=self.token, invoke=self.invoke, section="Actions")}

  def invoke(self):
    self.calls += 1
    return True

  def favorites(self):
    request = FavoriteRequest(0, "favorite.action", "favorite-revision", "favorite-token")
    slots = (FavoriteSlot(0, "favorite.action", "Favorite", True, True, available=self.available, request=request),
             FavoriteSlot(1), FavoriteSlot(2))
    return FavoriteSnapshot(slots, (), "favorite-revision", True, True)

  def invoke_favorite(self, request):
    self.favorite_calls.append(request)
    return FavoriteResult(True, "Favorite")

  def configure(self, *, enabled=True, key="safe.action"):
    snapshot = self.owner.snapshot()
    return self.owner.action({"operation": "save", "revision": snapshot["revision"], "enabled": enabled,
                              "slots": [key] + [None] * 9})

  def learn(self, slot, code=42):
    snapshot = self.owner.snapshot()
    self.owner.action({"operation": "learn", "revision": snapshot["revision"], "slot": slot})
    self.now += 1_000_000
    self.owner.feed(Press(self.device["id"], code, self.now))

  def test_default_persistence_revision_and_exact_shape(self):
    before = self.owner.snapshot()
    self.assertEqual(len(before["slots"]), 13)
    self.assertEqual(before["devices"], [self.device])
    self.assertFalse(before["enabled"])
    self.assertFalse(self.path.exists())
    after = self.configure()
    self.assertTrue(after["enabled"])
    self.assertNotEqual(after["revision"], before["revision"])
    self.assertEqual(json.loads(self.path.read_bytes()), {"version": 1, "enabled": True,
                                                           "slots": ["safe.action"] + [None] * 9, "bindings": []})
    with self.assertRaises(RuntimeError):
      self.owner.action({"operation": "save", "revision": before["revision"], "enabled": False, "slots": [None] * 10})

  def test_learning_only_trusted_new_press_then_fresh_execution(self):
    self.configure()
    self.owner.action({"operation": "learn", "revision": self.owner.snapshot()["revision"], "slot": 3})
    self.owner.feed(Press(self.device["id"], 42, self.now - 1))
    self.owner.feed(Press("forged", 42, self.now + 1))
    self.assertEqual(self.owner.snapshot()["bindings"], [])
    self.now += 1_000_000
    self.owner.feed(Press(self.device["id"], 42, self.now))
    self.assertEqual(self.owner.snapshot()["bindings"], [{"deviceId": self.device["id"], "name": self.device["name"],
                                                           "code": 42, "slot": 3}])
    self.assertEqual(self.calls, 0)
    self.now += 1_000_000
    press = Press(self.device["id"], 42, self.now)
    self.owner.feed(press)
    self.owner.feed(press)
    self.assertEqual(self.calls, 1)
    self.assertTrue(self.owner.snapshot()["lastPress"]["executed"])

  def test_test_mode_and_park_transition_never_execute(self):
    self.configure()
    self.learn(3)
    self.owner.action({"operation": "test", "enabled": True})
    self.now += 1_000_000
    self.owner.feed(Press(self.device["id"], 42, self.now))
    self.assertEqual(self.calls, 0)
    self.assertEqual(self.owner.snapshot()["lastPress"]["message"], "Test press detected")
    self.parked = False
    self.owner.tick()
    self.assertFalse(self.owner.snapshot()["testing"])
    self.assertFalse(self.owner.snapshot()["editable"])
    with self.assertRaises(PermissionError):
      self.owner.action({"operation": "cancel"})

  def test_favorite_reference_and_stale_or_unavailable_press(self):
    self.configure()
    self.learn(0)
    self.now += 1_000_000
    self.owner.feed(Press(self.device["id"], 42, self.now))
    self.assertEqual(len(self.favorite_calls), 1)
    self.owner.feed(Press(self.device["id"], 42, self.now - 251_000_000))
    self.owner.feed(Press(self.device["id"], 42, self.now + 1))
    self.assertEqual(len(self.favorite_calls), 1)
    self.available = False
    self.now += 1_000_000
    self.owner.feed(Press(self.device["id"], 42, self.now))
    self.assertEqual(len(self.favorite_calls), 1)

  def test_invalid_saved_document_stays_inert_and_repair_uses_exact_revision(self):
    self.path.write_bytes(b'{"version":1,"enabled":true,"enabled":false}')
    corrupted = self.owner.snapshot()
    self.assertFalse(corrupted["valid"])
    self.owner.feed(Press(self.device["id"], 42, self.now))
    self.assertEqual(self.calls, 0)
    self.assertEqual(self.path.read_bytes(), b'{"version":1,"enabled":true,"enabled":false}')
    self.owner.action({"operation": "save", "revision": corrupted["revision"], "enabled": False, "slots": [None] * 10})
    self.assertTrue(self.owner.snapshot()["valid"])

  def test_remove_and_invalid_payloads(self):
    self.configure()
    self.learn(3)
    rev = self.owner.snapshot()["revision"]
    self.owner.action({"operation": "remove", "revision": rev, "deviceId": self.device["id"], "code": 42})
    self.assertEqual(self.owner.snapshot()["bindings"], [])
    with self.assertRaises(ValueError):
      self.owner.action({"operation": "simulate", "deviceId": self.device["id"], "code": 42})
    with self.assertRaises(ValueError):
      self.owner.action({"operation": "save", "revision": self.owner.snapshot()["revision"],
                         "enabled": True, "slots": ["unknown"] + [None] * 9})

  def test_hat_code_and_changed_action_token_do_not_bypass_recheck(self):
    self.configure()
    self.learn(3, 65551)
    original = self.owner.actions
    calls = 0
    def changing_actions():
      nonlocal calls
      calls += 1
      self.token = "before" if calls == 1 else "after"
      return original()
    self.owner.actions = changing_actions
    self.now += 1_000_000
    self.owner.feed(Press(self.device["id"], 65551, self.now))
    self.assertEqual(self.calls, 0)
    self.assertEqual(self.owner.snapshot()["lastPress"]["message"], "Control changed")

  def test_learning_expiry_and_motion_cancel_are_inert(self):
    self.configure()
    self.owner.action({"operation": "learn", "revision": self.owner.snapshot()["revision"], "slot": 3})
    self.now += 20_000_000_000
    self.owner.tick()
    self.assertIsNone(self.owner.snapshot()["learning"])
    self.owner.feed(Press(self.device["id"], 42, self.now))
    self.assertEqual(self.owner.snapshot()["bindings"], [])
    self.owner.action({"operation": "learn", "revision": self.owner.snapshot()["revision"], "slot": 3})
    self.parked = False
    self.owner.tick()
    self.parked = True
    self.now += 1_000_000
    self.owner.feed(Press(self.device["id"], 42, self.now))
    self.assertEqual(self.owner.snapshot()["bindings"], [])

  def test_queued_press_during_expiring_session_cannot_execute(self):
    self.configure()
    self.learn(3)
    self.owner.action({"operation": "test", "enabled": True})
    session_press = self.now + 19_900_000_000
    self.now += 20_000_000_000
    self.owner.feed(Press(self.device["id"], 42, session_press))
    self.assertEqual(self.calls, 0)
    self.assertFalse(self.owner.snapshot()["testing"])
    self.now += 1_000_000
    self.owner.feed(Press(self.device["id"], 42, self.now))
    self.assertEqual(self.calls, 1)

  def test_queued_presses_after_cancel_or_motion_do_not_execute(self):
    self.configure()
    self.learn(3)
    self.owner.action({"operation": "test", "enabled": True})
    queued = self.now + 1_000_000
    self.now = queued
    self.owner.action({"operation": "cancel"})
    self.owner.feed(Press(self.device["id"], 42, queued))
    self.assertEqual(self.calls, 0)
    self.owner.action({"operation": "test", "enabled": True})
    self.parked = False
    self.now += 1_000_000
    self.owner.tick()
    self.parked = True
    self.owner.feed(Press(self.device["id"], 42, self.now))
    self.assertEqual(self.calls, 0)
    self.now += 1_000_000
    self.owner.feed(Press(self.device["id"], 42, self.now))
    self.assertEqual(self.calls, 1)

  def test_changed_saved_document_cancels_learning_without_overwrite(self):
    self.configure()
    self.owner.action({"operation": "learn", "revision": self.owner.snapshot()["revision"], "slot": 3})
    changed = json.loads(self.path.read_bytes())
    changed["enabled"] = False
    self.path.write_text(json.dumps(changed))
    before = self.path.read_bytes()
    self.now += 1_000_000
    self.owner.feed(Press(self.device["id"], 42, self.now))
    self.assertEqual(self.path.read_bytes(), before)
    self.assertIsNone(self.owner.snapshot()["learning"])


if __name__ == "__main__":
  unittest.main()
