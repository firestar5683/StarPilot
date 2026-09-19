"""Listening derivatives from sequential native outputs; no speaker or recorded-route access."""
from pathlib import Path
import sys,json
import numpy as np,soundfile as sf
P=Path(__file__).resolve().parent;R=P.parents[1];O=R/'results/ace_chestnut_20260916/flow';sys.path.insert(0,str(R/'prototype'))
from musical import analyze_music,ending_gesture
from phrase import cadence_runway,mix_cadence
rate=48000;rows=json.loads((O/'results.json').read_text());song=None;boundaries=[]
for row in rows:
 a=np.load(O/(row['case']+'_pcm.npy'));prefix=round(row['prefix_seconds']*rate)
 if song is None:song=a.copy()
 else:
  overlap=min(rate,prefix,len(song));alpha=np.linspace(0,1,overlap)[:,None];boundary=len(song)/rate
  song[-overlap:]=song[-overlap:]*(1-alpha)+a[prefix-overlap:prefix]*alpha
  song=np.concatenate([song,a[prefix:]]);boundaries.append({'case':row['case'],'at_seconds':boundary,'generated_new_seconds':row['new_seconds'],'overlap_seconds':overlap/rate})
 gain=min(1,.98/float(abs(a).max()));sf.write(O/(row['case']+'.wav'),a*gain,rate,subtype='PCM_24')
gain=min(1,.98/float(abs(song).max()));sf.write(O/'section_flow.wav',song*gain,rate,subtype='PCM_24')
audit={'source':'sequential native generation, only preceding latent tail supplied to each continuation','boundaries':boundaries,'listening_gain':gain,'human_continuity_approval':None}
if rows[-1]['case']=='repaint_outro':
 start=max(0,len(song)-4*rate);delay,runway=cadence_runway(song[max(0,start-12*rate):start],song[start:],rate);entry=start+round(delay*rate);past=song[max(0,entry-12*rate):entry];info=analyze_music(past,rate)
 if info['tonal_confidence']>=.05 and info['mode']!='open':cadence,details=ending_gesture(past,rate);details['mode_used']='existing cadence; tonal confidence gate passed'
 else:
  cadence=np.zeros((5*rate,2),np.float32);grain=past[-round(.4*rate):].copy();grain*=np.hanning(len(grain))[:,None]
  for k in range(16):
   at=round(k*.3*rate);count=min(len(grain),len(cadence)-at)
   if count>0:cadence[at:at+count]+=grain[:count]*np.exp(-k*.3/1.1)
  cadence[-rate//4:]*=np.linspace(1,0,rate//4)[:,None];details={**info,'mode_used':'source-tail release; no guessed tonic'}
 total=max(len(song),entry+len(cadence))+rate;out=np.zeros((total,2),np.float32);out[:len(song)]=song;out=mix_cadence(out,cadence,0,entry,rate)
 excerpt_start=max(0,round((boundaries[-1]['at_seconds']-12)*rate));out=out[excerpt_start:];g=min(1,.98/float(abs(out).max()));sf.write(O/'arrival.wav',out*g,rate,subtype='PCM_24');audit['arrival']={'entry_full_song_seconds':entry/rate,'excerpt_start_seconds':excerpt_start/rate,'runway':runway,'cadence':details,'test_kind':'explanatory musical render; no route acceptance claim'}
(O/'listening.json').write_text(json.dumps(audit,indent=2));print(audit)
