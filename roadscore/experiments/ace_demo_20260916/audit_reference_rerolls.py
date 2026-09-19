import sys,json
from pathlib import Path
import soundfile as sf
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'experiments/ace_chestnut_20260916'))
from quality_gate import inspect,reroll_seed
from window_policy import retained_end
rows=[]
for name,role,seed in [('community','chorus',2891394132),('curve','verse',2892054524)]:
 for i in range(3):
  p=R/f'results/ace_stability_20260916/cases/demo_bad_{name}_{i}/demo_reference';w,s=sf.read(p/'audio.wav',always_2d=True);w/=.65;error=None
  try:count,endpoint=retained_end(w,s,8,36)
  except ValueError as e:count=900;endpoint={};error=str(e)
  q=inspect(w[:count*1920],s,8,role=role,endpoint_error=error);report=json.loads((p/'report.json').read_text());row={'case':name,'role':role,'attempt':i,'seed':reroll_seed(seed,i),'quality':q,'endpoint':endpoint,'reference_generation_seconds':report['generation_seconds'],'reference_decode_seconds':report['decode_seconds'],'same_source_same_role':True};rows.append(row);print(name,i,q['accepted'],q['longest_quiet_seconds'],q['reasons'])
(R/'results/ace_demo_20260916/reroll_reference_audit.json').write_text(json.dumps(rows,indent=2))
