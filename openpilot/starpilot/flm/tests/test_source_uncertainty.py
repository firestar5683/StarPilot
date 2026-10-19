"""Actual source reader/parent loop; synthetic transport, no fitted admission."""
from dataclasses import replace
from types import SimpleNamespace
from typing import cast
from unittest import mock

import pytest
from openpilot.starpilot.flm import runtime_adapter_registry as registry, steerlearnerd
from openpilot.starpilot.flm.fullrate_collector import FullrateCollector, RawBlock, RawPoint
from openpilot.starpilot.flm.physical_observation import PendingPhysical
from openpilot.starpilot.flm.tests.test_fixed_manual_baseline import fixed_controls, BASE
from openpilot.starpilot.flm.tests.test_fullrate_pipeline import SyntheticAdapter, snapshots, serialized_control, serialized_output
from openpilot.starpilot.lateral.learning_preferences import KEY, replace_preference


def test_actual_saved_read_failure_unknown_then_exact_configuration_recovery():
  with fixed_controls() as (controls, _):
    args = {'now_ns': BASE, 'calibration': (0., 0., 0.), 'vehicle_session': 'source-test', 'calibration_generation': 'a' * 32}
    first = registry.read_source(controls.CP, controls.params, **args)
    assert first.configuration_known and first.enabled and first.source_epoch
    original = registry.read_saved
    with mock.patch.object(registry, 'read_saved', side_effect=lambda params, key, bound:
                           (b'', False) if key == KEY else original(params, key, bound)):
      missing = registry.read_source(controls.CP, controls.params, **args)
    assert not missing.configuration_known and not missing.enabled and not missing.source_epoch
    recovered = registry.read_source(controls.CP, controls.params, **args)
    assert steerlearnerd._source_config_binding(recovered) == steerlearnerd._source_config_binding(first)


@pytest.mark.parametrize('raw', (b'', b'{"version":1,"version":1,"vehicles":{}}', b'x' * 4097))
def test_invalid_actual_preference_is_unknown_not_explicit_off(raw):
  with fixed_controls() as (controls, _):
    controls.params.put(KEY, raw, block=True)
    value = registry.read_source(controls.CP, controls.params, now_ns=BASE, calibration=(0., 0., 0.), vehicle_session='source-test')
    assert not value.configuration_known and not value.enabled and not value.source_epoch


def test_actual_explicit_off_is_known_without_calibration():
  with fixed_controls() as (controls, _):
    controls.params.put(KEY, replace_preference(controls.params.get(KEY), controls.CP, False), block=True)
    value = registry.read_source(controls.CP, controls.params, now_ns=BASE, calibration=(), vehicle_session='source-test')
    assert value.configuration_known and not value.enabled and value.reset == '0'
    assert steerlearnerd._source_config_known(value, BASE)


def test_actual_preference_parsed_from_same_once_captured_bytes_as_epoch():
  with fixed_controls() as (controls, _):
    original, calls = registry.read_saved, []
    def read(params, key, bound):
      raw, readable = original(params, key, bound)
      calls.append(key)
      if key == KEY:
        params.put(KEY, replace_preference(raw, controls.CP, False), block=True)
      return raw, readable
    with mock.patch.object(registry, 'read_saved', side_effect=read), \
         mock.patch('openpilot.starpilot.lateral.learning_preferences.read_saved',
                    side_effect=AssertionError('read_source must not reread preference bytes')):
      first = registry.read_source(controls.CP, controls.params, now_ns=BASE, calibration=(0., 0., 0.), vehicle_session='source-test')
    second = registry.read_source(controls.CP, controls.params, now_ns=BASE + 1, calibration=(0., 0., 0.), vehicle_session='source-test')
    assert calls.count(KEY) == 1
    assert first.configuration_known and first.enabled
    assert second.configuration_known and not second.enabled


def exercise(recovery=None, *, publication_uncertain=False, publication_only_recovery=False):
  now, phase = [BASE], [-1]
  key = ('feedforward', 'low', 'steady')
  source = registry.SourceState(True, False, '0', '2' * 64, BASE, BASE + 500_000_000, 'b' * 64,
    (0., 0., 0.), calibration_generation='a' * 32)
  unknown = registry.SourceState(False, False, '', '', BASE, BASE + 500_000_000, 'b' * 64, configuration_known=False)
  objects, published, saves, history = [], [], [], []
  class Adapter(SyntheticAdapter):
    raw_storage = False
    @property
    def event_collection(self):
      return publication_only_recovery and phase[0] == 2
    def __init__(self):
      super().__init__()
      self.current_physical_valid = False
      self.last_physical_ns = 0
      self.fit_profile = None
      self.replay = SimpleNamespace(failed=False, records=('original-frame',), checkpoints=('original-checkpoint',))
    def select_objective(self, value):
      if publication_only_recovery and phase[0] == 2:
        from openpilot.starpilot.flm.event_collection import EventCollectionAdapter
        # Execute the actual event selector guard if the owner calls it without
        # a newly selected control objective; this must never be reached.
        EventCollectionAdapter.select_objective(cast(EventCollectionAdapter, SimpleNamespace(_event_initialized=True)), value)
        raise AssertionError("publication selected an objective before new control")
    def prepare_control(self, value):
      return value
  sm = mock.Mock()
  def update(timeout=None):
    if timeout == 0:
      return
    phase[0] += 1
    if phase[0] >= 3:
      raise StopIteration
    now[0] = BASE + phase[0] * 300_000_000
  sm.update.side_effect = update
  def read(stamp):
    item = unknown if phase[0] == 1 or (publication_only_recovery and phase[0] == 2) else replace(source, **(recovery or {})) if phase[0] == 2 else source
    return replace(item, observed_ns=stamp, expires_ns=stamp + 500_000_000)
  def publication_read(stamp):
    return replace(unknown if phase[0] == 1 else source, observed_ns=stamp, expires_ns=stamp + 500_000_000)
  def factory(adapter):
    collector = FullrateCollector(adapter)
    objects.append(collector)
    return collector
  c_sock, a_sock = object(), object()
  def drain(socket, callback, receive, sink, stamp):
    if publication_only_recovery and phase[0] == 2:
      return
    control, output, _ = snapshots(now[0] - 1_000_000)
    control = replace(control, source_receipt_ns=now[0], control_ns=now[0], state_ns=now[0] - 1_000_000)
    output = replace(output, control_ns=now[0], state_ns=now[0], apply_ns=now[0])
    callback(serialized_control(control) if socket is c_sock else serialized_output(output), sink, stamp)
    if socket is a_sock and phase[0] == 0 and objects:
      c = objects[0]
      rows = tuple(RawPoint(control.control_ns, output.apply_ns, output.apply_ns + i,
        control, output, {'synthetic_transport_only': i}, ('original-physical',)) for i in range(40))
      c.blocks.append(RawBlock(control.identity, 'original-storage', 'original', control.stage_revision, control.response_revision, rows))
  def send(service, event):
    row = event.autoSteeringLearning.learning
    published.append((phase[0], str(row.status), str(row.reason), row.runtimeProfile.version))
    if objects:
      c = objects[0]
      history.append((phase[0], len(c.blocks), len(c.ready), c.active_since, c.last_qualified_response,
                      c.adapter.current_physical_valid, c.adapter.replay.failed))
  fitter = mock.Mock(child=object())
  fitter.poll.return_value = None
  persistence, publisher = mock.Mock(), mock.Mock()
  persistence.save_current.side_effect = lambda *args, **kwargs: saves.append(phase[0])
  publisher.send.side_effect = send
  with mock.patch.object(steerlearnerd, 'drain', drain), \
       mock.patch.object(steerlearnerd, 'FullrateCollector', side_effect=factory), \
       mock.patch('openpilot.starpilot.flm.native_health.current_native_health', return_value=True):
    with pytest.raises(StopIteration):
      steerlearnerd.run(SimpleNamespace(), sm, c_sock, a_sock, publisher,
        lambda *args: Adapter(), lambda *args: PendingPhysical(now[0], now[0]),
        (lambda stamp: replace(source, observed_ns=stamp, expires_ns=stamp + 500_000_000)) if publication_uncertain else read,
        lambda _: (key,), lambda _: key, mock.Mock(), persistence, fitter, mock.Mock(), clock=lambda: now[0],
        publication_source_reader=publication_read if publication_uncertain or publication_only_recovery else None)
  return objects, published, saves, history, fitter


def test_actual_owner_uncertainty_keeps_storage_not_current_authority():
  collectors, published, saves, history, fitter = exercise()
  assert len(collectors) == 1 and len(collectors[0].blocks) == 1
  uncertain = next(row for row in history if row[0] == 1)
  assert uncertain[1:] == (1, 0, 0, 0, False, True)
  assert 1 not in saves
  assert any(row[0] == 1 and row[1] == 'unavailable' and row[3] == 0 for row in published)
  assert any(call.args == ('source_configuration_uncertain',) for call in fitter.cancel.call_args_list)
  assert collectors[0].fit_result is None and collectors[0].last_validation is None


@pytest.mark.parametrize('changes', ({'source_epoch': 'd' * 64}, {'reset': '1'},
  {'calibration_generation': 'c' * 32}, {'cp_sha256': 'd' * 64},
  {'manual_baseline': (3., 0., .1)}, {'enabled': False}, {'manual': True}))
def test_actual_owner_changed_or_explicit_disabled_recovery_purges_storage(changes):
  collectors, _, _, _, _ = exercise(changes)
  assert not collectors[0].blocks


def test_publication_uncertainty_cannot_save_or_publish_admission():
  _, published, saves, _, _ = exercise(publication_uncertain=True)
  assert 1 not in saves
  assert any(row[0] == 1 and row[1] == 'unavailable' and row[3] == 0 for row in published)



def test_actual_legacy_explicit_off_is_known_without_calibration():
  with fixed_controls() as (controls, _):
    controls.params.remove(KEY)
    controls.params.put_bool('ForceAutoTuneOff', True, block=True)
    source = registry.read_source(controls.CP, controls.params, now_ns=BASE, calibration=(), vehicle_session='source-test')
    assert source.configuration_known and not source.enabled


@pytest.mark.parametrize('changes', ({'observed_ns': BASE + 1}, {'expires_ns': BASE - 1},
  {'expires_ns': BASE + 500_000_001}, {'reset': ''}, {'reset': 'invalid'},
  {'cp_sha256': 'wrong'}, {'enabled': 0}, {'configuration_known': False}))
def test_malformed_or_stale_receipt_never_qualifies_for_explicit_off_purge(changes):
  source = registry.SourceState(False, False, '0', 'a' * 64, BASE, BASE + 500_000_000, 'b' * 64)
  assert not steerlearnerd._source_config_known(replace(source, **changes), BASE)


def test_actual_owner_publication_recovery_without_new_control_stays_unavailable():
  collectors, published, saves, history, _ = exercise(publication_only_recovery=True)
  assert len(collectors) == 1 and len(collectors[0].blocks) == 1
  assert 2 not in saves
  assert any(row[0] == 2 and row[1] == 'unavailable' and row[3] == 0 for row in published)
  assert next(row for row in history if row[0] == 2)[2:] == (0, 0, 0, False, True)
