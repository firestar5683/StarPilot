"""Prepared-condition ACE backend. Owns no audio device, route resolver, or input clock.
All heavy generation/decode runs on Chestnut. New identity preparation is not ported.
Caller must hold the shared GPU lock and establish offroad power supervision.
"""
from pathlib import Path
import json,time
import numpy as np
from tinygrad import TinyJit,Device
from native_ace import DiT,tensor,time_features
from native_vae import VAE
from chunk_decode import ChunkDecoder
class Composer:
 capabilities={'supports_full_song':True,'supports_reference':True,'supports_continuation':'repaint latent prefix','supports_transition':True,'supports_outro':True,'supports_streaming':False,'preparation':'precomputed identity/role embeddings; arbitrary prompt preparation remains host-assisted','precision':'FP16, TC_OPT=2','live_rtf':None,'coexistence_validated':False}
 def __init__(self,root):
  self.root=Path(root);self.dit=DiT(self.root/'weights');self.vae=VAE(self.root/'vae_weights');self.graphs={};self.decoder=ChunkDecoder(self.vae);self.decoder_ready=False
 def prepare(self,case,previous=None):
  p=self.root/case;cond=np.load(p/'encoder_hidden_states.npy').astype(np.float16);context=np.load(p/'context_latents.npy').astype(np.float16);n=context.shape[1]
  valid=np.load(p/'encoder_attention_mask.npy').astype(bool)
  width=max(256,((cond.shape[1]+31)//32)*32)
  mask=np.full((1,1,1,width),-np.inf,np.float16);mask[0,0,0,:cond.shape[1]]=np.where(valid[0],0,-np.inf)
  cond=np.pad(cond,((0,0),(0,width-cond.shape[1]),(0,0)))
  repaint=(p/'sampler_repaint_mask.npy').exists();source=keep=blend=None;settings={}
  if repaint:
   settings=json.loads((p/'sampler.json').read_text());source=np.load(p/'sampler_clean_src_latents.npy').astype(np.float16);keep=np.load(p/'sampler_repaint_mask.npy').astype(bool)
   if previous is not None:
    preserved=int(np.flatnonzero(keep[0])[0]);assert previous.shape[1]>=preserved
    source[:,:preserved]=previous[:,-preserved:];context[:,:preserved,:64]=source[:,:preserved]
   blend=keep.astype(np.float16)
   for row in blend:
    ids=np.flatnonzero(row);left,right=int(ids[0]),int(ids[-1])+1;cf=int(settings.get('repaint_crossfade_frames',12));lo=max(0,left-cf);hi=min(n,right+cf)
    if left>lo:row[lo:left]=np.linspace(0,1,left-lo+2)[1:-1]
    if hi>right:row[right:hi]=np.linspace(1,0,hi-right+2)[1:-1]
  return cond,context,mask,source,keep,blend,settings
 def generate(self,case,seed,previous=None):
  started=time.monotonic();cond,context,mask,source,keep,blend,settings=self.prepare(case,previous);n=context.shape[1]
  self.dit.prepare_shape(n);key=(n,cond.shape[1]);cold=key not in self.graphs
  fn=self.graphs.setdefault(key,TinyJit(self.dit.forward))
  noise=np.random.default_rng(seed).standard_normal((1,n,64)).astype(np.float16)
  x,c,ctx,cm,tf,rf=[tensor(v) for v in [noise,cond,context,mask,time_features([1]),time_features([0])]]
  if source is not None:src,km,bm,nt=[tensor(v) for v in [source,keep[...,None],blend[...,None],noise]]
  # Warmup is explicit and included in cold wall time, excluded from warm compute.
  graph_warmup_started=time.monotonic()
  if cold:
   for _ in range(3):fn(x,c,ctx,tf,rf,cm);Device['AMD'].synchronize()
  graph_warmup_seconds=time.monotonic()-graph_warmup_started if cold else 0.
  t=time.monotonic();schedule=np.linspace(1,0,9).tolist()
  for i in range(8):
   Device['AMD'].synchronize();tf.assign(tensor(time_features([schedule[i]]))).realize();v=fn(x,c,ctx,tf,rf,cm);x.assign(x-v*(schedule[i]-schedule[i+1])).realize()
   if source is not None and i<7 and i<round(float(settings.get('repaint_injection_ratio',.5))*8):x.assign(km.where(x,nt*schedule[i+1]+src*(1-schedule[i+1]))).realize()
  if source is not None:x.assign(bm*x+(1-bm)*src).realize()
  Device['AMD'].synchronize();generation=time.monotonic()-t;latent=x.numpy();decode_cold=not self.decoder_ready
  decode_warmup_started=time.monotonic()
  if decode_cold:
   for _ in range(2):self.decoder.decode(latent[:,:min(375,n)])
   self.decoder_ready=True
  decode_warmup_seconds=time.monotonic()-decode_warmup_started if decode_cold else 0.
  wave,decode_seconds=self.decoder.decode(latent)
  prefix=int(np.flatnonzero(keep[0])[0]) if keep is not None else 0
  return wave,latent,{'case':case,'seed':seed,'graph_warmup_seconds':graph_warmup_seconds,'decode_warmup_seconds':decode_warmup_seconds,'cold':cold or decode_cold,'wall_seconds':time.monotonic()-started,'generation_seconds':generation,'decode_seconds':decode_seconds,'duration':n/25,'new_seconds':(n-prefix)/25,'warm_rtf_new_audio':(generation+decode_seconds)/((n-prefix)/25),'prefix_seconds':prefix/25,'preparation_host':'prepared embeddings; no Mac required during this generation','sampler':'Euler8/DCW off','subjective_acceptance':None}
