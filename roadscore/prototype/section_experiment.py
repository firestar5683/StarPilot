"""Controlled song-section research. Generated audio only; no route access or playback."""
import argparse,json,time,shutil,os
from pathlib import Path
import numpy as np
R=Path('/data/roadscore');O=R/'results/overnight/sections';G=R/'generated'
BASE='Instrumental breakbeat action game score, 138 BPM, steady four beat bars, D minor, crisp syncopated breakbeat drums, punchy electric synth bass, compressed pulsing synths and bright arpeggiators. Recurring short playful staccato digital synth hook. One coherent song with a stable rhythmic identity. '
ROLES={
'intro':'INTRO. Establish the recognizable hook on a small plucked synth, filtered percussion pickup and sparse bass. Purposeful opening before the full groove.',
'verse':'VERSE. Restrained tight groove, dry drums, syncopated bass and short repeating synth hook with space between phrases. Sparse accompaniment, moderate energy, room for the chorus to grow.',
'prechorus':'PRECHORUS. Develop the same hook into rising melodic sequences, increasing sixteenth note percussion and opening synth filters. Bass and suspended harmony prepare a strong chorus landing. Tension and forward motion.',
'chorus':'CHORUS. Full powerful breakbeat and electric synth bass, soaring memorable lead hook doubled in octaves, wide layered polysynth harmonies and bright arpeggios. A substantially larger triumphant refrain with strong downbeat landings.',
'bridge':'BRIDGE. Contrasting half time lead phrasing over the same steady breakbeat pulse, new expressive glassy synth melody and spacious lower pad harmony. Related modal mixture and borrowed major harmony over a D pedal, then prepare return to the original chorus. Clear contrasting texture within the same song.',
'outro':'OUTRO. Reprise the original short hook then simplify drums and bass, conclude the melodic phrase with a resolved final D minor chord and natural ringing instruments. Intentional final cadence, not a volume fade.'}
def encode():
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
 import torch
 from transformers import AutoTokenizer,AutoConfig,T5GemmaEncoderModel
 torch.set_num_threads(4);p='/data/sa3-feasibility/t5gemma-b-b-ul2';cfg=AutoConfig.from_pretrained(p,local_files_only=True);cfg.is_encoder_decoder=False
 tok=AutoTokenizer.from_pretrained(p,local_files_only=True,use_fast=False);m=T5GemmaEncoderModel.from_pretrained(p,config=cfg,local_files_only=True,torch_dtype=torch.float32,low_cpu_mem_usage=True).eval()
 pad=np.load('/data/sa3-feasibility/native/conditioner.conditioners.prompt.padding_embedding.npy').astype(np.float32);meta={}
 for role,description in ROLES.items():
  prompt=BASE+description+' No vocals, no singing, no speech.';t=time.monotonic()
  with torch.no_grad():
   x=tok([prompt],padding='max_length',max_length=256,truncation=True,return_tensors='pt');e=m(**x).last_hidden_state.numpy();mask=x['attention_mask'].numpy()[...,None];e=e*mask+pad*(1-mask)
  np.save(R/f'assets/conditioning_{os.environ.get("ROADSCORE_CONDITION_ID","songform")}_{role}.npy',e.astype(np.float16));meta[role]={'prompt':prompt,'encoding_seconds':time.monotonic()-t};print(role,flush=True)
 (O/'conditioning.json').write_text(json.dumps(meta,indent=2))
def probe():
 import soundfile as sf
 deadline=time.monotonic()+600
 while not (G/'worker_ready').exists() or not (O/'conditioning.json').exists():
  if time.monotonic()>deadline:raise TimeoutError('Preparation')
  time.sleep(1)
 source=R/'results/unattended/switchback_seed.npy';jobs=[]
 # Paired random seed isolates conditioning; retained audio provides real musical context.
 for strategy,context,anchor in [('anchored',44,44),('prefix_only',44,0),('short_anchor',22,22)]:
  for role in ROLES:
   dest=O/f'{strategy}_{role}'
   if dest.with_suffix('.json').exists():continue
   req={'id':int(time.time()*1000),'run_id':'songform-screen','identity':'songform','conditioning':role,'seconds_total':180,'source_end':236,'latents':str(source),'seed':9301,'context_frames':context,'anchor_frames':anchor,'anchor_latents':str(source),'anchor_end':180}
   tmp=G/'request.tmp';tmp.write_text(json.dumps(req));tmp.replace(G/'request.json');result=G/f'result_{req["id"]}.json';deadline=time.monotonic()+180
   while not result.exists():
    if time.monotonic()>deadline:raise TimeoutError(str(dest))
    time.sleep(.1)
   r=json.loads(result.read_text());assert 'error' not in r,r
   wave,sr=sf.read(r['wav'],dtype='float32',always_2d=True);new=wave[context*4096:len(wave)-anchor*4096 if anchor else len(wave)]
   sf.write(dest.with_suffix('.wav'),new,sr);shutil.copy(r['latents'],dest.with_suffix('.npy'))
   r.update(request=req,strategy=strategy,section=role,rms=float(np.sqrt(np.mean(new**2))),duration=len(new)/sr,peak=float(abs(new).max()))
   dest.with_suffix('.json').write_text(json.dumps(r,indent=2));jobs.append(r);print(strategy,role,r['seconds'],r['rms'],flush=True)
 (O/'jobs.json').write_text(json.dumps(jobs,indent=2))
if __name__=='__main__':
 O.mkdir(parents=True,exist_ok=True);p=argparse.ArgumentParser();p.add_argument('mode',choices=['encode','probe']);a=p.parse_args();globals()[a.mode]()
