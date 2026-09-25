from types import SimpleNamespace

from opendbc.car import structs, gen_empty_fingerprint
from opendbc.car.mazda.interface import CarInterface
from opendbc.car.mazda.stock_aol import native_observation, temporary_restriction
from opendbc.car.mazda.values import CAR
from openpilot.starpilot.aol.intent import AolSettings, ButtonType
from openpilot.starpilot.car.mazda.stock_intent import MazdaStockCardIntent


def armed():
  cp = CarInterface.get_params(CAR.MAZDA_CX5_2022, gen_empty_fingerprint(), [], False, False, False)
  cp.alternativeExperience = 32
  owner = MazdaStockCardIntent(cp, AolSettings(True, 0., 0, 0, (0, 0, 0), (3, 0, 0)))
  state = structs.CarState(canValid=True, vEgo=20., gearShifter=structs.CarState.GearShifter.drive)
  owner.update(state, now_ns=1_000_000_000, fault_active=False)
  state.cruiseState.available = True
  owner.update(state, now_ns=1_010_000_000, fault_active=False)
  owner.update(state, now_ns=1_020_000_000, fault_active=False)
  assert owner.allowed_latch
  return cp, owner, state


def cancel(owner, state, now):
  state.buttonEvents = [structs.CarState.ButtonEvent(type=ButtonType.cancel, pressed=True)]
  owner.update(state, now_ns=now, fault_active=False)
  state.buttonEvents = [structs.CarState.ButtonEvent(type=ButtonType.cancel, pressed=False)]
  owner.update(state, now_ns=now+10_000_000, fault_active=False)
  state.buttonEvents = []


def test_intentional_pause_keeps_physical_intent_past_ack_deadline():
  cp, owner, state = armed()
  cancel(owner, state, 1_030_000_000)
  assert owner.pause_lateral and owner.allowed_latch
  native = SimpleNamespace(requestedLateral=False, lateralAllowed=False)
  pending = 1_020_000_000
  for tick in range(60):
    now = 1_050_000_000 + tick*10_000_000
    pending, lost, rejected = native_observation(native, latched=owner.allowed_latch, panda_ready=True,
      restricted=temporary_restriction(cp, state) or owner.pause_lateral, now_ns=now, pending_since_ns=pending)
    assert pending == 0 and not lost and not rejected
    owner.update(state, now_ns=now, fault_active=lost, native_rejection_ns=now if rejected else 0)
    assert owner.allowed_latch and owner.pause_lateral
    assert owner.output(state)[1]
  cancel(owner, state, 1_700_000_000)
  assert owner.allowed_latch and not owner.pause_lateral
  pending, lost, rejected = native_observation(SimpleNamespace(requestedLateral=True, lateralAllowed=True),
    latched=True, panda_ready=True, restricted=False, now_ns=1_720_000_000, pending_since_ns=0)
  assert pending == 0 and not lost and not rejected


def test_matching_native_or_panda_loss_revokes_even_during_pause():
  for native, panda_ready in ((None, True), (SimpleNamespace(requestedLateral=False, lateralAllowed=False), False)):
    cp, owner, state = armed()
    cancel(owner, state, 1_030_000_000)
    _, lost, rejected = native_observation(native, latched=True, panda_ready=panda_ready,
      restricted=temporary_restriction(cp, state) or owner.pause_lateral, now_ns=1_500_000_000, pending_since_ns=0)
    assert lost and not rejected
    owner.update(state, now_ns=1_500_000_000, fault_active=lost)
    assert not owner.allowed_latch


def test_resume_without_native_permission_has_bounded_ack_and_cannot_rearm():
  cp, owner, state = armed()
  cancel(owner, state, 1_030_000_000)
  cancel(owner, state, 1_500_000_000)
  assert not owner.pause_lateral and owner.allowed_latch
  native = SimpleNamespace(requestedLateral=False, lateralAllowed=False)
  pending, lost, rejected = native_observation(native, latched=True, panda_ready=True,
    restricted=False, now_ns=1_520_000_000, pending_since_ns=0)
  assert pending == 1_520_000_000 and not lost and not rejected
  pending, lost, rejected = native_observation(native, latched=True, panda_ready=True,
    restricted=False, now_ns=1_720_000_000, pending_since_ns=pending)
  assert rejected and not lost
  owner.update(state, now_ns=1_720_000_000, native_rejection_ns=1_720_000_000, fault_active=False)
  assert not owner.allowed_latch
