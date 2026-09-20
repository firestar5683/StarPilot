"""Launch saved native replays on comma and Mac, with Galaxy as control master."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler

from paired_demo_controls import GalaxyPeer, _NoRedirect, _http_json

HERE = Path(__file__).resolve().parent


class DemoPeer:
  def __init__(self, url, *, transport=_http_json):
    self.peer = GalaxyPeer(url, allow_lan_http=True)
    self.transport = transport

  def call(self, action, data=None):
    return self.transport('GET' if action == 'status' else 'POST',
                          self.peer.base_url+'/api/roadscore/'+action, data,
                          {'Accept':'application/json','Content-Type':'application/json','Cache-Control':'no-store'}, 4.)

  def frame(self, request_id):
    url=self.peer.base_url+'/api/roadscore/demo_frame?'+urlencode({'request_id':request_id})
    request=Request(url,headers={'Accept':'image/jpeg','Cache-Control':'no-store'})
    with build_opener(ProxyHandler({}),_NoRedirect()).open(request,timeout=2.) as response:
      if response.headers.get_content_type() != 'image/jpeg':raise ValueError('Expected a live replay image')
      frame=response.read(1500001)
      if len(frame)>1500000:raise ValueError('Replay frame is too large')
      return frame, {key:response.headers.get(key,'') for key in ('X-RoadScore-Frame','X-RoadScore-Age-Ms')}


def control_server(peer, request_id, port, state):
  class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self, body, kind='application/json', code=200, headers=None):
      self.send_response(code)
      self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store')
      self.send_header('Content-Length',str(len(body)))
      for name,value in (headers or {}).items():self.send_header(name,value)
      self.end_headers()
      try:self.wfile.write(body)
      except (BrokenPipeError,ConnectionResetError):pass
    def json(self,value,code=200):self.send(json.dumps(value).encode(),code=code)
    def do_GET(self):
      if self.path == '/':self.send((HERE/'paired_showcase.html').read_bytes(),'text/html; charset=utf-8');return
      if self.path == '/status':
        try:self.json({'phase':state['phase'],'peer':peer.call('status'),'galaxy_url':peer.peer.base_url+'/mobile/#/roadscore','muted':state['muted']})
        except Exception as error:self.json({'phase':state['phase'],'error':str(error)},503)
        return
      if self.path.startswith('/frame?'):
        try:
          frame,headers=peer.frame(request_id);self.send(frame,'image/jpeg',headers=headers)
        except Exception:self.json({'error':'Waiting for a fresh comma replay frame'},503)
        return
      self.send_error(404)
    def do_POST(self):
      if self.path!='/control':self.send_error(404);return
      expected={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
      if ('http://'+self.headers.get('Host','') not in expected
          or self.headers.get('Origin') not in expected
          or self.headers.get('Sec-Fetch-Site','same-origin') != 'same-origin'):
        self.json({'error':'Open controls from this local demo page'},403);return
      try:
        length=int(self.headers.get('Content-Length','0'))
        if not 0<length<=1024:raise ValueError('Invalid control payload')
        data=json.loads(self.rfile.read(length))
        if not isinstance(data,dict) or set(data)!={'field','value','session_id'}:raise ValueError('Invalid control payload')
        field=data['field'];allowed={'mode':('engaged','disengaged','recorded'),'signal_mode':('left','right','off','recorded')}
        if field not in allowed or data['value'] not in allowed[field]:raise ValueError('Unknown replay control')
        action='demo_engagement' if field=='mode' else 'demo_signal'
        self.json(peer.call(action,{'session_id':data['session_id'],field:data['value']}))
      except Exception as error:self.json({'error':str(error)},409)
  server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
  threading.Thread(target=server.serve_forever,daemon=True).start()
  return server


def mirror_main():
  parser=argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--roadscore',action='store_true');parser.add_argument('--demo',action='store_true')
  parser.add_argument('--screen-mirror',action='store_true')
  parser.add_argument('route',nargs='?',default='route1')
  parser.add_argument('--muted',action='store_true');parser.add_argument('--check',action='store_true')
  parser.add_argument('--no-browser',action='store_true');parser.add_argument('--port',type=int)
  parser.add_argument('--peer');parser.add_argument('--duration',type=float,default=float('inf'))
  args=parser.parse_args()
  root=HERE.parent
  from demo_catalog import entry
  selected=entry(root,args.route)
  config=json.loads((root/'assets/demo_catalog.json').read_text())
  peer=DemoPeer(args.peer or config.get('paired_comma'))
  port=args.port if args.port is not None else config.get('controls_port',56976)
  if type(port) is not int or not 0<=port<=65535:raise SystemExit('Invalid local controls port')
  status=peer.call('status')
  if status.get('offroad') is not True:raise SystemExit('Comma must be offroad for the saved demo')
  if args.check:
    print(json.dumps({'route':selected['route'],'alias':args.route,'peer_offroad':True,'generation_invoked':False,'controls_port':port}));return
  request_id=uuid.uuid4().hex
  state={'phase':'Preparing saved replay','muted':args.muted}
  # Claim the requested local page before starting anything on the peer.
  server=control_server(peer,request_id,port,state)
  launched=False;released=False;began=time.monotonic()
  def interrupt(*_):raise KeyboardInterrupt
  signal.signal(signal.SIGTERM,interrupt)
  try:
    launched=True
    peer.call('demo_start',{'alias':args.route,'request_id':request_id,'muted':args.muted,'screen_mirror':True})
    url=f'http://127.0.0.1:{server.server_port}'
    print('RoadScore saved demo. No model generation. Controls and mirrored screen: '+url,flush=True)
    if not args.no_browser:subprocess.Popen(['/usr/bin/open',url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    deadline=time.monotonic()+90
    while True:
      ready=peer.call('demo_ready',{})
      if ready.get('request_id')!=request_id:raise RuntimeError('Device demo ownership changed')
      if ready.get('failure'):raise RuntimeError(ready['failure'])
      if not ready.get('running'):raise RuntimeError('Saved demo failed to prepare')
      if ready.get('prepared'):break
      if time.monotonic()>deadline:raise TimeoutError('Saved replay did not prepare within 90 seconds; no model is being compiled')
      time.sleep(.25)
    peer.call('demo_play',{'request_id':request_id,'session_id':ready['ready_session_id']});released=True
    state['phase']='Playing saved replay'
    print('Playing on comma; this Mac mirrors its actual UI. Galaxy controls both views.',flush=True)
    started=time.monotonic()
    while time.monotonic()-started<args.duration:
      current=peer.call('demo_ready',{})
      if current.get('request_id')!=request_id:raise RuntimeError('Device demo ownership changed')
      if current.get('failure'):raise RuntimeError(current['failure'])
      if not current.get('running'):
        if current.get('complete'):break
        raise RuntimeError('Device demo stopped before completion')
      time.sleep(.5)
    state['phase']='Replay finished'
  finally:
    if launched:
      try:peer.call('demo_stop',{'request_id':request_id})
      except Exception as error:print('Could not confirm device demo stop: '+str(error),flush=True)
    server.shutdown();server.server_close()
    print('Saved demo stopped. Elapsed %.1f seconds.'%(time.monotonic()-began),flush=True)


def local_start_deadline(release, request_id, peer_session, sent, received):
  """Translate a short peer-relative countdown without comparing host clocks."""
  if release.get('request_id') != request_id or release.get('session_id') != peer_session:
    raise ValueError('Prepared playback release belongs to another session')
  values = [release.get('start_at_wall'), release.get('server_wall'), sent, received]
  if any(type(value) not in (int,float) or not math.isfinite(value) for value in values):
    raise ValueError('Invalid prepared playback clock')
  start,server,sent,received = values
  rtt = received-sent
  if not 0 <= rtt <= .5 or not 0 < start-server <= 5:
    raise ValueError('Playback release timing is too uncertain')
  deadline = received + (start-server) - rtt/2
  if deadline <= received:
    raise ValueError('Playback release arrived too late')
  return deadline


def mac_command(project, alias, selected, peer_url, out, duration, *, fullscreen=False):
  command = [str(project/'onroad'),'--roadscore',alias,'--prepared-showcase',
             '--score-archive',selected['archive'],'--paired-comma',peer_url,
             '--muted','--no-browser','--port','0','--hold-start','--follow-playhead',
             '--out',str(out),'--duration',str(duration)]
  if selected.get('curve_plan'):command += ['--curve-plan',selected['curve_plan']]
  if fullscreen:command.append('--fullscreen')
  return command


def read_ready(path, route):
  try:value=json.loads(path.read_text())
  except (OSError,ValueError):return None
  if not isinstance(value,dict) or value.get('ready') is not True:return None
  if value.get('route')!=route or not isinstance(value.get('session_id'),str) or not value['session_id']:
    raise ValueError('Mac prepared replay identity does not match the selected route')
  return value


def stop_mac(process):
  if process is not None and process.poll() is None:
    try:os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError:return
    try:process.wait(timeout=25)
    except subprocess.TimeoutExpired:
      try:os.killpg(process.pid,signal.SIGKILL)
      except ProcessLookupError:return
      process.wait(timeout=5)


def native_pair_main():
  parser=argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--roadscore',action='store_true');parser.add_argument('--demo',action='store_true')
  parser.add_argument('route',nargs='?',default='route1')
  parser.add_argument('--muted',action='store_true');parser.add_argument('--check',action='store_true')
  parser.add_argument('--no-browser',action='store_true',help=argparse.SUPPRESS)
  parser.add_argument('--fullscreen',action='store_true',help='Fill the Mac display with the native replay')
  parser.add_argument('--peer');parser.add_argument('--duration',type=float,default=float('inf'))
  args=parser.parse_args()
  if math.isnan(args.duration) or args.duration<=0:raise SystemExit('Duration must be positive')
  root=HERE.parent;project=root.parent
  from demo_catalog import entry
  selected=entry(root,args.route)
  config=json.loads((root/'assets/demo_catalog.json').read_text())
  peer=DemoPeer(args.peer or config.get('paired_comma'))
  if not args.check:
    from mac_replay_ownership import preflight, ReplayBusy
    try:preflight(root)
    except ReplayBusy as error:raise SystemExit(str(error)) from error
  if peer.call('status').get('offroad') is not True:raise SystemExit('Comma must be offroad for the saved demo')
  if args.check:
    print(json.dumps({'route':selected['route'],'alias':args.route,'peer_offroad':True,
                      'generation_invoked':False,'display':'native Mac replay','audio':'comma','screen_mirror':False}));return
  request_id=uuid.uuid4().hex
  out=root/'results'/('paired_showcase_'+request_id)
  out.mkdir(parents=True,exist_ok=False)
  mac_out=out/'mac'
  command=mac_command(project,args.route,selected,peer.peer.base_url,mac_out,args.duration,fullscreen=args.fullscreen)
  (out/'launch.json').write_text(json.dumps(dict(request_id=request_id,route=selected['route'],
      command=command,archive=selected['archive'],generation_invoked=False,screen_mirror=False,muted=args.muted),indent=2))
  process=None;launched=False;began=time.monotonic()
  def interrupt(*_):raise KeyboardInterrupt
  signal.signal(signal.SIGTERM,interrupt)
  try:
    launched=True
    peer.call('demo_start',{'alias':args.route,'request_id':request_id,'muted':args.muted})
    env=os.environ.copy()
    env.pop('ROADSCORE_MIRROR_DIR',None)
    with (out/'mac.log').open('wb') as log:
      process=subprocess.Popen(command,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=log,
                               stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
    print('Preparing saved RoadScore on comma and native Mac UI. No model generation.',flush=True)
    deadline=time.monotonic()+100
    while True:
      if process.poll() is not None:raise RuntimeError('Mac replay failed to prepare; see '+str(out/'mac.log'))
      ready=peer.call('demo_ready',{})
      if ready.get('request_id')!=request_id:raise RuntimeError('Device demo ownership changed')
      if ready.get('route')!=selected['route']:raise RuntimeError('Comma and Mac showcase routes do not match')
      if ready.get('failure'):raise RuntimeError(ready['failure'])
      if not ready.get('running'):raise RuntimeError('Saved comma demo failed to prepare')
      local=read_ready(mac_out/'demo_ready.json',selected['route'])
      if ready.get('prepared') and local is not None:break
      if time.monotonic()>deadline:raise TimeoutError('Saved replay preparation timed out')
      time.sleep(.15)
    sent=time.monotonic()
    release=peer.call('demo_play',{'request_id':request_id,'session_id':ready['ready_session_id']})
    received=time.monotonic()
    start_at=local_start_deadline(release,request_id,ready['ready_session_id'],sent,received)
    gate={'session_id':local['session_id'],'play':True,'start_at_wall':start_at}
    temporary=mac_out/'start.tmp';temporary.write_text(json.dumps(gate));temporary.replace(mac_out/'start.json')
    (out/'release.json').write_text(json.dumps({'peer':release,'local':gate,'rtt_s':received-sent}))
    print('Playing native replay on both screens; audio from comma. Use Galaxy for engagement and signals.',flush=True)
    print('Galaxy: '+peer.peer.base_url+'/mobile/#/roadscore',flush=True)
    print('Session evidence: '+str(out),flush=True)
    started=time.monotonic()
    mac_finished=False
    while time.monotonic()-started<args.duration:
      current=peer.call('demo_ready',{})
      if current.get('request_id')!=request_id:raise RuntimeError('Device demo ownership changed')
      if current.get('failure'):raise RuntimeError(current['failure'])
      if not current.get('running'):
        if current.get('complete'):break
        raise RuntimeError('Device demo stopped before completion')
      if not mac_finished and (code:=process.poll()) is not None:
        mac_finished=True
        degraded=dict(state='DEGRADED',component='mac_display',returncode=code,
                      request_id=request_id,wall=time.monotonic(),native_audio='continuing',
                      log=str(out/'mac.log'))
        try:(out/'mac_display.json').write_text(json.dumps(degraded,indent=2))
        except OSError as error:print('Could not record Mac display status: '+str(error),flush=True)
        print('Mac replay '+('failed' if code else 'ended')+'; comma audio continues to its own end. See '+str(out/'mac.log'),flush=True)
      time.sleep(.5)
  finally:
    # A second interrupt must not abandon the native windows or owned peer.
    signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
    try:stop_mac(process)
    finally:
      if launched:
        try:peer.call('demo_stop',{'request_id':request_id})
        except Exception as error:print('Could not confirm device demo stop: '+str(error),flush=True)
    print('Paired native demo stopped. Elapsed %.1f seconds.'%(time.monotonic()-began),flush=True)


def main():
  if '--screen-mirror' in sys.argv:mirror_main()
  else:native_pair_main()


if __name__=='__main__':main()
