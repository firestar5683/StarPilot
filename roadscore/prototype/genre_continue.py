"""Controlled retained-anchor versus moving-anchor long-form experiment. No route input."""
import argparse,json,time,shutil
from pathlib import Path
import numpy as np,soundfile as sf
from rolling import anchor_options,INITIAL_END,LATENT_SECONDS
from density import density
R=Path('/data/roadscore');O=R/'results/unattended';G=R/'generated'
p=argparse.ArgumentParser();p.add_argument('identity');p.add_argument('--count',type=int,default=6);p.add_argument('--sequence',default='develop,release,develop,base,release,develop');p.add_argument('--anchor-frames',type=int,default=44);p.add_argument('--moving-anchor',action='store_true');a=p.parse_args();key=a.identity;tag=key+('_moving' if a.moving_anchor else '_fixed')+(('_anchor'+str(a.anchor_frames)) if a.anchor_frames!=44 else '');folder=O/tag;folder.mkdir(exist_ok=True)
assert not (folder/'jobs.json').exists(),'Preserve previous experiment'
shutil.copy(O/f'{key}_seed.wav',R/f'assets/source_{key}.wav');shutil.copy(O/f'{key}_seed.npy',R/f'assets/source_{key}_latents.npy')
options=anchor_options(R,key);options['anchor_frames']=a.anchor_frames;last=str(R/f'assets/source_{key}_latents.npy');wave,sr=sf.read(R/f'assets/source_{key}.wav',dtype='float32',always_2d=True);audio=wave[:INITIAL_END*4096].copy();jobs=[]
for i in range(a.count):
 sequence=a.sequence.split(',');state=sequence[i%len(sequence)]
 req={'id':int(time.time()*1000),'run_id':tag,'identity':key,'conditioning':state,'seconds_total':180,'source_end':INITIAL_END if i==0 else 324,'latents':last,'seed':8201+i,**options}
 # Refresh identity only from previously generated material, every second section.
 if a.moving_anchor and i and i%2==0:
  req.update(anchor_latents=last,anchor_end=236)
 f=G/f'result_{req["id"]}.json';tmp=G/'request.tmp';tmp.write_text(json.dumps(req));tmp.replace(G/'request.json');end=time.monotonic()+120
 while not f.exists():
  if time.monotonic()>end:raise TimeoutError(tag)
  time.sleep(.1)
 r=json.loads(f.read_text());assert 'error' not in r,r;last=r['latents'];r['state']=state;r['request']=req;r['new_material_audio_s']=len(audio)/sr
 x,_=sf.read(r['wav'],dtype='float32',always_2d=True);keep=round(r['retained_seconds']*sr);n=round(2*sr);alpha=np.linspace(0,1,n)[:,None];audio=np.concatenate([audio[:-n],audio[-n:]*(1-alpha)+x[keep-n:keep]*alpha,x[keep:]])
 r['density']=density(x[keep:],sr);jobs.append(r)
 shutil.copy(r['wav'],folder/f'window_{i}.wav');shutil.copy(r['latents'],folder/f'window_{i}.npy');(folder/'jobs.json').write_text(json.dumps(jobs,indent=2));sf.write(folder/'long.wav',audio,sr)
 print(tag,i,state,r['seconds'],len(audio)/sr,flush=True)
