import unittest
import numpy as np
from phrase import pulse,cadence_runway,mix_cadence
class TestPhrase(unittest.TestCase):
 def test_known_pulse_and_bounded_landing(self):
  sr=8000;x=np.zeros(sr*16)
  rng=np.random.default_rng(1)
  for i in range(0,len(x),sr//2):x[i:i+160]=rng.normal(0,.2,160)*np.exp(-np.arange(160)/40)
  a=np.repeat(x[:,None],2,axis=1);p=pulse(a[:12*sr],sr)
  self.assertAlmostEqual(p['bpm'],120,delta=3)
  d,m=cadence_runway(a[:12*sr],a[12*sr:],sr);self.assertTrue(.8<=d<=3.5);self.assertEqual(m['method'],'pulse-grid plus local release')
 def test_weak_pulse_release(self):
  sr=8000;past=np.ones((sr*12,2))*.1;q=np.ones((sr*4,2))*.1;q[round(sr*1.7):round(sr*2.3)]=.01
  d,m=cadence_runway(past,q,sr);self.assertTrue(1.7<=d<=2.3);self.assertFalse(m['bar_detection'])
 def test_future_cadence_does_not_play_early(self):
  a=np.ones((100,2),dtype='float32')*.2;g=np.ones((500,2),dtype='float32')*.8
  self.assertTrue(np.array_equal(mix_cadence(a,g,0,200,100),a))
  y=mix_cadence(a,g,150,200,100);self.assertTrue(np.array_equal(y[:50],a[:50]));self.assertTrue(np.allclose(y[80:],.8))
 def test_no_future_audio(self):
  d,m=cadence_runway(np.zeros((48000,2)),np.zeros((100,2)));self.assertEqual(d,0)
if __name__=='__main__':unittest.main()
