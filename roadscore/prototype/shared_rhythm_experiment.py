"""DSP arrangement comparison from trusted Chestnut audio, not claimed instrument stems.
HPSS separates harmonic/percussive tendencies; no new pitches/chords are synthesized.
"""
import json,sys
from pathlib import Path
import numpy as np,soundfile as sf
from scipy.signal import stft,istft,butter,sosfilt
from scipy.ndimage import median_filter
from bar_grid import grid
from musical import ending_gesture
R=Path(__file__).resolve().parents[1];O=R/'results/overnight';rate=44100

def separate(w):
 parts=[]
 for channel in w.T:
  _,_,z=stft(channel,fs=rate,nperseg=2048,noverlap=1536);m=abs(z);h=median_filter(m,size=(1,25));p=median_filter(m,size=(25,1));mask=h*h/(h*h+p*p+1e-12)
  _,harm=istft(z*mask,fs=rate,nperseg=2048,noverlap=1536);_,perc=istft(z*(1-mask),fs=rate,nperseg=2048,noverlap=1536);parts.append((harm[:len(w)],perc[:len(w)]))
 return np.stack([x[0] for x in parts],axis=1),np.stack([x[1] for x in parts],axis=1)

def loop_to(w,n):
 return np.tile(w,(int(np.ceil(n/len(w))),1))[:n]
clips={};metrics={}
for role in ['intro','verse','prechorus','chorus','bridge','outro']:
 w,sr=sf.read(O/f'sections/anchored_{role}.wav',dtype='float32',always_2d=True);assert sr==rate;g=grid(w,rate);start=g['downbeats'][0];length=4*4*g['period'];lo=round(start*rate);clip=w[lo:lo+round(length*rate)];clips[role]=separate(clip);metrics[role]=g
period=metrics['verse']['period'];bar=4*period;bed=clips['verse'][1]
sequence=[('intro',4),('verse',8),('prechorus',4),('chorus',8),('verse',8),('bridge',8),('chorus',8),('outro',4)];audio=[];events=[];total=0
for role,bars in sequence:
 n=round(bars*bar*rate);harm=loop_to(clips[role][0],n);perc=loop_to(bed,n);low=sosfilt(butter(4,1600,fs=rate,output='sos'),harm,axis=0);high=harm-low
 if role=='intro':x=low*.8+perc*.18
 elif role=='verse':x=low*.8+high*.15+perc*.85
 elif role=='prechorus':
  ramp=np.linspace(0,1,n)[:,None];x=low*.8+high*(.15+.85*ramp)+perc*(.85+.15*ramp)
 elif role=='chorus':
  mid=harm.mean(axis=1,keepdims=True);wide=mid+(harm-mid)*1.35;x=wide+perc
 elif role=='bridge':x=harm*.95+perc*.65
 else:x=low*.85+perc*np.maximum(0,1-np.arange(n)[:,None]/max(1,n*.55))
 # Level-match the comparisons: contrast cannot be credited merely to louder output.
 gain=.12/max(float(np.sqrt(np.mean(x*x))),1e-8);x=x*min(gain,3);x=np.tanh(x/.95)*.95
 # Short edge declick, not a musical fade-out.
 k=round(.003*rate);x[:k]*=np.linspace(0,1,k)[:,None];x[-k:]*=np.linspace(1,0,k)[:,None]
 events.append({'section':role,'start':total/rate,'bars':bars,'bpm':60/period,'arrangement_gain':min(gain,3),'source':'Trusted normal-runtime anchored candidate','rhythm_source':'Chestnut-generated verse, approximate HPSS percussive component'});audio.append(x);total+=n
ending,info=ending_gesture(audio[-1],rate);audio.append(ending);wave=np.concatenate(audio);sf.write(O/'shared_rhythm_songform.wav',wave,rate);(O/'shared_rhythm_songform.json').write_text(json.dumps({'duration':len(wave)/rate,'sections':events,'cadence':info,'human_verified':False,'limitations':'HPSS is not true instrument separation. This changes orchestration/spectral balance without inventing harmony; it does not prove strong harmonic bridge or new composition.'},indent=2));print('Rendered',len(wave)/rate,'seconds, no playback')
