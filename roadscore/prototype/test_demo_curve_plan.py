import copy
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from demo_curve_plan import ReplayCurvePlan,launch_plan,validate
from score_archive import staging_provenance

PLAN={'version':1,'demo_only':True,'route':'synthetic-route','replay_start':149,
      'curves':[{'build_start':10.,'apex':24.,'end':25.5,'evidence':'Synthetic measured curve fixture'}]}


class PlanTests(unittest.TestCase):
 def test_exact_route_start_and_fresh_native_demo_only(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'plan.json';path.write_text(json.dumps(PLAN))
   options=dict(native=True,replay=False,judging=False,policy='conservative-v4')
   self.assertEqual(launch_plan(path,'synthetic-route',149,**options),PLAN)
   for changes in ({'native':False},{'replay':True},{'judging':True},{'policy':'conservative-v3'}):
    self.assertIsNone(launch_plan(path,'synthetic-route',149,**(options|changes)))
   self.assertIsNone(launch_plan(path,'another-route',149,**options))
   self.assertIsNone(launch_plan(path,'synthetic-route',150,**options))
 def test_no_live_or_judging_plan_and_no_input_mutation(self):
  env={'ROADSCORE_DEMO_CURVE_PLAN':json.dumps(PLAN),'ROADSCORE_PRESENTATION_POLICY':'conservative-v4'}
  self.assertIsNone(ReplayCurvePlan.from_environment('live',env))
  self.assertIsNone(ReplayCurvePlan.from_environment('replay',env|{'ROADSCORE_SEED_ORIGIN':'judging-route'}))
  plan=ReplayCurvePlan.from_environment('replay',env)
  source={'kind':'curve','phase':'neutral','activation':None,'amount':0.}
  self.assertIs(plan.state(15,'other-route',source),source)
  self.assertIs(plan.state(9,'synthetic-route',source),source)
  stages=[plan.state(t,'synthetic-route',source) for t in (10,17,23,24,25)]
  self.assertEqual(source,{'kind':'curve','phase':'neutral','activation':None,'amount':0.})
  self.assertEqual([s['phase'] for s in stages],['anticipation']*3+['event']*2)
  self.assertEqual(stages[1]['amount'],.5)
  self.assertTrue(all(s['demo_staged_curve'] for s in stages))
  self.assertIs(plan.state(26,'synthetic-route',source),source)
 def test_invalid_or_unbounded_timeline_is_rejected(self):
  for changes in ({'apex':float('nan')},{'build_start':-1},{'apex':100},{'end':24.1},{'evidence':''}):
   candidate=copy.deepcopy(PLAN);candidate['curves'][0].update(changes)
   with self.assertRaises(ValueError):validate(candidate)
  candidate=copy.deepcopy(PLAN);candidate['curves'].append(candidate['curves'][0].copy())
  with self.assertRaises(ValueError):validate(candidate)
 def test_archive_keeps_staging_disclosure_and_exact_plan_hash(self):
  with tempfile.TemporaryDirectory() as directory:
   self.assertEqual(staging_provenance(directory),{})
   path=Path(directory)/'demo_curve_plan.json';path.write_text(json.dumps(PLAN))
   meta=staging_provenance(directory)
   self.assertTrue(meta['presentation_demo_only'])
   self.assertEqual(meta['demo_curve_plan_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())


if __name__=='__main__':unittest.main()
