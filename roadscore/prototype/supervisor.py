"""Single-command private bench runner. Owns children and restores worker CPU settings."""
import os,subprocess,time,signal,sys,socket
from pathlib import Path
def terminate(sig,frame):raise KeyboardInterrupt
signal.signal(signal.SIGTERM,terminate)
ROOT=Path('/data/roadscore');children=[]
def start(args,log):
 f=log.open('a');p=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);f.close();children.append(p);return p
try:
 env=dict(os.environ);env.pop('OPENPILOT_PREFIX',None)
 subprocess.run(['/usr/local/venv/bin/python','-c','from openpilot.common.params import Params; assert not Params().get_bool("IsOnroad")'],cwd='/data/openpilot',env=env,check=True)
 # Refuse duplicate runs. File lock persists only for this invocation.
 import fcntl
 lock=(ROOT/'supervisor.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 worker=ROOT/'generated/worker_ready'
 # An already running manually launched worker can be reused; no second GPU owner.
 running=subprocess.run(['pgrep','-f','^/data/sa3-feasibility/venv/bin/python -u /data/roadscore/prototype/worker.py$'],capture_output=True).returncode==0
 if not running:
  worker.unlink(missing_ok=True);(ROOT/'generated/request.json').unlink(missing_ok=True)
  wp=start(['/usr/local/venv/bin/python','-u',str(ROOT/'prototype/power_worker.py')],ROOT/'results/worker.log')
  deadline=time.monotonic()+300
  print('Prewarming Chestnut; speaker output remains muted.',flush=True)
  while not worker.exists():
   if wp.poll() is not None or time.monotonic()>deadline:raise RuntimeError('SA3 prewarm failed; see results/worker.log')
   time.sleep(1)
 try:
  s=socket.create_connection(('192.168.3.111',8088),timeout=1);s.close()
 except OSError:start(['/usr/local/venv/bin/python',str(ROOT/'prototype/server.py')],ROOT/'results/server.log')
 if os.environ.get('ROADSCORE_DISPLAY')=='1':start(['/usr/local/venv/bin/python','-u',str(ROOT/'prototype/display_owner.py')],ROOT/'results/display.log')
 print('Private panel: http://192.168.3.111:8088 — audio is saved, bench speaker muted.',flush=True)
 rp=subprocess.Popen(['bash',str(ROOT/'prototype/run_device.sh'),*sys.argv[1:]],start_new_session=True);children.append(rp)
 rc=rp.wait();print('Replay finished; saved artifacts in /data/roadscore/results/current',flush=True)
 deadline=time.monotonic()+45
 while (ROOT/'generated/busy').exists() and time.monotonic()<deadline:time.sleep(.2)
 if rc:raise RuntimeError('Demo failed; inspect app.log and replay.log')
finally:
 for p in reversed(children):
  if p.poll() is None:
   # Signal wrapper first so its finally restores CPU configuration.
   p.terminate()
   try:p.wait(timeout=20)
   except subprocess.TimeoutExpired:
    os.killpg(p.pid,signal.SIGKILL);p.wait()
