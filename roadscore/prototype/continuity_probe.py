"""Bounded Horizon inpainting probe; existing generated music only, no route access."""
import json,time,shutil
from pathlib import Path
import numpy as np,soundfile as sf
R=Path('/data/roadscore');O=R/'results/continuity';G=R/'generated'
assert not (O/'probe.json').exists(), 'Preserve existing results'
source=R/'assets/source_horizon_latents.npy'
audio,sr=sf.read(R/'assets/source_horizon.wav',dtype='float32',always_2d=True)
# Fixed eight-second guard for the initial source; choose a loud active four-second
# identity anchor from its middle, exclusively from already-generated audio.
end=236;context=44
choices=range(100,end+1,2)
anchor_end=max(choices,key=lambda e:np.mean(audio[round((e-context)*4096):e*4096]**2))
meta=[]
def job(name,latent=source,**extra):
 req={'id':920000+len(meta),'run_id':'continuity-probe','identity':'horizon','conditioning':'base','seconds_total':120,'source_end':end,'context_frames':44,'seed':24000+len(meta),'latents':str(latent),**extra}
 p=G/'request.tmp';p.write_text(json.dumps(req));p.replace(G/'request.json')
 f=G/f'result_{req["id"]}.json';deadline=time.monotonic()+180
 while not f.exists():
  if time.monotonic()>deadline:raise RuntimeError('Timed out')
  time.sleep(.2)
 r=json.loads(f.read_text());assert 'error' not in r,r
 r['name']=name;r['request']=req
 shutil.copy(r['wav'],O/f'{name}.wav');shutil.copy(r['latents'],O/f'{name}.npy')
 meta.append(r);(O/'probe.json').write_text(json.dumps({'initial_end':end,'anchor_end':anchor_end,'jobs':meta},indent=2));print(name,r['seconds'],flush=True)
 return r['latents']
while not (G/'worker_ready').exists():time.sleep(1)
job('prefix_control',seed=24000)
latent=job('anchor_0',seed=24000,anchor_frames=44,anchor_end=anchor_end,anchor_latents=str(source))
for i in range(1,4):
 latent=job(f'anchor_{i}',latent=latent,source_end=324,anchor_frames=44,anchor_end=anchor_end,anchor_latents=str(source))
print('DONE',flush=True)
