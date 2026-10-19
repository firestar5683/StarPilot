"""Root-only actual Card/Controls boundaries; no optional failure masks core errors."""
from types import SimpleNamespace
from typing import cast
from unittest import mock

import pytest

from opendbc.car import structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR
from opendbc.car.steering_projection import install_observer
from openpilot.cereal import messaging
from openpilot.selfdrive.car.card import Car
from openpilot.starpilot.vehicle_startup import VehicleStartupOwner
from openpilot.starpilot.gps.publisher import CarGpsPublisher
from openpilot.starpilot.flm.tests.test_registered_controls_global import controls_for, frame

NOW = 600_000_000_000
CORE = ('sendcan', 'carParams', 'carOutput', 'carState', 'controlsState', 'carControl')


class Sink:
  def __init__(self):
    self.rows = []

  def send(self, service, message):
    self.rows.append((service, message if isinstance(message, bytes) else message.to_bytes()))


def card_fixture():
  cp = interfaces[CAR.TOYOTA_RAV4_TSS2].get_non_essential_params(CAR.TOYOTA_RAV4_TSS2)
  ci = interfaces[cp.carFingerprint](cp)
  ci.update([])
  cs = structs.CarState(vEgo=20.0, vEgoRaw=20.0, canValid=True,
                        gearShifter=structs.CarState.GearShifter.drive)
  cs.cruiseState.available = cs.cruiseState.enabled = True
  ci.CS.out = cs.as_reader()
  assert install_observer(ci)
  cc = structs.CarControl(enabled=True, latActive=True)
  cc.actuators.torque = 0.01
  sm = messaging.SubMaster(['carControl', 'pandaStates', 'deviceState'],
                           ignore_avg_freq=['carControl', 'pandaStates', 'deviceState'])
  control = messaging.new_message('carControl', valid=True, logMonoTime=NOW - 1_000_000)
  control.carControl = cc
  pandas = messaging.new_message('pandaStates', len(cp.safetyConfigs), valid=True, logMonoTime=NOW - 1_000_000)
  for panda, config in zip(pandas.pandaStates, cp.safetyConfigs, strict=True):
    panda.safetyModel, panda.safetyParam = config.safetyModel, config.safetyParam
    panda.alternativeExperience = cp.alternativeExperience
    panda.controlsAllowed = str(config.safetyModel) not in ('silent', 'noOutput')
  sm.update_msgs(NOW / 1e9, [control.as_reader(), pandas.as_reader()])
  card = Car.__new__(Car)
  card.CP, card.CI, card.sm = cp, ci, sm
  cast(SimpleNamespace, card).pm = Sink()
  card.vehicle_startup = VehicleStartupOwner()
  card.ci_initialized, card.ioniq6_long_prearmed = True, False
  card.ioniq6_keepalive = None
  card.aol_replay = card.slc_replay = card.curve_replay = card.conditional_replay = False
  card.car_params_published = False
  card.can_rcv_cum_timeout_counter = 0
  cast(SimpleNamespace, card).rk = SimpleNamespace(remaining=0.0)
  card.can_log_mono_time = NOW
  card.last_actuators_output = structs.CarControl.Actuators()
  cast(SimpleNamespace, card).v_cruise_helper = SimpleNamespace(slc_cruise_change=None)
  card.car_gps_publisher = CarGpsPublisher()
  card.learning_stamp_observer = card.record_learning_send_stamp
  card.learning_car_state_source_ns = NOW - 1_000_000
  card.learning_send_mono_ns = card.learning_send_committed_mono_ns = 0
  card.learning_applied_evidence = card.learning_previous_applied_evidence = SimpleNamespace(stale=True)
  return card, cs, cc


def ordinary(rows):
  return [(kind, raw) for kind, raw in rows if kind in CORE]


@pytest.mark.parametrize('hook', ('begin', 'snapshot', 'message', 'observer'))
@pytest.mark.parametrize('error_type', (RuntimeError, ValueError))
def test_actual_card_optional_runtimeerror_keeps_core_publication_and_clears_trust(hook, error_type):
  baseline, cs_a, cc_a = card_fixture()
  # Baseline has no old learning proof; the failing case starts with stale trust.
  baseline.learning_applied_evidence = baseline.learning_previous_applied_evidence = None
  failing, cs_b, cc_b = card_fixture()
  target = {'begin': 'begin_applied_frame', 'snapshot': 'applied_snapshot', 'message': 'applied_message'}

  def broken_message(message, _evidence):
    message.appliedEvidence.version = 1
    message.appliedEvidence.valid = True
    raise error_type('optional metadata failed after partial write')

  with mock.patch('openpilot.selfdrive.car.card.REPLAY', False), \
       mock.patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=NOW), \
       mock.patch('openpilot.selfdrive.car.card.time.monotonic', return_value=NOW / 1e9):
    baseline.controls_update(cs_a, cc_a.as_reader())
    baseline.state_publish(cs_a, None)
    if hook == 'observer':
      failing.learning_stamp_observer = mock.Mock(side_effect=error_type('optional observer'))
      failing.controls_update(cs_b, cc_b.as_reader())
      failing.state_publish(cs_b, None)
    else:
      effect = broken_message if hook == 'message' else error_type('optional metadata')
      with mock.patch('openpilot.starpilot.flm.evidence_hooks.' + ('write_applied' if hook == 'message' else target[hook]), side_effect=effect):
        failing.controls_update(cs_b, cc_b.as_reader())
        failing.state_publish(cs_b, None)
  assert ordinary(failing.pm.rows) == ordinary(baseline.pm.rows)
  assert any(kind == 'sendcan' for kind, _ in failing.pm.rows)
  assert any(kind == 'carState' for kind, _ in failing.pm.rows)
  assert failing.learning_stamp_observer is None
  assert failing.learning_applied_evidence is failing.learning_previous_applied_evidence is None
  assert failing.learning_send_mono_ns == failing.learning_send_committed_mono_ns == 0
  for kind, raw in failing.pm.rows:
    if kind == 'starpilotCarState':
      assert messaging.log_from_bytes(raw).starpilotCarState.appliedEvidence.version == 0


def test_actual_card_real_controller_and_send_errors_propagate():
  for failure in ('apply', 'send'):
    card, cs, cc = card_fixture()
    owner = card.CI if failure == 'apply' else card.pm
    method = 'apply' if failure == 'apply' else 'send'
    with mock.patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=NOW), \
         mock.patch('openpilot.selfdrive.car.card.time.monotonic', return_value=NOW / 1e9), \
         mock.patch.object(owner, method, side_effect=RuntimeError('core failure')):
      with pytest.raises(RuntimeError, match='core failure'):
        card.controls_update(cs, cc.as_reader())


@pytest.mark.parametrize('hook', ('prepare', 'begin_frame', 'finish_frame', 'control_message', 'write_application'))
@pytest.mark.parametrize('error_type', (RuntimeError, ValueError))
def test_actual_controls_optional_runtimeerror_preserves_baseline_and_publication(hook, error_type):
  cp = interfaces[CAR.TOYOTA_RAV4_TSS2].get_non_essential_params(CAR.TOYOTA_RAV4_TSS2)
  with controls_for(cp, 'standard', True) as baseline, controls_for(cp, 'standard', True) as failing:
    baseline._discard_global_learning()
    for tick in range(30):
      frame(baseline, NOW - 300_000_000 + tick * 10_000_000, tick)
      frame(failing, NOW - 300_000_000 + tick * 10_000_000, tick)
    runtime = failing.global_learning
    assert runtime is not None and runtime.eligible
    baseline.pm, failing.pm = Sink(), Sink()
    def broken_writer(message, *_args, **_kwargs):
      if hook == 'control_message':
        message.learningEvidence.version = 1
      else:
        message.learningApplication.version = 1
        message.learningApplication.status = 'applied'
      raise error_type('optional writer failed after partial fields')

    target = (mock.patch.object(runtime, hook, side_effect=error_type('optional'))
              if hook in ('prepare', 'begin_frame', 'finish_frame') else
              mock.patch('openpilot.starpilot.flm.evidence_hooks.write_control' if hook == 'control_message' else
                         'openpilot.selfdrive.controls.controlsd.write_application', side_effect=broken_writer))
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=NOW), \
         mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic', return_value=NOW / 1e9):
      expected, expected_log = frame(baseline, NOW, 30)
      baseline.publish(expected, expected_log)
      with target:
        actual, actual_log = frame(failing, NOW, 30)
        failing.publish(actual, actual_log)
    assert actual.to_dict() == expected.to_dict()
    assert ordinary(failing.pm.rows) == ordinary(baseline.pm.rows)
    assert [kind for kind, _ in failing.pm.rows] == ['controlsState', 'carControl', 'starpilotLateralState']
    assert failing.global_learning is None and runtime.outcome is runtime.frame is None
    assert runtime.applied_coordinates == (0.0, 0.0)
    assert not any(key in failing.LaC.__dict__ for key in
                   ('automatic_flm_stages', 'automatic_flm_centre', 'automatic_flm_observation', 'automatic_flm_adapter'))
    feedback = messaging.log_from_bytes(failing.pm.rows[-1][1]).starpilotLateralState
    assert feedback.learningEvidence.version == feedback.learningApplication.version == 0


def test_actual_controls_real_lac_error_propagates():
  cp = interfaces[CAR.TOYOTA_RAV4_TSS2].get_non_essential_params(CAR.TOYOTA_RAV4_TSS2)
  with controls_for(cp, 'standard', True) as controls:
    with mock.patch.object(controls.LaC, 'update', side_effect=RuntimeError('real LaC failure')):
      with pytest.raises(RuntimeError, match='real LaC failure'):
        frame(controls, NOW, 0)
