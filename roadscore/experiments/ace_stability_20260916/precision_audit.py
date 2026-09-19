"""Compare narrow precision diagnostics without treating teacher forcing as generation."""
import json
import numpy as np
from bundle import OUT

def error(a,b):
 a=a.astype(np.float64);b=b.astype(np.float64);d=a-b
 return {'relative_rmse':float(np.linalg.norm(d)/np.linalg.norm(b)),
         'peak_relative_error':float(abs(d).max()/abs(b).max())}

rows={}
for name in ['circuit_30','prism_45','prism_30']:
 p=OUT/'cases'/name;ref=np.load(p/'reference_rounded/latents.npy')
 row={}
 for variant in ['native_0','native_mixed','reference_fp16']:
  if (p/variant/'latents.npy').exists():
   row[variant]=error(np.load(p/variant/'latents.npy'),ref)
   report=json.loads((p/variant/'report.json').read_text())
   row[variant]['rtf']=report.get('rtf')
 rows[name]=row
p=OUT/'cases/circuit_30'
if (p/'reference_teacher/report.json').exists():
 rows['circuit_teacher_forced_velocity']=[{'step':i,**error(np.load(p/f'native_teacher/velocity_{i}.npy'),np.load(p/f'reference_teacher/velocity_{i}.npy'))} for i in range(8)]
 rows['teacher_note']='Each step receives the same rounded official input. Diagnostic only, not an end-to-end generation.'
(OUT/'precision_audit.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
