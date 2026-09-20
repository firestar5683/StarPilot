import os
import signal
import unittest
from unittest.mock import Mock, patch
from native_prepared_showcase import cleanup_owned

class CleanupTests(unittest.TestCase):
 def test_second_stop_during_wait_does_not_skip_display(self):
  child=Mock(pid=123);child.poll.return_value=None
  child.wait.side_effect=lambda **kw:os.kill(os.getpid(),signal.SIGTERM)
  display=Mock();log=Mock();old=signal.getsignal(signal.SIGTERM)
  with patch('native_prepared_showcase.os.killpg'):
   self.assertEqual(cleanup_owned({'ui':child},display,[log]),[])
  display.close.assert_called_once();log.close.assert_called_once()
  self.assertEqual(signal.getsignal(signal.SIGTERM),old)
 def test_failed_child_does_not_skip_other_children_or_display(self):
  bad=Mock(pid=1);bad.poll.side_effect=OSError('gone')
  good=Mock(pid=2);good.poll.return_value=None;display=Mock()
  with patch('native_prepared_showcase.os.killpg'):
   self.assertEqual(len(cleanup_owned({'good':good,'bad':bad},display,[])),1)
  good.wait.assert_called_once();display.close.assert_called_once()
