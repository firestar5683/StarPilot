"""Runtime: cereal inputs only; no route-file access. Bench audio and private status UI."""
import argparse,json,time,threading,queue,traceback,signal,os,gc,shutil
from pathlib import Path
import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy.signal import resample_poly
from cereal import messaging
from concurrent.futures import ThreadPoolExecutor
from core import Conductor,DSP
from phrase import pulse,cadence_runway,mix_cadence
from driving_music import DrivingDSP
from event_music import EventDSP
from input_clock import InputClock
from engagement_presentation import EngagementPresentation,PresentationConfig,engagement_active
from signal_shaker import SignalShaker,assess_grid,profile_tempo_prior
from core_apex import CoreApex
from rolling import anchor_options,INITIAL_END,WINDOW,LATENT_SECONDS,trajectory
from musical import Arrival,MusicalDSP,analyze_music,ending_gesture,match_continuation
p=argparse.ArgumentParser();p.add_argument('--root',default='/data/roadscore');p.add_argument('--input',choices=['live','replay'],default='replay');p.add_argument('--audible',action='store_true');p.add_argument('--no-conductor',action='store_true');a=p.parse_args();from audio_policy import allow_output;a.audible=allow_output(a.audible);a.mute=not a.audible
def terminate(sig,frame):raise KeyboardInterrupt
signal.signal(signal.SIGTERM,terminate)
root=Path(a.root)
from privacy_guard import install
install(root)
run=root/'results/current';run.mkdir(parents=True,exist_ok=True)
gc_events=[];gc_started={}
def gc_audit(phase,info):
 if phase=='start':gc_started[info['generation']]=time.monotonic()
 else:gc_events.append({'generation':info['generation'],'start':gc_started.get(info['generation']),'end':time.monotonic()})
gc.callbacks.append(gc_audit)
rate=48000;block=4800
styles=json.loads((root/'prototype/styles.json').read_text())
def configuration():
 try:return json.loads((root/'runtime.json').read_text())
 except (FileNotFoundError,json.JSONDecodeError):return {}
from composer_choice import choice
from composer_audio import result_window
from render_policy import selected as render_mode_selected, validate as validate_render_mode, render as render_audio, ring_only as render_ring_only
render_mode=render_mode_selected()
from generation_budget import GenerationBudget
from generation_seed import configured_seed,sample_seed
base_seed=configured_seed(required=choice()=="ace");generation_index=0
if base_seed is not None:
 if choice()!="ace":raise ValueError("Deterministic session seeds currently require ACE")
 prepared=json.loads((root/"generated/ace_initial.json").read_text())
 if prepared.get("generation_seed")!=base_seed:raise ValueError("Resident preparation seed differs from requested session seed")
generation_budget=GenerationBudget();budget_waiting=False
composer=choice()
from ace_profiles import selected,PROFILES
ace_profile=selected()
if composer=='ace':
 from ending_policy import safe_ending_gesture as ending_gesture
config=configuration();validate_render_mode(render_mode,composer,config.get('song_form_experimental',False));identity=config.get('identity','legacy');identity=identity if identity in styles else 'legacy'
rolling_mode=config.get('rolling',False);rolling_anchors={k:anchor_options(root,k) for k in styles if (root/f'assets/source_{k}.wav').exists()} if rolling_mode and composer!='ace' else {}
drive_events=config.get('drive_events',False) or config.get('event_music',False);phrase_runway=config.get('phrase_runway',False)
presentation_config=PresentationConfig.read(config.get('engagement_presentation'))
shaker_enabled=config.get('signal_shaker',{}).get('enabled') is True
apex_enabled=config.get('core_apex',{}).get('enabled') is True
if (presentation_config.enabled or shaker_enabled or apex_enabled) and render_mode!='gold-core':raise ValueError('Optional presentation layers require gold-core baseline')
presentation=EngagementPresentation(rate,block) if presentation_config.enabled else None
engagement=(False,False,0,0.,0);signal_state=(False,False,0,0.,0)
initial_identity=identity;musical_mode=config.get('musical',False);arrival=Arrival();ending_start=None;ending_audio=None;ending_info={};playing_identity=identity;identity_queue=[];last_requested_identity=identity
usable_frames=WINDOW if rolling_mode else (301 if musical_mode else 323)
source_path=root/f'assets/source_{identity}.wav' if identity!='legacy' else root/'assets/source.wav'
if composer=='ace':
 if identity!='kpop_control':raise ValueError('ACE requires the prepared kpop_control identity')
 source_path=root/'generated/ace_initial.wav'
source,sr=sf.read(source_path,dtype='float32',always_2d=True)
if sr!=rate:source=resample_poly(source,rate,sr).astype(np.float32)
if musical_mode and composer!='ace':source=source[:round((INITIAL_END if rolling_mode else usable_frames)*LATENT_SECONDS*rate)]
if source.shape[1]==1:source=np.repeat(source,2,axis=1)
con=Conductor(handoff=config.get('curve_handoff',False),threshold=float(config.get('curve_threshold',.8)));music_info=analyze_music(source,rate);dsp=MusicalDSP(rate,music_info['bpm']) if musical_mode else DSP();ending_audio,ending_info=ending_gesture(source,rate);state={'phase':'neutral','amount':0.};render_state=(state,0.,time.monotonic());nav={};origin=None;startmono=None;now=0;audio_started=False;replay_origin_wall=None
if drive_events:
 pulse_info=pulse(source,rate);dsp=DrivingDSP(rate,pulse_info['bpm'] if pulse_info['confidence']>=.25 else music_info['bpm'])
if config.get('event_music',False):
 dsp=EventDSP(rate,pulse_info['bpm'] if pulse_info['confidence']>=.25 else music_info['bpm'],styles.get(identity,{}).get('event_style','rock'))
songform=None;section_bank=None
if config.get('song_form_experimental',False):
 from song_form import SongForm
 from section_bank import SectionBank
 section_bank=SectionBank(root/'results/overnight/sections',rate);songform=SongForm(section_bank.clips['verse'][1]['bpm'])
gestures=None;composition=None
if config.get('gesture_layer',False) and render_mode=='current':
 if composer=='ace':
  if config.get('gesture_version',4)>=4:
   from musical_gestures_v4 import MusicalGestures
  elif config.get('gesture_version',4)>=3:
   from musical_gestures_v3 import MusicalGestures
  else:
   from musical_gestures_v2 import MusicalGestures
 else:
  from musical_gestures import MusicalGestures
 from bar_grid import grid
 gesture_source=source[:30*rate] if composer=='ace' else source
 gesture_pulse=pulse(gesture_source,rate)
 gesture_grid=grid(gesture_source,rate,gesture_pulse['bpm'] if gesture_pulse['confidence']>=.25 else music_info['bpm'])
 gestures=MusicalGestures(gesture_source,rate,gesture_grid['bpm'],gesture_grid['beat_phase'])
 (run/'gesture_grid.json').write_text(json.dumps(gesture_grid))
shaker=None;apex=None
if shaker_enabled or apex_enabled:
 profile_manifest=json.loads((root/'experiments/ace_chestnut_20260916/profiles'/ace_profile/'profile.json').read_text())
 shaker_grid,shaker_analysis=assess_grid(source,rate,profile_tempo_prior(profile_manifest))
 shaker=SignalShaker(shaker_grid,rate,enabled=shaker_enabled)
 apex=CoreApex(shaker_grid,rate,enabled=apex_enabled)
 (run/'shaker_grid.json').write_text(json.dumps({'grid':shaker.snapshot(),'analysis':shaker_analysis},indent=2))
if config.get('composition_control',False):
 from composition_policy import CompositionPolicy
 composition=CompositionPolicy(extended_buffer=composer=='ace')
clock_source=InputClock(a.input,run)
lock=threading.Lock();audio=source.copy();position=0;fallbacks=0;underflows=0;frames=0;seen_jobs=set();job=int(time.time()*1000);run_id=str(job);inflight=False;job_started=0.;worker_failed=False;lastlatent=str(root/f'assets/source_{identity}_latents.npy' if identity!='legacy' else root/'assets/source_latents.npy');generation=[];arrival_since=None;arrival_at=None;nav_revision=0;discarded_jobs=[]
safe_extensions=[];quality_failures=0;quality_hold=False;context_hold_only=False;holding=False
if composer=='ace':lastlatent=str(root/'generated/ace_initial.npy')
load_pool=ThreadPoolExecutor(max_workers=1);pending={}
def load_audio(meta):
 w,sr=sf.read(meta['wav'],dtype='float32',always_2d=True)
 w=resample_poly(w,rate,sr).astype(np.float32)
 end=round(usable_frames*4096/44100*rate) if musical_mode else len(w)
 start,end=result_window(meta,len(w),rate,end)
 return w[start:end]

capture=queue.Queue(maxsize=400);stop=threading.Event()
from pcm_transport import Export
export=Export(run/'pcm.sock') if os.environ.get('ROADSCORE_PCM_RETURN')=='1' else None
export_errors=[];snapshot={}
def recorder():
 with sf.SoundFile(run/'heard.wav',mode='w',samplerate=rate,channels=2,subtype='PCM_16') as f, sf.SoundFile(run/'dry.wav',mode='w',samplerate=rate,channels=2,subtype='PCM_16') as dry, (run/'audio_blocks.jsonl').open('w',buffering=1) as timing:
  while not stop.is_set() or not capture.empty():
   try:
    wet,raw,meta=capture.get(timeout=.1);f.write(wet);dry.write(raw);timing.write(json.dumps(meta)+'\n')
    meta['roadscore']={k:snapshot.get(k) for k in ['composer','job_inflight','generation_elapsed_seconds','readiness','profile','safe_extensions','quality_failures','holding_accepted_music','identity','style','playing_identity','phase','lead','buffered','arrival_at','worker_failed','section','next_section','scheduled','gesture_active','gesture_queued','turn_signal_music','outro_heard_seconds','form_labels_are_intent']}
    if export and not export_errors:
     try:export.send(wet,meta)
     except Exception as e:
      export_errors.append(repr(e));(run/'pcm_error.json').write_text(json.dumps(export_errors));export.close()
   except queue.Empty:pass
record_thread=threading.Thread(target=recorder,daemon=True);record_thread.start()
def append(wave,overlap=2.,match=False):
 global audio
 n=min(int(overlap*rate),len(audio)-position,len(wave))
 levels={}
 if match:wave,levels=match_continuation(audio,wave,n)
 with (run/'boundaries.jsonl').open('a') as f:f.write(json.dumps({'overlap_start_audio_s':frames/rate+(len(audio)-position-n)/rate,'new_material_audio_s':frames/rate+(len(audio)-position)/rate,'anchor_seconds':44*LATENT_SECONDS if rolling_mode else 0,**levels})+'\n')
 if n>0:
  alpha=np.linspace(0,1,n,dtype=np.float32)[:,None]
  audio=np.concatenate([audio[:-n],audio[-n:]*(1-alpha)+wave[:n]*alpha,wave[n:]])
 else:audio=np.concatenate([audio,wave])
def callback(out,n,ti,status):
 global position,audio,fallbacks,underflows,frames
 event_state,source_time,command_wall=render_state
 callback_wall=time.monotonic()
 if status:underflows+=1
 if not audio_started:out.fill(0);return
 with lock:
  ring_only=render_ring_only(render_mode,musical_mode,ending_start,frames,rate)
  if not ring_only and len(audio)-position<n:
   # Bounded emergency repeat of actual generated source, with crossfade.
   # Last-resort emergency; normal loop extension is prepared by the main thread.
   append(audio[-min(len(audio),rate*8):].copy(),overlap=.1);fallbacks+=1
  chunk=np.zeros((n,2),np.float32) if ring_only else audio[position:position+n].copy()
  if not ring_only:position+=n
  frames+=n
 amount=0 if a.no_conductor else event_state['amount']*(-.5 if event_state.get('kind')=='slowdown' else 1)
 ending=1 if musical_mode or arrival_at is None else max(0.,1-(source_time-arrival_at)/6)
 if drive_events:dsp.event_state=event_state if ending_start is None else {'phase':'neutral','strength':0}
 if ending_start is not None and frames-n<ending_start:amount=0.
 if section_bank is not None:chunk=section_bank.render(n)
 rendered=render_audio(render_mode,chunk,dsp,amount,ending,gestures,mix_cadence,
  (ending_audio,frames-n,ending_start,rate) if musical_mode and ending_start is not None else None)
 active,fresh=engagement_active(engagement[1],engagement[0],engagement[2],engagement[4],engagement[3],callback_wall)
 signal_on,signal_fresh=engagement_active(signal_state[1],signal_state[0],signal_state[2],signal_state[4],signal_state[3],callback_wall)
 if shaker is not None:rendered=shaker.process(rendered,frames-n,signal_on,signal_fresh)
 if apex is not None:rendered=apex.process(rendered,frames-n,event_state)
 if presentation is not None:rendered=presentation.process(rendered,active,presentation_config)
 out[:]=0 if a.mute else rendered
 try:capture.put_nowait((rendered,chunk,{'signal_shaker_enabled':shaker_enabled,'signal_on':signal_on,'signal_fresh':signal_fresh,'engagement_presentation_enabled':presentation_config.enabled,'engagement_active':active,'engagement_fresh':fresh,'audio_s':(frames-n)/rate,'callback_wall':callback_wall,'command_received_wall':command_wall,'replay_origin_wall':replay_origin_wall,'dac_delay':float(ti.outputBufferDacTime-ti.currentTime),'route_t':source_time,'amount':amount,'phase':event_state['phase'],'strength':event_state.get('strength',0),'predicted_peak':event_state.get('predicted_peak'),'activation':event_state.get('activation'),'kind':event_state.get('kind','curve'),'cadence_entry_audio_s':None if ending_start is None else ending_start/rate,'runway_active':ending_start is not None and frames-n<ending_start,'muted':a.mute,'portaudio_status':str(status),'callback_processing_seconds':time.monotonic()-callback_wall}))
 except queue.Full:underflows+=1
# Optional prewarmed continuation gives ~52 seconds before replay starts.
warm=root/'generated/job_-1.wav'
warm_identity='legacy'
try:warm_meta=json.loads((root/'generated/warm_metadata.json').read_text());warm_identity=warm_meta.get('identity','legacy')
except (FileNotFoundError,json.JSONDecodeError):pass
if composer!='ace' and warm.exists() and (root/'generated/worker_ready').exists() and warm_identity==identity and (bool(warm_meta.get('anchor_frames',0))==rolling_mode or bool(composition and warm_meta.get('anchor_frames',0)==0)):
 w,sr=sf.read(warm,dtype='float32',always_2d=True);w=resample_poly(w,rate,sr).astype(np.float32)
 end=round(usable_frames*4096/44100*rate) if musical_mode else len(w)
 append(w[round((warm_meta['retained_seconds']-2)*rate):end],overlap=2.,match=musical_mode and not rolling_mode)
 lastlatent=str(root/'generated/job_-1.npy')
sm=messaging.SubMaster(['modelV2','carState','navInstruction','navRoute','longitudinalPlan','starpilotPlan','livePose','selfdriveState'],poll='modelV2')
# Warm PortAudio before publishing ready; replay starts only once consumer exists.
if export:
 from render_clock import RenderClock
 stream=RenderClock(callback,rate,2,block)
else:stream=sd.OutputStream(samplerate=rate,channels=2,blocksize=block,dtype='float32',callback=callback)
trace=(run/'trace.jsonl').open('w',buffering=1)
(root/'generated').mkdir(exist_ok=True)
# Startup scipy/cereal graphs are long-lived. Exclude them from repeated full scans
# before audio begins; dynamic runtime objects remain normally collected.
gc.collect();gc.freeze()
try:
 with stream:
  (run/'ready').write_text('ready')
  last_progress=time.monotonic()
  while True:
   if getattr(stream,'error',None):raise RuntimeError('Remote render clock failed') from stream.error
   sm.update(100)
   control_wall=time.monotonic();latest_source=max(sm.logMonoTime.values())
   if sm.updated['selfdriveState']:
    engagement=(bool(sm['selfdriveState'].active),bool(sm.valid['selfdriveState']),sm.logMonoTime['selfdriveState'],control_wall,latest_source)
   else:engagement=(*engagement[:4],latest_source)
   if sm.updated['carState']:
    signal_state=(bool(sm['carState'].leftBlinker or sm['carState'].rightBlinker),bool(sm.valid['carState']),sm.logMonoTime['carState'],control_wall,latest_source)
   else:signal_state=(*signal_state[:4],latest_source)
   clock=clock_source.read(sm)
   if clock is None:continue
   if clock['done']:
    # EOF never arms an ending; allow only an already-triggered final gesture to ring out.
    if musical_mode and ending_start is not None and frames-ending_start<len(ending_audio):
     time.sleep(.02);continue
    break
   origin=clock['origin_ns'];replay_origin_wall=clock.get('origin_wall')
   if sm.updated['modelV2']:
    last_progress=time.monotonic();m=sm['modelV2'];now=(sm.logMonoTime['modelV2']-origin)/1e9
    if not audio_started:audio_started=True;startmono=time.monotonic()
    speed=float(sm['carState'].vEgo);available_ns=max(sm.logMonoTime.values())
    if sm.valid['modelV2'] and len(m.position.t)==33:
     state=con.update(now,{'mono':sm.logMonoTime['modelV2'],'eof':m.timestampEof,'t':list(m.orientationRate.t),'yaw':list(m.orientationRate.z),'v':list(m.velocity.x)},speed)
    else:state=con.state(now)
    samples=[(float(t),float(y)) for t,y in zip(m.orientationRate.t,m.orientationRate.z) if 1<=t<=8]
    state['predicted_turn_radians']=sum((y0+y1)*.5*(t1-t0) for (t0,y0),(t1,y1) in zip(samples,samples[1:]) if 0<t1-t0<2)
    render_state=(state,now,time.monotonic())
    if sm.updated['navRoute']:
     nav={};arrival_since=None;nav_revision+=1
     arrival.route_change(bool(sm.valid['navRoute']))
     if composition:composition.route_change()
     if sm.valid['navRoute']:arrival_at=None;ending_start=None
    if sm.updated['navInstruction']:
     n=sm['navInstruction'];nav={'valid':bool(sm.valid['navInstruction']),'type':n.maneuverType,'modifier':n.maneuverModifier,'distance':n.maneuverDistance,'remaining':n.distanceRemaining,'eta':n.timeRemaining,'mono':sm.logMonoTime['navInstruction']}
    navfresh=nav.get('valid',False) and 0<=(available_ns-nav.get('mono',0))/1e9<3
    arriving=navfresh and nav.get('remaining',1000)<40 and (nav.get('type')=='arrive') and speed<2
    arrival_since=(now if arrival_since is None else arrival_since) if arriving else None
    if musical_mode:
     arrival_at=arrival.update(now,speed,nav,navfresh,gear=str(sm['carState'].gearShifter),brake=bool(sm['carState'].brakePressed),standstill=bool(sm['carState'].standstill))
     if arrival_at is not None and ending_start is None:
      # Only already-generated music is previewed; no future road inputs.
      with lock:
       frame_at_trigger=frames;past=audio[max(0,position-rate*12):position].copy();queued=audio[position:position+rate*4].copy()
      if section_bank is not None:past,queued=section_bank.context()
      delay,runway=cadence_runway(past,queued,rate) if phrase_runway else (0.,{'method':'immediate baseline','delay_seconds':0.})
      landing=round(delay*rate)
      harmony_source=np.concatenate([past,queued[:landing]]) if landing else past
      if len(harmony_source)>=rate:ending_audio,ending_info=ending_gesture(harmony_source,rate)
      ending_start=max(frame_at_trigger+landing,frames)
      (run/'ending.json').write_text(json.dumps({'route_t':now,'trigger_audio_frame':frame_at_trigger,'audio_frame':ending_start,'harmony':ending_info,'source':arrival.reason,'runway':runway,'actual_runway_seconds':(ending_start-frame_at_trigger)/rate,'generated_outro_heard_seconds':composition.snapshot(frame_at_trigger/rate)['outro_heard_seconds'] if composition else 0.,'generated_outro_job':composition.snapshot(frame_at_trigger/rate)['outro_job'] if composition else None,'cadence_end_audio_s':ending_start/rate+len(ending_audio)/rate}))
    elif arrival_since is not None and now-arrival_since>=3 and arrival_at is None:arrival_at=now
    if songform:
     if not songform.next:
      songform.period=section_bank.clips[section_bank.section][1]['period'];songform.grid_origin=(section_bank.frames-section_bank.position)/rate
     songform.update(frames/rate,state,arrival=ending_start is not None or (navfresh and nav.get('remaining',1e9)<300),nav_approach=navfresh and speed>3 and 0<nav.get('distance',0)<400)
     if songform.next:section_bank.set_plan(songform.next,songform.preparation)
    if composition:composition.update(frames/rate)
    if gestures:
     c=sm['carState'];signal_fresh=bool(sm.valid['carState']) and 0<=(available_ns-sm.logMonoTime['carState'])/1e9<.5
     gestures.update(frames,left=signal_fresh and bool(c.leftBlinker),right=signal_fresh and bool(c.rightBlinker),road=state,nav={**nav,'revision':nav_revision} if navfresh else {},speed=speed,outro=bool(composition and composition.outro_intent),arrived=ending_start is not None,input_ns=available_ns)
    candidate=configuration().get('identity',identity)
    if candidate in styles:identity=candidate
    while identity_queue and frames/rate>=identity_queue[0][0]:playing_identity=identity_queue.pop(0)[1]
    expected_result=root/'generated'/f'result_{job}.json'
    for result in ([expected_result] if expected_result.exists() else []):
     if result.name in seen_jobs:continue
     meta=json.loads(result.read_text());seen_jobs.add(result.name)
     if meta.get('run_id')!=run_id:continue
     quality_source=root/'generated/quality'/str(meta['id'])
     if quality_source.exists():
      destination=run/'quality'/str(meta['id']);destination.parent.mkdir(exist_ok=True);shutil.move(str(quality_source),str(destination))
      meta['quality_artifact_directory']='quality/'+str(meta['id'])
     if meta.get('quality_attempts') is not None:
      with (run/'quality_events.jsonl').open('a') as f:f.write(json.dumps(meta)+'\n')
     if (meta.get('conditioning','base')=='closing') and meta.get('nav_revision')!=nav_revision:
      discarded_jobs.append(meta);inflight=False;continue
     budget_deferred=generation_budget.observe(meta)
     if meta.get('quality_rejected'):
      generation.append(meta);quality_failures+=int(not budget_deferred);quality_hold=True;inflight=False;budget_waiting=True
      if quality_failures>=2:worker_failed=True
      continue
     if meta.get('error'):generation.append(meta);worker_failed=True;inflight=False;continue
     if context_hold_only:
      discarded_jobs.append({**meta,'discard_reason':'accepted hold changed continuation context'});inflight=False;continue
     pending[result.name]=(meta,load_pool.submit(load_audio,meta))
    for key,(meta,future) in list(pending.items()):
     if not future.done():continue
     if (meta.get('conditioning','base')=='closing') and meta.get('nav_revision')!=nav_revision:
      discarded_jobs.append(meta);inflight=False;del pending[key];continue
     w=future.result()
     if section_bank is not None:section_bank.update(meta.get('conditioning','verse') if meta.get('conditioning') in section_bank.clips else 'verse',w,meta['id'])
     if composition:composition.generated(meta,frames/rate+(len(audio)-position)/rate)
     meta['usable_new_seconds']=len(w)/rate-2;identity_queue.append((frames/rate+(len(audio)-position)/rate-2,meta.get('identity',identity)));append(w,overlap=2.,match=musical_mode and not rolling_mode)
     ending_audio,ending_info=ending_gesture(w,rate) if ending_start is None else (ending_audio,ending_info)
     quality_failures=0;quality_hold=False;holding=False;budget_waiting=False
     lastlatent=meta['latents'];generation.append(meta);inflight=False;del pending[key]
    buffered=(len(audio)-position)/rate
    if composer=='ace' and not (root/'generated/worker_ready').exists():worker_failed=True;inflight=False
    if composer=='ace' and not inflight and not worker_failed and buffered<generation_budget.required_seconds:budget_waiting=True
    if composer=='ace' and ending_start is None and ((buffered<max(40,generation_budget.required_seconds+2) and (quality_hold or worker_failed or budget_waiting)) or (inflight and buffered<20)):
     # Only already accepted material; keep the exact source tail for the next latent prefix.
     from safe_extension import extend_tail
     hold_started=time.monotonic()
     extension,extension_meta=extend_tail(audio,rate)
     # Like normal continuations, build the immutable replacement outside the
     # callback lock. The final array-reference assignment is atomic; holding
     # this lock through concatenate can exceed an audio block on restored CPUs.
     append(extension,overlap=2.)
     if not extension_meta['preserves_latest_context']:worker_failed=True;context_hold_only=True
     holding=True
     safe_extensions.append({**extension_meta,'construction_seconds':time.monotonic()-hold_started,'audio_s':frames/rate,'buffer_before':buffered,'reason':'worker_failed' if worker_failed else ('quality_rejected' if quality_hold else ('generation_budget_reserve' if budget_waiting else 'inflight_deadline_reserve'))})
     buffered=(len(audio)-position)/rate;quality_hold=False
    if buffered<2:
     # Repeat the current generated tail so the queued continuation still shares its context.
     append(audio[-min(len(audio),rate*8):].copy(),overlap=2.);fallbacks+=1;buffered=(len(audio)-position)/rate
    with lock:
     if position>rate*90:audio=audio[position-rate*10:];position=rate*10
    if inflight and time.monotonic()-job_started>(110 if composer=='ace' else 50):worker_failed=True
    if not os.environ.get('ROADSCORE_NO_GENERATION') and buffered<=(90 if composer=='ace' else 30) and ending_start is None and not inflight and not worker_failed and (composer!='ace' or buffered>=generation_budget.required_seconds) and (root/'generated/worker_ready').exists():
     style='base'
     if navfresh and nav.get('remaining',1e9)<500 and nav.get('eta',1e9)<60:style='closing'
     elif navfresh and speed>3 and 30<nav.get('distance',0)/speed<60:style='approach'
     cache=root/f'assets/conditioning_{identity}_{style}.npy' if identity!='legacy' else root/f'assets/conditioning_{style}.npy'
     if composer!='ace' and not cache.exists():style='base'
     phase,mix=trajectory(len(generation),style)
     if config.get('arrangement',False) and (identity=='horizon_drive' or styles.get(identity,{}).get('trajectory')):
      if style!='closing':
       sequence=styles.get(identity,{}).get('trajectory',['explore','develop','build','peak','release']);phase=sequence[len(generation)%len(sequence)];style=phase
      mix=None
     if songform:
      style=songform.next['section'] if songform.next else songform.section;phase=style;mix=None
     if composition:
      style=composition.choose(frames,rate,nav if navfresh else {},speed,buffered);phase=style;mix=None
     generation_index+=1
     job+=1;req={'id':job,'run_id':run_id,'identity':identity,'previous_identity':last_requested_identity,'source_end':usable_frames,'seconds_total':120 if rolling_mode else (30 if style=='closing' else (120 if musical_mode else 30)),'conditioning':style,'nav_revision':nav_revision,'latents':lastlatent,'cutoff_ns':available_ns,'input_times':{k:v for k,v in sm.logMonoTime.items() if k!='selfdriveState'},'play_at_audio_s':frames/rate+buffered,'route_t':now,'intent':state['phase'],'nav':nav if navfresh else {},'trajectory':phase,'conditioning_mix':mix if rolling_mode else None,**(rolling_anchors[identity] if rolling_mode and composer!='ace' else {})}
     if composition:
      req.update(anchor_frames=0,context_frames=44,seconds_total=30 if style=='closing' else 120)
     if base_seed is not None:req.update(seed=sample_seed(base_seed,'continuation',generation_index-1),generation_seed=base_seed,generation_index=generation_index-1)
     if composer=='ace':
      req={k:v for k,v in req.items() if k not in ('source_end','seconds_total','context_frames','anchor_frames','conditioning_mix')}
      req.update(composer='ace',profile=ace_profile,buffer_seconds=buffered,playback_deadline_monotonic=time.monotonic()+buffered)
     with (run/'jobs.jsonl').open('a') as audit:audit.write(json.dumps(req)+'\n')
     f=root/'generated/request.tmp';f.write_text(json.dumps(req));f.replace(root/'generated/request.json');inflight=True;budget_waiting=False;job_started=time.monotonic();last_requested_identity=identity
    snapshot={'composer':composer,'render_mode':render_mode,'readiness':'DEGRADED' if worker_failed or quality_failures or holding else 'READY','profile':ace_profile if composer=='ace' else None,'safe_extensions':len(safe_extensions),'holding_accepted_music':holding,'quality_failures':quality_failures,'style':PROFILES[ace_profile]['name'] if composer=='ace' else styles.get(identity,{}).get('name',identity),'section':'OUTRO' if ending_start is not None else 'CONTINUATION','identity':identity,'playing_identity':playing_identity,'musical_mode':musical_mode,'route':clock['route'],'route_t':now,'elapsed':frames/rate,'kind':state.get('kind','curve'),'phase':state['phase'],'amount':state['amount'],'lead':state['lead'],'activation':state['activation'],'predicted_peak':state['predicted_peak'],'strength':state['strength'],'predicted_turn_radians':state.get('predicted_turn_radians'),'detector':state.get('detector'),'qualified_since':state.get('qualified_since'),'command_wall':time.monotonic(),'speed':speed,'steering':float(sm['carState'].steeringAngleDeg),'model_age':(sm.logMonoTime['modelV2']-m.timestampEof)/1e9,'source_cutoff_ns':available_ns,'model_mono_ns':sm.logMonoTime['modelV2'],'buffered':buffered,'fallbacks':fallbacks,'underflows':underflows,'job_inflight':inflight,'generation_elapsed_seconds':max(0.,time.monotonic()-job_started) if inflight else None,'worker_failed':worker_failed,'completed_jobs':sum(not j.get('error') and not j.get('quality_rejected') for j in generation),'nav':nav,'nav_revision':nav_revision,'discarded_jobs':len(discarded_jobs),'arrival_at':arrival_at,'replay_late':clock['late']}
    if presentation is not None:
     engagement_on,engagement_fresh=engagement_active(engagement[1],engagement[0],engagement[2],engagement[4],engagement[3],time.monotonic())
     snapshot.update(presentation.snapshot(presentation_config,engagement_on,engagement_fresh))
    if shaker is not None:snapshot['signal_shaker']=shaker.snapshot()
    if songform:snapshot.update(songform.snapshot())
    if composition:snapshot.update(composition.snapshot(frames/rate))
    if gestures:snapshot.update(gestures.status())
    trace.write(json.dumps(snapshot)+'\n');f=run/'status.tmp';f.write_text(json.dumps(snapshot));f.replace(run/'status.json')
   if time.monotonic()-last_progress>15:raise RuntimeError('Replay model input stalled')
finally:
 audio_started=False
 if apex is not None:(run/'core_apex_events.json').write_text(json.dumps(apex.events,indent=2))
 if shaker is not None:(run/'shaker_events.json').write_text(json.dumps({'sequences':shaker.events,'pulse_frames':shaker.pulse_frames,'settings':shaker.snapshot()},indent=2))
 if gestures:(run/'gestures.json').write_text(json.dumps({'events':gestures.events,'bpm':gestures.bpm,'source_derived':True,'tonal_key_not_inferred':True},indent=2))
 if composition:(run/'composition.json').write_text(json.dumps({'events':composition.events,**composition.snapshot(frames/rate)},indent=2))
 if songform:
  (run/'song_form.json').write_text(json.dumps({'decisions':songform.events,'waveform_events':section_bank.events,'experimental':True,'human_listening_verified':False},indent=2))
 (run/'gc_events.json').write_text(json.dumps(gc_events));gc.callbacks.remove(gc_audit);gc.unfreeze();load_pool.shutdown();stop.set();record_thread.join(timeout=5);trace.close();stream.close()
 if export:export.close()
 (run/'summary.json').write_text(json.dumps({'audio_seconds':frames/rate,'fallbacks':fallbacks,'underflows':underflows,'generation':generation,'safe_extensions':safe_extensions,'emergency_fallbacks':fallbacks,'accepted_music_holds':len(safe_extensions),'total_fallback_events':fallbacks+len(safe_extensions),'quality_failures':quality_failures,'discarded_jobs':discarded_jobs,'arrival_at':arrival_at},indent=2))
 print('Audio complete',frames/rate,'fallbacks',fallbacks,'underflows',underflows,flush=True)
