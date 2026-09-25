import gc
import os
from unittest.mock import patch

import pytest
from opendbc.car import structs
from opendbc.car.hyundai.canfd_angle_aol import MODELS, qualified, command_allowed, temporary_restriction
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.radar_interface import RadarInterface
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from openpilot.starpilot.aol.vehicle import native_latch_rejected


def source_profile(identity):
  from opendbc.car.hyundai.tests.test_angle_auto_identity import NINE, TestAngleAutoIdentity

  if identity in NINE:
    return TestAngleAutoIdentity().source_profile(identity)[0]
  if identity in (CAR.HYUNDAI_IONIQ_5_PE, CAR.KIA_EV9):
    from opendbc.car.hyundai.tests.test_ioniq5pe_stock import params

    return params(candidate=identity)
  from opendbc.car.hyundai.tests.test_ev6_2025 import params

  assert identity == CAR.KIA_EV6_2025
  return params()


@pytest.mark.parametrize('identity', sorted(MODELS))
@pytest.mark.parametrize('enabled', [False, True])
def test_actual_final_card_params_and_angle_controls(identity, enabled):
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.starpilot.aol.vehicle import policy_for
  from openpilot.selfdrive.car.card import Car
  from openpilot.selfdrive.controls.controlsd import Controls
  from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle

  with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
    saved = Params()
    saved.put_bool('OpenpilotEnabledToggle', True, block=True)
    saved.put_bool('AlwaysOnLateral', enabled, block=True)
    saved.put('MainCruiseButtonControl', 9, block=True)
    saved.put('LKASButtonControl', 9, block=True)
    cp = source_profile(CAR(identity))
    assert qualified(cp)
    word, flags, model = cp.safetyConfigs[0].safetyParam, cp.flags, cp.safetyConfigs[0].safetyModel
    before = (cp.mass, cp.wheelbase, cp.steerRatio, cp.lateralTuning.which())
    ci = CarInterface(cp)
    card = Car(CI=ci, RI=RadarInterface(cp))
    with structs.CarParams.from_bytes(saved.get('CarParams')) as published:
      assert published.pcmCruise and not published.openpilotLongitudinalControl and not published.passive
      assert published.safetyConfigs[0].safetyParam == word
      assert published.safetyConfigs[0].safetyModel == model and published.flags == flags
      assert published.alternativeExperience == (32 if enabled else 0)
      assert (published.mass, published.wheelbase, published.steerRatio, published.lateralTuning.which()) == before
      assert qualified(published, marked_only=enabled)
    controls = Controls()
    assert isinstance(controls.LaC, LatControlAngle)
    assert controls.CP.to_dict() == card.CP.to_dict()
    expected_ack = enabled or identity in (CAR.HYUNDAI_IONIQ_5_PE, CAR.KIA_EV9)
    assert controls.ordinary_axis_ack_required is expected_ack
    assert policy_for(controls.CP).full_axis_runtime_required is enabled
    subscribed = controls.aol_replay or expected_ack
    assert ('aolAxisState' in controls.sm.data) is subscribed
    assert ('aolSafetyWire' in controls.sm.data) is subscribed
    del controls, card, ci
    gc.collect()


@pytest.mark.parametrize('identity', sorted(MODELS))
def test_exact_gear_layout_long_and_profile_mutations_rejected(identity):
  cp = source_profile(CAR(identity))
  for field, value in (
    ('openpilotLongitudinalControl', True),
    ('pcmCruise', False),
    ('alternativeExperience', 64),
    ('notCar', True),
    ('passive', True),
    ('dashcamOnly', True),
  ):
    bad = cp.as_reader().as_builder()
    setattr(bad, field, value)
    assert not qualified(bad)
  bad = cp.as_reader().as_builder()
  bad.safetyConfigs[0].safetyParam ^= 0x800
  assert not qualified(bad)
  if not cp.flags & HyundaiFlags.EV:
    for flag in (HyundaiFlags.CANFD_ALT_GEARS, 0):
      bad = cp.as_reader().as_builder()
      bad.flags = (int(cp.flags) & ~int(HyundaiFlags.CANFD_ALT_GEARS_2)) | int(flag)
      assert not qualified(bad)


@pytest.mark.parametrize('identity', [CAR.HYUNDAI_IONIQ_5_PE, CAR.KIA_EV9, CAR.GENESIS_GV70_2026])
def test_known_temporary_denial_retains_intent_but_not_permission(identity):
  from openpilot.starpilot.aol.wire import SafetyState, decode_safety, encode_safety

  cp = source_profile(identity)
  cp.alternativeExperience = 32
  state = structs.CarState(canValid=True, gearShifter='drive', vEgoRaw=10, standstill=False)
  wire = decode_safety(
    encode_safety(
      SafetyState(
        protocolVersion=1,
        compatible=True,
        observedMonoTime=1,
        validUntilMonoTime=2,
        safetyModel=cp.safetyConfigs[0].safetyModel.raw,
        safetyParam=cp.safetyConfigs[0].safetyParam,
        requestedLateral=True,
        requestedLongitudinal=False,
        lateralAllowed=False,
        longitudinalAllowed=False,
        pandaSerial='angle-test',
        axisSessionId='angle-session',
      )
    )
  )
  assert command_allowed(cp, state)
  assert native_latch_rejected(cp, wire, state=state)
  for field, value in (
    ('gearShifter', structs.CarState.GearShifter.reverse),
    ('steerFaultTemporary', True),
    ('standstill', True),
    ('gasPressed', True),
    ('brakePressed', True),
  ):
    restricted = state.as_reader().as_builder()
    setattr(restricted, field, value)
    assert temporary_restriction(cp, restricted)
    assert not command_allowed(cp, restricted)
    assert not native_latch_rejected(cp, wire, state=restricted)
    restricted.canValid = False
    assert native_latch_rejected(cp, wire, state=restricted)
  assert native_latch_rejected(cp, wire, state=None)


def test_initial_acknowledgement_and_reset_during_temporary_restriction():
  from dataclasses import replace
  from openpilot.starpilot.aol.intent import AolCardIntent, AolSettings
  from openpilot.starpilot.aol.wire import SafetyState, decode_safety, encode_safety
  from opendbc.car.hyundai.canfd_angle_aol import native_observation

  cp = source_profile(CAR.HYUNDAI_IONIQ_5_PE)
  cp.alternativeExperience = 32
  pending = decode_safety(
    encode_safety(
      SafetyState(
        1, True, 20, 100, cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam, False, False, False, False, 'angle-test', 'angle-session'
      )
    )
  )
  assert native_observation(pending, latched=True, panda_ready=True, restricted=False, now_ns=10, pending_since_ns=0) == (10, False, False)
  accepted = replace(pending, requestedLateral=True, lateralAllowed=True)
  assert native_observation(accepted, latched=True, panda_ready=True, restricted=False, now_ns=20, pending_since_ns=10) == (0, False, False)
  assert native_observation(pending, latched=True, panda_ready=True, restricted=True, now_ns=30, pending_since_ns=0) == (0, False, False)
  assert native_observation(pending, latched=True, panda_ready=True, restricted=False, now_ns=40, pending_since_ns=0) == (40, False, False)
  assert native_observation(pending, latched=True, panda_ready=True, restricted=False, now_ns=200_000_040, pending_since_ns=40) == (40, False, True)
  assert native_observation(None, latched=True, panda_ready=True, restricted=True, now_ns=50, pending_since_ns=0) == (0, True, False)
  assert native_observation(accepted, latched=True, panda_ready=False, restricted=True, now_ns=50, pending_since_ns=0) == (0, True, False)
  owner = AolCardIntent(AolSettings(True, 0.0, 9, 9, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
  owner.allowed_latch = True
  owner._last_latch_edge_ns = 10
  state = structs.CarState(canValid=True, gearShifter='reverse', vEgoRaw=0, standstill=True, brakePressed=True)
  owner.update(state, now_ns=30, native_rejection_ns=20)
  assert not owner.allowed_latch
  state.gearShifter = structs.CarState.GearShifter.drive
  state.brakePressed = False
  state.standstill = False
  state.vEgoRaw = 10
  owner.update(state, now_ns=40)
  assert not owner.allowed_latch


def test_nine_discovered_angle_profiles_keep_whole_parser_health_with_ae32():
  from opendbc.car.hyundai.tests import test_angle_auto_identity as source_inventory

  inventory = source_inventory.TestAngleAutoIdentity()
  for identity in source_inventory.NINE:
    cp, packer, frames = inventory.source_profile(identity)
    cp.alternativeExperience = 32
    assert qualified(cp, marked_only=True)
    ci = CarInterface(cp)
    for tick in range(40):
      out = ci.update([(1_000_000_000 + tick * 10_000_000, inventory.fresh_frames(packer, frames))])
    assert out.canValid
    missing = [frame for frame in frames if frame[0] != 0xEA]
    assert len(missing) < len(frames)
    for tick in range(40, 120):
      out = ci.update([(1_000_000_000 + tick * 10_000_000, inventory.fresh_frames(packer, missing))])
    assert not out.canValid
    for tick in range(120, 160):
      out = ci.update([(1_000_000_000 + tick * 10_000_000, inventory.fresh_frames(packer, frames))])
    assert out.canValid


@pytest.mark.parametrize('identity', [CAR.HYUNDAI_IONIQ_5_PE, CAR.KIA_EV9])
def test_actual_card_panda_ae0_health_cannot_admit_ae32(identity):
  from openpilot.cereal import messaging
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.selfdrive.car.card import Car

  with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
    saved = Params()
    saved.put_bool('OpenpilotEnabledToggle', True, block=True)
    saved.put_bool('AlwaysOnLateral', True, block=True)
    ci = CarInterface(source_profile(identity))
    card = Car(CI=ci, RI=RadarInterface(ci.CP))
    assert card.CP.alternativeExperience == 32
    now = 1_000_000_000
    for experience, invalid_rx, expected in ((0, False, False), (32, False, True), (32, True, False)):
      now += 100_000_000
      with patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=now), \
           patch('openpilot.selfdrive.car.card.time.clock_gettime_ns', return_value=now):
        event = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=now)
        state = event.pandaStates[0]
        state.safetyModel = card.CP.safetyConfigs[0].safetyModel
        state.safetyParam = card.CP.safetyConfigs[0].safetyParam
        state.alternativeExperience = experience
        state.safetyRxChecksInvalid = invalid_rx
        card.sm.update_msgs(now / 1e9, [event.as_reader()])
        assert card.startup_panda_configured() is expected
    del card, ci
    gc.collect()
