"""Per-output-row symmetric int8 storage; dequantize once into FP16 GPU weights.
This tests transport/startup and quality, not reduced resident matmul precision.
"""
from pathlib import Path
import numpy as np,json
P=Path(__file__).resolve().parent;O=P/'weights_int8';O.mkdir(exist_ok=True);before=after=0;count=0
for path in (P/'weights').glob('*.npy'):
 a=np.load(path);before+=a.nbytes
 if a.ndim==2 and path.stem.endswith('.weight'):
  scale=np.maximum(np.max(abs(a.astype(np.float32)),axis=1,keepdims=True)/127,1e-8).astype(np.float16)
  q=np.clip(np.round(a/scale),-127,127).astype(np.int8);np.savez(O/(path.stem+'.npz'),q=q,scale=scale);after+=q.nbytes+scale.nbytes;count+=1
 else:np.save(O/path.name,a);after+=a.nbytes
(P/'int8_storage.json').write_text(json.dumps({'scheme':'row symmetric int8, FP16 scale, GPU dequantize once at load; FP16 resident computation','baseline_payload_bytes':before,'quantized_payload_bytes':after,'quantized_matrices':count},indent=2));print(before,after,count,flush=True)
