import shlex,unittest
from receiver_environment import assignments,resolve_compute
class ReceiverEnvironmentTests(unittest.TestCase):
 def test_power_graph_and_policy_cross_receiver_boundary(self):
  env={'AM_POWER_LIMIT':'100','TC_OPT':'2','ROADSCORE_COMPOSITION_POLICY':'hook-v2','ROADSCORE_PLANNER_TOKEN':'private value; $(no)','UNRELATED_SECRET':'omit'}
  actual=dict(item.split('=',1) for item in shlex.split(assignments(env)))
  self.assertEqual(actual,{k:v for k,v in env.items() if k!='UNRELATED_SECRET'})
 def test_absent_power_does_not_rewrite_frozen_policy(self):
  self.assertEqual(assignments({}),'')
 def test_plain_fresh_ace_resolves_event_settings(self):
  env={};record=resolve_compute(env,composer='ace')
  self.assertEqual(env,{'AM_POWER_LIMIT':'100','TC_OPT':'2'})
  self.assertIsNone(record['actual_power_limit_watts'])
  self.assertEqual(dict(item.split('=',1) for item in shlex.split(assignments(env))),env)
 def test_explicit_mitigation_and_graph_settings_survive(self):
  env={'AM_POWER_LIMIT':'75','TC_OPT':'1'};resolve_compute(env,composer='ace')
  self.assertEqual(env,{'AM_POWER_LIMIT':'75','TC_OPT':'1'})
 def test_frozen_stored_other_and_transport_get_no_defaults(self):
  for options in [{'judging':True},{'replay':True},{'transport_only':True},{'composer':'sa3'}]:
   env={};resolve_compute(env,**{'composer':'ace',**options});self.assertEqual(env,{})
  env={'AM_POWER_LIMIT':'45'};resolve_compute(env,composer='ace',judging=True)
  self.assertEqual(env,{'AM_POWER_LIMIT':'45'})
if __name__=='__main__':unittest.main()
