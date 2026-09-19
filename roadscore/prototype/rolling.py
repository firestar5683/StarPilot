"""Causal musical window policy. Only reads generated source audio; no route knowledge."""
from pathlib import Path
import numpy as np
import soundfile as sf
WINDOW=324
CONTEXT=44
ANCHOR=44
INITIAL_END=236
LATENT_SECONDS=4096/44100

def anchor_options(root,identity):
 root=Path(root);source=root/f'assets/source_{identity}.wav'
 a,sr=sf.read(source,dtype='float32',always_2d=True)
 # Active four-second identity from the already-generated opening, before its tail.
 end=max(range(100,INITIAL_END+1,2),key=lambda e:float(np.mean(a[round((e-ANCHOR)*LATENT_SECONDS*sr):round(e*LATENT_SECONDS*sr)]**2)))
 return {'context_frames':CONTEXT,'anchor_frames':ANCHOR,'anchor_end':end,'anchor_latents':str(root/f'assets/source_{identity}_latents.npy')}


def trajectory(index,nav_intent):
 """Small phrase-scale arc; close only from causally delivered navigation intent."""
 if nav_intent=='closing':return 'closing',1.0
 states=[('establish',0.),('explore',.15),('develop',.35),('build',.55),('release',.15)]
 phase,mix=states[min(index,4) if index<5 else 1+(index-5)%4]
 if nav_intent=='approach':mix=max(mix,.35)
 return phase,mix
