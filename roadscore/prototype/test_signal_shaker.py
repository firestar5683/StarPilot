import unittest
import numpy as np
from signal_shaker import SignalShaker,ShakerGrid,profile_tempo_prior
from core_apex import CoreApex
GRID=ShakerGrid(128,.125,.8,.9,True,'synthetic test grid')
class ShakerTests(unittest.TestCase):
 def test_profile_prior_is_not_a_route_or_global128_override(self):
  self.assertEqual(profile_tempo_prior({'style':'116 BPM A minor'}),116.)
  self.assertEqual(profile_tempo_prior({'style':'128 BPM Prism'}),128.)
  self.assertIsNone(profile_tempo_prior({'style':'unknown'}))
 def test_uncertain_and_disabled_are_exact_bypass(self):
  x=np.ones((4800,2),np.float32)*.2
  for g,e in [(GRID,False),(ShakerGrid(85.7,0,.6,.1,False,'ambiguous'),True)]:
   self.assertIs(SignalShaker(g,enabled=e).process(x,0,True,True),x)
 def test_one_sequence_blinks_do_not_restart_and_pulses_grid_aligned(self):
  shaker=SignalShaker(GRID,enabled=True);zero=np.zeros((4800,2),np.float32)
  for i in range(100):shaker.process(zero,i*4800,i%10<5,True)
  self.assertEqual(len(shaker.sequence_starts),1)
  self.assertEqual(len(shaker.pulse_frames),32)
  for frame in shaker.pulse_frames:
   tick=(frame-shaker.origin)/shaker.step
   self.assertLess(abs(tick-round(tick)),1/shaker.step)
 def test_signal_staleness_releases_and_natural_tail_ends(self):
  s=SignalShaker(GRID,enabled=True);x=np.zeros((4800,2),np.float32)
  s.process(x,0,True,True);s.process(x,4800,True,True)
  for i in range(2,8):y=s.process(x,i*4800,True,False)
  np.testing.assert_array_equal(y,x);self.assertFalse(s.active)
 def test_no_input_mutation_and_bounded_overlay(self):
  s=SignalShaker(GRID,enabled=True);x=np.ones((4800,2),np.float32)*.2;before=x.copy()
  for i in range(20):
   y=s.process(x,i*4800,True,True);self.assertLessEqual(abs(y-x).max(),.012001)
  np.testing.assert_array_equal(x,before)
 def test_new_sequence_after_quiet_gap(self):
  s=SignalShaker(GRID,enabled=True);x=np.zeros((4800,2),np.float32)
  for i in range(50):s.process(x,i*4800,i<5 or i>=35,True)
  self.assertEqual(len(s.sequence_starts),2)
 def test_apex_uses_source_only_and_density_limit(self):
  c=CoreApex(GRID,enabled=True);x=np.ones((4800,2),np.float32)*.3;before=x.copy()
  for i in range(600):
   state={'kind':'curve','phase':'anticipation','lead':.5,'activation':i//10}
   y=c.process(x,i*4800,state);self.assertTrue(np.all(y<=x));self.assertTrue(np.all(y>=x*10**(-1/20)-1e-6))
  self.assertLessEqual(len(c.events),3);np.testing.assert_array_equal(x,before)
if __name__=='__main__':unittest.main()
