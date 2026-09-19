"""Narrow ACE DiT port. Equations follow official ACE-Step Apache-2.0 implementation."""
from pathlib import Path
import numpy as np
from tinygrad import Tensor,TinyJit,dtypes

def tensor(x):return Tensor(np.asarray(x),device='AMD').realize()
class DiT:
 def __init__(self,path,layers=24):
  self.w={};self.layers=layers
  for p in sorted(list(Path(path).glob('*.npy'))+list(Path(path).glob('*.npz'))):
   if p.stem.startswith('layers.') and int(p.stem.split('.')[1])>=layers:continue
   if p.suffix=='.npz':
    with np.load(p) as packed:self.w[p.stem]=(tensor(packed['q']).cast(dtypes.float16)*tensor(packed['scale'])).realize()
   else:self.w[p.stem]=tensor(np.load(p))
 def linear(self,x,p):
  y=x@self.w[p+'.weight'].T
  return y+self.w[p+'.bias'] if p+'.bias' in self.w else y
 def rms(self,x,p):
  z=x.float();return (z*(z.square().mean(-1,keepdim=True)+1e-6).rsqrt()).cast(x.dtype)*self.w[p+'.weight']
 def attention(self,x,p,cond=None,cs=None,mask=None):
  b,n,_=x.shape;source=x if cond is None else cond
  def heads(z,h):return z.reshape(b,-1,h,128).transpose(1,2)
  q=self.rms(heads(self.linear(x,p+'.q_proj'),16),p+'.q_norm');k=self.rms(heads(self.linear(source,p+'.k_proj'),8),p+'.k_norm');v=heads(self.linear(source,p+'.v_proj'),8)
  if cs is not None:
   c,s=cs
   def rope(z):return z*c+(-z[...,64:]).cat(z[...,:64],dim=-1)*s
   q,k=rope(q),rope(k)
  k=k.unsqueeze(2).expand(b,8,2,k.shape[2],128).reshape(b,16,-1,128);v=v.unsqueeze(2).expand(b,8,2,v.shape[2],128).reshape(b,16,-1,128)
  scores=(q*(128**-.5))@k.transpose(-1,-2)
  if mask is not None:scores=scores+mask
  z=(scores.float().softmax(-1).cast(v.dtype)@v).transpose(1,2).reshape(b,n,2048)
  return self.linear(z,p+'.o_proj')
 def block(self,x,cond,temb,cs,mask,i=0,cond_mask=None):
  p=f'layers.{i}';shift,scale,gate,shift_ff,scale_ff,gate_ff=(self.w[p+'.scale_shift_table']+temb).chunk(6,dim=1)
  z=(self.rms(x,p+'.self_attn_norm')*(1+scale)+shift).cast(x.dtype)
  x=(x+self.attention(z,p+'.self_attn',cs=cs,mask=mask)*gate).cast(x.dtype)
  x=x+self.attention(self.rms(x,p+'.cross_attn_norm'),p+'.cross_attn',cond=cond,mask=cond_mask)
  z=(self.rms(x,p+'.mlp_norm')*(1+scale_ff)+shift_ff).cast(x.dtype)
  ff=self.linear(self.linear(z,p+'.mlp.gate_proj').silu()*self.linear(z,p+'.mlp.up_proj'),p+'.mlp.down_proj')
  return (x+ff*gate_ff).cast(x.dtype).realize()
 def time_embedding(self,tf,p):
  t=self.linear(self.linear(tf,p+'.linear_1').silu(),p+'.linear_2')
  return t,self.linear(t.silu(),p+'.time_proj').reshape(1,6,2048)
 def prepare_shape(self,n,align_tokens=0):
  self.original=n;valid=(n+1)//2;N=((valid+align_tokens-1)//align_tokens)*align_tokens if align_tokens else valid;self.padded_latents=2*N
  f=np.arange(N,dtype=np.float32)[:,None]/(1000000**(np.arange(0,128,2,dtype=np.float32)/128))[None,:];f=np.concatenate((f,f),-1)[None,None]
  self.cs=(tensor(np.cos(f).astype(np.float16)),tensor(np.sin(f).astype(np.float16)))
  i=np.arange(N);self.mask=tensor(np.where((abs(i[:,None]-i[None,:])<=128)&(i[None,:]<valid),0,-np.inf).astype(np.float16)[None,None]);self.fullmask=tensor(np.where(i<valid,0,-np.inf).astype(np.float16)[None,None,None,:]) if N!=valid else None
 def forward(self,x,cond,context,tf,rf,cond_mask=None):
  b,n,_=x.shape
  t,p=self.time_embedding(tf,'time_embed');tr,pr=self.time_embedding(rf,'time_embed_r');t=t+tr;p=p+pr
  x=context.cat(x,dim=-1)
  if self.padded_latents>n:x=x.pad(((0,0),(0,self.padded_latents-n),(0,0)))
  N=x.shape[1]//2
  x=x.reshape(b,N,2,192).permute(0,1,3,2).reshape(b,N,384)@self.w['proj_in.1.weight'].reshape(2048,384).T+self.w['proj_in.1.bias']
  cond=self.linear(cond,'condition_embedder')
  for i in range(self.layers):x=self.block(x,cond,p,self.cs,self.mask if i%2==0 else self.fullmask,i,cond_mask)
  shift,scale=(self.w['scale_shift_table']+t.unsqueeze(1)).chunk(2,dim=1)
  x=(self.rms(x,'norm_out')*(1+scale)+shift).cast(x.dtype)
  x=x@self.w['proj_out.1.weight'].reshape(2048,128)
  return (x.reshape(b,N,64,2).permute(0,1,3,2).reshape(b,N*2,64)+self.w['proj_out.1.bias'])[:,:n].realize()

def time_features(t):
 f=np.exp(-np.log(10000)*np.arange(128,dtype=np.float32)/128);v=np.asarray(t,dtype=np.float32).reshape(-1,1)*1000*f[None,:]
 return np.concatenate((np.cos(v),np.sin(v)),-1).astype(np.float16)
