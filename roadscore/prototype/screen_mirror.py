"""Opt-in native replay screen capture with one asynchronous JPEG slot."""
import io
import json
import os
from pathlib import Path
import queue
import re
import threading
import time

from replay_ui_controls import isolated_replay


class ScreenMirror:
  """The UI owns readback; a bounded worker owns resize, encoding and disk I/O."""
  def __init__(self, directory, session_id, *, fps=15, quality=78, max_width=1072):
    self.directory = Path(directory)
    if not self.directory.is_absolute() or self.directory == Path('/') or '..' in self.directory.parts:
      raise ValueError('Mirror directory must be an explicit absolute run directory')
    if not re.fullmatch(r'[a-zA-Z0-9-]{8,80}', session_id):
      raise ValueError('Mirror requires a valid showcase session')
    self.session_id = session_id
    self.interval = 1 / min(15, max(1, fps))
    self.quality = min(80, max(75, quality))
    self.max_width = min(1072, max(1, max_width))
    self._pending = queue.Queue(maxsize=1)
    self._busy = threading.Lock()
    self._closed = threading.Event()
    self._next_capture = 0.
    self._frame_id = 0
    self.last_error = None
    self._thread = threading.Thread(target=self._encode_loop, name='roadscore-screen-mirror', daemon=True)
    self._thread.start()

  @classmethod
  def from_environ(cls, environ):
    directory = environ.get('ROADSCORE_MIRROR_DIR')
    if (not directory or not isolated_replay(environ)
        or environ.get('ROADSCORE_PRESENTATION_POLICY', 'frozen') == 'frozen'
        or environ.get('ROADSCORE_SEED_ORIGIN') == 'judging-route'):
      return None
    try:
      return cls(directory, environ.get('ROADSCORE_SHOWCASE_SESSION', ''))
    except (ValueError, TypeError):
      return None

  def capture(self, readback, *, started, session_id, now=None):
    """Drop offroad, stale-session, rate-limited and busy frames before readback."""
    now = time.monotonic() if now is None else now
    if (self._closed.is_set() or not started or session_id != self.session_id
        or now < self._next_capture or not self._busy.acquire(blocking=False)):
      return False
    self._next_capture = now + self.interval
    begin = time.perf_counter()
    try:
      data, width, height, flipped = readback()
      if not 0 < width <= 4096 or not 0 < height <= 4096 or len(data) != width * height * 4:
        raise ValueError('Mirror readback must be a bounded RGBA frame')
      self._frame_id += 1
      job = dict(data=data, width=width, height=height, flipped=bool(flipped),
                 frame_id=self._frame_id, captured_wall=now,
                 capture_ms=(time.perf_counter()-begin)*1000)
      self._pending.put_nowait(job)
      return True
    except Exception as error:
      self.last_error = f'{type(error).__name__}: {error}'[:240]
      self._busy.release()
      return False

  def _encode(self, job):
    from PIL import Image
    begin = time.perf_counter()
    picture = Image.frombytes('RGBA', (job['width'], job['height']), job['data'])
    if job['flipped']:
      picture = picture.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if picture.width > self.max_width:
      picture = picture.resize((self.max_width, max(1, round(picture.height*self.max_width/picture.width))), Image.Resampling.BILINEAR)
    picture = picture.convert('RGB')
    encoded = io.BytesIO()
    picture.save(encoded, format='JPEG', quality=self.quality, optimize=False)
    metadata = dict(session_id=self.session_id, captured_wall=job['captured_wall'],
                    encoded_wall=time.monotonic(), frame_id=job['frame_id'], width=picture.width,
                    height=picture.height, encode_ms=(time.perf_counter()-begin)*1000,
                    capture_ms=job['capture_ms'])
    return encoded.getvalue(), metadata

  def _publish(self, data, metadata):
    self.directory.mkdir(parents=True, exist_ok=True)
    image_tmp = self.directory / ('.latest-' + self.session_id + '.jpg.tmp')
    metadata_tmp = self.directory / ('.frame-' + self.session_id + '.json.tmp')
    try:
      image_tmp.write_bytes(data)
      metadata_tmp.write_text(json.dumps(metadata, separators=(',', ':')))
      if not self._closed.is_set():
        os.replace(image_tmp, self.directory/'latest.jpg')
        os.replace(metadata_tmp, self.directory/'frame.json')
    finally:
      image_tmp.unlink(missing_ok=True)
      metadata_tmp.unlink(missing_ok=True)

  def _encode_loop(self):
    while not self._closed.is_set():
      try:
        job = self._pending.get(timeout=.1)
      except queue.Empty:
        continue
      try:
        if not self._closed.is_set():
          data, metadata = self._encode(job)
          if not self._closed.is_set():
            self._publish(data, metadata)
      except Exception as error:
        self.last_error = f'{type(error).__name__}: {error}'[:240]
      finally:
        self._busy.release()

  def close(self):
    """Do not block UI teardown on encoding or a slow filesystem."""
    self._closed.set()


def read_ui_rgba(rl, gui_app):
  """Call only from the native UI thread while its render target is active."""
  rl.rl_draw_render_batch_active()
  image = rl.load_image_from_texture(gui_app._render_texture.texture) if gui_app._render_texture else rl.load_image_from_screen()
  try:
    if not 0 < image.width <= 4096 or not 0 < image.height <= 4096:
      raise ValueError('Mirror render target is too large')
    data = bytes(rl.ffi.buffer(image.data, image.width*image.height*4))
    return data, image.width, image.height, bool(gui_app._render_texture)
  finally:
    rl.unload_image(image)
