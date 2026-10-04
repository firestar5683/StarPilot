import gc
import time

import pytest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.values import CAR
from opendbc.car.tesla.fingerprints import FINGERPRINTS


CARS = (CAR.TESLA_MODEL_S_PREAP,)


def exercise_startup(identity, alpha, release, aol, monkeypatch, mapping=(0, 0), probe=None):
  from opendbc.car import car_helpers
  from openpilot.cereal import messaging
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.selfdrive.car import card as card_module
  from openpilot.selfdrive.car.card import Car
  from openpilot.selfdrive.controls.controlsd import Controls
  from openpilot.starpilot.aol.runtime import current_native
  from openpilot.starpilot.aol.wire import SafetyState, encode_safety, decode_intent
  from openpilot.starpilot.lateral.tests.test_lane_runtime import feed

  monkeypatch.setenv("SIMULATION", "1")
  monkeypatch.setenv("REPLAY", "1")
  monkeypatch.setenv("AOL_REPLAY_RUNTIME", "1")
  fingerprint = gen_empty_fingerprint()
  fingerprint[0] = dict(FINGERPRINTS[identity][0])
  with OpenpilotPrefix():
    saved = Params()
    for key, value in (("OpenpilotEnabledToggle", True), ("AlwaysOnLateral", aol),
                       ("AlphaLongitudinalEnabled", alpha), ("IsReleaseBranch", release)):
      saved.put_bool(key, value, block=True)
    saved.put("MainCruiseButtonControl", mapping[0], block=True)
    saved.put("LKASButtonControl", mapping[1], block=True)
    if probe is not None:
      saved.put("CancelButtonControl", 3, block=True)

    initial = CarInterface.get_params(identity, fingerprint, [], card_module.alpha_long_requested(saved, is_release=release), release, False)
    initial.carVin = "0" * 17
    initial.carFw = []
    assert initial.safetyConfigs[0].safetyParam == 0
    expected = initial.to_dict()
    explicit_owner = True
    assert not initial.openpilotLongitudinalControl and initial.pcmCruise and not initial.dashcamOnly
    expected["alternativeExperience"] = 32
    subscriber = messaging.sub_sock("carParams", timeout=100, conflate=True)
    intent_subscriber = messaging.sub_sock("aolIntentWire", timeout=100, conflate=True)
    card = ci = controls = None
    try:
      observed = (identity, fingerprint, initial.carVin, [], initial.fingerprintSource, True)
      with monkeypatch.context() as discovery:
        discovery.setattr(car_helpers, "fingerprint", lambda *args: observed)
        discovery.setattr(card_module, "can_comm_callbacks", lambda *args: (lambda *args: [], lambda frames: None))
        initial_can = messaging.new_message("can", 1)
        discovery.setattr(card_module.messaging, "recv_one_retry", lambda socket: initial_can)
        card = Car()
      ci = card.CI
      assert card.CP.to_dict() == expected
      assert ci.CP is card.CP and ci.CC is not None
      from openpilot.starpilot.car.tesla.aol import policy_for
      assert policy_for(card.CP).fixed_cruise_buttons
      assert card.aol_qualified
      assert int(card.CP.safetyConfigs[0].safetyModel.raw) == 39
      assert card.aol_card_intent.explicit_latch is explicit_owner
      assert not card.aol_card_intent.allowed_latch
      assert card.aol_card_intent.settings.main_action == 0
      assert card.aol_card_intent.settings.lkas_action == 0
      with structs.CarParams.from_bytes(saved.get("CarParams")) as published:
        assert published.to_dict() == expected
      assert card.aol_replay

      class OneIteration:
        calls = 0

        def is_set(self):
          self.calls += 1
          return self.calls > 1

      with monkeypatch.context() as refresh:
        refresh.setattr(card_module.time, "sleep", lambda seconds: None)
        card.params_thread(OneIteration())
      assert card.aol_card_intent.settings.enabled
      assert card.aol_card_intent.settings.main_action == 0
      assert card.aol_card_intent.settings.lkas_action == 0
      assert saved.get_bool("AlwaysOnLateral") is aol
      event = intent_event = None
      for _ in range(10):
        card.car_params_published = False
        card.state_publish(ci.update([]), None)
        event = messaging.recv_one(subscriber) or event
        intent_event = messaging.recv_one(intent_subscriber) or intent_event
        if event is not None and intent_event is not None:
          break
        time.sleep(0.01)
      assert event is not None and event.valid and event.carParams.to_dict() == expected
      assert intent_event is not None
      intent = decode_intent(intent_event.aolIntentWire)
      assert intent is not None and not intent.allowedLatch and not intent.lateralArmed
      assert intent.producerSessionId == card.slc_producer_session
      controls = Controls()
      assert controls.CP.to_dict() == expected
      assert controls.ordinary_axis_ack_required
      now = 1_000_000_000
      feed(controls, now, 0, active=False, enabled=False, can_valid=False, can_timeout=True)
      receipt = messaging.new_message("aolSafetyWire", 0, valid=True, logMonoTime=now)
      receipt.aolSafetyWire = encode_safety(SafetyState(
        1, True, now, now + 200_000_000, int(card.CP.safetyConfigs[0].safetyModel.raw),
        card.CP.safetyConfigs[0].safetyParam, False, False, False, False, "fixture-panda", card.slc_producer_session))
      controls.sm.update_msgs(now / 1e9, [receipt.as_reader()])
      native = current_native(controls.sm, controls.CP, now_ns=now, axis_session_id=card.slc_producer_session)
      assert native is not None and not native.lateralAllowed and not native.requestedLateral
      assert current_native(controls.sm, controls.CP, now_ns=now, axis_session_id="different-session") is None
      command, lateral_log = controls.state_control()
      assert not command.enabled and not command.latActive and not command.longActive
      controls.publish(command, lateral_log)
      ci.apply(command.as_reader(), now)
      if probe is not None:
        probe(card, ci, controls, saved)
    finally:
      del controls, card, ci, subscriber, intent_subscriber
      gc.collect()


@pytest.mark.parametrize("release", (False, True))
@pytest.mark.parametrize("aol", (False, True))
def test_actual_default_physical_stalk_owner_card_publication_and_disabled_controls(release, aol, monkeypatch):
  exercise_startup(CAR.TESLA_MODEL_S_PREAP, False, release, aol, monkeypatch)


def test_old_safety35_cache_is_not_a_current_preap_owner():
  from opendbc.car.tesla.preap.aol import qualified
  from openpilot.starpilot.car.tesla.aol import policy_for
  fingerprint = gen_empty_fingerprint()
  fingerprint[0] = dict(FINGERPRINTS[CAR.TESLA_MODEL_S_PREAP][0])
  cp = CarInterface.get_params(CAR.TESLA_MODEL_S_PREAP, fingerprint, [], False, False, False)
  assert int(cp.safetyConfigs[0].safetyModel.raw) == 39
  cp.safetyConfigs[0].safetyModel = structs.CarParams.SafetyModel.byd
  cp.alternativeExperience = 32
  with structs.CarParams.from_bytes(cp.to_bytes()) as cached:
    assert not qualified(cached)
    policy = policy_for(cached)
    assert not policy.intent_supported and not policy.physical_stalk_owner and not policy.runtime_supported
