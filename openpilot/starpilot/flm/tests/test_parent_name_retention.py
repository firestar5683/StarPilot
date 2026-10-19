"""Actual wire/parent retention only: no fit, admission, or road qualification."""
import struct

from opendbc.car.car_helpers import interfaces
from opendbc.car.gm.values import CAR
from openpilot.cereal import messaging
from openpilot.starpilot.flm.controller_replay import (
  ControllerReplay, MAX_REPLAY_FRAMES, SelectedControllerFactory, capture_snapshot,
)
from openpilot.starpilot.flm.fullrate_collector import ControlEvidence
from openpilot.starpilot.flm.learner_factory import _frame
from openpilot.starpilot.flm.learning_wire import read_control, write_control
from openpilot.starpilot.flm.torque_adapter import Objective


def test_actual_wire_parent_recorder_retains_shared_keys_and_exact_values():
  cp = interfaces[CAR.CHEVROLET_VOLT_ASCM].get_non_essential_params(CAR.CHEVROLET_VOLT_ASCM)
  factory = SelectedControllerFactory(cp, 'starpilot')
  engine = ControllerReplay(factory, Objective('feedforward', 'high', 'steady'))
  first_ns = 10_000_000_000
  engine.checkpoint(first_ns, capture_snapshot(engine.actual, engine.vm))
  assert engine.records.maxlen == MAX_REPLAY_FRAMES == 60_000
  stage = (
    ('selected_command', .125), ('effective_factor', float(cp.lateralTuning.torque.latAccelFactor)),
    ('offset', float(cp.lateralTuning.torque.latAccelOffset)), ('friction', float(cp.lateralTuning.torque.friction)),
    ('pid_pos_limit', 1.), ('pid_neg_limit', -1.), ('actual_delta_ff', 0.), ('actual_delta_threshold', 0.),
    ('setpoint', .4),
  )
  for tick in range(80):
    stamp = first_ns + tick * 10_000_000
    inputs = (('control_frame', float(tick + 1)), ('roll', 0.0), ('desired_curvature', .001), ('vEgo', 20.0),
              ('signed_zero', -0.0), ('flag', False), ('label', 'unchanged'))
    evidence = ControlEvidence(
      identity='1' * 64, generation=0, control_ns=stamp, state_ns=stamp,
      domain='normalized_torque', stage_revision='retention-only', response_revision='retention-only',
      requested=.125, features=(0.,), baseline_prediction=.125, enabled=True, manual=False, active=True,
      valid=True, override=False, fault=False, saturated=False, limited=False, model_wobble=False,
      controller_chatter=False, stage_schema_revision='torque-selected-stage-snapshot-v1', stage_values=stage,
      controller_mode='starpilot', policy='retention-only', controller_revision='retention-only', replay_inputs=inputs,
    )
    event = messaging.new_message('starpilotLateralState', valid=True, logMonoTime=stamp)
    write_control(event.starpilotLateralState, evidence)
    decoded = read_control(messaging.log_from_bytes(event.to_bytes()))
    assert decoded == evidence
    point = _frame(decoded)
    assert point.inputs is decoded.replay_inputs
    assert engine.record_actual_frame(point)
  assert not engine.failed and len(engine.records) == 80
  first, last = engine.records[0], engine.records[-1]
  assert first.frame_sequence == 1 and last.frame_sequence == 80
  assert first.control_ns == first_ns and last.control_ns == first_ns + 790_000_000
  assert all(a[0] is b[0] for a, b in zip(first.inputs, last.inputs, strict=True))
  assert all(struct.pack('!d', dict(frame.inputs)['signed_zero']) == struct.pack('!d', -0.0) for frame in engine.records)
  assert all(type(dict(frame.inputs)['flag']) is bool and dict(frame.inputs)['flag'] is False for frame in engine.records)
  assert all(dict(frame.inputs)['label'] == 'unchanged' for frame in engine.records)
  # Key sharing cannot bypass the parent's unchanged sequence guard.
  assert not engine.record_actual_frame(last)
  assert engine.failed and len(engine.records) == 80
