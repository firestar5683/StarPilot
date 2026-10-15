#!/usr/bin/env python3
"""Generate the complete GitHub update manifest after editing bundled Galaxy.
Use --check in validation to reject stale hashes before publishing a UI update.
"""
from pathlib import Path
import hashlib
import json
import sys
root = Path(__file__).resolve().parents[1] / 'ios/GalaxyBluetooth/Resources/Web'
manifest = root / 'galaxy-native-manifest.json'
files = []
for path in sorted(root.rglob('*')):
    if path.is_file() and path != manifest:
        data = path.read_bytes()
        files.append(dict(path=path.relative_to(root).as_posix(), sha256=hashlib.sha256(data).hexdigest(), size=len(data)))
value = dict(schema=1, nativeBridge=1, files=files)
if '--check' in sys.argv:
    if json.loads(manifest.read_text()) != value:
        raise SystemExit('Galaxy manifest is stale; run scripts/generate_galaxy_manifest.py before publishing.')
    print(f'Galaxy update manifest: {len(files)} files verified')
else:
    manifest.write_text(json.dumps(value, indent=2) + '\n')
    print(f'Generated Galaxy update manifest: {len(files)} files')
