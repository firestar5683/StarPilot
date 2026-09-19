import unittest
import numpy as np
from event_music import EventDSP
from core import Conductor
from test_core import model
class Tests(unittest.TestCase):
 def test_handoff_preserves_original_by_default(self):
  c=Conductor();d=Conductor(handoff=True)
  for t in [0,.15,.35]:
   m=model(t,0);m['v']=np.linspace(20,0,33).tolist();c.update(t,m,20);d.update(t,m,20)
  for t in [.5,.7,.9]:c.update(t,model(t),20);d.update(t,model(t),20)
  self.assertEqual(c.kind,'slowdown');self.assertEqual(d.kind,'curve')
 def test_handoff_threshold_prefix_invariance(self):
  def run(future):
   c=Conductor(handoff=True,threshold=.6);out=[]
   for i in range(100):
    t=i*.05;out.append(c.update(t,model(t,.7 if t<=2 else future),20).copy())
   return out[:41]
  self.assertEqual(run(0),run(10))
 def test_styles_have_distinct_early_response_and_no_neutral_regression(self):
  rate=48000;t=np.arange(rate*2)/rate;a=np.stack([.2*np.sin(t*2*np.pi*110)+.06*np.sin(t*2*np.pi*1800)]*2,axis=1).astype(np.float32)
  outputs=[]
  for style in ['rock','electronic','synthwave','groove']:
   d=EventDSP(style=style);z=EventDSP(style=style);parts=[];refs=[]
   for i in range(20):
    x=a[i*4800:(i+1)*4800];d.event_state={'phase':'anticipation' if i>=5 else 'neutral','strength':1.5,'kind':'curve'}
    y=d.process(x,.25 if i>=5 else 0);ref=z.process(x,0)
    if i<5:self.assertTrue(np.allclose(y,ref))
    self.assertTrue(np.isfinite(y).all());self.assertLessEqual(abs(y).max(),.98);parts.append(y);refs.append(ref)
   y=np.concatenate(parts);ref=np.concatenate(refs);self.assertGreater(np.sqrt(np.mean((y[48000:]-ref[48000:])**2)),.003);outputs.append(y)
  for i in range(len(outputs)):
   for j in range(i):self.assertGreater(np.sqrt(np.mean((outputs[i]-outputs[j])**2)),.001)
if __name__=='__main__':unittest.main()
