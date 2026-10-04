import gc
import itertools
import time
from types import SimpleNamespace

import pytest

from openpilot.selfdrive.car.card import alpha_long_requested
from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.classic_long_aol import CLASSIC_LONG_IDS, qualified, aol_word, native_accepts
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from openpilot.starpilot.car.hyundai.aol import policy_for, create_intent
from openpilot.starpilot.aol.intent import AolSettings, AOL_TOGGLE


def params(identity=CAR.HYUNDAI_SONATA, *, release=False, lda=False):
  fingerprint = gen_empty_fingerprint()
  if lda:
    fingerprint[0][0x391] = 8
  request = alpha_long_requested(SimpleNamespace(get_bool=lambda key: True), is_release=release)
  return CarInterface.get_params(identity, fingerprint, [], request, release, False)


@pytest.mark.parametrize('identity', sorted(CLASSIC_LONG_IDS, key=str))
@pytest.mark.parametrize('lda', (False, True))
def test_actual_final_factory_state_and_exact_marked_configuration(identity, lda):
  cp = params(identity, lda=lda)
  if cp.dashcamOnly or cp.lateralTuning.which() != 'torque' or cp.steerControlType != structs.CarParams.SteerControlType.torque:
    assert not qualified(cp)
    return
  assert qualified(cp)
  before = cp.to_dict()
  policy = policy_for(cp)
  cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
  cp.alternativeExperience |= policy.alternative_experience_addition
  expected = dict(before)
  expected['safetyConfigs'] = [{**before['safetyConfigs'][0], 'safetyParam': aol_word(cp)}]
  expected['alternativeExperience'] = 32
  assert cp.to_dict() == expected
  assert native_accepts(cp, int(cp.safetyConfigs[0].safetyModel.raw), aol_word(cp))
  release = params(identity, release=True, lda=lda)
  assert not release.openpilotLongitudinalControl
  assert release.pcmCruise
  assert not qualified(release)


@pytest.mark.parametrize('identity', (CAR.GENESIS_G80, CAR.KIA_XCEED_PHEV, CAR.HYUNDAI_ELANTRA_2024, CAR.HYUNDAI_ELANTRA_HEV_2024))
def test_unqualified_legacy_prepared_owner_and_camera_topologies_excluded(identity):
  assert not qualified(params(identity))


def test_malformed_final_contract_never_marks_aol():
  cp = params()
  for field, value in (
    ('flags', int(cp.flags) | int(HyundaiFlags.EV)),
    ('pcmCruise', True),
    ('openpilotLongitudinalControl', False),
    ('passive', True),
    ('notCar', True),
    ('dashcamOnly', True),
    ('alternativeExperience', 1),
    ('alphaLongitudinalAvailable', False),
  ):
    bad = cp.as_reader().as_builder()
    setattr(bad, field, value)
    assert not qualified(bad)
  for word in (0x404 | 8, 0x404 | 256, 0x404 | 512, 0x404 | 4096, 0x404 | 32768, 0x407):
    bad = cp.as_reader().as_builder()
    bad.safetyConfigs[0].safetyParam = word
    assert not qualified(bad)
  bad = cp.as_reader().as_builder()
  bad.safetyConfigs[0].safetyModel = structs.CarParams.SafetyModel.hyundaiLegacy
  assert not qualified(bad)


def test_tcs_availability_without_physical_or_standard_engagement_is_not_intent():
  cp = params()
  intent = create_intent(cp, AolSettings(True, 0.0, AOL_TOGGLE, AOL_TOGGLE, (0, 0, 0), (0, 0, 0)))
  cs = structs.CarState.new_message(canValid=True, canTimeout=False, gearShifter='drive')
  cs.cruiseState.available = True
  for tick in range(20):
    intent.update(cs, fault_active=False, now_ns=1_000_000_000 + tick * 10_000_000, standard_enabled=False)
    assert not intent.allowed_latch


CARD_IDENTITIES = (CAR.HYUNDAI_SONATA, CAR.HYUNDAI_IONIQ, CAR.HYUNDAI_KONA_EV)
CARD_CASES = [
  (identity, alpha, disable, aol, False) for identity, alpha, disable, aol in itertools.product(CARD_IDENTITIES, (False, True), (False, True), (False, True))
]
CARD_CASES += [(identity, True, False, True, True) for identity in CARD_IDENTITIES]


@pytest.mark.parametrize('identity,alpha,disable,aol,release', CARD_CASES)
def test_actual_card_published_cp_controls_and_disabled_loop(identity, alpha, disable, aol, release, monkeypatch):
  from opendbc.car.hyundai.classic_scc_aol import qualified as stock_qualified, aol_word as stock_word
  from opendbc.car.hyundai.radar_interface import RadarInterface
  from opendbc.car.hyundai.values import HyundaiSafetyFlags
  from openpilot.cereal import messaging
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.selfdrive.car.card import Car
  from openpilot.selfdrive.controls.controlsd import Controls
  from openpilot.starpilot.lateral.tests.test_lane_runtime import feed

  monkeypatch.setenv('SIMULATION', '1')
  monkeypatch.setenv('REPLAY', '1')
  monkeypatch.setenv('AOL_REPLAY_RUNTIME', '0')
  with OpenpilotPrefix():
    saved = Params()
    for key, value in (
      ('OpenpilotEnabledToggle', True),
      ('AlphaLongitudinalEnabled', alpha),
      ('IsReleaseBranch', release),
      ('DisableOpenpilotLongitudinal', disable),
      ('AlwaysOnLateral', aol),
    ):
      saved.put_bool(key, value, block=True)
    saved.put('LKASButtonControl', AOL_TOGGLE, block=True)
    saved.put('MainCruiseButtonControl', AOL_TOGGLE, block=True)
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x391] = 8
    requested = alpha_long_requested(saved, is_release=saved.get_bool('IsReleaseBranch'))
    cp = CarInterface.get_params(identity, fingerprint, [], requested, release, False)
    assert cp.openpilotLongitudinalControl == requested
    assert cp.pcmCruise != requested
    assert not CarInterface.startup_required(cp)
    assert qualified(cp) if requested else stock_qualified(cp)
    before = cp.to_dict()
    subscriber = messaging.sub_sock('carParams', timeout=100, conflate=True)
    ci = card = controls = None
    try:
      ci = CarInterface(cp)
      card = Car(CI=ci, RI=RadarInterface(cp))
      expected = dict(before)
      if aol:
        expected['safetyConfigs'] = [{**before['safetyConfigs'][0], 'safetyParam': aol_word(card.CP) if requested else stock_word(card.CP)}]
        expected['alternativeExperience'] = 32
      assert card.CP.to_dict() == expected
      assert bool(card.CP.safetyConfigs[0].safetyParam & HyundaiSafetyFlags.LONG) == requested
      assert card.aol_qualified == aol
      assert card.vehicle_startup.owner is None
      with structs.CarParams.from_bytes(saved.get('CarParams')) as published:
        assert published.to_dict() == card.CP.to_dict()
      parsed = ci.update([])
      event = None
      for _ in range(10):
        card.car_params_published = False
        card.state_publish(parsed, None)
        event = messaging.recv_one(subscriber)
        if event is not None:
          break
        time.sleep(0.01)
      assert event is not None and event.which() == 'carParams' and event.valid
      assert event.carParams.to_dict() == card.CP.to_dict()
      controls = Controls()
      assert controls.CP.to_dict() == card.CP.to_dict()
      feed(controls, 1_000_000_000, 0, active=False, enabled=False, can_valid=False, can_timeout=True)
      command, lateral_log = controls.state_control()
      assert not command.enabled and not command.latActive and not command.longActive
      controls.publish(command, lateral_log)
    finally:
      del controls, card, ci, subscriber
      gc.collect()
