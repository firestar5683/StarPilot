import unittest
from presentation_status import export_status

class ExportStatusTests(unittest.TestCase):
 def test_actual_cue_state_and_audio_clock_survive_pcm_export(self):
  state={'elapsed':7.5,'render_mode':'gold-core','presentation_policy':'conservative-v1',
   'signal_shaker':{'sequence_active':True,'rendered_active':False,'block_end_seconds':7.4},
   'core_apex':{'rendered_active':True,'block_end_seconds':7.4},
   'engagement_presentation':{'enabled':True,'rendered_state':'transition','rendered_open_mix':.6}}
  actual=export_status(state)
  for key,value in state.items():self.assertEqual(actual[key],value)
  self.assertFalse(actual['signal_shaker']['rendered_active'])
 def test_missing_cues_are_not_invented(self):
  state=export_status({'gesture_active':None,'route':'private'})
  self.assertIsNone(state['signal_shaker'])
  self.assertNotIn('route',state)
if __name__=='__main__':unittest.main()
