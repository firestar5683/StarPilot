"""One initial clip plus twenty causal continuations, no route inputs."""
import json
from bundle import OUT
for implementation in ['native','reference']:
 plan=[{'case':'shape_30','seed':33602,'commit_seconds':28,'output':implementation+'_soak45_initial'}]
 previous='cases/shape_30/'+implementation+'_soak45_initial/committed_latents.npy'
 for i in range(20):
  role=(['prechorus','chorus','bridge','outro'][i] if i<4 else ['verse','prechorus','chorus','bridge'][i%4]) if i<19 else 'outro'
  case='window45_'+role;output=implementation+f'_soak45_{i:02d}'
  plan.append({'case':case,'seed':33603+i,'previous':previous,'commit_seconds':36,'output':output})
  previous=f'cases/{case}/{output}/committed_latents.npy'
 (OUT/(implementation+'_soak45_plan.json')).write_text(json.dumps(plan,indent=2))
