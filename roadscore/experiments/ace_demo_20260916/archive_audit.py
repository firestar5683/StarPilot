"""Post-run full rendered PCM audit; never feeds route/runtime decisions."""
import json
from pathlib import Path
import numpy as np,soundfile as sf
R=Path(__file__).resolve().parents[2];O=R/'results/ace_demo_20260916';rows=[]
for job in json.loads((O/'replay_results.json').read_text()):
 if not job.get('audio') or not (R/job['audio']).exists():continue
 wave,sr=sf.read(R/job['audio'],dtype='float32',always_2d=True);n=sr//10;x=wave[:len(wave)//n*n].reshape(-1,n,2);e=np.sqrt(np.mean((x-x.mean(axis=1,keepdims=True))**2,axis=(1,2)));spans=[];start=None
 for i,q in enumerate(list(e<.003)+[False]):
  if q and start is None:start=i
  if not q and start is not None:
   if i-start>=20:spans.append([start/10,i/10])
   start=None
 run=R/'results'/job['run'];ending=json.loads((run/'ending.json').read_text()) if (run/'ending.json').exists() else {};summary=json.loads((run/'summary.json').read_text());boundary=ending.get('audio_frame',float('inf'))/sr
 rows.append({'label':job['label'],'run':job['run'],'duration':len(wave)/sr,'finite':bool(np.isfinite(wave).all()),'peak':float(abs(wave).max()),'limited_sample_fraction':float(np.mean(abs(wave)>=.97997)),'quiet_spans_at_least_2s':spans,'quiet_spans_before_arrival_cadence':[s for s in spans if s[0]<boundary],'arrival_cadence_start_audio_seconds':None if not np.isfinite(boundary) else boundary,'safe_extensions':summary.get('safe_extensions',[]),'emergency_fallbacks':summary.get('fallbacks'),'underflows':summary.get('underflows'),'accepted_jobs':sum(j.get('quality_accepted',not j.get('error')) for j in summary['generation']),'rejected_attempts':sum(j.get('quality_rejections',0) for j in summary['generation']),'rerolls':sum(j.get('rerolls',0) for j in summary['generation']),'note':'All measured quiet spans retained. Intentional outro fades require context; energy alone is not human musical acceptance.'})
(O/'archive_energy.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
