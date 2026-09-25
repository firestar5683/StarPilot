from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import patch
from openpilot.starpilot.galaxy.tests import test_navigation_http as helpers
from openpilot.starpilot.drive_state.owner import DriveStateOwner, Mode
from openpilot.starpilot.drive_state.control import DriveStateControl
from openpilot.starpilot.drive_state.tests.test_owner import Params, BOOT


class ForceHttpTest(unittest.TestCase):
  close = helpers.NavigationHttpTest.close
  request = helpers.NavigationHttpTest.request

  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params()
    self.drive = DriveStateOwner(self.params, Path(temporary.name) / 'drive', alive=lambda _: True)
    self.drive.initialize(pid=1, birth=2, boot=BOOT)
    self.allowed = True
    self.physical = NS(allowed=lambda: self.allowed)
    self.control = DriveStateControl(self.drive, self.physical, effective=lambda: False)
    original = helpers.make_server
    with patch.object(helpers, 'make_server', side_effect=lambda **kwargs: original(**kwargs, drive_state=self.control)):
      helpers.NavigationHttpTest.setUp(self)

  def drive_action(self, mode, remote=False, revision=None, **kwargs):
    return self.request(
      '/api/drive-state/action',
      payload={'mode': mode, 'revision': revision or self.drive.snapshot().revision},
      remote=remote,
      cookie=self.remote_cookie if remote else self.local_cookie,
      **kwargs,
    )

  def test_local_remote_same_owner_status_actual_not_requested_and_strict_revision(self):
    result = self.drive_action('onroad')
    self.assertEqual(result[0], 200)
    self.assertEqual((result[1]['mode'], result[1]['effective']), ('onroad', 'offroad'))
    status = self.request('/api/drive-state/status', remote=True, cookie=self.remote_cookie)
    self.assertEqual(status[1]['revision'], result[1]['revision'])
    self.assertEqual(self.drive_action('offroad', remote=True)[0], 200)
    self.assertEqual(self.drive_action('auto', revision=result[1]['revision'])[0], 409)

  def test_physical_loss_blocks_override_but_auto_and_same_request_remain_recoverable(self):
    self.assertEqual(self.drive_action('offroad')[0], 200)
    self.allowed = False
    self.assertEqual(self.drive_action('onroad')[0], 409)
    self.assertEqual(self.drive.snapshot().mode, Mode.OFFROAD)
    self.assertEqual(self.drive_action('auto', remote=True)[0], 200)
    self.assertEqual(self.drive.snapshot().mode, Mode.AUTO)

  def test_auth_origin_schema_and_midcommit_revocation_write_nothing(self):
    before = list(self.params.writes)
    self.assertEqual(self.request('/api/drive-state/action', payload={'mode': 'onroad', 'revision': self.drive.snapshot().revision})[0], 401)
    self.assertEqual(self.drive_action('onroad', origin='https://unrelated.invalid')[0], 403)
    self.assertEqual(self.drive_action('badmode')[0], 409)
    self.assertEqual(self.params.writes, before)
    calls = []

    def revoke():
      calls.append(1)
      if len(calls) == 2:
        self.pairing.unpair()
      return True

    self.physical.allowed = revoke
    self.assertEqual(self.drive_action('onroad', remote=True)[0], 409)
    self.assertEqual(self.params.writes, before)

  def test_authenticated_force_offroad_from_live_onroad_state(self):
    from openpilot.starpilot.drive_state.evidence import PhysicalSource
    from openpilot.starpilot.drive_state.tests.test_evidence import Messages
    from openpilot.starpilot.drive_state.resolver import should_start
    messages = Messages()
    messages.after_mono_ns = 1_000_000_000
    messages.values['deviceState'] = NS(started=True)
    messages.values['pandaStates'][0].ignitionLine = True
    messages.values['pandaStates'][0].safetyModel = 'hyundai'
    physical = PhysicalSource(messages, mono=lambda: 2_100_000_000, boot=lambda: 12_100_000_000)
    self.addCleanup(physical.close)
    self.control.physical = physical
    self.control.effective = lambda: messages.values['deviceState'].started
    status = self.request('/api/drive-state/status', remote=True, cookie=self.remote_cookie)
    self.assertEqual(status[1]['effective'], 'onroad')
    self.assertTrue(status[1]['overrideAllowed'])
    result = self.drive_action('offroad', remote=True)
    self.assertEqual(result[0], 200)
    self.assertEqual(result[1]['mode'], 'offroad')
    # hardwared consumes this same owner request through the actual resolver.
    messages.values['deviceState'].started = should_start(self.drive.snapshot().mode,
      {'ignition': True}, {'ready': True}, already_started=True)
    self.assertFalse(messages.values['deviceState'].started)
    self.assertEqual(self.request('/api/drive-state/status', remote=True, cookie=self.remote_cookie)[1]['effective'], 'offroad')
