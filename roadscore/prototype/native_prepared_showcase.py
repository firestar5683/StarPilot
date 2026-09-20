"""Play prepared ACE core locally on comma, using the existing replay and DSP worker."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent


def write_json(path, value):
  temporary = Path(str(path)+'.tmp')
  temporary.write_text(json.dumps(value))
  temporary.replace(path)


@contextmanager
def native_session(root):
  """Same lease as fresh replay; children must not inherit it."""
  path = Path(root)/'generated/native_session.lock'
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open('a') as stream:
    try:fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:raise RuntimeError('Another native RoadScore session owns this bench') from None
    os.set_inheritable(stream.fileno(), False)
    yield


def install_current(root, out, session):
  """Retain the previous current directory/link and publish this new owned run."""
  parent = (Path(root)/'results').resolve()
  out = Path(out).resolve()
  if out.parent != parent or out.name == 'current':
    raise ValueError('Prepared output must be a separate direct child of RoadScore results')
  current = parent/'current'
  previous = None
  if current.exists() or current.is_symlink():
    previous = parent/('prepared_previous_'+session)
    if previous.exists() or previous.is_symlink():raise FileExistsError(previous)
    current.rename(previous)
  temporary = parent/('.prepared_current_'+session)
  try:
    temporary.symlink_to(out, target_is_directory=True)
    temporary.replace(current)
  except BaseException:
    temporary.unlink(missing_ok=True)
    if previous is not None and not current.exists():previous.rename(current)
    raise
  return previous


def start_deadline(path, session, now):
  try:
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict) or value.get('session_id') != session or value.get('play') is not True:return None
    deadline = value.get('start_at_wall', now)
    if type(deadline) not in (int, float) or not math.isfinite(deadline) or not now-1 <= deadline <= now+5:return None
    return max(now, deadline)
  except (OSError, ValueError):return None


def native_environment(project, root, out, session, inherited=None):
  env = dict(os.environ if inherited is None else inherited)
  for key in ('ZMQ','PARAMS_ROOT','OPENPILOT_ZMQ_NAMESPACE','ROADSCORE_PCM_RETURN','ROADSCORE_RESIDENT','ROADSCORE_GENERATION_SEED','ROADSCORE_SEED_ORIGIN'):
    env.pop(key, None)
  env.update(PYTHONDONTWRITEBYTECODE='1',OPENPILOT_PREFIX='roadscore_replay',BASEDIR=str(project),PWD=str(project),NOBOARD='1',SIMULATION='1',SKIP_FW_QUERY='1',BIG='0',ROADSCORE_PREPARED_SHOWCASE='1',ROADSCORE_SHOWCASE_SESSION=session,ROADSCORE_REPLAY_UI_CONTROLS='1',ROADSCORE_CLEAN_DEMO_UI='1',ROADSCORE_OVERLAY='1',ROADSCORE_STATUS_FILE=str(out/'status.json'),ROADSCORE_UI_AUDIT=str(out/'ui_audit.jsonl'),ROADSCORE_OVERLAY_CAPTURE=str(out/'overlay.png'),ROADSCORE_AUDIO_DRAIN_FILE=str(out/'audio_drained.json'),ROADSCORE_PRESENTATION_POLICY='conservative-v4',SP_ALLOW_DESKTOP_FAKE_WIFI='0',SP_ALLOW_DESKTOP_FAKE_BLUETOOTH='0',SP_ONROAD_NAV_DEMO='0',SP_ONROAD_CEM_DEMO='0')
  paths=[HERE,project,project/'starpilot/third_party',*project.glob('*_repo'),Path('/data/roadscore-feasibility/venv/lib/python3.12/site-packages')]
  env['PYTHONPATH']=':'.join(map(str,paths))
  env['ROADSCORE_MIRROR_DIR']=str(out/'mirror')
  return env


def replay_arguments(meta, local):
  args = list(meta['native_replay_args'])
  if '--data_dir' not in args:raise ValueError('Prepared source lacks a local replay recipe')
  args[args.index('--data_dir')+1] = str(local)
  if '--no-hw-decoder' not in args:args.append('--no-hw-decoder')
  if '--no-loop' not in args:args.append('--no-loop')
  if '--headless' not in args:args.append('--headless')
  return args


def worker_arguments(project, root, out, archive, route, muted, curve_plan=None, output=None, duration=float('inf')):
  output = output or {}
  args = ['/usr/local/venv/bin/python',str(HERE/'mac_showcase.py'),'--audio-worker',route,'--project-root',str(project),'--score-archive',str(archive),'--out',str(out),'--duration',str(duration),'--no-control-server','--presentation-root',str(root)]
  if muted:args.append('--muted')
  if curve_plan is not None:args += ['--curve-plan',str(curve_plan)]
  if output.get('bluetooth_selected'):
    args += ['--audio-device',output['pcm_name'],'--output-identity',output['output_identity']]
  return args


def cleanup_owned(children, display, logs):
  """Finish owned cleanup even if the parent sends a second stop signal."""
  previous = {sig: signal.signal(sig, signal.SIG_IGN) for sig in (signal.SIGTERM, signal.SIGINT)}
  errors = []
  try:
    for child in reversed(list(children.values())):
      try:
        if child.poll() is None:
          try: os.killpg(child.pid, signal.SIGTERM)
          except ProcessLookupError: pass
          try: child.wait(timeout=5)
          except subprocess.TimeoutExpired:
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            child.wait(timeout=5)
      except Exception as error:
        errors.append(type(error).__name__ + ': ' + str(error))
  finally:
    try:
      if display is not None: display.close()
    finally:
      for log in logs: log.close()
      for sig, handler in previous.items(): signal.signal(sig, handler)
  return errors


def main():
  p=argparse.ArgumentParser(description=__doc__)
  p.add_argument('--roadscore',action='store_true');p.add_argument('--demo',action='store_true')
  p.add_argument('route',nargs='?',default='route1')
  p.add_argument('--project-root',type=Path,default=Path('/data/openpilot'))
  p.add_argument('--score-archive',type=Path);p.add_argument('--curve-plan',type=Path)
  p.add_argument('--out',type=Path);p.add_argument('--muted',action='store_true');p.add_argument('--headless',action='store_true')
  p.add_argument('--check',action='store_true');p.add_argument('--hold-start',action='store_true')
  p.add_argument('--start-timeout',type=float,default=120.);p.add_argument('--duration',type=float,default=float('inf'))
  a=p.parse_args()
  if not Path('/TICI').exists() and not a.check:raise SystemExit('Native prepared showcase runs only on the comma')
  project=a.project_root.resolve();root=project/'roadscore'
  from route_favorites import resolve_favorite
  route,_=resolve_favorite(a.route,root/'routes/favorites.json')
  if a.score_archive is None:
    from demo_catalog import entry
    selected=entry(root,a.route)
    if selected['route']!=route:raise ValueError('No matching prepared showcase registered')
    a.score_archive=Path(selected['archive'])
    if a.curve_plan is None and selected.get('curve_plan'):a.curve_plan=Path(selected['curve_plan'])
  archive=a.score_archive.resolve(strict=True)
  from prepared_core import load_archive
  audio,rate,meta=load_archive(archive,route)
  duration=len(audio)/rate
  del audio
  if a.curve_plan is not None:
    a.curve_plan=a.curve_plan.resolve(strict=True)
    from demo_curve_plan import validate
    plan=validate(json.loads(a.curve_plan.read_text()))
    original_start=int(meta['native_replay_args'][meta['native_replay_args'].index('--start')+1])
    if plan['route']!=route or plan['replay_start']!=original_start:raise ValueError('Curve plan does not match the prepared route/start')
  from route_library import local_source
  local=local_source(route,root)
  if local is None:raise ValueError('Prepared showcase requires an existing local route cache')
  replay=root/'native_build/replay';py=Path('/usr/local/venv/bin/python')
  for path in (py,replay,project/'selfdrive/ui/ui.py',HERE/'mac_showcase.py'):
    if not path.is_file():raise FileNotFoundError(path)
  args=replay_arguments(meta,local)
  checked=dict(route=route,archive=str(archive),seconds=duration,local_cache=str(local),generation_invoked=False,requires_chestnut=False,replay_args=args)
  if a.check:
    print(json.dumps(checked,indent=2));return
  from native_ownership import verify_offroad,DisplayOwner
  from audio_policy import allow_output
  verify_offroad()
  session=uuid.uuid4().hex
  out=a.out or root/'results'/('native_demo_'+str(int(time.time()))+'_'+session[:8])
  out=out.resolve()
  results=(root/'results').resolve()
  if out.parent!=results or out.name=='current':raise ValueError('Output must be a dedicated run within RoadScore results')
  current=results/'current'
  if current.exists() and not current.is_symlink() and (archive==current or current in archive.parents):
    raise ValueError('Archive must be preserved outside the mutable current run before launch')
  muted=not allow_output(not a.muted and not a.headless)
  logs=[];children={};display=None;failure=None;began=time.monotonic()
  def stop(*_):raise KeyboardInterrupt
  signal.signal(signal.SIGTERM,stop)
  with native_session(root):
    verify_offroad()
    if out.exists():
      if any(path.name!='launcher.log' for path in out.iterdir()):raise ValueError('Prepared output directory must contain only its supervisor launcher.log')
    else:out.mkdir(parents=True)
    previous=install_current(root,out,session)
    env=native_environment(project,root,out,session)
    env['ROADSCORE_FORCE_MUTE']='1' if muted else '0'
    Path('/dev/shm/msgq_roadscore_replay').mkdir(exist_ok=True)
    launch={**checked,'mode':'prepared-interactive-showcase','session_id':session,'muted':muted,'core_sha256':hashlib.sha256((archive/'dry.wav').read_bytes()).hexdigest(),'previous_current':str(previous) if previous else None,'curve_plan':str(a.curve_plan) if a.curve_plan else None}
    write_json(out/'launch.json',launch)
    write_json(out/'status.json',dict(readiness='PREPARING',style='Prism',compute='prepared-core',route=route,input_mode='replay',presentation_session_id=session,command_wall=time.monotonic()))
    def start(cmd,name):
      log=(out/(name+'.log')).open('w');logs.append(log)
      child=subprocess.Popen(cmd,env=env,cwd=project,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
      children[name]=child;return child
    def check_children():
      for name,child in children.items():
        if child.poll() is not None:raise RuntimeError(name+' exited; see '+str(out/(name+'.log')))
    try:
      with (out/'seed.log').open('w') as log:
        subprocess.run([str(py),str(project/'tools/replay/onroad_config.py'),'seed',*args],env=env,cwd=project,stdout=log,stderr=subprocess.STDOUT,check=True,close_fds=True)
      if not a.headless:
        display=DisplayOwner(root);display.acquire()
        start([str(py),str(HERE/'normal_ui_audit.py')],'ui')
      output={'muted':muted,'bluetooth_selected':False}
      if not muted:
        from bluetooth_output import prepare_output
        output.update(prepare_output(out,env=env))
      write_json(out/'output_device.json',output)
      audio=start(worker_arguments(project,root,out,archive,route,muted,a.curve_plan,output,a.duration),'audio')
      deadline=time.monotonic()+35
      while not (out/'prepared_ready').exists():
        check_children()
        if time.monotonic()>deadline:raise TimeoutError('Prepared audio did not become ready')
        time.sleep(.1)
      ready=dict(session_id=session,route=route,ready=True,held=a.hold_start,prepare_seconds=time.monotonic()-began,source=str(archive),generation_invoked=False)
      write_json(out/'demo_ready.json',ready)
      print('DEMO_PREPARED '+json.dumps(ready),flush=True)
      if a.hold_start:
        deadline=time.monotonic()+a.start_timeout
        start_at=None
        while start_at is None:
          start_at=start_deadline(out/'start.json',session,time.monotonic())
          if start_at is not None:break
          check_children()
          if time.monotonic()>deadline:raise TimeoutError('Prepared demo start barrier expired')
          time.sleep(.05)
        while time.monotonic()<start_at:
          check_children()
          time.sleep(min(.02,max(0.,start_at-time.monotonic())))
      verify_offroad()
      replay_process=start([str(replay),*args],'replay')
      write_json(out/'demo_started.json',dict(session_id=session,wall=time.monotonic(),route=route))
      print('Prepared RoadScore demo playing locally; no model generation.',flush=True)
      while audio.poll() is None:
        if replay_process.poll() is not None:raise RuntimeError('Native replay exited before prepared audio finished')
        if 'ui' in children and children['ui'].poll() is not None:raise RuntimeError('Native UI exited before prepared audio finished')
        time.sleep(.2)
      if audio.returncode:raise RuntimeError('Prepared audio failed; see '+str(out/'audio.log'))
      write_json(out/'demo_complete.json',dict(session_id=session,complete=True,wall=time.monotonic()))
    except BaseException as error:
      failure=type(error).__name__+': '+str(error)
      write_json(out/'demo_failure.json',dict(session_id=session,error=failure,wall=time.monotonic()))
      raise
    finally:
      cleanup_errors=cleanup_owned(children,display,logs)
      if cleanup_errors:write_json(out/'cleanup_errors.json',dict(errors=cleanup_errors))
      write_json(out/'status.json',dict(readiness='DEGRADED' if failure else 'COLD',compute='prepared-core',route=route,presentation_session_id=session,command_wall=time.monotonic(),input_mode='stopped',error=failure))
      print('Prepared native demo stopped. Existing composer ownership unchanged.',flush=True)


if __name__=='__main__':main()
