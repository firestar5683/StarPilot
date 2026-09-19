"""Bound decoder workspace with overlapping latent windows; discard context, no crossfade."""
import time
import numpy as np
from tinygrad import TinyJit,Device
from native_ace import tensor
class ChunkDecoder:
 def __init__(self,vae,window=375,core=250):
  self.vae=vae;self.window=window;self.core=core;self.graphs={}
 def decode(self,latent):
  n=latent.shape[1];w=min(n,self.window);fn=self.graphs.setdefault(w,TinyJit(self.vae.forward));halo=(w-min(self.core,w))//2;parts=[];start_time=time.monotonic()
  for start in range(0,n,min(self.core,w)):
   left=max(0,min(start-halo,n-w));end=min(start+self.core,n);z=tensor(latent[:,left:left+w].transpose(0,2,1).astype(np.float16));a=fn(z).numpy()[0].T.astype(np.float32);parts.append(a[(start-left)*1920:(end-left)*1920])
  Device['AMD'].synchronize();return np.concatenate(parts),time.monotonic()-start_time

class FencedChunkDecoder(ChunkDecoder):
 """Bounded decoder with explicit completion at each USB/compute boundary.
 Optional trace is diagnostic only; it does not change the arithmetic or windows.
 This is not a claim that the earlier USB/GPU failure's root cause is repaired.
 """
 def __init__(self,vae,window=375,core=250,trace=None):
  super().__init__(vae,window,core);self.trace=trace
 def decode(self,latent):
  n=latent.shape[1];w=min(n,self.window);fn=self.graphs.setdefault(w,TinyJit(self.vae.forward));halo=(w-min(self.core,w))//2;parts=[];started=time.monotonic();dev=Device['AMD']
  def mark(stage,start):
   if self.trace:self.trace(stage,start,n,getattr(dev,'timeline_value',None))
  for start in range(0,n,min(self.core,w)):
   left=max(0,min(start-halo,n-w));end=min(start+self.core,n);stage='upload';mark('upload_begin',start)
   try:
    z=tensor(latent[:,left:left+w].transpose(0,2,1).astype(np.float16));dev.synchronize();mark('upload_done',start);stage='execute'
    result=fn(z);mark('compute_submitted',start);dev.synchronize()
    mark('execute_done',start);stage='readback'
    mark('readback_begin',start);a=result.numpy()[0].T.astype(np.float32);mark('readback_done',start);parts.append(a[(start-left)*1920:(end-left)*1920])
   except Exception:
    # Read through the existing owner before teardown; never recover silently.
    try:print('VAE_FAILURE_LINK',hex(dev.iface.pci_dev.usb.read(0xB450,1)[0]),'stage',stage,'latent_start',start,flush=True)
    except Exception as diagnostic:print('VAE_FAILURE_LINK_UNREADABLE',str(diagnostic),flush=True)
    raise
  dev.synchronize();return np.concatenate(parts),time.monotonic()-started
