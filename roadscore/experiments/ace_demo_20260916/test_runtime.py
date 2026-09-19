import unittest,sys,os
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'prototype'));sys.path.insert(0,str(R/'experiments/ace_chestnut_20260916'))
from safe_extension import extend_tail
from quality_gate import inspect
from composition_policy import CompositionPolicy
from ace_profiles import selected
from link_health import LinkProbe,LinkUnhealthy
from gesture_bank_v3 import GestureBank as V3
from gesture_bank_v4 import GestureBank as V4
class RuntimeTests(unittest.TestCase):
 def test_extension_preserves_source_tail(self):
  rate=48000;t=np.arange(12*rate)/rate;source=np.column_stack([.1*np.sin(2*np.pi*220*t)]*2).astype(np.float32)
  extended,meta=extend_tail(source,rate)
  self.assertEqual(meta['new_seconds'],24);self.assertFalse(meta['fresh_generation']);np.testing.assert_array_equal(extended[-6*rate:],source[-6*rate:]);self.assertTrue(inspect(extended,rate,2)['accepted'])
 def test_hold_does_not_repeat_silent_outro(self):
  rate=48000;t=np.arange(20*rate)/rate;source=np.column_stack([.1*np.sin(2*np.pi*220*t)]*2).astype(np.float32);source[-10*rate:]=0
  w,m=extend_tail(source,rate);self.assertFalse(m['preserves_latest_context']);self.assertTrue(inspect(w,rate,2)['accepted'])
 def test_arrival_accounts_for_buffer(self):
  nav={'valid':True,'remaining':900,'eta':90};self.assertEqual(CompositionPolicy(True).choose(0,48000,nav,12,90),'closing');self.assertEqual(CompositionPolicy().choose(0,48000,nav,12,90),'base')
 def test_causal_section_grammar(self):
  c=CompositionPolicy(True);roles=[]
  for i in range(7):
   role=c.choose(0,48000,{},12,90);roles.append(role);c.generated({'id':i,'conditioning':role},i*28)
  self.assertEqual(roles,['verse','prechorus','chorus','verse','bridge','chorus','verse'])
 def test_profile_closed_set(self):
  prior=os.environ.get('ROADSCORE_ACE_PROFILE')
  try:
   for value in ['prism','aurora']:
    os.environ['ROADSCORE_ACE_PROFILE']=value;self.assertEqual(selected(),value)
   os.environ['ROADSCORE_ACE_PROFILE']='circuit'
   with self.assertRaises(ValueError):selected()
  finally:
   if prior is None:os.environ.pop('ROADSCORE_ACE_PROFILE',None)
   else:os.environ['ROADSCORE_ACE_PROFILE']=prior
 def test_timeout_containment_skips_driver_reset(self):
  class Device:
   def on_device_hang(self):raise AssertionError('driver reset hook must not run')
  d=Device();probe=LinkProbe(d,R/'results/ace_demo_20260916/test_link.jsonl');stages=[];probe.sample=lambda stage:stages.append(stage);probe.install_failure_hook(contain=True)
  with self.assertRaises(LinkUnhealthy):d.on_device_hang()
  self.assertEqual(stages,['before_driver_timeout_handler'])
 def test_v4_preserves_turns(self):
  rng=np.random.default_rng(1);source=rng.normal(0,.08,(48000*8,2)).astype(np.float32);a=V3(source);b=V4(source)
  for kind in ['turn_signal','turn_signal_sustain','turn_signal_off']:np.testing.assert_array_equal(a.phrase(kind)[0],b.phrase(kind)[0])
  wave,meta=b.phrase('curve_apex');self.assertTrue(np.isfinite(wave).all());self.assertFalse(meta['new_tonal_pitches']);self.assertLess(abs(wave).max(),1.)
if __name__=='__main__':unittest.main()
