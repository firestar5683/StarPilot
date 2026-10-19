"""Whole physical event lineage; storage packet IDs never imply independence."""
import hashlib
import math

from openpilot.starpilot.flm.physical_response import kinematic_accel

from openpilot.starpilot.flm.controller_replay import MAX_FRAME_GAP_NS

GROUPING_REVISION = 'whole-source-window-bundles-v3'


def whole_event_windows(engine):
  events = []
  start = last = neutral = 0
  prior_sign = first_sign = reversals = 0
  mode = None
  previous_window = None
  for frame in engine.records:
    window = next((index for index, (a, b) in enumerate(engine.replay_windows) if a <= frame.control_ns <= b), None)
    if (window is None or window != previous_window or not engine._frame_context(frame) or
        last and not 0 < frame.control_ns - last <= MAX_FRAME_GAP_NS):
      start = neutral = prior_sign = first_sign = reversals = 0
      mode = None
    previous_window, last = window, frame.control_ns
    if window is None or not engine._frame_context(frame):
      continue
    goal = kinematic_accel(frame)
    if goal is None or not math.isfinite(goal):
      raise ValueError('whole episode actual goal missing')
    sign = 1 if goal > .03 else -1 if goal < -.03 else 0
    if abs(goal) >= .25:
      neutral = 0
      if mode != 'large':
        start, mode, first_sign, neutral = frame.control_ns, 'large', sign, 0
      elif sign != first_sign:
        if frame.control_ns - start >= 200_000_000:
          events.append((window, start, frame.control_ns - 1, 'large'))
        start, first_sign = frame.control_ns, sign
      prior_sign = sign
      continue
    if mode == 'large':
      if not sign:
        neutral = neutral or frame.control_ns
        if frame.control_ns - neutral >= 500_000_000:
          if frame.control_ns - start <= 30_000_000_000:
            events.append((window, start, frame.control_ns, 'large'))
          start = neutral = prior_sign = first_sign = reversals = 0
          mode = None
      elif sign != first_sign:
        if 200_000_000 <= frame.control_ns - start <= 30_000_000_000:
          events.append((window, start, frame.control_ns - 1, 'large'))
        start = neutral = prior_sign = first_sign = reversals = 0
        mode = None
      else:
        neutral = 0
      continue
    if sign and prior_sign and sign != prior_sign:
      if mode is None:
        start, mode, first_sign, reversals = frame.control_ns, 'subtle', sign, 0
      else:
        reversals += 1
        if reversals == 2 and sign == first_sign:
          if 200_000_000 <= frame.control_ns - start <= 10_000_000_000:
            events.append((window, start, frame.control_ns - 1, 'subtle'))
          start, first_sign, reversals = frame.control_ns, sign, 0
    if mode == 'subtle' and frame.control_ns - start > 10_000_000_000:
      start = first_sign = reversals = 0
      mode = None
    if sign:
      prior_sign = sign
  return tuple(events)


def regroup_whole_events(engine, raw_packets, objective):
  """Accumulate entire cycles to sample support; never cut a physical event.

  Packet boundaries are intentionally ignored. Bundles are disjoint in source
  time and cannot cross an omitted/rejected original source window. Episode
  kinds remain bound metadata; they do not define independent plant identities.
  Every original source, applied witness and physical timestamp is retained.
  """
  points = {}
  for packet in raw_packets:
    if packet['identity'] != engine.identity:
      raise ValueError('event storage identity')
    for point in packet['samples']:
      key = point['control_ns'], point['apply_ns'], point['mono_ns']
      if key in points:
        raise ValueError('event storage duplicated endpoint')
      points[key] = point
  ordered = sorted(points.values(), key=lambda point: point['mono_ns'])
  blocks = []
  pending, boundaries = [], []
  previous_context = None
  consumed = set()
  for window, start, end, kind in whole_event_windows(engine):
    context = window
    if context != previous_context:
      pending, boundaries = [], []
    previous_context = context
    rows = [point for point in ordered if start <= point['control_ns'] <= end]
    if not rows:
      # Zero measured rows confer zero support or boundary/ID membership.
      # Keep existing support: complete replay from its first through final
      # original boundary still includes every intervening source/native tick.
      continue
    if len(rows) > 240:
      pending, boundaries = [], []
      continue
    if len(pending) + len(rows) > 240:
      # Discard insufficient prior support, rather than manufacture a split.
      pending, boundaries = [], []
    pending.extend(rows)
    boundaries.append((start, end, kind))
    if len(pending) < 40:
      continue
    for point in pending:
      key = point['control_ns'], point['apply_ns'], point['mono_ns']
      if key in consumed:
        raise ValueError('event physical endpoint reused')
      consumed.add(key)
    digest = hashlib.sha256(repr((GROUPING_REVISION, engine.identity, engine.baseline_revision, objective.context_key,
                                  tuple(boundaries))).encode()).hexdigest()
    blocks.append({'identity': engine.identity, 'block_id': 'event-v3:' + digest, 'grouping_revision': GROUPING_REVISION,
                   'cohort': objective.required_cohorts[0], 'stage_revision': 'torque-selected-effect-v2',
                   'response_revision': 'event-independent-physical-v2', 'event_windows': tuple(boundaries), 'samples': tuple(pending)})
    pending, boundaries = [], []
  return tuple(blocks)
