"""Read-only headless producer for a separate large StarPilot projection view.

Frames are rendered only while requested. Projection does not receive touch input.
Onroad, each new camera frame is drawn exactly once, as soon as it lands (see
CameraPacer). When the encoder takes NV12, the frame is converted on the GPU,
and it can be read back without stalling the renderer.
"""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import gc
import os
import signal
import time

from openpilot.starpilot.system.android_auto.frame_source import (FLAG_ASYNC_READBACK, FLAG_NV12, FORMAT_NV12, FORMAT_RGBA,
                                                                  FrameProducer, FrameRequest, frame_bytes)

from openpilot.starpilot.system.android_auto.projection_geometry import projection_geometry

STARTUP_WAIT_SECONDS = 15.0
CAMERA_WAIT_STEP = 0.01    # s; keeps demand/stop checks responsive while waiting for the camera
CAMERA_MAX_GAP = 0.1       # s; a shown camera silent this long stops pacing (the encoder rate applies)
ASYNC_READBACK_FAILURES = 3  # consecutive failed asynchronous readbacks before the session reads back synchronously


class CameraPacer:
  """Onroad, draw each frame of the camera on screen exactly once, as soon as it lands.

  The road cameras and the driving model run at 20 Hz. A 30 fps timer redraws
  every third frame for nothing and shows camera frames in an uneven 2-1
  cadence; a 20 fps timer drifts against the camera clock and periodically
  repeats one frame and skips the next. camerad hands the frame to VisionIPC
  before it publishes the matching CameraState, so waking on that message means
  CameraView's non-blocking recv already has the new frame.

  Only the shown camera's CameraState is subscribed, conflated and never
  deserialized: the pacer only needs to know that one arrived. When that camera
  goes quiet, it stops pacing and the encoder's frame rate applies again.
  """

  def __init__(self, sock_factory=None, stream_types=None):
    if sock_factory is None:
      import openpilot.cereal.messaging as messaging

      def sock_factory(name):
        poller = messaging.Poller()
        return poller, messaging.sub_sock(name, poller=poller, conflate=True)
    if stream_types is None:
      from openpilot.cereal.visionipc import VisionStreamType as stream_types
    self.state_for_stream = {int(stream_types.VISION_STREAM_NARROW_ROAD): "narrowRoadCameraState",
                             int(stream_types.VISION_STREAM_WIDE_ROAD): "wideRoadCameraState",
                             int(stream_types.VISION_STREAM_CABIN): "cabinCameraState"}
    self._sock_factory = sock_factory
    self._socks: dict[str, tuple] = {}   # opened on first use, so an unshown camera costs nothing
    self._last_arrival: dict[str, float] = {}

  def wait(self, stream_type, now: float) -> bool:
    """True when a new frame of ``stream_type`` is ready, or when that camera is quiet; waits at most one step."""
    state = self.state_for_stream.get(int(stream_type))
    if state is None:
      return True
    if state not in self._socks:
      self._socks[state] = self._sock_factory(state)
    poller, sock = self._socks[state]
    quiet = now - self._last_arrival.get(state, float("-inf")) >= CAMERA_MAX_GAP
    # A quiet camera must not hold rendering back: just check whether it has resumed.
    arrived = bool(poller.poll(0 if quiet else int(CAMERA_WAIT_STEP * 1000))) and sock.receive(non_blocking=True) is not None
    if arrived:
      self._last_arrival[state] = now
    return arrived or quiet


def create_readback(factory, size: int, asynchronous: bool):
  try:
    return factory(size, asynchronous=asynchronous)
  except (RuntimeError, OSError, AttributeError) as error:
    if not asynchronous:
      raise
    print(f"Async readback unavailable, using synchronous readback: {error}", flush=True)
    return factory(size, asynchronous=False)


def visible_geometry(request: FrameRequest) -> tuple[int, int, float, int, int]:
  geometry = projection_geometry(request.width, request.height, request.margin_w, request.margin_h)
  return (geometry.width, geometry.height, geometry.scale,
          round((geometry.width - geometry.logical_width * geometry.scale) / 2),
          round((geometry.height - geometry.logical_height * geometry.scale) / 2))


def wait_for_request(producer: FrameProducer) -> FrameRequest:
  deadline = time.monotonic() + STARTUP_WAIT_SECONDS
  while time.monotonic() < deadline:
    producer._next_open_check = 0.0
    request = producer.pending_request(require_demand=False)
    if request is not None:
      return request
    time.sleep(0.1)
  raise TimeoutError("Android Auto did not request current UI frames")


def run(frames_path: str) -> int:
  if os.geteuid() == 0:
    raise RuntimeError("Car display must run as the comma user")
  parent = os.getppid()
  try:
    os.nice(10)
  except OSError:
    pass

  os.environ['BIG'] = '1'
  os.environ['STARPILOT_PROJECTION_READ_ONLY'] = '1'
  stopped = False

  def stop(*_) -> None:
    nonlocal stopped
    stopped = True

  signal.signal(signal.SIGTERM, stop)
  signal.signal(signal.SIGINT, stop)
  from openpilot.starpilot.system.android_auto.headless_egl import FrameReadback, HeadlessContext
  from openpilot.starpilot.system.android_auto import gpu_nv12
  from openpilot.starpilot.system.android_auto.projection_onroad import ProjectionOnroad
  import pyray as rl
  from openpilot.system.ui.lib.application import gui_app
  from openpilot.selfdrive.ui.ui_state import ui_state

  with ExitStack() as resources:
    producer = FrameProducer(frames_path)
    resources.callback(producer.close)
    request = wait_for_request(producer)
    geometry = projection_geometry(request.width, request.height, request.margin_w, request.margin_h)
    context = HeadlessContext(request.width, request.height)
    resources.callback(context.close)

    def close_gui_textures():
      for texture in gui_app._textures.values():
        rl.unload_texture(texture)
      gui_app._textures.clear()

    resources.callback(close_gui_textures)
    gui_app._width, gui_app._height = geometry.logical_width, geometry.logical_height
    gui_app._scale = 1.0
    gui_app._render_texture = None
    from openpilot.starpilot.system.android_auto.identity import certificate_days_left
    from openpilot.starpilot.system.android_auto.projection_layout_runtime import load_projection_layout
    viewport = (geometry.logical_width, geometry.logical_height)
    layout = ProjectionOnroad(viewport=viewport, customization=load_projection_layout(viewport),
                              certificate_days=certificate_days_left())
    resources.callback(layout.close)
    content = rl.load_render_texture(geometry.logical_width, geometry.logical_height)
    if not content.id:
      raise RuntimeError('Projection content target unavailable')
    resources.callback(rl.unload_render_texture, content)
    output = rl.load_render_texture(request.width, request.height)
    if not output.id:
      raise RuntimeError('Projection output target unavailable')
    resources.callback(rl.unload_render_texture, output)
    converter = None
    if request.flags & FLAG_NV12:
      try:
        # The composed frame already carries the margins and the top-down flip,
        # so it converts as is. Reading back NV12 moves 1.5 bytes per pixel
        # instead of 4, and the encoder skips its own RGBA conversion on the CPU.
        converter = gpu_nv12.Nv12Converter(request.width, request.height)
        resources.callback(converter.close)
      except Exception as error:
        print(f"NV12 conversion unavailable, publishing RGBA: {error}", flush=True)
        converter = None
    pixel_format = FORMAT_NV12 if converter is not None else FORMAT_RGBA
    readback = create_readback(FrameReadback, frame_bytes(request.width, request.height, pixel_format),
                             asynchronous=bool(request.flags & FLAG_ASYNC_READBACK))
    resources.callback(lambda: readback.close())
    rgba_regions = [(output.id, request.width, request.height, 0)]
    pixel_format_name = 'nv12' if converter is not None else 'rgba'
    pipeline = f"{pixel_format_name}, {'async' if readback.asynchronous else 'sync'} readback"
    print(f"car view pipeline: {pipeline}", flush=True)
    from openpilot.starpilot.system.android_auto import identity as identity_store
    from openpilot.starpilot.system.android_auto.render_profile import RenderSampler, RenderSummary
    config = identity_store.load_config()
    sampler = None
    if config["render_profile"]:
      sampler = RenderSampler(identity_store.LOG_DIR / "render_profile.txt", max_bytes=config["render_profile_kb"] * 1024)
      sampler.start()
      resources.callback(sampler.close)
    summary = RenderSummary(time.monotonic())
    camera_pacer = CameraPacer()
    in_flight_ns = 0

    async_failures = 0

    def publish_readback() -> None:
      """Hand the frame read back last to android_autod.

      A failed asynchronous wait drops only that frame; repeated failures switch
      the session to synchronous readback instead of crashing the renderer."""
      nonlocal async_failures
      try:
        try:
          pixels = readback.finish()
        except RuntimeError as error:
          if not readback.asynchronous:
            raise
          async_failures += 1
          print(f"car view dropped a frame: {error}", flush=True)
          if async_failures >= ASYNC_READBACK_FAILURES:
            readback.fall_back_to_sync()
            print(f"car view pipeline: {pixel_format_name}, sync readback (async failed {async_failures} times in a row)", flush=True)
          return
        async_failures = 0
        producer.publish(request, pixels, in_flight_ns, pixel_format, advance=False)
      finally:
        readback.release()

    # Everything built so far lives for the whole session. Frozen, it is never rescanned
    # by the collector, whose full passes over the UI's objects stall a frame every few seconds.
    gc.collect()
    gc.freeze()
    while not stopped and os.getppid() == parent:
      now = time.monotonic()
      pending = producer.pending_request(now)
      if pending is None:
        if readback.pending:
          readback.release()
        if sampler is not None:
          sampler.rendering = False
        context.pause()
        time.sleep(0.05)
        summary.reset(time.monotonic())
        continue
      if pending != request:
        return 3  # supervisor starts a new renderer for the new geometry
      captured_ns = time.monotonic_ns()
      # The requested frame rate (the encoder's budget) always applies. Rendering
      # only when it is due also keeps the schedule from running ahead of real time.
      delay = producer.capture_delay(request, captured_ns)
      if delay > 0:
        if readback.pending:
          publish_readback()  # never hold a finished frame back just to pace the next one
        if sampler is not None:
          sampler.rendering = False
        time.sleep(min(delay, 0.05))
        continue
      if layout.camera_stream is not None:
        # Within that budget, draw as soon as the camera on screen has a new frame.
        if readback.pending:
          publish_readback()
        if not camera_pacer.wait(layout.camera_stream, now):
          if sampler is not None:
            sampler.rendering = False
          continue
        captured_ns = time.monotonic_ns()
        now = captured_ns / 1e9
      if sampler is not None:
        sampler.rendering = True
      frame_began = time.monotonic()
      context.begin_frame(now)
      ui_state.update()
      if sampler is not None:
        sampler.onroad = ui_state.started
      layout.prepare()  # offscreen passes (the map) must not run inside the content target
      rl.begin_texture_mode(content)
      try:
        rl.clear_background(rl.BLACK)
        layout.render()
      finally:
        rl.end_texture_mode()
      if readback.pending:
        # The previous frame, read back while this one was drawn: waiting any
        # later only adds latency.
        publish_readback()
      gpu_nv12.compose_rgba(content.texture, output, request.margin_w, request.margin_h, fit=True)
      regions = converter.convert(output.texture) if converter is not None else rgba_regions
      producer.advance(request, captured_ns)
      readback.start(regions)
      in_flight_ns = captured_ns
      if not readback.asynchronous:
        publish_readback()
      report = summary.frame_done(frame_began, time.monotonic())
      if report is not None and sampler is not None:
        sampler.summary = report
      gui_app._frame += 1
  return 0


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--frames", required=True)
  args = parser.parse_args()
  return run(args.frames)


if __name__ == "__main__":
  raise SystemExit(main())
