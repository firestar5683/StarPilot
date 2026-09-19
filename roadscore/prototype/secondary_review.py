"""Append preserved follow-up musical evidence to the one private listening page."""
import json
from pathlib import Path
import soundfile as sf
from bar_grid import join
R=Path(__file__).resolve().parents[1]/'results/overnight';p=R/'index.html';html=p.read_text()
follow=R/'followup';files=sorted(follow.glob('[0-9]_*.wav'))
if files:
 wave,sr=sf.read(files[0],always_2d=True);events=[]
 for path in files[1:]:
  other,other_sr=sf.read(path,always_2d=True);assert sr==other_sr
  wave,event=join(wave,other,sr,.03);event['section']=path.stem;events.append(event)
 sf.write(R/'chained_songform.wav',wave,sr);(R/'chained_songform.json').write_text(json.dumps({'duration':len(wave)/sr,'events':events,'human_verified':False},indent=2))
 html+='<h2>C2. Chained context, preserving the reference key</h2><p>A second generated sequence rather than reusing independent paired clips. Human identity/contrast/harmony judgment required.</p><audio controls preload="none" src="chained_songform.wav"></audio>'
for style,title in [('nightshift','E. Synthwave'),('brassline','F. Funk')]:
 html+=f'<h2>{title}</h2>'
 for path in sorted((R/'styles').glob(style+'_*.wav')):html+=f'<section>{path.stem}<audio controls preload="none" src="styles/{path.name}"></audio></section>'
p.write_text(html)
