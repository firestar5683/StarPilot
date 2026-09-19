"""Diagnostic variant: FP32 residual accumulation, FP16 expensive matrix products."""
from native_ace import DiT as Base,tensor,time_features
from tinygrad import dtypes
class DiT(Base):
 def block(self,x,cond,temb,cs,mask,i=0,cond_mask=None):
  p=f'layers.{i}';shift,scale,gate,shift_ff,scale_ff,gate_ff=(self.w[p+'.scale_shift_table']+temb).chunk(6,dim=1)
  x=x.float();z=(self.rms(x,p+'.self_attn_norm')*(1+scale.float())+shift.float()).cast(dtypes.float16)
  x=x+self.attention(z,p+'.self_attn',cs=cs,mask=mask).float()*gate.float()
  x=x+self.attention(self.rms(x,p+'.cross_attn_norm').cast(dtypes.float16),p+'.cross_attn',cond=cond,mask=cond_mask).float()
  z=(self.rms(x,p+'.mlp_norm')*(1+scale_ff.float())+shift_ff.float()).cast(dtypes.float16)
  ff=self.linear(self.linear(z,p+'.mlp.gate_proj').silu()*self.linear(z,p+'.mlp.up_proj'),p+'.mlp.down_proj')
  return (x+ff.float()*gate_ff.float()).realize()
 def forward(self,x,cond,context,tf,rf,cond_mask=None):
  b,n,_=x.shape;t,p=self.time_embedding(tf,'time_embed');tr,pr=self.time_embedding(rf,'time_embed_r');t=t+tr;p=p+pr
  x=context.cat(x,dim=-1)
  if self.padded_latents>n:x=x.pad(((0,0),(0,self.padded_latents-n),(0,0)))
  N=x.shape[1]//2
  x=x.reshape(b,N,2,192).permute(0,1,3,2).reshape(b,N,384)@self.w['proj_in.1.weight'].reshape(2048,384).T+self.w['proj_in.1.bias']
  cond=self.linear(cond,'condition_embedder')
  for i in range(self.layers):x=self.block(x,cond,p,self.cs,self.mask if i%2==0 else self.fullmask,i,cond_mask)
  shift,scale=(self.w['scale_shift_table']+t.unsqueeze(1)).chunk(2,dim=1)
  x=(self.rms(x,'norm_out')*(1+scale.float())+shift.float()).cast(dtypes.float16)
  x=x@self.w['proj_out.1.weight'].reshape(2048,128)
  return (x.reshape(b,N,64,2).permute(0,1,3,2).reshape(b,N*2,64)+self.w['proj_out.1.bias'])[:,:n].realize()
