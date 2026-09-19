"""Arrange validated normal-runtime comparisons for the final listening gate."""
import os
from pathlib import Path
import json
import soundfile as sf
from bar_grid import join
R=Path(__file__).resolve().parents[1];O=R/'results/overnight';mapping={'verse':'0_verse','chorus':'2_chorus','bridge':'4_bridge'};rows=[]
for a,b in [('verse','chorus'),('chorus','bridge'),('bridge','chorus')]:
 left,sr=sf.read(O/f'followup/{mapping[a]}.wav',always_2d=True);right,_=sf.read(O/f'followup/{mapping[b]}.wav',always_2d=True)
 for name,overlap in [('cut',0),('short',.03),('crossfade',.2)]:
  wave,r=join(left.copy(),right,sr,overlap);stem=f'validated_{a}_{b}_{name}';sf.write(O/(stem+'.wav'),wave,sr);r.update(name=stem,from_section=a,to_section=b);rows.append(r)
(O/'validated_transitions.json').write_text(json.dumps(rows,indent=2))
route=R/'routes'/os.environ['ROADSCORE_ARRIVAL_ROUTE']/'roadscore/normal_1789527744';ending=json.loads((route/'ending.json').read_text());meta=json.loads((route/'metadata.json').read_text())
with sf.SoundFile(route/'score.flac') as source:
 source.seek(max(0,round((ending['audio_frame']/48000-20+meta['audio_zero_host_seconds'])*source.samplerate)));wave=source.read(dtype='float32',always_2d=True);sf.write(O/'native_arrival_outro.wav',wave,source.samplerate)
