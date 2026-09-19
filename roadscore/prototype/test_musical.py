import unittest
import numpy as np
from musical import Arrival,MusicalDSP,ending_gesture,match_continuation
class TestMusical(unittest.TestCase):
 def test_arrival_requires_stop_after_approach(self):
  a=Arrival();nav={'type':'arrive','remaining':20}
  for t in range(10):self.assertIsNone(a.update(t,1.5,nav,True))
  for t in [10,11]:self.assertIsNone(a.update(t,0,{},False))
  self.assertEqual(a.update(12,0,{},False),12)
 def test_new_route_abandons_arrival(self):
  a=Arrival();a.update(0,1,{'type':'arrive','remaining':20},True);a.route_change(True)
  for t in range(1,8):self.assertIsNone(a.update(t,0,{},False))
 def test_expired_context_does_not_end(self):
  a=Arrival();a.update(0,1,{'type':'arrive','remaining':20},True)
  for t in range(31,36):self.assertIsNone(a.update(t,0,{},False))
 def test_reverse_only_ends_with_destination_and_persistence(self):
  a=Arrival()
  for t in range(3):self.assertIsNone(a.update(t,1,{},False,gear='reverse',brake=True))
  nav={'type':'arrive','remaining':20}
  self.assertIsNone(a.update(4,1,nav,True,gear='reverse',brake=True))
  self.assertIsNone(a.update(4.7,1,{},False,gear='reverse',brake=True))
  self.assertIsNone(a.update(4.85,1,{'valid':True},True,gear='reverse',brake=True))
  self.assertEqual(a.update(4.9,1,{'valid':False},False,gear='reverse',brake=True),4.9)
 def test_reverse_context_reset(self):
  a=Arrival();a.update(0,1,{'type':'arrive','remaining':20},True,gear='reverse',brake=True);a.route_change(True)
  self.assertIsNone(a.update(1,1,{},False,gear='reverse',brake=True))
 def test_same_context_level_match(self):
  x=np.random.default_rng(0).normal(0,.1,(96000,2)).astype('float32');y,meta=match_continuation(x,x*.8)
  self.assertTrue(np.allclose(x,y,atol=1e-6));self.assertAlmostEqual(meta['gain'],1.25,places=4)
 def test_musical_output_and_ring(self):
  sr=48000;t=np.arange(sr*12)/sr;x=np.repeat((.1*np.sin(2*np.pi*261.626*t))[:,None],2,axis=1).astype('float32')
  d=MusicalDSP();y=d.process(x[:4800],1);self.assertTrue(np.isfinite(y).all())
  ring,info=ending_gesture(x);self.assertEqual(len(ring),sr*5);self.assertLess(abs(ring[-1]).max(),1e-5);self.assertTrue(np.isfinite(ring).all())
if __name__=='__main__':unittest.main()
