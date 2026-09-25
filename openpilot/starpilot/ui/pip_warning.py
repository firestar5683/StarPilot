"""Display-only V-ASM warning subscription for the native side-camera preview."""

from collections.abc import Callable
from typing import Any

import openpilot.cereal.messaging as messaging


def _new_reader() -> Any:
  # Keep the camera inference package out of the normal UI startup path.
  from openpilot.starpilot.spot_monitor.observation import ObservationReader
  return ObservationReader()


class PiPWarningSource:
  """Keep one nonblocking full-Event subscription while the preview is eligible."""

  def __init__(self, *, subscribe: Callable[[], Any] | None = None,
               receive: Callable[[Any], Any] | None = None,
               reader: Any = None):
    self._subscribe = subscribe or (lambda: messaging.sub_sock("spotMonitorState", conflate=True))
    self._receive = receive or messaging.recv_one_or_none
    self._reader = reader
    self._socket: Any = None
    self._active = False

  def close(self) -> None:
    if not self._active:
      return
    self._active = False
    socket, self._socket = self._socket, None
    self._reader = None
    if socket is not None:
      close = getattr(socket, "close", None)
      if callable(close):
        try:
          close()
        except Exception:
          pass  # Losing an optional visual feed cannot interrupt the UI.

  def sample(self, *, enabled: bool, settings_fingerprint: str,
             now_mono_ns: int, now_boot_ns: int) -> tuple[bool, bool]:
    if not enabled or not isinstance(settings_fingerprint, str) or len(settings_fingerprint) != 64:
      self.close()
      return False, False
    try:
      if self._socket is None:
        self._socket = self._subscribe()
        self._active = True
      if self._reader is None:
        self._reader = _new_reader()
      event = self._receive(self._socket)
      warning = (self._reader.read(event, now_mono_ns=now_mono_ns, now_boot_ns=now_boot_ns,
                                   settings_fingerprint=settings_fingerprint) if event is not None else
                 self._reader.current_at(now_mono_ns=now_mono_ns, now_boot_ns=now_boot_ns,
                                         settings_fingerprint=settings_fingerprint))
      return bool(warning.display_left.warning), bool(warning.display_right.warning)
    except Exception:
      # An optional display feed cannot take down the onroad UI.
      self.close()
      return False, False
