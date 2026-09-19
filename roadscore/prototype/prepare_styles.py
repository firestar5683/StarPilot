"""One local CPU encoding pass for optional navigation composition; no network access."""
import os,time,json
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
from pathlib import Path
import numpy as np,torch
from transformers import AutoTokenizer,AutoConfig,T5GemmaEncoderModel
root=Path('/data/sa3-feasibility');out=Path('/data/roadscore/assets');out.mkdir(exist_ok=True);torch.set_num_threads(4)
p=str(root/'t5gemma-b-b-ul2');cfg=AutoConfig.from_pretrained(p,local_files_only=True);cfg.is_encoder_decoder=False
tok=AutoTokenizer.from_pretrained(p,local_files_only=True,use_fast=False)
m=T5GemmaEncoderModel.from_pretrained(p,config=cfg,local_files_only=True,torch_dtype=torch.float32,low_cpu_mem_usage=True).eval()
styles=json.loads(Path('/data/roadscore/prototype/styles.json').read_text())
prompts={}
for key,style in styles.items():
 for intent,suffix in {'base':' Maintain a continuous evolving performance.', 'approach':' Develop the same recurring theme with a more active accompaniment and layered instrumental answers, preparing a larger phrase without changing genre.', 'closing':' Final resolving phrase of the same theme, settle onto a warm sustained final chord, let the instruments ring naturally to silence.'}.items():
  prompts[f'{key}_{intent}']=style['prompt']+suffix
meta={}
for name,prompt in prompts.items():
 t=time.monotonic()
 with torch.no_grad():
  x=tok([prompt],padding='max_length',max_length=256,truncation=True,return_tensors='pt');e=m(**x).last_hidden_state.numpy();mask=x['attention_mask'].numpy()[...,None]
  pad=np.load(root/'native/conditioner.conditioners.prompt.padding_embedding.npy').astype(np.float32);e=e*mask+pad*(1-mask)
 np.save(out/f'conditioning_{name}.npy',e.astype(np.float16));meta[name]={'prompt':prompt,'encoding_seconds':time.monotonic()-t};print(name,meta[name]['encoding_seconds'],flush=True)
(out/'styles_conditioning.json').write_text(json.dumps(meta,indent=2))
