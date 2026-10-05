"""Read-only headless producer for a separate large StarPilot projection view.

Frames are rendered only while requested. Projection does not receive touch input.
"""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import os
import signal
import time

from openpilot.starpilot.system.android_auto.frame_source import FrameProducer, FrameRequest, frame_bytes

from openpilot.starpilot.system.android_auto.projection_geometry import projection_geometry

STARTUP_WAIT_SECONDS = 15.0


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
  from openpilot.starpilot.system.android_auto.gpu_nv12 import compose_rgba
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
    from openpilot.starpilot.system.android_auto.projection_layout_runtime import load_projection_layout
    viewport = (geometry.logical_width, geometry.logical_height)
    layout = ProjectionOnroad(viewport=viewport, customization=load_projection_layout(viewport))
    resources.callback(layout.close)
    content = rl.load_render_texture(geometry.logical_width, geometry.logical_height)
    if not content.id:
      raise RuntimeError('Projection content target unavailable')
    resources.callback(rl.unload_render_texture, content)
    output = rl.load_render_texture(request.width, request.height)
    if not output.id:
      raise RuntimeError('Projection output target unavailable')
    resources.callback(rl.unload_render_texture, output)
    readback = FrameReadback(frame_bytes(request.width, request.height, 0), asynchronous=False)
    resources.callback(readback.close)
    from openpilot.starpilot.system.android_auto import identity as identity_store
    from openpilot.starpilot.system.android_auto.render_profile import RenderSampler, RenderSummary
    config = identity_store.load_config()
    sampler = None
    if config["render_profile"]:
      sampler = RenderSampler(identity_store.LOG_DIR / "render_profile.txt", max_bytes=config["render_profile_kb"] * 1024)
      sampler.start()
      resources.callback(sampler.close)
    summary = RenderSummary(time.monotonic())
    while not stopped and os.getppid() == parent:
      now = time.monotonic()
      pending = producer.pending_request(now)
      if pending is None:
        if sampler is not None:
          sampler.rendering = False
        context.pause()
        time.sleep(0.05)
        summary.reset(time.monotonic())
        continue
      if pending != request:
        return 3  # supervisor starts a new renderer for the new geometry
      captured_ns = time.monotonic_ns()
      delay = producer.capture_delay(request, captured_ns)
      if delay > 0:
        if sampler is not None:
          sampler.rendering = False
        time.sleep(min(delay, 0.05))
        continue
      if sampler is not None:
        sampler.rendering = True
      frame_began = time.monotonic()
      context.begin_frame(now)
      ui_state.update()
      if sampler is not None:
        sampler.onroad = ui_state.started
      rl.begin_texture_mode(content)
      try:
        rl.clear_background(rl.BLACK)
        layout.render()
      finally:
        rl.end_texture_mode()
      compose_rgba(content.texture, output, request.margin_w, request.margin_h, fit=True)
      readback.start([(output.id, request.width, request.height, 0)])
      try:
        producer.publish(request, readback.finish(), captured_ns)
      finally:
        readback.release()
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
