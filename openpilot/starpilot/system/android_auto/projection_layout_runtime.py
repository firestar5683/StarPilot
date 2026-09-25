"""Read the saved projection layout at connect, then again only after Galaxy saves it.

Never read on the drawing thread: a background thread stats the file once a second,
loads it only when it changed, and the renderer just takes the finished layout.
"""
import os
import threading

from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.system.android_auto.projection_layout import (
  DOCUMENT_KEY, MAX_BYTES, ProjectionLayoutSource, default_layout_for_viewport, decode_layout_for_viewport,
)


def load_projection_layout(viewport, source=None):
  raw, readable = read_saved(source or ProjectionLayoutSource(), DOCUMENT_KEY, MAX_BYTES)
  if not readable or raw is None:
    return default_layout_for_viewport(viewport)
  try:
    return decode_layout_for_viewport(raw, viewport)
  except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
    return default_layout_for_viewport(viewport)


CHECK_SECONDS = 1.0


class ProjectionLayoutWatcher:
  """Loads the layout and, on its own thread, picks up each layout Galaxy saves."""

  def __init__(self, viewport, source=None):
    self.viewport = viewport
    self.source = source or ProjectionLayoutSource()
    self._stamp = None
    self._lock = threading.Lock()
    self._pending = None
    self._stop = threading.Event()
    self._thread = None

  def start(self):
    self._thread = threading.Thread(target=self._run, name='aa-layout-watch', daemon=True)
    self._thread.start()

  def close(self):
    self._stop.set()
    if self._thread is not None:
      self._thread.join(timeout=2)

  def _run(self):
    while not self._stop.wait(CHECK_SECONDS):
      try:
        layout = self.poll()
      except Exception:
        continue  # a bad read must never stop live layout updates
      if layout is not None:
        with self._lock:
          self._pending = layout

  def take(self):
    """For the drawing thread: the newest saved layout not yet applied, or None. No file access."""
    with self._lock:
      layout, self._pending = self._pending, None
    return layout

  def _current_stamp(self):
    try:
      info = os.stat(self.source.get_param_path(DOCUMENT_KEY), follow_symlinks=False)
    except FileNotFoundError:
      return None
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns

  def load(self):
    self._stamp = self._current_stamp()
    return load_projection_layout(self.viewport, self.source)

  def poll(self):
    """Background thread only: the new layout after a save, or None. An unreadable file is retried."""
    try:
      stamp = self._current_stamp()
    except OSError:
      return None
    if stamp == self._stamp:
      return None
    raw, readable = read_saved(self.source, DOCUMENT_KEY, MAX_BYTES)
    if not readable:
      return None
    self._stamp = stamp
    if raw is None:
      return default_layout_for_viewport(self.viewport)
    try:
      return decode_layout_for_viewport(raw, self.viewport)
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
      return default_layout_for_viewport(self.viewport)
