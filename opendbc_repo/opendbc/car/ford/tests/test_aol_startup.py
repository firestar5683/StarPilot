import gc
import time

import pytest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.ford.interface import CarInterface
from opendbc.car.ford.values import CAR


PROFILES = (
  (CAR.FORD_BRONCO_SPORT_MK1, 32), (CAR.FORD_ESCAPE_MK4, 32), (CAR.FORD_FOCUS_MK4, 32),
  (CAR.FORD_MAVERICK_MK1, 32), (CAR.FORD_EXPLORER_MK6, 32),
  (CAR.FORD_MUSTANG_MACH_E_MK1, 18), (CAR.FORD_ESCAPE_MK4_5, 66),
  (CAR.FORD_EXPEDITION_MK4, 66), (CAR.FORD_F_150_MK14, 66),
  (CAR.FORD_F_150_LIGHTNING_MK1, 66), (CAR.FORD_RANGER_MK2, 66),
  (CAR.FORD_EDGE_MK2, 8), (CAR.FORD_MONDEO_MK5, 10), (CAR.FORD_TRANSIT_MK5, 12),
)


def run_startup(identity, base_word, alpha, release, topology, monkeypatch):
  from opendbc.car import car_helpers
  from opendbc.car.ford.aol import qualified
  from openpilot.cereal import messaging
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.selfdrive.car import card as card_module
  from openpilot.selfdrive.car.card import Car
  from openpilot.selfdrive.controls.controlsd import Controls
  from openpilot.starpilot.aol.vehicle import policy_for
  from openpilot.starpilot.controller_extensions import ManualTurnInputs
  from openpilot.starpilot.lateral.tests.test_lane_runtime import feed

  monkeypatch.setenv("SIMULATION", "1")
  monkeypatch.setenv("REPLAY", "1")
  monkeypatch.setenv("AOL_REPLAY_RUNTIME", "1")
  offset = 4 if topology == "multi-panda" else 0
  fingerprint = gen_empty_fingerprint()
  if topology != "manual":
    fingerprint[offset][0x5A] = 8
  fingerprint[offset + 2].update({0x3D6: 8, 0x186: 8})
  expected_long = alpha and not release
  expected_word = base_word | int(expected_long)
  initial = CarInterface.get_params(identity, fingerprint, [], expected_long, release, False)
  initial.carVin = "0" * 17
  initial.carFw = []
  admitted = topology == "automatic"
  expected = initial.to_dict()
  expected["alternativeExperience"] = 32 if admitted else 0
  assert initial.safetyConfigs[-1].safetyParam == expected_word
  assert initial.openpilotLongitudinalControl == expected_long
  assert not initial.passive and not initial.dashcamOnly
  with OpenpilotPrefix():
    saved = Params()
    for key, value in (("OpenpilotEnabledToggle", True), ("AlwaysOnLateral", True),
                       ("AlphaLongitudinalEnabled", alpha), ("IsReleaseBranch", release),
                       ("FordHumanTurnDetection", False)):
      saved.put_bool(key, value, block=True)
    observed = (identity, fingerprint, initial.carVin, [], initial.fingerprintSource, True)
    subscriber = messaging.sub_sock("carParams", timeout=100, conflate=True)
    card = ci = controls = None
    try:
      with monkeypatch.context() as discovery:
        discovery.setattr(car_helpers, "fingerprint", lambda *args: observed)
        discovery.setattr(card_module, "can_comm_callbacks", lambda *args: (lambda *args: [], lambda frames: None))
        initial_can = messaging.new_message("can", 1)
        discovery.setattr(card_module.messaging, "recv_one_retry", lambda socket: initial_can)
        card = Car()
      ci = card.CI
      assert card.CP.to_dict() == expected
      assert qualified(card.CP, marked_only=True) == admitted
      assert card.aol_qualified == admitted
      policy = policy_for(card.CP)
      assert policy.intent_supported == admitted
      assert policy.normal_runtime_supported == admitted
      assert ci.CP is card.CP
      assert ci.CC is not None
      if base_word in (18, 32, 66):
        owner = ci.CC.mache_lateral if base_word == 18 else ci.CC.classic_lateral
        assert owner is not None
        assert owner.CP is card.CP
        assert isinstance(ci.CC.manual_turn_inputs, ManualTurnInputs)
        assert not ci.CC.manual_turn_inputs.enabled
      if admitted:
        assert card.aol_card_intent is not None
        healthy = structs.CarState(canValid=True, canTimeout=False, gearShifter="drive", buttonEvents=[])
        healthy.cruiseState.available = True
        healthy.cruiseState.enabled = False
        card.aol_card_intent.update(healthy.as_reader(), now_ns=1_000_000_000)
        assert not card.aol_card_intent.allowed_latch
      else:
        assert card.aol_card_intent is None
        assert card.CP.alternativeExperience == 0
        assert card.CP.safetyConfigs[-1].safetyParam == expected_word
        if topology == "manual":
          assert card.CP.transmissionType == structs.CarParams.TransmissionType.manual
        else:
          assert len(card.CP.safetyConfigs) == 2
          assert card.CP.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.noOutput
      with structs.CarParams.from_bytes(saved.get("CarParams")) as published:
        assert published.to_dict() == expected
      event = None
      for _ in range(10):
        card.car_params_published = False
        card.state_publish(ci.update([]), None)
        event = messaging.recv_one(subscriber)
        if event is not None:
          break
        time.sleep(0.01)
      assert event is not None and event.valid and event.carParams.to_dict() == expected
      controls = Controls()
      assert controls.CP.to_dict() == expected
      feed(controls, 1_000_000_000, 0, active=False, enabled=False, can_valid=True, can_timeout=False)
      command, lateral_log = controls.state_control()
      assert not command.enabled and not command.latActive and not command.longActive
      controls.publish(command, lateral_log)
      ci.apply(command.as_reader(), 1_000_000_000)
      if base_word in (18, 32, 66):
        assert not owner.human_turn_enabled
    finally:
      del controls, card, ci, subscriber
      gc.collect()


@pytest.mark.parametrize("identity,word", PROFILES)
@pytest.mark.parametrize("alpha,release", ((False, False), (True, False), (True, True)))
def test_actual_card_aol_publication_and_disabled_controls(identity, word, alpha, release, monkeypatch):
  run_startup(identity, word, alpha, release, "automatic", monkeypatch)


@pytest.mark.parametrize("identity,word", PROFILES)
@pytest.mark.parametrize("topology", ("manual", "multi-panda"))
def test_aol_denied_topology_preserves_actual_ordinary_startup(identity, word, topology, monkeypatch):
  run_startup(identity, word, False, False, topology, monkeypatch)


@pytest.mark.parametrize("identity,word", PROFILES)
@pytest.mark.parametrize("alpha", (False, True))
def test_aol_qualifier_requires_actual_pcm_cruise_contract(identity, word, alpha):
  from opendbc.car.ford.aol import qualified
  fingerprint = gen_empty_fingerprint()
  fingerprint[0][0x5A] = 8
  fingerprint[2].update({0x3D6: 8, 0x186: 8})
  cp = CarInterface.get_params(identity, fingerprint, [], alpha, False, False)
  assert cp.pcmCruise
  assert cp.safetyConfigs[-1].safetyParam == word | int(alpha)
  assert qualified(cp)
  cp.alternativeExperience = 32
  assert qualified(cp, marked_only=True)
  cp.pcmCruise = False
  assert not qualified(cp)
  assert not qualified(cp, marked_only=True)
