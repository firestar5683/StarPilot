"""Temporarily lend the physical display to the existing replay UI, offroad only."""
import fcntl,os,signal,subprocess,time
from pathlib import Path
def verify_offroad():
 env=os.environ.copy()
 for key in ['OPENPILOT_PREFIX','PARAMS_ROOT','ZMQ']:env.pop(key,None)
 subprocess.run(['/usr/local/venv/bin/python','-c','from openpilot.common.params import Params; assert not Params().get_bool("IsOnroad"), "Device is onroad"'],cwd='/data/openpilot',env=env,check=True)

class DisplayOwner:
 def __init__(self,root):self.root=root;self.manager=None;self.lock=None
 def acquire(self):
  verify_offroad()
  self.lock=(self.root/'generated/display.lock').open('w');fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  pid=int(subprocess.check_output(['pgrep','-f','^selfdrive.ui.ui$'],text=True).strip())
  self.manager=int(Path(f'/proc/{pid}/stat').read_text().split()[3]);os.kill(self.manager,signal.SIGSTOP)
  os.kill(pid,signal.SIGTERM)
  for _ in range(80):
   path=Path(f'/proc/{pid}/stat')
   if not path.exists() or path.read_text().split()[2]=='Z':return
   time.sleep(.1)
  raise RuntimeError('Normal UI did not release display')
 def close(self):
  if self.manager is not None:os.kill(self.manager,signal.SIGCONT);self.manager=None
  if self.lock:self.lock.close();self.lock=None
