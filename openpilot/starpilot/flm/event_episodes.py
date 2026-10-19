"""Reconstruct whole tracking maneuvers/cycles from actual chronological trace."""
import hashlib
import math

from openpilot.starpilot.flm.physical_response import kinematic_accel

from openpilot.starpilot.flm.controller_replay import MAX_FRAME_GAP_NS


def tracking_episodes(engine, raw_blocks, model, objective):
  """Caller supplies independently verified stage endpoints after model cutoff.

  Large turns end only at a sustained neutral recovery or real sign reversal;
  small oscillations require a complete hysteretic cycle (two reversals), not a
  phase slice. Missing source/native/controller context resets lineage. Counts
  select when to attempt a fit and confer no actuation permission.
  """
  frames = {frame.control_ns: frame for frame in engine.records}
  points = {}
  for block in raw_blocks:
    for point in block['samples']:
      stamp = point['control_ns']
      if stamp in points:
        raise ValueError('event duplicated physical endpoint')
      frame = frames.get(stamp)
      if frame is None or frame.desired_physical_accel is None or not math.isfinite(frame.desired_physical_accel):
        raise ValueError('event exact control-frame physical target absent')
      points[stamp] = (block['block_id'], abs(frame.desired_physical_accel - point['physical']['lateral_accel']))
  windows = tuple(engine.replay_windows)
  episodes = []
  start = last = neutral_start = 0
  first_sign = previous_sign = reversals = 0
  mode = None
  current_window = None
  speeds = []

  def complete(end, kind):
    selected = [(stamp, value) for stamp, value in points.items() if start <= stamp <= end]
    if len(selected) < 4 or not speeds or min(speeds) <= 0 or max(speeds) > 1.15 * min(speeds):
      return
    error = max(value[1] for _, value in selected)
    floor = max(.10, 6 * model.heldout_rmse) if kind == 'large' else max(.015, 3 * model.heldout_rmse)
    if error < floor or not 200_000_000 <= end - start <= 10_000_000_000:
      return
    if kind == 'subtle' and objective.group.startswith(('ff.', 'turn.', 'unwind.', 'angle.')):
      return
    if kind == 'large' and objective.group.startswith(('center', 'deadband.')):
      return
    ids = tuple(dict.fromkeys(value[0] for _, value in sorted(selected)))
    digest = hashlib.sha256(repr((engine.identity, engine.baseline_revision, objective.group,
                                  objective.names, objective.anchor_digest, objective.context_key, start, end, kind)).encode()).hexdigest()
    episodes.append({'id': digest, 'kind': kind, 'start_ns': start, 'end_ns': end, 'block_ids': ids})

  for frame in engine.records:
    window = next((index for index, (a, b) in enumerate(windows) if a <= frame.control_ns <= b), None)
    if (window is None or window != current_window or last and not 0 < frame.control_ns - last <= MAX_FRAME_GAP_NS or
        not engine._frame_context(frame)):
      start = neutral_start = first_sign = previous_sign = reversals = 0
      mode, speeds = None, []
    current_window = window
    last = frame.control_ns
    if window is None or not engine._frame_context(frame):
      continue
    goal = kinematic_accel(frame)
    speed = dict(frame.inputs)['vEgo']
    if goal is None or not all(math.isfinite(value) for value in (goal, speed)):
      raise ValueError('event actual physical target/speed absent')
    sign = 1 if goal > .03 else -1 if goal < -.03 else 0
    if abs(goal) >= .25:
      neutral_start = 0
      if mode != 'large':
        start, mode, first_sign, speeds = frame.control_ns, 'large', sign, []
        neutral_start = 0
      elif sign != first_sign:
        complete(frame.control_ns - 1, 'large')
        start, first_sign, speeds = frame.control_ns, sign, []
      speeds.append(speed)
      previous_sign = sign
      continue
    if mode == 'large':
      speeds.append(speed)
      if not sign:
        neutral_start = neutral_start or frame.control_ns
        if frame.control_ns - neutral_start >= 500_000_000:
          complete(frame.control_ns, 'large')
          start = neutral_start = first_sign = previous_sign = reversals = 0
          mode, speeds = None, []
      elif sign != first_sign:
        complete(frame.control_ns - 1, 'large')
        start = neutral_start = first_sign = previous_sign = reversals = 0
        mode, speeds = None, []
      else:
        neutral_start = 0
      continue
    if sign and previous_sign and sign != previous_sign:
      if mode is None:
        # A real crossing starts a cycle. Window entry is never a new episode.
        start, mode, first_sign, reversals, speeds = frame.control_ns, 'subtle', sign, 0, []
      else:
        reversals += 1
        if reversals == 2 and sign == first_sign:
          complete(frame.control_ns - 1, 'subtle')
          # Adjacent cycles have disjoint source stamps; the common crossing
          # belongs only to the next cycle and cannot duplicate an endpoint.
          start, first_sign, reversals, speeds = frame.control_ns, sign, 0, []
    if mode == 'subtle':
      speeds.append(speed)
      if frame.control_ns - start > 10_000_000_000:
        start = first_sign = reversals = 0
        mode, speeds = None, []
    if sign:
      previous_sign = sign
  return tuple(episodes)
