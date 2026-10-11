"""Historical CarParams wire stays readable and cannot masquerade as a fit."""

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import capnp

from openpilot.cereal import custom, log, messaging
from openpilot.starpilot.flm.learning_source import SERVICE
from openpilot.starpilot.flm.tests import test_automatic_integration as integration
from tools.ci.custom_schema_contract import describe, validate

# Exact occupied prefix from c2109496a72e85ca702ecef7aff53ff45adcfb8c,
# cereal/custom.capnp. No learner pointer existed in these recordings.
HISTORICAL_CAR_PARAMS = """@0xb526ba661d550a59;
struct StarPilotCarParams @0xaedffd8f31e7b55d {
  alternativeExperience @0 :Int16;
  canUsePedal @1 :Bool;
  canUseSDSU @2 :Bool;
  flags @3 :UInt32;
  isHDA2 @4 :Bool;
  openpilotLongitudinalControlDisabled @5 :Bool;
  safetyConfigs @6 :List(SafetyConfig);
  pcmCruiseSpeed @7 :Bool = true;
  redneckCruiseAvailable @8 :Bool;

  struct SafetyConfig {
    safetyParam @0 :UInt16;
  }
}
"""


# Exact transient c204 payload: incompatible with the older occupied prefix.
TRANSIENT_FLAT_LEARNER = """@0xb526ba661d550a59;
struct AutoSteeringLearning @0xaedffd8f31e7b55d {
  version @0 :UInt16;
  status @1 :Status;
  reason @2 :Text;
  identity @3 :Identity;
  session @4 :Text;
  sequence @5 :UInt64;
  observedMonoTime @6 :UInt64;  # MONOTONIC, separate from Event BOOTTIME.
  validUntilMonoTime @7 :UInt64;
  sourceWindowStartMonoTime @8 :UInt64;
  sourceWindowEndMonoTime @9 :UInt64;
  family @10 :Family;
  latAccelFactor @11 :Float64;
  acceptancePolicyId @12 :Text;
  trainWindows @13 :UInt32;
  heldoutWindows @14 :UInt32;
  trainBaselineLoss @15 :Float64;
  trainCandidateLoss @16 :Float64;
  heldoutBaselineLoss @17 :Float64;
  heldoutCandidateLoss @18 :Float64;

  enum Status { unavailable @0; collecting @1; candidate @2; rejected @3; qualifiedFit @4; }
  enum Family { none @0; linearFactor @1; }
  struct Identity {
    vehicle @0 :Text;
    brand @1 :Text;
    controller @2 :Text;
    policy @3 :Text;
    profile @4 :Text;
    conversionVersion @5 :Text;
    firmwareSha256 @6 :Text;
    basis @7 :List(Float64);
    baselineSha256 @8 :Text;
    preferenceSha256 @9 :Text;
    resetGeneration @10 :Text;
    controllerRevision @11 :Text;
  }
}
"""


@contextmanager
def historical_car_params(source=HISTORICAL_CAR_PARAMS):
  with TemporaryDirectory() as directory:
    path = Path(directory) / 'historical.capnp'
    path.write_text(source)
    yield capnp.SchemaParser().load(str(path))


class TestAutomaticLearningWire(unittest.TestCase):
  def test_historical_car_params_prefix_defaults_and_nested_layout_survive(self):
    with historical_car_params() as historical:
      old_layout = describe(historical, ['StarPilotCarParams'])
      current_layout = describe(custom, ['StarPilotCarParams'])
      self.assertEqual(validate(current_layout, old_layout), [])
      self.assertEqual(set(old_layout['nodes'][str(0xaedffd8f31e7b55d)]['fields']),
                       {str(i) for i in range(9)})
      field = log.Event.schema.fields[SERVICE].proto
      self.assertEqual(field.ordinal.explicit, 108)
      self.assertEqual(field.slot.type.struct.typeId, 0xaedffd8f31e7b55d)
      self.assertEqual(custom.StarPilotCarParams.schema.fields['learning'].proto.ordinal.explicit, 9)
      values = {'alternativeExperience': -123, 'canUsePedal': True, 'canUseSDSU': True,
                'flags': 0xa5a51234, 'isHDA2': True, 'openpilotLongitudinalControlDisabled': True,
                'safetyConfigs': [{'safetyParam': 0x5a5a}, {'safetyParam': 0xffff}],
                'pcmCruiseSpeed': False, 'redneckCruiseAvailable': True}
      old = historical.StarPilotCarParams.new_message(**values)
      with custom.StarPilotCarParams.from_bytes(old.to_bytes()) as current:
        self.assertEqual({key: value for key, value in current.to_dict().items() if key != 'learning'}, values)
        self.assertEqual(current.learning.version, 0)
        self.assertEqual(str(current.learning.status), 'unavailable')
        self.assertEqual(current.learning.session, '')
        self.assertEqual(current.learning.latAccelFactor, 0.)
      with custom.StarPilotCarParams.from_bytes(historical.StarPilotCarParams.new_message().to_bytes()) as defaults:
        self.assertTrue(defaults.pcmCruiseSpeed)
        self.assertEqual(defaults.learning.version, 0)
      new = custom.StarPilotCarParams.new_message(**values)
      new.learning.version = 1
      new.learning.status = 'qualifiedFit'
      new.learning.latAccelFactor = 3.25
      with historical.StarPilotCarParams.from_bytes(new.to_bytes()) as prior:
        self.assertEqual(prior.to_dict(), values)

  def test_real_controls_treats_valid_historical_payload_as_absent_learning(self):
    with historical_car_params() as historical, integration.joined(self) as run:
      controls = run.controls
      cp_before = controls.CP.as_builder().to_bytes()
      native_factor = controls.LaC.torque_params.latAccelFactor
      old = historical.StarPilotCarParams.new_message(
        alternativeExperience=123, flags=0xffffffff, canUsePedal=True,
        safetyConfigs=[{'safetyParam': 65535}], redneckCruiseAvailable=True)
      readers = []
      for tick in range(100):
        now = integration.NOW + tick * 10_000_000
        integration.feed(controls, now, tick)
        if tick % 25 == 0:
          event = messaging.new_message(SERVICE, valid=True)
          with custom.StarPilotCarParams.from_bytes(old.to_bytes()) as envelope:
            event.autoSteeringLearning = envelope
          reader = messaging.log_from_bytes(event.to_bytes())
          readers.append(reader)
          controls.sm.update_msgs(now / 1e9, [reader])
        with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=now):
          command, _ = controls.state_control()
        self.assertTrue(command.latActive)
        self.assertIsNone(controls.torque_host)
        self.assertIsNone(controls.automatic_learning.result)
        self.assertEqual(controls.LaC.torque_params.latAccelFactor, native_factor)
      self.assertTrue(controls.sm.all_checks([SERVICE]))
      self.assertFalse(controls.sm.simulation)
      self.assertEqual(len(readers), 4)
      self.assertEqual(controls.automatic_learning.session, '')
      self.assertEqual(controls.CP.as_builder().to_bytes(), cp_before)

  def test_transient_flat_learner_bytes_cannot_be_admitted_as_nested_fit(self):
    with historical_car_params(TRANSIENT_FLAT_LEARNER) as historical, integration.joined(self) as run:
      controls = run.controls
      cp_before = controls.CP.as_builder().to_bytes()
      native_factor = controls.LaC.torque_params.latAccelFactor
      identity = run.producer.identity
      self.assertIsNotNone(identity)
      old = historical.AutoSteeringLearning.new_message(
        version=1, status='qualifiedFit', identity=identity, session='transient-c204', sequence=1,
        observedMonoTime=integration.NOW, validUntilMonoTime=integration.NOW + 500_000_000,
        sourceWindowStartMonoTime=integration.NOW - 10_000_000_000,
        sourceWindowEndMonoTime=integration.NOW - 1_000_000_000,
        family='linearFactor', latAccelFactor=native_factor * 1.05,
        acceptancePolicyId=next(iter(controls.automatic_learning.policies)),
        trainWindows=10, heldoutWindows=8, trainBaselineLoss=.1, trainCandidateLoss=.09,
        heldoutBaselineLoss=.1, heldoutCandidateLoss=.09)
      # Use the genuinely admitted policy, so only the changed wire layout denies the fit.
      self.assertEqual(str(old.status), 'qualifiedFit')
      self.assertEqual(old.identity.to_dict(), identity)
      readers = []
      for tick in range(50):
        now = integration.NOW + tick * 10_000_000
        integration.feed(controls, now, tick)
        if tick % 25 == 0:
          event = messaging.new_message(SERVICE, valid=True)
          with custom.StarPilotCarParams.from_bytes(old.to_bytes()) as envelope:
            self.assertEqual(envelope.learning.version, 0)
            event.autoSteeringLearning = envelope
          reader = messaging.log_from_bytes(event.to_bytes())
          readers.append(reader)
          controls.sm.update_msgs(now / 1e9, [reader])
        with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=now):
          command, _ = controls.state_control()
        self.assertTrue(command.latActive)
        self.assertIsNone(controls.torque_host)
        self.assertIsNone(controls.automatic_learning.result)
        self.assertEqual(controls.LaC.torque_params.latAccelFactor, native_factor)
      self.assertTrue(controls.sm.all_checks([SERVICE]))
      self.assertEqual(len(readers), 2)
      self.assertEqual(controls.automatic_learning.session, '')
      self.assertEqual(controls.CP.as_builder().to_bytes(), cp_before)
