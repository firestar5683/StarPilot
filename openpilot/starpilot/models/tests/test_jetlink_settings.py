"""Jetlink connection choices do not change the local model catalog."""
from types import SimpleNamespace
import tempfile
from pathlib import Path
import unittest

from jetlink.openpilot import Status
from openpilot.starpilot.models.jetlink_settings import JetlinkSettings
from openpilot.starpilot.models.manager import ModelManager, preferences


class MemoryParams:
  def __init__(self):
    self.values = {"JetlinkMode": 0, "JetlinkChargePhone": False}

  def get(self, key):
    return self.values.get(key)

  def get_bool(self, key):
    return self.values.get(key) is True

  def put(self, key, value, *, block):
    assert block
    self.values[key] = value

  put_bool = put


class TestJetlinkSettings(unittest.TestCase):
  def setUp(self):
    self.params = MemoryParams()
    self.chestnut = False
    self.device = "tizi"
    self.status = Status(enabled=True, mode="usb", transport="USB", present=True, port=None, ready=True, reason=None,
                         progress={"stage": "ready"}, model="remote", default_model="remote")
    self.owner = JetlinkSettings(params=self.params, device_type=lambda: self.device,
                                chestnut=lambda: self.chestnut, link=lambda: SimpleNamespace(status=lambda: self.status))

  def test_prepared_is_not_execution(self):
    self.owner.configure({"mode": "usb"})
    view = self.owner.snapshot()
    self.assertEqual(view["state"], "prepared")
    self.assertTrue(view["prepared"])
    self.assertFalse(view["active"])
    self.assertIsNone(view["activeArtifactSha256"])
    prepared = self.status
    self.status = prepared._replace(running="running", active=True, running_sha256="b" * 64, running_checkpoint="ckpt")
    view = self.owner.snapshot()
    self.assertEqual((view["state"], view["runtimeState"], view["active"]), ("active", "running", True))
    self.assertEqual((view["activeArtifactSha256"], view["activeCheckpoint"]), ("b" * 64, "ckpt"))
    # jetlink's phases, in Galaxy's words where they differ
    for running, state in (("ready", "waiting for disengagement"), ("retrying", "fallback / reconnecting")):
      self.status = prepared._replace(running=running)
      self.assertEqual(self.owner.snapshot()["state"], state)
    self.status = prepared._replace(ready=False, progress={"stage": "download", "msg": "Downloading"})
    self.assertEqual((self.owner.snapshot()["state"], self.owner.snapshot()["progress"]), ("preparing", "Downloading"))
    self.status = prepared._replace(reason="no gadget")
    self.assertEqual((self.owner.snapshot()["state"], self.owner.snapshot()["reason"]), ("unavailable", "no gadget"))

  def test_exact_choices_and_conflicts(self):
    for payload in ({"mode": 1}, {"mode": "other"}, {"chargePhone": 1}, {"unknown": True}):
      with self.assertRaises(ValueError):
        self.owner.configure(payload)
    self.chestnut = True
    with self.assertRaisesRegex(ValueError, "Chestnut"):
      self.owner.configure({"mode": "usb"})
    self.owner.configure({"mode": "off"})
    self.chestnut = False
    self.device = "tici"
    with self.assertRaisesRegex(ValueError, "3X"):
      self.owner.configure({"mode": "ios"})
    self.owner.configure({"mode": "off"})
    self.device = "mici"
    self.owner.configure({"mode": "ios", "chargePhone": True})
    self.assertEqual(self.params.values, {"JetlinkMode": 2, "JetlinkChargePhone": True})

  def test_manager_parked_guard_and_catalog_preserved(self):
    with tempfile.TemporaryDirectory() as tmp:
      parked = [True]
      manager = ModelManager(root=Path(tmp), parked=lambda: parked[0], gpu_present=lambda: False, jetlink=self.owner)
      before = preferences(Path(tmp))
      manager.action("jetlink", {"mode": "usb"})
      self.assertEqual(preferences(Path(tmp)), before)
      parked[0] = False
      with self.assertRaisesRegex(ValueError, "vehicle off"):
        manager.action("jetlink", {"mode": "off"})
      self.assertEqual(self.params.values["JetlinkMode"], 1)
