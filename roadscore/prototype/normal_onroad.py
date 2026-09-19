from device_target import device_target
from composer_choice import choice
"""Private external normal-onroad launcher. Existing replay discovers arbitrary routes.
No RoadScore event annotations, route allowlist, custom camera drawing, or modeld.
"""
import argparse,os,subprocess,time,signal,shlex,json
from pathlib import Path
from clock_sync import measure
from receiver_environment import assignments as receiver_assignments,resolve_compute
from presentation_policy import select_launch
from hook_launch import start_planner
from composition_launch import configure as configure_composition
from launch_health import check_children, describe_failure, write_failure
from session_seed import select_session, seed_argument, seed_environment, remote_assignments
R=Path(__file__).resolve().parents[1]
native=Path('/TICI').exists()
def interrupt(*_):raise KeyboardInterrupt
signal.signal(signal.SIGTERM,interrupt)
p=argparse.ArgumentParser();p.add_argument('--roadscore-seed',type=seed_argument,help='Reproduce an ACE session; normal launches choose a fresh seed');p.add_argument('--render-mode',choices=['current','gold-core'],default=None,help='ACE rendering mode');p.add_argument('--roadscore-presentation',choices=['conservative-v2','conservative-v1','off','frozen']);p.add_argument('route',nargs='?');p.add_argument('--routeid');p.add_argument('--roadscore',action='store_true',required=True);p.add_argument('--replay',action='store_true',help='Play recorded final score without Chestnut');p.add_argument('--score-archive',type=Path,help='Imported local archive for --replay');p.add_argument('--start',type=int,default=None);p.add_argument('--duration',type=float,default=float('inf'),help='Optional duration limit; normally replay to route EOF');p.add_argument('--audible',action='store_true',help='Compatibility flag; output is audible by default outside automated sessions');p.add_argument('--muted',action='store_true');p.add_argument('--no-overlay',action='store_true');p.add_argument('--capture-ui',action='store_true',help='Record the normal UI internally without speaker output');p.add_argument('--audio-device',default=None,help='Development host output device; default is the system output');p.add_argument('--transport-only',action='store_true');p.add_argument('--headless',action='store_true');p.add_argument('--runtime',type=Path,default=Path('/data/openpilot') if native else Path(os.environ.get('ROADSCORE_RUNTIME','/Users/dominickthompson/starpilot/.host_runtime/darwin/worktree')));p.add_argument('--bench',default=device_target());p.add_argument('--composer',choices=['sa3','ace'],default=choice(),help='ACE Prism is the event default; SA3 is an explicit fallback');p.add_argument('--profile',choices=['prism','aurora'],default='prism');a=p.parse_args()
explicit_start=a.start
if a.render_mode=='gold-core' and a.composer!='ace':raise SystemExit('Gold core requires ACE')
if a.roadscore_seed is not None and (a.replay or a.composer!='ace'):raise SystemExit('--roadscore-seed applies only to fresh ACE generation')
session=None
if not a.replay and a.composer=='ace':
 judging_seed=os.environ.get('ROADSCORE_GENERATION_SEED') if os.environ.get('ROADSCORE_SEED_ORIGIN')=='judging-route' and a.roadscore_seed is not None else None
 session=select_session(a.roadscore_seed,judging_seed=judging_seed)
presentation=select_launch(a.composer,a.profile,replay=a.replay,judging=bool(session and session['seed_origin']=='judging-route'),render_mode=a.render_mode,policy=a.roadscore_presentation)
a.render_mode=presentation['render_mode']
composition_environment=os.environ.copy();composition_environment['ROADSCORE_ACE_PROFILE']=a.profile
composition_policy=configure_composition(session,a.replay,a.composer,native=native,transport_only=a.transport_only,environ=composition_environment,root=R)
from settings import Settings,resolve_route
a.routeid=resolve_route(p,a.route,a.routeid)
from route_favorites import resolve_favorite
try:a.routeid,favorite_start=resolve_favorite(a.routeid)
except (ValueError,KeyError) as error:p.error(str(error))
if a.start is None:a.start=favorite_start
settings=Settings(mode='stored' if a.replay else 'generate',muted=a.muted,overlay=not a.no_overlay,output_device=a.audio_device)
a.audible=not settings.effective_muted(a.headless)
rt=a.runtime;py=Path('/usr/local/venv/bin/python') if native else rt/'.venv/bin/python3';replay=R/'native_build/replay' if native else rt/'tools/replay/replay'
for path in [py,replay,rt/'selfdrive/ui/ui.py']:
 if not path.exists():raise SystemExit(f'Missing existing normal onroad runtime: {path}')
if native:
 from native_ownership import verify_offroad
 verify_offroad()
out=R/'results'/('normal_'+str(int(time.time())));out.mkdir();env=composition_environment.copy();env.update(PYTHONDONTWRITEBYTECODE='1',ZMQ='1',OPENPILOT_ZMQ_NAMESPACE='roadscore-native-'+str(os.getpid()),PARAMS_ROOT=str(out/'params'),BASEDIR=str(rt),NOBOARD='1',SIMULATION='1',SKIP_FW_QUERY='1',BIG='0',SP_ALLOW_DESKTOP_FAKE_WIFI='0',SP_ALLOW_DESKTOP_FAKE_BLUETOOTH='0',SP_ONROAD_NAV_DEMO='0',SP_ONROAD_CEM_DEMO='0')
if session:
 env.update(seed_environment(session));(out/'session_seed.json').write_text(json.dumps(session,indent=2));print('RoadScore session seed:',session['generation_seed'],'('+session['seed_origin']+')',flush=True)
else:
 env.pop('ROADSCORE_GENERATION_SEED',None);env.pop('ROADSCORE_SEED_ORIGIN',None)
compute=resolve_compute(env,composer=a.composer,replay=a.replay,judging=bool(session and session['seed_origin']=='judging-route'),transport_only=a.transport_only)
(out/'compute_settings.json').write_text(json.dumps(compute,indent=2))
if session:print('Requested Chestnut cap:',compute['requested_power_limit_watts'],'W; TC_OPT:',compute['tc_opt'],'(actual readback recorded separately)',flush=True)
(out/'settings.json').write_text(json.dumps({**settings.snapshot(a.headless),'composer':a.composer,'profile':a.profile,'render_mode':a.render_mode,'presentation_policy':presentation['policy'],'composition_policy':composition_policy,**(session or {})},indent=2))
env['ROADSCORE_RENDER_MODE']=a.render_mode
env['ROADSCORE_PRESENTATION_POLICY']=presentation['policy']
env['ROADSCORE_COMPOSITION_POLICY']=composition_policy
env['ROADSCORE_COMPOSER']=a.composer
env['ROADSCORE_ACE_PROFILE']=a.profile
env['ROADSCORE_OVERLAY_CAPTURE']=str(out/'overlay.png')
env['ROADSCORE_STATUS_FILE']=str(out/'roadscore_status.json')
initial_display={'readiness':'Preparing','composer':a.composer,'profile':a.profile if a.composer=='ace' else None,'render_mode':a.render_mode,'style':a.profile.title() if a.composer=='ace' else settings.style}
if a.replay:initial_display.update(style='Stored score',section='ARCHIVED SCORE',compute='none')
(out/'roadscore_status.json').write_text(json.dumps(initial_display))
env['ROADSCORE_OVERLAY']='1' if settings.overlay else '0'
env['ROADSCORE_FORCE_MUTE']='0' if a.audible else '1'
env['ROADSCORE_ORIGIN_FILE']=str(out/'replay_origin.json')
env['ROADSCORE_UI_AUDIT']=str(out/'ui_audit.jsonl');env['PWD']=str(rt)
env.pop('OPENPILOT_PREFIX',None);
if native:
 env.pop('ZMQ',None);env['OPENPILOT_PREFIX']='roadscore_replay';env.pop('PARAMS_ROOT',None)
 Path('/dev/shm/msgq_roadscore_replay').mkdir(exist_ok=True)
env['PYTHONPATH']=':'.join(map(str,[rt,rt/'starpilot/third_party',*rt.glob('*_repo')]));env['PATH']=str(py.parent)+':/opt/homebrew/bin:'+env.get('PATH','')
env['PYTHONPATH']+=':'+('/data/roadscore-feasibility/venv/lib/python3.12/site-packages' if native else str(R/'.analysis-venv/lib/python3.12/site-packages'))
from route_library import local_source
local=local_source(a.routeid)
services='roadEncodeIdx,wideRoadEncodeIdx,driverEncodeIdx,modelV2,controlsState,onroadEvents,liveCalibration,radarState,deviceState,pandaStates,carParams,driverMonitoringState,carState,driverStateV2,roadCameraState,wideRoadCameraState,managerState,selfdriveState,longitudinalPlan,gpsLocationExternal,mapdOut,carOutput,carControl,liveParameters,starpilotCarState,starpilotPlan,starpilotRadarState,starpilotSelfdriveState,liveTracks,liveDelay,liveTorqueParameters,navInstruction,navRoute,livePose'
score=None;stored_limit=None
if a.score_archive and not a.replay:p.error('--score-archive requires --replay')
if a.replay:
 if not native and not local:raise SystemExit('Archived Mac replay requires a local route cache; no network fetch is started')
 from score_archive import latest
 from stored_replay_policy import replay_archive
 try:score=a.score_archive.resolve() if a.score_archive else latest(a.routeid)
 except FileNotFoundError:raise SystemExit('No stored RoadScore exists for this route. Generate a score first.')
 a.start,stored_limit=replay_archive(score,a.routeid,explicit_start)
args=[a.routeid,'--allow',services,'--start',str(a.start),'--no-loop','--headless','--cache','2']
if local:args+=['--data_dir',str(local)]
if native:args+=['--no-hw-decoder']
display=None;children=[];named_children={};failure=None;logs=[];launch_started=time.monotonic()
print(('Preparing stored score replay; no generation. ' if a.replay else ('Preparing ACE replay; first preparation may take 10–15 minutes. ' if a.composer=='ace' else 'Preparing RoadScore replay; cold preparation can take 2–3 minutes. '))+('Host speaker enabled.' if a.audible else 'Muted host capture.'),flush=True)
def launch(cmd,name,**kw):
 f=(out/(name+'.log')).open('wb');logs.append(f);c=subprocess.Popen(cmd,stdout=f,stderr=f,env=env,cwd=rt,start_new_session=True,**kw);children.append(c);named_children[name]=c;return c
try:
 if not native and Path('/usr/bin/caffeinate').exists():launch(['/usr/bin/caffeinate','-i'],'wake_assertion')
 if composition_policy=='hook-v2' and not a.transport_only:start_planner(launch,env,out,R,a.bench,native=native)
 # Native parameter seeding reads metadata; it does not feed future route data to RoadScore.
 subprocess.run([str(py),str(rt/'tools/replay/onroad_config.py'),'seed',*args],env=env,cwd=rt,check=True,stdout=(out/'seed.log').open('w'),stderr=subprocess.STDOUT)
 if native and not a.headless:
  from native_ownership import DisplayOwner
  display=DisplayOwner(R);display.acquire()
 if not a.headless:
  if a.capture_ui:env.update(RECORD='1',RECORD_OUTPUT=str(out/'normal_ui.mp4'),ROADSCORE_CAPTURE_TIMING='1')
  ui=launch([str(py),str(R/'prototype/normal_ui_audit.py')],'ui')
  env.pop('RECORD',None);env.pop('RECORD_OUTPUT',None)
 if a.replay:
  audio_py=py
  sender=launch([str(audio_py),str(R/'prototype/stored_score.py'),'--score',str(score),'--out',str(out),'--duration',str(a.duration)]+(['--audible'] if a.audible else [])+(['--device',a.audio_device] if a.audio_device else []),'stored_audio')
  audio_host=None;receiver=None
  deadline=time.monotonic()+20
  while not (out/'stored_ready').exists():
   if sender.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Stored audio failed; see stored_audio.log')
   time.sleep(.1)
 else:
  remote_policy=receiver_assignments(env)
  receiver_command=(['env','-u','ZMQ','ROADSCORE_AUDIBLE='+('1' if a.audible else '0'),'bash',str(R/'prototype/native_receiver.sh'),a.routeid] if native else ['ssh',a.bench,(remote_assignments(session) if session else '')+remote_policy+'ROADSCORE_RENDER_MODE='+a.render_mode+' ROADSCORE_COMPOSER='+a.composer+' ROADSCORE_ACE_PROFILE='+a.profile+' ROADSCORE_PCM_RETURN=1 '+('ROADSCORE_NO_GENERATION=1 ' if a.transport_only else '')+'bash /data/roadscore/prototype/native_receiver.sh '+shlex.quote(a.routeid)])
  receiver=launch(receiver_command,'receiver',stdin=subprocess.PIPE)
  deadline=time.monotonic()+(1560 if a.composer=='ace' else 420)
  while b'BRIDGE_READY' not in (out/'receiver.log').read_bytes():
   check_children(named_children,remote=not native,include_receiver=True)
   if receiver.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Bench receiver failed: '+(out/'receiver.log').read_text())
   time.sleep(.2)
  audio_host=None
  if not native:
   (out/'clock_sync.json').write_text(json.dumps(measure(a.bench),indent=2))
   audio_host=launch([str(R/'.analysis-venv/bin/python'),str(R/'prototype/host_audio.py'),'--bench',a.bench,'--out',str(out),'--clock',str(out/'clock_sync.json')]+(['--audible'] if a.audible else [])+(['--device',a.audio_device] if a.audio_device else []),'host_audio')
   deadline=time.monotonic()+20
   while not (out/'host_audio_ready').exists():
    check_children(named_children,remote=not native,include_receiver=True)
    if audio_host.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Host audio failed; see host_audio.log')
    time.sleep(.1)
  f=(out/'sender.log').open('wb');logs.append(f)
  sender=subprocess.Popen([str(py),str(R/'prototype/replay_bridge.py'),'send','--seconds',str(a.duration)],stdout=receiver.stdin,stderr=f,env=env,cwd=rt,start_new_session=True);children.append(sender);receiver.stdin.close()
  deadline=time.monotonic()+15
  while b'BRIDGE_SUBSCRIBED' not in (out/'sender.log').read_bytes():
   check_children(named_children,remote=not native,include_receiver=True)
   if sender.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Replay subscriber failed')
   time.sleep(.1)
 if a.replay:(out/'roadscore_status.json').write_text(json.dumps({'readiness':'READY','style':'Stored score','section':'ARCHIVED SCORE','compute':'none'}))
 player=launch([str(replay),*args],'replay');started=time.monotonic();print('Normal replay running; '+('host speaker enabled' if a.audible else 'bench muted')+'. Output:',out,flush=True)
 from replay_end import ReplayEnd
 end_watch=ReplayEnd();end_reason='requested duration'
 state_path=Path('/tmp/replay_state_'+env.get('OPENPILOT_PREFIX','default')+'.json')
 while sender.poll() is None:
  check_children(named_children,remote=not native,include_receiver=True,allow_clean_receiver=True)
  if receiver is not None and receiver.poll() not in (None,0):raise RuntimeError('RoadScore receiver failed; see receiver.log')
  if native and not a.replay:
   try:(out/'roadscore_status.json').write_text((R/'results/current/status.json').read_text())
   except OSError:pass
  try:
   native_state=json.loads(state_path.read_text())
   if end_watch.observe(native_state,(out/'replay.log').read_text(),time.monotonic()):
    end_reason='native final segment exhausted'
    if not a.replay:break
  except (FileNotFoundError,json.JSONDecodeError):pass
  if player.poll() is not None and time.monotonic()-started>2:
   if player.returncode:raise RuntimeError('Native replay failed; see replay.log')
   if not a.replay:break
  if a.replay and time.monotonic()-started>stored_limit:raise TimeoutError('Stored score did not finish within its recorded extent')
  if audio_host is not None and audio_host.poll() is not None:raise RuntimeError('Host PCM stream stopped; see host_audio.log')
  if not a.headless and ui.poll() is not None:raise RuntimeError('Existing normal UI exited; see ui.log')
  if time.monotonic()-started>a.duration+90:raise TimeoutError('No progressing replay messages')
  time.sleep(.5)
 if sender.poll() not in [None,0]:raise RuntimeError('Replay sender failed')
 if sender.poll() is None:os.killpg(sender.pid,signal.SIGTERM);sender.wait(timeout=5)
 (out/'launch.json').write_text(json.dumps({**(session or {}),'render_mode':a.render_mode,'route':a.routeid,'mode':'stored-score' if a.replay else 'fresh-generation','host':'comma' if native else 'development host','compute':'none' if a.replay else ('local Chestnut' if native else 'remote Chestnut'),'local_cache':str(local) if local else None,'native_replay_args':args,'end_reason':end_reason,'duration_wall':time.monotonic()-started,'startup_seconds':started-launch_started,'headless':a.headless,'ui':'existing selfdrive/ui/ui.py','muted':not a.audible},indent=2))
 if not a.replay:
  receiver.wait(timeout=35)
  if not (out/'replay_origin.json').exists():raise RuntimeError('Replay delivered no model clock; refusing empty score')
  if audio_host is not None:
   audio_host.wait(timeout=15)
   if audio_host.returncode:raise RuntimeError('Host audio failed')
  if receiver.returncode!=0:raise RuntimeError('Bench replay receiver failed')
  if not native:(out/'clock_sync_after.json').write_text(json.dumps(measure(a.bench),indent=2))
  if 'BRIDGE_MESSAGES 0' in (out/'sender.log').read_text():raise RuntimeError('No replay messages received')
  if native:
   subprocess.run([str(py),str(R/'prototype/archive_native.py'),str(out),a.routeid,str(a.start)],env=env,cwd=rt,check=True)
  if not native:
   # Preserve generated decisions with the exact host presentation audio.
   for filename in ['summary.json','jobs.jsonl','boundaries.jsonl','ending.json','bridge.json','trace.jsonl','runtime_manifest.json','song_form.json','gesture_grid.json','gestures.json','composition.json','quality_events.jsonl','shaker_grid.json','shaker_events.json','core_apex_events.json','dry.wav','audio_blocks.jsonl']:
    subprocess.run(['scp',a.bench+':/data/roadscore/results/current/'+filename,str(out/filename)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=filename in ('dry.wav','audio_blocks.jsonl'))
   subprocess.run(['scp','-r',a.bench+':/data/roadscore/results/current/quality',str(out/'quality')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   if a.composer=='ace':subprocess.run(['scp',a.bench+':/data/roadscore/generated/ace_link.jsonl',str(out/'ace_link.jsonl')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   from score_archive import archive
   archived=archive(a.routeid,out,a.start);print('Score archived:',archived,flush=True)
except Exception as error:
 try:
  check_children(named_children,remote=not native,include_receiver=True,allow_clean_receiver=True)
 except Exception as child_error:
  error=child_error
 failure=describe_failure(error)
 write_failure(out/'roadscore_status.json',failure)
 raise
finally:
 for c in reversed(children):
  if c.poll() is None:
   os.killpg(c.pid,signal.SIGTERM)
   try:c.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(c.pid,signal.SIGKILL);c.wait()
 if failure:write_failure(out/'roadscore_status.json',failure)
 if display:display.close()
 for f in logs:f.close()
 print('Replay processes stopped. Worker ownership remains with its supervisor.',flush=True)
if a.capture_ui and not native and (out/'normal_ui.mp4').exists():
 subprocess.run([str(R/'.analysis-venv/bin/python'),str(R/'prototype/synchronize_capture.py'),str(out)],check=True)
 print('Synchronized muted capture:',out/'synchronized.mp4',flush=True)
