"""Counterfactual inputs for the reproduced live gap; never route-specific runtime policy."""
import shutil,json,hashlib
import numpy as np
from bundle import OUT,OLD,create
base=OUT/'cases/live_community_chorus';prior=OUT/'live_chorus_source/ace_job_1789597789267.npy';seed=2891394132;plan=[]
for label in ['verse_condition','prefix4','prefix12','prefix16']:
 name='live_gap_'+label;p=OUT/'cases'/name
 if label=='verse_condition':create(name,OLD/'profiles/prism/verse',seed,prior)
 else:
  shutil.copytree(base,p,dirs_exist_ok=True,ignore=shutil.ignore_patterns('reference*','native*'))
  prefix=int(label.removeprefix('prefix'))*25
  c=np.load(p/'context_latents.npy');s=np.load(p/'source.npy');m=np.load(p/'mask.npy');previous=np.load(prior)
  # Same ordinary repaint boundary: source context outside the prefix remains
  # the prepared silence template, and chunk mask marks only new frames.
  silence=c[:,300:325,:64].copy()
  c[:,:,:64]=np.tile(silence,(1,45,1));c[:,:,64:]=1
  c[:,:prefix,:64]=previous[:,-prefix:];c[:,:prefix,64:]=0
  s[:,:prefix]=previous[:,-prefix:];m[:]=True;m[:,:prefix]=False
  for k,a in [('context_latents',c),('source',s),('mask',m)]:np.save(p/(k+'.npy'),a)
  meta=json.loads((base/'case.json').read_text());meta.update(name=name,ablation=label,sha256={})
  for f in p.glob('*.npy'):meta['sha256'][f.stem]=hashlib.sha256(np.load(f).tobytes()).hexdigest()
  (p/'case.json').write_text(json.dumps(meta,indent=2))
 plan.append({'case':name,'output':'reference_rounded'})
(OUT/'live_gap_ablation_plan.json').write_text(json.dumps(plan,indent=2))
