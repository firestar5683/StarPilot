import json
import fcntl
from pathlib import Path
import tempfile
import threading
import time
import unittest
from resident_session import request_preparation, session_active, session_lease, validate_session

SELECTION = dict(profile='prism', generation_seed=123, composition_policy='hook-cache-v1', bank_sha256='a'*64)

class ResidentTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def request(self, timeout=.5):
  return request_preparation(self.root,'prism',123,'hook-cache-v1','a'*64,timeout)
 def responder(self, change=None):
  def run():
   deadline=time.monotonic()+1
   path=self.root/'session_request.json'
   while not path.exists() and time.monotonic()<deadline:time.sleep(.005)
   if not path.exists():return
   payload=json.loads(path.read_text());payload.update(phase='READY',preparation_id='fresh-123')
   if change:payload.update(change)
   (self.root/'session_result.json').write_text(json.dumps(payload))
  t=threading.Thread(target=run);t.start();self.addCleanup(t.join)
 def test_identity_validation(self):
  self.assertEqual(validate_session(SELECTION),('prism',123,'hook-cache-v1','a'*64))
  for field,value in [('generation_seed',None),('generation_seed',True),('generation_seed',2**32),('profile','unknown'),('composition_policy','prepared-v1'),('bank_sha256','abc')]:
   with self.subTest(field=field,value=value),self.assertRaises(ValueError):validate_session({**SELECTION,field:value})
 def test_active_playback_blocks_requests(self):
  with session_lease(self.root):
   self.assertTrue(session_active(self.root))
   with self.assertRaisesRegex(RuntimeError,'owns'):self.request()
   self.assertFalse((self.root/'session_request.json').exists())
  self.assertFalse(session_active(self.root))
 def test_exact_ack_ignores_stale_ready(self):
  (self.root/'session_result.json').write_text(json.dumps({'id':'old','phase':'READY'}))
  self.responder();result=self.request()
  self.assertEqual(result['generation_seed'],123);self.assertNotEqual(result['id'],'old')
 def test_wrong_identity_ack_fails(self):
  self.responder({'bank_sha256':'b'*64})
  with self.assertRaisesRegex(RuntimeError,'different session'):self.request()
 def test_serialized_commands(self):
  with (self.root/'session_command.lock').open('a') as handle:
   fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaises(BlockingIOError):self.request()
   self.assertFalse((self.root/'session_request.json').exists())
 def test_ready_without_preparation_provenance_fails(self):
  self.responder({'preparation_id':None})
  with self.assertRaisesRegex(RuntimeError,'provenance'):self.request()
 def test_worker_failure_propagates(self):
  self.responder({'error':'quality rejected'})
  with self.assertRaisesRegex(RuntimeError,'quality rejected'):self.request()
 def test_timeout_preserves_request_and_refuses_retry(self):
  with self.assertRaises(TimeoutError):self.request(.02)
  original=(self.root/'session_request.json').read_bytes()
  with self.assertRaisesRegex(RuntimeError,'unacknowledged'):self.request()
  self.assertEqual(original,(self.root/'session_request.json').read_bytes())

if __name__=='__main__':unittest.main()
