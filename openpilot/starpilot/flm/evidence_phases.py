"""Whole-block causal phase selection in the optional fitter process."""


def stage_blocks(raw, split, calibration_response_end_ns):
  """Keep original rows and clocks; quarantine whole boundary maneuvers.

  Response lag can put early commands of the next maneuver before the end of
  calibration responses. Such a block is retained in the raw replay recording,
  but cannot become stage training or heldout evidence. Never slice its rows.
  """
  admitted, boundary = [], []
  for block in raw[split:]:
    if not block['samples']:
      raise ValueError('empty phase block')
    support = tuple((point['control_ns'], point['apply_ns'], point['mono_ns']) for point in block['samples'])
    if any(not 0 < command <= applied <= response for command, applied, response in support):
      raise ValueError('phase source chronology')
    if min(command for command, _, _ in support) <= calibration_response_end_ns:
      boundary.append(block['block_id'])
    else:
      admitted.append(block)
  return tuple(admitted), tuple(boundary)
