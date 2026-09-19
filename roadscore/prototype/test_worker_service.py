import unittest
from unittest.mock import patch
from worker_service import owned
class ServiceOwnershipTest(unittest.TestCase):
 def test_reused_pid_not_owned(self):
  with patch('worker_service.stamp',return_value='new'),patch('worker_service.command',return_value='python worker_service.py serve'):
   self.assertFalse(owned({'pid':123,'start_ticks':'old'}))
 def test_external_process_not_owned(self):
  with patch('worker_service.stamp',return_value='same'),patch('worker_service.command',return_value='python another_task.py'):
   self.assertFalse(owned({'pid':123,'start_ticks':'same'}))
 def test_matching_service_owned(self):
  with patch('worker_service.stamp',return_value='same'),patch('worker_service.command',return_value='python /data/roadscore/prototype/worker_service.py serve'):
   self.assertTrue(owned({'pid':123,'start_ticks':'same'}))

 def test_offroad_guard_reads_fresh_value_from_cached_reader(self):
  from unittest.mock import Mock
  from worker_service import offroad
  params=Mock();params.get_bool.side_effect=[False,True]
  with patch('worker_service._params',params):
   self.assertTrue(offroad());self.assertFalse(offroad())
  self.assertEqual(params.get_bool.call_count,2)
