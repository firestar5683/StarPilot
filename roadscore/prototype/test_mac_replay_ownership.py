import errno
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import mac_showcase
from mac_replay_ownership import ReplayBusy, check_camera_port, mac_replay_lease, preflight


class MacReplayOwnershipTests(unittest.TestCase):
  def setUp(self):
    temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
    self.root=Path(temporary.name)

  def test_two_real_descriptors_are_exclusive_and_release_on_exception(self):
    check=MagicMock()
    with self.assertRaisesRegex(ValueError,'fixture failure'):
      with mac_replay_lease(self.root,port_check=check) as held:
        self.assertFalse(os.get_inheritable(held.fileno()))
        with self.assertRaises(ReplayBusy):
          with mac_replay_lease(self.root,port_check=check):self.fail('Second lease acquired')
        self.assertEqual(check.call_count,1)
        raise ValueError('fixture failure')
    with mac_replay_lease(self.root,port_check=check):pass
    self.assertEqual(check.call_count,2)

  def test_port_failure_releases_lease_and_preflight_does_not_hold_it(self):
    with patch('mac_replay_ownership.check_camera_port',side_effect=ReplayBusy('busy')):
      with self.assertRaises(ReplayBusy):preflight(self.root)
    with patch('mac_replay_ownership.check_camera_port') as check:
      preflight(self.root)
      with mac_replay_lease(self.root):pass
      self.assertEqual(check.call_count,2)

  def test_port_probe_reports_busy_without_connecting_or_sending(self):
    probe=MagicMock();probe.__enter__.return_value=probe
    with patch('mac_replay_ownership.socket.socket',return_value=probe):
      check_camera_port()
      probe.bind.assert_called_once_with(('0.0.0.0',9000))
      probe.connect.assert_not_called();probe.send.assert_not_called()
      probe.bind.side_effect=OSError(errno.EADDRINUSE,'in use')
      with self.assertRaisesRegex(ReplayBusy,'port 9000'):check_camera_port()

  def test_parent_holds_lease_before_any_preparation(self):
    args=mac_showcase.parser().parse_args(['--project-root',str(self.root)])
    def prepared(value):
      with self.assertRaises(ReplayBusy):
        with mac_replay_lease(self.root/'roadscore',port_check=lambda:None):pass
      return 17
    with (patch('mac_showcase.parser') as parser,patch('mac_showcase.parent_main',side_effect=prepared) as parent,
          patch('mac_showcase.sys.platform','darwin'),patch('mac_replay_ownership.check_camera_port')):
      parser.return_value.parse_args.return_value=args
      self.assertEqual(mac_showcase.main(),17)
      parent.assert_called_once_with(args)
    with mac_replay_lease(self.root/'roadscore',port_check=lambda:None):pass

  def test_worker_and_check_never_acquire_parent_lease(self):
    for flags,target in ((['--audio-worker'],'audio_worker'),(['--check'],'parent_main')):
      args=mac_showcase.parser().parse_args(flags)
      with (patch('mac_showcase.parser') as parser,patch('mac_showcase.'+target,return_value=23),
            patch('mac_showcase.sys.platform','darwin'),patch('mac_replay_ownership.mac_replay_lease') as lease):
        parser.return_value.parse_args.return_value=args
        self.assertEqual(mac_showcase.main(),23)
        lease.assert_not_called()


if __name__=='__main__':unittest.main()
