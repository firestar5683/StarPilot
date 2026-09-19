"""Two fresh seeds for one focused dense identity, then matching prewarm. No routes."""
import json,time,shutil
from pathlib import Path
R=Path('/data/roadscore');O=R/'results/dense';G=R/'generated';meta=[]
assert not (O/'probe.json').exists()
def request(name,**kw):
 req={'id':940000+len(meta),'run_id':'dense-probe','identity':'horizon_drive','conditioning':'base','seconds_total':120,'latents':str(R/'assets/source_horizon_latents.npy'),'seed':7301+len(meta),**kw}
 p=G/'request.tmp';p.write_text(json.dumps(req));p.replace(G/'request.json');f=G/f'result_{req["id"]}.json';end=time.monotonic()+120
 while not f.exists():
  if time.monotonic()>end:raise RuntimeError('Generation timeout')
  time.sleep(.1)
 r=json.loads(f.read_text());assert 'error' not in r,r
 r['name']=name;meta.append(r);shutil.copy(r['wav'],O/f'{name}.wav');shutil.copy(r['latents'],O/f'{name}.npy');(O/'probe.json').write_text(json.dumps(meta,indent=2));print(name,r['seconds'],flush=True)
 return r
end=time.monotonic()+600
while not ((G/'worker_ready').exists() and (R/'assets/dense_conditioning.json').exists()):
 if time.monotonic()>end:raise RuntimeError('Preparation timed out')
 time.sleep(1)
for i in range(2):request(f'dense_seed_{i}',fresh=True)
