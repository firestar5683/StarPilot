"""Bounded diverse SA3 screen: six families, fixed seed, local text encoding then GPU requests."""
import argparse,json,time,shutil,os
from pathlib import Path
import numpy as np
R=Path('/data/roadscore');O=R/'results/unattended';G=R/'generated'
FAMILIES={
 'ignition':('Progressive electronic','Instrumental progressive house, 126 BPM four on the floor kick, sidechain pumping warm chords, syncopated plucked synth hook, crisp claps and open hats. Minor verse moving to a bright suspended chord chorus, melodic bass sequence and evolving eight bar arrangement. Club production, energetic and detailed.'),
 'nightshift':('Outrun synthwave','Instrumental outrun synthwave, 112 BPM gated snare backbeat, sixteenth note analog bass ostinato, bright octave arpeggiator, expressive soaring polysynth lead. Dramatic minor key with borrowed major chords, retro drum machine fills, contrasting register and countermelodies.'),
 'switchback':('Breakbeat game score','Instrumental rhythmic action game soundtrack, 138 BPM chopped syncopated breakbeat drums, punchy sub bass, staccato digital synth motifs, glitch percussion and chiptune counterpoint. Playful modal melody in call and response, sudden half time passage then busy rhythmic reprise.'),
 'brassline':('Live funk groove','Instrumental live funk fusion band, 104 BPM syncopated electric bass guitar, tight ghost note snare and dry kick, wah rhythm guitar, Rhodes electric piano with jazzy extended chord changes, short unison brass riffs. Improvised keyboard answers and lively drum fills, human pocket, warm room sound.'),
 'monument':('Cinematic hybrid','Instrumental cinematic hybrid action score, 118 BPM syncopated low string ostinato, large tom ensemble, electronic bass pulses, brass chord stabs, rising violins and metallic percussion. Alternating asymmetric rhythmic motifs, dark modal harmony developing toward an expansive brass theme, dynamic ensemble orchestration.'),
 'afterimage':('Atmospheric garage','Instrumental atmospheric UK garage, 132 BPM swung two step drum groove with shuffled hats and displaced snare, deep rolling sub bass, soft electric piano seventh chords, airy granular synth fragments, intimate plucked melodic motif. Rich changing jazz harmony and spacious rhythmic interplay, no four on the floor beat.')}
SUFFIX=' Strictly instrumental, no vocals, no singing, no spoken voices.'
def encode():
 os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
 import torch
 from transformers import AutoTokenizer,AutoConfig,T5GemmaEncoderModel
 torch.set_num_threads(4);p='/data/sa3-feasibility/t5gemma-b-b-ul2';cfg=AutoConfig.from_pretrained(p,local_files_only=True);cfg.is_encoder_decoder=False
 tok=AutoTokenizer.from_pretrained(p,local_files_only=True,use_fast=False);m=T5GemmaEncoderModel.from_pretrained(p,config=cfg,local_files_only=True,torch_dtype=torch.float32,low_cpu_mem_usage=True).eval()
 pad=np.load('/data/sa3-feasibility/native/conditioner.conditioners.prompt.padding_embedding.npy').astype(np.float32)
 meta={}
 for key,(name,prompt) in FAMILIES.items():
  for state,extra in {'base':'The full groove is already playing. Introduce a memorable theme.', 'develop':'Continue the same song but introduce a contrasting answering theme, move the bass and harmony, change the lead register and vary the drum pattern. A new developed section, not a repeated loop.', 'release':'A contrasting restrained bridge. Remove the lead, let the bass and chords move to a related harmonic area. Keep a recognizable pulse with different percussion and a short new motif.'}.items():
   text=prompt+' '+extra+SUFFIX;t=time.monotonic()
   with torch.no_grad():
    x=tok([text],padding='max_length',max_length=256,truncation=True,return_tensors='pt');e=m(**x).last_hidden_state.numpy();mask=x['attention_mask'].numpy()[...,None];e=e*mask+pad*(1-mask)
   np.save(R/f'assets/conditioning_{key}_{state}.npy',e.astype(np.float16));meta[key+'_'+state]={'name':name,'prompt':text,'encoding_seconds':time.monotonic()-t};print(key,state,flush=True)
 (O/'conditioning.json').write_text(json.dumps(meta,indent=2))
def probe():
 from density import density
 import soundfile as sf
 rows=[];end=time.monotonic()+900
 while not (G/'worker_ready').exists() or not (O/'conditioning.json').exists():
  if time.monotonic()>end:raise TimeoutError('Preparation')
  time.sleep(1)
 for i,(key,(name,_)) in enumerate(FAMILIES.items()):
  req={'id':950000+i,'run_id':'genre-screen','identity':key,'conditioning':'base','seconds_total':120,'fresh':True,'latents':str(R/'assets/source_horizon_latents.npy'),'seed':8101}
  path=G/'request.tmp';path.write_text(json.dumps(req));path.replace(G/'request.json');f=G/f'result_{req["id"]}.json';end=time.monotonic()+120
  while not f.exists():
   if time.monotonic()>end:raise TimeoutError(key)
   time.sleep(.1)
  row=json.loads(f.read_text());assert 'error' not in row,row
  for ext,src in [('wav',row['wav']),('npy',row['latents'])]:shutil.copy(src,O/f'{key}_seed.{ext}')
  wave,sr=sf.read(row['wav']);row.update(name=name,density=density(wave,sr),rms=float(np.sqrt(np.mean(wave**2))),peak=float(np.abs(wave).max()),rtf=row['seconds']/(len(wave)/sr));rows.append(row)
  (O/'genre_screen.json').write_text(json.dumps(rows,indent=2));print(key,row['rtf'],row['density'],flush=True)
if __name__=='__main__':
 O.mkdir(parents=True,exist_ok=True);p=argparse.ArgumentParser();p.add_argument('mode',choices=['encode','probe']);a=p.parse_args();globals()[a.mode]()
