from types import SimpleNamespace
from unittest.mock import Mock

from openpilot.starpilot.analytics.runtime import AnalyticsWorker


class Source:
  def __init__(self):
    self.data = {'deviceState': SimpleNamespace(started=False), 'carState': SimpleNamespace(vEgo=10),
                 'carControl': SimpleNamespace(latActive=True, longActive=False),
                 'selfdriveState': SimpleNamespace(enabled=False), 'modelV2': SimpleNamespace(big=False)}
    self.valid = dict.fromkeys(self.data, True)
    self.alive = dict(self.valid)
    self.logMonoTime = dict.fromkeys(self.data, 1_000_000_000)
    self.valid.update(carParams=False, gpsLocationExternal=False)
    self.alive.update(carParams=False, gpsLocationExternal=False)
    self.logMonoTime.update(carParams=0, gpsLocationExternal=0)

  def __getitem__(self, key):
    return self.data[key]

  def update(self, timeout):
    pass


def worker():
  values = {'ShareUsageStats': True, 'IsOffroad': True}
  params = Mock()
  params.get.side_effect = values.get
  params.get_bool.side_effect = lambda key: values.get(key, False)
  params.put.side_effect = lambda key, value, **kwargs: values.__setitem__(key, value)
  source = Source()
  clock = [1.0]
  client = Mock()
  client.send.return_value = True
  obj = AnalyticsWorker(params, source, collector=lambda *a: {}, token_reader=lambda: 'token',
                        client=client, commit_reader=lambda *a, **k: None, clock_valid=lambda: True, monotonic=lambda: clock[0], wall=lambda: 1_800_000_000,
                        identity=lambda *a: {'driving_model': 'executed'})
  return obj, values, source, clock, client


def test_initial_send_and_consent_rechecked_at_transport():
  obj, values, source, clock, client = worker()
  obj.poll_once()
  assert client.send.call_count == 1
  gate = client.send.call_args.kwargs['allowed']
  source.data['deviceState'].started = True
  assert not gate()
  source.data['deviceState'].started = False
  values['ShareUsageStats'] = False
  assert not gate()


def test_driving_snapshot_survives_offroad_clear_and_counts_actual_aol():
  obj, values, source, clock, client = worker()
  obj.poll_once()
  source.data['deviceState'].started = True
  values['IsOffroad'] = False
  clock[0] = 1.1
  obj.poll_once()
  assert client.send.call_count == 1
  assert obj.counters['drives'] == 1
  assert abs(obj.counters['total_aol_seconds'] - .1) < 1e-6
  source.valid['modelV2'] = False
  source.data['deviceState'].started = False
  values['IsOffroad'] = True
  clock[0] = 1.2
  obj.poll_once()
  assert b'driving_model=executed' in client.send.call_args.args[0]


def test_missing_credentials_and_stale_source_never_send():
  obj, values, source, clock, client = worker()
  obj.token_reader = lambda: None
  obj.poll_once()
  client.send.assert_not_called()
  assert values['UsageStatsStatus']['state'] == 'awaiting_credentials'
  obj.token_reader = lambda: 'token'
  clock[0] = 40
  obj.poll_once()
  client.send.assert_not_called()


def test_failures_have_finite_parked_retry_budget_and_bounded_stop():
  obj, values, source, clock, client = worker()
  client.send.return_value = False
  for _ in range(10):
    source.logMonoTime = dict.fromkeys(source.logMonoTime, int(clock[0] * 1e9))
    obj.poll_once()
    clock[0] += 301
  assert client.send.call_count == 5
  obj.start()
  obj.close()
  assert not obj.thread.is_alive()


def test_startup_onroad_and_disabled_sharing_never_contact_transport():
  obj, values, source, clock, client = worker()
  source.data['deviceState'].started = True
  values['IsOffroad'] = False
  obj.poll_once()
  client.send.assert_not_called()
  source.data['deviceState'].started = False
  values['IsOffroad'] = True
  values['ShareUsageStats'] = False
  obj.poll_once()
  client.send.assert_not_called()


def test_host_optional_hook_does_not_construct_network_worker():
  from unittest.mock import patch
  from openpilot.starpilot.analytics.runtime import start_optional_worker
  with patch('openpilot.common.hardware.COMMA_HARDWARE', False), patch('openpilot.starpilot.analytics.runtime.AnalyticsWorker') as factory:
    assert start_optional_worker() is None
    factory.assert_not_called()


def test_malformed_saved_state_has_finite_sanitized_counters():
  obj, values, source, clock, client = worker()
  values['UsageStatsState'] = {'version': 1, 'counters': 'bad', 'region': {'latitude': 12.345678}, 'extra': 'x' * 100000}
  other = AnalyticsWorker(obj.params, source, client=client, collector=lambda *a: {}, token_reader=lambda: None,
                          monotonic=lambda: clock[0], clock_valid=lambda: True)
  assert sum(other.counters.values()) == 0
  assert 'extra' not in other.state and 'region' not in other.state


def test_registered_native_params_roundtrip_and_restart_context():
  import tempfile
  from openpilot.common.params import Params
  from pathlib import Path
  from openpilot.starpilot.state_migration import prepare_manager_start
  with tempfile.TemporaryDirectory() as directory:
    params = Params(str(Path(directory) / 'params'))
    storage = Path(directory) / 'recovery'
    prepare_manager_start(params, storage)
    params.put_bool('ShareUsageStats', False, block=True)
    params.put_bool('IsOffroad', True, block=True)
    source = Source()
    obj = AnalyticsWorker(params, source, collector=lambda *a: {}, client=Mock(), token_reader=lambda: None,
                          monotonic=lambda: 1.0, clock_valid=lambda: True)
    obj.context = {'car_make': 'gm', 'car_model': 'actual', 'driving_model': 'verified'}
    obj.persist()
    assert isinstance(params.get('UsageStatsState'), dict)
    saved = params.get('UsageStatsState')
    prepare_manager_start(params, storage, dry_run=True)
    prepare_manager_start(params, storage)
    assert params.get('UsageStatsState') == saved
    assert params.get('ShareUsageStats') is False
    restored = AnalyticsWorker(params, source, collector=lambda *a: {}, client=Mock(), token_reader=lambda: None,
                               monotonic=lambda: 1.0, clock_valid=lambda: True)
    assert restored.context['driving_model'] == 'verified'
    assert restored.metadata['dongle_id'] == obj.metadata['dongle_id']
    restored.poll_once()
    restored.client.send.assert_not_called()


def test_enabling_consent_while_parked_schedules_report():
  obj, values, source, clock, client = worker()
  values['ShareUsageStats'] = False
  obj.poll_once()
  client.send.assert_not_called()
  values['ShareUsageStats'] = True
  obj.poll_once()
  assert client.send.call_count == 1


def test_executed_model_reports_verified_fallback_not_saved_request():
  from unittest.mock import patch
  from openpilot.starpilot.analytics.runtime import executed_model
  from openpilot.starpilot.models.catalog import BY_ID
  from openpilot.starpilot.models.status import ModelHealth, ModelVariant
  source = Source()
  status = SimpleNamespace(health=ModelHealth.ACTIVE, loaded_id='rdf43', artifact_sha256='a' * 64,
                           variant=ModelVariant.SMALL, requested_id='some-selected-large-model')
  with patch('openpilot.starpilot.models.jetlink_adapter.runtime_status', return_value={'active': False}), \
       patch('openpilot.starpilot.models.runtime.snapshot', return_value=status):
    result = executed_model(source, Mock(), 1_000_000_000)
  assert result['driving_model'] == BY_ID['rdf43'].name
  assert result['metrics']['model_variant'] == 'small'
  assert 'some-selected-large-model' not in str(result)
  source.data['modelV2'].big = True
  with patch('openpilot.starpilot.models.jetlink_adapter.runtime_status',
             return_value={'active': True, 'artifact_sha256': 'b' * 64}):
    remote = executed_model(source, Mock(), 1_000_000_000)
  assert remote['metrics']['model_sha256'] == 'b' * 64
  assert remote['metrics']['model_variant'] == 'jetlink'


def test_new_drive_clears_prior_identity_brief_unavailable_retains_last_used():
  obj, values, source, clock, client = worker()
  obj.poll_once()
  source.data['deviceState'].started = True
  values['IsOffroad'] = False
  obj.poll_once()
  assert obj.context['driving_model'] == 'executed'
  obj.identity = lambda *a: {}
  clock[0] = 2.0
  source.logMonoTime['modelV2'] = 2_000_000_000
  source.logMonoTime['deviceState'] = 2_000_000_000
  obj.poll_once()
  assert obj.context['driving_model'] == 'executed'
  source.data['deviceState'].started = False
  values['IsOffroad'] = True
  obj.poll_once()
  source.data['deviceState'].started = True
  values['IsOffroad'] = False
  obj.poll_once()
  assert 'driving_model' not in obj.context
  obj.identity = lambda *a: {'driving_model': 'verified-fallback'}
  clock[0] = 3.1
  source.logMonoTime['modelV2'] = 3_100_000_000
  source.logMonoTime['deviceState'] = 3_100_000_000
  obj.poll_once()
  assert obj.context['driving_model'] == 'verified-fallback'


def test_new_month_offroad_does_not_report_old_month_distance():
  obj, values, source, clock, client = worker()
  obj.state['month'] = '2000-01'
  obj.counters['current_months_meters'] = 1000
  obj.poll_once()
  assert obj.counters['current_months_meters'] == 0


def test_executed_model_real_message_catalog_identity_and_actual_small_fallback():
  from unittest.mock import patch
  from openpilot.cereal import messaging
  from openpilot.starpilot.analytics.runtime import executed_model
  from openpilot.starpilot.models.catalog import BY_ID
  from openpilot.starpilot.models.status import ModelHealth, ModelStatus, ModelVariant
  source = Source()
  source.data['modelV2'] = messaging.new_message('modelV2').modelV2
  status = ModelStatus('selected-large', 'rdf43', ModelVariant.SMALL, ModelHealth.ACTIVE, True,
                       'large model unavailable', 'a' * 64)
  with patch('openpilot.starpilot.models.jetlink_adapter.runtime_status', return_value={'active': False}), \
       patch('openpilot.starpilot.models.runtime.snapshot', return_value=status) as projection:
    params = Mock()
    result = executed_model(source, params, 1_000_000_000)
    projection.assert_called_once_with(source, params, 1_000_000_000)
  assert result == {'driving_model': BY_ID['rdf43'].name,
                    'metrics': {'model_sha256': 'a' * 64, 'model_variant': 'small'}}
  assert 'selected-large' not in str(result)


def test_executed_model_remote_requires_actual_big_output_not_remote_selection():
  from unittest.mock import patch
  from openpilot.cereal import messaging
  from openpilot.starpilot.analytics.runtime import executed_model
  from openpilot.starpilot.models.catalog import BY_ID
  from openpilot.starpilot.models.status import ModelHealth, ModelStatus, ModelVariant
  source = Source()
  source.data['modelV2'] = messaging.new_message('modelV2').modelV2
  small = ModelStatus('selected-large', 'rdf43', ModelVariant.SMALL, ModelHealth.ACTIVE, False, None, 'a' * 64)
  remote = {'active': True, 'artifact_sha256': 'b' * 64}
  with patch('openpilot.starpilot.models.jetlink_adapter.runtime_status', return_value=remote), \
       patch('openpilot.starpilot.models.runtime.snapshot', return_value=small) as projection:
    source.data['modelV2'].big = True
    big = executed_model(source, Mock(), 1_000_000_000)
    projection.assert_not_called()
    assert big == {'driving_model': 'jetlink:' + 'b' * 16,
                   'metrics': {'model_sha256': 'b' * 64, 'model_variant': 'jetlink'}}
    source.data['modelV2'].big = False
    fallback = executed_model(source, Mock(), 1_000_000_000)
    assert fallback['driving_model'] == BY_ID['rdf43'].name
    assert fallback['metrics']['model_sha256'] == 'a' * 64


def test_executed_model_unverified_receipt_never_reports_requested_identity():
  from unittest.mock import patch
  from openpilot.cereal import messaging
  from openpilot.starpilot.analytics.runtime import executed_model
  from openpilot.starpilot.models.status import ModelHealth, ModelStatus
  source = Source()
  source.data['modelV2'] = messaging.new_message('modelV2').modelV2
  for health in (ModelHealth.UNAVAILABLE, ModelHealth.IDENTITY_UNAVAILABLE, ModelHealth.LOADING,
                 ModelHealth.STALE, ModelHealth.FAILED):
    status = ModelStatus('selected-large', None, None, health, True, 'unverified', None)
    with patch('openpilot.starpilot.models.jetlink_adapter.runtime_status', return_value={'active': False}), \
         patch('openpilot.starpilot.models.runtime.snapshot', return_value=status):
      assert executed_model(source, Mock(), 1_000_000_000) == {}
