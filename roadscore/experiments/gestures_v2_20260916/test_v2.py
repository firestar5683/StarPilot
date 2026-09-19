import unittest,sys
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parents[1]/'prototype'))
from musical_gestures_v2 import MusicalGestures
class GesturesV2Test(unittest.TestCase):
 def make(self):return MusicalGestures(np.random.default_rng(1).normal(0,.03,(96000,2)).astype(np.float32),48000,120)
 def test_signal_has_on_sparse_sustain_and_release(self):
  g=self.make()
  for frame in range(0,48000*12,4800):
   g.update(frame,left=True,input_ns=frame);g.render(np.zeros((4800,2),np.float32))
  started=[e for e in g.events if e['type']=='started'];self.assertEqual(sum(e['kind']=='turn_signal' for e in started),1)
  self.assertLessEqual(sum(e['kind']=='turn_signal_sustain' for e in started),6)
  g.update(g.frames,left=False,input_ns=g.frames)
  self.assertFalse(any(e.get('tag')=='signal' for e in g.queue));self.assertEqual(sum(e['kind']=='turn_signal_off' for e in g.queue),1)
  for _ in range(20):g.render(np.zeros((4800,2),np.float32))
  self.assertFalse(g.voices);self.assertFalse(g.signal)
 def test_arrival_does_not_add_release(self):
  g=self.make();g.update(0,left=True);g.render(np.zeros((4800,2),np.float32));g.update(g.frames,arrived=True)
  self.assertFalse(g.queue)
 def test_causal_partition_and_neutral_identity(self):
  a=self.make();b=self.make();dry=np.full((48000,2),.02,np.float32)
  np.testing.assert_array_equal(a.render(dry),dry)
  a=self.make()
  for g in (a,b):g.update(0,left=True,input_ns=123)
  x=a.render(dry);y=np.concatenate([b.render(c) for c in np.split(dry,10)])
  self.assertEqual([e['actual_frame'] for e in a.events if e['type']=='started'],[e['actual_frame'] for e in b.events if e['type']=='started'])
  self.assertTrue(all(e['input_ns']==123 for e in a.events if e['type']=='started'))
 def test_resume_after_short_stop_and_speed_hysteresis(self):
  g=self.make();g.update(0,speed=12);g.update(48000,speed=2)
  self.assertFalse(any(e['kind']=='stop' for e in g.queue))
  g.update(96000,speed=0);g.update(240000,speed=12)
  self.assertEqual([e['kind'] for e in g.queue],['stop','resume'])
 def test_no_invented_pitch_and_distinct_bank(self):
  g=self.make()
  self.assertFalse(np.array_equal(g.bank.sounds['click'],g.bank.sounds['hat']))
  for kind in g.phrases:self.assertFalse(g.bank.phrase(kind)[1]['new_tonal_pitches'])
if __name__=='__main__':unittest.main()
