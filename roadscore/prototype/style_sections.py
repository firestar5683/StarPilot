"""Small secondary-style check using the same retained-context strategy."""
import argparse,json,time,shutil,os
from pathlib import Path
import numpy as np
from genre_experiment import FAMILIES
R=Path('/data/roadscore');O=R/'results/overnight/styles';G=R/'generated'
PROMPTS={
'nightshift':{'verse':'Restrained VERSE with bass groove, small arp and sparse pads.','chorus':'Large CHORUS, wide layered polysynth harmony, soaring lead, fuller bass and stronger drums.','bridge':'Contrasting BRIDGE, related borrowed harmonic color, different synth lead texture; preserve pulse and song identity.'},
'brassline':{'verse':'Stable tight funk groove, short keyboard answers and restrained rhythm guitar.','build':'A rising drum fill and melodic keyboard pickup over the same locked bass groove, preparing a playful solo.','solo':'Expressive playful improvised electric keyboard solo with fast answering phrases and bluesy syncopation over the same tight funk band groove; return to the recurring bass riff.'}}
def encode():
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
 import torch
 from transformers import AutoTokenizer,AutoConfig,T5GemmaEncoderModel
 torch.set_num_threads(4);p='/data/sa3-feasibility/t5gemma-b-b-ul2';cfg=AutoConfig.from_pretrained(p,local_files_only=True);cfg.is_encoder_decoder=False
 tok=AutoTokenizer.from_pretrained(p,local_files_only=True,use_fast=False);m=T5GemmaEncoderModel.from_pretrained(p,config=cfg,local_files_only=True,torch_dtype=torch.float32,low_cpu_mem_usage=True).eval();pad=np.load('/data/sa3-feasibility/native/conditioner.conditioners.prompt.padding_embedding.npy').astype(np.float32);meta={}
 for style,roles in PROMPTS.items():
  for role,desc in roles.items():
   prompt=desc+' '+FAMILIES[style][1]+' Preserve the reference tonal center and motif. No vocals.';t=time.monotonic()
   with torch.no_grad():
    x=tok([prompt],padding='max_length',max_length=256,truncation=True,return_tensors='pt');e=m(**x).last_hidden_state.numpy();mask=x['attention_mask'].numpy()[...,None];e=e*mask+pad*(1-mask)
   np.save(R/f'assets/conditioning_{style}2_{role}.npy',e.astype(np.float16));meta[style+'_'+role]={'prompt':prompt,'encoding_seconds':time.monotonic()-t}
 (O/'conditioning.json').write_text(json.dumps(meta,indent=2))
def probe():
 import soundfile as sf
 rows=[]
 for style,roles in PROMPTS.items():
  source=R/f'results/unattended/{style}_seed.npy'
  for role in roles:
   dest=O/f'{style}_{role}';assert not dest.with_suffix('.json').exists()
   req={'id':int(time.time()*1000),'run_id':'secondary-form','identity':style+'2','conditioning':role,'seconds_total':180,'source_end':236,'latents':str(source),'seed':9601,'context_frames':22,'anchor_frames':22,'anchor_latents':str(source),'anchor_end':180}
   tmp=G/'request.tmp';tmp.write_text(json.dumps(req));tmp.replace(G/'request.json');result=G/f'result_{req["id"]}.json';end=time.monotonic()+150
   while not result.exists():
    if time.monotonic()>end:raise TimeoutError(role)
    time.sleep(.1)
   r=json.loads(result.read_text());assert 'error' not in r,r;wave,sr=sf.read(r['wav']);sf.write(dest.with_suffix('.wav'),wave[22*4096:-22*4096],sr);r['request']=req;dest.with_suffix('.json').write_text(json.dumps(r,indent=2));rows.append(r);print(style,role,r['seconds'],flush=True)
 (O/'jobs.json').write_text(json.dumps(rows,indent=2))
if __name__=='__main__':
 O.mkdir(parents=True,exist_ok=True);p=argparse.ArgumentParser();p.add_argument('mode',choices=['encode','probe']);a=p.parse_args();globals()[a.mode]()
