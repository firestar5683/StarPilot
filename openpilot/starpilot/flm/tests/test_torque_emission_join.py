"""Actual registered CI/CAN and chronological encoder tests, source-only proposal.

Synthetic CarState/public-health fixtures exercise encoding/transport only.
No fitted plant, profile, ReplayValidation or hardware permission is fabricated.
"""

from dataclasses import replace
from types import SimpleNamespace
import copy

import pytest
from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR as TOYOTA
from opendbc.car.honda.values import CAR as HONDA
from opendbc.car.gm.values import CAR as GM, CanBus as GMCanBus
from opendbc.car.gm.radar_interface import RADAR_HEADER_MSG
from opendbc.car.steering_projection import install_observer, inspect_projection, normalized_applied_command
from openpilot.cereal import messaging
from openpilot.cereal.services import SERVICE_LIST
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.flm.fullrate_collector import AppliedEvidence
from openpilot.starpilot.flm.learning_wire import write_applied, read_applied
from openpilot.starpilot.flm.evidence_hooks import begin_applied_frame, applied_snapshot
from openpilot.starpilot.flm.torque_emission_replay import EmissionHistory, EncoderBranch, delivered
from openpilot.starpilot.flm.runtime_adapter_registry import (
  current_authority,
  read_source,
  selected_descriptor,
  selected_identity,
  baseline_values,
  baseline_revision,
)
from openpilot.selfdrive.controls.lib.latcontrol_pid import LatControlPID
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque

BASE = 10_000_000_000


def interface(platform, firmware=()):
  factory = interfaces[platform]
  fingerprint = gen_empty_fingerprint()
  if platform == GM.GMC_ACADIA:
    # Explicit registered ASCM radar layout; state below remains a codec fixture.
    fingerprint[GMCanBus.OBSTACLE][RADAR_HEADER_MSG] = 8
  cp = factory.get_params(platform, fingerprint, list(firmware), False, False, False)
  ci = factory(cp)
  ci.update([])
  cs = structs.CarState(vEgo=18.0, vEgoRaw=18.0, canValid=True, gearShifter=structs.CarState.GearShifter.drive)
  cs.cruiseState.available = cs.cruiseState.enabled = True
  ci.CS.out = cs.as_reader()
  assert install_observer(ci)
  return ci


def cc(torque):
  message = structs.CarControl(enabled=True, latActive=True)
  message.actuators.torque = torque
  return message.as_reader()


def source(ci, tmp_path, requested, control_ns):
  cp = ci.CP.as_reader()
  lac = LatControlPID(cp, ci, 0.01) if cp.lateralTuning.which() == 'pid' else LatControlTorque(cp, ci, 0.01)
  descriptor = selected_descriptor(cp, ci, lac)
  actual_source = read_source(
    cp, SimpleNamespace(get_param_path=lambda key: str(tmp_path / key)), now_ns=control_ns, calibration=(0.0, 0.0, 0.0), vehicle_session="fixture-drive"
  )
  return SimpleNamespace(
    identity=selected_identity(descriptor, actual_source.source_epoch),
    source_epoch=actual_source.source_epoch,
    baseline_revision=baseline_revision(descriptor, baseline_values(lac)),
    requested=requested,
    control_ns=control_ns,
    native_required=False,
    native_allowed=False,
    native_observed_ns=0,
    native_expires_ns=0,
    native_identity='',
  )


def actual_public_health(cp, now_ns):
  with OpenpilotPrefix():
    sm = messaging.SubMaster(['pandaStates'])
    period_ns = round(1e9 / SERVICE_LIST['pandaStates'].frequency)
    for stamp in (now_ns - period_ns, now_ns):
      packet = messaging.new_message('pandaStates', len(cp.safetyConfigs), valid=True, logMonoTime=stamp)
      for panda, config in zip(packet.pandaStates, cp.safetyConfigs, strict=True):
        panda.safetyModel = config.safetyModel
        panda.safetyParam = config.safetyParam
        panda.alternativeExperience = cp.alternativeExperience
        panda.controlsAllowed = str(config.safetyModel) not in ('silent', 'noOutput')
      sm.update_msgs(stamp / 1e9, [packet.as_reader()])
    assert sm.freq_ok['pandaStates']
    allowed, _, _ = current_authority(sm, cp, now_ns=now_ns, required=False)
    assert allowed
    return allowed


def emitted(ci, command, tmp_path, *, control_ns=None):
  frame = ci.CC.frame
  stamp = BASE + frame * 10_000_000
  output, packets = ci.apply(command, stamp)
  witness = ci.CC.learning_projection
  if witness is None:
    return None
  assert (witness.can_address, witness.can_data, witness.can_bus) in packets
  assert inspect_projection(ci, command, output, witness) is True
  control_ns = stamp if control_ns is None else control_ns
  authority = actual_public_health(ci.CP, stamp)
  evidence = AppliedEvidence(
    control_ns, stamp - 1, stamp, 'normalized_torque', float(output.torque), True, True, False, False, False, authority, witness, ci.CC.frame, stamp
  )
  return source(ci, tmp_path, float(command.actuators.torque), control_ns), evidence


def settle(ci, command, ticks=280):
  for _ in range(ticks):
    ci.apply(command, BASE + ci.CC.frame * 10_000_000)


@pytest.mark.parametrize('platform', (TOYOTA.TOYOTA_COROLLA_TSS2, HONDA.HONDA_CIVIC))
def test_actual_quantized_wire_roundtrip_preserves_reported_and_delivered(platform, tmp_path):
  ci = interface(platform)
  settle(ci, cc(0.01))
  maximum = ci.CC.learning_projection.effective_max
  command = cc(1.6 / maximum)
  settle(ci, command)
  control, output = emitted(ci, command, tmp_path)
  history = EmissionHistory(ci.CP, identity=control.identity, baseline_revision=control.baseline_revision)
  assert history.record_carrier(output) and history.record(control, output)
  history.verify(control, output)
  assert delivered(output) == normalized_applied_command(output.projection)
  assert delivered(output) != control.requested  # actual quantization, no epsilon allowance
  event = messaging.new_message('starpilotCarState', valid=True, logMonoTime=output.carrier_observed_ns)
  write_applied(event.starpilotCarState, output)
  assert read_applied(event.as_reader()) == output
  if platform == HONDA.HONDA_CIVIC:
    assert delivered(output) != output.applied  # inverse lookup/sign, not reported input
  changed = replace(output, projection=output.projection._replace(final_raw=output.projection.final_raw + 1))
  with pytest.raises(ValueError):
    history.verify(control, changed)


def test_candidate_keeps_own_previous_raw_and_refuses_integer_rate_cut(tmp_path):
  ci = interface(TOYOTA.TOYOTA_COROLLA_TSS2)
  command = cc(0.1)
  settle(ci, command)
  first, output = emitted(ci, command, tmp_path)
  history = EmissionHistory(ci.CP)
  assert history.record_carrier(output) and history.record(first, output)
  event = history.event(first.control_ns)
  branch = EncoderBranch()
  branch.step(event, first.requested)
  assert branch.previous == output.projection.final_raw
  next_control, next_output = emitted(ci, command, tmp_path)
  assert history.record_carrier(next_output) and history.record(next_control, next_output)
  next_event = history.event(next_control.control_ns)
  # The branch state is authoritative, not next_event's recorded prior torque.
  branch.previous -= dict(next_event.witness.limits)['STEER_DELTA_UP'] + 1
  assert branch.previous > 0  # Exercise the upward same-sign rate limit, not sign reversal.
  with pytest.raises(ValueError):
    branch.step(next_event, next_control.requested)


def test_missing_constant_emission_is_not_disguised_as_hold(tmp_path):
  ci = interface(TOYOTA.TOYOTA_COROLLA_TSS2)
  command = cc(0.01)
  settle(ci, command)
  history = EmissionHistory(ci.CP)
  sources = []
  for _ in range(4):
    control, output = emitted(ci, command, tmp_path)
    assert history.record_carrier(output) and history.record(control, output)
    sources.append((control, output))
  window = ((sources[0][0].control_ns, sources[-1][0].control_ns),)
  snapshot = history.snapshot(window)
  assert len({row['witness']['final_raw'] for row in snapshot['events']}) == 1
  restored = EmissionHistory(ci.CP)
  restored.load(snapshot, window)
  missing = copy.deepcopy(snapshot)
  missing['events'] = missing['events'][:1] + missing['events'][2:]
  with pytest.raises(ValueError, match='carrier points to missing'):
    EmissionHistory(ci.CP).load(missing, window)


def test_real_hold_advances_only_carrier_metadata(tmp_path):
  ci = interface(GM.GMC_ACADIA)
  command = cc(0.01)
  settle(ci, command)
  output = None
  for _ in range(5):
    candidate = emitted(ci, command, tmp_path)
    if candidate is not None:
      output = candidate[1]
      break
  assert output is not None
  owner = SimpleNamespace(
    CP=ci.CP,
    CI=ci,
    learning_applied_evidence=output,
    sm=SimpleNamespace(
      valid={'carControl': True, 'pandaStates': True},
      alive={'carControl': True, 'pandaStates': True},
      seen={'carControl': True, 'pandaStates': True},
      logMonoTime={'carControl': output.control_ns},
    ),
  )
  begin_applied_frame(owner)
  stamp = BASE + ci.CC.frame * 10_000_000
  actuators, _ = ci.apply(command, stamp)
  assert ci.CC.learning_projection is None
  held = applied_snapshot(owner, command, ci.CS.out, actuators, apply_ns=stamp, state_ns=stamp - 1)
  assert held is not None and held.carrier_frame == ci.CC.frame
  assert held.carrier_observed_ns == stamp
  assert replace(held, carrier_frame=output.carrier_frame, carrier_observed_ns=output.carrier_observed_ns) == output
  assert held.apply_ns == output.apply_ns and held.control_ns == output.control_ns and held.projection is output.projection


def test_civic_candidate_filter_matches_original_update_without_borrowing_future_state(tmp_path):
  from opendbc.car.honda.modified_civic_steering import ModifiedCivicSteering

  firmware = structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.eps, address=0x18DA30F1, subAddress=0, fwVersion=b'39990-TGG,A020\x00\x00', brand='honda')
  ci = interface(HONDA.HONDA_CIVIC_BOSCH, (firmware,))
  command = cc(0.03)
  settle(ci, command)
  first, output = emitted(ci, command, tmp_path)
  history = EmissionHistory(ci.CP)
  assert history.record_carrier(output) and history.record(first, output)
  event = history.event(first.control_ns)
  branch = EncoderBranch()
  reference = ModifiedCivicSteering()
  reference.torque_lpf, reference.prev_torque_cmd, reference.steering_pressed_filter_s, reference.steering_pressed_robust_prev = event.witness.shape[:4]
  for index in range(8):
    if index:
      control, output = emitted(ci, command, tmp_path)
      assert history.record_carrier(output) and history.record(control, output)
      event = history.event(control.control_ns)
    request = float(cc(0.029).actuators.torque)
    branch.step(event, request)
    expected = reference.update(cc(request), ci.CS)
    assert branch.previous == expected
    assert branch.civic == (reference.torque_lpf, reference.prev_torque_cmd, reference.steering_pressed_filter_s, reference.steering_pressed_robust_prev)
  assert branch.civic != tuple(event.witness.shape[:4])


def test_sampler_observer_copies_original_stamp_and_cannot_change_packet(monkeypatch):
  from openpilot.selfdrive.pandad import pandad_api_impl as sampler

  monkeypatch.setattr(sampler.time, 'monotonic', lambda: 12.5)
  frames = [(0x123, b'\x01\x02', 0)]
  original = sampler.can_list_to_can_capnp(frames, msgtype='sendcan')
  observed = []
  same = sampler.can_list_to_can_capnp(frames, msgtype='sendcan', source_observer=observed.append)
  assert same == original and observed == [12_500_000_000]

  def fail(stamp):
    raise RuntimeError('optional observation')

  assert sampler.can_list_to_can_capnp(frames, msgtype='sendcan', source_observer=fail) == original
