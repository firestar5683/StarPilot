import unittest
import numpy as np
from alert_accent import AlertAccent
from signal_shaker import ShakerGrid, assess_grid

GRID=ShakerGrid(120,.125,.8,.9,True,'test')

class AccentTests(unittest.TestCase):
 def render(self, alerts, fresh=True, competing=False, grid=GRID):
  accent=AlertAccent(grid,rate=8000,enabled=True)
  source=np.full((800,2),.1,np.float32);heard=False
  for i,key in enumerate(alerts):
   wet=accent.process(source,i*800,key,bool(key),fresh,competing)
   heard |= bool(np.any(wet!=source))
   self.assertLessEqual(float(np.max(np.abs(wet-source))),.016001)
  return accent,heard
 def test_persistent_alert_once_and_grid_aligned(self):
  accent,heard=self.render(['takeover']*200)
  self.assertTrue(heard);self.assertEqual(len(accent.events),1)
  self.assertEqual(accent.events[0]['scheduled_frame'],5000)
 def test_tiny_changes_and_competing_cues_are_omitted(self):
  self.assertFalse(self.render(['a','b']*100)[1])
  self.assertFalse(self.render(['a']*100,competing=True)[1])
  self.assertFalse(self.render(['a']*100,fresh=False)[1])
 def test_density_limit(self):
  accent,_=self.render([str(i//30) for i in range(600)])
  self.assertLessEqual(len(accent.events),3)
 def test_ambiguous_grid_bypasses(self):
  grid=ShakerGrid(120,0,0,0,False,'uncertain')
  self.assertFalse(self.render(['a']*100,grid=grid)[1])
 def test_cancel_pending_on_stale_input(self):
  a=AlertAccent(GRID,rate=8000,enabled=True);x=np.full((800,2),.1,np.float32)
  for i in range(3):a.process(x,i*800,'a',True,True)
  self.assertTrue(a.pending)
  self.assertIs(a.process(x,2400,'a',True,False),x);self.assertFalse(a.pending)
 def test_short_opening_assessed_without_assuming_confidence(self):
  # Real estimator must accept a 23s opening; silence must still veto cues.
  grid,_=assess_grid(np.zeros((23*8000,2),np.float32),8000,128)
  self.assertNotEqual(grid.reason,'insufficient audio for grid')
  self.assertFalse(grid.usable)

if __name__=='__main__':unittest.main()
