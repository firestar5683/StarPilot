import gc
import time

import pytest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.hyundai.classic_scc_aol import qualified, aol_word
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR
from openpilot.selfdrive.car.card import alpha_long_requested
from openpilot.starpilot.aol.intent import AOL_TOGGLE


@pytest.mark.parametrize('aol', (False, True))
@pytest.mark.parametrize('lda', (False, True))
def test_actual_nexo_card_publication_and_disabled_loop(aol, lda, monkeypatch):
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
      ('AlphaLongitudinalEnabled', False),
      ('IsReleaseBranch', False),
      ('DisableOpenpilotLongitudinal', False),
      ('AlwaysOnLateral', aol),
    ):
      saved.put_bool(key, value, block=True)
    saved.put('LKASButtonControl', AOL_TOGGLE, block=True)
    saved.put('MainCruiseButtonControl', AOL_TOGGLE, block=True)
    fingerprint = gen_empty_fingerprint()
    if lda:
      fingerprint[0][0x391] = 8
    requested = alpha_long_requested(saved, is_release=saved.get_bool('IsReleaseBranch'))
    cp = CarInterface.get_params(CAR.HYUNDAI_NEXO_1ST_GEN, fingerprint, [], requested, False, False)
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


@pytest.mark.parametrize('lda', (False, True))
def test_nexo_alpha_long_does_not_admit_stock_or_long_aol(lda):
  from opendbc.car.hyundai.classic_long_aol import qualified as long_qualified
  from openpilot.starpilot.car.hyundai.aol import native_profile_supported, policy_for

  fingerprint = gen_empty_fingerprint()
  if lda:
    fingerprint[0][0x391] = 8
  cp = CarInterface.get_params(CAR.HYUNDAI_NEXO_1ST_GEN, fingerprint, [], True, False, False)
  assert cp.openpilotLongitudinalControl and not cp.pcmCruise
  assert cp.safetyConfigs[0].safetyParam == 0x0104
  assert not qualified(cp)
  assert not long_qualified(cp)
  assert not policy_for(cp).intent_supported
  assert not native_profile_supported(int(cp.safetyConfigs[0].safetyModel.raw), 0x0504)
  assert not native_profile_supported(int(cp.safetyConfigs[0].safetyModel.raw), 0x0D04)
