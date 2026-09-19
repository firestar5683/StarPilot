import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ace_chestnut_20260916'))
from window_policy import retained_end
class EndpointTest(unittest.TestCase):
 def test_continuous_and_internal_breakdown(self):
  a=np.full((45000,2),.2);a[17000:19000]=.001
  self.assertEqual(retained_end(a,1000,8,36)[0],900)
 def test_terminal_fade_is_excluded_before_next_prefix(self):
  a=np.full((45000,2),.2);a[32000:]=.001
  end,info=retained_end(a,1000,8,36);self.assertEqual(end,800);self.assertTrue(info['endpoint_trimmed']);self.assertEqual((end-200)/25,24)
 def test_gain_relative_endpoint(self):
  a=np.full((45000,2),.2);a[32000:]=.001
  self.assertEqual(retained_end(a*.5,1000,8,36)[0],retained_end(a,1000,8,36)[0])
 def test_explicit_outro_may_resolve(self):
  a=np.full((45000,2),.2);a[32000:]=0
  self.assertEqual(retained_end(a,1000,8,36,allow_fade=True)[0],900)
 def test_unusable_silence_fails_instead_of_looping_it(self):
  with self.assertRaises(ValueError):retained_end(np.zeros((45000,2)),1000,8,36)
 def test_insufficient_new_material_fails(self):
  a=np.full((45000,2),.2);a[20000:]=0
  with self.assertRaises(ValueError):retained_end(a,1000,8,36)
if __name__=='__main__':unittest.main()
