"""Composed automatic fit application; synthetic evidence, actual owners and wire."""

from contextlib import contextmanager
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import struct
import unittest
from unittest import mock

from opendbc.car.car_helpers import interfaces
from opendbc.car.gm.values import CAR as GM
from opendbc.car.hyundai.values import CAR as HKG
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.starpilot.flm.automatic import identity_digest
from openpilot.starpilot.flm.learning_producer import AutomaticLearningProducer
from openpilot.starpilot.flm.learning_source import AutomaticLearningConsumer, MAX_AGE_NS, RESET_KEY, SERVICE
from openpilot.starpilot.flm.tests import test_automatic as evidence
from openpilot.starpilot.lateral.controller_selection import ControllerMode, DOCUMENT_KEY as CONTROLLER_KEY, policy_for, replace_mode
from openpilot.starpilot.lateral.learning_preferences import KEY as PREFERENCE_KEY, replace_preference
from openpilot.starpilot.lateral.tests.test_lane_runtime import feed, publish_corolla_params
from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY as TORQUE_KEY, replace_field, serialize_document

NOW = 400_000_000_000


def float32(value):
  """The controller's CarParams torque fields are Float32, not Python doubles."""
  return struct.unpack('<f', struct.pack('<f', value))[0]


class AbsentCollection:
  """Only exercise the real Params/identity refresh; no fabricated pose admission."""
  def all_checks(self, _services):
    return False


class JoinedLearning:
  def __init__(self, test, controls):
    self.test, self.controls = test, controls
    self.now, self.tick = NOW, 0
    self.producer = self.new_producer()
    self.last_publication = None
    self.wire_readers = []

  def new_producer(self):
    producer = AutomaticLearningProducer(self.controls.CP, self.controls.params)
    with mock.patch('openpilot.starpilot.flm.learning_producer.time.monotonic_ns', return_value=self.now), \
         mock.patch('openpilot.starpilot.flm.learning_producer.time.clock_gettime_ns', return_value=self.now):
      producer.update(AbsentCollection(), None)
    self.test.assertEqual(producer.optional_errors, 0)
    return producer

  def fit(self, multiplier=1.05):
    identity = self.producer.identity
    self.test.assertIsNotNone(identity)
    factor = self.controls.CP.lateralTuning.torque.latAccelFactor * multiplier
    # Reuse the independently timed, direction/speed-balanced physical evidence
    # fixture. Bind it to the real current factory identity, not a fabricated fit.
    windows = []
    for window in evidence.windows():
      points = tuple(replace(point, lateral_accel=factor * point.applied_torque +
                             math.copysign(.02, point.applied_torque)) for point in window.response)
      rows = tuple(replace(row, actual_la=point.lateral_accel, desired_la=point.lateral_accel)
                   for row, point in zip(window.controls, points, strict=True))
      windows.append(replace(window, identity_sha256=identity_digest(identity), controls=rows, response=points))
    self.producer.windows.extend(windows)
    self.producer.block = len(windows)
    self.producer.evaluate(self.now)
    self.test.assertIsNotNone(self.producer.result)
    return self.producer.result

  def step(self, *, publish=True, change=None, **health):
    controls = self.controls
    feed(controls, self.now, self.tick, **health)
    if publish and self.tick % 25 == 0:
      with mock.patch('openpilot.starpilot.flm.learning_producer.time.monotonic_ns', return_value=self.now):
        event = self.producer.get_msg()
      self.test.assertIsNotNone(event)
      self.test.assertTrue(event.valid, 'The real producer must mark its usable wire valid')
      if change is not None:
        change(event.autoSteeringLearning)
      reader = messaging.log_from_bytes(event.to_bytes())
      self.wire_readers.append(reader)
      controls.sm.update_msgs(self.now / 1e9, [reader])
      self.last_publication = self.now
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=self.now):
      command, _ = controls.state_control()
    self.now += 10_000_000
    self.tick += 1
    return command

  def drive(self, ticks, **kwargs):
    for _ in range(ticks):
      command = self.step(**kwargs)
    return command


@contextmanager
def joined(test, *, native_ack=False):
  with OpenpilotPrefix(), mock.patch.dict(os.environ, {'REPLAY': '1', 'TORQUE_REPLAY_RUNTIME': '0',
                                                       'AOL_REPLAY_RUNTIME': '1' if native_ack else '0', 'LANE_CENTERING_REPLAY_RUNTIME': '0',
                                                       'SIMULATION': '0'}), \
       mock.patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
    params = Params()
    cp = publish_corolla_params(params)
    params.put(CONTROLLER_KEY, json.loads(replace_mode(None, cp, ControllerMode.STANDARD)), block=True)
    params.put(PREFERENCE_KEY, replace_preference(None, cp, True), block=True)
    controls = Controls()
    test.assertTrue(controls.automatic_learning.supported)
    test.assertTrue(controls.torque_learning_allowed)
    test.assertIsNone(controls.torque_host)
    yield JoinedLearning(test, controls)


class TestAutomaticLearningIntegration(unittest.TestCase):
  def test_produced_fit_reaches_actual_controls_once_without_manual_document(self):
    with joined(self) as run:
      controls = run.controls
      before_cp = controls.CP.as_builder().to_bytes()
      basis = controls.CP.lateralTuning.torque
      offset, friction = basis.latAccelOffset, basis.friction
      command = run.drive(50)
      self.assertTrue(command.latActive)
      self.assertIsNone(controls.torque_host, 'Collecting alone must not instantiate an application owner')
      result = run.fit()
      self.assertEqual(result.status, 'qualified_fit')
      native_factor = controls.LaC.torque_params.latAccelFactor
      command = run.drive(100)
      self.assertTrue(controls.sm.all_checks([SERVICE]))
      self.assertFalse(controls.sm.simulation, 'Exercise actual frequency tracking, not simulation relaxation')
      host = controls.torque_host
      self.assertIsNotNone(host)
      self.assertIs(host.applied_controller, controls.LaC)
      self.assertGreater(controls.LaC.torque_params.latAccelFactor, native_factor)
      self.assertEqual(controls.LaC.torque_params.latAccelFactor, float32(dict(result.candidate)['latAccelFactor']))
      self.assertEqual(controls.LaC.torque_params.latAccelOffset, offset)
      self.assertEqual(controls.LaC.torque_params.friction, friction)
      self.assertEqual(controls.CP.as_builder().to_bytes(), before_cp)
      self.assertIsNone(controls.params.get(TORQUE_KEY))
      self.assertTrue(command.latActive)
      run.drive(30)
      self.assertIs(controls.torque_host, host, 'One controller parameter writer must survive subsequent publications')

  def test_actual_application_expires_and_reset_restart_or_manual_choice_falls_back(self):
    for reason in ('stale', 'restart', 'off', 'corrupt', 'reset', 'manual'):
      with self.subTest(reason=reason), joined(self) as run:
        controls = run.controls
        self.assertEqual(run.fit().status, 'qualified_fit')
        run.drive(100)
        host = controls.torque_host
        self.assertIsNotNone(host)
        base = controls.CP.lateralTuning.torque.latAccelFactor
        self.assertGreater(controls.LaC.torque_params.latAccelFactor, base)
        if reason == 'restart':
          previous_session = run.producer.session
          run.producer = run.new_producer()
          self.assertNotEqual(run.producer.session, previous_session)
          self.assertIsNone(run.producer.result)
        elif reason == 'off':
          controls.params.put(PREFERENCE_KEY, replace_preference(None, controls.CP, False), block=True)
        elif reason == 'corrupt':
          Path(controls.params.get_param_path(PREFERENCE_KEY)).write_bytes(b'malformed')
        elif reason == 'reset':
          controls.params.put(RESET_KEY, 'a' * 32, block=True)
        elif reason == 'manual':
          basis = controls.CP.lateralTuning.torque
          profile = replace_field({}, str(controls.CP.carFingerprint),
            (basis.latAccelFactor, basis.latAccelOffset, basis.friction), 'factor', 'custom', base * 1.2)
          controls.params.put(TORQUE_KEY, json.loads(serialize_document(profile)), block=True)
        command = run.drive(220, publish=reason != 'stale')
        if reason == 'stale':
          self.assertGreater(run.now - run.last_publication, MAX_AGE_NS)
        self.assertTrue(command.latActive, 'Learning source loss must not manufacture a driving fault')
        self.assertIs(controls.torque_host, host)
        self.assertEqual(controls.LaC.torque_params.latAccelFactor, float32(base * (1.2 if reason == 'manual' else 1.)))
        self.assertEqual(host.selected.source.value, 'user' if reason == 'manual' else host.native_base.source.value)
        if reason in ('reset', 'off', 'corrupt', 'manual'):
          run.producer = run.new_producer()
          self.assertIsNone(run.producer.result, 'Changed saved identity cannot recover an earlier process fit')
        if reason in ('off', 'corrupt', 'manual'):
          self.assertIsNone(run.producer.identity)

  def test_real_controller_bounds_and_authority_are_independent_of_qualified_wire(self):
    with joined(self, native_ack=True) as run:
      controls = run.controls
      before_cp = controls.CP.as_builder().to_bytes()
      self.assertEqual(run.fit().status, 'qualified_fit')
      commands = [run.step() for _ in range(100)]
      self.assertIsNotNone(controls.torque_host)
      self.assertTrue(all(math.isfinite(command.actuators.torque) and
                          abs(command.actuators.torque) <= controls.LaC.steer_max for command in commands))
      for health in ({'native_allowed': False}, {'can_valid': False}, {'can_timeout': True}, {'fault': True},
                     {'active': False, 'enabled': False}):
        command = run.step(**health)
        self.assertFalse(command.latActive)
        self.assertEqual(command.actuators.torque, 0.)
        self.assertEqual(controls.LaC.pid.i, 0.)
      # A qualified sender cannot escape consumer factor or identity admission.
      for field, value in (('latAccelFactor', float('nan')), ('latAccelFactor', 100.), ('acceptancePolicyId', 'unknown')):
        while run.tick % 25:
          run.step()
        command = run.step(change=lambda state, key=field, new=value: setattr(state, key, new))
        self.assertEqual(controls.torque_host.selected, controls.torque_host.native_base)
        self.assertTrue(math.isfinite(command.actuators.torque))
      self.assertEqual(controls.CP.as_builder().to_bytes(), before_cp, 'Automatic fitting must never change native safety configuration')
    for vehicle, mode in ((HKG.HYUNDAI_IONIQ_6, ControllerMode.STARPILOT),
                          (GM.CHEVROLET_SILVERADO, ControllerMode.STANDARD)):
      with self.subTest(vehicle=vehicle), OpenpilotPrefix():
        cp = interfaces[vehicle].get_non_essential_params(vehicle)
        params = Params()
        if policy_for(cp) is not None:
          params.put(CONTROLLER_KEY, json.loads(replace_mode(None, cp, mode)), block=True)
        else:
          self.assertIsNone(params.get(CONTROLLER_KEY))
        params.put(PREFERENCE_KEY, replace_preference(None, cp, True), block=True)
        consumer = AutomaticLearningConsumer(cp, interfaces[vehicle](cp), mode, params)
        self.assertFalse(consumer.supported, 'Saved On cannot qualify a rich or fixed custom conversion')
