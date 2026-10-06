import pytest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.stock_aol import CLASSIC_BOSCH, NIDEC, RADARLESS, qualified, temporary_restriction
from opendbc.car.honda.values import CAR, HondaFlags
from openpilot.starpilot.aol.intent import AolSettings, AOL_TOGGLE
from openpilot.starpilot.car.honda.aol import policy_for, create_intent, native_accepts_cp


AUTO_188 = frozenset((CAR.ACURA_RDX, CAR.HONDA_CRV_SA, CAR.HONDA_ACCORD_9G))
IDENTITIES = tuple(sorted(CLASSIC_BOSCH | NIDEC | RADARLESS, key=str))


def final_cp(identity, alpha=False, release=False, *, hybrid=False):
  fingerprint = gen_empty_fingerprint()
  pt = 1 if identity in CLASSIC_BOSCH else 0
  address, length = (0x188, 6) if identity in AUTO_188 else (0x1A3, 8)
  fingerprint[pt][address] = length
  if hybrid:
    fingerprint[pt][0x184] = 8
  return CarInterface.get_params(identity, fingerprint, [], alpha, release, False)


@pytest.mark.parametrize("identity", IDENTITIES)
@pytest.mark.parametrize("alpha,release", ((False, False), (True, False), (True, True)))
@pytest.mark.parametrize("hybrid", (False, True))
def test_actual_factory_admission_and_marker(identity, alpha, release, hybrid):
  cp = final_cp(identity, alpha, release, hybrid=hybrid)
  assert bool(cp.flags & HondaFlags.HYBRID) == hybrid
  expected = not (identity in CLASSIC_BOSCH and cp.openpilotLongitudinalControl)
  assert qualified(cp) == expected
  if not expected:
    return
  before = cp.to_dict()
  policy = policy_for(cp)
  assert not policy.ordinary_axis_ack_required
  settings = AolSettings(True, 5.0, AOL_TOGGLE, 0, (0, 0, 0), (0, 0, 0))
  intent = create_intent(cp, settings)
  assert intent.explicit_latch
  cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
  cp.alternativeExperience |= policy.alternative_experience_addition
  assert qualified(cp, marked_only=True)
  assert policy_for(cp).ordinary_axis_ack_required
  assert cp.alternativeExperience == 32
  assert cp.safetyConfigs[0].safetyParam == (260 if identity == CAR.HONDA_ODYSSEY_TWN else before["safetyConfigs"][0]["safetyParam"])
  assert cp.openpilotLongitudinalControl == before["openpilotLongitudinalControl"]
  assert cp.pcmCruise == before["pcmCruise"]
  assert native_accepts_cp(cp, cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam)
  cp.alternativeExperience = 0
  assert not qualified(cp, marked_only=True)
  assert not native_accepts_cp(cp, cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam)


@pytest.mark.parametrize("identity", IDENTITIES)
@pytest.mark.parametrize("hybrid", (False, True))
def test_manual_unknown_namespace_and_extra_panda_denied(identity, hybrid):
  cp = final_cp(identity, hybrid=hybrid)
  cp.fingerprintSource = structs.CarParams.FingerprintSource.fixed
  assert not qualified(cp)
  cp = final_cp(identity, hybrid=hybrid)
  cp.transmissionType = structs.CarParams.TransmissionType.manual
  assert not qualified(cp)
  cp = final_cp(identity, hybrid=hybrid)
  cp.flags |= 1 << 31
  assert not qualified(cp)
  cp = final_cp(identity, hybrid=hybrid)
  cp.safetyConfigs[0].safetyParam |= 0x4000
  assert not qualified(cp)
  cp = final_cp(identity, hybrid=hybrid)
  cp.safetyConfigs = [structs.CarParams.SafetyConfig(safetyModel="noOutput"), cp.safetyConfigs[0]]
  assert not qualified(cp)


def state(pressed=None, *, available=True, gear="drive", temporary=False):
  cs = structs.CarState(canValid=True, gearShifter=gear, steerFaultTemporary=temporary)
  cs.cruiseState.available = available
  if pressed is not None:
    cs.buttonEvents = [structs.CarState.ButtonEvent(type="lkas", pressed=pressed)]
  return cs.as_reader()


def test_real_schema_loss_then_lkas_arms_once_without_toggle_off():
  cp = final_cp(CAR.HONDA_CIVIC_BOSCH)
  cp.alternativeExperience = 32
  settings = AolSettings(True, 5.0, AOL_TOGGLE, 0, (0, 0, 0), (0, 0, 0))
  intent = create_intent(cp, settings)
  intent.update(state(), now_ns=10)
  intent.update(state(True), now_ns=20)
  intent.update(state(False), now_ns=30)
  assert intent.allowed_latch
  intent.update(state(), now_ns=40, native_rejection_ns=40)
  assert not intent.allowed_latch
  intent.update(state(True), now_ns=50, native_rejection_ns=40)
  assert intent.allowed_latch
  assert not intent.pause_lateral
  intent.update(state(False), now_ns=60)
  intent.update(state(gear="reverse"), now_ns=70)
  assert intent.allowed_latch
  assert temporary_restriction(cp, state(gear="reverse"))
  intent.update(state(temporary=True), now_ns=80)
  assert intent.allowed_latch


def test_cancel_uses_saved_pause_instead_of_erasing_latch():
  cp = final_cp(CAR.HONDA_CIVIC_BOSCH)
  cp.alternativeExperience = 32
  for action in (0, 3):
    settings = AolSettings(True, 5.0, AOL_TOGGLE, 0, (0, 0, 0), (action, 0, 0))
    intent = create_intent(cp, settings)
    intent.update(state(), now_ns=10)
    intent.update(state(True), now_ns=20)
    intent.update(state(False), now_ns=30)
    cs = structs.CarState(**state().to_dict())
    cs.buttonEvents = [structs.CarState.ButtonEvent(type="cancel", pressed=True)]
    intent.update(cs.as_reader(), now_ns=40)
    cs.buttonEvents = [structs.CarState.ButtonEvent(type="cancel", pressed=False)]
    intent.update(cs.as_reader(), now_ns=50)
    assert intent.allowed_latch
    assert intent.pause_lateral == (action == 3)


@pytest.mark.parametrize("lkas_action,main_action", ((0, 0), (0, AOL_TOGGLE), (AOL_TOGGLE, 0), (3, 4)))
def test_configured_button_ownership_and_default_main_pulse(lkas_action, main_action):
  cp = final_cp(CAR.HONDA_CIVIC_BOSCH)
  cp.alternativeExperience = 32
  settings = AolSettings(True, 5.0, lkas_action, main_action, (0, 0, 0), (0, 0, 0))
  intent = create_intent(cp, settings)
  intent.update(state(available=False), now_ns=10)
  intent.update(state(), now_ns=20)
  intent.update(state(), now_ns=30)
  automatic = lkas_action != AOL_TOGGLE and main_action != AOL_TOGGLE
  assert intent.allowed_latch == automatic
  assert not intent._main_held
  if automatic:
    intent.allowed_latch = False
  for button, action in (("mainCruise", main_action), ("lkas", lkas_action)):
    cs = structs.CarState(**state().to_dict())
    cs.buttonEvents = [structs.CarState.ButtonEvent(type=button, pressed=True)]
    intent.update(cs.as_reader(), now_ns=40)
    assert intent.allowed_latch == (action == AOL_TOGGLE)
    if action == 3:
      assert intent.pause_lateral
    if action == 4:
      assert intent.pause_longitudinal
    cs.buttonEvents = [structs.CarState.ButtonEvent(type=button, pressed=False)]
    intent.update(cs.as_reader(), now_ns=50)
    intent.allowed_latch = False
    intent.pause_lateral = False
