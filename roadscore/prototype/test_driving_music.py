import unittest
import numpy as np
from driving_music import DrivingDSP
from musical import MusicalDSP
class TestDrivingMusic(unittest.TestCase):
 def test_neutral_preserves_base_and_build_adds_reprise(self):
  rng=np.random.default_rng(4);blocks=[]
  for i in range(30):
   x=np.zeros((4800,2),np.float32)
   if i%3==0:x[:480]=rng.normal(0,.1,(480,2))*np.exp(-np.arange(480)[:,None]/100)
   blocks.append(x)
  a=MusicalDSP(bpm=108);b=DrivingDSP(bpm=108)
  for x in blocks[:10]:self.assertTrue(np.allclose(a.process(x,0),b.process(x,0)))
  differences=[]
  for x in blocks[10:]:
   b.event_state={'phase':'anticipation','strength':2};y=b.process(x,.8);z=a.process(x,.8);differences.append(np.max(abs(y-z)));self.assertTrue(np.isfinite(y).all());self.assertLessEqual(np.max(abs(y)),.98)
  self.assertGreater(max(differences),.001)
if __name__=='__main__':unittest.main()
