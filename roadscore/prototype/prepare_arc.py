"""A small controlled test of contrasting section prompts without conflicting base instructions."""
import os,json,time
from pathlib import Path
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
import torch,numpy as np
from transformers import AutoTokenizer,AutoConfig,T5GemmaEncoderModel
R=Path('/data/roadscore');P='/data/sa3-feasibility/t5gemma-b-b-ul2';torch.set_num_threads(4)
common='Instrumental progressive electronic song, 126 BPM, E minor with related G major harmony. Recognizable short rising plucked synthesizer motif. Detailed warm production. No vocals, no singing, no voices. '
prompts={
 'base':'Steady four on the floor kick, crisp claps, rounded syncopated bass and repeating plucked synth hook. Establish the full dance groove with changing minor chords.',
 'explore':'A contrasting half time bridge of the same song. Electric piano plays moving seventh chords, soft shaker and sparse rim clicks replace the kick and clap beat. Low bass plays spacious answering notes. The hook appears as a high glassy bell fragment. Restrained but continuous music, no fade.',
 'develop':'A new melodic section with interlocking mallet synth and staccato string-like sequencer, syncopated bass variations, broken beat drums and offbeat hand percussion. Develop a second answering melody in a higher register with brighter relative major harmony.',
 'build':'Tension section: repeating rising synth motif over suspended harmony, eighth note bass ostinato, snare subdivisions building gradually, filtered airy synth textures climbing in register. Continuous music, no sudden ending.',
 'peak':'Expansive chorus: wide sustained lead synthesizer plays the developed melody, full four on the floor kick and clap beat, bright open hats and octave bass. Strong harmonic resolution and full rhythmic energy. Rich layered dance production.',
 'release':'Intimate rhythmic breakdown after the chorus. Remove the lead and heavy kick. Rhodes piano answers a muted plucked motif over sparse syncopated sub bass and brushed shaker, changing warm extended chords. Maintain a light pulse without building again or fading out.',
 'closing':'Final measured phrase of the same electronic song. The existing short rising motif resolves downward to the tonic, bass settles on E, drums simplify to a final restrained phrase with space for a warm resolving chord. No new riff, no vocals.'}
cfg=AutoConfig.from_pretrained(P,local_files_only=True);cfg.is_encoder_decoder=False;tok=AutoTokenizer.from_pretrained(P,local_files_only=True,use_fast=False);m=T5GemmaEncoderModel.from_pretrained(P,config=cfg,local_files_only=True,torch_dtype=torch.float32,low_cpu_mem_usage=True).eval();pad=np.load('/data/sa3-feasibility/native/conditioner.conditioners.prompt.padding_embedding.npy').astype(np.float32);meta={}
for state,description in prompts.items():
 text=common+description;t=time.monotonic()
 with torch.no_grad():
  x=tok([text],padding='max_length',max_length=256,truncation=True,return_tensors='pt');e=m(**x).last_hidden_state.numpy();mask=x['attention_mask'].numpy()[...,None];e=e*mask+pad*(1-mask)
 np.save(R/f'assets/conditioning_ignition_arc_{state}.npy',e.astype(np.float16));meta[state]={'prompt':text,'seconds':time.monotonic()-t};print(state,flush=True)
(R/'results/unattended/arc_conditioning.json').write_text(json.dumps(meta,indent=2))
