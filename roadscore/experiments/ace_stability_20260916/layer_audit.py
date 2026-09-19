"""Numerical layer localization; no listening or bit-equivalence claim across hardware."""
import json
import numpy as np
from bundle import OUT
p=OUT/'cases/circuit_30';rows={}
def error(a,b):
 a=a.astype(np.float64);b=b.astype(np.float64)
 return {'relative_rmse':float(np.linalg.norm(a-b)/np.linalg.norm(b)),'peak_relative_error':float(abs(a-b).max()/abs(b).max())}
for step in [0,7]:
 rows[str(step)]=[{'layer':i,'attention':'sliding' if i%2==0 else 'full',**error(np.load(p/f'layers_native/step_{step}_layer_{i}.npy'),np.load(p/f'layers_reference/step_{step}_layer_{i}.npy'))} for i in range(24)]
 rows[f'{step}_probe_vs_jit_velocity']=error(np.load(p/f'layers_native/step_{step}_velocity.npy'),np.load(p/f'native_teacher/velocity_{step}.npy'))
(OUT/'layer_audit.json').write_text(json.dumps(rows,indent=2))
