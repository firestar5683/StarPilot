"""Re-score preserved PCM with playback-scale thresholds; no regeneration/future input."""
import json,sys
from dataclasses import replace
from pathlib import Path
import soundfile as sf
R=Path(__file__).resolve().parents[2];O=R/'results/ace_demo_20260916';sys.path.insert(0,str(R/'experiments/ace_chestnut_20260916'))
from quality_gate import POLICY,inspect
paths=list((O/'soak').glob('*/attempt_*.json'))+list((O/'resident_flow').glob('**/attempt_*.json'))
for route in json.loads((O/'replay_results.json').read_text()):
 if route.get('audio'):paths+=list((R/route['audio']).parent.glob('quality/*/attempt_*.json'))
rows=[]
for p in paths:
 m=json.loads(p.read_text());q=m.get('quality',{});wav=p.with_suffix('.wav')
 if not q or not wav.exists():continue
 wave,sr=sf.read(wav,dtype='float32',always_2d=True)
 # Standalone suite saves raw floats; resident worker saves at .65 output gain.
 saved_gain=1. if O/'soak' in p.parents else .65
 new=inspect(wave/saved_gain,sr,q['prefix_seconds'],role=q['role'])
 rows.append({'attempt':str(p.relative_to(R)),'old_policy':q['policy']['version'],'old_accepted':q['accepted'],'old_longest_quiet':q['longest_quiet_seconds'],'new_accepted':new['accepted'],'new_longest_quiet':new['longest_quiet_seconds'],'new_reasons':new['reasons']})
out={'policy':POLICY.__dict__,'count':len(rows),'changes':[r for r in rows if r['old_accepted']!=r['new_accepted']],'soak_accepted':sum(r['new_accepted'] for r in rows if '/soak/section_' in r['attempt']),'rows':rows}
(O/'output_gain_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))
