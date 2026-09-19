"""Stage one generated identity seed and prepare one matching continuation."""
import json,shutil,time
from pathlib import Path
from rolling import anchor_options,INITIAL_END
R=Path('/data/roadscore');G=R/'generated';O=R/'results/dense'
# Seed 7301: selected for stronger transient activity and a pulse near the request.
assert (O/'dense_seed_0.npy').exists()
shutil.copy(O/'dense_seed_0.wav',R/'assets/source_horizon_drive.wav');shutil.copy(O/'dense_seed_0.npy',R/'assets/source_horizon_drive_latents.npy')
req={'id':940010,'run_id':'dense-stage','identity':'horizon_drive','conditioning':'base','seconds_total':120,'source_end':INITIAL_END,'latents':str(R/'assets/source_horizon_drive_latents.npy'),'seed':7303,**anchor_options(R,'horizon_drive')}
p=G/'request.tmp';p.write_text(json.dumps(req));p.replace(G/'request.json');f=G/'result_940010.json';end=time.monotonic()+90
while not f.exists():
 if time.monotonic()>end:raise RuntimeError('Prewarm timeout')
 time.sleep(.1)
r=json.loads(f.read_text());assert 'error' not in r,r
shutil.copy(r['wav'],G/'job_-1.wav');shutil.copy(r['latents'],G/'job_-1.npy');(G/'warm_metadata.json').write_text(json.dumps(r))
(O/'prewarm.json').write_text(json.dumps(r,indent=2))
(R/'runtime.json').write_text(json.dumps({'identity':'horizon_drive','musical':True,'rolling':True}))
print(json.dumps(r),flush=True)
