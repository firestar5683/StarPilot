"""Exact optional secondary Cancel profiles; no unsupported alternative bits."""
import pytest
from opendbc.car.gm.cancel_remap import supported, enabled, aol_enabled, valid_alternative_experience, prepare
from opendbc.car.gm.tests.test_bolt_pedal import params
from opendbc.car.gm.values import CAR

IDS = (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021,
       CAR.CHEVROLET_BOLT_CC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)


@pytest.mark.parametrize('candidate', IDS)
@pytest.mark.parametrize('removed', [False, True])
@pytest.mark.parametrize('aol', [False, True])
def test_exact_configuration_keeps_optional_default_off(candidate, removed, aol):
  cp = params(candidate, pedal=True, camera=True, removed=removed)
  cp.alternativeExperience = 32 if aol else 0
  before = cp.as_reader().to_dict()
  assert supported(cp) and not enabled(cp) and valid_alternative_experience(cp)
  prepare(cp, True)
  assert cp.alternativeExperience == (96 if aol else 64)
  assert enabled(cp) and aol_enabled(cp) is aol and valid_alternative_experience(cp)
  after = cp.as_reader().to_dict()
  after['alternativeExperience'] = before['alternativeExperience']
  assert after == before
  prepare(cp, False)
  assert cp.alternativeExperience == (32 if aol else 0)
  assert not enabled(cp)


@pytest.mark.parametrize('mutation', ['stock', 'no_pedal', 'wrong_word', 'unknown_bits', 'passive'])
def test_unqualified_configuration_cannot_remap(mutation):
  cp = params(CAR.CHEVROLET_BOLT_CC_2018_2021, pedal=mutation != 'no_pedal', camera=True)
  if mutation == 'stock':
    cp.openpilotLongitudinalControl = False
  elif mutation == 'wrong_word':
    cp.safetyConfigs[0].safetyParam = 0
  elif mutation == 'passive':
    cp.passive = True
  cp.alternativeExperience = 96 | (1 if mutation == 'unknown_bits' else 0)
  assert not valid_alternative_experience(cp)
  assert not enabled(cp)


def test_assignment_migration_keeps_explicit_values_and_runs_once():
  from tempfile import TemporaryDirectory
  from openpilot.common.params import Params
  from opendbc.car.gm.cancel_remap import migrate_assignments
  cp = params(CAR.CHEVROLET_BOLT_CC_2018_2021, pedal=True, camera=True)
  prepare(cp, True)
  with TemporaryDirectory() as directory:
    saved = Params(directory)
    saved.put('CancelButtonControl', 8, block=True)
    saved.put('LongDistanceButtonControl', 3, block=True)
    assert migrate_assignments(saved, cp)
    assert saved.get('CancelButtonControl') == 8
    assert saved.get('LongCancelButtonControl') == 3
    assert saved.get('VeryLongCancelButtonControl') == 6
    saved.put('LongDistanceButtonControl', 4, block=True)
    assert not migrate_assignments(saved, cp)
    assert saved.get('LongCancelButtonControl') == 3


@pytest.mark.parametrize('remap', [False, True])
def test_cancel_experimental_assignment_does_not_invalidate_unrelated_map_for_exact_owner(remap):
  from tempfile import TemporaryDirectory
  from openpilot.common.params import Params
  from openpilot.starpilot.conditional_mode.manual import read_button_map
  from openpilot.starpilot.conditional_mode.button_actions import capture_sources, runtime_map_ready
  cp = params(CAR.CHEVROLET_BOLT_CC_2018_2021, pedal=True, camera=True)
  cp.alternativeExperience = 32
  prepare(cp, remap)
  with TemporaryDirectory() as directory:
    saved = Params(directory)
    saved.put('LongCancelButtonControl', 5, block=True)
    assert read_button_map(saved) is None
    assert (read_button_map(saved, cp=cp) is not None) is remap
    sources = capture_sources(saved, None, None)
    assert not runtime_map_ready(sources)
    assert runtime_map_ready(sources, cp=cp) is remap
