"""Transactional semantic-plan binding to the native sampler and accepted audio."""
import json
import hashlib
from pathlib import Path
import time
import numpy as np
import soundfile as sf
from hook_planning import PlanCache, digest, request_plan, next_section

class PlannedComposition:
 def __init__(self, client, root, session_seed, profile):
  self.client,self.root,self.seed,self.profile=client,Path(root),session_seed,profile
  self.root.mkdir(parents=True,exist_ok=True)
  self.cache=PlanCache(self.root/'plans');self.identity=client.fingerprints()
  self.index=0;self.previous_key=None;self.pending=None;self.accepted={}
  self.hook=self.root/'accepted_hook.wav'
 def begin(self, previous, arrival=False):
  sources={};context={}
  if previous is not None:
   identity=hashlib.sha256(previous.tobytes()).hexdigest()
   if identity not in self.accepted:raise ValueError('Continuation source was not accepted in this session')
   self.index,self.previous_key=self.accepted[identity]
  role='initial' if self.index==0 else next_section(self.index-1,arrival_intent=arrival)
  if self.index:
   if previous is None or previous.ndim!=3 or previous.shape[0]!=1 or previous.shape[1]<200 or previous.shape[2]!=64:raise ValueError('Committed musical tail required')
   prefix=self.root/'committed_prefix.npy';np.save(prefix,previous[:,-200:].copy())
   sources={'hook_reference':self.hook,'committed_prefix':prefix}
   context={'hook_reference_sha256':digest(self.hook),'committed_prefix_sha256':digest(prefix),'previous_plan_sha256':self.previous_key}
  elif previous is not None:raise ValueError('Fresh composition cannot reuse a previous session latent')
  request=request_plan(session_seed=self.seed,plan_index=self.index,profile=self.profile,section=role,window_seconds=30 if self.index==0 else 45,**self.identity,**context)
  started=time.monotonic();directory,hit=self.cache.resolve(request,self.client.prepare,sources=sources)
  self.pending={'request':request.identity(),'plan_key':request.cache_key,'directory':str(directory),'host_preparation_seconds':time.monotonic()-started,'plan_cache_hit':hit}
  (self.root/f'plan_{self.index}.json').write_text(json.dumps(self.pending,indent=2))
  return role
 def generate(self, native_generate, seed, previous, retain):
  if self.pending is None:raise RuntimeError('Begin a semantic plan before sampling')
  wave,latent,stats=native_generate(self.pending['directory'],seed,previous)
  role=self.pending['request']['section'];seconds=28 if self.index==0 else 36
  try:frames,endpoint=retain(wave,48000,stats['prefix_seconds'],seconds,allow_fade=role=='outro')
  except ValueError as exc:
   frames=seconds*25;endpoint={'rejected':str(exc)};stats['endpoint_error']=str(exc)
  committed=wave[:frames*1920];z=latent[:,:frames]
  if len(committed)!=frames*1920 or z.shape[1]!=frames:raise ValueError('Native sampler returned incomplete planned window')
  model_duration=stats['duration'];duration=frames/25;new=duration-stats['prefix_seconds']
  if new<=0 or not np.isfinite(committed).all():raise ValueError('Invalid committed planned audio')
  stats.update(self.pending,case=role,prepared_profile=self.profile,model_duration=model_duration,duration=duration,new_seconds=new,discarded_lookahead_seconds=model_duration-duration,endpoint=endpoint,composition_policy='hook-v2',preparation_host='authenticated host semantic planner',warm_rtf_new_audio=(stats['generation_seconds']+stats['decode_seconds'])/new)
  return committed,z,stats
 def accept(self,wave,latent):
  if self.pending is None:raise RuntimeError('No pending plan')
  if self.index==0:sf.write(self.hook,wave,48000,subtype='FLOAT')
  self.previous_key=self.pending['plan_key'];self.index+=1
  self.accepted[hashlib.sha256(latent.tobytes()).hexdigest()]=(self.index,self.previous_key)
  self.pending=None
