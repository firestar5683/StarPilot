"""SSH pipe adapter for already-published normal replay cereal; never opens routes.
One ordered, bounded stream. The existing replay owns video and route discovery.
"""
import argparse,json,struct,sys,time,os,signal
from pathlib import Path
from cereal import messaging,log
SERVICES=['modelV2','carState','navInstruction','navRoute','longitudinalPlan','starpilotPlan','livePose']
p=argparse.ArgumentParser();p.add_argument('mode',choices=['send','receive']);p.add_argument('--root',default='/data/roadscore');p.add_argument('--seconds',type=float,default=0);p.add_argument('--route',default='normal-replay');a=p.parse_args()
def packet(stream,data):
 data=struct.pack('!d',time.monotonic())+data
 stream.write(struct.pack('!I',len(data)));stream.write(data);stream.flush()
def read_exact(n):
 parts=[]
 while n:
  data=sys.stdin.buffer.read(n)
  if not data:raise EOFError
  parts.append(data);n-=len(data)
 return b''.join(parts)
if a.mode=='send':
 def terminate(*_):raise KeyboardInterrupt
 signal.signal(signal.SIGTERM,terminate)
 poller=messaging.Poller();socks=[messaging.sub_sock(s,poller=poller,conflate=False) for s in SERVICES];start=None;count=0;first_model=None;service_counts={}
 # Receiver confirms the app is ready before the host starts native replay.
 print('BRIDGE_SUBSCRIBED',file=sys.stderr,flush=True)
 try:
  while True:
   for sock in poller.poll(100):
    data=sock.receive(non_blocking=True)
    if data is None:continue
    if start is None:start=time.monotonic()
    with log.Event.from_bytes(data) as event:
     kind=event.which();service_counts[kind]=service_counts.get(kind,0)+1
     if kind=='modelV2' and first_model is None:
      first_model=event.logMonoTime
      if os.environ.get('ROADSCORE_ORIGIN_FILE'):Path(os.environ['ROADSCORE_ORIGIN_FILE']).write_text(json.dumps({'first_model_ns':first_model,'host_received_wall':time.monotonic()}))
    packet(sys.stdout.buffer,data);count+=1
   if start and a.seconds and time.monotonic()-start>=a.seconds:break
 except (KeyboardInterrupt,BrokenPipeError):pass
 finally:
  print('BRIDGE_MESSAGES',count,file=sys.stderr,flush=True)
  print('BRIDGE_SERVICES',json.dumps(service_counts),file=sys.stderr,flush=True)
else:
 root=Path(a.root);run=root/'results/current';run.mkdir(parents=True,exist_ok=True);pm=messaging.PubMaster(SERVICES);origin=None;last=None;count=0;first_received=None;max_clock_drift=0.;failure=None;delivery_stalls=[]
 while not (run/'ready').exists():time.sleep(.1)
 print('BRIDGE_READY',flush=True)
 try:
  while True:
   n=struct.unpack('!I',read_exact(4))[0]
   if n>4*1024*1024:raise ValueError('Oversized cereal packet')
   payload=read_exact(n);host_send_wall=struct.unpack('!d',payload[:8])[0];data=payload[8:];received=time.monotonic()
   with log.Event.from_bytes(data) as e:
    kind=e.which()
    if kind not in SERVICES:raise ValueError('Service outside replay adapter allowlist')
    mono=e.logMonoTime
    if kind=='modelV2':
     with (run/'model_delivery.jsonl').open('a') as f:f.write(json.dumps({'mono':mono,'host_send_wall':host_send_wall,'bench_receive_wall':received})+'\n')
     if origin is None:origin=mono;wall=time.monotonic();first_received=wall
     t=(mono-origin)/1e9
     if last is not None and (t<last-.05 or t-last>5):raise RuntimeError('Seek or discontinuity: restart RoadScore for a new replay clock')
     max_clock_drift=max(max_clock_drift,abs((time.monotonic()-wall)-t))
     if t>2 and abs((time.monotonic()-wall)-t)>.75:raise RuntimeError('Replay clock is no longer1x or transport is delayed; restart for a new clock')
     last=t;max_clock_drift=max(max_clock_drift,abs((time.monotonic()-wall)-t));clock={'done':False,'origin_ns':origin,'origin_wall':wall,'route':a.route,'t':t,'late':max(0.,time.monotonic()-wall-t),'adapter':'native-replay-ssh','received_wall':time.monotonic()}
     tmp=run/'clock.tmp';tmp.write_text(json.dumps(clock));tmp.replace(run/'clock.json')
    publish_started=time.monotonic();pm.send(kind,data);published=time.monotonic();count+=1
    if published-received>.05:
     delivery_stalls.append({'service':kind,'mono':mono,'wall':published,'event_handling_seconds':publish_started-received,'publish_seconds':published-publish_started})
     delivery_stalls=delivery_stalls[-100:]
 except EOFError:pass
 except Exception as error:
  failure=repr(error);raise
 finally:
  if origin is not None:clock['done']=True;(run/'clock.json').write_text(json.dumps(clock))
  (run/'bridge.json').write_text(json.dumps({'delivery_stalls':delivery_stalls,'failure':failure,'messages':count,'origin_ns':origin,'last_t':last,'max_absolute_source_clock_drift_seconds':max_clock_drift,'route':a.route,'clock':'zero at first model received; source logMonoTime remains unchanged'},indent=2))
