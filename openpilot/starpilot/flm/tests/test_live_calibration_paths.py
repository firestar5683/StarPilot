"""Actual Controls admission and physical observer with live calibration estimates."""
from types import SimpleNamespace
import math
from unittest import mock

import pytest
from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR
from openpilot.cereal import messaging
from openpilot.starpilot.flm.learning_wire import result_message, write_source_receipt
from openpilot.starpilot.flm.runtime_adapter_registry import read_source, physical_observer
from openpilot.starpilot.flm.tests.test_registered_controls_global import controls_for, feed

BASE = 600_000_000_000


def live_frame(controls, tick, generation, *, status='calibrated', blocks=50,
               basis=(0., 0., 0.), healthy=True, publish=None, result=None, validation=None, wire_mutator=None, **health):
  now = BASE + tick * 10_000_000
  original_message = messaging.new_message

  def packet(service, *args, **kwargs):
    event = original_message(service, *args, **kwargs)
    if service == 'carState':
      event.carState.steeringAngleDeg = math.degrees(controls.VM.get_steer_from_curvature(-.0002, 30., 0.))
    if service == 'extrinsicsCalibration':
      event.extrinsicsCalibration.calStatus = status
      event.extrinsicsCalibration.validBlocks = blocks
      event.extrinsicsCalibration.rpyCalib = basis
      event.extrinsicsCalibration.rpyCalibSpread = [0., .001, .001]
    return event

  # Keep the real 4 Hz calibration/source cadence, rather than injecting a
  # second 100 Hz calibration stream that correctly fails frequency checks.
  with mock.patch.object(messaging, 'new_message', side_effect=packet):
    feed(controls, now, tick, speed=30., calibration=basis, **health)
  if publish is None:
    publish = tick % 25 == 0
  if publish:
    source = read_source(controls.CP, controls.params, now_ns=now, calibration=basis,
                         calibration_generation=generation, vehicle_session='current-test-drive')
    event = result_message(result, 'calibration-lifecycle-regression', tick + 1, now, replay_validation=validation)
    event.logMonoTime = now
    write_source_receipt(event, source)
    if wire_mutator is not None:
      wire_mutator(event)
    controls.sm.update_msgs(now / 1e9, [messaging.log_from_bytes(event.to_bytes())])
    controls._test_calibration_source_generation = generation
  if not healthy:
    controls.global_learning.prepare(controls.sm, now_ns=now, active=True, healthy=False)
    return
  with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=now):
    return controls.state_control()


def test_actual_controls_keeps_identity_through_eighty_seconds_of_calibration_refinement():
  cp = interfaces[CAR.TOYOTA_RAV4_TSS2].get_non_essential_params(CAR.TOYOTA_RAV4_TSS2)
  with controls_for(cp, 'standard', True) as controls:
    identity = None
    tune = controls.LaC.torque_params.to_dict()
    for tick in range(8000):
      # Refine the estimate every five seconds, just as in the reported route.
      basis = (0., (tick // 500) * .00002, -(tick // 500) * .00002)
      live_frame(controls, tick, 'a' * 32, basis=basis, publish=tick % 25 == 0)
      runtime = controls.global_learning
      if tick >= 30:
        assert runtime.eligible and runtime.reason != 'qualified', (tick, runtime.reason, vars(runtime._calibration_lifecycle))
        identity = runtime.identity if identity is None else identity
        assert runtime.identity == identity
    assert controls.LaC.torque_params.to_dict() == tune
    assert controls.global_learning.applied_coordinates == (0., 0.)


@pytest.mark.parametrize('initial', [True, False])
def test_actual_core_rejects_old_generation_after_calibration_failure_even_on_other_health_return(initial):
  cp = interfaces[CAR.TOYOTA_RAV4_TSS2].get_non_essential_params(CAR.TOYOTA_RAV4_TSS2)
  with controls_for(cp, 'standard', True) as controls:
    if not initial:
      for tick in range(30):
        live_frame(controls, tick, 'a' * 32)
    start = 0 if initial else 30
    live_frame(controls, start, 'a' * 32, status='recalibrating', blocks=1, healthy=False)
    for tick in range(start + 1, start + 31):
      live_frame(controls, tick, 'a' * 32)
      assert not controls.global_learning.eligible
    for tick in range(start + 31, start + 91):
      live_frame(controls, tick, 'b' * 32)
    assert controls.global_learning.eligible, (controls.global_learning.reason, vars(controls.global_learning._calibration_lifecycle))
    live_frame(controls, start + 91, 'a' * 32, publish=True)
    assert not controls.global_learning.eligible


def test_actual_core_rejects_calibration_block_regression_until_new_generation():
  cp = interfaces[CAR.TOYOTA_RAV4_TSS2].get_non_essential_params(CAR.TOYOTA_RAV4_TSS2)
  with controls_for(cp, 'standard', True) as controls:
    for tick in range(30):
      live_frame(controls, tick, 'a' * 32)
    live_frame(controls, 30, 'a' * 32, blocks=5)
    assert not controls.global_learning.eligible
    for tick in range(31, 201):
      live_frame(controls, tick, 'b' * 32, blocks=5)
    assert controls.global_learning.eligible, (controls.global_learning.reason, vars(controls.global_learning._calibration_lifecycle))


class PhysicalSources:
  def __init__(self, messages, now):
    self.messages = messages
    self.logMonoTime = dict.fromkeys(messages, now)
    self.recv_time = dict.fromkeys(messages, now / 1e9)

  def __getitem__(self, name):
    return self.messages[name]

  def all_checks(self, services):
    return True


def physical_frame(collector, basis, now=BASE):
  motion = messaging.new_message('deviceMotion').deviceMotion
  motion.timestamp = now
  motion.inputsOK = motion.sensorsOK = motion.posenetOK = True
  for name, xyz in (('angularVelocityDevice', (.05, .1, .02)),
                    ('orientationNED', (.01, .02, .03))):
    value = getattr(motion, name)
    value.valid = True
    value.x, value.y, value.z = xyz
  cal = messaging.new_message('extrinsicsCalibration').extrinsicsCalibration
  cal.calStatus = 'calibrated'
  cal.validBlocks = 50
  cal.rpyCalib, cal.rpyCalibSpread = basis, [0., .001, .001]
  cs = SimpleNamespace(steeringPressed=False, brakePressed=False, gasPressed=False,
                       regenBraking=False, buttonEvents=(), canTimeout=False, canValid=True,
                       steerFaultTemporary=False, steerFaultPermanent=False, accFaulted=False)
  sm = PhysicalSources({'deviceMotion': motion, 'extrinsicsCalibration': cal,
                        'carState': cs, 'lateralDelay': SimpleNamespace(lateralDelay=.1),
                        'driverMonitoringState': SimpleNamespace(noResponseForceDecel=False)}, now)
  cp = SimpleNamespace(steerRatio=14., wheelbase=2.9, centerToFront=1.2, mass=2000.)
  with mock.patch('openpilot.starpilot.flm.runtime_adapter_registry.time.monotonic_ns', return_value=now), \
       mock.patch('openpilot.starpilot.flm.runtime_adapter_registry.time.clock_gettime_ns', return_value=now):
    return physical_observer(sm, cp, collector, now)


def test_actual_physical_observer_updates_live_transform_without_splitting_generation():
  command = SimpleNamespace(native_identity='current-native', state_ns=BASE,
    replay_inputs=(('vm.sR', 14.), ('vm.cF', 100000.), ('vm.cR', 100000.),
                   ('vEgo', 30.), ('steeringAngleDeg', 0.)))
  collector = SimpleNamespace(context=('identity', 1, 'normalized_torque', 'stage', 'response', 'a' * 64),
    _calibration_generation='b' * 32, _learning_current_native_allowed=True,
    ready=[(command, SimpleNamespace(native_allowed=True, apply_ns=BASE))],
    adapter=SimpleNamespace(command_domain='normalized_torque'))
  first = physical_frame(collector, (0., 0., 0.))
  next_frame = physical_frame(collector, (0., .002, .001))
  assert first is not None and next_frame is not None
  assert first.calibration == next_frame.calibration
  assert first.yaw_rate != next_frame.yaw_rate
  assert first.roll_rad != next_frame.roll_rad
  assert first.native_allowed and next_frame.native_allowed


def test_new_generation_at_block_regression_is_not_permanently_retired():
  cp = interfaces[CAR.TOYOTA_RAV4_TSS2].get_non_essential_params(CAR.TOYOTA_RAV4_TSS2)
  with controls_for(cp, 'standard', True) as controls:
    for tick in range(30):
      live_frame(controls, tick, 'a' * 32)
    live_frame(controls, 30, 'b' * 32, blocks=5, publish=True)
    # The first reset observation may pause learning, but its new generation
    # must be usable on a subsequent fresh receipt.
    for tick in range(31, 201):
      live_frame(controls, tick, 'b' * 32, blocks=5)
    assert controls.global_learning.eligible, (controls.global_learning.reason, vars(controls.global_learning._calibration_lifecycle))


def test_computed_registered_correction_reaches_controller_with_live_calibration_generation():
  from openpilot.starpilot.flm.tests.test_registered_accepted_profile import computed_registered_fit

  cp = interfaces[CAR.TOYOTA_RAV4_TSS2].get_non_essential_params(CAR.TOYOTA_RAV4_TSS2)
  with controls_for(cp, 'standard', True) as controls:
    for tick in range(30):
      live_frame(controls, tick, 'a' * 32)
    runtime = controls.global_learning
    identity = runtime.identity
    tune = controls.LaC.torque_params.to_dict()
    result, validation = computed_registered_fit(controls.CP, runtime, BASE + 300_000_000)
    assert result.profile is not None and validation is not None
    for tick in range(30, 71):
      live_frame(controls, tick, 'a' * 32, basis=(0., .00002, -.00002),
                 result=result, validation=validation, publish=tick % 25 == 0)
    assert runtime.identity == identity
    assert runtime.reason == 'qualified'
    assert any(value != 0 for value in runtime.applied_coordinates)
    assert controls.LaC.torque_params.to_dict() == tune
