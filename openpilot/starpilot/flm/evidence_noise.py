"""Conservative learning exclusions recomputed from actual child chronology.

These thresholds label unusable fitting evidence; they are not plant parameters
or safety limits. The controller command and native owners remain unchanged.
"""

from collections import deque
import math

COMMAND_STEP = {'normalized_torque': 0.005, 'pid': 0.005, 'angle': 0.1, 'curvature': 1e-5, 'ford_path_angle': 0.0005}


def _reversals(values, floor):
  previous = 0
  count = 0
  for left, right in zip(values, values[1:], strict=False):
    change = right - left
    if abs(change) < floor:
      continue
    direction = 1 if change > 0 else -1
    count += bool(previous and direction != previous)
    previous = direction
  return count


def noisy_frames(rows, domain, *, max_gap_ns=50_000_000):
  """Return actual source stamps excluded for model wobble or quiet-goal chatter."""
  floor = COMMAND_STEP[domain]
  window = deque()
  bad = {}
  last = 0
  for row in rows:
    stamp = int(row['control_ns'])
    values = dict(row['inputs'])
    goal = float(values['raw_model_curvature']) * float(values['vEgo']) ** 2
    command = float(row.get('actual_command', row.get('selected_command', row.get('requested', float('nan')))))
    if not stamp > last or not all(math.isfinite(value) for value in (goal, command)):
      raise ValueError('noise chronology unavailable')
    if last and stamp - last > max_gap_ns:
      window.clear()
    last = stamp
    window.append((stamp, goal, command))
    while window and stamp - window[0][0] > 1_000_000_000:
      window.popleft()
    if len(window) < 5:
      continue
    goals, commands = [value[1] for value in window], [value[2] for value in window]
    model = _reversals(goals, 0.03) >= 4
    chatter = max(goals) - min(goals) <= 0.03 and _reversals(commands, floor) >= 4
    if model or chatter:
      for source, _, _ in window:
        prior = bad.get(source, (False, False))
        bad[source] = (prior[0] or model, prior[1] or chatter)
  return bad


def reject_noisy_job(payload, *, retain_centre_chatter=False):
  from openpilot.starpilot.flm.controller_replay import unpack_primitive_snapshot

  replay = unpack_primitive_snapshot(payload['replay'])
  domain = payload.get('domain', 'normalized_torque')
  flags = noisy_frames(replay['frames'], domain)
  blocks = payload.get('raw_blocks', payload.get('blocks', ()))
  # Plant calibration blocks need not export full controller replay windows,
  # but retain actual20Hz joined controls/goals. Recompute model noise there
  # as well, keeping each original stamp and resetting across missing samples.
  controls = {}
  for block in blocks:
    for point in block['samples']:
      control = point['control']
      controls[point['control_ns']] = {'control_ns': point['control_ns'], 'inputs': control['replay_inputs'], 'selected_command': control['requested']}
  for stamp, current in noisy_frames(tuple(controls[key] for key in sorted(controls)), domain, max_gap_ns=100_000_000).items():
    prior = flags.get(stamp, (False, False))
    flags[stamp] = (prior[0] or current[0], prior[1] or current[1])
  for block in blocks:
    for point in block['samples']:
      model, chatter = flags.get(point['control_ns'], (False, False))
      if model or chatter and not retain_centre_chatter:
        return 'model_goal_wobble' if model else 'controller_chatter'
  return None
