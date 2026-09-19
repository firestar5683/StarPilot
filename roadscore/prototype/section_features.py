"""Coarse acoustic contrast evidence, never a harmonic/listening verdict."""
import json
from pathlib import Path
import numpy as np,soundfile as sf
R=Path(__file__).resolve().parents[1]/'results/overnight/sections'
def feature(path):
 w,sr=sf.read(path,always_2d=True);x=w.mean(axis=1)[::4];sr/=4;n=4096;frames=np.lib.stride_tricks.sliding_window_view(x,n)[::1024];mag=abs(np.fft.rfft(frames*np.hanning(n),axis=1));freq=np.fft.rfftfreq(n,1/sr);valid=(freq>70)&(freq<4000);pc=np.round(69+12*np.log2(freq[valid]/440)).astype(int)%12;c=np.bincount(pc,weights=mag[:,valid].mean(axis=0),minlength=12);c/=max(np.linalg.norm(c),1e-9)
 return {'chroma':c.tolist(),'spectral_centroid_hz':float(np.sum(freq*mag.mean(axis=0))/mag.mean(axis=0).sum()),'rms':float(np.sqrt(np.mean(w*w)))}
rows={p.stem:feature(p) for p in R.glob('*.wav')};comparisons={}
for strategy in ['anchored','prefix_only','short_anchor']:
 base=rows[strategy+'_verse'];comparisons[strategy]={role:{'chroma_cosine':float(np.dot(base['chroma'],rows[strategy+'_'+role]['chroma'])),'centroid_ratio':rows[strategy+'_'+role]['spectral_centroid_hz']/base['spectral_centroid_hz'],'rms_ratio':rows[strategy+'_'+role]['rms']/base['rms']} for role in ['chorus','bridge','outro']}
(R/'features.json').write_text(json.dumps({'features':rows,'comparisons':comparisons,'limitation':'Coarse spectral proxies cannot certify key, chord membership, form or musical coherence.'},indent=2));print(json.dumps(comparisons,indent=2))
