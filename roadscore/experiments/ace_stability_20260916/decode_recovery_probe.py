"""Isolate saved56s latents from DiT/shape changes, with trace and physical VRAM audit."""
import os
os.environ.setdefault('TC_OPT','2')
import sys,time,json,fcntl,resource,hashlib
import numpy as np
import soundfile as sf
from bundle import R,OLD,OUT
sys.path.insert(0,str(OLD))
from native_vae import VAE
from observed_decode import ChunkDecoder
from tinygrad import Device
lock=open(R/'generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
run_name=os.environ.get('ACE_DECODE_PROBE_NAME','decode56_recovery')
if not run_name.replace('_','').isalnum():raise ValueError('Invalid local probe name')
z=np.load(OUT/'cases/shape_56/native_0/latents.npy');decoder=ChunkDecoder(VAE(OLD/'vae_weights'));reports=[]
for i in range(5):
 print('DECODE_ONLY_BEGIN',i,flush=True);wave,t=decoder.decode(z);a=Device['AMD'].iface.dev_impl.mm.pa_allocator
 reports.append({'repeat':i,'seconds':t,'finite':bool(np.isfinite(wave).all()),'pcm_sha256':hashlib.sha256(wave.tobytes()).hexdigest(),'host_peak_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'physical_vram_used':sum(s for s,_,_,free in a.blocks.values() if not free),'shape':z.shape});(OUT/(run_name+'.json')).write_text(json.dumps(reports,indent=2));print('DECODE_ONLY_DONE',reports[-1],flush=True)
 if i==0:sf.write(OUT/(run_name+'.wav'),wave*.65,48000,subtype='FLOAT')
