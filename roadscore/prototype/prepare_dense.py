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
style=json.loads(Path('/data/roadscore/prototype/styles.json').read_text())['horizon_drive']['prompt']
intents={
 'base':'The band is already in a steady full groove, with audible drums and bass throughout. Continue an evolving instrumental song.',
 'explore':'Keep kick, snare and bass moving. Vary the guitar hook harmonically, introduce a short synth answer and small percussion fills.',
 'develop':'Develop the same song with active bass movement, syncopated rhythm guitar, additional synth counterpoint and denser hi-hat and tom figures.',
 'build':'Build the existing groove through interlocking guitar layers, snare and tom subdivisions and rising melodic tension. Keep the pulse continuous.',
 'peak':'Full energetic band statement of the existing hook, assertive bass, layered guitars, live drums and cymbal accents. Controlled instrumental rock climax.',
 'release':'Resolve the tension, remove the extra lead and cymbal layers, return to steady kick snare bass and the recognizable guitar groove. Keep playing, no fade or silence.',
 'closing':'Closing phrase of this same instrumental band performance. Stop introducing new riffs, repeat and resolve the existing guitar motif, simplify the bass toward a held root, drums play a final measured phrase with space for a resolving chord.'}
intents['approach']=intents['develop']
meta={}
for intent,suffix in intents.items():
 name='horizon_drive_'+intent;prompt=style+' '+suffix;t=time.monotonic()
 with torch.no_grad():
  x=tok([prompt],padding='max_length',max_length=256,truncation=True,return_tensors='pt');e=m(**x).last_hidden_state.numpy();mask=x['attention_mask'].numpy()[...,None]
  pad=np.load(root/'native/conditioner.conditioners.prompt.padding_embedding.npy').astype(np.float32);e=e*mask+pad*(1-mask)
 np.save(out/f'conditioning_{name}.npy',e.astype(np.float16));meta[name]={'prompt':prompt,'encoding_seconds':time.monotonic()-t};print(name,meta[name]['encoding_seconds'],flush=True)
(out/'dense_conditioning.json').write_text(json.dumps(meta,indent=2))
