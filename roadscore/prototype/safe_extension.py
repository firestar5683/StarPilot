"""Explicit hold of accepted generated music; never described as fresh generation."""
import numpy as np
def viable(tail,rate):
 size=rate//10;x=tail[:len(tail)//size*size].reshape(-1,size,2);x=x-x.mean(axis=1,keepdims=True);e=np.sqrt(np.mean(x*x,axis=(1,2)))
 quiet=e<max(.0002,min(.003,float(np.quantile(e,.8))*.025));run=0
 for value in quiet:
  run=run+1 if value else 0
  if run>=20:return False
 return float(np.max(e))>.0002

def extend_tail(audio,rate):
 a=np.asarray(audio,dtype=np.float32)
 if len(a)<8*rate or not np.isfinite(a).all():raise ValueError('No valid accepted material for safe extension')
 # Prefer the current endpoint. An intentionally faded outro must not become a silent loop.
 tail=None;offset=0
 for offset in range(min(len(a)//rate-8,120)+1):
  end=len(a)-offset*rate;candidate=a[end-8*rate:end]
  if viable(candidate,rate):tail=candidate.copy();break
 if tail is None:raise ValueError('No audible accepted span available for safe extension')
 n=2*rate;alpha=np.linspace(0,1,n,dtype=np.float32)[:,None];wave=tail.copy()
 for _ in range(3):wave=np.concatenate([wave[:-n],wave[-n:]*(1-alpha)+tail[:n]*alpha,tail[n:]])
 return wave,{'source':'previously accepted generated audio','fresh_generation':False,'new_seconds':len(wave)/rate-2,'source_tail_seconds':8,'source_end_offset_seconds':offset,'preserves_latest_context':offset==0,'crossfade_seconds':2}
