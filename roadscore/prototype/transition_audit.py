"""Offline diagnostics of listening comparisons, never input to route playback."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
O=Path(__file__).resolve().parents[1]/'results/overnight'
def chroma(wave,rate):
 x=wave.mean(axis=1)[::4];sr=rate/4;n=2048
 frames=np.lib.stride_tricks.sliding_window_view(x,n)[::512]
 mag=abs(np.fft.rfft(frames*np.hanning(n),axis=1)).mean(axis=0)
 f=np.fft.rfftfreq(n,1/sr);valid=(f>70)&(f<4000)
 pc=np.round(69+12*np.log2(f[valid]/440)).astype(int)%12
 c=np.bincount(pc,weights=mag[valid],minlength=12)
 return c/max(np.linalg.norm(c),1e-12)
rows=json.loads((O/'validated_transitions.json').read_text())
for row in rows:
 w,sr=sf.read(O/(row['name']+'.wav'),always_2d=True)
 cut=round(row['actual_transition_seconds']*sr);n=round(2*sr)
 before=w[max(0,cut-n):cut];after=w[cut:cut+n]
 row['local_chroma_cosine_2s']=float(chroma(before,sr)@chroma(after,sr))
 row['boundary_sample_jump']=float(abs(w[cut]-w[cut-1]).max())
 row['rms_before_after']=[float(np.sqrt(np.mean(x*x))) for x in (before,after)]
 row['diagnostic_limit']='Two-second broad-band chroma can be dominated by percussion. Not a key/chord or audible-coherence verdict.'
(O/'validated_transitions.json').write_text(json.dumps(rows,indent=2))
print(json.dumps([{k:r[k] for k in ('name','local_chroma_cosine_2s','boundary_sample_jump')} for r in rows],indent=2))
