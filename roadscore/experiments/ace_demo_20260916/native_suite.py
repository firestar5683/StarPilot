"""Bounded trained-weight gate benchmark and sequential fixed-window soak. No playback."""
import os,sys,time,json,fcntl,resource
os.environ.setdefault('TC_OPT','2')
from pathlib import Path
import numpy as np,soundfile as sf
R=Path(__file__).resolve().parents[2];P=R/'experiments/ace_chestnut_20260916';sys.path.insert(0,str(P));OUT=R/'results/ace_demo_20260916';OUT.mkdir(exist_ok=True)
from window_runtime import Composer
from quality_gate import QualifiedGenerator
from link_health import LinkProbe
from tinygrad import Device
lock=open(R/'generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
c=Composer(P);probe=LinkProbe(Device['AMD'],OUT/'suite_link.jsonl');probe.install_failure_hook(contain=True);c.decoder.trace=probe.trace
current=None
print('SUITE_CONFIGURATION',json.dumps({'TC_OPT':os.environ.get('TC_OPT'),'DEV':os.environ.get('DEV'),'mode':os.environ.get('ACE_SUITE')}),flush=True)
def generate(role,seed,previous):
 probe.preflight()
 try:return c.generate(role,seed,previous)
 except Exception as e:
  probe.sample('generation_exception',error=str(e),role=role,seed=seed);raise
q=QualifiedGenerator(generate)
def run(name,role,seed,previous=None,deadline=None):
 folder=OUT/name;folder.mkdir(parents=True,exist_ok=True)
 def record(i,w,z,row):
  sf.write(folder/f'attempt_{i}.wav',w,48000,subtype='FLOAT');np.save(folder/f'attempt_{i}.npy',z);(folder/f'attempt_{i}.json').write_text(json.dumps(row,indent=2));return {'directory':str(folder),'attempt':i}
 w,z,stats=q.run(role,seed,previous,deadline=deadline,record=record)
 stats['host_peak_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024;stats['tracked_allocation_bytes']=probe.last.get('allocator_bytes')
 (folder/'result.json').write_text(json.dumps(stats,indent=2));print('SUITE_RESULT',name,stats['quality_accepted'],stats.get('quality_stop_reason'),flush=True)
 if w is not None:sf.write(folder/'accepted.wav',w,48000,subtype='FLOAT');np.save(folder/'accepted.npy',z)
 return w,z,stats
mode=os.environ.get('ACE_SUITE','bad')
if mode in ('bad','all'):
 warm,warm_z,warm_s=run('warmup/initial','initial',33602)
 if warm is None:raise RuntimeError('Production-shape initial warmup failed bounded quality gate')
 run('warmup/verse','verse',33603,warm_z)
 sources=[('community','chorus',2891394132,'live_chorus_source/ace_job_1789597789267.npy'),('curve','verse',2892054524,'live_curve_source/ace_job_1789598449659.npy')]
 for name,role,seed,path in sources:run('bad_'+name,role,seed,np.load(R/'results/ace_stability_20260916'/path))
if mode in ('soak','all'):
 w,z,s=run('soak/initial','initial',33602);assert w is not None,'Initial failed bounded retries'
 rows=[s];audio=w.copy();buffer=112.;clock=time.monotonic();roles=['verse','prechorus','chorus','verse','bridge','chorus'];accepted=0
 for i in range(int(os.environ.get('ACE_SOAK_COUNT','30'))):
  # Standalone measured buffer-equivalent simulation; no future route reads.
  role='outro' if i==int(os.environ.get('ACE_SOAK_COUNT','30'))-1 else roles[i%len(roles)];buffer=min(buffer,90.);t=time.monotonic();w,nextz,s=run(f'soak/section_{i:02d}',role,41000+i,z,deadline=t+buffer)
  elapsed=time.monotonic()-t;buffer-=elapsed;s['buffer_equivalent_before_commit']=buffer
  if w is None:s['blocked']='bounded quality retries exhausted';rows.append(s);break
  prefix=round(s['prefix_seconds']*48000);overlap=96000;alpha=np.linspace(0,1,overlap)[:,None];audio[-overlap:]=audio[-overlap:]*(1-alpha)+w[prefix-overlap:prefix]*alpha;audio=np.concatenate([audio,w[prefix:]]);z=nextz;buffer+=s['new_seconds'];accepted+=1;s['buffer_equivalent_after_commit']=buffer;rows.append(s)
  (OUT/'soak_progress.json').write_text(json.dumps({'accepted':accepted,'rows':rows,'buffer_equivalent':buffer},indent=2))
  if buffer<10:s['blocked']='buffer-equivalent danger reached';break
 sf.write(OUT/'section_flow.wav',audio,48000,subtype='FLOAT');(OUT/'soak_result.json').write_text(json.dumps({'accepted':accepted,'rows':rows,'buffer_equivalent':buffer,'wall_seconds':time.monotonic()-clock},indent=2))
