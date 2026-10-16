from pathlib import Path
import hashlib
import json
import re
root = Path('GalaxyBluetooth/Resources/Web')
manifest = json.loads((root / 'galaxy-native-manifest.json').read_text())
listed = set()
for file in manifest['files']:
  path = file['path']
  listed.add(path)
  assert not path.startswith('/') and '..' not in path.split('/')
  data = (root / path).read_bytes()
  assert len(data) == file['size'] and hashlib.sha256(data).hexdigest() == file['sha256'], path
assert {'index.html', 'js/boot.js', 'js/app.js', 'data/catalog.json'} <= listed
assert not (root / 'data/runtime.json').exists(), 'Never ship preview runtime as a real comma'
assert not (root / 'data/system-monitor.sample.json').exists()
assert not (root / 'assets/mobile').exists()
for file in root.rglob('*.js'):
  for relative in re.findall(r'(?:from\s*|import\s*\()\s*[\"\'](\.[^\"\']+)[\"\']', file.read_text()):
    assert (file.parent / relative).is_file(), (file, relative)
for name in ['LANDiscovery.swift', 'Info.plist']:
  value = (Path('GalaxyBluetooth') / name).read_text()
  assert '_sp-galaxy._tcp' in value and '_starpilot-galaxy._tcp' not in value
for name in ['CarPlaySceneDelegate.swift', 'GalaxyBluetoothApp.swift', 'NetworkTransport.swift']:
  value = (Path('GalaxyBluetooth') / name).read_text()
  for old in ['/api/params', '/api/stats', '/api/device/status', '/api/personality_profiles', '/api/longitudinal_mode']:
    assert old not in value, (name, old)
print(f'SecretGood bundle: {len(listed)} verified files; imports, runtime isolation and endpoint migration passed')
