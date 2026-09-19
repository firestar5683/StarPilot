"""Narrow experimental MusicGen Small decoder, weights from Transformers. No training."""
import numpy as np
from tinygrad import Tensor, TinyJit, Variable, dtypes

class NativeDecoder:
 def __init__(self, decoder, conditioning, mask, max_length):
  self.weights={}
  for name,p in decoder.named_parameters():
   self.weights[name]=Tensor(p.detach().numpy().copy(),device='AMD').realize()
  self.max_length=max_length
  self.enc=Tensor(conditioning.numpy().astype(np.float16),device='AMD').realize()
  self.mask=Tensor(((1-mask.numpy())*-65504.).astype(np.float16),device='AMD').reshape(2,1,1,-1).realize()
  self.caches=[]; self.cross=[]
  for i in range(24):
   prefix=f'model.decoder.layers.{i}.'
   self.caches.append(Tensor.zeros(2,2,16,max_length,64,device='AMD',dtype=dtypes.float16).contiguous().realize())
   k=self.linear(self.enc,prefix+'encoder_attn.k_proj').reshape(2,-1,16,64).transpose(1,2)
   v=self.linear(self.enc,prefix+'encoder_attn.v_proj').reshape(2,-1,16,64).transpose(1,2)
   k.realize(v); self.cross.append((k,v))
  self.run_jit=TinyJit(self.forward)
 def linear(self,x,prefix):
  out=x.linear(self.weights[prefix+'.weight'].T)
  if prefix+'.bias' in self.weights: out=out+self.weights[prefix+'.bias']
  return out
 def norm(self,x,prefix):
  return x.float().layernorm(eps=1e-5).cast(x.dtype)*self.weights[prefix+'.weight']+self.weights[prefix+'.bias']
 def attention(self,q,k,v):
  scores=(q*0.125)@k.transpose(-1,-2)
  return scores.float().softmax(-1).cast(q.dtype)@v
 def forward(self,ids,pos):
  x=sum(self.weights[f'model.decoder.embed_tokens.{c}.weight'][ids[:,c]] for c in range(4)).reshape(2,1,1024)
  x=x+self.weights['model.decoder.embed_positions.weights'][pos:pos+1]
  for i in range(24):
   p=f'model.decoder.layers.{i}.'
   z=self.norm(x,p+'self_attn_layer_norm')
   q=self.linear(z,p+'self_attn.q_proj').reshape(2,1,16,64).transpose(1,2)
   k=self.linear(z,p+'self_attn.k_proj').reshape(2,1,16,64).transpose(1,2)
   v=self.linear(z,p+'self_attn.v_proj').reshape(2,1,16,64).transpose(1,2)
   cache=self.caches[i]
   cache[:,:,:,pos:pos+1,:].assign(Tensor.stack(k,v)).realize()
   a=self.attention(q,cache[0,:,:,:pos+1,:],cache[1,:,:,:pos+1,:]).transpose(1,2).reshape(2,1,1024)
   x=x+self.linear(a,p+'self_attn.out_proj')
   z=self.norm(x,p+'encoder_attn_layer_norm')
   q=self.linear(z,p+'encoder_attn.q_proj').reshape(2,1,16,64).transpose(1,2)
   k,v=self.cross[i]
   scores=(q*0.125)@k.transpose(-1,-2)+self.mask
   a=(scores.float().softmax(-1).cast(q.dtype)@v).transpose(1,2).reshape(2,1,1024)
   x=x+self.linear(a,p+'encoder_attn.out_proj')
   z=self.norm(x,p+'final_layer_norm')
   x=(x+self.linear(self.linear(z,p+'fc1').gelu(approximate='none'),p+'fc2')).realize()
  x=self.norm(x,'model.decoder.layer_norm')
  return Tensor.stack(*[self.linear(x,f'lm_heads.{c}') for c in range(4)],dim=1).reshape(8,2048).realize()
 def __call__(self,ids,pos):
  t=Tensor(ids.numpy().astype(np.int32).reshape(2,4),device='AMD').realize()
  result=self.run_jit(t,Variable('pos',0,self.max_length-1).bind(pos))
  return result.float().numpy()
