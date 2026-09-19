import unittest
import numpy as np
from quality_gate import HOOK_POLICY,POLICY,inspect,leading_seam_gap,QualifiedGenerator,reroll_seed

class HookSeamTests(unittest.TestCase):
 def tone(self):
  t=np.arange(36*48000)/48000
  return np.repeat((.1*np.sin(2*np.pi*220*t))[:,None],2,axis=1)
 def test_leading_gap_rejected_only_by_hook_gate(self):
  wave=self.tone();wave[8*48000:round(9.5*48000)]=0
  self.assertTrue(inspect(wave,48000,8,policy=POLICY)['accepted'])
  result=inspect(wave,48000,8,policy=HOOK_POLICY)
  self.assertFalse(result['accepted']);self.assertIn('leading_continuation_gap',result['reasons'])
  self.assertTrue(inspect(wave,48000,8,role='outro',policy=HOOK_POLICY)['accepted'])
 def test_intentional_interior_break_and_sparse_opening_preserved(self):
  wave=self.tone();wave[15*48000:round(16.5*48000)]=0
  self.assertTrue(inspect(wave,48000,8,policy=HOOK_POLICY)['accepted'])
  wave=self.tone();wave[8*48000:15*48000]*=.1
  self.assertTrue(inspect(wave,48000,8,policy=HOOK_POLICY)['accepted'])
 def test_recorded_user_review_cases(self):
  first=dict(role='verse',prefix_seconds=8,leading_quiet_seconds=1.5,source_energy_rms=.0480834596,new_energy_rms_p80=.0811132708,quiet_threshold=.0015026081)
  third=dict(role='verse',prefix_seconds=8,leading_quiet_seconds=0,source_energy_rms=.1008403855,new_energy_rms_p80=.1471485812,quiet_threshold=.003)
  self.assertTrue(leading_seam_gap(first,HOOK_POLICY));self.assertFalse(leading_seam_gap(first,POLICY));self.assertFalse(leading_seam_gap(third,HOOK_POLICY))
  for changes in ({'prefix_seconds':0},{'role':'outro'},{'source_energy_rms':.0001},{'leading_quiet_seconds':.9}):
   self.assertFalse(leading_seam_gap({**first,**changes},HOOK_POLICY))
 def test_existing_deterministic_bounded_retry_keeps_parent(self):
  calls=[];prior=np.zeros((1,700,64));wave=self.tone();bad=wave.copy();bad[8*48000:round(9.5*48000)]=0
  def generate(role,seed,previous):
   self.assertIs(previous,prior);calls.append((role,seed))
   return (bad if len(calls)==1 else wave),np.zeros((1,900,64)),dict(prefix_seconds=8,cold=False)
  _,_,result=QualifiedGenerator(generate,policy=HOOK_POLICY).run('verse',123,prior)
  self.assertEqual(calls,[('verse',123),('verse',reroll_seed(123,1))]);self.assertTrue(result['quality_accepted']);self.assertEqual(result['rerolls'],1)

if __name__=='__main__':unittest.main()
