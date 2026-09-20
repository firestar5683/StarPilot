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

HERE = Path(__file__).resolve().parent


def write_json(path, value):
  temporary = Path(str(path)+'.tmp')
  temporary.write_text(json.dumps(value))
  temporary.replace(path)


def control_server(project, out, shared, port):
  spec = importlib.util.spec_from_file_location('showcase_galaxy', project/'starpilot/system/the_galaxy/roadscore.py')
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  operator_root = out/'operator'
  (operator_root/'results').mkdir(parents=True)
  (operator_root/'results/current').symlink_to(out)
  operator = module.Operator(operator_root, device=False, offroad=lambda: True)
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
        self.send_json({'demo': operator.demo_status(), **shared})
      elif self.path == '/':
        data = (HERE/'mac_showcase.html').read_bytes()
        self.send_response(200);self.send_header('Content-Type', 'text/html; charset=utf-8');self.send_header('Content-Length', str(len(data)));self.end_headers();self.wfile.write(data)
      else:self.send_error(404)
    def do_POST(self):
      if self.path != '/control':self.send_error(404);return
      if not module.control_origin_allowed(self.headers.get('Origin'), self.headers.get('Host'), 'http', self.headers.get('Sec-Fetch-Site')):
        self.send_json({'error':'Cross-origin controls are not allowed'},403);return
      try:
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 1024:raise ValueError('Invalid control size')
        data = json.loads(self.rfile.read(length))
        field = 'signal_mode' if 'signal_mode' in data else 'mode'
        self.send_json(operator.demo_engagement(data, field))
      except (ValueError, TypeError) as error:self.send_json({'error':str(error)},400)
  server = ThreadingHTTPServer(('127.0.0.1',port),Handler)
  threading.Thread(target=server.serve_forever,daemon=True).start()
  return server


def audio_worker(a):
  import numpy as np
  import sounddevice as sd
  from cereal import messaging
  from core import Conductor
  from demo_engagement import DemoEngagement
  from operator_output import PresentationDelay
  from prepared_core import load_archive, initial_frame, PreparedPresentation
  audio, rate, meta = load_archive(a.score_archive, a.route)
  processor = PreparedPresentation(a.score_archive, rate)
  session = os.environ['ROADSCORE_SHOWCASE_SESSION']
  controls = DemoEngagement(a.out, session, 'replay')
  delay = PresentationDelay(a.out,output_provider=lambda: None)
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
  state = dict(active=False,signal_on=False,fresh=False,car_fresh=False,model_fresh=False,speed=0.,alert_key='',alert_meaningful=False,curve={'kind':'curve','phase':'neutral','amount':0.,'activation':None})
  received = {name:float('-inf') for name in sm.services}
  anchor = None
  position = None
  rendered = None
  done = False
  errors = []
  flags = 0
  max_drift = 0.
  first_frame = None
  shared = dict(state='PREPARING',audio_s=0.,muted=a.muted)
  server = control_server(a.project_root,a.out,shared,a.port)
  write_json(a.out/'controls.json',{'url':f'http://127.0.0.1:{server.server_port}/'})
  def callback(out, n, ti, status):
    nonlocal position,rendered,done,flags,max_drift,first_frame
    out.fill(0)
    if anchor is None or done:return
    now=time.monotonic();dac=now+float(ti.outputBufferDacTime-ti.currentTime)
    expected=initial_frame(meta,anchor[0],dac-anchor[1],rate)
    if position is None:position=expected;first_frame=position
    start=position;position+=n
    max_drift=max(max_drift,abs(start-expected)/rate)
    if status:flags+=1
    chunk=np.zeros((n,2),np.float32)
    lo=max(0,-start);hi=min(n,len(audio)-start)
    if hi>lo:chunk[lo:hi]=audio[start+lo:start+hi]
    try:
      wet,cues=processor.process(chunk,start,state,controls.selection)
      rendered=dict(sequence=start,callback_wall=now,dac_wall=dac,cues=cues)
      if not a.muted:out[:]=wet
      if start+n>=len(audio):done=True
    except Exception as error:
      errors.append(repr(error));done=True
  started=None;last_status=0.
  trace=(a.out/'presentation.jsonl').open('w',buffering=1)
  try:
    with sd.OutputStream(device=a.audio_device,samplerate=rate,channels=2,blocksize=960,dtype='float32',callback=callback):
      (a.out/'prepared_ready').write_text('ready')
      while not done:
        sm.update(50);now=time.monotonic();controls.poll()
        for name in received:
          if sm.updated[name]:received[name]=now
        latest=max(sm.logMonoTime.values())
        def fresh(name):return bool(sm.valid[name] and 0<=now-received[name]<=.6 and 0<=(latest-sm.logMonoTime[name])/1e9<=1.)
        c=sm['carState'];s=sm['selfdriveState']
        update=dict(active=bool(s.active) and fresh('selfdriveState'),signal_on=bool(c.leftBlinker or c.rightBlinker),fresh=fresh('selfdriveState'),car_fresh=fresh('carState'),model_fresh=fresh('modelV2'),speed=float(c.vEgo),alert_key=str(s.alertType),alert_meaningful=int(s.alertStatus.raw)>0 and int(s.alertSize.raw)>0,curve=state['curve'])
        if sm.updated['modelV2']:
          mono=sm.logMonoTime['modelV2']
          if anchor is None:anchor=(mono,now);started=now
          if abs((mono-anchor[0])/1e9-(now-anchor[1]))>.75:raise RuntimeError('Prepared showcase left its 1x replay clock')
          route_t=(mono-meta['first_model_ns'])/1e9
          m=sm['modelV2']
          curve=conductor.update(route_t,{'mono':mono,'eof':m.timestampEof,'t':list(m.orientationRate.t),'yaw':list(m.orientationRate.z),'v':list(m.velocity.x)},float(c.vEgo)) if fresh('modelV2') and len(m.position.t)==33 else conductor.state(route_t)
          update['curve']=staged.state(route_t,a.route,curve) if staged else curve
        state=update
        if now-last_status>=.08:
          shared.update(state='READY' if anchor else 'PREPARING',audio_s=max(0,(position or 0)/rate))
          snapshot=dict(command_wall=now,input_mode='replay',compute='prepared-core',composer='ace',profile='prism',style='Prism',readiness=shared['state'],section='PREPARED PRISM',route=a.route,buffered=max(0,(len(audio)-(position or 0))/rate),presentation_session_id=session,demo_engagement_mode=controls.mode,demo_signal_mode=controls.signal_mode,engagement_presentation={'enabled':True},generation_invoked=False)
          snapshot=delay.apply(snapshot,rendered)
          # The command API must remain available during initial DAC lead-in.
          snapshot.setdefault('engagement_presentation',{'enabled':True})
          write_json(a.out/'status.json',snapshot)
          trace.write(json.dumps({**snapshot,'audio_s':shared['audio_s']})+'\n');last_status=now
        if started and now-started>=a.duration:break
        if started and now-received['modelV2']>2 and (position or 0)/rate < len(audio)/rate-2:raise RuntimeError('Replay model stream stopped before prepared audio ended')
  finally:
    server.shutdown();trace.close()
    write_json(a.out/'prepared_summary.json',dict(generation_invoked=False,source=str(a.score_archive),first_source_frame=first_frame,last_source_frame=position,sample_rate=rate,portaudio_flags=flags,max_clock_error_seconds=max_drift,callback_errors=errors,muted=a.muted,session_id=session,manual_scope='isolated replay display and presentation only'))
  if errors:raise RuntimeError(errors[0])
  if max_drift>.05:raise RuntimeError('Prepared audio clock drift exceeded 50 ms')


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
  p.add_argument('--port',type=int,default=0)
  p.add_argument('--muted',action='store_true');p.add_argument('--headless',action='store_true')
  p.add_argument('--no-browser',action='store_true');p.add_argument('--audio-device');p.add_argument('--check',action='store_true');p.add_argument('--audio-worker',action='store_true',help=argparse.SUPPRESS)
  return p


def main():
  a=parser().parse_args()
  if a.audio_worker:return audio_worker(a)
  if sys.platform!='darwin' or Path('/TICI').exists():raise SystemExit('Prepared Mac showcase runs only on the Mac')
  launch_started=time.monotonic()
  project=a.project_root.resolve();rt=a.runtime or project/'.host_runtime/darwin/worktree'
  py=rt.parent/'venv/bin/python'
  from route_favorites import resolve_favorite
  a.route,_=resolve_favorite(a.route,project/'roadscore/routes/favorites.json')
  if a.score_archive is None:
    config=json.loads((project/'roadscore/assets/prepared_showcase.json').read_text())
    if config['route']!=a.route:raise SystemExit('No prepared showcase configured for this route')
    a.score_archive=Path(config['archive'])
    if a.curve_plan is None and config.get('curve_plan'):a.curve_plan=Path(config['curve_plan'])
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
  env.pop('OPENPILOT_PREFIX',None)
  env['PWD']=str(rt)
  env['PYTHONPATH']=':'.join(map(str,[HERE,rt,rt/'starpilot/third_party',*rt.glob('*_repo'),project/'roadscore/.analysis-venv/lib/python3.12/site-packages']))
  args=launch['native_replay_args'][:]
  args[args.index('--data_dir')+1]=str(local)
  if '--no-hw-decoder' in args:args.remove('--no-hw-decoder')
  write_json(out/'status.json',dict(readiness='PREPARING',style='Prism',compute='prepared-core'))
  write_json(out/'launch.json',dict(core_sha256=hashlib.sha256((a.score_archive/'dry.wav').read_bytes()).hexdigest(),curve_plan_sha256=hashlib.sha256(a.curve_plan.read_bytes()).hexdigest() if a.curve_plan else None,mode='prepared-interactive-showcase',route=a.route,source=str(a.score_archive),runtime=str(rt),native_replay_args=args,generation_invoked=False,network_required=False,session_id=session,muted=a.muted or a.headless))
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
    audio=start([str(py),str(__file__),'--audio-worker',a.route,'--score-archive',str(a.score_archive),'--project-root',str(project),'--out',str(out),'--duration',str(a.duration),'--port',str(a.port)]+(['--curve-plan',str(a.curve_plan)] if a.curve_plan else [])+(['--muted'] if a.muted or a.headless else [])+(['--audio-device',a.audio_device] if a.audio_device else []),'audio')
    deadline=time.monotonic()+30
    while not (out/'prepared_ready').exists():
      if audio.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Prepared audio did not become ready; see '+str(out/'audio.log'))
      time.sleep(.1)
    ready_at=time.monotonic()
    write_json(out/'startup.json',dict(launch_to_prepared_ready_seconds=ready_at-launch_started,local_parameter_seed_seconds=seed_finished-seed_started,generation_seconds=0.,model_loading_seconds=0.,compile_seconds=0.))
    controls_url=json.loads((out/'controls.json').read_text())['url']
    print('Replay controls:',controls_url,flush=True)
    if not a.no_browser and not a.headless:subprocess.Popen(['/usr/bin/open',controls_url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    replay=start([str(rt/'tools/replay/replay'),*args],'replay')
    print('Prepared RoadScore showcase running locally. Ctrl+C stops it. Output:',out,flush=True)
    while audio.poll() is None:
      if replay.poll() not in (None,0):raise RuntimeError('Local replay failed; see '+str(out/'replay.log'))
      if not a.headless and ui.poll() is not None:raise RuntimeError('Native UI exited; see '+str(out/'ui.log'))
      time.sleep(.2)
    if audio.returncode:raise RuntimeError('Prepared audio failed; see '+str(out/'audio.log'))
  finally:
    for child in reversed(children):
      if child.poll() is None:
        os.killpg(child.pid,signal.SIGTERM)
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
    for log in logs:log.close()
    print('Local prepared showcase stopped.',flush=True)

if __name__=='__main__':main()
