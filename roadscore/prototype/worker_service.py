from device_target import device_target
"""Explicit offroad-only resident worker ownership for rapid demo relaunches.
No audio devices. Never stops an externally owned worker. Not a driving integration.
"""
import argparse,json,os,signal,subprocess,sys,time,fcntl
from pathlib import Path
from composer_choice import worker_path,choice
from ace_profiles import selected
ROOT=Path(__file__).resolve().parents[1];STATE=ROOT/'generated/worker_service.json'
def command(pid):
 try:return Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode()
 except OSError:return ''
def stamp(pid):
 try:return Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[19]
 except OSError:return None
def owned(record):return record.get('start_ticks')==stamp(record.get('pid',0)) and 'worker_service.py serve' in command(record.get('pid',0))
def write_state(record):
 tmp=STATE.with_suffix('.tmp');tmp.write_text(json.dumps(record));tmp.replace(STATE)
def state():
 try:r=json.loads(STATE.read_text())
 except (OSError,ValueError):r={}
 return {**r,'running':owned(r),'ready':owned(r) and (ROOT/'generated/worker_ready').exists()}
_params=None
def offroad():
 global _params
 # Cache the native reader; repeatedly importing openpilot in subprocesses
 # competed with compilation during resident preparation (~1.3s per check).
 if _params is None:
  os.environ.pop('OPENPILOT_PREFIX',None);os.environ.pop('PARAMS_ROOT',None)
  sys.path.insert(0,'/data/openpilot')
  from openpilot.common.params import Params
  _params=Params()
 return not _params.get_bool('IsOnroad')
def serve():
 STATE.parent.mkdir(exist_ok=True);lock=(STATE.parent/'worker_service.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 if not offroad():raise SystemExit('Resident preparation requires a verified offroad bench')
 record={'pid':os.getpid(),'start_ticks':stamp(os.getpid()),'started_wall':time.time(),'gpu_power_limit_watts':os.environ.get('AM_POWER_LIMIT','30' if choice()=='ace' else None),'ownership':'explicit resident service','phase':'Preparing','composer':choice(),'profile':selected() if choice()=='ace' else None};write_state(record);child=None;stop=False
 def interrupt(*_):
  nonlocal stop;stop=True
 signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
 try:
  env=os.environ.copy();env.pop('OPENPILOT_PREFIX',None);env.pop('PARAMS_ROOT',None)
  env.setdefault('ROADSCORE_WORKER',str(worker_path()))
  child=subprocess.Popen(['/usr/local/venv/bin/python','-u',str(ROOT/'prototype/power_worker.py')],env=env)
  record['power_pid']=child.pid;write_state(record)
  while child.poll() is None and not stop:
   if not offroad():record['stop_reason']='real onroad state';break
   phase='READY' if (ROOT/'generated/worker_ready').exists() else 'Preparing'
   if choice()=='ace' and phase=='Preparing':
    try:
     worker_state=json.loads((ROOT/'generated/ace_worker_state.json').read_text())
     if worker_state.get('phase')=='Stopped' and worker_state.get('pid') and command(worker_state['pid']):phase='Failed'
    except (OSError,ValueError):pass
   if phase!=record['phase']:record['phase']=phase;write_state(record)
   time.sleep(1)
 finally:
  if child is not None and child.poll() is None:child.terminate();child.wait(timeout=25)
  failed=not stop and child is not None and child.returncode not in (None,0)
  record.update(phase='Failed' if failed else 'Stopped',exit_code=None if child is None else child.returncode,stopped_wall=time.time());write_state(record)
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['start','status','stop','serve']);p.add_argument('--bench',default=device_target());p.add_argument('--composer',choices=['sa3','ace'],default=choice());p.add_argument('--profile',choices=['prism','aurora'],default=selected());a=p.parse_args()
 os.environ['ROADSCORE_COMPOSER']=a.composer;os.environ['ROADSCORE_ACE_PROFILE']=a.profile
 if not Path('/TICI').exists():
  raise SystemExit(subprocess.run(['ssh',a.bench,'/usr/local/venv/bin/python','/data/roadscore/prototype/worker_service.py',a.action,'--composer',a.composer,'--profile',a.profile]).returncode)
 if a.action=='serve':serve();return
 r=state()
 if a.action=='start' and r['running'] and (r.get('composer')!=a.composer or (a.composer=='ace' and r.get('profile')!=a.profile)):raise SystemExit('Resident selection mismatch: stop the owned worker before switching')
 if a.action=='start' and not r['running']:
  # Refuse to take over an active launcher or another experiment.
  workers=[x for x in Path('/proc').iterdir() if x.name.isdigit() and any(str(ROOT/name) in command(int(x.name)) for name in ['prototype/worker.py','experiments/ace_chestnut_20260916/ace_worker.py'])]
  if workers:raise SystemExit('An external worker already exists; its owner retains control')
  if not offroad():raise SystemExit('Resident preparation requires a verified offroad bench')
  (ROOT/'results').mkdir(exist_ok=True)
  with (ROOT/'results/resident_worker.log').open('ab') as log:
   c=subprocess.Popen(['/usr/local/venv/bin/python',str(Path(__file__)),'serve'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
  for _ in range(150):
   workers=[x for x in Path('/proc').iterdir() if x.name.isdigit() and str(worker_path()) in command(int(x.name))]
   if state()['running'] and workers:break
   if c.poll() is not None:raise RuntimeError('Resident worker failed; see resident_worker.log')
   time.sleep(.1)
  else:raise RuntimeError('Worker process did not start in time; inspect resident_worker.log')
 elif a.action=='stop' and r['running']:
  os.kill(r['pid'],signal.SIGTERM)
  for _ in range(60):
   if not owned(r):break
   time.sleep(.5)
  if owned(r):raise RuntimeError('Resident worker is still stopping; inspect supervisor log')
 print(json.dumps(state(),indent=2))
if __name__=='__main__':main()
