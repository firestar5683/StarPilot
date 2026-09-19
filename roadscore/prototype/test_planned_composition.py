import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
import numpy as np
from hook_service import Client,make_server
from hook_planning import PlanCache
from planned_composition import PlannedComposition
from test_hook_planning import fake_prepare

class Adapter:
 def fingerprints(self):return {'model_fingerprint':'a'*64,'preparation_fingerprint':'b'*64}
 def __call__(self,req,sources,out):
  fake_prepare(req,sources,out)
  if req.prefix_seconds:
   n=req.window_seconds*25;prefix=np.load(sources['committed_prefix'])
   context=np.zeros((1,n,128),np.float32);context[:,:200,:64]=prefix
   source=np.zeros((1,n,64),np.float32);source[:,:200]=prefix
   np.save(out/'context_latents.npy',context);np.save(out/'sampler_clean_src_latents.npy',source)
   np.save(out/'sampler_repaint_mask.npy',np.arange(n)[None,:]>=200)
   (out/'sampler.json').write_text(json.dumps({'repaint_crossfade_frames':12,'repaint_injection_ratio':.5}))

def retain(wave,sr,prefix,seconds,allow_fade=False):return seconds*25,{}

def sampler(path,seed,previous):
 context=np.load(Path(path)/'context_latents.npy');n=context.shape[1]
 latent=np.full((1,n,64),seed,np.float16)
 wave=np.full((n*1920,2),.1,np.float32)
 return wave,latent,dict(duration=n/25,prefix_seconds=0 if previous is None else 8,generation_seconds=1,decode_seconds=.1)

class IntegrationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.server=make_server(Adapter(),PlanCache(self.root/'server'),'secret')
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.client=Client('http://127.0.0.1:'+str(self.server.server_port),'secret')
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
 def test_freshplans_causal_chain_and_discarded_result(self):
  run=PlannedComposition(self.client,self.root/'session',101,'prism')
  self.assertEqual(run.begin(None),'initial')
  wave,latent,stats=run.generate(sampler,11,None,retain)
  self.assertEqual(len(wave),28*48000);self.assertEqual(latent.shape,(1,700,64))
  initial_key=stats['plan_key'];run.accept(wave,latent)
  committed=latent.copy()
  self.assertEqual(run.begin(committed),'verse')
  wave,latent,stats=run.generate(sampler,12,committed,retain)
  self.assertEqual(len(wave),36*48000);self.assertEqual(stats['new_seconds'],28)
  self.assertEqual(stats['request']['previous_plan_sha256'],initial_key)
  prefix=np.load(self.root/'session/committed_prefix.npy');np.testing.assert_array_equal(prefix,committed[:,-200:])
  run.accept(wave,latent)
  # Audio scheduler discarded this result: its next request supplies the old committed tail.
  self.assertEqual(run.begin(committed),'verse')
  self.assertEqual(run.pending['request']['previous_plan_sha256'],initial_key)
  self.assertTrue(run.pending['plan_cache_hit'])
  run.accept(wave,latent)
  self.assertEqual(run.begin(latent),'prechorus')
  wave,new,stats=run.generate(sampler,13,latent,retain);run.accept(wave,new)
  self.assertEqual(run.begin(new),'chorus')
  other=PlannedComposition(self.client,self.root/'other',102,'prism');other.begin(None)
  self.assertNotEqual(other.pending['plan_key'],initial_key)
 def test_unknown_context_and_bad_auth_fail_closed(self):
  run=PlannedComposition(self.client,self.root/'session',101,'prism')
  with self.assertRaises(ValueError):run.begin(np.zeros((1,700,64)))
  with self.assertRaises(HTTPError):Client(self.client.url,'wrong').fingerprints()
 def test_seed_and_prompt_tampering_rejected(self):
  run=PlannedComposition(self.client,self.root/'session',101,'prism');run.begin(None)
  request=run.pending['request'].copy();request['caption']='stale generic plan'
  with self.assertRaises(HTTPError):self.client.call('/plan',{'request':request,'sources':{}})

if __name__=='__main__':unittest.main()
