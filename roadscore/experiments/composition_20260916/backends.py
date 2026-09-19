"""Small research boundary: capabilities and measured results, no model imports.

Each runner owns preparation, model-native request translation and decoding. The live
runtime keeps its existing SA3 job/PCM transport. Alternative adapters cannot be
selected live until capability, musical and accelerator gates have been evaluated.
"""
from dataclasses import dataclass,asdict
from pathlib import Path
import json
@dataclass(frozen=True)
class Backend:
 name:str
 execution:str
 runner:str
 controls:tuple[str,...]
 continuation:str
 live_eligible:bool=False
BACKENDS=(
 Backend('SA3 Small-Music','Chestnut native tinygrad','prototype/composition_sa3.py',('text','prefix audio latents','inpainting mask','duration conditioning'),'Actual prefix-conditioned continuation; exact tempo/key/form unverified',True),
 Backend('ACE-Step1.5 turbo','M1 Max MLX / PyTorch','experiments/composition_20260916/ace_probe.py',('caption','instrumental structure tags','tempo/key metadata','reference audio'),'Reference conditioning tested; repaint/cover exist upstream, not validated live'),
 Backend('YuE2-3B','M1 Max MPS / PyTorch','experiments/composition_20260916/yue_probe.py',('style','lyrics/structure tags','ABC melody/chord plan'),'Staged full-song generation; streaming continuation not tested'),
)
def inventory():return [asdict(b) for b in BACKENDS]
def measurements(root:Path):
 rows=[]
 for p in sorted((root/'sa3').glob('*.json')):
  d=json.loads(p.read_text());perf=d.get('performance',d)
  if 'seconds' not in perf:continue
  rows.append({'backend':'SA3','sample':p.stem,**perf})
 for p in sorted((root/'ace').glob('*/benchmark.json')):
  rows.append({'backend':'ACE-Step','sample':p.parent.name,**json.loads(p.read_text())})
 if (p:=root/'yue/benchmark.json').exists():rows.append({'backend':'YuE2','sample':'structured90',**json.loads(p.read_text())})
 return rows
