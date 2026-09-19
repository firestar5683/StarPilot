"""One initial clip plus twenty causal continuations, no route inputs."""
import json
from bundle import OUT
for implementation in ['native','reference']:
 plan=[{'case':'shape_30','seed':33602,'commit_seconds':28,'output':implementation+'_soak_initial'}]
 previous='cases/shape_30/'+implementation+'_soak_initial/committed_latents.npy'
 for i in range(20):
  role=['verse','prechorus','chorus','bridge'][i%4] if i<19 else 'outro'
  case='window48_'+role;output=implementation+f'_soak_{i:02d}'
  plan.append({'case':case,'seed':33603+i,'previous':previous,'commit_seconds':40,'output':output})
  previous=f'cases/{case}/{output}/committed_latents.npy'
 (OUT/(implementation+'_soak_plan.json')).write_text(json.dumps(plan,indent=2))
