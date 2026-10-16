"""Detected vehicle telemetry populates Galaxy without changing Auto selection."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from opendbc.car import gen_empty_fingerprint
from opendbc.car.car_helpers import interfaces
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.galaxy.settings import LiveContextSource, SettingsChanged, SettingsGateway
from openpilot.starpilot.schema_cache import put_cache
from openpilot.starpilot.vehicle_selection import encode


@pytest.fixture
def detected():
  with OpenpilotPrefix(), tempfile.TemporaryDirectory() as directory:
    params = Params(directory)
    params.put_bool('OpenpilotEnabledToggle', True, block=True)
    now = [100_000_000_000]
    sm = messaging.SubMaster(['deviceState', 'pandaStates', 'carState', 'selfdriveState', 'carParams'])
    source = LiveContextSource(params, messages=sm, borrowed_messages=True, mono_clock=lambda: now[0])
    gateway = SettingsGateway(params, source)
    with patch.object(source, 'offroad', return_value=True):
      yield params, now, sm, source, gateway
    gateway.close()


def publish(detected, identity='HYUNDAI_IONIQ_6', *, valid=True, stamp=None):
  _, now, sm, _, _ = detected
  cp = interfaces[identity].get_params(identity, gen_empty_fingerprint(), [], False, False, False)
  cp.fingerprintSource = 'can'
  now[0] += 1_000_000_000
  event = messaging.new_message('carParams', valid=valid, logMonoTime=now[0] if stamp is None else stamp)
  event.carParams = cp
  sm.update_msgs(now[0] / 1e9, [event.as_reader()])
  return cp


@pytest.mark.parametrize('identity', ['HYUNDAI_IONIQ_6', 'CHEVROLET_VOLT_ASCM', 'TOYOTA_COROLLA_TSS2'])
def test_actual_gateway_auto_exposes_learning_and_same_vehicle_fields_as_manual(detected, identity):
  params, _, _, source, gateway = detected
  assert source.sample().cp is None
  cp = publish(detected, identity)
  before = cp.to_dict()
  pages = {name: gateway.page(name, 'session', b'generation') for name in ('torque', 'vehicle')}
  learning = next(row for row in pages['torque']['rows'] if row['label'] == 'Use StarPilot Auto Learn')
  assert learning['available']
  params.put('VehicleSelection', json.loads(encode(identity)), block=True)
  for name, automatic in pages.items():
    manual = gateway.page(name, 'session', b'generation')
    assert [(r['label'], r['available'], r['value']) for r in automatic['rows']] == [
      (r['label'], r['available'], r['value']) for r in manual['rows']]
  assert cp.to_dict() == before
  for key in ('CarParams', 'CarParamsPersistent', 'CarParamsCache'):
    assert not Path(params.get_param_path(key)).exists()


def test_auto_learning_can_be_saved_and_republication_does_not_reset_context(detected):
  params, _, _, source, gateway = detected
  publish(detected)
  token = source.sample().cp_raw
  page = gateway.page('torque', 'session', b'generation')
  index = next(i for i, row in enumerate(page['rows']) if row['label'] == 'Use StarPilot Auto Learn')
  intent = gateway.preview(page['view'], index, 0, 'session', b'generation', value='Off')
  publish(detected)
  assert source.sample().cp_raw == token
  assert gateway.confirm(intent['intent'], 'session', b'generation')
  saved = gateway.page('torque', 'session', b'generation')
  assert next(row for row in saved['rows'] if row['label'] == 'Use StarPilot Auto Learn')['value'] == 'Off'
  assert params.get('VehicleSelection') is None


def test_new_detected_vehicle_invalidates_previous_vehicle_edit(detected):
  _, _, _, _, gateway = detected
  publish(detected)
  page = gateway.page('torque', 'session', b'generation')
  index = next(i for i, row in enumerate(page['rows']) if row['label'] == 'Use StarPilot Auto Learn')
  intent = gateway.preview(page['view'], index, 0, 'session', b'generation', value='Off')
  publish(detected, 'TOYOTA_COROLLA_TSS2')
  with pytest.raises(SettingsChanged):
    gateway.confirm(intent['intent'], 'session', b'generation')


@pytest.mark.parametrize('variation', ['invalid', 'future', 'old', 'stale', 'not_seen', 'not_alive', 'oversized', 'reset'])
def test_unusable_live_vehicle_falls_back_to_verified_cache(detected, variation):
  params, now, sm, source, _ = detected
  cached = interfaces['TOYOTA_COROLLA_TSS2'].get_params('TOYOTA_COROLLA_TSS2', gen_empty_fingerprint(), [], False, False, False)
  put_cache(params, 'CarParamsPersistent', cached, block=True)
  before = Path(params.get_param_path('CarParamsPersistent')).read_bytes()
  publish(detected)
  if variation == 'invalid':
    sm.valid['carParams'] = False
  elif variation == 'future':
    sm.logMonoTime['carParams'] = now[0] + 1
  elif variation == 'old':
    sm.logMonoTime['carParams'] = source.device_after_mono_ns
  elif variation == 'stale':
    now[0] += source.MAX_LIVE_CP_AGE_NS + 1
  elif variation == 'not_seen':
    sm.seen['carParams'] = False
  elif variation == 'not_alive':
    sm.alive['carParams'] = False
  elif variation == 'oversized':
    source.MAX_CP_BYTES = 1
    assert source.runtime_vehicle()[0] is None
    return
  elif variation == 'reset':
    sm.after_mono_ns = now[0]
  cp, _ = source.runtime_vehicle()
  assert cp.carFingerprint == cached.carFingerprint
  assert Path(params.get_param_path('CarParamsPersistent')).read_bytes() == before


def test_explicit_manual_choice_remains_an_offroad_override(detected):
  params, _, _, source, _ = detected
  publish(detected)
  params.put('VehicleSelection', json.loads(encode('TOYOTA_COROLLA_TSS2')), block=True)
  assert source.runtime_vehicle()[0].carFingerprint == 'HYUNDAI_IONIQ_6'
  assert source.sample().cp.carFingerprint == 'TOYOTA_COROLLA_TSS2'
