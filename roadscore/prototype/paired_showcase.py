"""Launch one saved native replay and mirror its actual UI on the Mac."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
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


def main():
  parser=argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--roadscore',action='store_true');parser.add_argument('--demo',action='store_true')
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
    peer.call('demo_start',{'alias':args.route,'request_id':request_id,'muted':args.muted})
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


if __name__=='__main__':main()
