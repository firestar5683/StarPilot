import unittest
import numpy as np
from musical_gestures import MusicalGestures
class GestureTest(unittest.TestCase):
 def make(self):
  rate=48000;rng=np.random.default_rng(7);source=rng.normal(0,.03,(rate*4,2)).astype(np.float32)
  return MusicalGestures(source,rate,120)
 def test_signal_immediate_grid_and_cancellation(self):
  g=self.make();g.update(0,left=True,input_ns=10)
  e=g.events[0];self.assertEqual(e['scheduled_frame'],6000)
  g.render(np.ones((12000,2),np.float32)*.05)
  begun=[x for x in g.events if x['type']=='started'];self.assertEqual(begun[0]['actual_frame'],6000)
  g.update(12000,input_ns=20);self.assertFalse(g.signal);self.assertFalse(g.queue)
  g.render(np.zeros((4800,2),np.float32));self.assertFalse(g.voices)
 def test_chunk_partition_does_not_move_events(self):
  a=self.make();b=self.make()
  for g in (a,b):g.update(0,left=True,input_ns=10)
  a.render(np.zeros((24000,2),np.float32))
  for _ in range(5):b.render(np.zeros((4800,2),np.float32))
  self.assertEqual([e['actual_frame'] for e in a.events if e['type']=='started'],[e['actual_frame'] for e in b.events if e['type']=='started'])
 def test_curve_prediction_and_outro_suppression(self):
  g=self.make();road={'kind':'curve','phase':'anticipation','activation':10,'lead':6}
  g.update(0,road=road,input_ns=10)
  self.assertEqual([e['kind'] for e in g.queue],['curve_prepare','curve_apex'])
  self.assertTrue(all(e['input_ns']==10 for e in g.queue))
  g.update(4800,road=road,outro=True,input_ns=20)
  self.assertEqual([e['kind'] for e in g.queue],['arrival_prepare'])
 def test_neutral_has_no_output_change(self):
  g=self.make();x=np.ones((4800,2),np.float32)*.05
  np.testing.assert_array_equal(g.render(x),x)
 def test_no_new_tonal_pitches_claim(self):
  g=self.make()
  for k in g.phrases:self.assertFalse(g.bank.phrase(k)[1]['new_tonal_pitches'])

 def test_payoff_tracks_current_prediction_without_moving_started_audio(self):
  g=self.make();road={'kind':'curve','phase':'anticipation','activation':10,'lead':6}
  g.update(0,road=road,input_ns=10)
  g.update(48000,road={**road,'lead':7},input_ns=20)
  apex=next(e for e in g.queue if e['kind']=='curve_apex')
  self.assertEqual(apex['scheduled_frame'],48000*8)
  self.assertEqual(apex['input_ns'],20)
  self.assertTrue(any(e['type']=='cancelled' and e['reason']=='current forecast revised' for e in g.events))
