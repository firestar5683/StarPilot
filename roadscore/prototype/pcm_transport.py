"""Bounded final-PCM return over an SSH-forwarded Unix socket; no model tensors."""
import json, os, socket, struct, time
from pathlib import Path
HEADER=struct.Struct('!II')

def exact(stream,n):
 data=bytearray()
 while len(data)<n:
  chunk=stream.read(n-len(data))
  if not chunk:
   if not data:return None
   raise EOFError('Truncated PCM packet')
  data.extend(chunk)
 return bytes(data)

def read_packet(stream):
 header=exact(stream,HEADER.size)
 if header is None:return None
 m,n=HEADER.unpack(header)
 if m>16384 or n>48000*2*4:raise ValueError('Oversized PCM packet')
 meta=exact(stream,m);pcm=exact(stream,n)
 if meta is None or pcm is None:raise EOFError('Truncated PCM payload')
 return json.loads(meta),pcm

class Export:
 def __init__(self,path):
  self.path=Path(path);self.path.unlink(missing_ok=True)
  self.server=socket.socket(socket.AF_UNIX);self.server.bind(str(path));os.chmod(path,0o600);self.server.listen(1);self.server.settimeout(10);self.client=None;self.sequence=0
 def send(self,pcm,meta):
  if self.client is None:self.client,_=self.server.accept();self.client.settimeout(2)
  meta={**meta,'pcm_sequence':self.sequence,'export_wall':time.monotonic()};self.sequence+=1
  data=json.dumps(meta,separators=(',',':')).encode();raw=pcm.astype('<f4',copy=False).tobytes()
  self.client.sendall(HEADER.pack(len(data),len(raw))+data+raw)
 def close(self):
  if self.client:self.client.close()
  self.server.close();self.path.unlink(missing_ok=True)

if __name__=='__main__':
 import sys
 client=socket.socket(socket.AF_UNIX);client.connect(sys.argv[1])
 print('PCM_CONNECTED',file=sys.stderr,flush=True)
 while True:
  data=client.recv(65536)
  if not data:break
  sys.stdout.buffer.write(data);sys.stdout.buffer.flush()
