"""Temporary offroad display ownership; resume existing manager on every normal exit."""
import os,signal,subprocess,time
from pathlib import Path
ROOT=Path('/data/roadscore');env=dict(os.environ);env.pop('OPENPILOT_PREFIX',None)
subprocess.run(['/usr/local/venv/bin/python','-c','from openpilot.common.params import Params; assert not Params().get_bool("IsOnroad")'],cwd='/data/openpilot',env=env,check=True)
pid=int(subprocess.check_output(['pgrep','-f','^selfdrive.ui.ui$'],text=True).strip());manager=int(Path(f'/proc/{pid}/stat').read_text().split()[3]);child=None

def stop(*args):raise KeyboardInterrupt
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
try:
 os.kill(manager,signal.SIGSTOP);os.kill(pid,signal.SIGTERM)
 for _ in range(50):
  if not Path(f'/proc/{pid}').exists() or Path(f'/proc/{pid}/stat').read_text().split()[2]=='Z':break
  time.sleep(.1)
 child=subprocess.Popen(['taskset','-c','0-3','/usr/local/venv/bin/python',str(ROOT/'prototype/native_display.py')],env=env)
 child.wait()
except KeyboardInterrupt:pass
finally:
 if child is not None and child.poll() is None:
  child.terminate()
  try:child.wait(timeout=8)
  except subprocess.TimeoutExpired:child.kill();child.wait()
 os.kill(manager,signal.SIGCONT)
 print('Original UI manager resumed',flush=True)
