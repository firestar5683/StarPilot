"""Enforce the runtime's no-route-file rule for Python file opens."""
import sys,os
from pathlib import Path

def install(root):
 forbidden=[Path(root,'routes').resolve(),Path('/data/media/0/realdata')]
 def audit(event,args):
  if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
  path=Path(os.fsdecode(args[0])).resolve()
  if any(path==p or p in path.parents for p in forbidden):
   raise PermissionError('RoadScore runtime may not open recorded route files')
 sys.addaudithook(audit)
