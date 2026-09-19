"""Integrity/silence measurements only; never classify musical quality from RMS."""
import json
from pathlib import Path
import numpy as np,soundfile as sf
O=Path(__file__).resolve().parents[2]/'results/composition_20260916';rows=[]
files=list((O/'sa3').glob('*.wav'))+list((O/'ace').glob('*.wav'))+list((O/'yue').glob('*/audio.flac'))
for p in files:
 x,sr=sf.read(p,dtype='float32',always_2d=True);n=sr//10;k=len(x)//n;rms=np.sqrt(np.mean(x[:k*n].reshape(k,n,-1)**2,axis=(1,2)))
 rows.append({'file':str(p.relative_to(O)),'seconds':len(x)/sr,'rate':sr,'finite':bool(np.isfinite(x).all()),'rms':float(np.sqrt(np.mean(x*x))),'peak':float(abs(x).max()),'near_silent_seconds_100ms_below_minus50dBFS':float(np.sum(rms<10**(-50/20))*.1),'samples_at_or_above_0999_fraction':float(np.mean(abs(x)>=.999)),'ending_rms_dbfs':float(20*np.log10(max(np.sqrt(np.mean(x[-sr:]**2)),1e-10)))})
(O/'audio_integrity.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
