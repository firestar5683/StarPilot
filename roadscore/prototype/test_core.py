import unittest
import numpy as np
from core import Conductor,DSP

def model(t,strength=1.5):
 times=np.linspace(0,10,33);lat=strength*np.exp(-((times-6)/1.5)**2)
 return {'mono':int((100+t)*1e9),'eof':int((100+t-.1)*1e9),'t':times.tolist(),'v':[20]*33,'yaw':(lat/20).tolist()}
class Tests(unittest.TestCase):
 def test_persistence(self):
  c=Conductor();self.assertEqual(c.update(0,model(0),20)['phase'],'neutral')
  for t in [.1,.2,.31]:s=c.update(t,model(t),20)
  self.assertEqual(s['phase'],'anticipation');self.assertGreater(s['lead'],2)
 def test_low_speed_and_stale(self):
  for speed in [0,2]:
   c=Conductor()
   for t in [0,.2,.4]:self.assertEqual(c.update(t,model(t),speed)['phase'],'neutral')
  c=Conductor();m=model(1);m['eof']-=int(1e9)
  self.assertEqual(c.update(1,m,20)['phase'],'neutral')
 def test_prefix_invariance(self):
  def run(future):
   c=Conductor();out=[]
   for i in range(100):
    t=i*.05;out.append(c.update(t,model(t,1.5 if t<=2 else future),20).copy())
   return out[:41]
  self.assertEqual(run(0),run(100))
 def test_slowdown(self):
  c=Conductor()
  for t in [0,.15,.35]:
   m=model(t,0);m['v']=np.linspace(20,0,33).tolist();s=c.update(t,m,20)
  self.assertEqual(s['kind'],'slowdown');self.assertEqual(s['phase'],'anticipation')
 def test_release(self):
  c=Conductor()
  for t in [0,.15,.35]:c.update(t,model(t),20)
  self.assertEqual(c.state(20)['phase'],'neutral')
 def test_dsp_finite_audible_difference(self):
  a=np.random.default_rng(3).normal(0,.15,(48000,2)).astype(np.float32)
  x=DSP().process(a,0);y=DSP().process(a,1)
  self.assertTrue(np.isfinite(y).all());self.assertLess(np.abs(y).max(),1)
  self.assertGreater(np.sqrt(((x-y)**2).mean()),.02)
if __name__=='__main__':unittest.main()
