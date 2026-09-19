"""Loopback-only semantic preparation transport; no diffusion or route input."""
import argparse
import base64
import hmac
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from hook_planning import PlanCache, PlanRequest, request_plan

LIMIT = 32 * 1024 * 1024

class Client:
 def __init__(self, url, token, timeout=600):
  if not url.startswith('http://127.0.0.1:'):raise ValueError('Planner must use authenticated loopback tunnel')
  self.url,self.token,self.timeout=url.rstrip('/'),token,timeout
 def call(self, endpoint, data=None):
  body=None if data is None else json.dumps(data).encode()
  req=Request(self.url+endpoint,data=body,headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
  with urlopen(req,timeout=self.timeout) as response:
   result=response.read(LIMIT+1)
  if len(result)>LIMIT:raise ValueError('Oversized planner response')
  return json.loads(result)
 def fingerprints(self):return self.call('/identity')
 def prepare(self, request, sources, output):
  data=self.call('/plan',{'request':request.identity(),'sources':{k:base64.b64encode(Path(v).read_bytes()).decode() for k,v in sources.items()}})
  for name,encoded in data['files'].items():
   if Path(name).name!=name or name in ('.','..','cache.json'):raise ValueError('Invalid planner filename')
   (output/name).write_bytes(base64.b64decode(encoded,validate=True))


def make_server(adapter, cache, token, port=0):
 lock=threading.Lock()
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def respond(self,status,data):
   body=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  def authorized(self):return hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token)
  def do_GET(self):
   if not self.authorized():return self.respond(403,{'error':'Authentication required'})
   if self.path!='/identity':return self.respond(404,{'error':'Unknown endpoint'})
   try:self.respond(200,adapter.fingerprints())
   except Exception as exc:self.respond(500,{'error':str(exc)})
  def do_POST(self):
   if not self.authorized():return self.respond(403,{'error':'Authentication required'})
   if self.path!='/plan':return self.respond(404,{'error':'Unknown endpoint'})
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=LIMIT:raise ValueError('Invalid planner request size')
    data=json.loads(self.rfile.read(size));request=PlanRequest(**data['request'])
    canonical=request_plan(**{k:v for k,v in request.identity().items() if k in ('session_seed','plan_index','profile','section','window_seconds','model_fingerprint','preparation_fingerprint','hook_reference_sha256','committed_prefix_sha256','previous_plan_sha256')})
    if request!=canonical:raise ValueError('Request does not match current composition policy')
    if any(request.identity()[k]!=v for k,v in adapter.fingerprints().items()):raise ValueError('Planner identity mismatch')
    with lock,tempfile.TemporaryDirectory(dir=cache.root) as scratch:
     sources={}
     for name,value in data['sources'].items():
      if name not in ('hook_reference','committed_prefix'):raise ValueError('Unknown musical context')
      path=Path(scratch)/name;path.write_bytes(base64.b64decode(value,validate=True));sources[name]=path
     directory,hit=cache.resolve(request,adapter,sources=sources)
     files={p.name:base64.b64encode(p.read_bytes()).decode() for p in directory.iterdir() if p.name!='cache.json'}
    self.respond(200,{'files':files,'cache_hit':hit})
   except Exception as exc:self.respond(400,{'error':str(exc)})
 cache.root.mkdir(parents=True,exist_ok=True)
 return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--assets-root',type=Path,required=True);parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--ready',type=Path,required=True);args=parser.parse_args()
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments/ace_chestnut_20260916'))
 from host_hook_adapter import HostHookAdapter
 token=os.environ['ROADSCORE_PLANNER_TOKEN'];adapter=HostHookAdapter(args.assets_root)
 server=make_server(adapter,PlanCache(args.cache),token)
 identity=adapter.fingerprints()
 args.ready.write_text(json.dumps({'port':server.server_port,**identity}))
 try:server.serve_forever()
 finally:server.server_close();args.ready.unlink(missing_ok=True)

if __name__=='__main__':main()
