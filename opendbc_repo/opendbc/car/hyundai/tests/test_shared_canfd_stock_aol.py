"""Typed CAN FD topology and startup ownership contracts for shared AOL."""

from unittest.mock import patch

import pytest
from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.hyundai.canfd_stock_aol import qualified, STOCK_AOL_WORDS
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from openpilot.starpilot.car.hyundai.aol import policy_for, native_accepts_cp


@pytest.mark.parametrize('identity', [CAR.HYUNDAI_IONIQ_5, CAR.HYUNDAI_KONA_EV_2ND_GEN])
@pytest.mark.parametrize('topology', ['hda1_standard', 'hda1_alternate', 'hda2_standard', 'hda2_alternate'])
def test_actual_typed_factory_binds_stock_word(identity, topology):
  fp = gen_empty_fingerprint()
  hda2 = topology.startswith('hda2')
  if hda2:
    fp[2].update({0x110: 32, 0x362: 32} if topology == 'hda2_alternate' else {0x50: 16, 0x2A4: 24})
  if topology != 'hda1_alternate':
    fp[1 if hda2 else 0][0x1CF] = 8
  else:
    fp[0][0x1AA] = 16
  cp = CarInterface.get_params(identity, fp, [], False, False, False)
  assert qualified(cp)
  policy = policy_for(cp)
  assert policy.explicit_latch and policy.safety_param_addition == 0x800
  cp.safetyConfigs[0].safetyParam |= 0x800
  assert int(cp.safetyConfigs[0].safetyParam) in STOCK_AOL_WORDS
  assert native_accepts_cp(cp, cp.safetyConfigs[0].safetyModel.raw, int(cp.safetyConfigs[0].safetyParam))


@pytest.mark.parametrize('identity', [CAR.HYUNDAI_IONIQ_5, CAR.HYUNDAI_KONA_EV_2ND_GEN])
def test_fuel_identity_mismatch_is_not_a_different_native_profile(identity):
  fp = gen_empty_fingerprint()
  fp[0][0x1CF] = 8
  cp = CarInterface.get_params(identity, fp, [], False, False, False)
  assert qualified(cp)
  cp.flags = int(cp.flags) & ~int(HyundaiFlags.EV)
  cp.safetyConfigs[0].safetyParam = int(cp.safetyConfigs[0].safetyParam) & ~1
  assert not qualified(cp)


def test_ioniq6_keeps_its_separate_namespace_and_policy():
  fp = gen_empty_fingerprint()
  fp[2][0x50] = 16
  fp[1][0x1CF] = 8
  fp[0][0x3A5] = 24
  cp = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fp, [], False, False, False)
  assert not qualified(cp)
  assert policy_for(cp).safety_param_addition == 0x800


@pytest.mark.parametrize('identity,fuel', [(CAR.HYUNDAI_SONATA_2024, 0), (CAR.KIA_SPORTAGE_5TH_GEN, 2), (CAR.HYUNDAI_IONIQ_5, 1)])
@pytest.mark.parametrize('alternate', [False, True])
def test_stock_hda1_factory_fuel_and_button_source(identity, fuel, alternate):
  fp = gen_empty_fingerprint()
  fp[0][0x1AA if alternate else 0x1CF] = 16 if alternate else 8
  if fuel == 2:
    fp[0][0xFA] = 8
  cp = CarInterface.get_params(identity, fp, [], False, False, False)
  assert qualified(cp)
  raw = int(cp.safetyConfigs[0].safetyParam)
  assert raw & 3 == fuel
  assert bool(cp.flags & HyundaiFlags.CANFD_ALT_BUTTONS) == alternate
  cp.safetyConfigs[0].safetyParam = raw | 0x800
  assert qualified(cp, marked_only=True)
  assert native_accepts_cp(cp, cp.safetyConfigs[0].safetyModel.raw, raw | 0x800)


def test_static_angle_identity_cannot_alias_torque_admission():
  fp = gen_empty_fingerprint()
  fp[2].update({0x110: 32, 0x362: 32})
  fp[1][0x1CF] = 8
  cp = CarInterface.get_params(CAR.HYUNDAI_IONIQ_5_PE, fp, [], False, False, False)
  cp.steerControlType = structs.CarParams.SteerControlType.torque
  cp.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEER_MSG | HyundaiFlags.CANFD_LKA_STEER_MSG_ALT)
  cp.safetyConfigs[0].safetyParam = 0x891
  assert not qualified(cp)
  assert not policy_for(cp).explicit_latch


FACTORY_CASES = tuple(
  (identity, topology, 1)
  for identity in (CAR.HYUNDAI_IONIQ_5, CAR.HYUNDAI_KONA_EV_2ND_GEN)
  for topology in ('hda1_standard', 'hda1_alternate', 'hda2_standard', 'hda2_alternate')
) + tuple(
  (identity, 'hda1_alternate' if alternate else 'hda1_standard', fuel)
  for identity, fuel in ((CAR.HYUNDAI_SONATA_2024, 0), (CAR.KIA_SPORTAGE_5TH_GEN, 2), (CAR.HYUNDAI_IONIQ_5, 1))
  for alternate in (False, True)
)


@pytest.mark.parametrize('identity,topology,fuel', FACTORY_CASES)
@pytest.mark.parametrize('enabled', [False, True])
def test_actual_stock_card_publication_and_controls(identity, topology, fuel, enabled):
  import gc
  import os
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.selfdrive.car.card import Car
  from openpilot.selfdrive.controls.controlsd import Controls
  from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
  from opendbc.car.hyundai.radar_interface import RadarInterface

  fp = gen_empty_fingerprint()
  hda2 = topology.startswith('hda2')
  if hda2:
    fp[2].update({0x110: 32, 0x362: 32} if topology == 'hda2_alternate' else {0x50: 16, 0x2A4: 24})
  fp[1 if hda2 else 0][0x1AA if topology == 'hda1_alternate' else 0x1CF] = 16 if topology == 'hda1_alternate' else 8
  if fuel == 2:
    fp[0][0xFA] = 8
  with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
    saved = Params()
    saved.put_bool('OpenpilotEnabledToggle', True, block=True)
    saved.put_bool('AlwaysOnLateral', enabled, block=True)
    saved.put('MainCruiseButtonControl', 9, block=True)
    saved.put('LKASButtonControl', 9, block=True)
    cp = CarInterface.get_params(identity, fp, [], False, False, False)
    assert qualified(cp)
    original_word = int(cp.safetyConfigs[0].safetyParam)
    original_flags = cp.flags
    ci = CarInterface(cp)
    card = Car(CI=ci, RI=RadarInterface(cp))
    with structs.CarParams.from_bytes(saved.get('CarParams')) as published:
      assert published.pcmCruise and not published.openpilotLongitudinalControl and not published.passive
      assert published.safetyConfigs[0].safetyParam == original_word | (0x800 if enabled else 0)
      assert published.alternativeExperience == 0
      assert published.flags == original_flags
      assert qualified(published, marked_only=enabled)
      assert published.carFingerprint == identity
    controls = Controls()
    assert controls.CP.to_dict() == card.CP.to_dict()
    assert isinstance(controls.LaC, LatControlTorque)
    assert card.aol_qualified == enabled
    del controls, card, ci
    gc.collect()


@pytest.mark.parametrize('identity', [CAR.KIA_EV6, CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN])
def test_existing_stock_startup_profiles_update_without_duplicate_units_source(identity):
  from opendbc.can import CANPacker

  fp = gen_empty_fingerprint()
  fp[2].update({0x50: 16, 0x2A4: 24})
  fp[1][0x1CF] = 8
  cp = CarInterface.get_params(identity, fp, [], False, False, False)
  assert qualified(cp)
  cp.safetyConfigs[0].safetyParam |= 0x800
  ci = CarInterface(cp)
  packer = CANPacker('hyundai_canfd_generated')
  drive = next(code for code, label in ci.CS.shifter_values.items() if label == 'D')
  inventory = [
    ('ACCELERATOR', 1),
    ('TCS', 1),
    ('WHEEL_SPEEDS', 1),
    ('MDPS', 1),
    ('STEERING_SENSORS', 1),
    ('DOORS_SEATBELTS', 1),
    ('BLINKERS', 1),
    ('GEAR_ALT_2', 1),
    ('CRUISE_BUTTONS', 1),
    ('SCC_CONTROL', 1),
    ('CAM_0x2a4', 2),
    ('MANUAL_SPEED_LIMIT_ASSIST', 1),
  ]
  assert all(name != 'CRUISE_BUTTONS_ALT' for name, _ in inventory)
  for tick in range(40):
    frames = []
    for name, bus in inventory:
      values = {'COUNTER': tick % (16 if name == 'CRUISE_BUTTONS' else 256)}
      if name == 'GEAR_ALT_2':
        values['GEAR'] = drive
      elif name == 'DOORS_SEATBELTS':
        values['DRIVER_SEATBELT'] = 1
      elif name == 'WHEEL_SPEEDS':
        values.update(WHL_SpdFLVal=72, WHL_SpdFRVal=72, WHL_SpdRLVal=72, WHL_SpdRRVal=72)
      frames.append(packer.make_can_msg(name, bus, values))
    state = ci.update([(1_000_000_000 + tick * 10_000_000, frames)])
  assert state.canValid and not state.canTimeout
