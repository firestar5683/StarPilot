"""Opt-in bounded timings for an owner-created replay worker; no decoder or rate changes."""
from collections import Counter, deque
from contextlib import ExitStack, contextmanager
import argparse
import gc
import hashlib
import itertools
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
from types import SimpleNamespace

from tools.diagnostics.performance import Distribution, metadata

MAX_EVENTS = 30000
STAMPS = ('narrowRoadEncodeIdx', 'wideRoadEncodeIdx', 'cabinEncodeIdx',
          'carState', 'controlsState', 'selfdriveState', 'modelV2', 'radarState')


class Trace:
  def __init__(self):
    self.events = deque(maxlen=MAX_EVENTS)
    self.sequence = itertools.count(1)
    self.local = threading.local()
    self.count = self.attempt = 0
    self.outcomes = Counter()
    self.core = None
    self.pending_attempt = self.submitted_ns = None
    self.last_draw = 0.
    self.loop_now = None
    self.await_loop_clock = False
    self.connection_generation = 0
    self.capabilities = {}
    self.configuration = {}
    self.flush_requested = False

  def record(self, event):
    self.events.append(event)
    self.count += 1

  @contextmanager
  def span(self, stage):
    stack = getattr(self.local, 'stack', [])
    self.local.stack = stack
    event = {'id': next(self.sequence), 'stage': stage, 'thread': threading.get_ident(),
             'attempt': getattr(self.local, 'attempt', None), 'parent': stack[-1]['id'] if stack else None,
             'start_ns': time.monotonic_ns()}
    cpu = time.thread_time_ns()
    entry = {'id': event['id'], 'child_wall': 0, 'child_cpu': 0}
    stack.append(entry)
    try:
      yield event
    except BaseException as error:
      event['error_type'] = type(error).__name__
      raise
    finally:
      event['wall_ns'] = time.monotonic_ns() - event['start_ns']
      event['cpu_ns'] = time.thread_time_ns() - cpu
      event['exclusive_wall_ns'] = event['wall_ns'] - entry['child_wall']
      event['exclusive_cpu_ns'] = event['cpu_ns'] - entry['child_cpu']
      stack.pop()
      if stack:
        stack[-1]['child_wall'] += event['wall_ns']
        stack[-1]['child_cpu'] += event['cpu_ns']
      self.record(event)

  def snapshot(self):
    began = time.monotonic_ns()
    core = self.core
    sample, sm, camera = core.ui.replay_sample, core.ui.sm, core.camera
    client = camera.client
    connected = client is not None and client.is_connected()
    frame = camera.frame if connected else None
    return {'epoch': getattr(sample, 'epoch', None), 'route_ns': getattr(sample, 'now_ns', None),
            'boot_ns': getattr(sample, 'boot_ns', None), 'clock_valid': getattr(sample, 'valid', False),
            'paused': getattr(sample, 'paused', None), 'stream': int(camera.stream_type),
            'client': id(client) if client is not None else None, 'connected': connected,
            'switching': camera._switching, 'connection_generation': self.connection_generation,
            'pip_generation': core.pip_stream.generation,
            'client_frame_id': getattr(client, 'frame_id', None),
            'sof': getattr(client, 'timestamp_sof', None), 'eof': getattr(client, 'timestamp_eof', None),
            'buffer': {name: getattr(frame, name, None) for name in
                       ('frame_id', 'idx', 'fd', 'width', 'height', 'stride', 'uv_offset')},
            'sources': {name: {'seen': sm.seen[name], 'valid': sm.valid[name], 'stamp': sm.logMonoTime[name],
                               **({'frame_id': sm[name].frameId, 'sof': sm[name].timestampSof, 'eof': sm[name].timestampEof}
                                  if name.endswith('EncodeIdx') and sm.seen[name] else {})}
                        for name in STAMPS},
            'observation_ns': time.monotonic_ns() - began}

  def report(self):
    events, count = list(self.events), self.count
    stages = {}
    for event in events:
      values = stages.setdefault(event['stage'], {key: Distribution() for key in
                                ('wall_ms', 'cpu_ms', 'exclusive_wall_ms', 'exclusive_cpu_ms')})
      for key, distribution in values.items():
        value = event.get(key.replace('_ms', '_ns'))
        distribution.add(value / 1e6 if value is not None else None)
    return {'schemaVersion': 1, 'kind': 'replay-render-trace', 'compositor_fps': 20,
            'capabilities': self.capabilities, 'configuration': self.configuration,
            'max_events': MAX_EVENTS, 'overwritten_events': count - len(events),
            'lifetime_draw_outcomes': dict(self.outcomes),
            'retained_window_stages': {stage: {key: value.summary() for key, value in values.items()}
                                       for stage, values in stages.items()}, 'events': events}


@contextmanager
def instrument(render, trace, *, flush=None):
  """Patch only this diagnostic worker; restore callbacks even when a frame fails."""
  patched = set()
  trace.capabilities = {name: hasattr(render.Compositor, method) for name, method in
                        (('early_rejection_reason', '_draw_rejection'), ('preparation_hooks', '_prepare'))}
  with ExitStack() as restore:
    def replace(target, name, value):
      previous = vars(target).get(name)
      owned = name in vars(target)
      setattr(target, name, value)
      restore.callback(setattr, target, name, previous) if owned else restore.callback(delattr, target, name)

    def wrap(target, name, stage, *, camera=False, after=None):
      key = id(target), name
      if key in patched:
        return
      patched.add(key)
      original = getattr(target, name)
      def measured(*args, **kwargs):
        before = trace.snapshot() if camera else None
        with trace.span(stage) as event:
          result = original(*args, **kwargs)
          if after is not None:
            after(event, result, args)
        if camera:
          event.update(before=before, after=trace.snapshot())
          if stage == 'stream_switch' or stage == 'connect_import' and not before['connected'] and event['after']['connected']:
            trace.connection_generation += 1
            event['after']['connection_generation'] = trace.connection_generation
        return result
      replace(target, name, measured)

    def bind_view(event, result, args):
      view = args[0].view
      wrap(type(view), 'render', 'composition')
      wrap(type(view.alert), 'render', 'alerts')
      for name in ('current_speed', 'unified_speed', 'cem_gauge', 'steering_wheel', 'compact_hud', 'compact_sidebar', 'torque_bar'):
        widget = getattr(view, name, None)
        if widget is not None:
          for method in vars(type(widget)):
            if method == 'render' or method.startswith('render_'):
              wrap(type(widget), method, 'hud')

    def bind_core(event, result, args):
      core = trace.core = args[0]
      trace.configuration = {'profile': getattr(getattr(core, 'profile', None), 'value', None),
                             'width': getattr(core, 'width', None), 'height': getattr(core, 'height', None),
                             'gui_target_fps': getattr(core.gui, 'target_fps', None)}
      from openpilot.starpilot.system.android_auto import gpu_nv12
      camera_base = sys.modules[type(core.camera).__module__].CameraView
      for method, stage in (('_render', 'camera'), ('_ensure_connection', 'connect_import'),
                            ('_handle_switch', 'target_acquisition'), ('_complete_switch', 'stream_switch')):
        wrap(camera_base, method, stage, camera=True)
      for target, method, stage in (
        (core.ui, 'update', 'replay_update'), (core.ui.sm, 'update', 'messages'),
        (type(core.ui.replay_clock), 'sample', 'clock_sample'), (type(core.adapter), 'build', 'snapshot'),
        (core.placement, 'maintain', 'placement'), (core.context, 'begin_frame', 'frame_clock'),
        (gpu_nv12, 'compose_rgba', 'rgba_conversion'), (gpu_nv12.Nv12Converter, 'convert', 'nv12_conversion'),
        (type(core.pip_stream), 'poll', 'pip_acquisition'), (type(core.pip), 'render', 'pip'),
        (type(core.monitor), 'render', 'driver_monitor'),
        (core.readback, 'finish', 'readback_map'), (core.readback, 'release', 'readback_release'),
        (core.rl, 'begin_texture_mode', 'texture_begin'), (core.rl, 'end_texture_mode', 'texture_end'),
      ):
        wrap(target, method, stage)
      def phase(name, callback, *args, **kwargs):
        with trace.span('model' if name == 'model' else 'camera_phase'):
          return original_phase(name, callback, *args, **kwargs)
      original_phase = core.gui.measure_frame_phase
      replace(core.gui, 'measure_frame_phase', phase)
      def submitted(event, result, args):
        trace.pending_attempt = trace.local.attempt
        trace.submitted_ns = time.monotonic_ns()
      def ready(event, result, args):
        event['ready'] = result
        if result and trace.submitted_ns is not None:
          event['submit_to_observed_ready_ns'] = time.monotonic_ns() - trace.submitted_ns
          trace.submitted_ns = None
      def released(event, result, args):
        trace.pending_attempt = trace.submitted_ns = None
      wrap(core.readback, 'start', 'readback_submit', after=submitted)
      wrap(core.readback, 'ready', 'readback_poll', after=ready)
      # Record cancellation on seek too, without retaining the borrowed pixel memory.
      original_release = core.readback.release
      def release():
        try:
          return original_release()
        finally:
          released(None, None, None)
      replace(core.readback, 'release', release)

    original_draw, original_finish = render.Compositor.draw, render.Compositor.finish
    def draw(core, *args):
      trace.attempt += 1
      trace.local.attempt = trace.attempt
      trace.local.rejection = None
      before = trace.snapshot()
      try:
        with trace.span('draw') as event:
          accepted = original_draw(core, *args)
          reason = 'accepted' if accepted else trace.local.rejection or (
            'late_camera_not_ready' if trace.capabilities['early_rejection_reason'] else 'unclassified_rejection')
          trace.outcomes[reason] += 1
          event.update(accepted=accepted, reason=reason, captured_ns=args[2], position=args[1], before=before)
          if accepted and trace.loop_now is not None:
            trace.last_draw = max(trace.last_draw + render.FRAME_INTERVAL, trace.loop_now - render.FRAME_INTERVAL)
        event['after'] = trace.snapshot()
        return accepted
      except BaseException:
        trace.outcomes['error'] += 1
        raise
      finally:
        trace.local.attempt = None

    @contextmanager
    def finish(core):
      trace.local.attempt = trace.pending_attempt
      try:
        with trace.span('delivery_scope') as event:
          with original_finish(core) as value:
            event['delivered'] = value is not None
            yield value
      finally:
        trace.local.attempt = None

    def eligibility(event, result, args):
      trace.local.rejection = event['reason'] = result

    def updated(event, result, args):
      trace.await_loop_clock = True
      event['readback_pending'] = trace.core.readback.pending

    def monotonic():
      now = time.monotonic()
      if trace.await_loop_clock:
        trace.await_loop_clock, trace.loop_now = False, now
        with trace.span('scheduler') as event:
          event.update(readback_pending=trace.core.readback.pending,
                       deadline_lateness_ns=round(max(0., now - trace.last_draw - render.FRAME_INTERVAL) * 1e9)
                       if trace.last_draw else None)
      return now

    def sleep(seconds):
      with trace.span('scheduler_sleep') as event:
        event['requested_ns'] = round(seconds * 1e9)
        time.sleep(seconds)
      sample = trace.core.ui.replay_sample if trace.core is not None else None
      if (flush is not None and trace.flush_requested and sample is not None and sample.valid and sample.paused and
          not trace.core.readback.pending):
        trace.flush_requested = False
        flush()

    pending_gc = {}
    def gc_event(phase, info):
      generation = info['generation']
      if phase == 'start':
        pending_gc[generation] = time.monotonic_ns()
      elif generation in pending_gc:
        start = pending_gc.pop(generation)
        trace.record({'id': next(trace.sequence), 'stage': 'gc', 'start_ns': start,
                      'wall_ns': time.monotonic_ns() - start, 'generation': generation,
                      'collected': info['collected'], 'overlaps_other_stages': True})

    wrap(render.Compositor, '_new_view', 'view_init', after=bind_view)
    wrap(render.Compositor, '__init__', 'compositor_init', after=bind_core)
    wrap(render.Compositor, 'update', 'update', after=updated)
    wrap(render.Compositor, '_receive_primary', 'primary_acquisition', camera=True)
    if trace.capabilities['early_rejection_reason']:
      wrap(render.Compositor, '_draw_rejection', 'eligibility', after=eligibility)
    if trace.capabilities['preparation_hooks']:
      wrap(render.Compositor, '_prepare', 'preparation_hooks')
    wrap(render.Compositor, 'reset_epoch', 'epoch_reset')
    replace(render.Compositor, 'draw', draw)
    replace(render.Compositor, 'finish', finish)
    replace(render, 'time', SimpleNamespace(monotonic=monotonic, monotonic_ns=time.monotonic_ns, sleep=sleep))
    from openpilot.starpilot.system.android_auto.hw_encoder import HardwareH264Encoder
    for target, method, stage in ((HardwareH264Encoder, 'encode_nv12', 'encode'),
                                  (render.MediaMux, 'frame', 'mux'), (render.MediaStore, 'publish', 'web_publish'),
                                  (render.ReplayFramePublisher, 'publish', 'native_publish')):
      wrap(target, method, stage)
    gc.callbacks.append(gc_event)
    restore.callback(gc.callbacks.remove, gc_event)
    yield


def main(argv=None):
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('worker_args', nargs=argparse.REMAINDER)
  args = parser.parse_args(argv)
  if args.worker_args[:1] != ['--']:
    parser.error('pass the existing owner-created worker arguments after --')
  from openpilot.starpilot.replay import render
  if render.FRAME_INTERVAL != .05:
    parser.error('this diagnostic is restricted to the existing 20 FPS compositor')
  # Reject a non-owner context before installing any instrumentation or starting the engine.
  worker = argparse.ArgumentParser(add_help=False)
  worker.add_argument('--session-dir', type=Path, required=True)
  context, _ = worker.parse_known_args(args.worker_args[1:])
  render.validate_context(context.session_dir)
  trace = Trace()
  root = Path(render.__file__).resolve().parents[3]
  source = metadata(root)
  for name in ('openpilot/cereal/messaging/__init__.py', 'openpilot/selfdrive/ui/ui_state.py',
               'openpilot/selfdrive/ui/onroad/cameraview.py', 'openpilot/selfdrive/ui/mici/onroad/cameraview.py',
               'openpilot/tools/replay/display_clock.py', 'openpilot/starpilot/system/android_auto/headless_egl.py',
               'openpilot/starpilot/system/android_auto/hw_encoder.py'):
    source['sourceSha256'][name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
  source['replayHashes'] = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in
                          (('render', Path(render.__file__)), ('owner', Path(render.__file__).with_name('owner.py')),
                           ('media', Path(render.__file__).with_name('media.py')), ('harness', Path(__file__)))}
  fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
  previous = sys.argv
  try:
    with os.fdopen(fd, 'w') as output:
      saved = False
      def save(boundary):
        nonlocal saved
        if not saved:
          output.write(json.dumps({**trace.report(), 'source': source, 'worker_args': args.worker_args[1:],
                                   'report_boundary': boundary}, separators=(',', ':'), allow_nan=False))
          output.write('\n')
          output.flush()
          saved = True
      previous_signal = signal.signal(signal.SIGUSR1, lambda *_: setattr(trace, 'flush_requested', True))
      try:
        sys.argv = ['replay-render-diagnostic', *args.worker_args[1:]]
        with instrument(render, trace, flush=lambda: save('paused_checkpoint')):
          render.main()
      finally:
        signal.signal(signal.SIGUSR1, previous_signal)
        save('worker_exit')
  finally:
    sys.argv = previous


if __name__ == '__main__':
  main()
