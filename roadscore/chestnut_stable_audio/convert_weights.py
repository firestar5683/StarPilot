"""Bounded-memory safetensors -> FP16 NPY native weights; no pickle deserialization."""
import json,struct
from pathlib import Path
import numpy as np
ROOT=Path('/tmp/chestnut-sa3-weights');OUT=ROOT/'native';OUT.mkdir(exist_ok=True)
with (ROOT/'model.safetensors').open('rb') as f:
 n=struct.unpack('<Q',f.read(8))[0];h=json.loads(f.read(n));base=8+n
 def get(k):
  v=h[k];f.seek(base+v['data_offsets'][0]);a=np.frombuffer(f.read(v['data_offsets'][1]-v['data_offsets'][0]),dtype={'F32':'<f4','F16':'<f2'}[v['dtype']]).reshape(v['shape'])
  return a
 count=0
 for k,v in h.items():
  if k=='__metadata__':continue
  if not k.startswith(('model.model.','pretransform.model.decoder.','pretransform.model.bottleneck.running_std','conditioner.')):continue
  np.save(OUT/(k+'.npy'),get(k).astype(np.float16));count+=1
 prefix='pretransform.model.decoder.layers.3.mapping'
 w=get(prefix+'.weight_v');g=get(prefix+'.weight_g')
 np.save(OUT/(prefix+'.weight.npy'),(w*g/np.sqrt(np.sum(w*w,axis=(1,2),keepdims=True))).astype(np.float16))
print('NATIVE_TENSORS',count,'BYTES',sum(p.stat().st_size for p in OUT.glob('*.npy')))
with (ROOT/'t5gemma-b-b-ul2/model.safetensors').open('rb') as f:
 n=struct.unpack('<Q',f.read(8))[0];h=json.loads(f.read(n))
print('TEXT_KEYS',list(h)[:12]);print('TEXT_DTYPES',set(v.get('dtype') for v in h.values()))
