import unittest
import numpy as np
from curve_reaction import CurveReaction
from signal_shaker import ShakerGrid
GRID=ShakerGrid(128,0,.8,.9,True,'test')

class CurveTests(unittest.TestCase):
 def setUp(self):
  t=np.arange(4800)/48000;self.pcm=np.column_stack([.1*np.sin(2*np.pi*6000*t)]*2).astype('float32')
  self.state=dict(kind='curve',phase='anticipation',activation=1.,amount=.9)
 def test_build_then_quantized_payoff_preserves_source(self):
  dsp=CurveReaction(GRID,enabled=True);original=self.pcm.copy()
  for i in range(15):y=dsp.process(self.pcm,i*4800,self.state)
  self.assertLess(np.std(y),np.std(self.pcm)*.4)
  state={**self.state,'phase':'event'}
  dsp.process(self.pcm,72000,state)
  self.assertGreaterEqual(dsp.payoff,72000);self.assertLessEqual(dsp.payoff-72000,48000*60/128/2)
  for i in range(16,23):y=dsp.process(self.pcm,i*4800,state)
  self.assertTrue(np.array_equal(y,self.pcm));self.assertTrue(np.array_equal(original,self.pcm))
 def test_bypass_stale_and_priority(self):
  dsp=CurveReaction(GRID,enabled=False)
  self.assertIs(dsp.process(self.pcm,0,self.state),self.pcm)
  dsp.enabled=True
  for i in range(10):dsp.process(self.pcm,i*4800,self.state)
  for i in range(10,15):y=dsp.process(self.pcm,i*4800,self.state,blocked=True)
  self.assertTrue(np.array_equal(y,self.pcm))
  for i in range(15,20):y=dsp.process(self.pcm,i*4800,self.state,source_fresh=False)
  self.assertTrue(np.array_equal(y,self.pcm))
 def test_uncertain_grid_has_filter_release_without_added_notes(self):
  grid=ShakerGrid(128,0,0,0,False,'uncertain');dsp=CurveReaction(grid,enabled=True)
  silence=np.zeros_like(self.pcm)
  for i in range(10):self.assertFalse(np.any(dsp.process(silence,i*4800,self.state)))
  dsp.process(silence,48000,{**self.state,'phase':'event'})
  self.assertEqual(dsp.payoff,48000)

if __name__=='__main__':unittest.main()
