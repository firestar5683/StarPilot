"""Post-run energy audit; does not alter score audio or route behavior."""
import json
import numpy as np,soundfile as sf
from bundle import R,OUT
rows=[]
for row in json.loads((OUT/'replay_results.json').read_text()):
 if not row.get('audio'):continue
 wave,sr=sf.read(R/row['audio'],dtype='float32',always_2d=True);n=sr//10;energy=np.sqrt(np.mean(wave[:len(wave)//n*n].reshape(-1,n,2)**2,axis=(1,2)))
 spans=[];start=None
 for i,quiet in enumerate(list(energy<.003)+[False]):
  if quiet and start is None:start=i
  if not quiet and start is not None:
   if i-start>=10:spans.append([start/10,i/10])
   start=None
 ending=R/'results'/row['run']/'ending.json';ending=json.loads(ending.read_text()) if ending.exists() else {}
 rows.append({'label':row['label'],'run':row['run'],'duration':len(wave)/sr,'finite':bool(np.isfinite(wave).all()),'peak':float(abs(wave).max()),'rms':float(np.sqrt(np.mean(wave*wave))),'quiet_spans_at_least_1s':spans,'intentional_cadence_end_audio_s':ending.get('cadence_end_audio_s'),'scope':'All spans retained, including intentional end silence. Energy alone does not establish musical quality.'})
(OUT/'archive_energy.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
