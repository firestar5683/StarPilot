"""Opt-in diagnostics and screen snapshots for the iPhone pilot."""
import base64
import hashlib
import hmac
import json
import logging
import math
import os
import queue
import struct
import subprocess
from pathlib import Path
import threading
import tempfile
import time

DATA = Path('/dev/shm/galaxy-companion')
ENABLED = Path('/data/galaxy-ble/diagnostics-enabled')
_lock = threading.Lock()
_nonces = {}


def atomic_write(name, content):
  DATA.mkdir(mode=0o700, exist_ok=True)
  with tempfile.NamedTemporaryFile(dir=DATA, prefix=name + '.', suffix='.tmp', delete=False) as output:
    temporary = Path(output.name)
    try:
      output.write(content)
      output.flush()
      os.replace(temporary, DATA / name)
    finally:
      temporary.unlink(missing_ok=True)


def register_routes(app):
  from flask import Response, jsonify, request, stream_with_context
  from openpilot.tools.galaxy_bluetooth.bridge.pairing import load_key

  def allowed(path):
    if not ENABLED.exists():
      return False
    nonce = request.headers.get('X-Companion-Nonce', '')
    mac = request.headers.get('X-Companion-MAC', '')
    if len(nonce) != 32 or any(c not in '0123456789abcdef' for c in nonce):
      return False
    try:
      expected = hmac.new(load_key(), f'{nonce}\nGET\n{path}'.encode(), hashlib.sha256).hexdigest()
    except (OSError, ValueError, KeyError):
      return False
    if not hmac.compare_digest(mac, expected):
      return False
    now = time.monotonic()
    with _lock:
      for key, expiry in list(_nonces.items()):
        if expiry <= now:
          del _nonces[key]
      if nonce in _nonces or len(_nonces) >= 1024:
        return False
      _nonces[nonce] = now + 120
    return True

  def denial(path):
    if not ENABLED.exists():
      return jsonify(error='Diagnostics are disabled on comma.'), 503
    if not allowed(path):
      return jsonify(error='Phone pairing was rejected.'), 403
    return None

  @app.get('/api/companion/diagnostics')
  def diagnostics():
    rejected = denial('/api/companion/diagnostics')
    if rejected is not None:
      return rejected
    try:
      sample = json.loads((DATA / 'diagnostics.json').read_bytes())
      sample['ageSeconds'] = max(0, time.monotonic() - sample.pop('monotonic'))
      response = jsonify(sample)
      response.headers['Cache-Control'] = 'no-store'
      return response
    except (OSError, ValueError, KeyError):
      return jsonify(error='Waiting for comma UI telemetry.'), 503

  @app.get('/api/companion/frame')
  def frame():
    rejected = denial('/api/companion/frame')
    if rejected is not None:
      return rejected
    atomic_write('capture-request', str(time.monotonic()).encode())
    try:
      raw = (DATA / 'frame.bin').read_bytes()
      captured = struct.unpack('!d', raw[:8])[0]
      age = max(0, time.monotonic() - captured)
      if age > 1 or len(raw) > 650008:
        return jsonify(error='Waiting for a fresh screen frame.'), 503
      response = jsonify(image=base64.b64encode(raw[8:]).decode(), ageSeconds=age)
      response.headers['Cache-Control'] = 'no-store'
      return response
    except (OSError, ValueError, struct.error):
      return jsonify(error='Waiting for screen capture.'), 503

  @app.get('/api/companion/stream')
  def stream():
    rejected = denial('/api/companion/stream')
    if rejected is not None:
      return rejected
    session_key = load_key()

    @stream_with_context
    def frames():
      last = None
      started = time.monotonic()
      lease = 0.0
      while ENABLED.exists() and time.monotonic() - started < 60:
        now = time.monotonic()
        if now - lease >= 1:
          try:
            if not hmac.compare_digest(session_key, load_key()):
              return
          except (OSError, ValueError):
            return
          atomic_write('capture-request', str(now).encode())
          lease = now
          yield b'\r\n'
        try:
          raw = (DATA / 'frame.bin').read_bytes()
          captured = struct.unpack('!d', raw[:8])[0]
          if captured != last and 0 <= now - captured < 1 and 8 < len(raw) <= 650008:
            last = captured
            image = raw[8:]
            yield b'--galaxy-frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(image)).encode() + b'\r\n\r\n' + image + b'\r\n'
        except (OSError, ValueError, struct.error):
          pass
        time.sleep(0.01)

    response = Response(frames(), content_type='multipart/x-mixed-replace; boundary=galaxy-frame')
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Accel-Buffering'] = 'no'
    return response



class CompanionPublisher:
  def __init__(self):
    self.last = 0.0
    self.previous = {}
    self.received = {}
    self.last_capture = 0.0
    self.capture_failed_until = 0.0
    self.extra = None
    self.images = queue.Queue(maxsize=1)
    self.encoder = None
    self.process = None
    self.video_size = None
    self.sent_times = queue.Queue(maxsize=8)
    self.capture_hook = 0.0
    self.last_encoded = 0.0
    self.capture_error = None
    self.encoder_error = None
    self.encoder_stderr = None

  def update(self, ui, gui):
    if not ENABLED.exists():
      return
    now = time.monotonic()
    if self.extra is None:
      from cereal import messaging
      self.extra = messaging.SubMaster(['driverCameraState', 'chestnutState'])
    self.extra.update(0)
    rates = []
    sm = ui.sm
    sources = [('UI', gui.frame, 'FPS', now)]
    for source in (sm, self.extra):
      for service in source.services:
        recv = source.recv_time[service]
        if recv <= 0 or not source.valid.get(service, False):
          continue
        message = source[service]
        if hasattr(message, 'frameId'):
          sources.append((service, int(message.frameId), 'FPS', recv))
        else:
          seen = source.recv_frame[service]
          previous = self.received.get(service, (-1, 0))
          count = previous[1] + int(seen != previous[0])
          self.received[service] = (seen, count)
          sources.append((service, count, 'Hz observed', recv))
    if now - self.last < 1:
      return
    elapsed = now - self.last
    for name, count, unit, recv in sources:
      old = self.previous.get(name)
      fresh = now - recv < 3
      value = (count - old) / elapsed if old is not None and count >= old and fresh else None
      rates.append({'name': name, 'value': round(value, 1) if value is not None else None, 'unit': unit})
    self.previous = {name: count for name, count, _, _ in sources}
    self.last = now
    capture_status = {
      'hookAgeSeconds': round(now - self.capture_hook, 2) if self.capture_hook else None,
      'frameAgeSeconds': round(now - self.last_encoded, 2) if self.last_encoded else None,
      'queuedImages': self.images.qsize(), 'captureError': self.capture_error,
      'encoderError': self.encoder_error,
      'encoderStderr': self.encoder_stderr,
      'encoderExitCode': self.process.poll() if self.process is not None else None,
      'videoSize': list(self.video_size) if self.video_size else None,
      'encoderRunning': self.process is not None and self.process.poll() is None,
    }
    atomic_write('capture-status.json', json.dumps(capture_status).encode())
    temperatures = []
    device = sm['deviceState']
    if sm.valid['deviceState'] and now - sm.recv_time['deviceState'] < 3:
      for field in ('cpuTempC', 'gpuTempC', 'dspTempC', 'memoryTempC', 'modemTempC', 'pmicTempC', 'intakeTempC', 'exhaustTempC', 'gnssTempC', 'bottomSocTempC'):
        value = getattr(device, field, None)
        values = [value] if isinstance(value, (int, float)) else list(value or [])
        for i, reading in enumerate(values):
          reading = float(reading)
          names = {'cpu': 'CPU', 'gpu': 'GPU', 'dsp': 'DSP', 'pmic': 'PMIC', 'gnss': 'GNSS', 'bottomSoc': 'Bottom SoC'}
          stem = field.removesuffix('TempC')
          label = names.get(stem, stem.capitalize()) + (f' {i + 1}' if len(values) > 1 else '')
          temperatures.append({'name': label, 'value': round(reading, 1) if math.isfinite(reading) and reading > 0 else None, 'unit': '°C'})
    if self.extra.valid['chestnutState'] and now - self.extra.recv_time['chestnutState'] < 3:
      chestnut = self.extra['chestnutState']
      for label, field in [('External GPU', 'tempC'), ('External GPU memory', 'memoryTempC')]:
        value = float(getattr(chestnut, field, 0))
        temperatures.append({'name': label, 'value': round(value, 1) if math.isfinite(value) and value > 0 else None, 'unit': '°C'})
    for zone in sorted(Path('/sys/class/thermal').glob('thermal_zone*')):
      try:
        value = float((zone / 'temp').read_text()) / 1000
        if math.isfinite(value) and 0 < value < 200:
          temperatures.append({'name': 'Sensor: ' + (zone / 'type').read_text().strip(), 'value': round(value, 1), 'unit': '°C'})
      except (OSError, ValueError):
        pass
    for monitor in sorted(Path('/sys/class/hwmon').glob('hwmon*')):
      for sensor in sorted(monitor.glob('temp*_input')):
        try:
          value = float(sensor.read_text()) / 1000
          name = (monitor / 'name').read_text().strip()
          label_path = sensor.with_name(sensor.name.replace('_input', '_label'))
          label = label_path.read_text().strip() if label_path.exists() else sensor.stem
          if math.isfinite(value) and 0 < value < 200:
            temperatures.append({'name': f'Sensor: {name} {label}', 'value': round(value, 1), 'unit': '°C'})
        except (OSError, ValueError):
          pass
    atomic_write('diagnostics.json', json.dumps({'monotonic': now, 'engaged': bool(ui.engaged) if sm.valid.get('selfdriveState', False) and now - sm.recv_time.get('selfdriveState', 0) < 3 else None, 'temperatures': temperatures,
                 'rates': rates, 'captureLimitFPS': 20, 'capture': capture_status}, allow_nan=False, separators=(',', ':')).encode())

  def capture(self):
    if not ENABLED.exists():
      return
    now = time.monotonic()
    self.capture_hook = now
    if now < self.capture_failed_until or now - self.last_capture < 0.045 or self.images.full():
      return
    try:
      if now - float((DATA / 'capture-request').read_text()) > 4:
        return
    except (OSError, ValueError):
      return
    import pyray as rl
    image = None
    self.last_capture = now
    try:
      rl.rl_draw_render_batch_active()
      image = rl.load_image_from_screen()
      if not image.data or image.width <= 0 or image.height <= 0:
        raise ValueError('No screen pixels')
      width = min(image.width, 960)
      height = max(1, round(image.height * width / image.width))
      rl.image_resize(image, width, height)
      if self.encoder is None:
        self.encoder = threading.Thread(target=self.encode, daemon=True)
        self.encoder.start()
      self.images.put_nowait((image, now))
      self.capture_error = None
      image = None

    except Exception as error:
      self.capture_error = str(error)[:500]
      logging.getLogger("galaxy-companion").warning("Screen capture: %s", error)
      self.capture_failed_until = now + 10
    finally:
      if image is not None:
        rl.unload_image(image)

  def read_encoded(self, process, times):
    buffer = bytearray()
    try:
      while True:
        chunk = process.stdout.read1(65536)
        if not chunk:
          return
        buffer.extend(chunk)
        if len(buffer) > 1300000:
          return
        while True:
          start = buffer.find(b'\xff\xd8')
          end = buffer.find(b'\xff\xd9', max(0, start))
          if start < 0 or end < 0:
            break
          raw = bytes(buffer[start:end + 2])
          del buffer[:end + 2]
          captured = times.get(timeout=2)
          if len(raw) <= 650000 and time.monotonic() - captured < 1 and ENABLED.exists():
            atomic_write('frame.bin', struct.pack('!d', captured) + raw)
            self.last_encoded = captured
    except (OSError, ValueError, queue.Empty):
      pass
    finally:
      if process.poll() is None:
        process.kill()

  def encode(self):
    import pyray as rl
    while True:
      image, captured = self.images.get()
      try:
        if not ENABLED.exists() or time.monotonic() - captured > 1:
          continue
        dimensions = (image.width, image.height)
        if self.process is None or self.process.poll() is not None or self.video_size != dimensions:
          if self.process is not None and self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=2)
          self.sent_times = queue.Queue(maxsize=8)
          self.process = subprocess.Popen([
            'ffmpeg', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba',
            '-s:v', f'{image.width}x{image.height}', '-r', '20', '-i', 'pipe:0',
            '-an', '-c:v', 'mjpeg', '-q:v', '5', '-threads', '1', '-f', 'image2pipe',
            '-flush_packets', '1', 'pipe:1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
          self.video_size = dimensions
          self.encoder_error = None
          self.encoder_stderr = None
          threading.Thread(target=self.read_encoder_errors, args=(self.process,), daemon=True).start()
          threading.Thread(target=self.read_encoded, args=(self.process, self.sent_times), daemon=True).start()
        rl.image_format(image, rl.PIXELFORMAT_UNCOMPRESSED_R8G8B8A8)
        raw = bytes(rl.ffi.buffer(image.data, image.width * image.height * 4))
        self.sent_times.put_nowait(captured)
        self.process.stdin.write(raw)
        self.process.stdin.flush()
      except Exception as error:
        self.encoder_error = str(error)[:500]
        logging.getLogger("galaxy-companion").warning("Screen encoder: %s", error)
        self.capture_failed_until = time.monotonic() + 10
        if self.process is not None and self.process.poll() is None:
          self.process.kill()
      finally:
        rl.unload_image(image)
        self.images.task_done()

  def read_encoder_errors(self, process):
    try:
      for line in process.stderr:
        if process is self.process:
          self.encoder_stderr = line.decode(errors='replace').strip()[:500]
    except (OSError, ValueError):
      pass


publisher = CompanionPublisher()


def publish_telemetry(ui, gui):
  try:
    publisher.update(ui, gui)
  except Exception:
    pass


def capture_frame():
  try:
    publisher.capture()
  except Exception as error:
    publisher.capture_error = str(error)[:500]
