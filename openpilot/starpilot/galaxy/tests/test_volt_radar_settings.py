from types import SimpleNamespace
from unittest.mock import Mock
from pathlib import Path

import pytest

from opendbc.car.gm.values import CAR
from openpilot.common.params import Params
from openpilot.starpilot.car.gm.radar_recovery import KEY
from openpilot.starpilot.car.gm.tests.test_radar_recovery import vehicle
from openpilot.starpilot.favorites.actions import FEATURE_KEYS
from openpilot.starpilot.galaxy.settings import AuthorityContext, SettingsChanged, SettingsGateway
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeaturePage, row_change, row_default


@pytest.fixture
def setup(tmp_path):
  params = Params(str(tmp_path))
  current = SimpleNamespace(cp=vehicle(), raw=b'confirmed-volt', parked=True, saved=False)
  context = Mock(sample=lambda: AuthorityContext(current.parked, current.cp, current.raw, editing_saved_vehicle=current.saved))
  gateway = SettingsGateway(params, context, clock=lambda: 10)
  return params, current, gateway


def recovery_row(page):
  return next(row for row in page['rows'] if row['label'] == 'Radar Recovery Alert')


def test_shared_galaxy_projection_default_and_owner_routed_reset(setup):
  params, current, gateway = setup
  page = gateway.page('vehicle', 'session', b'generation')
  row = recovery_row(page)
  assert row['label'] == 'Radar Recovery Alert' and row['value'] == row['defaultValue'] == 'Off'
  assert row['choices'] == ['Off', 'On'] and row['resetAvailable']
  assert row['reason'] == 'Play a chime and show a brief message when a radar fault clears. You must re-engage manually.'
  assert params.get(KEY) is None
  index = page['rows'].index(row)
  intent = gateway.preview(page['view'], index, 0, 'session', b'generation', value='On')
  current.parked = False
  assert gateway.confirm(intent['intent'], 'session', b'generation')
  assert params.get_bool(KEY)
  page = gateway.page('vehicle', 'session', b'generation')
  index = page['rows'].index(recovery_row(page))
  intent = gateway.preview(page['view'], index, 0, 'session', b'generation', reset_default=True)
  assert gateway.confirm(intent['intent'], 'session', b'generation')
  assert not params.get_bool(KEY)


@pytest.mark.parametrize('kind', ['unknown', 'bolt', 'other_gm', 'radarless', 'passive', 'saved_selection'])
def test_ineligible_information_hidden_in_shared_page_and_search_projection(setup, kind):
  _, current, gateway = setup
  if kind == 'unknown':
    current.cp = None
  elif kind == 'bolt':
    current.cp = vehicle(CAR.CHEVROLET_BOLT_EUV)
  elif kind == 'other_gm':
    current.cp = vehicle(CAR.GMC_ACADIA)
  elif kind == 'radarless':
    current.cp.radarUnavailable = True
  elif kind == 'passive':
    current.cp.passive = True
  else:
    current.saved = True
  assert all(row['label'] != 'Radar Recovery Alert' for row in gateway.page('vehicle', 'session', b'generation')['rows'])


def test_no_native_settings_or_favorite_registration(setup):
  params, current, gateway = setup
  owner = FeatureSettingsOwner(params, lambda group: True, vehicle_fingerprint=lambda: current.cp.carFingerprint,
                               vehicle_params=lambda: current.cp)
  state = owner.snapshot(FeaturePage.VEHICLE, parked=True, system_long=True, lateral_context=True, metric=False)
  assert all(row.key != KEY for row in state.rows)
  assert all(KEY not in keys for keys in FEATURE_KEYS.values())
  galaxy_row = next(row for row in gateway._state('vehicle', gateway.context.sample()).rows if row.key == KEY)
  assert not owner.apply(row_change(galaxy_row))


@pytest.mark.parametrize('change', ['vehicle', 'vin', 'saved', 'session', 'preference'])
def test_pending_write_cannot_cross_changed_context(setup, change):
  params, current, gateway = setup
  page = gateway.page('vehicle', 'session', b'generation')
  index = page['rows'].index(recovery_row(page))
  intent = gateway.preview(page['view'], index, 0, 'session', b'generation', value='On')
  if change == 'vehicle':
    current.cp = vehicle(CAR.CHEVROLET_BOLT_EUV)
    current.raw = b'bolt'
  elif change == 'vin':
    current.cp.carVin = 'different'
  elif change == 'saved':
    current.saved = True
  elif change == 'preference':
    Path(params.get_param_path(KEY)).write_bytes(b'0')
  try:
    assert not gateway.confirm(intent['intent'], 'session', b'generation', session_valid=lambda: change != 'session')
  except SettingsChanged:
    pass
  assert not params.get_bool(KEY)


def test_invalid_saved_preference_not_repaired_by_raw_reset(setup):
  params, _, gateway = setup
  Path(params.get_param_path(KEY)).write_bytes(b'bad')
  row = next(row for row in gateway._state('vehicle', gateway.context.sample()).rows if row.key == KEY)
  assert not row.available
  assert row_change(row) is None and row_default(row) is None
  assert Path(params.get_param_path(KEY)).read_bytes() == b'bad'
