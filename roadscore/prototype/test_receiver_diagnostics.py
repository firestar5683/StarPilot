from pathlib import Path
import tempfile
import unittest
from launch_health import LaunchFailure, describe_failure
from receiver_diagnostics import receiver_failure

class ReceiverDiagnosticsTests(unittest.TestCase):
 def test_preserves_actual_final_error_and_log_location(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'receiver.log';p.write_text('noise\n'*10000+'Traceback (most recent call last):\n  app.py:200\nRuntimeError: Selected Bluetooth speaker missing\n')
   e=receiver_failure(LaunchFailure('receiver',1),p)
   self.assertIn('Selected Bluetooth speaker missing',str(e));self.assertIn(str(p),str(e))
   self.assertLess(len(str(e)),2100);self.assertEqual(describe_failure(e)['failure_exit_code'],1)
 def test_secret_redaction_and_missing_log(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'receiver.log';p.write_text('token=abcdef\nAuthorization: Bearer secret123\n{"password":"hidden"}\nhttps://user:pass@example.test\nValueError: output unavailable\n')
   text=str(receiver_failure(LaunchFailure('receiver',1),p))
   for secret in ['abcdef','secret123','hidden','user:pass']:self.assertNotIn(secret,text)
   self.assertIn('ValueError: output unavailable',text)
   self.assertIn('unavailable',str(receiver_failure(LaunchFailure('receiver',1),Path(d)/'absent')))
 def test_other_failures_unchanged(self):
  e=ValueError('original');self.assertIs(receiver_failure(e,'/unused'),e);self.assertEqual(str(e),'original')

if __name__=='__main__':unittest.main()
