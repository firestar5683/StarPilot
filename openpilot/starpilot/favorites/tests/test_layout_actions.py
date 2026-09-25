import tempfile
import unittest
from pathlib import Path

from openpilot.common.params import Params
from openpilot.starpilot.favorites.layout_actions import TOGGLES, layout_actions
from openpilot.starpilot.favorites.owner import FavoritesOwner
from openpilot.starpilot.ui.onroad_customization import PARAM_KEY, STOPPED_TIMER_WIDGET, read_customization


class TestLayoutQuickSelect(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.allowed = True
    self.changes = 0

  def actions(self, profile="large"):
    def changed():
      self.changes += 1
    return layout_actions(self.params, profile, lambda: self.allowed, changed)

  def toggle(self, key, profile="large"):
    action = self.actions(profile)[key]
    self.assertTrue(action.invoke())
    return read_customization(self.params)

  def test_legacy_keys_keep_their_labels_and_meaning(self):
    large = self.actions()
    self.assertEqual(set(large), set(TOGGLES))
    self.assertEqual([(large[key].label, large[key].state_label) for key in ("HideSpeed", "EnableTorqueBarWidget", "RainbowPath")],
                     [("Hide Current Speed", "Off"), ("Show Torque Bar", "On"), ("Rainbow Road", "Off")])
    self.assertEqual({action.section for action in large.values()}, {"Visual"})
    self.assertEqual((large["StoppedTimer"].available, large["StoppedTimer"].reason), (False, "Only on the small UI"))
    compact = self.actions("compact")
    self.assertEqual((compact["HideSpeed"].available, compact["HideSpeed"].reason), (False, "Only on the large UI"))
    self.assertTrue(compact["StoppedTimer"].available)

  def test_toggles_edit_only_the_active_profile(self):
    document = self.toggle("HideSpeed")
    self.assertFalse(document["layouts"]["large"]["current_speed"]["enabled"])
    self.assertEqual(self.actions()["HideSpeed"].state_label, "On")
    document = self.toggle("HideSteeringWheel", "compact")
    self.assertEqual((document["layouts"]["compact"]["steering_wheel"]["enabled"],
                      document["layouts"]["large"]["steering_wheel"]["enabled"]), (False, True))
    self.assertIs(self.toggle("HideMaxSpeed")["showMaxSpeed"], False)
    self.assertFalse(self.toggle("HideMaxSpeed", "compact")["layouts"]["compact"]["max_speed"]["enabled"])
    self.assertTrue(self.toggle("StoppedTimer", "compact")["layouts"]["compact"][STOPPED_TIMER_WIDGET]["enabled"])
    self.assertFalse(self.toggle("EnableTorqueBarWidget")["layouts"]["large"]["torque_bar"]["enabled"])
    self.assertEqual(self.toggle("RainbowPath", "compact")["roadColors"]["compact"]["pathMode"], "rainbow")
    self.assertEqual(self.toggle("RainbowPath", "compact")["roadColors"]["compact"]["pathMode"], "acceleration")
    self.assertTrue(self.toggle("HideSpeed")["layouts"]["large"]["current_speed"]["enabled"])
    self.assertEqual(self.changes, 9)

  def test_authority_stale_bytes_and_invalid_layout_block_writes(self):
    self.allowed = False
    blocked = self.actions()["HideSpeed"]
    self.assertEqual((blocked.available, blocked.invoke), (False, None))
    self.allowed = True
    stale = self.actions()["HideSpeed"]
    self.toggle("RainbowPath")
    saved = self.params.get(PARAM_KEY)
    self.assertFalse(stale.invoke(), "a press bound to older bytes never writes")
    self.assertEqual(self.params.get(PARAM_KEY), saved)
    path = Path(self.params.get_param_path(PARAM_KEY))
    path.write_bytes(b'{"version": 99}')
    broken = self.actions()["HideSpeed"]
    self.assertEqual((broken.state_label, broken.available, broken.reason),
                     ("Unavailable", False, "Saved layout needs repair in Galaxy"))
    self.assertEqual(path.read_bytes(), b'{"version": 99}')

  def test_slot_saved_before_retirement_works_through_the_owner(self):
    owner = FavoritesOwner(self.params, self.actions, lambda: True)
    self.assertTrue(owner.configure_index(0, "HideSpeed", owner.snapshot().revision))
    slot = owner.snapshot().slots[0]
    self.assertEqual((slot.label, slot.state_label, slot.available), ("Hide Current Speed", "Off", True))
    result = owner.invoke(slot.request)
    self.assertEqual((result.success, result.state_label), (True, "On"))
    self.assertFalse(owner.invoke(slot.request).success, "the same press cannot apply twice")
    self.assertFalse(read_customization(self.params)["layouts"]["large"]["current_speed"]["enabled"])


if __name__ == "__main__":
  unittest.main()
