"""Retain active generated music; never pass a model's terminal fade as the next prefix."""
import numpy as np

def retained_end(wave,rate,prefix_seconds,target_seconds,allow_fade=False):
 target_frames=round(target_seconds*25);prefix_frames=round(prefix_seconds*25)
 target_samples=min(len(wave),round(target_frames*rate/25));bins=target_samples//rate
 if bins<2:raise ValueError('ACE output is too short for endpoint validation')
 rms=np.sqrt(np.mean(np.asarray(wave[:bins*rate],dtype=np.float64).reshape(bins,rate,-1)**2,axis=(1,2)))
 first=min(bins-1,int(np.ceil(prefix_seconds)));reference=float(np.quantile(rms[first:max(first+1,bins-2)],.6));threshold=max(.003,reference*.25)
 end=target_frames;trimmed=False
 if not allow_fade:
  if reference<.003:raise ValueError('Generated continuation has no usable musical energy')
  while end>prefix_frames and rms[min(bins-1,int(np.ceil(end/25))-1)]<threshold:
   end=max(prefix_frames,(int(np.ceil(end/25))-1)*25);trimmed=True
  if end-prefix_frames<18*25:raise ValueError('Model ended too early for the bounded continuation budget')
 return end,{'requested_commit_seconds':target_seconds,'committed_seconds':end/25,'endpoint_trimmed':trimmed,'energy_reference_rms':reference,'terminal_energy_threshold':threshold,'allow_intentional_fade':allow_fade,'policy':'retain fixed interior unless its terminal energy is below25% of generated active level; whole-second endpoints on exact latent frames'}
