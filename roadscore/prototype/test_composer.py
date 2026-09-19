import os,unittest
from unittest.mock import patch
import numpy as np
from composer_choice import choice,worker_path
from composer_audio import result_window
from ending_policy import safe_ending_gesture
class ComposerTest(unittest.TestCase):
 def test_default_and_explicit_backend(self):
  with patch.dict(os.environ,{},clear=True):self.assertEqual(choice(),'ace');self.assertEqual(worker_path().name,'ace_worker.py')
  with patch.dict(os.environ,{'ROADSCORE_COMPOSER':'sa3'}):self.assertEqual(worker_path().name,'worker.py')
  with patch.dict(os.environ,{'ROADSCORE_COMPOSER':'unexpected'}):
   with self.assertRaises(ValueError):choice()
 def test_native_pcm_retains_only_overlap_plus_new_material(self):
  rate=48000;meta={'new_audio_start_frame':12*rate,'overlap_frames':2*rate,'sample_rate':rate}
  start,end=result_window(meta,40*rate,rate,27*rate)
  self.assertEqual((start,end),(10*rate,40*rate));self.assertEqual((end-start)/rate-2,28)
 def test_guarded_continuation_uses_actual_committed_length(self):
  rate=48000;meta={'new_audio_start_frame':8*rate,'overlap_frames':2*rate,'sample_rate':rate}
  for duration in [36,32]:
   start,end=result_window(meta,duration*rate,rate,27*rate)
   self.assertEqual(start,6*rate);self.assertEqual(end,duration*rate);self.assertEqual((end-start)/rate-2,duration-8)
 def test_legacy_pcm_boundaries_unchanged(self):
  self.assertEqual(result_window({'retained_seconds':4.2},2000000,48000,1300000),(105600,1300000))
 def test_bad_frame_metadata_rejected(self):
  for meta in [{'sample_rate':44100,'new_audio_start_frame':100,'overlap_frames':10},{'sample_rate':48000,'new_audio_start_frame':1,'overlap_frames':10}]:
   with self.assertRaises(ValueError):result_window(meta,1000,48000,1000)
 def test_weak_tone_never_uses_inferred_chord(self):
  source=np.zeros((48000*4,2),np.float32)
  with patch('ending_policy.ending_gesture',side_effect=AssertionError('must not infer chord')):
   wave,info=safe_ending_gesture(source)
  self.assertEqual(len(wave),240000);self.assertIn('no guessed tonic',info['cadence_policy']);self.assertTrue(np.isfinite(wave).all())
if __name__=='__main__':unittest.main()
