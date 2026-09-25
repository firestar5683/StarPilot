"""UI-thread lifecycle for parked Galaxy layout previews."""

import sys
import time

from openpilot.starpilot.galaxy.settings import LiveContextSource
from openpilot.starpilot.ui.layout_preview_renderer import LayoutPreviewRenderer
from openpilot.starpilot.ui.layout_preview_transport import PreviewService


class LayoutPreviewRuntime:
  def __init__(self, params, active_profile: str, *, offroad_hint=lambda: True, authority=None):
    self.renderer = LayoutPreviewRenderer()
    self.authority = authority if authority is not None else LiveContextSource(params)
    self.service = PreviewService(self.renderer, self.authority.parked, active_profile=active_profile)
    self._offroad_hint = offroad_hint
    self._hint_was_offroad = False
    self._warm = False
    self._warm_until = 0.0
    self._next_warm = 0.0
    self._next_authority_check = 0.0
    self._started = False
    self._closed = False
    try:
      self.service.start()
      self._started = True
    except (OSError, RuntimeError) as error:
      print(f"Layout preview unavailable: {error}", file=sys.stderr, flush=True)
      self.close()

  def _warm_authority(self, now: float) -> None:
    offroad = bool(self._offroad_hint())
    if not offroad:
      self._hint_was_offroad = False
      self._warm = False
      self._next_warm = now + 1.0
      return
    if not self._hint_was_offroad:
      self._warm_until = now + 2.0
      self._next_warm = now
    self._hint_was_offroad = True
    if not self._warm and now >= self._next_warm:
      self._warm = bool(self.authority.parked())
      self._next_warm = now + (0.1 if now < self._warm_until else 1.0)

  def poll(self) -> None:
    if not self._started:
      return
    try:
      observer = getattr(self.authority, 'observe_borrowed_device_clock', None)
      if observer is not None:
        observer()
      now = time.monotonic()
      self._warm_authority(now)
      if self.renderer.has_resources and now >= self._next_authority_check:
        self._next_authority_check = now + 1.0
        if not self.authority.parked():
          self.renderer.close()
      self.renderer.expire()
      self.service.poll()
    except Exception as error:
      print(f"Layout preview stopped: {error}", file=sys.stderr, flush=True)
      self.close()
      self._started = False

  def close(self) -> None:
    if self._closed:
      return
    self._closed = True
    try:
      self.service.close()
    except OSError as error:
      print(f"Layout preview shutdown: {error}", file=sys.stderr, flush=True)
    finally:
      self._started = False
      try:
        self.authority.close()
      finally:
        self.renderer.close()
