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


@pytest.mark.parametrize('identity', (CAR.GENESIS_G80, CAR.KIA_XCEED_PHEV))
@pytest.mark.parametrize('lda', (False, True))
def test_prepared_legacy_candidate_exact_axis_contract(identity, lda):
  from opendbc.car.hyundai.legacy_long_aol import candidate, ordinary_word
  cp = candidate(params(identity, lda=lda), requested=True)
  assert cp is not None and qualified(cp)
  before = cp.to_dict()
  policy = policy_for(cp)
  cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
  cp.alternativeExperience = policy.alternative_experience_addition
  assert qualified(cp, marked_only=True)
  assert native_accepts(cp, int(cp.safetyConfigs[0].safetyModel.raw), aol_word(cp))
  assert cp.safetyConfigs[0].safetyParam == ordinary_word(cp) + 2
  assert cp.longitudinalTuning.to_dict() == before['longitudinalTuning']
  assert cp.steerActuatorDelay == before['steerActuatorDelay']
  for word in (4, 6, 0xE904, 0xE914):
    bad = cp.as_reader().as_builder()
    bad.safetyConfigs[0].safetyParam = word
    assert not qualified(bad)
  for field in ('passive', 'dashcamOnly', 'notCar', 'pcmCruise'):
    bad = cp.as_reader().as_builder()
    setattr(bad, field, True)
    assert not qualified(bad)


@pytest.mark.parametrize('identity', (CAR.GENESIS_G80, CAR.KIA_XCEED_PHEV))
@pytest.mark.parametrize('radar_available', (False, True))
def test_legacy_candidate_radar_state_and_consumed_stopping_rate(identity, radar_available):
  from opendbc.car.hyundai.legacy_long_aol import candidate, aol_word
  from openpilot.selfdrive.controls.lib.longcontrol import LongControl
  stock = params(identity)
  stock.radarUnavailable = not radar_available
  active = candidate(stock, requested=True)
  assert active is not None
  assert active.radarUnavailable == (True if identity == CAR.GENESIS_G80 else not radar_available)
  assert stock.radarUnavailable == (not radar_available)
  assert active.longitudinalTuning.to_dict() == stock.longitudinalTuning.to_dict()
  for marked in (False, True):
    cp = active.as_reader().as_builder()
    if marked:
      cp.safetyConfigs[0].safetyParam = aol_word(cp)
      cp.alternativeExperience = 32
    control = LongControl(cp)
    assert control.extension is not None
    assert control.stopping_decel_rate == 0.8
  assert LongControl(stock).stopping_decel_rate == 1.0
  malformed = active.as_reader().as_builder()
  malformed.safetyConfigs[0].safetyParam = 4
  assert LongControl(malformed).stopping_decel_rate == 1.0


@pytest.mark.parametrize('family', ('legacy', 'classic_long', 'mixed', 'mixed_alpha', 'classic', 'non_scc', 'canfd_stock', 'canfd_long', 'ioniq6', 'angle'))
@pytest.mark.parametrize('marked', (False, True))
def test_retained_marked_cp_saved_off_restarts_axis_transport(family, marked, monkeypatch):
  from opendbc.car.hyundai.legacy_long_aol import candidate
  from opendbc.car.hyundai.blended_longitudinal import candidate_from_stock
  from opendbc.car.hyundai.tests.test_blended_stock_aol import params as mixed_params
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.selfdrive.controls.controlsd import Controls
  from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
  from openpilot.starpilot.feature_runtime import enabled

  monkeypatch.setenv('SIMULATION', '1')
  monkeypatch.setenv('REPLAY', '1')
  monkeypatch.setenv('AOL_REPLAY_RUNTIME', '0')
  from openpilot.starpilot.aol.tests.test_classic_scc_profiles import params as classic_params
  from openpilot.starpilot.aol.tests.test_non_scc_profiles import params as non_scc_params
  from openpilot.starpilot.aol.tests.test_canfd_stock_profiles import params as canfd_params
  from opendbc.car.hyundai.torque_ev_startup import candidate as canfd_candidate

  from opendbc.car.hyundai.tests.test_stock_angle_aol import source_profile
  from opendbc.car.hyundai.tests.test_ioniq6_stock_parser import params as ioniq6_params

  factories = {
    'legacy': lambda: candidate(params(CAR.GENESIS_G80), requested=True),
    'classic_long': params,
    'mixed': mixed_params,
    'mixed_alpha': lambda: candidate_from_stock(mixed_params(), alpha_requested=True, native_qualified=True),
    'classic': lambda: classic_params(CAR.HYUNDAI_SONATA),
    'non_scc': lambda: non_scc_params(CAR.KIA_FORTE),
    'canfd_stock': lambda: canfd_params(CAR.KIA_EV6),
    'canfd_long': lambda: canfd_candidate(canfd_params(CAR.HYUNDAI_IONIQ_5), requested=True, is_release=False),
    'ioniq6': lambda: ioniq6_params(False)[0],
    'angle': lambda: source_profile(CAR.KIA_EV9),
  }
  cp = factories[family]()
  assert cp is not None
  if marked:
    policy = policy_for(cp)
    cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
    cp.alternativeExperience = policy.alternative_experience_addition
  with OpenpilotPrefix():
    saved = Params()
    saved.put_bool('AlwaysOnLateral', False, block=True)
    saved.put('CarParams', cp.to_bytes(), block=True)
    policy = policy_for(cp)
    assert policy.full_axis_runtime_required == marked
    assert policy.ordinary_axis_ack_required == (marked or family == 'angle')
    assert enabled(saved, cp, 'aol', {'AOL_REPLAY_RUNTIME': '0'}) == marked
    if marked:
      negatives = [('passive', True)]
      if family != 'ioniq6':
        negatives.append(('alternativeExperience', 1))
      for field, value in negatives:
        bad = cp.as_reader().as_builder()
        setattr(bad, field, value)
        assert not policy_for(bad).full_axis_runtime_required
      bad = cp.as_reader().as_builder()
      bad.safetyConfigs[0].safetyParam = 0xFFFF
      assert not policy_for(bad).full_axis_runtime_required
    controls = drive = None
    try:
      controls = Controls()
      drive = SelfdriveD(CP=cp)
      assert controls.aol_replay == marked
      assert drive.aol_replay == marked
      assert drive.axis_transport_required == (marked or family == 'angle')
      assert not saved.get_bool('AlwaysOnLateral')
      assert controls.CP.to_dict() == cp.to_dict()
    finally:
      del controls, drive
      gc.collect()
