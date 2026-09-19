import json
import ast
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from hook_planning import PlanCache,digest,request_plan
from cached_composition import CachedComposition,validate_bank,ROLES
from prepare_local_plan_bank import export_bank
from test_planned_composition import Adapter,sampler,retain

class CachedTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.prefix=self.root/'prefix.npy';np.save(self.prefix,np.ones((1,200,64),np.float32)*7)
  self.hook=self.root/'reference.wav';self.hook.write_bytes(b'test reference only')
  plans={};adapter=Adapter();cache=PlanCache(self.root/'cache')
  for i,role in enumerate(ROLES):
   context={} if not i else dict(hook_reference_sha256=digest(self.hook),committed_prefix_sha256=digest(self.prefix),previous_plan_sha256=plans['initial'][0].cache_key)
   req=request_plan(session_seed=101,plan_index=i,profile='prism',section=role,window_seconds=30 if not i else 45,**adapter.fingerprints(),**context)
   sources={} if not i else {'hook_reference':self.hook,'committed_prefix':self.prefix}
   plans[role]=(req,cache.resolve(req,adapter,sources=sources)[0])
  self.bank=self.root/'bank';export_bank(self.bank,plans,self.prefix,digest(self.hook),101)
 def tearDown(self):self.temp.cleanup()
 def test_bank_has_current_real_plan_provenance_without_pcm(self):
  result=validate_bank(self.bank);self.assertEqual(result['preparation_seed'],101)
  self.assertEqual(set(result['roles']),set(ROLES));self.assertFalse(list(self.bank.rglob('*.wav')))
  (self.bank/'verse/context_latents.npy').write_bytes(b'corrupt')
  with self.assertRaises(ValueError):validate_bank(self.bank)
 def test_fresh_noise_and_actual_prefix_are_forwarded_without_replanning(self):
  run=CachedComposition(self.bank,self.root/'run',991,'prism');self.assertEqual(run.begin(None),'initial')
  calls=[]
  def native(path,seed,previous):calls.append((path,seed,previous));return sampler(path,seed,previous)
  wave,latent,stats=run.generate(native,19,None,retain);run.accept(wave,latent)
  self.assertEqual(run.begin(latent),'verse');wave,new,stats=run.generate(native,20,latent,retain)
  self.assertIs(calls[-1][2],latent);self.assertEqual(calls[-1][1],20)
  self.assertEqual(stats['conditioning_preparation_seed'],101);self.assertEqual(stats['generation_seed'],991)
  self.assertFalse(stats['runtime_hook_used_for_conditioning']);self.assertEqual(stats['composition_policy'],'hook-cache-v1')
  run.accept(wave,new);self.assertEqual(run.begin(new,arrival=True),'outro')
  # A scheduler-discarded candidate cannot advance the musical parent.
  self.assertEqual(run.begin(latent),'verse')
 def test_actual_native_preparer_rebinds_only_fresh_tail(self):
  source=Path(__file__).resolve().parents[1]/'experiments/ace_chestnut_20260916/ace_runtime.py'
  tree=ast.parse(source.read_text())
  cls=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='Composer')
  method=next(node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='prepare')
  namespace={'np':np,'json':json}
  exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),namespace)
  actual=np.arange(700*64,dtype=np.float32).reshape(1,700,64)/10000
  before=np.load(self.bank/'verse/context_latents.npy')
  _,context,_,source_latent,mask,_,_=namespace['prepare'](SimpleNamespace(root=self.root),str(self.bank/'verse'),actual)
  np.testing.assert_array_equal(context[:,:200,:64],actual[:,-200:].astype(np.float16))
  np.testing.assert_array_equal(source_latent[:,:200],actual[:,-200:].astype(np.float16))
  np.testing.assert_array_equal(context[:,200:],before[:,200:].astype(np.float16))
  np.testing.assert_array_equal(np.load(self.bank/'verse/context_latents.npy'),before)
  self.assertFalse(mask[:,:200].any());self.assertTrue(mask[:,200:].all())

 def test_incomplete_stale_and_pcm_banks_refused(self):
  path=self.bank/'bank.json';value=json.loads(path.read_text());value['plan_version']='old';path.write_text(json.dumps(value))
  with self.assertRaises(ValueError):validate_bank(self.bank)

if __name__=='__main__':unittest.main()
