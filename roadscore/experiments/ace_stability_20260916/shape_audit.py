"""Duration evidence includes incomplete/failed shapes, never silently drops them."""
import json
import numpy as np
from bundle import OUT
rows=[]
for seconds in [15,20,24,28,30,32,36,40,45,48,52,56,60]:
 p=OUT/'cases'/f'shape_{seconds}';n=p/'native_0';ref=p/'reference_rounded'
 if seconds==30:n=p/'native_adaptive_initial';ref=p/'reference_adaptive_initial'
 row={'seconds':seconds,'latent_frames':seconds*25,'attention_tokens':(seconds*25+1)//2}
 row['native_directory']=str(n.relative_to(OUT))
 row['reference_directory']=str(ref.relative_to(OUT))
 if (n/'report.json').exists():
  r=json.loads((n/'report.json').read_text());row.update(status='completed',**{k:r.get(k) for k in ['generation_seconds','decode_seconds','rtf','warmup_seconds','host_peak_mib','tracked_gpu_peak','physical_vram_used_including_allocator_cache','finite']})
 else:row['status']='decode failed' if seconds==56 else 'pending'
 if (n/'latents.npy').exists() and (ref/'latents.npy').exists():
  a=np.load(n/'latents.npy').astype(np.float64);b=np.load(ref/'latents.npy').astype(np.float64)
  row['final_latent_relative_rmse']=float(np.linalg.norm(a-b)/np.linalg.norm(b));row['final_latent_peak_relative_error']=float(abs(a-b).max()/abs(b).max())
 rows.append(row)
(OUT/'shape_audit.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
