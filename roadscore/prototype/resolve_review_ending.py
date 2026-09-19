"""Use the existing accepted cadence mechanism on the new generated long-form capture."""
import json
from pathlib import Path
import numpy as np,soundfile as sf
from musical import ending_gesture
from phrase import mix_cadence
R=Path(__file__).resolve().parents[1]/'results/overnight';wave,rate=sf.read(R/'chained_songform.wav',dtype='float32',always_2d=True);gesture,info=ending_gesture(wave[-12*rate:],rate);entry=len(wave)-2*rate;out=np.pad(wave,((0,max(0,entry+len(gesture)-len(wave))),(0,0)));out=mix_cadence(out,gesture,0,entry,rate);sf.write(R/'chained_songform_resolved.wav',out,rate);(R/'chained_ending.json').write_text(json.dumps({'entry_seconds':entry/rate,'duration':len(out)/rate,'method':'Existing source-derived ending_gesture and sample-exact mix_cadence','analysis':info,'human_verified':False},indent=2))
