"""Explicit private experimental backend choice. Never inferred from a route."""
import os,sys,fcntl,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NAMES={'sa3':'Stable Audio 3 Small-Music, native tinygrad, Chestnut USB AMD','ace':'ACE-Step1.5 turbo FP16, prepared conditioning, native tinygrad Chestnut'}
def choice():
 value=os.environ.get('ROADSCORE_COMPOSER','ace')
 if value not in NAMES:raise ValueError('Unknown composer backend')
 return value
def worker_path():return ROOT/('experiments/ace_chestnut_20260916/ace_worker.py' if choice()=='ace' else 'prototype/worker.py')
def source_path(identity):return ROOT/'generated/ace_initial.wav' if choice()=='ace' else ROOT/f'assets/source_{identity}.wav'
def check_available():
 selected=str(worker_path());commands=[]
 for entry in Path('/proc').glob('[0-9]*/cmdline'):
  try:commands.append(entry.read_bytes().replace(b'\0',b' ').decode())
  except OSError:pass
 if any(selected in command and 'python' in command for command in commands):
  if choice()=='ace':
   from ace_profiles import selected as selected_profile
   try:
    worker_state=json.loads((ROOT/'generated/ace_worker_state.json').read_text());profile=worker_state['profile']
   except (OSError,ValueError,KeyError):raise SystemExit('ACE worker profile unavailable; restart preparation explicitly')
   from generation_seed import configured_seed
   resident_handoff=False
   if os.environ.get('ROADSCORE_RESIDENT')=='1' and os.environ.get('ROADSCORE_SEED_ORIGIN')!='judging-route':
    try:resident_handoff=json.loads((ROOT/'generated/ace_initial.json').read_text()).get('resident_capable') is True
    except (OSError,ValueError):pass
   if not resident_handoff and worker_state.get('generation_seed')!=configured_seed():raise SystemExit('Resident ACE seed differs; stop owned worker and prepare requested seed')
   if not resident_handoff and profile!=selected_profile():raise SystemExit('Resident ACE profile differs; stop owned worker and prepare requested profile')
  return
 lockpath=ROOT/'generated/gpu.lock'
 if lockpath.exists():
  with lockpath.open('r') as handle:
   try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:raise SystemExit('Another composer owns Chestnut; stop its owned session before switching backends')
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='check':check_available()
 print(worker_path())
