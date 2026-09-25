"""What the car shows: a separate StarPilot view or a test pattern.

The car view runs ``current_car_ui`` as a child process and reads its frames from a
dedicated shared-memory slot. An unavailable renderer sends no stale frames; a failed
renderer is restarted a bounded number of times before the session shows an
unavailable message until it ends.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from openpilot.starpilot.system.android_auto.frame_source import DEFAULT_PATH, FrameConsumer, FrameRequest, SyntheticFrames
from openpilot.starpilot.system.android_auto.projection_control import DEFAULT_CONTROL_SOCKET, ProjectionControlReceiver
from openpilot.starpilot.system.android_auto.touch import DEFAULT_TOUCH_SOCKET, TouchEvent, TouchSender

CAR_FRAME_PATH = "/dev/shm/starpilot_android_auto_car_frame"
CAR_STARTUP_TIMEOUT = 25.0   # loading the full UI (fonts, textures, layouts) takes a few seconds on device
CAR_STALL_TIMEOUT = 5.0
MAX_RESTARTS = 2
RESTART_WINDOW = 300.0
OUTPUT_TAIL_LINES = 40
OUTPUT_TAIL_BYTES = 8192


class UnavailableFrames:
  def demand(self, seconds: float = 1.0) -> None: pass
  def release_demand(self) -> None: pass
  def latest(self): return None
  def close(self) -> None: pass


class ViewSource:
  def __init__(self, view: str, request: FrameRequest, log, *, synthetic: bool = False, mirror_path: str = DEFAULT_PATH,
               car_path: str = CAR_FRAME_PATH, touch_path: str = DEFAULT_TOUCH_SOCKET,
               control_path: str = DEFAULT_CONTROL_SOCKET, renderer_command: list[str] | None = None, renderer_log: Path | None = None):
    self.log = log
    self.request = request
    self.mirror_path, self.car_path, self.touch_path, self.control_path = mirror_path, car_path, touch_path, control_path
    self.renderer_command = renderer_command or [sys.executable, "-m", "openpilot.starpilot.system.android_auto.current_car_ui",
                                                 "--frames", car_path, "--touch", touch_path, "--control", control_path]
    self.renderer_log = renderer_log
    self.process: subprocess.Popen | None = None
    self.touch: TouchSender | None = None
    self.control: ProjectionControlReceiver | None = None
    self.fallback_reason = ""
    self.started_at = time.monotonic()
    self.last_frame_at = 0.0
    self.unfocused_since: float | None = None
    self.frames = 0
    self.restarts: list[float] = []
    if synthetic:
      self.view = "synthetic"
      self.source = SyntheticFrames()
      self.source.configure(request)
    elif view == "car":
      self.view = "car"
      self._start_car()
    else:
      self.view = "unavailable"
      self.fallback_reason = ("mirror source is not installed" if view == "mirror" else
                              "renderer is unavailable")
      self.source = UnavailableFrames()

  def _consumer(self, path: str) -> FrameConsumer:
    consumer = FrameConsumer(path)
    consumer.configure(self.request)
    consumer.demand(1.0)
    return consumer

  def _start_car(self) -> None:
    self.source = self._consumer(self.car_path)
    try:
      self.control = ProjectionControlReceiver(self.control_path)
      output = subprocess.DEVNULL
      if self.renderer_log is not None:
        try:
          self.renderer_log.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
          output = open(self.renderer_log, "w")
        except OSError:
          output = subprocess.DEVNULL
      try:
        self.process = subprocess.Popen(self.renderer_command, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                                        close_fds=True)
      finally:
        if output is not subprocess.DEVNULL:
          output.close()
      self.touch = TouchSender(self.touch_path)
    except BaseException:
      self._stop_car()
      raise
    self.started_at = time.monotonic()
    self.log("car_view_started", pid=self.process.pid)

  @property
  def label(self) -> str:
    if self.fallback_reason:
      return f"display unavailable ({self.fallback_reason})"
    return self.view

  @property
  def waiting_for_first_frame(self) -> bool:
    return self.frames == 0 and not self.fallback_reason

  def demand(self, seconds: float = 1.0) -> None:
    self.source.demand(seconds)

  def release_demand(self) -> None:
    self.source.release_demand()

  def latest(self):
    frame = self.source.latest()
    if frame is not None:
      self.frames += 1
      self.last_frame_at = time.monotonic()
    return frame

  def send_touches(self, events: list[TouchEvent]) -> None:
    if self.touch is not None and self.view == "car" and events:
      self.touch.send(events)

  def drain_controls(self) -> list[str]:
    control = getattr(self, 'control', None)
    return control.drain() if control is not None and self.view == "car" else []

  def check(self, now: float | None = None, *, focused: bool = True) -> None:
    """Withdraw frames when the car view is not healthy.

    Frames are only pulled while the car shows projection, so the startup and
    stall timers are paused while it shows its own screen.
    """
    if self.view != "car":
      return
    now = time.monotonic() if now is None else now
    if not focused:
      if self.unfocused_since is None:
        self.unfocused_since = now
    elif self.unfocused_since is not None:
      paused = now - self.unfocused_since
      self.started_at += paused
      self.last_frame_at += paused
      self.unfocused_since = None
    reason = ""
    code = self.process.poll() if self.process is not None else None
    if code is not None:
      reason = f"renderer exited with {code}"
    elif not focused:
      pass
    elif self.frames == 0 and now - self.started_at > CAR_STARTUP_TIMEOUT:
      reason = f"no frames after {CAR_STARTUP_TIMEOUT:.0f} s"
    elif self.frames and now - self.last_frame_at > CAR_STALL_TIMEOUT:
      reason = f"frames stopped for {CAR_STALL_TIMEOUT:.0f} s"
    if reason:
      self._log_output(reason)
      self.restarts = [t for t in self.restarts if now - t < RESTART_WINDOW]
      if len(self.restarts) < MAX_RESTARTS:
        self.restarts.append(now)
        self.log("car_view_restart", reason=reason, attempt=len(self.restarts))
        self._stop_car()
        self.frames = 0
        self.unfocused_since = None
        self._start_car()
      else:
        self.fallback(reason)

  def _output_tail(self) -> list[str]:
    if self.renderer_log is None:
      return []
    try:
      with open(self.renderer_log, "rb") as f:
        f.seek(max(0, f.seek(0, os.SEEK_END) - OUTPUT_TAIL_BYTES))
        text = f.read().decode("utf-8", errors="replace")
    except OSError:
      return []
    return [line[:300] for line in text.splitlines()[-OUTPUT_TAIL_LINES:]]

  def _log_output(self, reason: str) -> None:
    process = self.process
    if process is not None and process.poll() is None:
      process.terminate()
      try:
        process.wait(timeout=3.0)
      except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2.0)
    lines = self._output_tail()
    if lines:
      self.log("car_view_output", reason=reason, lines=lines)

  def fallback(self, reason: str) -> None:
    self.log("car_view_fallback", reason=reason)
    self._stop_car()
    self.fallback_reason = reason
    self.view = "unavailable"
    self.frames = 0
    self.source = UnavailableFrames()

  def _stop_car(self) -> None:
    if self.touch is not None:
      self.touch.close()
      self.touch = None
    control = getattr(self, 'control', None)
    if control is not None:
      control.close()
      self.control = None
    process, self.process = self.process, None
    if process is not None and process.poll() is None:
      process.terminate()
      try:
        process.wait(timeout=3.0)
      except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2.0)
    self.source.close()

  def close(self) -> None:
    if self.view == "car" or self.process is not None:
      self._stop_car()
    else:
      self.source.close()


def renderer_available() -> bool:
  """The car view needs the GPU render node."""
  return os.path.exists("/dev/dri/renderD128")
