"""Private offline analysis/assembly of generated candidates; never reads route logs."""
import json
from pathlib import Path
import numpy as np,soundfile as sf
from bar_grid import grid,join
R=Path(__file__).resolve().parents[1];O=R/'results/overnight/sections';review=R/'results/overnight';rows=[]
for path in sorted(O.glob('*.wav')):
 wave,sr=sf.read(path,always_2d=True);g=grid(wave,sr);r=json.loads(path.with_suffix('.json').read_text());r.update(grid=g)
 rms=np.sqrt(np.mean(wave.reshape(-1,2)**2));r['analysis']={'rms':float(rms),'near_silent_fraction':float(np.mean(abs(wave)<1e-4))}
 rows.append(r)
(O/'analysis.json').write_text(json.dumps(rows,indent=2))
strategy='short_anchor';clips={r:sf.read(O/f'{strategy}_{r}.wav',always_2d=True)[0] for r in ['intro','verse','prechorus','chorus','bridge','outro']};sr=44100
transitions=[]
for a,b in [('verse','chorus'),('chorus','bridge'),('bridge','chorus')]:
 for name,overlap in [('cut',0),('short',.03),('bar_crossfade',.2)]:
  wave,meta=join(clips[a].copy(),clips[b],sr,overlap);name=f'{a}_{b}_{name}';sf.write(review/f'{name}.wav',wave,sr);meta.update(name=name,from_section=a,to_section=b);transitions.append(meta)
sequence=['intro','verse','prechorus','chorus','verse','bridge','chorus','outro'];wave=clips[sequence[0]].copy();schedule=[{'section':'intro','start':0}]
for role in sequence[1:]:
 wave,meta=join(wave,clips[role],sr,.03);schedule.append({'section':role,'start':meta['actual_transition_seconds'],'transition':meta})
sf.write(review/'songform.wav',wave,sr);(review/'songform.json').write_text(json.dumps({'duration':len(wave)/sr,'sequence':schedule,'selection':'Controlled short-anchor candidate, provisional pending human listening; no automated musical pass'},indent=2));(review/'transitions.json').write_text(json.dumps(transitions,indent=2))
html=['<!doctype html><meta charset="utf-8"><title>RoadScore overnight review</title><style>body{background:#10151d;color:#eef;font:17px system-ui;max-width:980px;margin:40px auto}audio{width:100%}section{padding:18px;border:1px solid #345;border-radius:12px;margin:20px 0}small{color:#abc}</style><h1>RoadScore · Song form research</h1><p>All rendering was physically muted. Press play only when ready for human evaluation. No autoplay. Section labels are requested roles, not verified musical outcomes. Bar estimates are uncertain on syncopated music.</p><h2>A. Breakbeat identity</h2>']
for role in clips:html.append(f'<section><h3>{role.title()}</h3><audio controls preload="none" src="sections/short_anchor_{role}.wav"></audio></section>')
html.append('<h2>B. Transition comparison</h2>')
for meta in transitions:html.append(f'<section>{meta["name"]} · landing {meta["actual_transition_seconds"]:.2f}s · overlap {meta["overlap_seconds"]:.3f}s<audio controls preload="none" src="{meta["name"]}.wav"></audio></section>')
html.append(f'<h2>C. Long form ({len(wave)/sr:.1f}s)</h2><p>Explicit arranged section sequence; human assessment of identity, contrast and harmonic coherence remains required.</p><audio controls preload="none" src="songform.wav"></audio><details><summary>Controlled alternatives</summary>')
for strategy in ['anchored','prefix_only']:
 for role in clips:html.append(f'<section>{strategy} · {role}<audio controls preload="none" src="sections/{strategy}_{role}.wav"></audio></section>')
html.append('</details>');(review/'index.html').write_text('\n'.join(html))
