import unittest
import numpy as np
from engagement_presentation import EngagementPresentation, PresentationConfig, engagement_active

ON = PresentationConfig(enabled=True)


class PresentationTests(unittest.TestCase):
  def test_disabled_exact_identity_no_mutation(self):
    x=np.random.default_rng(3).uniform(-.5,.5,(4800,2)).astype('float32');before=x.copy()
    y=EngagementPresentation().process(x,False,PresentationConfig())
    np.testing.assert_array_equal(y,before);np.testing.assert_array_equal(x,before)

  def test_frame_count_bounds_variable_blocks_rapid_toggles(self):
    dsp=EngagementPresentation();rng=np.random.default_rng(5)
    for i,n in enumerate([1,17,480,4800,9701,0]*10):
      x=rng.uniform(-.5,.5,(n,2)).astype('float32');before=x.copy()
      y=dsp.process(x,i%2==0,ON if i%3 else PresentationConfig())
      self.assertEqual(x.shape,y.shape);self.assertTrue(np.isfinite(y).all())
      self.assertLessEqual(np.max(np.abs(y),initial=0),.75)
      np.testing.assert_array_equal(x,before)

  def test_ramps_are_sample_smooth_and_reversible(self):
    dsp=EngagementPresentation();dsp.mix=0
    x=np.full((4800,2),.25,np.float32)
    dsp.process(x,False,ON)  # settle filter before measuring transition clicks
    outputs=[dsp.process(x,True,ON) for _ in range(4)]
    y=np.concatenate(outputs)
    self.assertLess(np.abs(np.diff(y[:,0])).max(),.002)
    self.assertEqual(dsp.mix,1.)
    np.testing.assert_array_equal(y[-4800:],x)
    dsp.process(x,False,ON);self.assertGreater(dsp.mix,0);self.assertLess(dsp.mix,1)
    dsp.process(x,True,ON);self.assertEqual(dsp.mix,1.)

  def test_attenuation_and_stereo_width(self):
    t=np.arange(48000)/48000
    def tone(freq):return np.column_stack([np.sin(t*2*np.pi*freq),-np.sin(t*2*np.pi*freq)]).astype('float32')*.4
    rms=[]
    for freq in [200,10000]:
      dsp=EngagementPresentation();dsp.mix=0
      x=tone(freq);y=dsp.process(x,False,ON)
      rms.append(np.sqrt(np.mean(y[4800:]**2))/np.sqrt(np.mean(x[4800:]**2)))
    self.assertAlmostEqual(rms[0],.85*.89125,places=2);self.assertLess(rms[1],.2)

  def test_split_block_continuity(self):
    x=np.random.default_rng(1).normal(0,.1,(16000,2)).astype('float32')
    a=EngagementPresentation();b=EngagementPresentation()
    whole=a.process(x,False,ON)
    split=np.concatenate([b.process(x[:123],False,ON),b.process(x[123:901],False,ON),b.process(x[901:],False,ON)])
    np.testing.assert_allclose(whole,split,atol=2e-7)

  def test_recorder_output_ownership(self):
    dsp=EngagementPresentation();x=np.ones((480,2),np.float32)*.1
    y=dsp.process(x,False,ON);saved=y.copy();dsp.process(-x,False,ON)
    np.testing.assert_array_equal(y,saved)

  def test_stale_invalid_future_engagement_contained(self):
    self.assertEqual(engagement_active(True,True,2_000_000_000,2_100_000_000,10.,10.1),(True,True))
    for valid,stamp,latest,wall in [(False,2e9,2.1e9,10.1),(True,2e9,4e9,10.1),(True,2e9,1e9,10.1),(True,2e9,2.1e9,12.)]:
      self.assertEqual(engagement_active(valid,True,stamp,latest,10.,wall),(False,False))
    self.assertEqual(engagement_active(True,False,2e9,2.1e9,10.,10.1),(False,True))

  def test_status_reports_applied_mix_not_requested_state(self):
    dsp=EngagementPresentation();x=np.ones((4800,2),np.float32)*.1
    dsp.process(x,False,ON);status=dsp.snapshot(ON,False,True)['engagement_presentation']
    self.assertEqual(status['rendered_state'],'transition');self.assertGreater(status['rendered_open_mix'],0)
    self.assertEqual(status['rendered_block_end_seconds'],.1)
    for _ in range(8):dsp.process(x,False,ON)
    self.assertEqual(dsp.snapshot(ON,False,True)['engagement_presentation']['rendered_state'],'contained')

  def test_configuration_fail_closed_and_clamps(self):
    self.assertFalse(PresentationConfig.read({'version':3,'enabled':True}).enabled)
    self.assertFalse(PresentationConfig.read({'enabled':'true'}).enabled)
    self.assertEqual(PresentationConfig.read({'attack_ms':0}).attack_ms,20)
    self.assertEqual(PresentationConfig.read({'release_ms':float('nan')}).release_ms,650)

if __name__=='__main__':unittest.main()
