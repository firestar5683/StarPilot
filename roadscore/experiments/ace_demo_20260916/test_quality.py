import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ace_chestnut_20260916'))
from quality_gate import inspect,QualifiedGenerator
class QualityTests(unittest.TestCase):
 def tone(self,seconds=36,level=.1):
  t=np.arange(round(seconds*48000))/48000;return np.repeat((level*np.sin(2*np.pi*220*t))[:,None],2,axis=1)
 def test_long_gap_and_short_rest(self):
  a=self.tone();a[12*48000:15*48000]=.0007;self.assertFalse(inspect(a,48000,8)['accepted']);a=self.tone();a[12*48000:13*48000]=0;self.assertTrue(inspect(a,48000,8)['accepted'])
 def test_uniform_sparse_and_soft_intro(self):
  a=self.tone(level=.003);self.assertTrue(inspect(a,48000,8,role='prechorus')['accepted']);self.assertTrue(inspect(a,48000,0,role='initial')['accepted'])
 def test_outro_tail_allowed_but_silent_start_not(self):
  a=self.tone();a[20*48000:]=0;self.assertTrue(inspect(a,48000,8,role='outro')['accepted']);a=self.tone();a[8*48000:20*48000]=0;self.assertFalse(inspect(a,48000,8,role='outro')['accepted'])
 def test_quiet_preview_accounts_for_output_scale(self):
  a=self.tone(level=.8);t=np.arange(2*48000)/48000;a[12*48000:14*48000]=(.0055*np.sin(2*np.pi*440*t))[:,None]
  q=inspect(a,48000,8);self.assertFalse(q['accepted']);self.assertIn('multi_second_near_silence',q['reasons'])
 def test_only_committed_region(self):
  a=self.tone();a[:6*48000]=0;self.assertTrue(inspect(a,48000,8)['accepted'])
 def test_bounded_retry_and_deadline(self):
  clock=[0.];seeds=[]
  def generate(role,seed,prior):
   seeds.append(seed);clock[0]+=24;return np.zeros((36*48000,2)),np.zeros((1,900,64)),{'prefix_seconds':8,'cold':False}
  g=QualifiedGenerator(generate,clock=lambda:clock[0]);_,_,r=g.run('chorus',123,deadline=90);self.assertEqual(len(seeds),3);self.assertFalse(r['quality_accepted']);self.assertEqual(len(set(seeds)),3)
  clock[0]=0;seeds.clear();_,_,r=g.run('chorus',123,deadline=50);self.assertEqual(len(seeds),1);self.assertEqual(r['quality_stop_reason'],'insufficient_playback_buffer')
 def test_accept_first_viable_same_role(self):
  roles=[]
  def generate(role,seed,prior):
   roles.append(role);return self.tone() if len(roles)>1 else np.zeros((36*48000,2)),np.zeros((1,900,64)),{'prefix_seconds':8,'cold':False}
  _,_,r=QualifiedGenerator(generate).run('chorus',42);self.assertTrue(r['quality_accepted']);self.assertEqual(roles,['chorus','chorus']);self.assertEqual(r['rerolls'],1)
if __name__=='__main__':unittest.main()
