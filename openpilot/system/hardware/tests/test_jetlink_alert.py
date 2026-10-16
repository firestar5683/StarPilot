"""hardwared's Jetlink offroad alert says why the link cannot run, and never takes hardwared down."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from openpilot.common.params import UnknownKeyName
from openpilot.system.hardware import hardwared


class TestJetlinkAlert(unittest.TestCase):
  def setUp(self):
    hardwared.jetlink_alert_usable = True
    self.addCleanup(setattr, hardwared, 'jetlink_alert_usable', True)
    self.reason = Mock(return_value='no usable gadget')
    self.link = SimpleNamespace(hooks=lambda: SimpleNamespace(reason=self.reason))
    self.set_alert = Mock()
    for name, value in (('jetlink_adapter', self.link), ('set_offroad_alert_if_changed', self.set_alert), ('cloudlog', Mock())):
      patcher = patch.object(hardwared, name, value)
      patcher.start()
      self.addCleanup(patcher.stop)

  def test_the_alert_follows_jetlinks_reason(self):
    hardwared.update_jetlink_alert()
    self.set_alert.assert_called_with('Offroad_JetlinkUnavailable', True, extra_text='no usable gadget')
    self.reason.return_value = None
    hardwared.update_jetlink_alert()
    self.set_alert.assert_called_with('Offroad_JetlinkUnavailable', False, extra_text=None)

  def test_with_the_link_off_jetlink_is_not_bound(self):
    from jetlink.openpilot.hooks import Hooks
    from openpilot.starpilot.models.jetlink_adapter import API
    factory = Mock()
    self.link.hooks = lambda: Hooks(API, factory, link_on=lambda: False)
    hardwared.update_jetlink_alert()
    factory.assert_not_called()
    self.set_alert.assert_called_once_with('Offroad_JetlinkUnavailable', False, extra_text=None)

  def test_a_params_library_without_the_key_turns_the_alert_off_once(self):
    self.set_alert.side_effect = UnknownKeyName(b'Offroad_JetlinkUnavailable')
    hardwared.update_jetlink_alert()
    hardwared.update_jetlink_alert()
    self.set_alert.assert_called_once()
    hardwared.cloudlog.warning.assert_called_once()


if __name__ == '__main__':
  unittest.main()
