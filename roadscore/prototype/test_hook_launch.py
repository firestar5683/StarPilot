import unittest
import tempfile
import json
from pathlib import Path
from types import SimpleNamespace
from hook_launch import enabled,start_planner
from prepared_session import verify
from session_seed import select_session

class LaunchTests(unittest.TestCase):
 def test_planner_environment_isolated_and_caller_restored(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);python=root/'python';python.touch()
   env={'ROADSCORE_PLANNER_PYTHON':str(python),'PYTHONPATH':'unrelated-runtime:analysis/site-packages','PYTORCH_ENABLE_MPS_FALLBACK':'0'}
   observed=[]
   def launch(command,name,**kwargs):
    observed.append((name,env.copy()))
    if name=='semantic_planner':(root/'planner_ready.json').write_text(json.dumps({'port':12345}))
    else:(root/'semantic_tunnel.log').write_text('PLANNER_TUNNEL_READY')
    return SimpleNamespace(poll=lambda:None)
   start_planner(launch,env,root,root/'roadscore','fake-no-connection')
   self.assertEqual(observed[0][1]['PYTHONPATH'],str(root/'roadscore/prototype')+':'+str(root/'roadscore/experiments/ace_chestnut_20260916'))
   self.assertEqual(observed[0][1]['PYTORCH_ENABLE_MPS_FALLBACK'],'1')
   self.assertEqual(env['PYTHONPATH'],'unrelated-runtime:analysis/site-packages')
   self.assertEqual(env['PYTORCH_ENABLE_MPS_FALLBACK'],'0')
   self.assertEqual(observed[1][1]['PYTHONPATH'],env['PYTHONPATH'])

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
