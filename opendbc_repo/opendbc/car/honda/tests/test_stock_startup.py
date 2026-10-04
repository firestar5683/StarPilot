import gc
import time

import pytest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, HondaFlags, DBC


CASES = (
  (CAR.HONDA_CIVIC_BOSCH, False, False, 0),
  (CAR.HONDA_CRV_5G, False, False, 1),
  (CAR.HONDA_CIVIC, False, False, 0),
  (CAR.HONDA_CRV, False, False, 4),
  (CAR.HONDA_ODYSSEY_TWN, False, False, 4),
  (CAR.HONDA_CIVIC_2022, False, False, 8),
  (CAR.HONDA_CIVIC_2022, True, False, 10),
  (CAR.HONDA_CIVIC_2022, True, True, 8),
  (CAR.HONDA_CIVIC_BOSCH, True, False, 2),
  (CAR.HONDA_CRV_5G, True, False, 3),
  (CAR.ACURA_RDX_3G, True, False, 131),
)
EPS_CASES = (
  (CAR.HONDA_CLARITY, b"39990-TRW,A020\x00\x00"),
  (CAR.HONDA_CIVIC, b"39990-TBA,A030\x00\x00"),
  (CAR.HONDA_ACCORD, b"39990-TVA,A150\x00\x00"),
  (CAR.HONDA_CIVIC_BOSCH, b"39990-TGG,A020\x00\x00"),
  (CAR.HONDA_CIVIC_BOSCH, b"39990-TGG,A120\x00\x00"),
  (CAR.HONDA_CRV_5G, b"39990-TLA,A040\x00\x00"),
)


def exercise_startup(identity, alpha, release, aol, base_word, monkeypatch, firmware=()):
  from opendbc.can.dbc import DBC as CANDBC
  from opendbc.car import Bus, car_helpers
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
  flags = identity.config.flags
  classic = flags & HondaFlags.BOSCH and not flags & (HondaFlags.BOSCH_RADARLESS | HondaFlags.BOSCH_CANFD)
  fingerprint = gen_empty_fingerprint()
  messages = CANDBC(DBC[identity][Bus.pt]).name_to_msg
  gear = messages.get("GEARBOX_AUTO") or messages.get("GEARBOX_CVT")
  assert gear is not None
  fingerprint[1 if classic else 0][gear.address] = gear.size
  with OpenpilotPrefix():
    saved = Params()
    for key, value in (("OpenpilotEnabledToggle", True), ("AlwaysOnLateral", aol),
                       ("AlphaLongitudinalEnabled", alpha), ("IsReleaseBranch", release)):
      saved.put_bool(key, value, block=True)

    initial = CarInterface.get_params(identity, fingerprint, list(firmware), card_module.alpha_long_requested(saved, is_release=release), release, False)
    initial.carVin = "0" * 17
    initial.carFw = list(firmware)
    assert initial.safetyConfigs[0].safetyParam == base_word
    expected = initial.to_dict()
    explicit_owner = not (classic and initial.openpilotLongitudinalControl)
    expected["alternativeExperience"] = 32 if aol and explicit_owner else 0
    if aol and not explicit_owner:
      expected["safetyConfigs"][0]["safetyParam"] = base_word | 32
    if aol and identity == CAR.HONDA_ODYSSEY_TWN:
      expected["safetyConfigs"][0]["safetyParam"] = 260
    subscriber = messaging.sub_sock("carParams", timeout=100, conflate=True)
    intent_subscriber = messaging.sub_sock("aolIntentWire", timeout=100, conflate=True)
    card = ci = controls = None
    try:
      observed = (identity, fingerprint, initial.carVin, list(firmware), initial.fingerprintSource, True)
      with monkeypatch.context() as discovery:
        discovery.setattr(car_helpers, "fingerprint", lambda *args: observed)
        discovery.setattr(card_module, "can_comm_callbacks", lambda *args: (lambda *args: [], lambda frames: None))
        initial_can = messaging.new_message("can", 1)
        discovery.setattr(card_module.messaging, "recv_one_retry", lambda socket: initial_can)
        card = Car()
      ci = card.CI
      assert card.CP.to_dict() == expected
      assert ci.CP is card.CP and ci.CC is not None
      assert card.aol_qualified is aol
      if aol:
        assert card.aol_card_intent.explicit_latch is explicit_owner
        assert not card.aol_card_intent.allowed_latch
      with structs.CarParams.from_bytes(saved.get("CarParams")) as published:
        assert published.to_dict() == expected
      assert card.aol_replay
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
      assert controls.ordinary_axis_ack_required is (aol and explicit_owner)
      now = 1_000_000_000
      feed(controls, now, 0, active=False, enabled=False, can_valid=False, can_timeout=True)
      if aol:
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
    finally:
      del controls, card, ci, subscriber, intent_subscriber
      gc.collect()


@pytest.mark.parametrize("identity,alpha,release,word", CASES)
@pytest.mark.parametrize("aol", (False, True))
def test_actual_stock_owner_card_publication_and_disabled_controls(identity, alpha, release, word, aol, monkeypatch):
  exercise_startup(identity, alpha, release, aol, word, monkeypatch)


@pytest.mark.parametrize("identity,version", EPS_CASES)
def test_known_eps_stock_owner_card_publication(identity, version, monkeypatch):
  firmware = (structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.eps, address=0x18DA30F1,
                                     subAddress=0, fwVersion=version, brand="honda"),)
  word = 1 if identity == CAR.HONDA_CRV_5G else 0
  exercise_startup(identity, False, False, True, word, monkeypatch, firmware)
