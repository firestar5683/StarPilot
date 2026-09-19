import json,struct,shutil
from pathlib import Path
import numpy as np
from safetensors.numpy import save_file
src=Path('/data/roadscore-feasibility/musicgen-small'); dst=Path('/data/roadscore-feasibility/musicgen-small-fp16'); dst.mkdir(exist_ok=True)
for p in list(src.glob('*.json'))+list(src.glob('*.model')): shutil.copy2(p,dst/p.name)
weight_map={}; shard={}; size=0; total=0; idx=0

def flush():
 global shard,size,idx
 if not shard: return
 name=f'model-{idx:03}.safetensors'; save_file(shard,str(dst/name),metadata={'format':'pt'})
 weight_map.update({k:name for k in shard}); print(name,size,flush=True);idx+=1;shard={};size=0
with open(src/'model.safetensors','rb') as f:
 n=struct.unpack('<Q',f.read(8))[0]; h=json.loads(f.read(n)); start=8+n
 for key,info in h.items():
  if key=='__metadata__': continue
  lo,hi=info['data_offsets'];f.seek(start+lo)
  dt={'F32':np.float32,'F16':np.float16,'I64':np.int64,'I32':np.int32}[info['dtype']]
  arr=np.frombuffer(f.read(hi-lo),dtype=dt).reshape(info['shape'])
  if dt==np.float32: arr=arr.astype(np.float16)
  if size+arr.nbytes>64*1024**2: flush()
  shard[key]=arr;size+=arr.nbytes;total+=arr.nbytes
 flush()
(dst/'model.safetensors.index.json').write_text(json.dumps({'metadata':{'total_size':total},'weight_map':weight_map}))
print('DONE',total)
