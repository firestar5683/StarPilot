"""Passive local command-response identification, independent of controller tables."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PhysicalRow:
  block_id: str
  command_ns: int
  response_ns: int
  command: float
  physical_response: float
  context: str
  direction: str
  healthy: bool
  overridden: bool
  saturated: bool


@dataclass(frozen=True)
class PhysicalModel:
  identity: str
  context: str
  domain: str
  lag_ns: int
  slope: float
  intercept: float
  command_low: float
  command_high: float
  train_blocks: tuple[str, ...]
  heldout_blocks: tuple[str, ...]
  heldout_rmse: float

  def inverse(self, response):
    if not math.isfinite(response):
      return None
    command = (response - self.intercept) / self.slope
    return command if self.command_low <= command <= self.command_high else None


def fit_physical(identity, domain, context, rows, *, lag_ns, min_excitation, max_rmse, now_ns, history_ns=600_000_000_000):
  """Rows must contain independently measured yaw/angle, never desired trajectory."""
  if (len(identity) != 64 or not domain or not context or type(lag_ns) is not int or
      not 0 <= lag_ns <= 500_000_000 or type(now_ns) is not int or now_ns <= 0 or
      type(history_ns) is not int or not 0 < history_ns <= 600_000_000_000 or
      not math.isfinite(min_excitation) or not math.isfinite(max_rmse) or min_excitation <= 0 or max_rmse <= 0):
    return None
  ids = tuple(dict.fromkeys(row.block_id for row in rows))
  if len(ids) < 8 or len(ids) > 24:
    return None
  if any(not 40 <= sum(row.block_id == block for row in rows) <= 240 or
         len({row.direction for row in rows if row.block_id == block}) != 1 for block in ids):
    return None
  split = len(ids) // 2
  train_ids, heldout_ids = ids[:split], ids[split:]
  previous = 0
  for row in rows:
    if (not row.healthy or row.overridden or row.saturated or row.context != context or
        row.direction not in ('left', 'right') or
        type(row.command_ns) is not int or type(row.response_ns) is not int or
        not 0 < row.command_ns <= row.response_ns <= now_ns or row.command_ns < now_ns - history_ns or not math.isfinite(row.command) or
        not math.isfinite(row.physical_response) or row.command_ns <= previous or
        not 0 <= row.response_ns - lag_ns - row.command_ns <= 30_000_000):
      return None
    previous = row.command_ns
  train = [row for row in rows if row.block_id in train_ids]
  heldout = [row for row in rows if row.block_id in heldout_ids]
  for group in (train, heldout):
    if any(len({row.block_id for row in group if row.direction == direction}) < 2 for direction in ('left', 'right')):
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
    group = [row for row in heldout if row.block_id == block]
    if len(group) < 40 or any(not low <= row.command <= high for row in group):
      return None
    error = math.sqrt(sum((row.physical_response - (slope * row.command + intercept)) ** 2 for row in group) / len(group))
    if error > max_rmse:
      return None
    errors.append(error)
  return PhysicalModel(identity, context, domain, lag_ns, slope, intercept, low, high,
                       train_ids, heldout_ids, max(errors))
