"""Diagnostic same-causal-event renders across generated genres; clearly not live captures."""
import json
from pathlib import Path
import numpy as np,soundfile as sf
from scipy.signal import resample_poly
from event_music import EventDSP
from driving_music import DrivingDSP
from phrase import pulse
R=Path(__file__).resolve().parents[1];O=R/'results/unattended';blocks=[json.loads(x) for x in (R/'results/dense/live_curve/audio_blocks.jsonl').read_text().splitlines()];out={}
for key,style in [('ignition','electronic'),('nightshift','synthwave'),('brassline','groove')]:
 source,sr=sf.read(O/f'{key}_fixed/long.wav',dtype='float32',always_2d=True);pi=pulse(source[:round(21.9196*sr)],sr);source=resample_poly(source,48000,sr).astype(np.float32);d=EventDSP(bpm=pi['bpm'],style=style);control=DrivingDSP(bpm=pi['bpm']);neutral=EventDSP(bpm=pi['bpm'],style=style);wet=[];old=[];metrics=[]
 for b in blocks:
  k=round(b['audio_s']*48000);x=source[k:k+4800]
  if len(x)!=4800:break
  event={'phase':b['phase'],'strength':b['strength'],'kind':'slowdown' if b['amount']<0 else 'curve'};d.event_state=event;control.event_state=event
  y=d.process(x,b['amount']);c=control.process(x,b['amount']);z=neutral.process(x,0);wet.append(y);old.append(c);ref=float(np.sqrt(np.mean(z*z)));res=float(np.sqrt(np.mean((y-z)**2)));metrics.append({'audio_s':b['audio_s'],'phase':b['phase'],'ratio':res/max(ref,1e-9),'rms':ref})
 for label,parts in [('style',wet),('previous',old)]:sf.write(O/f'{key}_curve_{label}.wav',np.concatenate(parts)[18*48000:82*48000],48000)
 events=[]
 for i,b in enumerate(metrics):
  if b['phase']!='anticipation' or (i and metrics[i-1]['phase']=='anticipation'):continue
  end=next((j for j in range(i+1,len(metrics)) if metrics[j]['phase']=='neutral'),len(metrics));cross=next((metrics[j]['audio_s'] for j in range(i,end-2) if all(x['ratio']>=.1 and x['rms']>=.003 for x in metrics[j:j+3])),None);events.append({'command_audio_s':b['audio_s'],'proxy_audio_s':cross,'delay':None if cross is None else cross-b['audio_s']})
 out[key]={'style':style,'events':events,'bpm_proxy':pi['bpm'],'range_audio_s':[18,82],'source':'Generated long-form sample with original captured causal event states. Offline diagnostic, not a live replay.'}
(O/'style_response.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
