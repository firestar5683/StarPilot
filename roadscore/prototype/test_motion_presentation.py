import unittest
import numpy as np
from motion_presentation import MotionPresentation
from engagement_presentation import EngagementPresentation,PresentationConfig


class MotionTests(unittest.TestCase):
  def setUp(self):
    self.rate=48000;t=np.arange(4800)/self.rate
    self.pcm=np.column_stack([.15*np.sin(2*np.pi*6000*t)]*2).astype('float32')

  def run_blocks(self,dsp,n=12,**kw):
    for _ in range(n):out=dsp.process(self.pcm,**kw)
    return out

  def test_disabled_unity_and_stopped_strong_lift(self):
    dsp=MotionPresentation(enabled=False);original=self.pcm.copy()
    self.assertTrue(np.array_equal(self.run_blocks(dsp,speed=0.,source_fresh=True),self.pcm))
    dsp.enabled=True;contained=self.run_blocks(dsp,speed=0.,source_fresh=True)
    self.assertLess(np.std(contained)/np.std(self.pcm),.05)
    lifted=self.run_blocks(dsp,speed=1.,source_fresh=True)
    self.assertTrue(np.array_equal(lifted,self.pcm));self.assertTrue(np.array_equal(original,self.pcm))

  def test_hysteresis_dwell_and_stale_input(self):
    dsp=MotionPresentation(enabled=True)
    self.run_blocks(dsp,3,speed=0.,source_fresh=True);self.assertFalse(dsp.stopped)
    self.run_blocks(dsp,1,speed=0.,source_fresh=True);self.assertTrue(dsp.stopped)
    for speed in (.3,.7,.4,.6):self.run_blocks(dsp,2,speed=speed,source_fresh=True);self.assertTrue(dsp.stopped)
    self.run_blocks(dsp,1,speed=1.,source_fresh=True);self.assertTrue(dsp.stopped)
    self.run_blocks(dsp,1,speed=1.,source_fresh=True);self.assertFalse(dsp.stopped)
    self.run_blocks(dsp,speed=0.,source_fresh=True)
    y=self.run_blocks(dsp,speed=float('nan'),source_fresh=False)
    self.assertTrue(np.array_equal(y,self.pcm));self.assertFalse(dsp.stopped)

  def test_engagement_owns_inactive_presentation(self):
    dsp=MotionPresentation(enabled=True);eng=EngagementPresentation();config=PresentationConfig(enabled=True)
    y=self.run_blocks(dsp,speed=0.,source_fresh=True,engagement_open_mix=0.)
    self.assertLess(np.std(y),np.std(self.pcm)*.05)
    y=self.run_blocks(dsp,speed=1.,source_fresh=True,engagement_open_mix=0.)
    self.assertTrue(np.array_equal(y,self.pcm))
    # Moving bypass cannot undo the existing engagement lowpass.
    for _ in range(10):out=eng.process(y,False,config)
    self.assertLess(np.std(out),np.std(y)*.7)

  def test_ramps_have_no_step_on_dc_and_disable_releases(self):
    dsp=MotionPresentation(enabled=True);x=np.full((4800,2),.1,np.float32)
    blocks=[]
    for i in range(35):blocks.append(dsp.process(x,speed=0. if i<18 else 1.,source_fresh=True))
    self.assertLess(np.max(np.abs(np.diff(np.concatenate(blocks)[:,0]))),.0001)
    self.run_blocks(dsp,speed=0.,source_fresh=True);dsp.enabled=False
    self.assertTrue(np.array_equal(self.run_blocks(dsp,speed=0.,source_fresh=True),self.pcm))

if __name__=='__main__':unittest.main()
