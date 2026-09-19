"""Download model weights only; all inference runs locally. Run in experiment venv."""
import os
os.environ.setdefault('HF_HOME', '/data/roadscore-feasibility/cache/huggingface')
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
from huggingface_hub import snapshot_download
print(snapshot_download(
  'facebook/musicgen-small',
  revision='4c8334b02c6ec4e8664a91979669a501ec497792',
  local_dir='/data/roadscore-feasibility/musicgen-small',
  allow_patterns=['*.json', '*.model', 'model.safetensors'],
  max_workers=2,
))
