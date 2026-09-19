"""Silent controlled A/B. Timed synthetic events are declared, never route fixtures."""
from pathlib import Path
import sys,json
import numpy as np,soundfile as sf
P=Path(__file__).resolve().parent;R=P.parents[1];sys.path.insert(0,str(R/'prototype'));sys.path.insert(0,str(P))
from musical_gestures_v3 import MusicalGestures as V3
from musical_gestures_v2 import MusicalGestures as V2
O=R/'results/ace_stability_20260916/gestures';O.mkdir(parents=True,exist_ok=True)
source,rate=sf.read(R/'results/composition_20260916/ace/structured90.wav',dtype='float32',always_2d=True);source=source[:60*rate]*.65
reports={}
for version,cls in [('v2',V2),('v3',V3)]:
 g=cls(source[:8*rate],rate,128);blocks=[]
 for frame in range(0,len(source),4800):
  t=frame/rate;road={'kind':'curve','phase':'anticipation','activation':1,'lead':26-t} if 20<=t<26 else {}
  nav={'valid':True,'type':'turn','modifier':'left','revision':1,'distance':60} if 32<=t<33 else {}
  g.update(frame,left=2<=t<14,road=road,nav=nav,speed=0 if 40<=t<44 else 12,outro=t>=53,input_ns=round(t*1e9))
  if frame==36*rate:g.schedule('lane_change',g.beat(frame+1),frame,round(t*1e9),'controlled lane change example')
  blocks.append(g.render(source[frame:frame+4800]))
 a=np.concatenate(blocks);sf.write(O/(version+'.wav'),a,rate,subtype='PCM_24');reports[version]={'events':g.events,'peak':float(abs(a).max()),'rms':float(np.sqrt(np.mean(a*a))),'late':sum(e.get('lateness_frames',0)>0 for e in g.events),'signal_phrases':sum(e.get('type')=='started' and e.get('tag')=='signal' for e in g.events)}
 for kind in g.phrases:
  phrase=g.phrases[kind];sf.write(O/(version+'_'+kind+'.wav'),phrase,rate,subtype='PCM_24')
sf.write(O/'dry.wav',source,rate,subtype='PCM_24');(O/'audit.json').write_text(json.dumps({'fixture':'controlled synthetic events, no recorded route timestamps','events_seconds':{'signal_on':2,'signal_off':14,'curve_preparation':20,'predicted_curve_peak':26,'navigation':32,'lane_change':36,'stop':40,'resume':44,'outro':53},'results':reports,'human_acceptance':None},indent=2));print({k:{x:v[x] for x in ['late','signal_phrases','peak']} for k,v in reports.items()})
