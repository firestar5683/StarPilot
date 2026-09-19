"""Second controlled conditioning pass: no imposed key; short-context chained sections."""
import argparse,json,time,shutil,os
from pathlib import Path
import numpy as np
R=Path('/data/roadscore');O=R/'results/overnight/followup';G=R/'generated'
from section_experiment import ROLES
BASE='Instrumental breakbeat game score. Preserve the tonal center, recurring motif and rhythmic identity of the reference audio. Crisp syncopated drums, electric synth bass, pulsing synths, bright arpeggiators. No vocals. '
def encode():
 import section_experiment as e
 e.O=O;e.BASE=BASE
 e.ROLES={k:v.replace('D pedal','tonic pedal').replace('D minor chord','tonic chord') for k,v in ROLES.items()}
 os.environ["ROADSCORE_CONDITION_ID"]="songform2"
 e.encode()
 # Keep the prior first screen immutable; use distinct conditioner identity.

def probe():
 import soundfile as sf
 sequence=['verse','prechorus','chorus','verse','bridge','chorus','outro'];last=R/'results/unattended/switchback_seed.npy';jobs=[]
 for i,role in enumerate(sequence):
  dest=O/f'{i}_{role}';assert not dest.with_suffix('.json').exists(),'Preserve prior run'
  req={'id':int(time.time()*1000),'run_id':'songform-key-preserving','identity':'songform2','conditioning':role,'seconds_total':180,'source_end':236 if i==0 else 302,'latents':str(last),'seed':9501+i,'context_frames':22,'anchor_frames':22,'anchor_latents':str(R/'results/unattended/switchback_seed.npy'),'anchor_end':180}
  tmp=G/'request.tmp';tmp.write_text(json.dumps(req));tmp.replace(G/'request.json');result=G/f'result_{req["id"]}.json';deadline=time.monotonic()+150
  while not result.exists():
   if time.monotonic()>deadline:raise TimeoutError(role)
   time.sleep(.1)
  r=json.loads(result.read_text());assert 'error' not in r,r;last=Path(r['latents']);wave,sr=sf.read(r['wav']);sf.write(dest.with_suffix('.wav'),wave[22*4096:-22*4096],sr);shutil.copy(last,dest.with_suffix('.npy'));r['request']=req;r['section']=role;dest.with_suffix('.json').write_text(json.dumps(r,indent=2));jobs.append(r);print(i,role,r['seconds'],flush=True)
 (O/'jobs.json').write_text(json.dumps(jobs,indent=2))
if __name__=='__main__':
 O.mkdir(parents=True,exist_ok=True);p=argparse.ArgumentParser();p.add_argument('mode',choices=['encode','probe']);a=p.parse_args();globals()[a.mode]()
