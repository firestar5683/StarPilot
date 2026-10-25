"""Start the manager with desktop-only UI defaults in its isolated host runtime."""

import json
import os
from pathlib import Path
import subprocess
import sys


def attach_shared_bluetooth() -> None:
  """Reattach a previously shared Windows Bluetooth adapter after a WSL reboot."""
  try:
    state = subprocess.run(['usbipd.exe', 'state'], capture_output=True, text=True, timeout=5, check=True)
    devices = json.loads(state.stdout)['Devices']
  except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
    return
  if not isinstance(devices, list):
    return
  busid = next((device['BusId'] for device in devices if isinstance(device, dict) and isinstance(device.get('BusId'), str) and
                device.get('PersistedGuid') and not device.get('ClientIPAddress') and
                'bluetooth' in str(device.get('Description', '')).lower()), None)
  if busid is not None:
    try:
      subprocess.run(['usbipd.exe', 'attach', '--wsl', '--busid', busid], timeout=30, check=True)
    except (OSError, subprocess.SubprocessError):
      print('Bluetooth USB attach failed; check usbipd list', file=sys.stderr)


def main() -> None:
  if os.getenv('WSL_DISTRO_NAME'):
    attach_shared_bluetooth()
    try:
      mode = subprocess.run(['wslinfo', '--networking-mode'], capture_output=True, text=True, timeout=1, check=True)
      os.environ['SP_HOST_NETWORK_MODE'] = mode.stdout.strip()
    except (OSError, subprocess.SubprocessError):
      os.environ['SP_HOST_NETWORK_MODE'] = 'unknown'
  for path in (Path(os.environ['SP_HOST_GALAXY_BLE_DATA']), Path(os.environ['SP_HOST_BLUETOOTH_PREFERENCE']).parent):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)
  from openpilot.starpilot.ui.host_launch import seed_developer_defaults
  from openpilot.system.manager.manager import main as manager_main
  manager_main(after_init=seed_developer_defaults)


if __name__ == "__main__":
  main()
