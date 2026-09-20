"""Bind this process's BlueALSA PCM to the real operator-selected speaker."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ADDRESS = re.compile(r'^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$')


def real_selection(env=None, run=subprocess.run):
  child_env=dict(os.environ if env is None else env)
  for name in ('OPENPILOT_PREFIX', 'PARAMS_ROOT', 'ZMQ'):
    child_env.pop(name, None)
  code=('import json; from openpilot.common.params import Params; p=Params(); '
        'print(json.dumps({"enabled":p.get_bool("BluetoothEnabled"), '
        '"address":p.get("BluetoothAudioAddress",encoding="utf-8") or ""}))')
  result=run(['/usr/local/venv/bin/python', '-c', code], cwd='/data/openpilot',
             env=child_env, check=True, capture_output=True, text=True, timeout=5)
  return json.loads(result.stdout)


def prepare_output(directory, *, env=None, reader=real_selection,
                   alsa_base='/usr/share/alsa/alsa.conf', loaded_modules=None):
  """Call before importing sounddevice. Does not connect, pair, or open audio."""
  env=os.environ if env is None else env
  selection=reader(env)
  if selection.get('enabled') is not True:
    return {'bluetooth_selected':False}
  address=str(selection.get('address', '')).strip().upper()
  if not address:
    return {'bluetooth_selected':False}
  if not ADDRESS.fullmatch(address):
    raise ValueError('Selected Bluetooth audio address is invalid; output was not opened')
  modules=sys.modules if loaded_modules is None else loaded_modules
  if 'sounddevice' in modules:
    raise RuntimeError('Configure Bluetooth output before importing sounddevice')
  if env.get('ALSA_CONFIG_PATH'):
    raise RuntimeError('Existing ALSA_CONFIG_PATH must be reviewed before binding Bluetooth output')
  base=Path(alsa_base)
  if not base.is_file() or any(c in str(base) for c in '\n\r<>'):
    raise ValueError('A valid system ALSA configuration file is required')
  path=Path(directory).resolve()/'roadscore-bluealsa.conf'
  path.parent.mkdir(parents=True, exist_ok=True)
  config=f'<{base}>\n\ndefaults.bluealsa.!device "{address}"\ndefaults.bluealsa.!profile "a2dp"\n'
  # Exclusive creation protects existing configuration and keeps the change process-local.
  with path.open('x') as handle:
    os.chmod(path, 0o600)
    handle.write(config)
  env['ALSA_CONFIG_PATH']=str(path)
  return {'bluetooth_selected':True, 'address':address, 'output_identity':f'bluealsa:{address}',
          'profile':'a2dp', 'sample_rate':48000, 'channels':2, 'alsa_config':str(path),
          'timing_source':'PortAudio host/backend estimate; not measured acoustic Bluetooth latency',
          'physical_latency_ms':None}


def select_device(devices, metadata):
  if not metadata.get('bluetooth_selected'):
    return None
  matches=[index for index, device in enumerate(devices)
           if str(device.get('name', '')).strip().lower()=='bluealsa'
           and device.get('max_output_channels', 0)>=2]
  if len(matches)!=1:
    raise RuntimeError('Selected Bluetooth speaker requires one stereo BlueALSA output; no speaker fallback')
  return matches[0]
