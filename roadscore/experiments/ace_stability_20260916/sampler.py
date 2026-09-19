"""Portable exact Haar DCW algebra for diagnostic sampler parity."""
import numpy as np

def dcw(x_next,denoised,t,settings):
 if not settings.get('dcw_enabled',False):return x_next
 assert settings.get('dcw_wavelet','haar')=='haar'
 mode=settings.get('dcw_mode','double');n=x_next.shape[1];x=x_next.astype(np.float32);y=denoised.astype(np.float32)
 if n%2:x=np.pad(x,((0,0),(0,1),(0,0)));y=np.pad(y,((0,0),(0,1),(0,0)))
 s=np.float32(2**-.5);xl=(x[:,::2]+x[:,1::2])*s;xh=(x[:,::2]-x[:,1::2])*s;yl=(y[:,::2]+y[:,1::2])*s;yh=(y[:,::2]-y[:,1::2])*s;scale=settings.get('dcw_scaler',.05)
 if mode in ('low','double'):xl+=t*scale*(xl-yl)
 if mode in ('high','double'):xh+=(1-t)*(settings.get('dcw_high_scaler',.02) if mode=='double' else scale)*(xh-yh)
 assert mode in ('low','high','double')
 return np.stack(((xl+xh)*s,(xl-xh)*s),axis=2).reshape(x.shape)[:,:n]
