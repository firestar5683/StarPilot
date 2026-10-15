"""Idle shortcut is narrow; accepted wheel traffic keeps live admission checks."""

from contextlib import contextmanager
import copy
import tempfile
import unittest
from unittest.mock import Mock, patch

from capnp.lib.capnp import KjException
from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.controllers.coast import CoastOwner, CoastPlan, CoastRuntime
from openpilot.starpilot.controllers import wheel_actions

DRIVE, NOW = 1_000_000_000, 3_000_000_000
SERVICES = ('deviceState', 'carState', 'carControl')


@contextmanager
def coast_fixture():
  """Reusable actual Params + reader CP + actual SubMaster, with private IPC."""
  with OpenpilotPrefix(), tempfile.TemporaryDirectory() as directory:
    params = Params(directory)
    params.put_bool('SafeMode', False, block=True)
    cp = CarInterface.get_params(CAR.HONDA_CIVIC_BOSCH, gen_empty_fingerprint(), [], True, False, False).as_reader()
    sm = messaging.SubMaster(list(SERVICES), poll='carState')
    frames = []
    for service in SERVICES:
      message = messaging.new_message(service, valid=True, logMonoTime=NOW)
      if service == 'deviceState':
        message.deviceState.started, message.deviceState.startedMonoTime = True, DRIVE
      elif service == 'carState':
        message.carState.canValid, message.carState.vEgo = True, 20.0
      else:
        message.carControl.enabled = message.carControl.longActive = True
        message.carControl.orientationNED = [0.0, 0.0, 0.0]
      frames.append(message.as_reader())
    sm.update_msgs(NOW / 1e9, frames)
    yield params, cp, sm


def sample(runtime, params, cp, sm, **changes):
  values = {'now_ns': NOW, 'target_mps': 20.0, 'lead_relevant': False, 'stop_context': False}
  values.update(changes)
  return runtime.sample(params, cp, sm, **values)


def deliver_action(runtime, params, cp, sm, action=2):
  """Use the actual WheelPublisher and serialized receipt, without CAN or IPC send."""
  class Sink:
    def send(self, _service, message):
      self.raw = message.to_bytes()
  sink = Sink()
  params.put('DistanceButtonControl', action, block=True)
  publisher = wheel_actions.WheelPublisher()
  publisher.publish((('DistanceButtonControl', action),), cp, sink, now_ns=NOW, drive_id=DRIVE,
                    source_car_ns=NOW, source_control_ns=NOW)
  return runtime.receive(messaging.log_from_bytes(sink.raw), params, cp, sm, now_ns=NOW)


class FallbackReached(Exception):
  pass


class TestCoastIdle(unittest.TestCase):
  def test_zero_admission_resets_all_flags_preserves_bookkeeping_and_skips_work(self):
    with coast_fixture() as (params, cp, sm):
      for drive, heartbeat in ((0, 0), (0, NOW), (DRIVE, 0)):
        for stop in (False, True):
          runtime = CoastRuntime()
          runtime.drive, runtime.consumer.last_heartbeat = drive, heartbeat
          runtime.session, runtime.cp_signature, runtime.traffic_toggles = 'kept', 'kept', 7
          runtime.consumer.session, runtime.consumer.sequence = 'kept-consumer', 23
          runtime.consumer.retired.add('retired')
          runtime.conditional_stop = stop
          for flag in ('force_coast', 'pulse_glide', 'coasting', 'hill_paused'):
            setattr(runtime.owner, flag, True)
          bookkeeping = {key: value for key, value in vars(runtime).items() if key not in ('owner', 'consumer')}
          consumer = copy.deepcopy(vars(runtime.consumer))
          with patch('openpilot.starpilot.saved_source.read_saved', side_effect=AssertionError('idle read')) as reads, \
               patch.object(wheel_actions, 'cp_fingerprint', side_effect=AssertionError('idle hash')) as fingerprint:
            first = sample(runtime, params, cp, sm, stop_context=stop)
            second = sample(runtime, params, cp, sm, stop_context=stop)
          self.assertEqual(first, CoastPlan())
          self.assertIsNot(first, second)
          self.assertFalse(any(vars(runtime.owner).values()))
          self.assertEqual(bookkeeping, {key: value for key, value in vars(runtime).items() if key not in ('owner', 'consumer')})
          self.assertEqual(vars(runtime.consumer), consumer)
          reads.assert_not_called()
          fingerprint.assert_not_called()

  def test_nonexact_sentinels_and_runtime_owners_keep_fallback(self):
    class Integer(int):
      pass
    class RuntimeSubclass(CoastRuntime):
      pass
    class OwnerSubclass(CoastOwner):
      pass
    class ConsumerSubclass(wheel_actions.WheelConsumer):
      pass
    with coast_fixture() as (params, cp, sm):
      for field in ('drive', 'heartbeat', 'stop_context', 'conditional_stop'):
        for value in (False, 0.0, Integer(0), None):
          if field in ('stop_context', 'conditional_stop') and type(value) is bool:
            continue
          runtime, changes = CoastRuntime(), {}
          if field == 'heartbeat':
            runtime.consumer.last_heartbeat = value
          elif field == 'stop_context':
            changes[field] = value
          else:
            setattr(runtime, field, value)
          with self.subTest(field=field, value=value), patch('openpilot.starpilot.saved_source.read_saved', side_effect=FallbackReached):
            with self.assertRaises(FallbackReached):
              sample(runtime, params, cp, sm, **changes)
      runtime_cases = (RuntimeSubclass(), CoastRuntime(), CoastRuntime())
      runtime_cases[1].owner, runtime_cases[2].consumer = OwnerSubclass(), ConsumerSubclass()
      for runtime in runtime_cases:
        with patch('openpilot.starpilot.saved_source.read_saved', side_effect=FallbackReached):
          with self.assertRaises(FallbackReached):
            sample(runtime, params, cp, sm)

  def test_instance_sample_override_is_observed(self):
    with coast_fixture() as (params, cp, sm):
      runtime, marker = CoastRuntime(), object()
      runtime.owner.sample = Mock(return_value=marker)
      with patch('openpilot.starpilot.saved_source.read_saved', return_value=(None, True)), \
           patch.object(wheel_actions, 'cp_fingerprint', return_value='different'):
        self.assertIs(sample(runtime, params, cp, sm), marker)
      runtime.owner.sample.assert_called_once()

  def test_fake_contexts_builders_wrong_schemas_and_missing_readers_fall_back(self):
    class Proxy:
      def __init__(self, target):
        self.target = target
      def __getattr__(self, name):
        return getattr(self.target, name)
      def __getitem__(self, name):
        return self.target[name]
    class Mapping(dict):
      pass
    with coast_fixture() as (params, cp, sm):
      cases = ((Proxy(params), cp, sm), (params, cp, Proxy(sm)),
               (params, cp.as_builder(), sm), (params, structs.CarState().as_reader(), sm))
      for actual_params, actual_cp, actual_sm in cases:
        with patch('openpilot.starpilot.saved_source.read_saved', side_effect=FallbackReached):
          with self.assertRaises(FallbackReached):
            sample(CoastRuntime(), actual_params, actual_cp, actual_sm)
      original = sm.data
      try:
        sm.data = Mapping(original)
        with patch('openpilot.starpilot.saved_source.read_saved', side_effect=FallbackReached):
          with self.assertRaises(FallbackReached):
            sample(CoastRuntime(), params, cp, sm)
        for name in SERVICES:
          for replacement in (None, structs.CarParams().as_reader(), original[name].as_builder()):
            sm.data = dict(original)
            if replacement is None:
              del sm.data[name]
            else:
              sm.data[name] = replacement
            expected = KeyError if replacement is None and name == 'deviceState' else \
                       (AttributeError, KjException) if name == 'deviceState' and replacement.schema == structs.CarParams.schema else FallbackReached
            with self.subTest(name=name, replacement=type(replacement)), \
                 patch('openpilot.starpilot.saved_source.read_saved', side_effect=FallbackReached):
              with self.assertRaises(expected):
                sample(CoastRuntime(), params, cp, sm)
      finally:
        sm.data = original

  def test_real_published_action_ends_shortcut_and_live_rejections_still_reset(self):
    from openpilot.starpilot.saved_source import read_saved
    for fault in ('safe_mode', 'cp_mutation', 'expiry', 'can_invalid', 'can_timeout'):
      with self.subTest(fault=fault), coast_fixture() as (params, cp, sm):
        runtime = CoastRuntime()
        self.assertEqual(sample(runtime, params, cp, sm), CoastPlan())
        self.assertTrue(deliver_action(runtime, params, cp, sm))
        self.assertGreater(runtime.drive, 0)
        self.assertGreater(runtime.consumer.last_heartbeat, 0)
        with patch('openpilot.starpilot.saved_source.read_saved', wraps=read_saved) as reads, \
             patch.object(wheel_actions, 'cp_fingerprint', wraps=wheel_actions.cp_fingerprint) as fingerprint:
          self.assertTrue(sample(runtime, params, cp, sm).force_decel)
          self.assertGreater(reads.call_count, 0)
          fingerprint.assert_called()
        changes = {}
        if fault == 'safe_mode':
          params.put_bool('SafeMode', True, block=True)
        elif fault == 'cp_mutation':
          changed = cp.as_builder()
          changed.carVin = 'changed-after-receipt'
          cp = changed.as_reader()
        elif fault == 'expiry':
          changes['now_ns'] = NOW + wheel_actions.LIFETIME_NS + 1
        else:
          changed = sm.data['carState'].as_builder()
          if fault == 'can_invalid':
            changed.canValid = False
          else:
            changed.canTimeout = True
          sm.data['carState'] = changed.as_reader()
        self.assertEqual(sample(runtime, params, cp, sm, **changes), CoastPlan())
        self.assertFalse(any(vars(runtime.owner).values()))


if __name__ == '__main__':
  unittest.main()
