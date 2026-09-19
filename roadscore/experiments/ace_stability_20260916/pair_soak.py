"""Re-run official reference with each native job's actual incoming latent prefix."""
import json,os,shutil
import numpy as np
from bundle import OUT
plan=json.loads((OUT/'native_soak45_plan.json').read_text())
for i,j in enumerate(plan[1:5]):
 source=OUT/'cases'/j['case'];native=source/j['output']
 if not (native/'report.json').exists():continue
 p=OUT/'cases'/('paired45_'+j['case'].split('_')[-1]);p.mkdir(exist_ok=True)
 for key in ['encoder_hidden_states','encoder_attention_mask','mask']:
  shutil.copy2(source/(key+'.npy'),p/(key+'.npy'))
 for target,key in [('noise','noise'),('source','source'),('context_latents','context')]:shutil.copy2(native/('input_'+key+'.npy'),p/(target+'.npy'))
 meta=json.loads((source/'case.json').read_text());meta['name']=p.name;meta['paired_native_job']=j;meta['seed']=j['seed'];(p/'case.json').write_text(json.dumps(meta,indent=2))
 link=p/'native_0'
 if not link.exists():link.symlink_to(os.path.relpath(native,p),target_is_directory=True)
 print(p.name)
