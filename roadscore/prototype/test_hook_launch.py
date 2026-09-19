import unittest
from hook_launch import enabled
from prepared_session import verify
from session_seed import select_session

class LaunchTests(unittest.TestCase):
 def test_fresh_and_explicit_but_not_judging_or_replay(self):
  self.assertTrue(enabled(select_session(123),False,'ace'))
  self.assertTrue(enabled(select_session(random_bits=lambda _:234),False,'ace'))
  self.assertFalse(enabled(select_session(123,judging_seed=123),False,'ace'))
  self.assertFalse(enabled(select_session(123),True,'ace'))
  self.assertFalse(enabled(None,False,'sa3'))
 def test_resident_policy_and_seed_must_match(self):
  metadata={'generation_seed':123,'prepared_profile':'prism','composition_policy':'hook-v2'}
  env={'ROADSCORE_GENERATION_SEED':'123','ROADSCORE_ACE_PROFILE':'prism','ROADSCORE_COMPOSITION_POLICY':'hook-v2'}
  verify(metadata,env)
  for key,value in [('generation_seed',124),('prepared_profile','aurora'),('composition_policy','prepared-v1')]:
   with self.assertRaises(ValueError):verify({**metadata,key:value},env)

if __name__=='__main__':unittest.main()
