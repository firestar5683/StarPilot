"""Private LAN-only read-only demo server. Explicit file allowlist; no route access."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
import re,json
ROOT=Path('/data/roadscore')
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_POST(self):
  if self.path!='/style':self.send_error(404);return
  if self.headers.get('Origin') not in (None,'http://192.168.3.111:8088'):self.send_error(403);return
  try:
   size=int(self.headers.get('Content-Length','0'));assert 0<size<256
   assert self.headers.get('Content-Type','').startswith('application/json')
   selected=json.loads(self.rfile.read(size))['identity'];styles=json.loads((ROOT/'prototype/styles.json').read_text())
   assert selected in styles and (ROOT/f'assets/source_{selected}.wav').exists()
   config=json.loads((ROOT/'runtime.json').read_text()) if (ROOT/'runtime.json').exists() else {}
   config['identity']=selected
   f=ROOT/'runtime.tmp';f.write_text(json.dumps(config));f.replace(ROOT/'runtime.json')
  except (ValueError,KeyError,AssertionError):self.send_error(400);return
  self.send_response(204);self.end_headers()
 def do_GET(self):
  files={'/':(ROOT/'prototype/index.html','text/html'),'/styles':(ROOT/'prototype/styles.json','application/json'),'/status':(ROOT/'results/current/status.json','application/json'),'/trace':(ROOT/'results/current/trace.jsonl','application/x-ndjson'),'/video':(ROOT/'assets/demo.mp4','video/mp4'),'/recording':(ROOT/'results/current/heard.wav','audio/wav')}
  item=files.get(self.path.split('?')[0])
  if item is None or not item[0].exists():self.send_error(404);return
  path,mime=item;size=path.stat().st_size;start=0;end=size-1;partial=False
  value=self.headers.get('Range','');m=re.fullmatch(r'bytes=(\d+)-(\d*)',value)
  if m:
   start=int(m[1]);end=min(end,int(m[2])) if m[2] else end;partial=True
  if start>end or start>=size:self.send_error(416);return
  self.send_response(206 if partial else 200);self.send_header('Content-Type',mime);self.send_header('Accept-Ranges','bytes');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(end-start+1))
  if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
  self.end_headers()
  try:
   with path.open('rb') as f:
    f.seek(start);remaining=end-start+1
    while remaining:
     b=f.read(min(65536,remaining));self.wfile.write(b);remaining-=len(b)
     if not b:break
  except (BrokenPipeError,ConnectionResetError):pass
ThreadingHTTPServer(('192.168.3.111',8088),Handler).serve_forever()
