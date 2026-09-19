"""Prepare real generic current plans once; never generate or cache playback PCM."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'prototype'))
from hook_planning import PlanCache, VERSION, digest, request_plan, validate_prepared
from cached_composition import SCHEMA, ROLES, validate_bank
from host_hook_adapter import HostHookAdapter


def export_bank(output,plans,prefix,reference_hash,seed):
 output=Path(output);output.mkdir(exist_ok=False)
 manifest={'schema':SCHEMA,'profile':'prism','plan_version':VERSION,'preparation_seed':seed,
           'reference_audio_sha256':reference_hash,'reference_mode':'fixed-preparation-audio','contains_pcm':False,
           'runtime_seed_policy':'fresh logged native diffusion seed per normal launch; semantic plans reused',
           'runtime_context_policy':'overwrite retained8s with actual committed fresh latent tail',
           'scope':'generic demo optimization; same bundle for route1 and route2; no route/event inputs',
           'roles':{}}
 for role,(request,directory) in plans.items():
  dest=output/role;dest.mkdir()
  sources=None if role=='initial' else {'committed_prefix':prefix}
  hashes=validate_prepared(request,directory,sources)
  for name in hashes:shutil.copyfile(directory/name,dest/name)
  if role!='initial':
   shutil.copyfile(prefix,dest/'preparation_prefix.npy');hashes['preparation_prefix.npy']=digest(prefix)
  manifest['roles'][role]={'request':request.identity(),'plan_key':request.cache_key,'sha256':hashes}
 (output/'bank.json').write_text(json.dumps(manifest,indent=2))
 validate_bank(output)
 return manifest


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--assets-root',type=Path,required=True);parser.add_argument('--reference-batch',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 if args.output.exists():raise FileExistsError('Do not overwrite prepared conditioning')
 report=json.loads((args.reference_batch/'validation.json').read_text())
 seed=report['sessions'][0]['generation_seed'];first=report['runs'][0]
 if first['generation_seed']!=seed or not first['windows'][0]['quality']['accepted']:raise ValueError('First registered session has no accepted initial reference')
 reference=args.reference_batch/'session_1/hook_reference.wav';latent=args.reference_batch/'session_1/quality/00_committed.npy'
 initial_key=first['windows'][0]['plan_key']
 original=json.loads((args.reference_batch/'plans'/initial_key/'prepared.json').read_text())['request']
 if original['version']!=VERSION or original['section']!='initial':raise ValueError('Reference is not current initial strategy')
 adapter=HostHookAdapter(args.assets_root,preparation_only=True);identities=adapter.fingerprints()
 args.output.parent.mkdir(parents=True,exist_ok=True)
 cache=PlanCache(args.output.parent/'current-planner-cache')
 with tempfile.TemporaryDirectory(prefix='bank-prefix-',dir=args.output.parent) as scratch:
  prefix=Path(scratch)/'prefix.npy';np.save(prefix,np.load(latent,allow_pickle=False)[:,-200:].copy())
  sources={'hook_reference':reference,'committed_prefix':prefix}
  plans={};started=time.monotonic()
  indices={'initial':0,'verse':1,'prechorus':2,'chorus':3,'bridge':5,'outro':7}
  for role in ROLES:
   if shutil.disk_usage(args.output.parent).free<1024**3:raise RuntimeError('Less than1GiB free; refusing preparation')
   context={} if role=='initial' else dict(hook_reference_sha256=digest(reference),committed_prefix_sha256=digest(prefix),previous_plan_sha256=plans['initial'][0].cache_key)
   request=request_plan(session_seed=seed,plan_index=indices[role],profile='prism',section=role,window_seconds=30 if role=='initial' else 45,**identities,**context)
   tick=time.monotonic();directory,hit=cache.resolve(request,adapter,sources={} if role=='initial' else sources)
   plans[role]=(request,directory)
   print(json.dumps({'role':role,'plan_key':request.cache_key,'cache_hit':hit,'seconds':time.monotonic()-tick}),flush=True)
  export_bank(args.output,plans,prefix,digest(reference),seed)
  print(json.dumps({'complete':True,'output':str(args.output),'seconds':time.monotonic()-started,'contains_pcm':False}),flush=True)

if __name__=='__main__':main()
