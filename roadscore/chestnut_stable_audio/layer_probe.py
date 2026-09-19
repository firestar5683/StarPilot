"""Synthetic SA3 layer-shape probe. NOT model inference or a music benchmark.
Shapes from Stability-AI/stable-audio-3 optimized/mlx models, see report.
"""
import time,json,threading,os
from pathlib import Path
import numpy as np,psutil
from tinygrad import Tensor,TinyJit,Device,dtypes
from tinygrad.helpers import GlobalCounters
ROOT=Path('/data/sa3-feasibility');ROOT.mkdir(exist_ok=True)
rng=np.random.default_rng(1709)
peak_rss=peak_buffers=0
proc=psutil.Process()
def monitor():
 global peak_rss,peak_buffers
 while True:
  peak_rss=max(peak_rss,proc.memory_info().rss);peak_buffers=max(peak_buffers,GlobalCounters.mem_used);time.sleep(.02)
threading.Thread(target=monitor,daemon=True).start()
def random(shape,scale=.02): return Tensor((rng.standard_normal(shape)*scale).astype(np.float16),device='AMD').realize()
def norm(x,eps): return (x.float()*(x.float().square().mean(-1,keepdim=True)+eps).rsqrt()).cast(x.dtype)
def rope(x,c,s):
 a,b=x[...,:16],x[...,16:32]
 return (a*c-b*s).cat(a*s+b*c,x[...,32:],dim=-1)
class Block:
 def __init__(self,kind,seq):
  f=np.arange(seq)[:,None]/10000**(np.arange(0,32,2)/32)
  self.cos=Tensor(np.cos(f).astype(np.float16),device='AMD').realize();self.sin=Tensor(np.sin(f).astype(np.float16),device='AMD').realize()
  self.kind=kind;self.dim=1024 if kind=='dit' else 768;d=self.dim
  self.heads=d//64;self.inner=4096 if kind=='dit' else 2304
  self.wqkv=random((d,(3 if kind=='dit' else 5)*d));self.wo=random((d,d))
  self.wff=random((d,2*self.inner));self.bff=random((2*self.inner,));self.wout=random((self.inner,d));self.bout=random((d,))
  if kind=='dit':
   self.wq=random((d,d));self.wkv=random((d,2*d));self.wcross=random((d,d))
   self.wlocal=random((257,d));self.blocal=random((d,));self.wlocal2=random((d,d));self.blocal2=random((d,))
  self.jit=TinyJit(self.forward)
 def attention(self,q,k,v): return (((q*.125)@k.transpose(-1,-2)).float().softmax(-1).cast(q.dtype)@v)
 def forward(self,x,context,local,g):
  B,T,D=x.shape
  def heads(y):return y.reshape(B,T,self.heads,64).transpose(1,2)
  if self.kind=='dit':
   ss=g.reshape(B,1,6,D);a,b,c,d,e,f=[ss[:,:,i] for i in range(6)]
   z=norm(x,1e-5)*(1+a)+b
   q,k,v=[heads(t) for t in (z@self.wqkv).chunk(3,dim=-1)]
   q=rope(norm(q,1e-6),self.cos,self.sin);k=rope(norm(k,1e-6),self.cos,self.sin)
   x=x+(self.attention(q,k,v).transpose(1,2).reshape(B,T,D)@self.wo)*(1-c).sigmoid()
   q=norm(heads(norm(x,1e-5)@self.wq),1e-6)
   k,v=[t.reshape(B,-1,self.heads,64).transpose(1,2) for t in (context@self.wkv).chunk(2,dim=-1)]
   k=norm(k,1e-6)
   x=x+self.attention(q,k,v).transpose(1,2).reshape(B,T,D)@self.wcross
   x=x+((local@self.wlocal+self.blocal).silu()@self.wlocal2+self.blocal2)
   z=norm(x,1e-5)*(1+d)+e
  else:
   q,k,v,qd,kd=[heads(t) for t in (x.tanh()@self.wqkv).chunk(5,dim=-1)]
   q,k,qd,kd=[rope(t.tanh(),self.cos,self.sin) for t in [q,k,qd,kd]]
   y=self.attention(q,k,v)-self.attention(qd,kd,v)
   x=x+y.transpose(1,2).reshape(B,T,D)@self.wo
   z=x.tanh()
  val,gate=(z@self.wff+self.bff).chunk(2,dim=-1)
  y=(val*gate.silu())@self.wout+self.bout
  if self.kind=='dit':y=y*(1-f).sigmoid()
  return (x+y).realize()
results={'warning':'Random-weight representative blocks only. No text conditioning, complete model, decoded audio, or gate success. Repeated-layer extrapolation is not measured end-to-end latency.','runs':[]}
for kind,shape in [('dit',(1,384,1024)),('same_s_decoder',(160,34,768))]:
 t0=time.monotonic();block=Block(kind,shape[1]);x=random(shape,.2)
 context=random((shape[0],257 if kind=='dit' else 1,shape[-1]));local=random((shape[0],shape[1],257))
 g=random((shape[0],6*shape[-1]));init=time.monotonic()-t0
 times=[]
 for i in range(6):
  t0=time.monotonic();out=block.jit(x,context,local,g);Device['AMD'].synchronize();dt=time.monotonic()-t0
  times.append(dt);print(kind,i,dt,flush=True)
 assert np.isfinite(out.numpy()).all()
 run={'kind':kind,'shape':shape,'initialization_seconds':init,'calls_seconds':times,'warm_median_seconds':float(np.median(times[3:])),
  'peak_host_rss_bytes':peak_rss,'peak_tracked_buffer_bytes':peak_buffers}
 results['runs'].append(run)
 results['hardware']={'backend':type(Device['AMD'].iface).__name__,'arch':Device['AMD'].arch}
 results['cpu_affinity']=list(os.sched_getaffinity(0))
 (ROOT/'layer_probe.json').write_text(json.dumps(results,indent=2));print('RESULT',json.dumps(run),flush=True)
