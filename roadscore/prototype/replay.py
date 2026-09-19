"""Only this process may read route data. Publishes original messages at recorded times."""
import os,time,json,argparse,warnings
from pathlib import Path
from cereal import messaging
from concurrent.futures import ThreadPoolExecutor
from openpilot.tools.lib.logreader import _LogFileReader
p=argparse.ArgumentParser();p.add_argument('--route',required=True);p.add_argument('--root',default='/data/roadscore');p.add_argument('--start',type=float,default=0);p.add_argument('--duration',type=float,default=180);a=p.parse_args()
root=Path(a.root);run=root/'results/current';run.mkdir(parents=True,exist_ok=True)
services=['modelV2','carState','longitudinalPlan','starpilotPlan','navInstruction','navRoute','livePose','gpsLocationExternal','mapdOut','roadCameraState']
pm=messaging.PubMaster(services)
while not (run/'ready').exists():time.sleep(.1)
origin=None;startwall=None;nav=None;laststatus=0;total=0
folders=sorted((root/'routes').glob(a.route+'--*'),key=lambda d:int(d.name.rsplit('--',1)[1]))
def read(d):
 with warnings.catch_warnings():
  warnings.simplefilter('error');return _LogFileReader(str(d/'rlog.zst'),sort_by_time=True)
pool=ThreadPoolExecutor(max_workers=1);future=pool.submit(read,folders[0])
for index,d in enumerate(folders):
 log=future.result()
 if index+1<len(folders):future=pool.submit(read,folders[index+1])
 for e in log:
  if origin is None:origin=e.logMonoTime
  t=(e.logMonoTime-origin)/1e9;k=e.which()
  if t<a.start:
   if k=='navRoute':nav=e.as_builder().to_bytes()
   continue
  if t>a.start+a.duration:break
  if k not in services:continue
  if startwall is None:
   if nav:pm.send('navRoute',nav)
   startwall=time.monotonic();base=t
  due=startwall+t-base;delay=due-time.monotonic()
  if delay>0:time.sleep(delay)
  pm.send(k,e.as_builder().to_bytes());total+=1
  if t-laststatus>=.05:
   state={'t':t,'origin_ns':origin,'wall':time.monotonic(),'origin_wall':startwall-base,'start':a.start,'route':a.route,'done':False,'late':max(0,time.monotonic()-due)}
   f=run/'clock.tmp';f.write_text(json.dumps(state));f.replace(run/'clock.json');laststatus=t
 if origin is not None and t>a.start+a.duration:break
 del log
pool.shutdown();state['done']=True;(run/'clock.json').write_text(json.dumps(state));print('Replay complete',total,flush=True)
