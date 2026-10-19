"""Independent response fit over whole physical episodes, never sign-sliced wiggles."""
import math

from openpilot.starpilot.flm.physical_response import PhysicalModel


def fit_event_physical(identity, context, rows, *, lag_ns, now_ns, min_excitation=.05, max_rmse=.05):
  """Event-v2 only: mixed-direction episodes retain one independent block ID.

  Same measured response, bounded latency, excitation, train/heldout split,
  physical envelope and per-heldout-episode error gates as legacy fit_physical.
  Direction coverage counts whole independent episodes, never separate halves.
  Caller must first recompute source/native/actual CAN provenance in the child.
  """
  if (type(identity) is not str or len(identity) != 64 or type(context) is not str or not context or
      type(lag_ns) is not int or not 0 <= lag_ns <= 500_000_000 or
      type(now_ns) is not int or now_ns <= 0 or
      any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0 for value in (min_excitation, max_rmse))):
    return None
  ids = tuple(dict.fromkeys(row.block_id for row in rows))
  if not 8 <= len(ids) <= 24 or any(not 40 <= sum(row.block_id == block for row in rows) <= 240 for block in ids):
    return None
  previous = 0
  for row in rows:
    if (not row.healthy or row.overridden or row.saturated or row.context != context or
        row.direction not in ('left', 'right') or row.direction != ('left' if row.command > 0 else 'right') or
        type(row.command_ns) is not int or type(row.response_ns) is not int or
        not 0 < row.command_ns <= row.response_ns <= now_ns or row.command_ns < now_ns - 600_000_000_000 or
        not math.isfinite(row.command) or not math.isfinite(row.physical_response) or row.command_ns <= previous or
        not 0 <= row.response_ns - lag_ns - row.command_ns <= 30_000_000):
      return None
    previous = row.command_ns
  split = len(ids) // 2
  train_ids, heldout_ids = ids[:split], ids[split:]
  train = tuple(row for row in rows if row.block_id in train_ids)
  heldout = tuple(row for row in rows if row.block_id in heldout_ids)
  # A sign must have substantive measured support in at least two independent
  # episodes on BOTH sides of the chronological split. One turn's zero-crossing
  # never creates another independent observation or another heldout ID.
  for group in (train, heldout):
    for direction in ('left', 'right'):
      selected = tuple(row for row in group if (row.command > 0 if direction == 'left' else row.command < 0))
      supporting = {row.block_id for row in selected}
      if len(selected) < 80:
        return None
      if sum(sum(row.block_id == block for row in selected) >= 20 for block in supporting) < 2:
        return None
  mean_x = sum(row.command for row in train) / len(train)
  mean_y = sum(row.physical_response for row in train) / len(train)
  variance = sum((row.command - mean_x) ** 2 for row in train) / len(train)
  if variance < min_excitation ** 2:
    return None
  slope = sum((row.command - mean_x) * (row.physical_response - mean_y) for row in train) / (len(train) * variance)
  if not math.isfinite(slope) or slope <= 0:
    return None
  intercept = mean_y - slope * mean_x
  low, high = min(row.command for row in train), max(row.command for row in train)
  errors = []
  for block in heldout_ids:
    group = tuple(row for row in heldout if row.block_id == block)
    if any(not low <= row.command <= high for row in group):
      return None
    error = math.sqrt(sum((row.physical_response - (slope * row.command + intercept)) ** 2 for row in group) / len(group))
    if error > max_rmse:
      return None
    errors.append(error)
  return PhysicalModel(identity, context, 'normalized_torque', lag_ns, slope, intercept, low, high,
                       train_ids, heldout_ids, max(errors))
