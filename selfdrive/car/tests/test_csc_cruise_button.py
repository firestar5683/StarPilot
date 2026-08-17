import pytest

from types import SimpleNamespace

from openpilot.selfdrive.car.cruise import ButtonType, VCruiseHelper, is_csc_override_pending


def make_helper():
  CP = SimpleNamespace(carFingerprint="MOCK", flags=0, pcmCruise=False, brand="mock")
  helper = VCruiseHelper(CP)
  helper.v_cruise_kph = 40.0
  return helper


def make_toggles():
  return SimpleNamespace(cruise_increase=1.0, cruise_increase_long=5.0, reverse_cruise_increase=False)


def make_cs(button_events):
  return SimpleNamespace(
    buttonEvents=button_events,
    cruiseState=SimpleNamespace(available=True, standstill=False, speed=0, speedCluster=0),
    gasPressed=False,
    vEgo=20.0,
  )


def press(button):
  return SimpleNamespace(type=SimpleNamespace(raw=button), pressed=True)


def release(button):
  return SimpleNamespace(type=SimpleNamespace(raw=button), pressed=False)


def press_and_release(helper, button, csc_active):
  toggles = make_toggles()
  helper.update_v_cruise(make_cs([press(button)]), True, True, False, toggles, None, csc_active=csc_active)
  helper.update_v_cruise(make_cs([release(button)]), True, True, False, toggles, None, csc_active=csc_active)


def test_accel_press_consumed_while_csc_active():
  helper = make_helper()

  press_and_release(helper, ButtonType.accelCruise, csc_active=True)

  assert helper.v_cruise_kph == pytest.approx(40.0)


def test_accel_press_adjusts_set_speed_when_csc_inactive():
  helper = make_helper()

  press_and_release(helper, ButtonType.accelCruise, csc_active=False)

  assert helper.v_cruise_kph > 40.0


def test_decel_press_still_works_while_csc_active():
  helper = make_helper()

  press_and_release(helper, ButtonType.decelCruise, csc_active=True)

  assert helper.v_cruise_kph < 40.0


def test_csc_override_pending_defers_to_slc_confirmation():
  active_plan = SimpleNamespace(cscControllingSpeed=True, speedLimitChanged=False, unconfirmedSlcSpeedLimit=0)
  assert is_csc_override_pending(active_plan)

  idle_plan = SimpleNamespace(cscControllingSpeed=False, speedLimitChanged=False, unconfirmedSlcSpeedLimit=0)
  assert not is_csc_override_pending(idle_plan)

  slc_pending_plan = SimpleNamespace(cscControllingSpeed=True, speedLimitChanged=True, unconfirmedSlcSpeedLimit=25)
  assert not is_csc_override_pending(slc_pending_plan)
