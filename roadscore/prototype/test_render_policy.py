import unittest
import numpy as np
from render_policy import render, ring_only, selected, validate

class Spy:
 def __init__(self, operation):self.operation=operation;self.calls=0
 def process(self, wave, amount, ending):
  self.calls+=1;return self.operation(wave)
 def render(self, wave):
  self.calls+=1;return self.operation(wave)

class TestRenderPolicy(unittest.TestCase):
 def test_gold_is_bit_exact_already_scaled_pcm_without_any_processing(self):
  raw=np.array([[-.81,.72],[.25,-.01],[0.,.94]],np.float32)*np.float32(.65)
  original=raw.copy()
  def forbidden(*args):raise AssertionError('Gold core invoked processing')
  dsp=Spy(forbidden);gesture=Spy(forbidden)
  actual=render('gold-core',raw,dsp,1.,0.,gesture,forbidden,('cadence',100,0,48000))
  self.assertIs(actual,raw)
  np.testing.assert_array_equal(actual,original)
  self.assertEqual((dsp.calls,gesture.calls),(0,0))

 def test_current_preserves_order_and_arguments(self):
  events=[];raw=np.ones((2,2),np.float32)
  class DSP:
   def process(self,wave,amount,ending):events.append(('dsp',amount,ending));return wave*2
  class Gestures:
   def render(self,wave):events.append('gesture');return wave+3
  def cadence(wave,*args):events.append(('cadence',args));return wave*5
  actual=render('current',raw,DSP(),.6,.4,Gestures(),cadence,(1,2,3,4))
  np.testing.assert_array_equal(actual,np.full((2,2),25))
  self.assertEqual(events,[('dsp',.6,.4),'gesture',('cadence',(1,2,3,4))])

 def test_gold_does_not_zero_source_after_arrival(self):
  for frames in (0,14400,480000):
   self.assertFalse(ring_only('gold-core',True,0,frames,48000))
  self.assertTrue(ring_only('current',True,0,14400,48000))
  self.assertFalse(ring_only('current',True,None,480000,48000))

 def test_opt_in_and_invalid_combinations(self):
  self.assertEqual(selected({}),'current')
  self.assertEqual(selected({'ROADSCORE_RENDER_MODE':'gold-core'}),'gold-core')
  validate('gold-core','ace')
  for args in [('gold-core','sa3'),('gold-core','ace',True),('unknown','ace')]:
   with self.assertRaises(ValueError):validate(*args)
  with self.assertRaises(ValueError):selected({'ROADSCORE_RENDER_MODE':'typo'})

if __name__=='__main__':unittest.main()
