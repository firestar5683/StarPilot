"""Offline analysis of model outputs only. Never trims or repairs listening audio."""
import json
from pathlib import Path
import numpy as np
from bundle import R,OUT

def quiet(a,rate=48000):
 n=rate//10;e=np.sqrt(np.mean(a[:len(a)//n*n].reshape(-1,n,2).astype(np.float64)**2,axis=(1,2)));runs=[];start=None
 for i,v in enumerate(np.r_[e<.003,False]):
  if v and start is None:start=i
  elif not v and start is not None:
   if i-start>=5:runs.append([start/10,i/10])
   start=None
 return {'quiet_seconds':float(sum(e<.003)/10),'quiet_runs_at_least_half_second':runs,'rms_100ms':e.tolist()}
report={}
for name,old in [('legacy_verse','verse'),('legacy_prechorus','repaint_prechorus')]:
 p=OUT/'cases'/name;r=np.load(p/'reference/pcm.npy');n=np.load(R/f'results/ace_chestnut_20260916/flow/{old}_pcm.npy');report[name]={'native_previous':quiet(n),'official_same_inputs':quiet(r),'envelope_correlation':float(np.corrcoef(quiet(n)['rms_100ms'],quiet(r)['rms_100ms'])[0,1])}
 if old=='verse':
  ctx=np.load(p/'context_latents.npy')[0,:,:64];same=np.max(abs(ctx[5:]-ctx[:-5]),axis=1)==0;start=next((i for i in range(len(same)) if same[i:].all()),None);report[name]['five_frame_repeated_condition_tail_start_seconds']=None if start is None else (start+5)/25
report['conclusion']='Silence is reproduced by the official DiT and VAE from identical inputs, before wrapper concatenation. Initial verse has a five-frame repeating planner-hint tail. Continuation preserves the preceding silent tail, so preserved-prefix equality is not a musical continuity guarantee. Further conditioning interventions are required; no crossfade concealment is applied.'
(OUT/'silence_initial.json').write_text(json.dumps(report,indent=2));print({k:{t:v for t,v in x.items() if t not in ['native_previous','official_same_inputs']} for k,x in report.items() if isinstance(x,dict)})
