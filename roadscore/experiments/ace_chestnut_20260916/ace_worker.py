"""Opt-in, offroad resident ACE composer. No route reads or physical audio output."""
import os
os.environ.setdefault('TC_OPT','2')
# Full-speed is the event default. A cap must be an explicit failure mitigation.
import time,json,fcntl,signal,traceback,sys,resource
BOOT=time.monotonic()
from pathlib import Path
import numpy as np,soundfile as sf
windowed=os.environ.get('ROADSCORE_ACE_WINDOWED','1')=='1'
if windowed:
 from window_runtime import Composer
else:
 from ace_runtime import Composer
P=Path(__file__).resolve().parent;R=P.parents[1];G=R/'generated'
sys.path.insert(0,str(R/'prototype'))
from ace_profiles import selected
from generation_seed import configured_seed,sample_seed
base_seed=configured_seed(required=True)
from quality_gate import QualifiedGenerator,POLICY,HOOK_POLICY
from link_health import LinkProbe
from hook_service import Client
from planned_composition import PlannedComposition
composition_policy=os.environ.get('ROADSCORE_COMPOSITION_POLICY','prepared-v1')
if composition_policy not in ('prepared-v1','hook-v2','hook-cache-v1'):raise ValueError('Unknown composition policy')
if composition_policy in ('hook-v2','hook-cache-v1') and not windowed:raise ValueError('Hook planning requires windowed native sampler')
if composition_policy=='hook-cache-v1':
 from cached_composition import CachedComposition,validate_bank
 validate_bank(Path(os.environ['ROADSCORE_PLAN_BANK']),profile=selected())
from tinygrad import Device
profile=selected();preparation_id=f'{profile}_{time.time_ns()}'
lock=open(G/'gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
ready=G/'worker_ready';ready.unlink(missing_ok=True)
def stop(*_):raise KeyboardInterrupt
signal.signal(signal.SIGTERM,stop)
def write_json(path,data):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2));tmp.replace(path)
def save_wave(path,wave):sf.write(path,wave*POLICY.output_gain,48000,subtype='FLOAT')
try:
 write_json(G/'ace_worker_state.json',{'pid':os.getpid(),'generation_seed':base_seed,'composition_policy':composition_policy,'profile':profile,'phase':'preparing'})
 load_started=time.monotonic()
 c=Composer(P,profile=profile) if windowed else Composer(P)
 model_load_seconds=time.monotonic()-load_started
 probe=LinkProbe(Device['AMD'],G/'ace_link.jsonl');probe.install_failure_hook(contain=True)
 if windowed:c.decoder.trace=probe.trace
 planned=None
 if composition_policy in ('hook-v2','hook-cache-v1'):
  from ace_runtime import Composer as NativeComposer
  from window_policy import retained_end
  if composition_policy=='hook-cache-v1':
   planned=CachedComposition(Path(os.environ['ROADSCORE_PLAN_BANK']),G/'hook_sessions'/preparation_id,base_seed,profile)
  else:
   planned=PlannedComposition(Client(os.environ['ROADSCORE_PLANNER_URL'],os.environ['ROADSCORE_PLANNER_TOKEN']),G/'hook_sessions'/preparation_id,base_seed,profile)
  def planned_generate(role,seed,previous):return planned.generate(lambda case,seed,previous:NativeComposer.generate(c,case,seed,previous),seed,previous,retained_end)
 sample=planned_generate if planned else c.generate
 def generate(role,seed,previous):
  probe.preflight(role=role,seed=seed)
  try:
   wave,latent,stats=sample(role,seed,previous);stats['power_limit_watts']=float(os.environ['AM_POWER_LIMIT']) if os.environ.get('AM_POWER_LIMIT') else None;stats['link_session']=probe.session;stats['host_peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;stats['tracked_allocation_bytes']=probe.last.get('allocator_bytes');return wave,latent,stats
  except Exception as e:
   probe.sample('generation_exception',error=str(e),role=role,seed=seed);raise
 qualified=QualifiedGenerator(generate,policy=HOOK_POLICY if planned else POLICY)
 def record_for(job):
  folder=G/'quality'/str(job);folder.mkdir(parents=True,exist_ok=True)
  def record(attempt,wave,latent,row):
   stem=folder/f'attempt_{attempt}'
   save_wave(stem.with_suffix('.wav'),wave);np.save(stem.with_suffix('.npy'),latent);write_json(stem.with_suffix('.json'),row)
   return {'directory':str(folder),'stem':stem.name,'output_gain':POLICY.output_gain}
  return record
 print('ACE_PREPARING',profile,flush=True)
 initial=None;last=None;preparation=[];slot=0
 while initial is None or len(initial)/48000<POLICY.initial_buffer_seconds:
  role=('initial' if windowed else 'verse') if initial is None else ('verse' if windowed else 'repaint_verse')
  if planned:role=planned.begin(last)
  wave,last_new,stats=qualified.run(role,sample_seed(base_seed,"prepare",slot),last,record=record_for('prepare_'+preparation_id+'_'+str(slot)))
  preparation.append(stats)
  if wave is None:raise RuntimeError('Preparation rejected after bounded quality retries; inspect generated/quality')
  if planned:planned.accept(wave,last_new)
  if initial is None:initial=wave.copy()
  else:
   overlap=2*48000;prefix=round(stats['prefix_seconds']*48000);alpha=np.linspace(0,1,overlap)[:,None]
   initial[-overlap:]=initial[-overlap:]*(1-alpha)+wave[prefix-overlap:prefix]*alpha
   initial=np.concatenate([initial,wave[prefix:]])
  last=last_new;slot+=1
  if slot>8:raise RuntimeError('Initial buffer did not fill within bounded preparation')
 save_wave(G/'ace_initial.wav',initial);np.save(G/'ace_initial.npy',last)
 write_json(G/'ace_initial.json',{'generation_seed':base_seed,'composition_policy':composition_policy,'composer':'ace','startup_seconds':time.monotonic()-BOOT,'model_load_seconds':model_load_seconds,'host_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'duration':len(initial)/48000,'source_identity':'kpop_control','prepared_profile':profile if windowed else 'legacy','preparation_id':preparation_id,'continuation_policy':'quality-gated fixed lookahead','generation':preparation,'prepared_identity':True,'output_gain':POLICY.output_gain,'created_wall':time.time()})
 write_json(G/'ace_worker_state.json',{'pid':os.getpid(),'generation_seed':base_seed,'composition_policy':composition_policy,'profile':profile,'phase':'READY','initial_buffer_seconds':len(initial)/48000})
 (G/'request.json').unlink(missing_ok=True);ready.write_text('ace');print('ACE_READY',flush=True)
 while True:
  request=G/'request.json'
  if not request.exists():time.sleep(.1);continue
  req=json.loads(request.read_text());request.unlink()
  if req.get('composer')!='ace':raise ValueError('ACE worker received a request for a different backend')
  if req.get('profile',profile)!=profile:raise ValueError('Resident ACE profile mismatch; stop and prepare requested profile before replay')
  if req.get('identity')!='kpop_control':raise ValueError('ACE experimental worker only has the prepared kpop_control identity')
  if req.get('generation_seed')!=base_seed:raise ValueError('Generation request does not match prepared session seed')
  job=int(req['id']);busy=G/'busy';busy.write_text(str(job));start=time.monotonic()
  try:
   case={'base':'repaint_verse','approach':'repaint_chorus','bridge_transition':'repaint_bridge','closing':'repaint_outro'}.get(req['conditioning'])
   if case is None and req['conditioning'] in ('verse','prechorus','chorus','bridge','outro'):case=req['conditioning'] if windowed else 'repaint_'+req['conditioning']
   if case is None:raise ValueError('Unsupported ACE section intent')
   if windowed:case=case.removeprefix('repaint_')
   previous=np.load(req['latents'])
   if planned:case=planned.begin(previous,arrival=case=='outro')
   deadline=req.get('playback_deadline_monotonic')
   wave,latent,stats=qualified.run(case,int(req['seed']),previous,deadline=deadline,record=record_for(job))
   if wave is None:
    write_json(G/f'result_{job}.json',{**req,**stats,'id':job,'composer':'ace','seconds':time.monotonic()-start});continue
   if planned:planned.accept(wave,latent)
   wav=G/f'ace_job_{job}.wav';lat=G/f'ace_job_{job}.npy';save_wave(wav,wave);np.save(lat,latent)
   result={**req,**stats,'id':job,'composer':'ace','backend':'ACE-Step1.5 turbo native Chestnut, prepared identity','wav':str(wav),'latents':str(lat),'seconds':time.monotonic()-start,'retained_seconds':stats['prefix_seconds'],'new_audio_start_frame':round(stats['prefix_seconds']*48000),'overlap_frames':96000,'sample_rate':48000,'output_gain':POLICY.output_gain,'conditioning':req['conditioning']}
   write_json(G/f'result_{job}.json',result);print('ACE_RESULT',job,result['seconds'],flush=True)
  except Exception as e:
   write_json(G/f'result_{job}.json',{**req,'error':str(e),'composer':'ace'});traceback.print_exc();raise
  finally:busy.unlink(missing_ok=True)
finally:
 ready.unlink(missing_ok=True)
 write_json(G/'ace_worker_state.json',{'pid':os.getpid(),'generation_seed':base_seed,'composition_policy':composition_policy,'profile':profile,'phase':'Stopped'})
