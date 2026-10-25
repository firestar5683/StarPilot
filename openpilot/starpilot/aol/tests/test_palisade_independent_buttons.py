"""Mapped Palisade HDA2 intent; no CAN sends or native authority changes."""
from dataclasses import replace

import pytest
from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR
from opendbc.car.hyundai.blended_longitudinal import candidate_from_stock
from openpilot.starpilot.aol.intent import AolSettings
from openpilot.starpilot.car.hyundai.aol import create_intent, independent_cruise_buttons_supported, policy_for

SETTINGS = AolSettings(True, 0., 9, 0, (0, 0, 0), (0, 0, 0))


def profile(*, alpha=False, hda2=True, marked=True):
  fp = gen_empty_fingerprint()
  if hda2:
    fp[2][0x50] = 16
  fp[int(hda2)][0x391] = 8
  cp = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, fp, [], False, False, False)
  if alpha:
    cp = candidate_from_stock(cp, alpha_requested=True, native_qualified=True)
    assert cp is not None
  cp.alternativeExperience = 32 if marked else 0
  return cp


@pytest.mark.parametrize('alpha', [False, True])
@pytest.mark.parametrize('marked', [False, True])
def test_exact_hda2_profiles_select_independent_intent_without_mutating_cp(alpha, marked):
  cp = profile(alpha=alpha, marked=marked)
  before = cp.to_dict()
  assert independent_cruise_buttons_supported(cp)
  assert independent_cruise_buttons_supported(cp, marked_only=True) == marked
  policy = policy_for(cp)
  assert policy.explicit_latch and not policy.cruise_main_required
  if alpha:
    assert policy.ordinary_axis_ack_required == marked
    assert policy.full_axis_runtime_required == marked
  assert cp.to_dict() == before


@pytest.mark.parametrize('alpha', [False, True])
def test_lkas_toggles_with_main_off_and_unmapped_main_does_not_toggle(alpha):
  owner = create_intent(profile(alpha=alpha), SETTINGS)
  state = structs.CarState(canValid=True, gearShifter='drive')
  owner.update(state, now_ns=1, fault_active=False)
  assert not owner.allowed_latch
  state.buttonEvents = [structs.CarState.ButtonEvent(type='lkas', pressed=True)]
  owner.update(state, now_ns=2, fault_active=False)
  assert owner.allowed_latch
  state.buttonEvents = [structs.CarState.ButtonEvent(type='lkas', pressed=False)]
  owner.update(state, now_ns=3, fault_active=False)
  state.buttonEvents = [structs.CarState.ButtonEvent(type='mainCruise', pressed=True)]
  owner.update(state, now_ns=4, fault_active=False)
  assert owner.allowed_latch
  state.buttonEvents = [structs.CarState.ButtonEvent(type='mainCruise', pressed=False)]
  owner.update(state, now_ns=5, fault_active=False)
  state.buttonEvents = [structs.CarState.ButtonEvent(type='lkas', pressed=True)]
  owner.update(state, now_ns=6, fault_active=False)
  assert not owner.allowed_latch
  assert not state.cruiseState.available and not state.cruiseState.enabled


@pytest.mark.parametrize('alpha', [False, True])
def test_disabled_settings_and_acc_fault_cannot_arm(alpha):
  for settings, fault in ((replace(SETTINGS, enabled=False), False), (SETTINGS, True)):
    owner = create_intent(profile(alpha=alpha), settings)
    state = structs.CarState(canValid=True, gearShifter='drive', accFaulted=fault)
    owner.update(state, now_ns=1, fault_active=False)
    state.buttonEvents = [structs.CarState.ButtonEvent(type='lkas', pressed=True)]
    owner.update(state, now_ns=2, fault_active=False)
    assert not owner.allowed_latch


@pytest.mark.parametrize('alpha', [False, True])
@pytest.mark.parametrize('invalid', ['hda1', 'passive', 'notCar', 'dashcamOnly', 'word', 'marker'])
def test_nearby_profiles_do_not_gain_independent_buttons(alpha, invalid):
  cp = profile(alpha=alpha, hda2=invalid != 'hda1')
  if invalid in ('passive', 'notCar', 'dashcamOnly'):
    setattr(cp, invalid, True)
  elif invalid == 'word':
    cp.safetyConfigs[0].safetyParam ^= 0x10
  elif invalid == 'marker':
    cp.alternativeExperience = 64
  assert not independent_cruise_buttons_supported(cp)
  if invalid == 'hda1':
    assert policy_for(cp).cruise_main_required

