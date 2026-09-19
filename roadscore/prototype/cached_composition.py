"""Local current-planner tensors; fresh native sampling with explicit preparation provenance."""
import hashlib
import json
from pathlib import Path
import numpy as np
from hook_planning import VERSION, PlanRequest, digest, next_section, request_plan, validate_prepared
from planned_composition import PlannedComposition

SCHEMA='roadscore-local-plan-bank-v1'
POLICY='hook-cache-v1'
ROLES=('initial','verse','prechorus','chorus','bridge','outro')


def validate_bank(path,profile='prism'):
 root=Path(path).resolve();manifest=json.loads((root/'bank.json').read_text())
 if manifest.get('schema')!=SCHEMA or manifest.get('profile')!=profile:raise ValueError('Wrong local conditioning bank/profile')
 if manifest.get('plan_version')!=VERSION or set(manifest.get('roles',{}))!=set(ROLES):raise ValueError('Current complete planner bundle required')
 if manifest.get('reference_mode')!='fixed-preparation-audio' or manifest.get('contains_pcm') is not False:raise ValueError('Ambiguous cached conditioning provenance')
 for role,row in manifest['roles'].items():
  folder=root/role
  if folder.resolve().parent!=root:raise ValueError('Conditioning directory escapes bank')
  request=PlanRequest(**row['request'])
  keys=('session_seed','plan_index','profile','section','window_seconds','model_fingerprint','preparation_fingerprint','hook_reference_sha256','committed_prefix_sha256','previous_plan_sha256')
  if request!=request_plan(**{k:request.identity()[k] for k in keys}):raise ValueError('Cached plan does not match current prompt policy')
  if request.section!=role or request.profile!=profile or request.window_seconds!=(30 if role=='initial' else 45):raise ValueError('Wrong role/window in conditioning bundle')
  if request.session_seed!=manifest['preparation_seed']:raise ValueError('Mixed preparation sessions')
  if request.hook_reference_sha256!=(None if role=='initial' else manifest['reference_audio_sha256']):raise ValueError('Reference identity mismatch')
  sources=None if role=='initial' else {'committed_prefix':folder/'preparation_prefix.npy'}
  hashes=validate_prepared(request,folder,sources)
  if role!='initial':
   hashes['preparation_prefix.npy']=digest(sources['committed_prefix'])
   if hashes['preparation_prefix.npy']!=request.committed_prefix_sha256:raise ValueError('Preparation prefix identity mismatch')
  if hashes!=row['sha256'] or request.cache_key!=row['plan_key']:raise ValueError('Corrupt cached conditioning')
  if set(p.name for p in folder.iterdir())!=set(hashes):raise ValueError('Unexpected file in conditioning role')
 if set(p.name for p in root.iterdir())!=set(ROLES)|{'bank.json'}:raise ValueError('Unexpected bank files; PCM must remain outside runtime conditioning')
 return manifest


class CachedComposition(PlannedComposition):
 def __init__(self,bank,session_root,session_seed,profile):
  if type(session_seed) is not int or not 0<=session_seed<2**32:raise ValueError('Explicit fresh/reproduction session seed required')
  self.bank=Path(bank).resolve();self.manifest=validate_bank(self.bank,profile)
  self.bank_hash=digest(self.bank/'bank.json');self.root=Path(session_root);self.root.mkdir(parents=True,exist_ok=True)
  self.seed,self.profile=session_seed,profile
  self.index=0;self.previous_key=None;self.pending=None;self.accepted={}
  self.hook=self.root/'fresh_initial_for_audit.wav'
 def begin(self,previous,arrival=False):
  if previous is not None:
   identity=hashlib.sha256(previous.tobytes()).hexdigest()
   if identity not in self.accepted:raise ValueError('Unknown committed context for this fresh session')
   self.index,self.previous_key=self.accepted[identity]
  elif self.index:raise ValueError('Continuation requires actual committed context')
  role='initial' if self.index==0 else next_section(self.index-1,arrival_intent=arrival)
  row=self.manifest['roles'][role]
  self.pending={'request':row['request'],'plan_key':row['plan_key'],'directory':str(self.bank/role),
                'host_preparation_seconds':0.,'plan_cache_hit':True,'conditioning_bank_sha256':self.bank_hash,
                'generation_seed':self.seed,'conditioning_preparation_seed':self.manifest['preparation_seed'],
                'conditioning_reference_mode':'fixed-preparation-audio','runtime_hook_used_for_conditioning':False,
                'actual_committed_latent_sha256':None if previous is None else hashlib.sha256(previous.tobytes()).hexdigest()}
  (self.root/f'plan_{self.index}.json').write_text(json.dumps(self.pending,indent=2))
  return role
 def generate(self,native_generate,seed,previous,retain):
  wave,latent,stats=super().generate(native_generate,seed,previous,retain)
  stats.update(composition_policy=POLICY,preparation_host='precomputed current generic planner; no host at runtime')
  return wave,latent,stats
