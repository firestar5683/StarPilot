"""Offline A/B exports, never imported by runtime."""
import json
from pathlib import Path
import numpy as np,soundfile as sf
from scipy.signal import resample_poly
from core import DSP
from musical import MusicalDSP,Arrival,ending_gesture,match_continuation,analyze_music
R=Path('/data/roadscore');O=R/'results/quality';sr=48000

def read(p):
 w,r=sf.read(p,dtype='float32',always_2d=True)
 return resample_poly(w,sr,r).astype('float32') if r!=sr else w

def save(name,w):sf.write(O/(name+'.wav'),w,sr,subtype='PCM_16')

def rms_dips(w):
 size=4800;x=w[:len(w)//size*size].reshape(-1,size,2);r=np.sqrt(np.mean(x*x,axis=(1,2)))
 return {'seconds':len(w)/sr,'rms':float(np.sqrt(np.mean(w*w))),'near_silence_seconds':float((r<.00316).sum()/10),'peak':float(np.abs(w).max())}

metrics={}
for name in ['nocturne','horizon','orbit','canopy']:
 parts=[read(O/f'{name}_{kind}.wav') for kind in ['initial','base','approach','closing']]
 old=parts[0].copy();new=old.copy();joins=[];context=86*4096/44100
 for part in parts[1:]:
  b=part[round((context-2)*sr):];n=sr*2;alpha=np.linspace(0,1,n)[:,None]
  old=np.concatenate([old[:-n],old[-n:]*(1-alpha)+b[:n]*alpha,b[n:]])
  b,match=match_continuation(new,b,n);joins.append({'t':len(new)/sr-2,**match,'correlation':float(np.corrcoef(new[-n:].ravel(),b[:n].ravel())[0,1])})
  new=np.concatenate([new[:-n],new[-n:]*(1-alpha)+b[:n]*alpha,b[n:]])
 save(name+'_journey',new);save(name+'_boundary_old',old[24*sr:38*sr]);save(name+'_boundary_new',new[24*sr:38*sr]);save(name+'_preview',new[2*sr:22*sr]);save(name+'_development',new[58*sr:78*sr]);save(name+'_ending',new[-sr*18:])
 metrics[name]={'audio':rms_dips(new),'boundaries':joins,'musical_estimate':analyze_music(new[:30*sr])}
# Same captured dry performance and identical causal amount, old/new conducting.
p=R/'results/quality/baseline_replay';dry=read(p/'dry.wav');blocks=[json.loads(x) for x in (p/'audio_blocks.jsonl').read_text().splitlines()]
old=DSP();new=MusicalDSP();a=[];b=[]
for i,block in enumerate(blocks):
 chunk=dry[i*4800:(i+1)*4800]
 if len(chunk)!=4800:break
 a.append(old.process(chunk,block['amount']));b.append(new.process(chunk,block['amount']))
a=np.concatenate(a);b=np.concatenate(b);save('curve_old',a[18*sr:43*sr]);save('curve_new',b[18*sr:43*sr])
# Sequential arrival rule on actual recorded, previously delivered state.
p=R/'results/arrival_composed';rows=[json.loads(x) for x in (p/'trace.jsonl').read_text().splitlines()];det=Arrival();revision=None;when=None
for s in rows:
 if s['nav_revision']!=revision:
  det.route_change(s['nav'].get('valid',False));revision=s['nav_revision']
 fresh=s['nav'].get('valid',False) and 0<=(s['source_cutoff_ns']-s['nav'].get('mono',0))/1e9<3
 when=det.update(s['route_t'],s['speed'],s['nav'],fresh)
 if when is not None:break
assert when is not None
w=read(p/'dry.wav');n=round((when-170)*sr);gesture,info=ending_gesture(w[max(0,n-sr*12):n]);dsp=MusicalDSP();render=[]
for i in range(0,n,4800):render.append(dsp.process(w[i:min(n,i+4800)],0))
render=np.concatenate(render);new=np.concatenate([render,gesture]);save('arrival_new',new);save('arrival_old',read(p/'heard.wav'))
metrics['arrival']={'old_trigger':234.505508006,'new_trigger':when,'ending':info,'note':'Same historical speed/nav sequence, latest arrival context held 30s through invalidation; no EOF trigger. Five-second synthetic source-informed sonority is a candidate, not an established harmonic cadence.'}
(O/'quality_metrics.json').write_text(json.dumps(metrics,indent=2));print(json.dumps(metrics,indent=2))
