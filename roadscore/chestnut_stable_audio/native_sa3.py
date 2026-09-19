"""Narrow trained-weight SA3 Small-Music port. No PyTorch backend bridge.
Reference: Stability-AI/stable-audio-3 @ 779434a908193105335fd8d833418603625b2859.
"""
from pathlib import Path
import numpy as np
from tinygrad import Tensor,TinyJit,dtypes

def tensor(a):return Tensor(np.asarray(a),device='AMD').realize()
def fourier(values):
 f=np.exp(np.linspace(np.log(.5),np.log(10000.),128,dtype=np.float32))*np.float32(2*np.pi)
 args=np.asarray(values,dtype=np.float32).reshape(-1,1)*f
 return np.concatenate([np.cos(args),np.sin(args)],axis=-1).astype(np.float16)
class Weights:
 def __init__(self,path,prefix):
  self.w={}
  for f in sorted(Path(path).glob(prefix+'*.npy')):
   self.w[f.stem[len(prefix):]]=tensor(np.load(f))
 def linear(self,x,p):
  w=self.w[p+'.weight'];y=x.cast(w.dtype)@w.T
  if p+'.bias' in self.w:y=y+self.w[p+'.bias'].cast(y.dtype)
  return y
 def mlp(self,x,p):return self.linear(self.linear(x,p+'.0').silu(),p+'.2')
 def rms(self,x,p,eps=1e-5):
  z=x.float();z=z*(z.square().mean(-1,keepdim=True)+eps).rsqrt()
  return (z*self.w[p+'.gamma'].float()).cast(x.dtype)
 def dyt(self,x,p):
  return (self.w[p+'.gamma'].float()*(self.w[p+'.alpha'].float()*x.float()).tanh()+self.w[p+'.beta'].float()).cast(x.dtype)
 def ff(self,x,p):
  a,b=self.linear(x,p+'.ff.0.proj').chunk(2,dim=-1)
  return self.linear(a*b.silu(),p+'.ff.2')
 @staticmethod
 def attention(q,k,v):
  return (((q*.125)@k.transpose(-1,-2)).float().softmax(-1).cast(v.dtype)@v)
 @staticmethod
 def rope_tables(n):
  inv=1./10000**(np.arange(0,32,2,dtype=np.float32)/32)
  f=np.arange(n,dtype=np.float32)[:,None]*inv[None,:]
  return tensor(np.cos(f)),tensor(np.sin(f))
 @staticmethod
 def rope(x,cs):
  c,s=cs;a,b=x[...,:16].float(),x[...,16:32].float()
  return (a*c-b*s).cat(a*s+b*c,dim=-1).cast(x.dtype).cat(x[...,32:],dim=-1)

class DiT(Weights):
 def __init__(self,path,persistent=False):
  super().__init__(path,'model.model.')
  self.jits={};self.ropes={};self.inputs={};self.persistent=persistent
 def forward(self,x,tf,cond,global_cond,local):
  B,T,D=x.shape
  context=self.mlp(cond,'to_cond_embed')
  g=self.mlp(global_cond,'to_global_embed')+self.mlp(tf,'to_timestep_embed')
  g=self.mlp(g,'transformer.global_cond_embedder')
  x=x+x@self.w['preprocess_conv.weight'][:,:,0].T
  x=self.linear(x,'transformer.project_in')
  x=self.w['transformer.memory_tokens'].unsqueeze(0).expand(B,64,1024).cat(x,dim=1)
  N=T+64;cs=self.ropes[T]
  def heads(a):return a.reshape(B,-1,16,64).transpose(1,2)
  for i in range(20):
   p=f'transformer.layers.{i}.'
   a,b,c,d,e,f=(g+self.w[p+'to_scale_shift_gate']).unsqueeze(1).chunk(6,dim=-1)
   z=self.rms(x,p+'pre_norm')*(1+a)+b
   q,k,v=[heads(t) for t in self.linear(z,p+'self_attn.to_qkv').chunk(3,dim=-1)]
   q=self.rope(self.rms(q,p+'self_attn.q_norm',1e-6),cs)
   k=self.rope(self.rms(k,p+'self_attn.k_norm',1e-6),cs)
   att=self.attention(q,k,v).transpose(1,2).reshape(B,N,1024)
   x=x+self.linear(att,p+'self_attn.to_out')*(1-c).sigmoid()
   q=self.rms(heads(self.linear(self.rms(x,p+'cross_attend_norm'),p+'cross_attn.to_q')),p+'cross_attn.q_norm',1e-6)
   k,v=[heads(t) for t in self.linear(context,p+'cross_attn.to_kv').chunk(2,dim=-1)]
   k=self.rms(k,p+'cross_attn.k_norm',1e-6)
   att=self.attention(q,k,v).transpose(1,2).reshape(B,N,1024)
   x=x+self.linear(att,p+'cross_attn.to_out')
   loc=self.mlp(local,p+'to_local_embed').pad(((0,0),(64,0),(0,0)))
   x=x+loc
   x=(x+self.ff(self.rms(x,p+'ff_norm')*(1+d)+e,p+'ff')*(1-f).sigmoid()).realize()
  x=self.linear(x[:,64:],'transformer.project_out')
  return (x+x@self.w['postprocess_conv.weight'][:,:,0].T).realize()
 def __call__(self,x,tf,cond,g,local):
  n=x.shape[1]
  if n not in self.jits:
   self.ropes[n]=self.rope_tables(n+64);self.jits[n]=TinyJit(self.forward)
  if self.persistent:
   if n not in self.inputs:self.inputs[n]=(x.clone().realize(),tf.clone().realize())
   xi,ti=self.inputs[n];xi.assign(x).realize();ti.assign(tf).realize()
   return self.jits[n](xi,ti,cond,g,local)
  return self.jits[n](x,tf,cond,g,local)

class Decoder(Weights):
 def __init__(self,path):
  super().__init__(path,'pretransform.model.decoder.')
  self.std=tensor(np.load(Path(path)/'pretransform.model.bottleneck.running_std.npy'))
  self.ropes=self.rope_tables(34);self.jits={}
  # Converter folds weight normalization before casting.
 def block(self,x,i):
  B,T,D=x.shape;p=f'layers.3.transformers.{i}.'
  def heads(a):return a.reshape(B,T,12,64).transpose(1,2)
  q,k,v,qd,kd=[heads(t) for t in self.linear(self.dyt(x,p+'pre_norm'),p+'self_attn.to_qkv').chunk(5,dim=-1)]
  q,qd=[self.rope(self.dyt(a,p+'self_attn.q_norm'),self.ropes) for a in [q,qd]]
  k,kd=[self.rope(self.dyt(a,p+'self_attn.k_norm'),self.ropes) for a in [k,kd]]
  att=(self.attention(q,k,v)-self.attention(qd,kd,v)).transpose(1,2).reshape(B,T,D)
  x=x+self.linear(att,p+'self_attn.to_out')
  return (x+self.ff(self.dyt(x,p+'ff_norm'),p+'ff')).realize()
 def forward(self,latents):
  B,T,C=latents.shape
  x=self.linear((latents.float()*self.std.float()).cast(latents.dtype),'layers.1')
  nt=self.w['layers.3.new_tokens'].reshape(1,1,1,768).expand(B,T,16,768)
  x=x.unsqueeze(2).cat(nt,dim=2).reshape(B*T//2,34,768)
  for i in range(3):x=self.block(x,i)
  x=x.reshape(B,T*17,768)
  x=x[:,:17].cat(x,x[:,-17:],dim=1).reshape(B*(T//2+1),34,768)
  for i in range(3,6):x=self.block(x,i)
  x=x.reshape(B,(T+2)*17,768)[:,17:-17].reshape(B,T,17,768)[:,:,1:].reshape(B,T*16,768)
  padded=x.pad(((0,0),(1,1),(0,0)));w=self.w['layers.3.mapping.weight']
  out=sum(padded[:,i:i+T*16]@w[:,:,i].T for i in range(3))+self.w['layers.3.mapping.bias']
  return out.reshape(B,T*16,2,256).permute(0,2,1,3).reshape(B,2,T*4096).realize()
 def __call__(self,x):
  n=x.shape[1]
  if n not in self.jits:self.jits[n]=TinyJit(self.forward)
  return self.jits[n](x)
