import unittest
import numpy as np
from core_apex import CoreApex
from signal_shaker import ShakerGrid

class ApexEnvelopeTests(unittest.TestCase):
 def test_late_predictions_start_and_end_at_unity(self):
  rate=8000;start=rate*10
  grid=ShakerGrid(128,0,1,1,True,'test',True)
  for lead in [.25,.35,.5,1.]:
   with self.subTest(lead=lead):
    c=CoreApex(grid,rate,True,-3.)
    source=np.full((rate*2,2),.3,np.float32)
    result=c.process(source,start,{'kind':'curve','phase':'anticipation','activation':1,'lead':lead})
    self.assertEqual(result[0,0],source[0,0])
    np.testing.assert_array_equal(result[c.peak-start:],source[c.peak-start:])
    self.assertLess(float(result.min()),.3*.72)
    self.assertGreaterEqual(float(result.min()),.3*10**(-3/20)-1e-6)
    self.assertLess(float(np.max(np.abs(np.diff(result[:,0])))),.0002)
    np.testing.assert_array_equal(source,np.full_like(source,.3))
 def test_uncertain_grid_finishes_existing_breath_without_new_triggers(self):
  rate=8000;good=ShakerGrid(128,0,1,1,True,'test',True)
  c=CoreApex(good,rate,True,-3)
  state={'kind':'curve','phase':'anticipation','activation':1,'lead':.25}
  x=np.full((80,2),.3,np.float32)
  c.process(x,rate*10,state)
  c.grid=ShakerGrid(128,0,0,0,False,'uncertain')
  heard=False
  for i in range(1,100):
   result=c.process(x,rate*10+i*80,dict(state,activation=2))
   heard |= bool(np.any(result<x))
  self.assertTrue(heard)
  self.assertEqual(len(c.events),1)
  np.testing.assert_array_equal(result,x)
 def test_callback_partition_preserves_envelope(self):
  rate=8000;grid=ShakerGrid(128,0,1,1,True,'test',True)
  state={'kind':'curve','phase':'anticipation','activation':1,'lead':.25}
  source=np.full((rate,2),.3,np.float32)
  whole=CoreApex(grid,rate,True,-3).process(source,10*rate,state)
  c=CoreApex(grid,rate,True,-3)
  blocks=[c.process(source[i:i+80],10*rate+i,state) for i in range(0,rate,80)]
  np.testing.assert_array_equal(np.concatenate(blocks),whole)

if __name__=='__main__':unittest.main()
