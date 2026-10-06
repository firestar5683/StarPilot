"""Closed local H.264 Quick road remux and authenticated byte serving."""

import http.client
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest import mock

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.drive_history import DriveHistory
from openpilot.starpilot.galaxy.recording_media import (RecordingMedia, RecordingMediaChanged, RecordingMediaNotPrepared,
                                                       RecordingMediaUnsupported,
                                                       VerifiedRecording, _ffmpeg_binary, byte_range)
from openpilot.starpilot.galaxy.server import make_server


NAME = '00000042--abcdef1234--0'


def make_h264(source: Path) -> None:
  """Four tiny real frames, with no lavfi or repository/media dependency."""
  source.parent.mkdir(parents=True, exist_ok=True)
  frame = bytes([48, 84, 126]) * (64 * 48)
  subprocess.run([str(_ffmpeg_binary()), '-nostdin', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo',
                  '-pix_fmt', 'rgb24', '-s', '64x48', '-r', '10', '-i', 'pipe:0', '-frames:v', '4',
                  '-c:v', 'libx264', '-f', 'mpegts', '-y', str(source)], input=frame * 4,
                 timeout=10, check=True)


class RecordingMediaTest(unittest.TestCase):
  def test_mutation_during_remux_and_unsupported_codec(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      source = root / NAME / 'qcamera.ts'
      make_h264(source)
      media = RecordingMedia(root)
      try:
        remux = media._remux
        def changed(verified):
          remux(verified)
          with source.open('ab') as output:
            output.write(b'late')
        with mock.patch.object(media, '_remux', side_effect=changed), self.assertRaises(RecordingMediaChanged):
          media.open(NAME)
        source.unlink()
        source.write_bytes(b'not an H.264 MPEG-TS stream')
        with self.assertRaises(RecordingMediaUnsupported):
          media.open(NAME)
      finally:
        media.close()

  def test_full_camera_segments_and_combined_video_keep_resolution_and_frames(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      route = NAME.rsplit('--', 1)[0]
      fixture = Path(__file__).with_name('fixtures') / 'tiny-camera.hevc.bin'
      for number in range(2):
        segment = root / f'{route}--{number}'
        segment.mkdir()
        make_h264(segment / 'qcamera.ts')
        for camera in ('fcamera', 'dcamera', 'ecamera'):
          (segment / f'{camera}.hevc').write_bytes(fixture.read_bytes())
      media = RecordingMedia(root)
      try:
        for camera in ('qcamera', 'fcamera', 'dcamera', 'ecamera'):
          for combined in (False, True):
            lease = media.open_route(route, camera=camera) if combined else media.open(NAME, camera=camera)
            try:
              decoded = subprocess.run([str(_ffmpeg_binary()), '-nostdin', '-hide_banner', '-loglevel', 'error',
                                        '-i', str(media._cache_path), '-fps_mode', 'passthrough', '-f', 'rawvideo',
                                        '-pix_fmt', 'rgb24', 'pipe:1'], capture_output=True, timeout=10, check=True)
              self.assertEqual(len(decoded.stdout), 64 * 48 * 3 * (8 if combined else 4))
              self.assertTrue(lease.source.current())
            finally:
              lease.close()
      finally:
        media.close()

  def test_closed_source_range_and_in_place_change(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      source = root / NAME / 'qcamera.ts'
      make_h264(source)
      media = RecordingMedia(root)
      try:
        with self.assertRaises(RecordingMediaNotPrepared):
          media.open(NAME, prepare=False)
        lease = media.open(NAME)
        self.assertGreater(lease.size, 100)
        self.assertTrue(lease.source.current())
        self.assertEqual(byte_range('bytes=0-15', lease.size), (0, 15))
        self.assertEqual(byte_range('bytes=-10', lease.size), (lease.size - 10, lease.size - 1))
        self.assertIsNone(byte_range('bytes=' + '9' * 5000 + '-', lease.size))
        with source.open('ab') as output:
          output.write(b'changed')
        self.assertFalse(lease.source.current(), 'same-inode append invalidates the original source identity')
        lease.close()
        repaired = media.open(NAME)
        self.assertGreater(repaired.size, 100)
        repaired.close()
        (source.parent / 'active.lock').touch()
        with self.assertRaises(RecordingMediaChanged):
          media.open(NAME)
      finally:
        media.close()

  def test_symlink_and_source_replacement(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      source = root / NAME / 'qcamera.ts'
      make_h264(source)
      verified = VerifiedRecording(root, NAME)
      source.rename(source.with_suffix('.old'))
      make_h264(source)
      self.assertFalse(verified.current())
      verified.close()
      source.unlink()
      source.symlink_to('qcamera.old')
      with self.assertRaises(RecordingMediaChanged):
        VerifiedRecording(root, NAME)

  def test_authenticated_get_range_head_logout(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      recordings = root / 'recordings'
      make_h264(recordings / NAME / 'qcamera.ts')
      access = GalaxyAccessOwner(root / 'access')
      access.configure('password123', lambda: True)
      server = make_server(port=0, owner=access, recordings=DriveHistory(recordings))
      worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
      worker.start()

      def request(method: str, path: str, *, cookie: str = '', range_header: str = ''):
        headers = {'Cookie': cookie} if cookie else {}
        if range_header:
          headers['Range'] = range_header
        if method == 'POST':
          headers.update({'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{server.server_port}'})
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        try:
          body = json.dumps({'password': 'password123'} if path.endswith('/login') else {}) if method == 'POST' else None
          connection.request(method, path, body, headers)
          response = connection.getresponse()
          return response.status, response.read(), dict(response.getheaders())
        finally:
          connection.close()

      path = f'/api/recordings/media/{NAME}'
      try:
        self.assertEqual(request('GET', path)[0], 401)
        status, _, headers = request('POST', '/api/auth/login')
        self.assertEqual(status, 200)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        self.assertEqual(request('HEAD', path, cookie=cookie)[0], 202, 'cold HEAD does not remux')
        status, video, headers = request('GET', path, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'video/mp4')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertIn(b'ftyp', video[:64])
        status, part, headers = request('GET', path, cookie=cookie, range_header='bytes=5-19')
        self.assertEqual((status, part), (206, video[5:20]))
        self.assertEqual(headers['Content-Range'], f'bytes 5-19/{len(video)}')
        self.assertEqual(request('HEAD', path, cookie=cookie)[0], 200)
        self.assertEqual(request('GET', path, cookie=cookie, range_header='bytes=' + '9' * 5000 + '-')[0], 416)
        self.assertEqual(request('POST', '/api/auth/logout', cookie=cookie)[0], 200)
        self.assertEqual(request('GET', path, cookie=cookie)[0], 401)
      finally:
        server.shutdown()
        worker.join(2)
        cache = server.recording_media_source._cache.name
        server.server_close()
        self.assertFalse(os.path.exists(cache), 'server shutdown removes its temporary MP4 cache')

  def test_logout_during_preparation_withholds_video(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      recordings = root / 'recordings'
      make_h264(recordings / NAME / 'qcamera.ts')
      access = GalaxyAccessOwner(root / 'access')
      access.configure('password123', lambda: True)
      ready, release = threading.Event(), threading.Event()

      class PausedMedia(RecordingMedia):
        def open(self, name, *, prepare=True, camera="qcamera"):
          lease = super().open(name, prepare=prepare, camera=camera)
          ready.set()
          release.wait(2)
          return lease

      server = make_server(port=0, owner=access, recordings=DriveHistory(recordings),
                           recording_media=PausedMedia(recordings))
      worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
      worker.start()

      def request(method, path, cookie=''):
        headers = {'Cookie': cookie} if cookie else {}
        if method == 'POST':
          headers.update({'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{server.server_port}'})
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        try:
          body = json.dumps({'password': 'password123'} if path.endswith('/login') else {}) if method == 'POST' else None
          connection.request(method, path, body, headers)
          response = connection.getresponse()
          return response.status, response.read(), dict(response.getheaders())
        finally:
          connection.close()

      try:
        cookie = request('POST', '/api/auth/login')[2]['Set-Cookie'].split(';', 1)[0]
        result = []
        pending = threading.Thread(target=lambda: result.append(request('GET', f'/api/recordings/media/{NAME}', cookie)))
        pending.start()
        try:
          self.assertTrue(ready.wait(2))
          self.assertEqual(request('POST', '/api/auth/logout', cookie)[0], 200)
        finally:
          release.set()
          pending.join(3)
        self.assertEqual(result[0][0], 401)
        self.assertNotIn(b'ftyp', result[0][1])
      finally:
        release.set()
        server.shutdown()
        worker.join(2)
        server.server_close()
