"""Common gain per A/B pair prevents browser clipping; no time or spectral edits."""
import json
import numpy as np,soundfile as sf
from bundle import OUT
out=OUT/'listening';out.mkdir(exist_ok=True);reports={}
for name in ['prism_30','prism_45','prism_60','aurora_30','circuit_30','gold_transition','gold_recovered_codes']:
 p=OUT/'cases'/name;paths=[p/'reference_rounded/audio.wav',p/'native_0/audio.wav']
 if not all(f.exists() for f in paths):continue
 waves=[sf.read(f,dtype='float32',always_2d=True)[0] for f in paths];peak=max(float(abs(a).max()) for a in waves);gain=min(1.,.95/max(peak,1e-8))
 for label,a in zip(['mac','native'],waves):sf.write(out/(name+'_'+label+'.wav'),a*gain,48000,subtype='PCM_24')
 reports[name]={'additional_common_pair_gain':gain,'original_max_peak':peak,'edits':'constant identical gain only; no trimming, splice, noise replacement, EQ or limiting'}
(OUT/'listening_gains.json').write_text(json.dumps(reports,indent=2))
