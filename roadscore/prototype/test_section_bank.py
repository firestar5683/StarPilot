import unittest,threading
import numpy as np
from section_bank import SectionBank
class BankTest(unittest.TestCase):
 def make(self):
  b=SectionBank.__new__(SectionBank);b.rate=10;b.clips={'verse':(np.ones((20,2),np.float32),{}),'chorus':(np.full((20,2),2,np.float32),{})};b.pending={};b.section='verse';b.position=0;b.events=[];b.frames=0;b.scheduled=None;b.plan_tail=[];b.plan_key=None;b.plan_lock=threading.RLock();return b
 def test_exact_landing_inside_callback(self):
  b=self.make();b.schedule('chorus',7);out=b.render(10)
  np.testing.assert_array_equal(out[:7],1);np.testing.assert_array_equal(out[7:],2);self.assertEqual(b.events[0]['audio_s'],.7)
 def test_fresh_material_only_at_phrase_boundary(self):
  b=self.make();b.pending['verse']=(np.full((20,2),3,np.float32),{'job':42});out=b.render(25)
  np.testing.assert_array_equal(out[:20],1);np.testing.assert_array_equal(out[20:],3)
 def test_late_schedule_does_not_wait_forever(self):
  b=self.make();b.render(10);b.schedule('chorus',5);self.assertTrue((b.render(5)==2).all())

 def test_preparation_survives_control_tick_at_exact_block_boundary(self):
  b=self.make();b.clips['prechorus']=(np.full((20,2),3,np.float32),{})
  plan={'section':'chorus','at':2.,'requested':0.,'reason':'predicted curve'}
  prep={'section':'prechorus','at':1.}
  b.set_plan(plan,prep);np.testing.assert_array_equal(b.render(10),1)
  b.set_plan(plan,None) # Planner has advanced; audio has not consumed frame 10 yet.
  np.testing.assert_array_equal(b.render(10),3)
  np.testing.assert_array_equal(b.render(5),2)
  self.assertEqual([e['audio_s'] for e in b.events],[1.,2.])
 def test_arrival_replaces_pending_curve_plan(self):
  b=self.make();b.clips['outro']=(np.full((20,2),4,np.float32),{})
  b.set_plan({'section':'chorus','at':2.,'requested':0.,'reason':'predicted curve'})
  b.set_plan({'section':'outro','at':1.,'requested':.5,'reason':'arrival'})
  b.render(10);np.testing.assert_array_equal(b.render(20),4)
