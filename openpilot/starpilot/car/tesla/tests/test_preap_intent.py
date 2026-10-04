from opendbc.car import structs
from openpilot.starpilot.aol.intent import AolSettings
from openpilot.starpilot.car.tesla.stock_intent import TeslaPreapCardIntent


def state(*, button=None, pressed=False, **changes):
  result = structs.CarState(canValid=True, gearShifter=structs.CarState.GearShifter.drive,
                            cruiseState={"available": False, "enabled": False})
  if button is not None:
    result.buttonEvents = [structs.CarState.ButtonEvent(type=button, pressed=pressed)]
  for key, value in changes.items():
    setattr(result, key, value)
  return result.as_reader()


def owner():
  return TeslaPreapCardIntent(None, AolSettings(False, 0., 0, 0, (0, 0, 0), (0, 0, 0)))


def pull(intent, tick):
  intent.update(state(button=structs.CarState.ButtonEvent.Type.setCruise, pressed=True), now_ns=tick)


def test_global_off_physical_pull_arms_once_without_claiming_stock_engagement():
  intent = owner()
  intent.update(state(), now_ns=1)
  source = state(button=structs.CarState.ButtonEvent.Type.setCruise, pressed=True)
  intent.update(source, now_ns=2)
  assert intent.allowed_latch and intent.output(source)[0]
  assert not source.cruiseState.enabled
  assert source.buttonEvents[0].type == structs.CarState.ButtonEvent.Type.setCruise
  intent.update(state(button=structs.CarState.ButtonEvent.Type.setCruise), now_ns=3)
  pull(intent, 4)
  assert intent.allowed_latch


def test_cold_held_or_stock_enabled_does_not_arm_without_fresh_pull():
  intent = owner()
  pull(intent, 1)
  assert not intent.allowed_latch
  steady = state()
  builder = steady.as_builder()
  builder.cruiseState.enabled = True
  intent.update(builder.as_reader(), now_ns=2)
  assert not intent.allowed_latch
  intent.update(state(button=structs.CarState.ButtonEvent.Type.setCruise), now_ns=3)
  pull(intent, 4)
  assert intent.allowed_latch


def test_cancel_and_permanent_fault_require_new_pull():
  intent = owner()
  intent.update(state(), now_ns=1)
  pull(intent, 2)
  intent.update(state(button=structs.CarState.ButtonEvent.Type.cancel, pressed=True), now_ns=3)
  assert not intent.allowed_latch
  intent.update(state(button=structs.CarState.ButtonEvent.Type.setCruise), now_ns=4)
  assert not intent.allowed_latch
  pull(intent, 5)
  assert intent.allowed_latch
  intent.update(state(steerFaultPermanent=True), now_ns=6)
  assert not intent.allowed_latch
  intent.update(state(), now_ns=7, fault_active=False)
  assert not intent.allowed_latch
  intent.update(state(button=structs.CarState.ButtonEvent.Type.setCruise), now_ns=8)
  pull(intent, 9)
  assert intent.allowed_latch


def test_owner_refresh_preserves_physical_contract_without_mutating_saved_settings():
  saved = AolSettings(False, 0., 9, 9, (0, 0, 0), (0, 0, 0))
  intent = owner()
  intent.settings = saved
  assert saved.enabled is False and saved.main_action == 9 and saved.lkas_action == 9
  assert intent.settings.enabled and intent.settings.main_action == 0 and intent.settings.lkas_action == 0
  intent.update(state(), now_ns=1)
  pull(intent, 2)
  assert intent.output(state())[0]
