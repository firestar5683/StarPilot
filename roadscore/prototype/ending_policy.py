"""Experimental ending: never infer a new chord from weak tonal evidence."""
import numpy as np
from musical import analyze_music,ending_gesture

def safe_ending_gesture(wave,rate=48000):
 info=analyze_music(wave,rate)
 if info['tonal_confidence']>=.05 and info['mode']!='open':
  out,info=ending_gesture(wave,rate);return out,{**info,'cadence_policy':'tonal confidence gate passed'}
 out=np.zeros((5*rate,2),np.float32);grain=wave[-min(len(wave),round(.4*rate)):].copy();grain*=np.hanning(len(grain))[:,None]
 for k in range(16):
  at=round(k*.3*rate);count=min(len(grain),len(out)-at)
  if count>0:out[at:at+count]+=grain[:count]*np.exp(-k*.3/1.1)
 out[-rate//4:]*=np.linspace(1,0,rate//4)[:,None]
 return out,{**info,'cadence_policy':'source-tail release; no guessed tonic'}
