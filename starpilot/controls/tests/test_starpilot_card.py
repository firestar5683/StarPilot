from types import SimpleNamespace

from opendbc.car.chrysler.values import CAR as CHRYSLER_CAR

from openpilot.common.params import ParamKeyType
from openpilot.starpilot.common.favorite_slots import FAVORITE_SLOTS_PARAM
from openpilot.starpilot.controls import starpilot_card as spc


class FakeParams:
  def __init__(self, *args, **kwargs):
    self._store = {}
    self._types = {
      FAVORITE_SLOTS_PARAM: ParamKeyType.JSON,
      "RedneckCruise": ParamKeyType.BOOL,
    }

  def get(self, key):
    return self._store.get(key)

  def get_bool(self, key):
    return bool(self._store.get(key, False))

  def put_bool(self, key, value):
    self._store[key] = bool(value)

  def put(self, key, value):
    self._store[key] = value

  def get_int(self, key, default=0):
    return int(self._store.get(key, default))

  def put_int(self, key, value):
    self._store[key] = int(value)

  def put_bool_nonblocking(self, key, value):
    self.put_bool(key, value)

  def get_type(self, key):
    return self._types.get(key, ParamKeyType.STRING)


class FakeSM(dict):
  def __init__(self, *args, updated=None, **kwargs):
    super().__init__(*args, **kwargs)
    self.updated = updated or {}


def make_sm():
  return FakeSM({
    "carControl": SimpleNamespace(longActive=False),
    "selfdriveState": SimpleNamespace(active=False, alertType=[], experimentalMode=False),
    "starpilotSelfdriveState": SimpleNamespace(alertType=[]),
    "starpilotPlan": SimpleNamespace(lateralCheck=True),
    "liveCalibration": SimpleNamespace(calPerc=100),
  }, updated={"starpilotPlan": False})


def make_toggles(**overrides):
  defaults = {
    "always_on_lateral": False,
    "always_on_lateral_lkas": False,
    "always_on_lateral_main": False,
    "always_on_lateral_pause_speed": 0.0,
    "bookmark_via_cancel": False,
    "bookmark_via_cancel_long": False,
    "bookmark_via_cancel_very_long": False,
    "bookmark_via_lkas": False,
    "conditional_experimental_mode": False,
    "experimental_mode_via_lkas": False,
    "force_coast_via_lkas": False,
    "lkas_allowed_for_aol": False,
    "main_cruise_aol_toggle": False,
    "main_cruise_slc_adopt": False,
    "pause_lateral_via_lkas": False,
    "pause_longitudinal_via_lkas": False,
    "speed_limit_controller": False,
    "switchback_mode_via_lkas": False,
    "traffic_mode_via_lkas": False,
  }
  defaults.update(overrides)
  return SimpleNamespace(**defaults)


def make_car_state(available=False, enabled=False, button_events=None):
  return SimpleNamespace(
    buttonEvents=button_events or [],
    cruiseState=SimpleNamespace(available=available, enabled=enabled),
    gearShifter=spc.GearShifter.drive,
    brakePressed=False,
    gasPressed=False,
    standstill=False,
    vEgo=15.0,
  )


def make_wrapped_button_event(button_type, pressed):
  return SimpleNamespace(type=SimpleNamespace(raw=int(button_type)), pressed=pressed)


def test_honda_lkas_button_can_toggle_always_on_lateral(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="honda"), SimpleNamespace(alternativeExperience=0))

  car_state = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral_lkas=True, lkas_allowed_for_aol=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.pauseLateral is False


def test_hyundai_lkas_button_can_start_aol_before_normal_engagement(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  car_state = make_car_state(available=True, button_events=[
    SimpleNamespace(type=spc.ButtonType.decelCruise, pressed=True),
    SimpleNamespace(type=spc.ButtonType.lkas, pressed=True),
  ])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_lkas=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.buttonEvents = [SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)]
  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is False
  assert ret.pauseLateral is False


def test_hyundai_aol_does_not_auto_start_from_cruise_availability(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  ret = card.update(make_car_state(available=True), SimpleNamespace(distancePressed=False), make_sm(),
                    make_toggles(always_on_lateral=True, always_on_lateral_lkas=True))

  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False


def test_hyundai_canfd_lkas_button_can_toggle_aol_before_engagement(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", flags=spc.HyundaiFlags.CANFD),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  car_state = make_car_state(available=True, button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_lkas=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_hyundai_canfd_lkas_button_wrapped_enum_can_toggle_aol(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", flags=spc.HyundaiFlags.CANFD),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  car_state = make_car_state(available=True, button_events=[make_wrapped_button_event(spc.ButtonType.lkas, True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_lkas=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.buttonEvents = [make_wrapped_button_event(spc.ButtonType.lkas, True)]
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False


def test_kia_forte_non_scc_main_cruise_button_can_toggle_aol_before_engagement(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(
      brand="hyundai",
      carFingerprint=spc.HYUNDAI_CAR.KIA_FORTE_2021_NON_SCC,
      flags=spc.HyundaiFlags.NON_SCC,
    ),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  car_state = make_car_state(available=True, button_events=[SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, main_cruise_aol_toggle=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_hyundai_main_cruise_button_can_start_aol_before_normal_engagement(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  car_state = make_car_state(available=True, button_events=[SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, main_cruise_aol_toggle=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.buttonEvents = [SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)]
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False


def test_hyundai_main_cruise_button_wrapped_enum_can_toggle_aol(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  car_state = make_car_state(available=True, button_events=[make_wrapped_button_event(spc.ButtonType.mainCruise, True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, main_cruise_aol_toggle=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.buttonEvents = [make_wrapped_button_event(spc.ButtonType.mainCruise, True)]
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False


def test_hyundai_main_cruise_button_adopts_slc_when_assigned_to_slc(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="hyundai"), SimpleNamespace(alternativeExperience=0))

  car_state = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_lkas=True,
                         main_cruise_slc_adopt=True, speed_limit_controller=True)

  initial_allowed = card.always_on_lateral_allowed
  card.update(car_state, starpilot_car_state, sm, toggles)

  assert card.always_on_lateral_allowed is initial_allowed
  assert card.params_memory.get_bool("SLCAdoptSpeedLimit") is True


def test_honda_lkas_button_pauses_lateral_when_cruise_is_active(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="honda"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  card.always_on_lateral_allowed = True

  car_state = make_car_state(available=True, enabled=True, button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  sm["selfdriveState"].active = True
  toggles = make_toggles(always_on_lateral_lkas=True, lkas_allowed_for_aol=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is False
  assert ret.pauseLateral is True

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.pauseLateral is False


def test_main_aol_still_follows_cruise_main_for_other_platforms(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="toyota", carFingerprint="TOYOTA_TEST", pcmCruise=True),
                           SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL))

  ret = card.update(make_car_state(available=True), SimpleNamespace(distancePressed=False), make_sm(),
                    make_toggles(always_on_lateral_main=True))

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_pacifica_hybrid_main_aol_waits_for_set_press(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="chrysler", carFingerprint=CHRYSLER_CAR.CHRYSLER_PACIFICA_2019_HYBRID, pcmCruise=True),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  sm = make_sm()
  toggles = make_toggles(always_on_lateral_main=True)
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  car_state = make_car_state(available=True, enabled=False)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False

  car_state.cruiseState.enabled = True
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.cruiseState.enabled = False
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.cruiseState.available = False
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False


def test_conditional_chill_wheel_override_cycles_manual_state(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  sm = make_sm()
  toggles = make_toggles(conditional_chill_mode=True)

  sm["selfdriveState"].experimentalMode = True
  card.handle_experimental_mode(sm, toggles)
  assert card.params_memory.get_int("CCStatus") == spc.CCStatus["USER_CHILL"]

  card.handle_experimental_mode(sm, toggles)
  assert card.params_memory.get_int("CCStatus") == spc.CCStatus["OFF"]


def test_cancel_button_short_press_can_run_independent_mapping(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  sm = make_sm()
  toggles = make_toggles(bookmark_via_cancel=True)
  starpilot_car_state = SimpleNamespace(distancePressed=False, cancelPressed=False)

  card.update(make_car_state(), starpilot_car_state, sm, toggles)
  assert card.params_memory.get_int("WheelButtonBookmarkCounter") == 0

  starpilot_car_state.cancelPressed = True
  ret = card.update(make_car_state(), starpilot_car_state, sm, toggles)
  assert ret.cancelLongPressed is False
  assert ret.cancelVeryLongPressed is False
  assert card.params_memory.get_int("WheelButtonBookmarkCounter") == 0

  starpilot_car_state.cancelPressed = False
  ret = card.update(make_car_state(), starpilot_car_state, sm, toggles)
  assert ret.cancelLongPressed is False
  assert ret.cancelVeryLongPressed is False
  assert card.params_memory.get_int("WheelButtonBookmarkCounter") == 1


def test_favorite_wheel_action_toggles_hidden_onroad_slot(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "is_FrogsGoMoo", lambda: False)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  card.params.put("RedneckCruise", False)
  card.params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": False, "key": "RedneckCruise", "label": "Redneck Cruise"},
  ])

  card.handle_button_event("lkas", make_sm(), make_toggles(favorite_1_via_lkas=True))

  assert card.params.get_bool("RedneckCruise") is True
  assert card.params_memory.get_bool("StarPilotTogglesUpdated") is True
