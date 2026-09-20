"""Local native replay + prepared ACE core + interactive presentation, without inference."""
import argparse
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from paired_demo_controls import DISCLOSURE, GalaxyPeer, PairedDemoControls
from replay_sync import ReplayFollower, start_deadline, validate_follow_options

HERE = Path(__file__).resolve().parent


def write_json(path, value):
  temporary = Path(str(path)+'.tmp')
  temporary.write_text(json.dumps(value))
  temporary.replace(path)


def cleanup_children(children, logs):
  # A repeated stop must not interrupt cleanup of separately owned groups.
  signal.signal(signal.SIGTERM,signal.SIG_IGN)
  signal.signal(signal.SIGINT,signal.SIG_IGN)
  for child in reversed(children):
    if child.poll() is None:
      try:os.killpg(child.pid,signal.SIGTERM)
      except ProcessLookupError:pass
      except OSError as error:print('Child termination failed:',error,flush=True)
  deadline=time.monotonic()+5.
  for child in reversed(children):
    try:
      child.wait(timeout=max(0.,deadline-time.monotonic()))
    except subprocess.TimeoutExpired:
      try:os.killpg(child.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      except OSError as error:print('Child force-stop failed:',error,flush=True)
      try:child.wait(timeout=2.)
      except subprocess.TimeoutExpired:print('Child could not be reaped:',child.pid,flush=True)
      except (OSError,ChildProcessError) as error:print('Child reap failed:',error,flush=True)
    except (OSError,ChildProcessError) as error:print('Child reap failed:',error,flush=True)
  for log in logs:
    try:log.close()
    except OSError:pass


def control_server(project, out, shared, port, forwarder=None, *, follow_peer=False):
  spec = importlib.util.spec_from_file_location('showcase_galaxy', project/'starpilot/system/the_galaxy/roadscore.py')
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  operator_root = out/'operator'
  (operator_root/'results').mkdir(parents=True)
  (operator_root/'results/current').symlink_to(out)
  operator = module.Operator(operator_root, device=False, offroad=lambda: True)
  control_lock = threading.Lock()
  sequence = 0
  follower_stop = threading.Event()
  following = dict(enabled=bool(follow_peer and forwarder),status='waiting',error=None,snapshot=None)
  local_session = None
  last_mirror_write = None
  paired = dict(enabled=forwarder is not None, sequence=0, request=None, music_video_synchronized=False, disclosure=DISCLOSURE,
                targets={'comma':dict(status='idle' if forwarder else 'disabled',acknowledged=False,applied=False,error=None)})
  def paired_snapshot(demo):
    with control_lock:result = {**paired, 'targets':dict(paired['targets']), 'following':dict(following)}
    snapshot = result['following']['snapshot']
    if snapshot and time.monotonic()-snapshot['received_wall']>1.5:
      result['following'].update(status='stale',error='peer_status_stale',snapshot=None)
    result['targets']['mac'] = dict(status='ready' if demo['available'] else 'unready',
                                   mode=demo['mode'],signal_mode=demo['signal_mode'],acknowledged=False,applied=False)
    request = result['request']
    if request:
      applied = demo['available'] and demo['session_id'] == request['session_id'] and demo[request['field']] == request['value']
      result['targets']['mac'].update(acknowledged=True,applied=bool(applied),action=request['action'],value=request['value'])
    return result
  def failed_peer():
    return dict(targets={'comma':dict(status='failed',acknowledged=False,applied=False,error='peer_submission_failed')})
  def received(future, request_sequence):
    try:result = future.result()
    except Exception:result = failed_peer()
    with control_lock:
      # A slow result cannot replace the status of a newer button action.
      if sequence == request_sequence:paired['targets'] = result['targets']
  def follow_once():
    nonlocal local_session,last_mirror_write
    with control_lock:before=sequence
    try:
      snapshot=forwarder.read_status()
      with control_lock:
        if follower_stop.is_set():return
        if sequence != before:
          following.update(status='pending',error='peer_action_in_progress',snapshot=None);return
        demo=operator.demo_status()
        if not demo['available']:raise ValueError('local_replay_unready')
        local_route=demo.get('route') or module.read_json(out/'status.json').get('route')
        if snapshot['route']!=local_route:raise ValueError('peer_route_mismatch')
        if local_session is None:local_session=demo['session_id']
        elif demo['session_id']!=local_session:raise ValueError('local_session_changed')
        signature=(snapshot['session_id'],local_session,snapshot['mode'],snapshot['signal_mode'],sequence)
        matching=all(demo[field]==snapshot[field] for field in ('mode','signal_mode'))
        if not matching and last_mirror_write!=signature:
          # Write only local replay commands with the Mac's own session. This
          # path never calls submit(), so following Galaxy cannot feed back.
          for field in ('mode','signal_mode'):
            if demo[field]!=snapshot[field]:operator.demo_engagement({'session_id':local_session,field:snapshot[field]},field)
          last_mirror_write=signature
        if matching:last_mirror_write=None
        following.update(status='following' if matching else 'applying',error=None,snapshot=snapshot)
    except Exception as error:
      known={'peer_action_in_progress','peer_session_changed','local_session_changed','local_replay_unready',
             'peer_not_ready_for_replay','invalid_peer_session','forwarder_disabled','invalid_peer_route',
             'peer_route_changed','peer_route_mismatch'}
      reason=str(error) if str(error) in known else 'peer_timeout' if isinstance(error,TimeoutError) else 'peer_status_unavailable'
      with control_lock:following.update(status='paused',error=reason,snapshot=None)
  def follow():
    while not follower_stop.is_set():
      follow_once()
      follower_stop.wait(.25)
  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):pass
    def send_json(self, value, status=200):
      data = json.dumps(value).encode()
      self.send_response(status)
      self.send_header('Content-Type', 'application/json')
      self.send_header('Content-Length', str(len(data)))
      self.send_header('Cache-Control', 'no-store')
      self.end_headers();self.wfile.write(data)
    def do_GET(self):
      if self.path == '/status':
        demo = operator.demo_status()
        self.send_json({'demo': demo, **shared, 'paired_controls':paired_snapshot(demo)})
      elif self.path == '/':
        data = (HERE/'mac_showcase.html').read_bytes()
        self.send_response(200);self.send_header('Content-Type', 'text/html; charset=utf-8');self.send_header('Content-Length', str(len(data)));self.end_headers();self.wfile.write(data)
      else:self.send_error(404)
    def do_POST(self):
      nonlocal sequence
      if self.path != '/control':self.send_error(404);return
      allowed_hosts = {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
      if (self.headers.get('Host') not in allowed_hosts
          or not module.control_origin_allowed(self.headers.get('Origin'), self.headers.get('Host'), 'http', self.headers.get('Sec-Fetch-Site'))):
        self.send_json({'error':'Cross-origin controls are not allowed'},403);return
      try:
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 1024:raise ValueError('Invalid control size')
        data = json.loads(self.rfile.read(length))
        field = 'signal_mode' if 'signal_mode' in data else 'mode'
        future = None
        with control_lock:
          # Serialize local writes with their submissions. The peer is optional;
          # waiting for its network/status response never holds this lock.
          result = operator.demo_engagement(data, field)
          sequence += 1;request_sequence = sequence
          action = 'demo_signal' if field == 'signal_mode' else 'demo_engagement'
          paired.update(sequence=sequence,request=dict(action=action,field=field,value=data[field],session_id=data['session_id']))
          if forwarder is not None:
            try:
              future = forwarder.submit(action, data[field])
              paired['targets'] = {'comma':dict(status='pending',action=action,value=data[field],
                                               acknowledged=False,applied=False,error=None)}
            except Exception:paired['targets'] = failed_peer()['targets']
        if future is not None:future.add_done_callback(lambda completed:received(completed,request_sequence))
        self.send_json({**result,'control_sequence':request_sequence})
      except (ValueError, TypeError) as error:self.send_json({'error':str(error)},400)
  class ControlServer(ThreadingHTTPServer):
    def server_close(self):
      follower_stop.set()
      if forwarder is not None:forwarder.close()
      super().server_close()
  server = ControlServer(('127.0.0.1',port),Handler)
  def following_snapshot():
    with control_lock:return following['snapshot']
  server.following_snapshot = following_snapshot
  threading.Thread(target=server.serve_forever,daemon=True).start()
  if following['enabled']:threading.Thread(target=follow,name='galaxy-control-follower',daemon=True).start()
  return server


def audio_worker(a):
  import numpy as np
  import sounddevice as sd
  from cereal import messaging
  from core import Conductor
  from demo_engagement import DemoEngagement
  from operator_output import PresentationDelay
  from prepared_core import load_archive, initial_frame, PreparedPresentation
  from prepared_clock import PreparedClock
  from stream_clock_bridge import StreamClockBridge
  audio, rate, meta = load_archive(a.score_archive, a.route)
  processor = PreparedPresentation(a.score_archive, rate)
  playback_clock = PreparedClock(rate)
  sync = ReplayFollower(a.route,meta['first_model_ns'],duration=len(audio)/rate) if a.follow_playhead else None
  prefix = os.environ.get('OPENPILOT_PREFIX','')
  if sync is not None and prefix != 'roadscore-showcase-'+os.environ['ROADSCORE_SHOWCASE_SESSION']:
    raise ValueError('Playhead following requires this isolated Mac replay prefix')
  replay_state_path = Path('/tmp/replay_state_'+prefix+'.json')
  replay_command_path = Path('/tmp/replay_cmd_'+prefix+'.json')
  session = os.environ['ROADSCORE_SHOWCASE_SESSION']
  controls = DemoEngagement(a.out, session, 'replay')
  delay = PresentationDelay(a.presentation_root or a.out,output_provider=lambda: {'id':a.output_identity} if a.output_identity else None)
  sm = messaging.SubMaster(['modelV2','carState','selfdriveState'],poll='modelV2')
  conductor = Conductor(handoff=True)
  staged = None
  plan_path = a.curve_plan
  if plan_path is not None:
    from demo_curve_plan import ReplayCurvePlan
    value = json.loads(plan_path.read_text())
    if value['route'] != a.route or value['replay_start'] != int(meta['native_replay_args'][meta['native_replay_args'].index('--start')+1]):
      raise ValueError('Staged curve plan does not match prepared route/start')
    staged = ReplayCurvePlan(value)
    write_json(a.out/'demo_curve_plan.json',value)
  state = dict(active=False,signal_on=False,fresh=False,car_fresh=False,model_fresh=False,speed=0.,alert_key='',alert_meaningful=False,route_t=None,curve={'kind':'curve','phase':'neutral','amount':0.,'activation':None})
  received = {name:float('-inf') for name in sm.services}
  anchor = None
  position = None
  rendered = None
  done = False
  errors = []
  clock_errors = []
  clock_observations = []
  bridge = None
  flags = 0
  max_drift = 0.
  first_frame = None
  callback_revision = 0
  shared = dict(state='PREPARING',audio_s=0.,muted=a.muted)
  def callback(out, n, ti, status):
    nonlocal position,rendered,done,flags,max_drift,first_frame,callback_revision
    out.fill(0)
    if bridge is None:
      if len(clock_observations)<24:
        clock_observations.append((float(time.monotonic()),float(ti.currentTime),float(ti.outputBufferDacTime)))
      return
    if anchor is None or done:return
    now=time.monotonic()
    active_anchor=anchor
    expected=None;dac=None;start=position
    if status:flags+=1
    try:
      dac=bridge.dac_wall(float(ti.outputBufferDacTime))
      expected=initial_frame(meta,active_anchor[0],dac-active_anchor[1],rate)
      explicit_seek=sync is not None and active_anchor[2]!=callback_revision
      chunk,clock_info=playback_clock.render(audio,expected,n,explicit_seek=explicit_seek)
      callback_revision=active_anchor[2]
      start=clock_info['source_frame'];position=clock_info['next_source_frame']
      if first_frame is None:first_frame=start
      max_drift=max(max_drift,abs(clock_info['pre_error_frames'])/rate)
      wet,cues=processor.process(chunk,start,state,controls.selection)
      rendered=dict(sequence=start,callback_wall=now,dac_wall=dac,cues=cues)
      if not a.muted:out[:]=wet
      if start+n>=len(audio):done=True
    except Exception as error:
      clock_errors.append(dict(error=repr(error),callback_wall=now,portaudio_current_time=float(ti.currentTime),
                               portaudio_dac_time=float(ti.outputBufferDacTime),dac_wall=dac,
                               expected_frame=expected,start_frame=start,next_source_frame=position,
                               clock_position=playback_clock.position,anchor_model_ns=active_anchor[0],anchor_wall=active_anchor[1]))
      errors.append(repr(error));done=True
  started=None;last_status=0.
  trace=(a.out/'presentation.jsonl').open('w',buffering=1)
  sync_trace=(a.out/'replay_sync.jsonl').open('w',buffering=1) if sync is not None else None
  last_sync=0.
  forwarder = PairedDemoControls(GalaxyPeer(a.paired_comma,allow_lan_http=True),enabled=True) if a.paired_comma and not a.no_control_server else None
  server = None
  try:
    if not a.no_control_server:
      server = control_server(a.project_root,a.out,shared,a.port,forwarder,follow_peer=forwarder is not None)
      write_json(a.out/'controls.json',{'url':f'http://127.0.0.1:{server.server_port}/'})
    with sd.OutputStream(device=a.audio_device,samplerate=rate,channels=2,blocksize=960,dtype='float32',callback=callback) as stream:
      calibration_deadline=time.monotonic()+2.
      while len(clock_observations)<20:
        if not stream.active:raise RuntimeError('Output stream stopped during silent clock calibration')
        if time.monotonic()>=calibration_deadline:raise TimeoutError('Output clock did not provide 20 silent callbacks')
        time.sleep(.01)
      observations=list(clock_observations[:20])
      write_json(a.out/'stream_clock_calibration.json',dict(silent_callback_samples=observations))
      bridge=StreamClockBridge.from_callbacks(observations)
      (a.out/'prepared_ready').write_text('ready')
      while not done:
        sm.update(50);now=time.monotonic();controls.poll()
        for name in received:
          if sm.updated[name]:received[name]=now
        latest=max(sm.logMonoTime.values())
        def fresh(name):return bool(sm.valid[name] and 0<=now-received[name]<=.6 and 0<=(latest-sm.logMonoTime[name])/1e9<=1.)
        c=sm['carState'];s=sm['selfdriveState']
        update=dict(active=bool(s.active) and fresh('selfdriveState'),signal_on=bool(c.leftBlinker or c.rightBlinker),fresh=fresh('selfdriveState'),car_fresh=fresh('carState'),model_fresh=fresh('modelV2'),speed=float(c.vEgo),alert_key=str(s.alertType),alert_meaningful=int(s.alertStatus.raw)>0 and int(s.alertSize.raw)>0,curve=state['curve'])
        update['route_t']=state['route_t']
        if sm.updated['modelV2']:
          mono=sm.logMonoTime['modelV2']
          if anchor is None:anchor=(mono,now,0);started=now
          drift=(mono-anchor[0])/1e9-(now-anchor[1])
          if sync is not None and sync.consume_reanchor(drift,now):
            # This mode is always muted. Reset presentation filters outside the
            # callback before publishing the new original-model/audio anchor.
            processor=PreparedPresentation(a.score_archive,rate)
            conductor=Conductor(handoff=True)
            delay=PresentationDelay(a.presentation_root or a.out,output_provider=lambda: {'id':a.output_identity} if a.output_identity else None)
            rendered=None
            anchor=(mono,now,anchor[2]+1)
            drift=0.
            sync_trace.write(json.dumps(dict(wall=now,status='reanchored',source_model_ns=mono))+'\n')
          if abs(drift)>.75:raise RuntimeError('Prepared showcase left its 1x replay clock')
          route_t=(mono-meta['first_model_ns'])/1e9
          update['route_t']=route_t
          m=sm['modelV2']
          curve=conductor.update(route_t,{'mono':mono,'eof':m.timestampEof,'t':list(m.orientationRate.t),'yaw':list(m.orientationRate.z),'v':list(m.velocity.x)},float(c.vEgo)) if fresh('modelV2') and len(m.position.t)==33 else conductor.state(route_t)
          update['curve']=staged.state(route_t,a.route,curve) if staged else curve
        state=update
        if sync is not None and anchor is not None and now-last_sync>=.25:
          try:
            replay_state=json.loads(replay_state_path.read_text())
            replay_age=time.time()-replay_state_path.stat().st_mtime
          except (OSError,ValueError):replay_state=None;replay_age=float('inf')
          measurement=sync.evaluate(server.following_snapshot(),sm.logMonoTime['modelV2'],received['modelV2'],
                                    replay_state,now=now,replay_age=replay_age)
          if measurement['command'] is not None:
            if replay_command_path.exists():measurement.update(status='paused',reason='local_command_pending',command=None)
            else:
              write_json(replay_command_path,measurement['command'])
              drift=(sm.logMonoTime['modelV2']-anchor[0])/1e9-(received['modelV2']-anchor[1])
              sync.issued(measurement,now,drift)
          shared['replay_sync']={key:value for key,value in measurement.items() if key!='command'}
          sync_trace.write(json.dumps(dict(wall=now,**measurement))+'\n');last_sync=now
        if now-last_status>=.08:
          shared.update(state='READY' if anchor else 'PREPARING',audio_s=max(0,(position or 0)/rate))
          snapshot=dict(command_wall=now,input_mode='replay',compute='prepared-core',composer='ace',profile='prism',style='Prism',readiness=shared['state'],section='PREPARED PRISM',route=a.route,buffered=max(0,(len(audio)-(position or 0))/rate),presentation_session_id=session,demo_engagement_mode=controls.mode,demo_signal_mode=controls.signal_mode,engagement_presentation={'enabled':True},generation_invoked=False)
          if anchor is not None and state['route_t'] is not None and np.isfinite(state['route_t']):
            snapshot.update(route_t=float(state['route_t']),elapsed=max(0,(position or 0)/rate),
                            source_model_ns=int(sm.logMonoTime['modelV2']))
          snapshot['prepared_clock']=playback_clock.snapshot()
          if sync is not None:snapshot['replay_sync']=shared.get('replay_sync')
          snapshot=delay.apply(snapshot,rendered)
          # The command API must remain available during initial DAC lead-in.
          snapshot.setdefault('engagement_presentation',{'enabled':True})
          write_json(a.out/'status.json',snapshot)
          trace.write(json.dumps({**snapshot,'audio_s':shared['audio_s']})+'\n');last_status=now
        if started and now-started>=a.duration:break
        if started and now-received['modelV2']>2 and (position or 0)/rate < len(audio)/rate-2:raise RuntimeError('Replay model stream stopped before prepared audio ended')
  finally:
    try:write_json(a.out/'audio_drained.json',dict(wall=time.monotonic(),drained=not errors))
    finally:
      try:
        if server is not None:
          try:server.shutdown()
          finally:server.server_close()
        elif forwarder is not None:forwarder.close()
      finally:
        trace.close()
        if sync_trace is not None:sync_trace.close()
    write_json(a.out/'prepared_summary.json',dict(generation_invoked=False,source=str(a.score_archive),first_source_frame=first_frame,last_source_frame=position,sample_rate=rate,portaudio_flags=flags,max_clock_error_seconds=max_drift,prepared_clock=playback_clock.snapshot(),stream_clock_bridge=bridge.snapshot() if bridge else None,callback_errors=errors,clock_errors=clock_errors,muted=a.muted,session_id=session,manual_scope='isolated replay display and presentation only'))
  if errors:raise RuntimeError(errors[0])
  if playback_clock.snapshot()['max_post_error_seconds']>.05:raise RuntimeError('Prepared audio clock drift remained above 50 ms after recovery')


def apply_showcase_config(a, config):
  """Resolve the matching route's saved choices once; explicit CLI choices win."""
  if not isinstance(config, dict):raise ValueError('Prepared showcase configuration must be an object')
  matching = config.get('route') == a.route
  if a.score_archive is None:
    if not matching or not config.get('archive'):raise ValueError('No prepared showcase configured for this route')
    a.score_archive = Path(config['archive'])
    if a.curve_plan is None and config.get('curve_plan'):a.curve_plan = Path(config['curve_plan'])
  if a.unpaired:a.paired_comma = None
  elif a.paired_comma is None and matching:a.paired_comma = config.get('paired_comma')
  if a.paired_comma is not None:GalaxyPeer(a.paired_comma,allow_lan_http=True)
  if a.port is None:a.port = config.get('controls_port',0) if matching else 0
  if type(a.port) is not int or not 0 <= a.port <= 65535:raise ValueError('Controls port must be an integer from 0 to 65535')
  return a


def parser():
  p=argparse.ArgumentParser()
  p.add_argument('--roadscore',action='store_true');p.add_argument('--prepared-showcase',action='store_true')
  p.add_argument('route',nargs='?',default='route1')
  p.add_argument('--score-archive',type=Path)
  p.add_argument('--curve-plan',type=Path)
  p.add_argument('--project-root',type=Path,default=HERE.parents[1])
  p.add_argument('--runtime',type=Path)
  p.add_argument('--out',type=Path)
  p.add_argument('--duration',type=float,default=float('inf'))
  p.add_argument('--port',type=int,default=None,help='Override the saved local controls port; 0 selects an available port')
  p.add_argument('--no-control-server',action='store_true',help=argparse.SUPPRESS)
  p.add_argument('--presentation-root',type=Path,help=argparse.SUPPRESS)
  p.add_argument('--output-identity',help=argparse.SUPPRESS)
  p.add_argument('--hold-start',action='store_true',help=argparse.SUPPRESS)
  p.add_argument('--follow-playhead',action='store_true',help=argparse.SUPPRESS)
  def paired_url(value):
    try:GalaxyPeer(value,allow_lan_http=True)
    except ValueError as error:raise argparse.ArgumentTypeError(str(error)) from error
    return value
  pairing=p.add_mutually_exclusive_group()
  pairing.add_argument('--paired-comma',type=paired_url,default=None,metavar='URL',
                       help='Override the saved Galaxy LAN URL http://PRIVATE_IPV4:8082; forwards replay controls only')
  pairing.add_argument('--unpaired',action='store_true',help='Use Mac-only controls for this launch, overriding a saved comma target')
  p.add_argument('--muted',action='store_true');p.add_argument('--headless',action='store_true')
  p.add_argument('--no-browser',action='store_true');p.add_argument('--audio-device');p.add_argument('--check',action='store_true');p.add_argument('--audio-worker',action='store_true',help=argparse.SUPPRESS)
  return p


def main():
  a=parser().parse_args()
  if a.audio_worker:
    if a.no_control_server and a.paired_comma:raise SystemExit('Paired controls require the local control server')
    if a.port is None:a.port=0
    validate_follow_options(a)
    return audio_worker(a)
  if a.no_control_server:raise SystemExit('--no-control-server is an internal prepared audio-worker option')
  if sys.platform!='darwin' or Path('/TICI').exists():raise SystemExit('Prepared Mac showcase runs only on the Mac')
  launch_started=time.monotonic()
  project=a.project_root.resolve();rt=a.runtime or project/'.host_runtime/darwin/worktree'
  py=rt.parent/'venv/bin/python'
  from route_favorites import resolve_favorite
  a.route,_=resolve_favorite(a.route,project/'roadscore/routes/favorites.json')
  config_path=project/'roadscore/assets/prepared_showcase.json'
  try:
    config=json.loads(config_path.read_text()) if config_path.is_file() else {}
    apply_showcase_config(a,config)
    validate_follow_options(a)
  except (OSError,ValueError,TypeError) as error:raise SystemExit('Invalid prepared showcase configuration: '+str(error)) from error
  launch=json.loads((a.score_archive/'launch.json').read_text())
  if launch['route']!=a.route:raise SystemExit('Prepared score belongs to a different route')
  from route_library import local_source
  local=local_source(a.route,project/'roadscore')
  if local is None:raise SystemExit('Local route missing; no network fetch will be started')
  # This Mac binary predates native H.264 cache support. Prefer the complete
  # local originals, which VideoToolbox decodes, instead of its qcamera fallback.
  if local.name=='playback':
    original=local.parent
    segments=list(original.glob(a.route.split('/')[1]+'--*'))
    if segments and all((segment/'fcamera.hevc').is_file() for segment in segments):local=original
  for path in (py,rt/'tools/replay/replay',rt/'selfdrive/ui/ui.py'):
    if not path.exists():raise SystemExit('Missing existing host runtime: '+str(path))
  session=uuid.uuid4().hex
  out=a.out or project/'roadscore/results'/('mac_showcase_'+str(int(time.time())))
  out.mkdir(parents=True,exist_ok=False)
  env=os.environ.copy()
  env.update(PYTHONDONTWRITEBYTECODE='1',ZMQ='1',OPENPILOT_ZMQ_NAMESPACE='roadscore-showcase-'+session,ROADSCORE_SHOWCASE_SESSION=session,ROADSCORE_PREPARED_SHOWCASE='1',ROADSCORE_REPLAY_UI_CONTROLS='1',PARAMS_ROOT=str(out/'params'),BASEDIR=str(rt),NOBOARD='1',SIMULATION='1',SKIP_FW_QUERY='1',BIG='0',SP_ALLOW_DESKTOP_FAKE_WIFI='0',SP_ALLOW_DESKTOP_FAKE_BLUETOOTH='0',SP_ONROAD_NAV_DEMO='0',SP_ONROAD_CEM_DEMO='0',ROADSCORE_CLEAN_DEMO_UI='1',ROADSCORE_OVERLAY='1',ROADSCORE_STATUS_FILE=str(out/'status.json'),ROADSCORE_UI_AUDIT=str(out/'ui_audit.jsonl'),ROADSCORE_OVERLAY_CAPTURE=str(out/'overlay.png'),ROADSCORE_PRESENTATION_POLICY='conservative-v4')
  env['OPENPILOT_PREFIX']='roadscore-showcase-'+session
  env['ROADSCORE_AUDIO_DRAIN_FILE']=str(out/'audio_drained.json')
  env['PWD']=str(rt)
  env['PYTHONPATH']=':'.join(map(str,[HERE,rt,rt/'starpilot/third_party',*rt.glob('*_repo'),project/'roadscore/.analysis-venv/lib/python3.12/site-packages']))
  args=launch['native_replay_args'][:]
  args[args.index('--data_dir')+1]=str(local)
  if '--no-hw-decoder' in args:args.remove('--no-hw-decoder')
  if a.follow_playhead and '--headless' not in args:args.append('--headless')
  write_json(out/'status.json',dict(readiness='PREPARING',style='Prism',compute='prepared-core'))
  write_json(out/'launch.json',dict(core_sha256=hashlib.sha256((a.score_archive/'dry.wav').read_bytes()).hexdigest(),curve_plan_sha256=hashlib.sha256(a.curve_plan.read_bytes()).hexdigest() if a.curve_plan else None,mode='prepared-interactive-showcase',route=a.route,source=str(a.score_archive),runtime=str(rt),native_replay_args=args,generation_invoked=False,network_required=False,session_id=session,muted=a.muted or a.headless,paired_comma=a.paired_comma,paired_controls_scope=DISCLOSURE))
  check=subprocess.run([str(py),'-c','from cereal import messaging; import sounddevice,soundfile; from prepared_core import load_archive; import sys; a,r,m=load_archive(sys.argv[1],sys.argv[2]); print("Prepared core:",len(a)/r,"seconds; local replay ready")',str(a.score_archive),a.route],cwd=rt,env=env)
  if check.returncode:raise SystemExit(check.returncode)
  if a.check:return
  children=[];logs=[]
  def start(cmd,name):
    log=(out/(name+'.log')).open('w');logs.append(log)
    proc=subprocess.Popen(cmd,env=env,cwd=rt,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    children.append(proc);return proc
  def stop(*_):raise KeyboardInterrupt
  signal.signal(signal.SIGTERM,stop)
  try:
    seed_started=time.monotonic()
    with (out/'seed.log').open('w') as log:subprocess.run([str(py),str(rt/'tools/replay/onroad_config.py'),'seed',*args],env=env,cwd=rt,stdout=log,stderr=subprocess.STDOUT,check=True)
    seed_finished=time.monotonic()
    if not a.headless:ui=start([str(py),str(HERE/'normal_ui_audit.py')],'ui')
    audio=start([str(py),str(__file__),'--audio-worker',a.route,'--score-archive',str(a.score_archive),'--project-root',str(project),'--out',str(out),'--duration',str(a.duration),'--port',str(a.port)]+(['--curve-plan',str(a.curve_plan)] if a.curve_plan else [])+(['--muted'] if a.muted or a.headless else [])+(['--audio-device',a.audio_device] if a.audio_device else [])+(['--paired-comma',a.paired_comma] if a.paired_comma else [])+(['--follow-playhead'] if a.follow_playhead else []),'audio')
    deadline=time.monotonic()+30
    while not (out/'prepared_ready').exists():
      if audio.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Prepared audio did not become ready; see '+str(out/'audio.log'))
      time.sleep(.1)
    if a.hold_start and not a.headless:
      while not (out/'ui_audit.jsonl').is_file() or (out/'ui_audit.jsonl').stat().st_size==0:
        if ui.poll() is not None or audio.poll() is not None or time.monotonic()>deadline:
          raise RuntimeError('Native UI did not become ready for the held start')
        time.sleep(.1)
    ready_at=time.monotonic()
    write_json(out/'startup.json',dict(launch_to_prepared_ready_seconds=ready_at-launch_started,local_parameter_seed_seconds=seed_finished-seed_started,generation_seconds=0.,model_loading_seconds=0.,compile_seconds=0.))
    controls_url=json.loads((out/'controls.json').read_text())['url']
    print('Replay controls:',controls_url,flush=True)
    if not a.no_browser and not a.headless:subprocess.Popen(['/usr/bin/open',controls_url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    write_json(out/'demo_ready.json',dict(session_id=session,ready=True,route=a.route,held=a.hold_start))
    if a.hold_start:
      deadline=time.monotonic()+120.
      while True:
        if audio.poll() is not None or (not a.headless and ui.poll() is not None):raise RuntimeError('Prepared Mac child exited before start')
        now=time.monotonic()
        if now>=deadline:raise TimeoutError('Prepared Mac start barrier expired')
        try:release=start_deadline(json.loads((out/'start.json').read_text()),session,now)
        except (OSError,ValueError):release=None
        if release is not None:
          while time.monotonic()<release:
            if audio.poll() is not None or (not a.headless and ui.poll() is not None):raise RuntimeError('Prepared Mac child exited before release')
            time.sleep(min(.02,max(0.,release-time.monotonic())))
          break
        time.sleep(.05)
    replay=start([str(rt/'tools/replay/replay'),*args],'replay')
    write_json(out/'demo_started.json',dict(session_id=session,route=a.route,wall=time.monotonic()))
    print('Prepared RoadScore showcase running locally. Ctrl+C stops it. Output:',out,flush=True)
    while audio.poll() is None:
      if replay.poll() not in (None,0):raise RuntimeError('Local replay failed; see '+str(out/'replay.log'))
      if not a.headless and ui.poll() is not None:raise RuntimeError('Native UI exited; see '+str(out/'ui.log'))
      time.sleep(.2)
    if audio.returncode:raise RuntimeError('Prepared audio failed; see '+str(out/'audio.log'))
  finally:
    cleanup_children(children,logs)
    print('Local prepared showcase stopped.',flush=True)

if __name__=='__main__':main()
