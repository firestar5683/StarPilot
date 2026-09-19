"""Download authorized, pinned weights; auth header is not forwarded on redirects."""
import json,urllib.request
from pathlib import Path
ROOT=Path('/tmp/chestnut-sa3-weights');ROOT.mkdir(exist_ok=True)
REPO='stabilityai/stable-audio-3-small-music';REV='0fef1392cd842149a2b6d445e181c97608faac06'
token=(Path.home()/'.cache/huggingface/token').read_text().strip()
files=['model_config.json','model.safetensors','t5gemma-b-b-ul2/config.json','t5gemma-b-b-ul2/model.safetensors','t5gemma-b-b-ul2/tokenizer.model','t5gemma-b-b-ul2/tokenizer_config.json','t5gemma-b-b-ul2/special_tokens_map.json']
for filename in files:
 out=ROOT/filename;out.parent.mkdir(exist_ok=True)
 if out.exists():print('EXISTS',filename,flush=True);continue
 req=urllib.request.Request(f'https://huggingface.co/{REPO}/resolve/{REV}/{filename}')
 req.add_unredirected_header('Authorization','Bearer '+token)
 with urllib.request.urlopen(req,timeout=60) as r,out.with_suffix(out.suffix+'.tmp').open('wb') as f:
  while buf:=r.read(8*1024*1024):f.write(buf)
 out.with_suffix(out.suffix+'.tmp').rename(out)
 print('DOWNLOADED',filename,out.stat().st_size,flush=True)
