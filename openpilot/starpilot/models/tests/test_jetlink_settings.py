"""Jetlink connection choices do not change the local model catalog."""
from types import SimpleNamespace
import tempfile
from pathlib import Path
import unittest

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
    self.runtime = {"state": "unavailable", "active": False}
    self.status = SimpleNamespace(enabled=True, present=True, ready=True, reason=None,
                                  progress={"stage": "ready"}, model="remote", transport="USB")
    self.owner = JetlinkSettings(params=self.params, device_type=lambda: self.device,
                                chestnut=lambda: self.chestnut, runtime=lambda: self.runtime, link=lambda: SimpleNamespace(status=lambda: self.status))

  def test_prepared_is_not_execution(self):
    self.owner.configure({"mode": "usb"})
    view = self.owner.snapshot()
    self.assertEqual(view["state"], "prepared")
    self.assertTrue(view["prepared"])
    self.assertFalse(view["active"])
    self.runtime = {"state": "running", "active": True}
    self.assertEqual(self.owner.snapshot()["state"], "active")
    self.runtime = {"state": "unavailable", "active": False}
    self.status.ready = False
    self.status.progress = {"stage": "joining", "msg": "Connecting"}
    self.assertEqual(self.owner.snapshot()["state"], "joining")

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
