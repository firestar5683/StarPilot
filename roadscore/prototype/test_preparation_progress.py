import json
import tempfile
import unittest
from pathlib import Path
from preparation_progress import current_progress

class ProgressTests(unittest.TestCase):
 def test_only_current_matching_worker_can_update_preparing(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'worker.json'
   path.write_text(json.dumps({'generation_seed':12,'profile':'prism','phase':'preparing','accepted_buffer_seconds':53,'elapsed_seconds':120}))
   args=dict(seed=12,profile='prism',launch_wall=path.stat().st_mtime-1)
   result=current_progress(path,**args)
   self.assertEqual(result['buffered'],53);self.assertEqual(result['readiness'],'PREPARING')
   self.assertIsNone(current_progress(path,**{**args,'seed':13}))
   self.assertIsNone(current_progress(path,**{**args,'profile':'aurora'}))
   self.assertIsNone(current_progress(path,**{**args,'launch_wall':path.stat().st_mtime+1}))
 def test_ready_worker_does_not_claim_started_playback(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'worker.json'
   path.write_text(json.dumps({'generation_seed':12,'profile':'prism','phase':'READY','initial_buffer_seconds':81}))
   result=current_progress(path,seed=12,profile='prism',launch_wall=0)
   self.assertEqual(result['readiness'],'PREPARING');self.assertEqual(result['preparation_worker_phase'],'READY')
   path.write_text('{');self.assertIsNone(current_progress(path,seed=12,profile='prism',launch_wall=0))

if __name__=='__main__':unittest.main()
