"""Authenticated recording responses with range and live-session checks."""
import os
from urllib.parse import unquote

from openpilot.starpilot.galaxy.recording_media import (RecordingMediaBusy, RecordingMediaChanged, RecordingMediaMissing,
                                                      RecordingMediaNotPrepared, RecordingMediaUnavailable,
                                                      RecordingMediaUnsupported, byte_range)


def camera_video(self, encoded_name: str, *, media, combined=False):
  if not self.require_session():
    return
  name, separator, camera = unquote(encoded_name).partition('/')
  camera = camera if separator else "qcamera"
  if not name or '/' in camera or '?' in name or camera not in {"qcamera", "fcamera", "dcamera", "ecamera"}:
    self.json(400, {'error': 'Invalid recording identity'})
    return
  try:
    lease = media().open_route(name, camera=camera, prepare=self.command != 'HEAD') if combined else \
      media().open(name, prepare=self.command != 'HEAD', **({'camera': camera} if camera != 'qcamera' else {}))
  except ValueError:
    if self.require_session():
      self.json(400, {'error': 'Invalid recording identity'})
    return
  except RecordingMediaMissing:
    if self.require_session():
      self.json(404, {'error': 'Closed camera recording unavailable'})
    return
  except RecordingMediaNotPrepared:
    if self.require_session():
      self.json(202, {'status': 'Camera video not prepared; use GET to prepare it'})
    return
  except RecordingMediaChanged:
    if self.require_session():
      self.json(409, {'error': 'Recording changed; refresh the inventory'})
    return
  except RecordingMediaUnsupported:
    if self.require_session():
      self.json(415, {'error': 'Camera recording format is unsupported'})
    return
  except (RecordingMediaBusy, RecordingMediaUnavailable, OSError):
    if self.require_session():
      self.json(503, {'error': 'Camera video unavailable'})
    return
  self.send_recording(lease)


def send_recording(self, lease, content_type='video/mp4'):
  try:
    if not self.require_session():
      return
    if not lease.source.current():
      self.json(409, {'error': 'Recording changed; refresh the inventory'})
      return
    selected = byte_range(self.headers.get('Range'), lease.size)
    if selected is None:
      self.send_response(416)
      self.send_header('Content-Range', f'bytes */{lease.size}')
      self.send_header('Content-Length', '0')
      self.send_header('Cache-Control', 'no-store')
      self.end_headers()
      return
    start, end = selected
    self.send_response(206 if self.headers.get('Range') is not None else 200)
    self.send_header('Content-Type', content_type)
    self.send_header('Content-Length', str(end - start + 1))
    self.send_header('Accept-Ranges', 'bytes')
    if self.headers.get('Range') is not None:
      self.send_header('Content-Range', f'bytes {start}-{end}/{lease.size}')
    self.send_header('Cache-Control', 'no-store')
    self.send_header('X-Content-Type-Options', 'nosniff')
    self.send_header('Referrer-Policy', 'no-referrer')
    self.end_headers()
    if self.command == 'HEAD':
      return
    cursor = start
    while cursor <= end and self.authenticated() and lease.source.current():
      chunk = os.pread(lease.video_fd, min(64 * 1024, end - cursor + 1), cursor)
      if not chunk:
        break
      self.wfile.write(chunk)
      cursor += len(chunk)
  finally:
    lease.close()
