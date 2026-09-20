import unittest

import numpy as np

from curve_build_drop import CurveBuildDrop
from signal_shaker import ShakerGrid

GRID=ShakerGrid(120.,0.,.9,.9,True,'test grid')


class BuildDropTests(unittest.TestCase):
  def test_disabled_uncertain_and_blocked_are_bit_exact(self):
    x=np.random.default_rng(2).normal(0,.1,(4800,2)).astype(np.float32)
    unknown=ShakerGrid(120.,0.,0.,0.,False,'uncertain')
    for enabled,fresh,blocked,grid in ((False,True,False,GRID),(True,False,False,GRID),
                                       (True,True,True,GRID),(True,True,False,unknown)):
      before=x.copy();fx=CurveBuildDrop()
      y=fx.process(x,0,grid,0,48000,enabled=enabled,source_fresh=fresh,blocked=blocked)
      self.assertIs(y,x);np.testing.assert_array_equal(x,before)

  def test_grid_aligned_crescendo_and_exact_cut_payoff(self):
    fx=CurveBuildDrop(low_boost_db=0);x=np.full((4*48000,2),.2,np.float32)
    y=fx.process(x,0,GRID,0,3*48000,enabled=True)
    self.assertEqual(y.shape,x.shape);self.assertTrue(np.isfinite(y).all())
    self.assertTrue(np.all(y[round(2.89*48000):3*48000]==0))
    self.assertGreater(y[3*48000,0],0)
    np.testing.assert_array_equal(y[3*48000+480:],x[3*48000+480:])
    self.assertEqual(fx.snapshot()['actual_payoff_frame'],3*48000)
    self.assertEqual(fx.snapshot()['added_delay_samples'],0)
    for frame in fx.pulse_frames:
      self.assertEqual(frame%6000,0)
    self.assertGreater(max(abs(y[:2*48000]-x[:2*48000]).ravel()),.02)
    # The final mute and return use 480-sample ramps, not a discontinuity.
    smooth=CurveBuildDrop(low_boost_db=0);smooth.grain.fill(0)
    ramped=smooth.process(x,0,GRID,0,3*48000,enabled=True)
    self.assertLess(np.max(abs(np.diff(ramped[round(2.88*48000):round(3.02*48000),0]))),.001)

  def test_cancellation_during_cut_restores_core_without_hanging_mute(self):
    for cancel in ({'source_fresh':False},{'blocked':True},{'enabled':False}):
      fx=CurveBuildDrop(low_boost_db=0)
      fx.process(np.full((round(2.95*48000),2),.2,np.float32),0,GRID,0,3*48000,enabled=True)
      x=np.full((4800,2),.2,np.float32)
      y=fx.process(x,round(2.95*48000),GRID,0,3*48000,**({'enabled':True}|cancel))
      self.assertGreater(y[0,0],0);self.assertLess(y[0,0],.001)
      self.assertLess(np.max(abs(np.diff(y[:,0]))),.001)
      np.testing.assert_array_equal(y[round(.031*48000):],x[round(.031*48000):])
      self.assertIsNone(fx.snapshot()['actual_payoff_frame'])
      self.assertEqual(fx.strength,0.)

  def test_headroom_and_source_ownership(self):
    fx=CurveBuildDrop();t=np.arange(4*48000)/48000
    x=(.97*np.sin(2*np.pi*80*t))[:,None]*np.ones((1,2),np.float32);x=x.astype(np.float32)
    before=x.copy();y=fx.process(x,0,GRID,0,3*48000,enabled=True)
    self.assertLessEqual(float(abs(y).max()),1.)
    np.testing.assert_array_equal(x,before)

  def test_irregular_callback_blocks_match_whole_render(self):
    x=np.random.default_rng(7).normal(0,.1,(4*48000,2)).astype(np.float32)
    whole=CurveBuildDrop().process(x,0,GRID,0,3*48000,enabled=True)
    fx=CurveBuildDrop();blocks=[];start=0;sizes=[37,800,13,9701,4800]
    while start<len(x):
      n=min(sizes[len(blocks)%len(sizes)],len(x)-start)
      blocks.append(fx.process(x[start:start+n],start,GRID,0,3*48000,enabled=True));start+=n
    np.testing.assert_allclose(np.concatenate(blocks),whole,atol=3e-7)


if __name__=='__main__':unittest.main()
