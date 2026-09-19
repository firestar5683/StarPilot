"""Same-source, same-causal-state diagnostic A/B; never modifies primary live audio."""
import json
from pathlib import Path
import numpy as np,soundfile as sf
from musical import MusicalDSP
from driving_music import DrivingDSP
from phrase import pulse
R=Path('/data/roadscore');O=R/'results/dense';p=O/'ab_input'
a,sr=sf.read(p/'dry.wav',dtype='float32',always_2d=True);source,_=sf.read(R/'assets/source_horizon_drive.wav',dtype='float32',always_2d=True)
pi=pulse(source[:236*4096],44100);bpm=pi['bpm'];old=MusicalDSP(sr,bpm);new=DrivingDSP(sr,bpm)
blocks=[json.loads(t) for t in (p/'audio_blocks.jsonl').read_text().splitlines()];x=[];y=[]
for b in blocks:
 k=round(b['audio_s']*sr);chunk=a[k:k+4800]
 if len(chunk)!=4800:break
 new.event_state={'phase':b['phase'],'strength':b.get('strength',0)}
 amount=b['amount'];x.append(old.process(chunk,amount));y.append(new.process(chunk,amount))
x=np.concatenate(x);y=np.concatenate(y);lo=18*sr;hi=45*sr
sf.write(O/'curve_same_source_old.wav',x[lo:hi],sr);sf.write(O/'curve_same_source_reprises.wav',y[lo:hi],sr)
(O/'curve_ab.json').write_text(json.dumps({'bpm':bpm,'source':'live_curve dry capture, same already-recorded causal states','range_audio_s':[18,45],'note':'Diagnostic re-render only; primary player is actual live capture. Old is existing phrase echo using the same pulse estimate, new adds source-derived transient reprises.'},indent=2))
