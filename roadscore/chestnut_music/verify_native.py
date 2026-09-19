import time,json
from pathlib import Path
import numpy as np,torch
from transformers import AutoProcessor,MusicgenForConditionalGeneration
from transformers.utils import logging
logging.set_verbosity_error();torch.set_num_threads(2)
root=Path('/data/roadscore-feasibility');path=str(root/'musicgen-small-fp16')
report=json.loads((root/'bench8_result.json').read_text())
processor=AutoProcessor.from_pretrained(path,local_files_only=True)
model=MusicgenForConditionalGeneration.from_pretrained(path,local_files_only=True,torch_dtype=torch.float16,low_cpu_mem_usage=True,attn_implementation='eager').eval()
model.text_encoder.float();model.enc_to_dec_proj.float()
checks=[]
with torch.no_grad():
 inputs=processor(text=[report['prompt']],padding=True,return_tensors='pt')
 enc=model.text_encoder(**inputs).last_hidden_state
 enc=torch.cat([enc,torch.zeros_like(enc)],0);enc=model.enc_to_dec_proj(enc)
 mask=torch.cat([inputs['attention_mask'],torch.zeros_like(inputs['attention_mask'])],0)
 enc=(enc*mask[...,None]).half()
 for r in range(2):
  cache=None
  for step in range(1,5):
   d=np.load(root/f'bench8_r{r}_step{step}.npz')
   out=model.decoder(input_ids=torch.from_numpy(d['inputs']),encoder_hidden_states=enc,encoder_attention_mask=mask,past_key_values=cache,use_cache=True,return_dict=True)
   cache=out.past_key_values;ref=out.logits[:,-1].float().numpy();actual=d['logits']
   c=dict(run=r,step=step,mae=float(np.abs(ref-actual).mean()),max_error=float(np.abs(ref-actual).max()),cosine=float(np.dot(ref.ravel(),actual.ravel())/(np.linalg.norm(ref)*np.linalg.norm(actual))))
   checks.append(c);print(c,flush=True)
   assert np.isfinite(actual).all() and c['cosine']>.999,c
(root/'validation.json').write_text(json.dumps({'passed':True,'checks':checks},indent=2))
print('ALL_CACHED_STEPS_MATCH',flush=True)
