"""Download only published model/runtime files, no demonstration audio."""
import json,os
from pathlib import Path
from huggingface_hub import snapshot_download
P=Path(__file__).resolve().parent
allow=['config.json','generation_config.json','yue2_generation_config.json','weights_manifest.json','model.safetensors','model.safetensors.index.json','model-?????-of-?????.safetensors','qwen.tiktoken','modeling_yue2.py','modeling_vae.py','LICENSE','THIRD_PARTY_NOTICES.md','licenses/*.txt']
for repo,name in [('m-a-p/YuE2-3B','yue2'),('m-a-p/YuE2-Vae','yue2_vae')]:
 path=snapshot_download(repo,local_dir=P/'models'/name,allow_patterns=allow,max_workers=2);print(path,flush=True)
