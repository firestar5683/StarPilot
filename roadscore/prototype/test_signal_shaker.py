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
 def test_audible_flag_expires_after_budget_despite_active_sequence(self):
  s=SignalShaker(GRID,enabled=True);x=np.zeros((4800,2),np.float32);heard=False
  for i in range(100):
   s.process(x,i*4800,True,True);heard |= s.snapshot()['rendered_active']
  self.assertTrue(heard);self.assertTrue(s.active);self.assertFalse(s.snapshot()['rendered_active'])
  self.assertEqual(s.snapshot()['rendered_block_end_seconds'],10.)
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
 def test_deliberate_opposite_direction_restarts_once_not_each_callback(self):
  s=SignalShaker(GRID,enabled=True,peak=.055);x=np.zeros((4800,2),np.float32)
  for i in range(140):
   direction='left' if i<90 else 'right'
   s.process(x,i*4800,True,True,sequence_key=direction)
  self.assertEqual(len(s.sequence_starts),2)
  self.assertEqual([e['direction'] for e in s.events if e['kind']=='sequence_start'],['left','right'])
  self.assertGreater(len(s.pulse_frames),32)
  self.assertEqual(s.snapshot()['remaining_pulses'],32-s.sequence_pulses)
 def test_rapid_direction_changes_do_not_restart_and_stale_input_stays_silent(self):
  s=SignalShaker(GRID,enabled=True);x=np.zeros((4800,2),np.float32)
  for i in range(18):s.process(x,i*4800,True,True,sequence_key='left' if i%2 else 'right')
  self.assertEqual(len(s.sequence_starts),1)
  for i in range(18,28):s.process(x,i*4800,True,False,sequence_key='left' if i%2 else 'right')
  self.assertFalse(s.rendered_active);self.assertFalse(s.active)
  self.assertEqual(s.snapshot()['suppression_reason'],'stale signal source')
 def test_stronger_cue_scales_and_respects_final_output_headroom(self):
  old=SignalShaker(GRID,enabled=True,peak=.018);new=SignalShaker(GRID,enabled=True,peak=.055)
  x=np.zeros((48000,2),np.float32)
  before=old.process(x,0,True,True);after=new.process(x,0,True,True)
  np.testing.assert_allclose(after,before*(.055/.018),atol=1e-8)
  contained=SignalShaker(GRID,enabled=True,peak=.055).process(x,0,True,True,presentation_gain=.45)
  np.testing.assert_allclose(contained,after*.45,atol=1e-8)
  for value in (.99,-.99):
   y=SignalShaker(GRID,enabled=True,peak=.055).process(np.full_like(x,value),0,True,True)
   self.assertLessEqual(float(abs(y).max()),1.)
  s=SignalShaker(GRID,enabled=True)
  for i in range(100):s.process(x[:4800],i*4800,True,True)
  self.assertEqual(s.snapshot()['suppression_reason'],'sequence budget exhausted')

 def test_accented_signal_is_directional_and_first_bar_is_strongest(self):
  x=np.zeros((4800,2),np.float32)
  samples=[];s=SignalShaker(GRID,enabled=True,peak=.14,accented=True)
  for i in range(90):samples.append(s.process(x,i*4800,True,True,sequence_key='left'))
  y=np.concatenate(samples)
  self.assertAlmostEqual(float(abs(y).max()),.14,places=6)
  np.testing.assert_allclose(y[:,1],y[:,0]*.65,atol=1e-8)
  first=s.pulse_frames[0];n=len(s.grain)
  later=s.pulse_frames[8]
  np.testing.assert_allclose(y[later:later+n],y[first:first+n]*.65,atol=1e-8)
  self.assertEqual(len(s.sequence_starts),1)
  self.assertEqual(len(s.pulse_frames),32)

 def test_accented_signal_keeps_unknown_phase_and_headroom_guards(self):
  unknown=ShakerGrid(128,0,.8,0,True,'unverified phase')
  x=np.full((48000,2),.98,np.float32)
  self.assertIs(SignalShaker(unknown,enabled=True,peak=.14,accented=True).process(x,0,True,True),x)
  s=SignalShaker(GRID,enabled=True,peak=9,accented=True)
  y=s.process(x,0,True,True,sequence_key='right')
  self.assertEqual(s.peak,.16);self.assertLessEqual(float(y.max()),1.)
  np.testing.assert_array_equal(x,np.full_like(x,.98))

 def test_silenced_priority_is_reported_and_does_not_restart_sequence(self):
  s=SignalShaker(GRID,enabled=True,peak=.14,accented=True)
  x=np.zeros((4800,2),np.float32)
  for i in range(40):
   np.testing.assert_array_equal(s.process(x,i*4800,True,True,sequence_key='left',presentation_gain=0),x)
  self.assertEqual(s.snapshot()['suppression_reason'],'presentation priority')
  self.assertEqual(len(s.sequence_starts),1)
  self.assertGreater(s.sequence_pulses,0)

if __name__=='__main__':unittest.main()
