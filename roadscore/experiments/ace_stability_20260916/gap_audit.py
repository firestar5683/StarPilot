"""Measure generated quiet regions in boundary counterfactuals, without editing audio."""
import json
import numpy as np,soundfile as sf
from bundle import OUT
rows=[]
for p in sorted((OUT/'cases').glob('live_*/reference*/audio.wav')):
 mask=np.load(p.parent.parent/'mask.npy');prefix=np.flatnonzero(mask[0])[0]/25;a,s=sf.read(p);n=s//10;e=np.sqrt(np.mean(a[:len(a)//n*n].reshape(-1,n,2)**2,axis=(1,2)));q=e[int(prefix*10):360]<.003;sp=[];start=None
 for i,v in enumerate(list(q)+[False]):
  if v and start is None:start=i
  if not v and start is not None:
   if i-start>=10:sp.append([prefix+start/10,prefix+i/10])
   start=None
 rows.append({'case':p.parent.parent.name,'output':p.parent.name,'prefix_seconds':prefix,'quiet_spans':sp,'max_quiet_seconds':max([b-a for a,b in sp],default=0)})
(OUT/'live_gap_audit.json').write_text(json.dumps(rows,indent=2))
for r in rows:print(r)
