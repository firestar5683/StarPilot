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
 def test_stale_or_blocked_payoff_cannot_show_apex(self):
  for kwargs in ({'blocked':True},{'source_fresh':False}):
   dsp=CurveReaction(GRID,enabled=True)
   for i in range(10):dsp.process(self.pcm,i*4800,self.state)
   event={**self.state,'phase':'event'}
   dsp.process(self.pcm,48000,event)
   dsp.process(self.pcm,52800,event,**kwargs)
   view=dsp.snapshot()['curve_reaction']
   self.assertEqual(view['rendered_phase'],'neutral');self.assertFalse(view['rendered_active'])
   self.assertIsNone(view['payoff_audio_s'])
   dsp.process(self.pcm,57600,event)
   self.assertEqual(dsp.snapshot()['curve_reaction']['rendered_phase'],'neutral')
 def test_missing_activation_and_unbuilt_event_never_claim_payoff(self):
  for activation in (None,float('nan'),True):
   dsp=CurveReaction(GRID,enabled=True)
   for i in range(5):y=dsp.process(self.pcm,i*4800,{**self.state,'activation':activation})
   self.assertTrue(np.array_equal(y,self.pcm))
   self.assertEqual(dsp.snapshot()['curve_reaction']['rendered_phase'],'neutral')
  dsp=CurveReaction(GRID,enabled=True)
  dsp.process(self.pcm,0,{**self.state,'phase':'event'})
  self.assertIsNone(dsp.payoff)
 def test_quantized_wait_processes_each_sample_once(self):
  dsp=CurveReaction(GRID,enabled=True)
  dsp.process(self.pcm,0,self.state)
  before=dsp.dsp.frames_processed
  # Next eighth is11250; this entire100ms block precedes that boundary.
  dsp.process(self.pcm,4800,{**self.state,'phase':'event'})
  self.assertEqual(dsp.dsp.frames_processed-before,len(self.pcm))
  self.assertGreater(dsp.payoff,9600)
 def test_uncertain_grid_has_filter_release_without_added_notes(self):
  grid=ShakerGrid(128,0,0,0,False,'uncertain');dsp=CurveReaction(grid,enabled=True)
  silence=np.zeros_like(self.pcm)
  for i in range(10):self.assertFalse(np.any(dsp.process(silence,i*4800,self.state)))
  dsp.process(silence,48000,{**self.state,'phase':'event'})
  self.assertEqual(dsp.payoff,48000)
 def test_bass_build_removes_low_end_then_restores_exact_song(self):
  rate=48000;t=np.arange(rate*5)/rate
  source=np.column_stack([.22*np.sin(2*np.pi*80*t)+.1*np.sin(2*np.pi*2000*t)]*2).astype('float32')
  original=source.copy();dsp=CurveReaction(GRID,enabled=True,bass_build=True);output=[]
  for start in range(0,len(source),4800):
   now=start/rate
   state={**self.state,'amount':min(1.,now/3),'phase':'anticipation' if now<3.5 else 'event','demo_staged_curve':True}
   output.append(dsp.process(source[start:start+4800],start,state))
  wave=np.concatenate(output)
  def magnitude(samples,hz):
   spectrum=np.abs(np.fft.rfft(samples[:,0]));return spectrum[round(hz*len(samples)/rate)]
  before=source[rate*3:rate*3+4800];build=wave[rate*3:rate*3+4800]
  self.assertLess(magnitude(build,80),magnitude(before,80)*.15)
  self.assertGreater(magnitude(build,2000),magnitude(before,2000)*.8)
  self.assertTrue(np.array_equal(wave[rate*4:],source[rate*4:]))
  self.assertTrue(np.array_equal(source,original));self.assertTrue(np.isfinite(wave).all())
  self.assertLess(np.abs(wave).max(),1.)
  self.assertEqual(dsp.snapshot()['curve_reaction']['source'],'known replay route event')


if __name__=='__main__':unittest.main()
