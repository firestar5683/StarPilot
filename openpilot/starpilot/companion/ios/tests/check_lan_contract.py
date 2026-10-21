from pathlib import Path
for name in ['LANDiscovery.swift', 'Info.plist']:
  value = (Path('GalaxyBluetooth') / name).read_text()
  assert '_sp-galaxy._tcp' in value and '_starpilot-galaxy._tcp' not in value
for name in ['CarPlaySceneDelegate.swift', 'GalaxyBluetoothApp.swift', 'NetworkTransport.swift']:
  value = (Path('GalaxyBluetooth') / name).read_text()
  for old in ['/api/params', '/api/stats', '/api/device/status', '/api/personality_profiles', '/api/longitudinal_mode']:
    assert old not in value, (name, old)
for name in ['GalaxyAssetStore.swift', 'LoopbackServer.swift', 'GalaxyBluetoothApp.swift']:
  value = (Path('GalaxyBluetooth') / name).read_text()
  assert 'bundledRoot' not in value and 'Resources/Web' not in value and 'raw.githubusercontent.com' not in value, name
assert not Path('GalaxyBluetooth/Resources/Web').exists(), 'Galaxy pages come from comma, never from the app bundle'
print('LAN contract: discovery service type, endpoint migration and no bundled Galaxy pages passed')
