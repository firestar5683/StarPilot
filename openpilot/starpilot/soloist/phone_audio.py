"""Capture one paired phone through BlueALSA and feed the private music server.

The worker's arecord child shares its process group, so supervisor shutdown kills
both even if the output is blocked. ALSA plug converts to 48 kHz stereo; Pulse's
bounded playback queue keeps backpressure from growing an unbounded Python queue.
No system default audio device is opened.
"""
from __future__ import annotations

import ctypes as C
import os
import signal
import subprocess
import sys
from pathlib import Path

from openpilot.starpilot.soloist import backend
from openpilot.starpilot.soloist.preferences import ADDRESS

A2DP_SOURCE = '0000110a-0000-1000-8000-00805f9b34fb'
MEDIA_PLAYER = 'org.bluez.MediaPlayer1'
PLAYER_METHODS = {'play': 'Play', 'pause': 'Pause', 'next': 'Next', 'previous': 'Previous'}


def profile(action: str) -> None:
  if action not in ('acquire', 'release'):
    raise ValueError('Unknown profile action')
  command = ['/usr/bin/python3', str(Path(__file__).with_name('phone_profile.py')), action]
  if os.geteuid() != 0:
    command = ['/usr/bin/sudo', '-n', *command]
  result = subprocess.run(command, capture_output=True, text=True, timeout=60)
  if result.returncode:
    raise RuntimeError('Could not configure phone audio: ' + result.stderr.strip()[-500:])


class PhoneInput:
  def __init__(self):
    self.client = None
    self.next_connect = 0.0

  def _objects(self):
    from openpilot.starpilot.bluetooth.owner import BlueZ
    try:
      if self.client is None:
        self.client = BlueZ()
      return self.client._objects()
    except Exception as error:
      self.close()
      raise RuntimeError('Bluetooth is unavailable. Turn it on from the Bluetooth page.') from error

  def _call(self, *args, **kwargs):
    try:
      return self.client._call(*args, **kwargs)
    except Exception as error:
      raise RuntimeError(str(error)) from error

  def powered(self) -> bool:
    from openpilot.starpilot.bluetooth.owner import ADAPTER
    return any(interfaces.get(ADAPTER, {}).get('Powered') is True for interfaces in self._objects().values())

  def ready(self, address: str, now: float) -> bool:
    from openpilot.starpilot.bluetooth.owner import DEVICE
    for path, interfaces in self._objects().items():
      props = interfaces.get(DEVICE, {})
      if str(props.get('Address', '')).upper() != address:
        continue
      if not props.get('Paired') or props.get('Blocked'):
        return False
      if A2DP_SOURCE not in props.get('UUIDs', []):
        raise RuntimeError('The selected device does not offer Bluetooth music. Choose your phone.')
      # Connected alone does not mean A2DP is connected (e.g. an existing HFP link).
      if now >= self.next_connect:
        self.next_connect = now + 20
        try:
          self._call(path, DEVICE, 'ConnectProfile', 's', (A2DP_SOURCE,), timeout=5.0)
        except RuntimeError:
          if not props.get('Connected'):
            return False
      return bool(props.get('Connected'))
    return False

  def track(self, address: str) -> dict | None:
    """The phone's Bluetooth media player (title, artist, status), for the car screen; never raises."""
    try:
      from openpilot.starpilot.bluetooth.owner import DEVICE
      objects = self._objects()
      device = next((path for path, interfaces in objects.items()
                     if str(interfaces.get(DEVICE, {}).get('Address', '')).upper() == address), None)
      return next((interfaces[MEDIA_PLAYER] for path, interfaces in objects.items()
                   if device and path.startswith(device + '/') and MEDIA_PLAYER in interfaces), None)
    except Exception:
      return None

  def pause(self, address: str) -> None:
    self.control(address, 'pause')

  def control(self, address: str, action: str) -> None:
    if action not in (*PLAYER_METHODS, 'play_pause'):
      raise ValueError('Unsupported phone control')
    if self.client is None:
      return
    from openpilot.starpilot.bluetooth.owner import DEVICE
    objects = self._objects()
    device = next((path for path, interfaces in objects.items()
                   if str(interfaces.get(DEVICE, {}).get('Address', '')).upper() == address), None)
    if device:
      for path, interfaces in objects.items():
        if path.startswith(device + '/') and MEDIA_PLAYER in interfaces:
          if action == 'play_pause':
            action = 'pause' if str(interfaces[MEDIA_PLAYER].get('Status', '')).lower() == 'playing' else 'play'
          self._call(path, MEDIA_PLAYER, PLAYER_METHODS[action], timeout=2.0)
          return

  def close(self):
    if self.client is not None:
      try:
        self.client.close()
      except Exception:
        pass
      self.client = None
    self.next_connect = 0.0


def capture_config(address: str) -> str:
  if not ADDRESS.fullmatch(address):
    raise ValueError('Invalid phone Bluetooth address')
  return ('</usr/share/alsa/alsa.conf>\npcm.starpilot_phone {\n type plug\n slave.pcm {\n' +
          f'  type bluealsa\n  device "{address}"\n  profile "a2dp"\n' + ' }\n}\n')


class SampleSpec(C.Structure):
  _fields_ = [('format', C.c_int), ('rate', C.c_uint32), ('channels', C.c_uint8)]


class BufferAttr(C.Structure):
  _fields_ = [(name, C.c_uint32) for name in ('maxlength', 'tlength', 'prebuf', 'minreq', 'fragsize')]


class PulseWriter:
  def __init__(self, server: str):
    self.lib = C.CDLL('libpulse-simple.so.0')
    self.lib.pa_simple_new.argtypes = [C.c_char_p, C.c_char_p, C.c_int, C.c_char_p, C.c_char_p,
                                     C.POINTER(SampleSpec), C.c_void_p, C.POINTER(BufferAttr), C.POINTER(C.c_int)]
    self.lib.pa_simple_new.restype = C.c_void_p
    self.lib.pa_simple_write.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_int)]
    self.lib.pa_simple_write.restype = C.c_int
    self.lib.pa_simple_free.argtypes = [C.c_void_p]
    self.lib.pa_simple_free.restype = None
    spec = SampleSpec(3, 48000, 2)  # PA_SAMPLE_S16LE
    attr = BufferAttr(38400, 19200, 0xffffffff, 3840, 0xffffffff)  # 200 ms maximum, 100 ms target, refill before playing
    error = C.c_int()
    self.stream = self.lib.pa_simple_new(server.encode(), b'StarPilot phone', 1, backend.SINK_NAME.encode(), b'Phone music',
                                           C.byref(spec), None, C.byref(attr), C.byref(error))
    if not self.stream:
      raise RuntimeError(f'Phone audio output unavailable ({error.value})')

  def write(self, data: bytes):
    error = C.c_int()
    if self.lib.pa_simple_write(self.stream, data, len(data), C.byref(error)) < 0:
      raise RuntimeError(f'Phone audio output closed ({error.value})')

  def close(self):
    self.lib.pa_simple_free(self.stream)


def relay(address: str, server: str, config: Path):
  config.write_text(capture_config(address))
  os.chmod(config, 0o600)
  writer = PulseWriter(server)
  try:
    with subprocess.Popen(['/usr/bin/arecord', '-q', '-D', 'starpilot_phone', '-t', 'raw', '-f', 'S16_LE',
                           '-r', '48000', '-c', '2', '--buffer-time=200000', '--period-time=20000'],
                          env={**os.environ, 'ALSA_CONFIG_PATH': str(config)}, stdout=subprocess.PIPE) as capture:
      try:
        while data := capture.stdout.read(3840):
          if len(data) % 4:
            raise RuntimeError('Incomplete phone audio frame')
          writer.write(data)
      finally:
        capture.terminate()
        try:
          capture.wait(timeout=3)
        except subprocess.TimeoutExpired:
          capture.kill()
          capture.wait(timeout=3)
      if capture.returncode != 0:
        raise RuntimeError('Phone audio disconnected; reconnecting')
  finally:
    writer.close()


if __name__ == '__main__':
  # Exit after an abrupt supervisor death too, so stale phone audio cannot overlap a new source.
  parent = int(os.environ['STARPILOT_AUDIO_PARENT_PID'])
  libc = C.CDLL(None, use_errno=True)
  if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0 or os.getppid() != parent:
    raise SystemExit('Music supervisor stopped')

  def stopped(*_):
    raise SystemExit(0)
  signal.signal(signal.SIGTERM, stopped)
  relay(sys.argv[1], sys.argv[2], Path(sys.argv[3]))
