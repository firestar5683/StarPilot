"""Separate, source-bound QCOM warp package for external Jetlink inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from tools.laptop_device_build.jetlink_pickle import require_jetlink_qcom_pickle

CAMERAS = ((1344, 760), (1928, 1208))
MODEL_SIZES = ((512, 256), (1024, 512))
MODEL_DIR = Path('openpilot/selfdrive/modeld/models')


def warp_names() -> tuple[str, ...]:
  return tuple(f'jetlink_warp_{cw}x{ch}_{mw}x{mh}.pkl' for cw, ch in CAMERAS for mw, mh in MODEL_SIZES)


def sha(path: Path) -> str:
  return hashlib.sha256(path.read_bytes()).hexdigest()


def sources(root: Path) -> dict[str, str]:
  files = [root / 'openpilot/starpilot/models/jetlink_warp.py',
           root / 'jetlink_repo/jetlink/openpilot/warp.py',
           root / 'jetlink_repo/jetlink/openpilot/interface.py',
           root / 'openpilot/common/transformations/camera.py',
           root / 'openpilot/common/transformations/model.py',
           root / 'openpilot/system/camerad/cameras/nv12_info.py']
  for folder in ('tinygrad_repo/tinygrad', 'tinygrad_repo/extra', 'tinygrad_repo/examples/openpilot'):
    files.extend(p for p in (root / folder).rglob('*') if p.is_file() and p.suffix in ('.py', '.c', '.h', '.cl') and '__pycache__' not in p.parts)
  if not (root / 'jetlink_repo/jetlink/openpilot/warp.py').is_file():
    raise ValueError('Pinned Jetlink warp sources are required')
  return {p.relative_to(root).as_posix(): sha(p) for p in sorted(files)}


def create(root: Path, package: Path) -> None:
  package.mkdir(parents=True, exist_ok=True)
  rows = {}
  for name in warp_names():
    path = root / MODEL_DIR / name
    require_jetlink_qcom_pickle(path)
    rows[name] = {'sha256': sha(path), 'size': path.stat().st_size}
    shutil.copyfile(path, package / name)
  (package / 'manifest.json').write_text(json.dumps({'version': 1, 'sources': sources(root), 'artifacts': rows}, indent=2) + '\n')


def import_artifact(package: Path, root: Path, target: Path) -> None:
  manifest = json.loads((package / 'manifest.json').read_text())
  if manifest.get('version') != 1 or manifest.get('sources') != sources(root):
    raise ValueError('Jetlink QCOM warp source closure differs; compile a current package on supported QCOM hardware')
  if set(manifest.get('artifacts', {})) != set(warp_names()):
    raise ValueError('Jetlink QCOM warp package has an incomplete geometry set')
  if target.parent.resolve() != (root / MODEL_DIR).resolve() or target.name not in warp_names():
    raise ValueError('Unexpected Jetlink warp target')
  row = manifest['artifacts'][target.name]
  artifact = package / target.name
  if row != {'sha256': sha(artifact), 'size': artifact.stat().st_size}:
    raise ValueError('Jetlink QCOM warp artifact digest or size differs')
  require_jetlink_qcom_pickle(artifact)
  target.parent.mkdir(parents=True, exist_ok=True)
  shutil.copyfile(artifact, target)


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--root', type=Path, default=Path.cwd())
  parser.add_argument('--package', type=Path, required=True)
  args = parser.parse_args()
  create(args.root.resolve(), args.package.resolve())


if __name__ == '__main__':
  main()
