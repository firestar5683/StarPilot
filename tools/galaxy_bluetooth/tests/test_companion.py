import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import importlib.util
import io
import json
from pathlib import Path
import sys
import struct
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

from flask import Flask

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('companion', ROOT / 'companion.py')
companion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(companion)
KEY = b'k' * 32


class CompanionTests(unittest.TestCase):
  def setUp(self):
    self.temporary = tempfile.TemporaryDirectory()
    self.addCleanup(self.temporary.cleanup)
    self.old_data, self.old_enabled = companion.DATA, companion.ENABLED
    companion.DATA = Path(self.temporary.name) / 'frames'
    companion.ENABLED = Path(self.temporary.name) / 'enabled'
    self.addCleanup(self.restore)
    companion._nonces.clear()
    module = types.ModuleType('openpilot.tools.galaxy_bluetooth.bridge.pairing')
    module.load_key = lambda: KEY
    self.fake_module = patch.dict(sys.modules, {module.__name__: module})
    self.fake_module.start()
    self.addCleanup(self.fake_module.stop)
    app = Flask(__name__)
    companion.register_routes(app)
    self.client = app.test_client()

  def restore(self):
    companion.DATA, companion.ENABLED = self.old_data, self.old_enabled

  def headers(self, path, nonce='a' * 32):
    mac = hmac.new(KEY, f'{nonce}\nGET\n{path}'.encode(), hashlib.sha256).hexdigest()
    return {'X-Companion-Nonce': nonce, 'X-Companion-MAC': mac}

  def test_overlapping_capture_requests_write_complete_files(self):
    barrier = threading.Barrier(4)
    replace = companion.os.replace
    payloads = [str(i).encode() * 4096 for i in range(4)]

    def overlapping_replace(source, destination):
      barrier.wait(timeout=5)
      replace(source, destination)

    with patch.object(companion.os, 'replace', side_effect=overlapping_replace):
      with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(lambda data: companion.atomic_write('capture-request', data), payloads))
    self.assertIn((companion.DATA / 'capture-request').read_bytes(), payloads)
    self.assertEqual(list(companion.DATA.glob('*.tmp')), [])

  def test_opt_in_authentication_and_replay(self):
    path = '/api/companion/diagnostics'
    headers = self.headers(path)
    self.assertEqual(self.client.get(path, headers=headers).status_code, 503)
    companion.ENABLED.touch()
    self.assertEqual(self.client.get(path).status_code, 403)
    bad = dict(headers, **{'X-Companion-MAC': '0' * 64})
    self.assertEqual(self.client.get(path, headers=bad).status_code, 403)
    companion.atomic_write('diagnostics.json', json.dumps({'monotonic': time.monotonic(), 'temperatures': [], 'rates': []}).encode())
    response = self.client.get(path, headers=headers)
    self.assertEqual(response.status_code, 200)
    self.assertLess(response.json['ageSeconds'], 1)
    self.assertEqual(response.headers['Cache-Control'], 'no-store')
    self.assertEqual(self.client.get(path, headers=headers).status_code, 403)
    self.assertEqual(self.client.post(path, headers=self.headers(path, 'b' * 32)).status_code, 405)

  def test_signature_bound_to_path_and_frame_staleness(self):
    companion.ENABLED.touch()
    path = '/api/companion/frame'
    wrong = self.headers('/api/companion/diagnostics')
    self.assertEqual(self.client.get(path, headers=wrong).status_code, 403)
    missing = self.client.get(path, headers=self.headers(path))
    self.assertEqual(missing.status_code, 503)
    self.assertTrue((companion.DATA / 'capture-request').exists())
    companion.atomic_write('frame.bin', struct.pack('!d', time.monotonic() - 10) + b'expired')
    self.assertEqual(self.client.get(path, headers=self.headers(path, 'b' * 32)).status_code, 503)
    companion.atomic_write('frame.bin', struct.pack('!d', time.monotonic()) + b'JPEG')
    fresh = self.client.get(path, headers=self.headers(path, 'c' * 32))
    self.assertEqual(fresh.status_code, 200)
    self.assertLess(fresh.json['ageSeconds'], 1)
    self.assertEqual(base64.b64decode(fresh.json['image']), b'JPEG')

  def test_disabled_capture_never_reads_gpu(self):
    publisher = companion.CompanionPublisher()
    publisher.update(None, None)
    publisher.capture()
    self.assertFalse(companion.DATA.exists())

  def test_capture_lease_expiry_and_error_containment(self):
    companion.ENABLED.touch()
    companion.atomic_write('capture-request', str(time.monotonic() - 20).encode())
    publisher = companion.CompanionPublisher()
    publisher.capture()
    self.assertEqual(publisher.last_capture, 0)
    with patch.object(companion.publisher, 'capture', side_effect=RuntimeError('GPU')):
      companion.capture_frame()
    self.assertEqual(companion.publisher.capture_error, 'GPU')
    companion.publisher.capture_error = None

  def test_encoder_error_is_visible_and_bounded(self):
    publisher = companion.CompanionPublisher()
    process = types.SimpleNamespace(stderr=io.BytesIO(b'encoder unavailable\n' + b'x' * 1000 + b'\n'))
    publisher.process = process
    publisher.read_encoder_errors(process)
    self.assertEqual(publisher.encoder_stderr, 'x' * 500)
    publisher.process = None
    process.stderr = io.BytesIO(b'old encoder error\n')
    publisher.read_encoder_errors(process)
    self.assertEqual(publisher.encoder_stderr, 'x' * 500)

  def test_capture_queue_is_bounded_and_preserves_aspect(self):
    companion.ENABLED.touch()
    companion.atomic_write('capture-request', str(time.monotonic()).encode())
    image = types.SimpleNamespace(data=True, width=2160, height=1080)
    calls = []
    raylib = types.ModuleType('pyray')
    raylib.rl_draw_render_batch_active = lambda: None
    raylib.load_image_from_screen = lambda: image
    raylib.image_resize = lambda _, width, height: calls.append((width, height))
    raylib.unload_image = lambda _: calls.append('unloaded')
    publisher = companion.CompanionPublisher()
    publisher.encoder = object()
    with patch.dict(sys.modules, {'pyray': raylib}):
      publisher.capture()
      publisher.capture()
    self.assertEqual(calls, [(960, 480)])
    self.assertEqual(publisher.images.qsize(), 1)
    self.assertIs(publisher.images.get()[0], image)

  def test_stream_sends_fresh_frames_and_stops_on_disable(self):
    companion.ENABLED.touch()
    companion.atomic_write('frame.bin', struct.pack('!d', time.monotonic()) + b'JPEG')
    path = '/api/companion/stream'
    response = self.client.get(path, headers=self.headers(path), buffered=False)
    self.assertEqual(response.status_code, 200)
    self.assertIn('multipart/x-mixed-replace', response.content_type)
    part = next(response.response)
    if part == b'\r\n':
      part = next(response.response)
    self.assertIn(b'Content-Length: 4', part)
    self.assertTrue(part.endswith(b'JPEG\r\n'))
    companion.ENABLED.unlink()
    self.assertEqual(list(response.response), [])
    response.close()

  def test_missing_sensors_and_measured_frame_rates(self):
    companion.ENABLED.touch()
    now = time.monotonic()
    class Source:
      services = ['deviceState', 'modelV2']
      recv_time = {'deviceState': now, 'modelV2': now, 'selfdriveState': now}
      recv_frame = {'deviceState': 1, 'modelV2': 1}
      valid = {'deviceState': True, 'modelV2': True, 'selfdriveState': True}
      device = types.SimpleNamespace(cpuTempC=[55, 56], gpuTempC=[0], memoryTempC=60)
      model = types.SimpleNamespace(frameId=100)
      def __getitem__(self, key):
        return self.device if key == 'deviceState' else self.model
    class Extra:
      services = []
      valid = {'chestnutState': False}
      def update(self, _): pass
    source = Source()
    ui = types.SimpleNamespace(sm=source, engaged=True)
    gui = types.SimpleNamespace(frame=10)
    publisher = companion.CompanionPublisher()
    publisher.extra = Extra()
    with patch.object(companion.time, "monotonic", return_value=now):
      publisher.update(ui, gui)
    first = json.loads((companion.DATA / 'diagnostics.json').read_bytes())
    self.assertIsNone(first['capture']['hookAgeSeconds'])
    self.assertFalse(first['capture']['encoderRunning'])
    gpu = next(m for m in first['temperatures'] if m['name'] == 'GPU')
    self.assertIsNone(gpu['value'])
    self.assertIsNone(next(m for m in first['rates'] if m['name'] == 'modelV2')['value'])
    gui.frame = 30
    source.model.frameId = 120
    publisher.capture_hook = now
    publisher.capture_error = 'No screen pixels'
    with patch.object(companion.time, 'monotonic', return_value=now + 1):
      publisher.update(ui, gui)
    sample = json.loads((companion.DATA / 'diagnostics.json').read_bytes())
    rate = next(m for m in sample['rates'] if m['name'] == 'modelV2')
    self.assertEqual(rate['value'], 20)
    self.assertEqual(rate['unit'], 'FPS')
    self.assertTrue(sample['engaged'])
    self.assertEqual(sample['capture']['hookAgeSeconds'], 1)
    self.assertEqual(sample['capture']['captureError'], 'No screen pixels')
    self.assertEqual(json.loads((companion.DATA / 'capture-status.json').read_bytes()), sample['capture'])


if __name__ == '__main__':
  unittest.main()
