from types import SimpleNamespace

import pytest

from opendbc.car.chrysler.values import CAR as CHRYSLER_CAR

from openpilot.common.params import ParamKeyType
from openpilot.starpilot.common.favorite_slots import (
  FAVORITE_ACTION_ACCEL_COUNTER,
  FAVORITE_ACTION_DISTANCE_INCREASE,
  FAVORITE_ACTION_TRAFFIC_MODE_COUNTER,
  FAVORITE_ACTION_TOGGLE_TRAFFIC_MODE,
  FAVORITE_SLOTS_PARAM,
)
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
    "starpilotPlan": SimpleNamespace(lateralCheck=True, speedLimitChanged=False, unconfirmedSlcSpeedLimit=0.0),
    "liveCalibration": SimpleNamespace(calPerc=100),
  }, updated={"starpilotPlan": False})


def make_toggles(**overrides):
  defaults = {
    "always_on_lateral": False,
    "always_on_lateral_lkas": False,
    "always_on_lateral_main": False,
    "always_on_lateral_pause_speed": 0.0,
    "tesla_aol_disengage_on_brake": False,
    "bookmark_via_cancel": False,
    "bookmark_via_cancel_long": False,
    "bookmark_via_cancel_very_long": False,
    "experimental_mode_via_cancel": False,
    "experimental_mode_via_cancel_long": False,
    "experimental_mode_via_cancel_very_long": False,
    "force_coast_via_cancel": False,
    "force_coast_via_cancel_long": False,
    "force_coast_via_cancel_very_long": False,
    "bookmark_via_lkas": False,
    "conditional_experimental_mode": False,
    "experimental_mode_via_lkas": False,
    "force_coast_via_lkas": False,
    "ford_lkas_aol_toggle": False,
    "pulse_and_glide_available": False,
    "pulse_and_glide_via_cancel": False,
    "pulse_and_glide_via_cancel_long": False,
    "pulse_and_glide_via_cancel_very_long": False,
    "pulse_and_glide_via_lkas": False,
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


def test_preap_aol_stays_available_but_waits_for_authorization(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)
  card = spc.StarPilotCard(SimpleNamespace(brand="tesla", carFingerprint="TESLA_MODEL_S_PREAP"),
                           SimpleNamespace(alternativeExperience=32))
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=True)
  sm = make_sm()
  for authorized in (False, True, False, True):
    ret = card.update(make_car_state(available=True, enabled=False), SimpleNamespace(distancePressed=False),
                      sm, toggles, preap_authorized=authorized)
    assert card.always_on_lateral_supported
    assert ret.alwaysOnLateralAllowed
    assert ret.alwaysOnLateralEnabled == authorized


def test_pulse_and_glide_requires_developer_access_and_active_longitudinal(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  sm = make_sm()
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  toggles = make_toggles(
    pulse_and_glide_available=True,
    pulse_and_glide_via_lkas=True,
  )

  card.handle_button_event("lkas", sm, toggles)
  assert card.pulse_and_glide is False

  sm["carControl"].longActive = True
  card.handle_button_event("lkas", sm, toggles)
  assert card.pulse_and_glide is True

  car_state = make_car_state(gas_pressed=True)
  result = card.update(car_state, starpilot_car_state, sm, toggles)
  assert result.pulseAndGlide is True


def test_pulse_and_glide_survives_temporary_disengagement(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  sm = make_sm()
  sm["carControl"].longActive = True
  toggles = make_toggles(
    pulse_and_glide_available=True,
    pulse_and_glide_via_lkas=True,
  )
  starpilot_car_state = SimpleNamespace(distancePressed=False)

  card.handle_button_event("lkas", sm, toggles)
  assert card.pulse_and_glide is True

  sm["carControl"].longActive = False
  result = card.update(make_car_state(brake_pressed=True), starpilot_car_state, sm, toggles)
  assert result.pulseAndGlide is True

  sm["carControl"].longActive = True
  result = card.update(make_car_state(), starpilot_car_state, sm, toggles)
  assert result.pulseAndGlide is True

  sm["carControl"].longActive = False
  off_press = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])
  result = card.update(off_press, starpilot_car_state, sm, toggles)
  assert result.pulseAndGlide is False
  assert off_press.buttonEvents == []


def test_pulse_and_glide_consumes_native_cancel_when_mapped(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  sm = make_sm()
  sm["carControl"].longActive = True
  toggles = make_toggles(
    pulse_and_glide_available=True,
    pulse_and_glide_via_cancel=True,
  )
  starpilot_car_state = SimpleNamespace(distancePressed=False, cancelPressed=True)

  press = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.cancel, pressed=True)])
  card.update(press, starpilot_car_state, sm, toggles)
  assert press.buttonEvents == []

  starpilot_car_state.cancelPressed = False
  release = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.cancel, pressed=False)])
  result = card.update(release, starpilot_car_state, sm, toggles)

  assert card.pulse_and_glide is True
  assert result.pulseAndGlide is True
  assert release.buttonEvents == []


def test_pulse_and_glide_consumes_lkas_when_mapped(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  sm = make_sm()
  sm["carControl"].longActive = True
  toggles = make_toggles(
    pulse_and_glide_available=True,
    pulse_and_glide_via_lkas=True,
  )
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  car_state = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])

  result = card.update(car_state, starpilot_car_state, sm, toggles)

  assert card.pulse_and_glide is True
  assert result.pulseAndGlide is True
  assert car_state.buttonEvents == []


def test_pulse_and_glide_long_cancel_consumes_release_after_threshold(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  sm = make_sm()
  sm["carControl"].longActive = True
  toggles = make_toggles(
    pulse_and_glide_available=True,
    pulse_and_glide_via_cancel_long=True,
  )
  starpilot_car_state = SimpleNamespace(distancePressed=False, cancelPressed=True)

  for frame in range(card.long_press_threshold):
    button_events = [SimpleNamespace(type=spc.ButtonType.cancel, pressed=True)] if frame == 0 else []
    card.update(make_car_state(button_events=button_events), starpilot_car_state, sm, toggles)

  assert card.pulse_and_glide is True

  starpilot_car_state.cancelPressed = False
  release = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.cancel, pressed=False)])
  card.update(release, starpilot_car_state, sm, toggles)

  assert card.pulse_and_glide is True
  assert release.buttonEvents == []


@pytest.mark.parametrize(
  ("pressed_field", "long_key", "very_long_key"),
  (
    ("distancePressed", "distance_long", "distance_very_long"),
    ("cancelPressed", "cancel_long", "cancel_very_long"),
    ("modePressed", "mode_long", "mode_very_long"),
    ("customPressed", "star_long", "star_very_long"),
  ),
)
def test_very_long_press_does_not_repeat_long_press_action(monkeypatch, tmp_path, pressed_field, long_key, very_long_key):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  sm = make_sm()
  toggles = make_toggles(has_canfd_media_buttons=pressed_field in ("modePressed", "customPressed"))
  starpilot_car_state = SimpleNamespace(
    distancePressed=False,
    cancelPressed=False,
    modePressed=False,
    customPressed=False,
  )
  setattr(starpilot_car_state, pressed_field, True)
  handled = []
  monkeypatch.setattr(card, "handle_button_event", lambda key, _sm, _toggles: handled.append(key) or False)

  for _ in range(card.very_long_press_threshold):
    card.update(make_car_state(), starpilot_car_state, sm, toggles)

  assert handled == [long_key, very_long_key]


def make_car_state(available=False, enabled=False, button_events=None, brake_pressed=False, gas_pressed=False):
  return SimpleNamespace(
    buttonEvents=button_events or [],
    cruiseState=SimpleNamespace(available=available, enabled=enabled),
    gearShifter=spc.GearShifter.drive,
    brakePressed=brake_pressed,
    gasPressed=gas_pressed,
    standstill=False,
    vEgo=15.0,
  )


def make_wrapped_button_event(button_type, pressed):
  return SimpleNamespace(type=SimpleNamespace(raw=int(button_type)), pressed=pressed)


@pytest.mark.parametrize("fingerprint", tuple(spc.HYUNDAI_CAR))
@pytest.mark.parametrize("openpilot_long, pcm_cruise", ((True, False), (False, True), (True, True)))
def test_ev6_arming_gate_is_limited_to_ev6_openpilot_long(monkeypatch, tmp_path, fingerprint, openpilot_long, pcm_cruise):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)
  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", carFingerprint=fingerprint, flags=spc.HyundaiFlags.CANFD,
                    openpilotLongitudinalControl=openpilot_long, pcmCruise=pcm_cruise),
    SimpleNamespace(alternativeExperience=32),
  )
  needs_arming = fingerprint == spc.HYUNDAI_CAR.KIA_EV6 and openpilot_long and not pcm_cruise
  assert card.ev6_aol_needs_arming == needs_arming
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=True)
  ret = card.update(make_car_state(available=True), SimpleNamespace(distancePressed=False), make_sm(), toggles)
  assert ret.alwaysOnLateralEnabled == (card.always_on_lateral_supported and not needs_arming)


@pytest.mark.parametrize("lkas_mapping", (False, True))
def test_ev6_aol_requires_physical_authorization_even_for_controller_actions(monkeypatch, tmp_path, lkas_mapping):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)
  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", carFingerprint=spc.HYUNDAI_CAR.KIA_EV6, flags=spc.HyundaiFlags.CANFD,
                    openpilotLongitudinalControl=True, pcmCruise=False),
    SimpleNamespace(alternativeExperience=32),
  )
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=not lkas_mapping,
                         always_on_lateral_lkas=lkas_mapping)
  sm = make_sm()
  output = SimpleNamespace(distancePressed=False)
  cs = make_car_state(available=True)
  ret = card.update(cs, output, sm, toggles)
  assert not ret.alwaysOnLateralAllowed
  assert not ret.alwaysOnLateralEnabled

  counter = spc.CONTROLLER_ACTION_COUNTERS[spc.CONTROLLER_ACTION_TOGGLE_AOL]
  card.params_memory.put_int(counter, 1)
  ret = card.update(cs, output, sm, toggles)
  assert not ret.alwaysOnLateralAllowed
  assert not ret.alwaysOnLateralEnabled

  cs.buttonEvents = [make_wrapped_button_event(spc.ButtonType.lkas, True)]
  ret = card.update(cs, output, sm, toggles, ev6_aol_authorized=True)
  assert ret.alwaysOnLateralEnabled
  cs.buttonEvents = []
  ret = card.update(cs, output, sm, toggles, ev6_aol_authorized=True)
  assert ret.alwaysOnLateralEnabled

  ret = card.update(cs, output, sm, toggles, ev6_aol_authorized=False)
  assert not ret.alwaysOnLateralAllowed
  assert not ret.alwaysOnLateralEnabled


def test_ev6_lkas_experimental_mapping_still_runs_when_armed(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)
  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", carFingerprint=spc.HYUNDAI_CAR.KIA_EV6, flags=spc.HyundaiFlags.CANFD,
                    openpilotLongitudinalControl=True, pcmCruise=False),
    SimpleNamespace(alternativeExperience=32),
  )
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=True, experimental_mode_via_lkas=True,
                         experimental_mode_available=True)
  sm = make_sm()
  sm["carControl"].latActive = True
  cs = make_car_state(available=True, button_events=[make_wrapped_button_event(spc.ButtonType.lkas, True)])
  ret = card.update(cs, SimpleNamespace(distancePressed=False), sm, toggles, ev6_aol_authorized=True)
  assert ret.alwaysOnLateralEnabled
  assert card.params.get_bool("ExperimentalMode")


@pytest.mark.parametrize("pending_before_press", [False, True])
def test_slc_confirmation_release_does_not_republish_accel(monkeypatch, tmp_path, pending_before_press):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)
  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  sm = make_sm()
  toggles = make_toggles(speed_limit_controller=True)
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  button_type = spc.ButtonType.accelCruise

  if pending_before_press:
    sm["starpilotPlan"].speedLimitChanged = True
    sm["starpilotPlan"].unconfirmedSlcSpeedLimit = 20.0
  pressed = make_car_state(button_events=[make_wrapped_button_event(button_type, True)])
  assert card.update(pressed, starpilot_car_state, sm, toggles).accelPressed

  if not pending_before_press:
    sm["starpilotPlan"].speedLimitChanged = True
    sm["starpilotPlan"].unconfirmedSlcSpeedLimit = 20.0
    card.update(make_car_state(), starpilot_car_state, sm, toggles)

  sm["starpilotPlan"].speedLimitChanged = False
  sm["starpilotPlan"].unconfirmedSlcSpeedLimit = 0.0
  released = make_car_state(button_events=[make_wrapped_button_event(button_type, False)])
  assert not card.update(released, starpilot_car_state, sm, toggles).accelPressed
  assert not card.confirmation_button_suppressed

  assert card.update(pressed, starpilot_car_state, sm, toggles).accelPressed
  assert card.update(released, starpilot_car_state, sm, toggles).accelPressed


@pytest.mark.parametrize(
  ("car_fingerprint", "expect_normalized_release"),
  (
    (spc.HYUNDAI_CAR.HYUNDAI_ELANTRA_HEV_2024, True),
    (spc.HYUNDAI_CAR.HYUNDAI_ELANTRA_2024, False),
  ),
)
def test_distance_release_normalization_is_limited_to_reported_elantra_hybrid(
    monkeypatch, tmp_path, car_fingerprint, expect_normalized_release,
):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", carFingerprint=car_fingerprint),
    SimpleNamespace(alternativeExperience=0),
  )
  toggles = make_toggles(
    experimental_mode_via_distance=False,
    bookmark_via_distance=False,
    force_coast_via_distance=False,
    pulse_and_glide_via_distance=False,
    pause_lateral_via_distance=False,
    pause_longitudinal_via_distance=False,
    switchback_mode_via_distance=False,
  )
  sm = make_sm()
  starpilot_car_state = SimpleNamespace(distancePressed=True)

  card.update(make_car_state(), starpilot_car_state, sm, toggles)

  starpilot_car_state.distancePressed = False
  car_state = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.unknown, pressed=False)])
  card.update(car_state, starpilot_car_state, sm, toggles)

  assert any(
    be.type == spc.ButtonType.gapAdjustCruise and not be.pressed
    for be in car_state.buttonEvents
  ) is expect_normalized_release


def test_honda_lkas_button_can_toggle_always_on_lateral(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="honda"), SimpleNamespace(alternativeExperience=0))

  car_state = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral_lkas=True, lkas_allowed_for_aol=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.pauseLateral is False


def test_controller_actions_match_vehicle_button_behaviors(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="honda"), SimpleNamespace(alternativeExperience=0))
  sm = make_sm()
  sm["carControl"].longActive = True
  toggles = make_toggles(
    always_on_lateral=True,
    lkas_allowed_for_aol=True,
    openpilot_longitudinal=True,
    pulse_and_glide_available=True,
  )
  for _key, counter in spc.CONTROLLER_ACTION_COUNTERS.items():
    if counter != "WheelButtonBookmarkCounter":
      card.params_memory.put_int(counter, 1)

  ret = card.update(make_car_state(), SimpleNamespace(distancePressed=False), sm, toggles)

  assert card.force_coast is True
  assert card.pulse_and_glide is True
  assert ret.alwaysOnLateralAllowed is True

  ret = card.update(make_car_state(), SimpleNamespace(distancePressed=False), sm, toggles)
  assert card.force_coast is True
  assert card.pulse_and_glide is True
  assert ret.alwaysOnLateralAllowed is True


def test_controller_aol_does_not_require_physical_lkas_button_mapping(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="honda"), SimpleNamespace(alternativeExperience=0))
  card.params_memory.put_int(spc.CONTROLLER_ACTION_COUNTERS[spc.CONTROLLER_ACTION_TOGGLE_AOL], 1)
  ret = card.update(
    make_car_state(),
    SimpleNamespace(distancePressed=False),
    make_sm(),
    make_toggles(always_on_lateral=True, lkas_allowed_for_aol=False),
  )

  assert ret.alwaysOnLateralAllowed is True


@pytest.mark.parametrize("brand", ["tesla", "gm"])
def test_controller_aol_owns_main_latch_only_while_cruise_is_available(monkeypatch, tmp_path, brand):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand=brand),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=True)
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  counter = spc.CONTROLLER_ACTION_COUNTERS[spc.CONTROLLER_ACTION_TOGGLE_AOL]

  initial = card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)
  assert initial.alwaysOnLateralAllowed is True
  assert initial.alwaysOnLateralEnabled is True

  card.params_memory.put_int(counter, 1)
  toggled_off = card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)
  assert toggled_off.alwaysOnLateralAllowed is False
  assert toggled_off.alwaysOnLateralEnabled is False

  persisted_off = card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)
  assert persisted_off.alwaysOnLateralAllowed is False
  assert persisted_off.alwaysOnLateralEnabled is False

  card.params_memory.put_int(counter, 2)
  toggled_on = card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)
  assert toggled_on.alwaysOnLateralAllowed is True
  assert toggled_on.alwaysOnLateralEnabled is True

  unavailable = card.update(make_car_state(available=False), starpilot_car_state, sm, toggles)
  assert unavailable.alwaysOnLateralAllowed is False
  assert unavailable.alwaysOnLateralEnabled is False

  available_again = card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)
  assert available_again.alwaysOnLateralAllowed is True
  assert available_again.alwaysOnLateralEnabled is True

  card.params_memory.put_int(counter, 3)
  card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)
  card.update(make_car_state(available=False), starpilot_car_state, sm, toggles)
  still_off = card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)
  assert still_off.alwaysOnLateralAllowed is False
  assert still_off.alwaysOnLateralEnabled is False


def test_controller_aol_cannot_arm_main_latch_without_cruise(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)
  card = spc.StarPilotCard(SimpleNamespace(brand="tesla"), SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL))
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=True)
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  card.params_memory.put_int(spc.CONTROLLER_ACTION_COUNTERS[spc.CONTROLLER_ACTION_TOGGLE_AOL], 1)

  unavailable = card.update(make_car_state(available=False), starpilot_car_state, make_sm(), toggles)
  assert unavailable.alwaysOnLateralEnabled is False
  assert card.controller_aol_override is None

  available = card.update(make_car_state(available=True), starpilot_car_state, make_sm(), toggles)
  assert available.alwaysOnLateralEnabled is True


def test_tesla_controller_disarm_survives_engagement(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)
  card = spc.StarPilotCard(SimpleNamespace(brand="tesla"), SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL))
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=True, tesla_aol_disengage_on_brake=True)
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  counter = spc.CONTROLLER_ACTION_COUNTERS[spc.CONTROLLER_ACTION_TOGGLE_AOL]
  card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)
  card.params_memory.put_int(counter, 1)
  card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)

  sm["selfdriveState"].active = True
  engaged = card.update(make_car_state(available=True, enabled=True), starpilot_car_state, sm, toggles)
  assert engaged.alwaysOnLateralAllowed is False
  assert engaged.alwaysOnLateralEnabled is False


def test_hyundai_lkas_button_can_start_aol_before_normal_engagement(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
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


def test_volvo_aol_stays_disabled_even_with_stale_enabled_toggle(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="volvo"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  car_state = make_car_state(available=True, enabled=True)
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(
    always_on_lateral=True,
    always_on_lateral_main=True,
    always_on_lateral_lkas=True,
    lkas_allowed_for_aol=True,
    main_cruise_aol_toggle=True,
  )

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False


def test_sonata_hybrid_lkas_button_can_start_aol_before_normal_engagement(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", carFingerprint=spc.HYUNDAI_CAR.HYUNDAI_SONATA_HYBRID),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  car_state = make_car_state(available=False, enabled=False, button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_lkas=True, lkas_allowed_for_aol=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_sonata_hybrid_preserves_aol_latch_across_reverse(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", carFingerprint=spc.HYUNDAI_CAR.HYUNDAI_SONATA_HYBRID),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_lkas=True, lkas_allowed_for_aol=True)

  enabled_state = make_car_state(available=False, enabled=False, button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])
  ret = card.update(enabled_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  reverse_state = make_car_state(available=False, enabled=False)
  reverse_state.gearShifter = spc.GearShifter.reverse
  ret = card.update(reverse_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is False

  drive_state = make_car_state(available=False, enabled=False)
  ret = card.update(drive_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_hyundai_aol_does_not_auto_start_from_cruise_availability(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  ret = card.update(make_car_state(available=True), SimpleNamespace(distancePressed=False), make_sm(),
                    make_toggles(always_on_lateral=True, always_on_lateral_lkas=True))

  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False


def test_genesis_g90_main_aol_can_start_before_set(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", carFingerprint=spc.HYUNDAI_CAR.GENESIS_G90),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  ret = card.update(make_car_state(available=True), SimpleNamespace(distancePressed=False), make_sm(),
                    make_toggles(always_on_lateral=True, always_on_lateral_main=True))

  assert card.hyundai_aol_needs_engagement is False
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_other_legacy_hyundai_main_aol_still_waits_for_set(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", carFingerprint=spc.HYUNDAI_CAR.GENESIS_G80),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  ret = card.update(make_car_state(available=True), SimpleNamespace(distancePressed=False), make_sm(),
                    make_toggles(always_on_lateral=True, always_on_lateral_main=True))

  assert card.hyundai_aol_needs_engagement is True
  assert ret.alwaysOnLateralEnabled is False


def test_legacy_hyundai_main_aol_waits_for_main_button_permission(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", carFingerprint=spc.HYUNDAI_CAR.HYUNDAI_ELANTRA_2021),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  sm = make_sm()
  toggles = make_toggles(
    always_on_lateral=True,
    always_on_lateral_main=True,
    lkas_allowed_for_aol=True,
    main_cruise_aol_toggle=True,
  )
  starpilot_car_state = SimpleNamespace(distancePressed=False)

  ret = card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False

  ret = card.update(
    make_car_state(available=True, button_events=[SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)]),
    starpilot_car_state,
    sm,
    toggles,
  )
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_nissan_main_aol_can_start_before_normal_engagement(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="nissan"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  ret = card.update(make_car_state(available=True), SimpleNamespace(distancePressed=False), make_sm(),
                    make_toggles(always_on_lateral=True, always_on_lateral_main=True))

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_hyundai_canfd_lkas_button_can_toggle_aol_before_engagement(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
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


@pytest.mark.parametrize("fingerprint", (
  spc.HYUNDAI_CAR.KIA_FORTE_2019_NON_SCC,
  spc.HYUNDAI_CAR.KIA_FORTE_2021_NON_SCC,
))
def test_kia_forte_non_scc_main_cruise_aol_follows_cruise_state(monkeypatch, tmp_path, fingerprint):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(
      brand="hyundai",
      carFingerprint=fingerprint,
      flags=spc.HyundaiFlags.NON_SCC,
    ),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  assert card.kia_forte_non_scc

  car_state = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, main_cruise_aol_toggle=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False

  car_state.buttonEvents = []
  car_state.cruiseState.available = True
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.cruiseState.available = False
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False


def test_kia_forte_non_scc_main_cruise_aol_restores_state_after_boot(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(
      brand="hyundai",
      carFingerprint=spc.HYUNDAI_CAR.KIA_FORTE_2021_NON_SCC,
      flags=spc.HyundaiFlags.NON_SCC,
    ),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  assert card.kia_forte_non_scc

  ret = card.update(
    make_car_state(available=True),
    SimpleNamespace(distancePressed=False),
    make_sm(),
    make_toggles(always_on_lateral=True, main_cruise_aol_toggle=True),
  )
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_genesis_g90_main_cruise_button_toggles_aol_immediately(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", carFingerprint=spc.HYUNDAI_CAR.GENESIS_G90),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  car_state = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, main_cruise_aol_toggle=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.buttonEvents = []
  car_state.cruiseState.available = False
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_genesis_g70_main_cruise_button_waits_for_cruise_availability(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", carFingerprint=spc.HYUNDAI_CAR.GENESIS_G70_2020),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  car_state = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, main_cruise_aol_toggle=True)

  card.update(make_car_state(), starpilot_car_state, sm, toggles)
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False

  car_state.buttonEvents = []
  car_state.cruiseState.available = True
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.buttonEvents = [SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)]
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.buttonEvents = []
  car_state.cruiseState.available = False
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False


def test_legacy_hyundai_main_cruise_button_toggles_aol_immediately(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai", carFingerprint=spc.HYUNDAI_CAR.HYUNDAI_PALISADE),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  car_state = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, main_cruise_aol_toggle=True)

  card.update(make_car_state(), starpilot_car_state, sm, toggles)
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.buttonEvents = [SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)]
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False


def test_hyundai_main_cruise_button_toggles_aol_immediately(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  car_state = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, main_cruise_aol_toggle=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.buttonEvents = [SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)]
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False


def test_hyundai_main_cruise_button_wrapped_enum_can_toggle_aol(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  car_state = make_car_state()
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, main_cruise_aol_toggle=True)

  card.update(car_state, starpilot_car_state, sm, toggles)
  car_state.buttonEvents = [make_wrapped_button_event(spc.ButtonType.mainCruise, True)]
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.buttonEvents = []
  car_state.cruiseState.available = False
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  car_state.buttonEvents = [make_wrapped_button_event(spc.ButtonType.mainCruise, True)]
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False


def test_hyundai_lda_platform_main_aol_waits_for_engagement_without_lkas_mapping(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  car_state = make_car_state(available=True)
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=True, lkas_allowed_for_aol=True)

  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is False

  sm["selfdriveState"].active = True
  ret = card.update(car_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralEnabled is True


def test_honda_mapped_main_cruise_button_keeps_immediate_toggle(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="honda"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  car_state = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.mainCruise, pressed=True)])
  toggles = make_toggles(always_on_lateral=True, main_cruise_aol_toggle=True, lkas_allowed_for_aol=True)

  ret = card.update(car_state, SimpleNamespace(distancePressed=False), make_sm(), toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_hyundai_main_cruise_button_adopts_slc_when_assigned_to_slc(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
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
  card.prev_active = True

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is False
  assert ret.pauseLateral is True

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.pauseLateral is False


def test_ford_lkas_button_pauses_lateral_when_cruise_is_active(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="ford"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  card.always_on_lateral_allowed = True

  car_state = make_car_state(available=True, enabled=True, button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  sm["selfdriveState"].active = True
  sm["carControl"].longActive = True
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=True, pause_lateral_via_lkas=True)
  card.prev_active = True

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.pauseLateral is True
  assert ret.pauseLongitudinal is False

  car_state.buttonEvents = [SimpleNamespace(type=spc.ButtonType.lkas, pressed=False)]
  card.update(car_state, starpilot_car_state, sm, toggles)
  car_state.buttonEvents = [SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)]
  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.pauseLateral is False
  assert ret.pauseLongitudinal is False


def test_ford_lkas_button_pauses_aol_with_only_cruise_master_on(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="ford"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=True, pause_lateral_via_lkas=True)

  master_on = make_car_state(available=True, enabled=False)
  ret = card.update(master_on, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  master_on.buttonEvents = [SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)]
  ret = card.update(master_on, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.pauseLateral is True
  assert ret.pauseLongitudinal is False

  sm["starpilotPlan"].lateralCheck = False
  master_on.buttonEvents = []
  ret = card.update(master_on, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is False

  master_on.cruiseState.available = False
  master_on.buttonEvents = [SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)]
  ret = card.update(master_on, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is False
  assert ret.pauseLateral is True

  sm["starpilotPlan"].lateralCheck = True
  master_on.cruiseState.available = True
  master_on.buttonEvents = []
  ret = card.update(master_on, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True
  assert ret.pauseLateral is False


def test_ford_lkas_button_pauses_lateral_when_aol_is_disabled(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="ford"), SimpleNamespace(alternativeExperience=0))
  car_state = make_car_state(available=True, enabled=True, button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  sm["selfdriveState"].active = True
  sm["carControl"].longActive = True
  toggles = make_toggles(pause_lateral_via_lkas=True)
  card.prev_active = True

  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is False
  assert ret.pauseLateral is True
  assert ret.pauseLongitudinal is False

  car_state.buttonEvents = [SimpleNamespace(type=spc.ButtonType.lkas, pressed=False)]
  card.update(car_state, starpilot_car_state, sm, toggles)
  car_state.buttonEvents = [SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)]
  ret = card.update(car_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is False
  assert ret.pauseLateral is False
  assert ret.pauseLongitudinal is False


def test_ford_lkas_button_can_use_aol_mapping(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="ford"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  car_state = make_car_state(available=True)
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=True, ford_lkas_aol_toggle=True, lkas_allowed_for_aol=True)

  ret = card.update(car_state, SimpleNamespace(distancePressed=False), make_sm(), toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.pauseLateral is False

  car_state.buttonEvents = [SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)]
  ret = card.update(car_state, SimpleNamespace(distancePressed=False), make_sm(), toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.pauseLateral is True

  car_state.buttonEvents = [SimpleNamespace(type=spc.ButtonType.lkas, pressed=False)]
  card.update(car_state, SimpleNamespace(distancePressed=False), make_sm(), toggles)
  car_state.buttonEvents = [SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)]
  ret = card.update(car_state, SimpleNamespace(distancePressed=False), make_sm(), toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.pauseLateral is False


def test_ford_aol_mapping_pauses_lateral_when_aol_is_disabled(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="ford"), SimpleNamespace(alternativeExperience=0))
  card.prev_cruise_enabled = True
  car_state = make_car_state(available=True, enabled=True, button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])
  sm = make_sm()
  sm["selfdriveState"].active = True
  sm["carControl"].longActive = True

  ret = card.update(car_state, SimpleNamespace(distancePressed=False), sm, make_toggles(ford_lkas_aol_toggle=True))

  assert ret.alwaysOnLateralAllowed is False
  assert ret.pauseLateral is True
  assert ret.pauseLongitudinal is False


def test_ford_lkas_button_can_keep_experimental_mapping(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="ford"), SimpleNamespace(alternativeExperience=0))
  card.prev_cruise_enabled = True
  car_state = make_car_state(available=True, enabled=True, button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])
  sm = make_sm()
  sm["carControl"].longActive = True

  ret = card.update(car_state, SimpleNamespace(distancePressed=False), sm, make_toggles(experimental_mode_via_lkas=True))

  assert card.params.get_bool("ExperimentalMode") is True
  assert ret.pauseLateral is False


def test_ford_new_longitudinal_engagement_resumes_lateral(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="ford"), SimpleNamespace(alternativeExperience=0))
  card.pause_lateral = True

  car_state = make_car_state(available=True, enabled=True)
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  sm = make_sm()
  sm["selfdriveState"].active = True
  sm["carControl"].longActive = True

  ret = card.update(car_state, starpilot_car_state, sm, make_toggles())

  assert ret.pauseLateral is False
  assert ret.pauseLongitudinal is False


def test_honda_main_aol_follows_cruise_main_without_manual_aol_button_mapping(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="honda"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  toggles = make_toggles(always_on_lateral_main=True, lkas_allowed_for_aol=True)
  ret = card.update(make_car_state(available=True), SimpleNamespace(distancePressed=False), make_sm(), toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_hyundai_main_aol_persists_after_brake_disengage_without_manual_aol_button_mapping(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="hyundai"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  sm = make_sm()
  toggles = make_toggles(always_on_lateral_main=True)
  starpilot_car_state = SimpleNamespace(distancePressed=False)

  sm["selfdriveState"].active = True
  enabled_state = make_car_state(available=True, enabled=True)
  ret = card.update(enabled_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  sm["selfdriveState"].active = False
  disengaged_state = make_car_state(available=True, enabled=False)
  ret = card.update(disengaged_state, starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_tesla_aol_disengages_on_brake_until_deliberate_reengagement(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="tesla", carFingerprint="TESLA_MODEL_Y", pcmCruise=True),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  sm = make_sm()
  toggles = make_toggles(
    always_on_lateral=True,
    always_on_lateral_main=True,
    tesla_aol_disengage_on_brake=True,
  )
  starpilot_car_state = SimpleNamespace(distancePressed=False)

  sm["selfdriveState"].active = True
  ret = card.update(make_car_state(available=True, enabled=True), starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralEnabled is True

  sm["selfdriveState"].active = False
  ret = card.update(
    make_car_state(available=True, brake_pressed=True), starpilot_car_state, sm, toggles,
  )
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False

  ret = card.update(
    make_car_state(available=True, gas_pressed=True), starpilot_car_state, sm, toggles,
  )
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False

  sm["selfdriveState"].active = True
  ret = card.update(make_car_state(available=True, enabled=True), starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


@pytest.fixture
def tesla_screen_card(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)
  return spc.StarPilotCard(
    SimpleNamespace(brand="tesla", carFingerprint=spc.TESLA_CAR.TESLA_MODEL_3, pcmCruise=True,
                    flags=spc.TeslaFlags.HAS_VEHICLE_BUS | spc.TeslaFlags.AOL_SCREEN_BUTTON),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )


def screen_toggles(**overrides):
  return make_toggles(always_on_lateral=True, always_on_lateral_main=True, tesla_aol_screen_tap=True, **overrides)


def screen_state(**kwargs):
  return make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)], **kwargs)


def test_tesla_screen_tap_toggles_without_engaging_cruise(tesla_screen_card):
  card = tesla_screen_card
  toggles, sm, fp_cs = screen_toggles(), make_sm(), SimpleNamespace(distancePressed=False)
  cs = screen_state()
  assert card.update(cs, fp_cs, sm, toggles).alwaysOnLateralEnabled
  assert not cs.cruiseState.enabled
  assert not cs.cruiseState.available
  assert not sm["carControl"].longActive
  for _ in range(10):
    assert card.update(make_car_state(), fp_cs, sm, toggles).alwaysOnLateralEnabled
  assert not card.update(screen_state(), fp_cs, sm, toggles).alwaysOnLateralEnabled
  assert not card.update(make_car_state(), fp_cs, sm, toggles).alwaysOnLateralEnabled


def test_tesla_screen_tap_pauses_only_lateral_with_active_cruise(tesla_screen_card):
  card = tesla_screen_card
  toggles, sm, fp_cs = screen_toggles(pulse_and_glide_via_lkas=True), make_sm(), SimpleNamespace(distancePressed=False)
  sm["selfdriveState"].active = True
  sm["carControl"].longActive = True
  card.update(make_car_state(available=True, enabled=True), fp_cs, sm, toggles)
  cs = screen_state(available=True, enabled=True)
  ret = card.update(cs, fp_cs, sm, toggles)
  assert not ret.alwaysOnLateralEnabled
  assert ret.pauseLateral
  assert cs.cruiseState.enabled
  assert sm["carControl"].longActive
  assert not card.pulse_and_glide
  assert card.update(make_car_state(available=True, enabled=True), fp_cs, sm, toggles).pauseLateral
  ret = card.update(screen_state(available=True, enabled=True), fp_cs, sm, toggles)
  assert ret.alwaysOnLateralEnabled
  assert not ret.pauseLateral


def test_tesla_screen_tap_preserves_brake_and_stalk_paths(tesla_screen_card):
  card = tesla_screen_card
  toggles, sm, fp_cs = screen_toggles(), make_sm(), SimpleNamespace(distancePressed=False)
  card.update(screen_state(), fp_cs, sm, toggles)
  assert card.update(make_car_state(brake_pressed=True), fp_cs, sm, toggles).alwaysOnLateralAllowed
  card.update(make_car_state(available=True, enabled=True), fp_cs, sm, toggles)
  assert not card.update(make_car_state(), fp_cs, sm, toggles).alwaysOnLateralAllowed
  sm["selfdriveState"].active = True
  assert card.update(make_car_state(available=True, enabled=True), fp_cs, sm, toggles).alwaysOnLateralEnabled


def test_tesla_screen_tap_respects_brake_disengage_option(tesla_screen_card):
  card = tesla_screen_card
  card.tesla_screen_disengage_on_brake = True
  toggles, sm, fp_cs = screen_toggles(tesla_aol_disengage_on_brake=True), make_sm(), SimpleNamespace(distancePressed=False)
  card.update(screen_state(), fp_cs, sm, toggles)
  assert not card.update(make_car_state(brake_pressed=True), fp_cs, sm, toggles).alwaysOnLateralAllowed
  assert not card.update(screen_state(brake_pressed=True), fp_cs, sm, toggles).alwaysOnLateralAllowed
  assert not card.update(make_car_state(), fp_cs, sm, toggles).alwaysOnLateralAllowed
  assert card.update(screen_state(), fp_cs, sm, toggles).alwaysOnLateralAllowed


def test_tesla_screen_tap_reenables_after_brake_without_a_blocked_tap(tesla_screen_card):
  card = tesla_screen_card
  card.tesla_screen_disengage_on_brake = True
  toggles, sm, fp_cs = screen_toggles(tesla_aol_disengage_on_brake=True), make_sm(), SimpleNamespace(distancePressed=False)
  card.update(screen_state(), fp_cs, sm, toggles)
  card.update(make_car_state(brake_pressed=True), fp_cs, sm, toggles)
  card.update(make_car_state(), fp_cs, sm, toggles)
  assert card.update(screen_state(), fp_cs, sm, toggles).alwaysOnLateralAllowed


def test_tesla_screen_tap_does_not_bypass_other_aol_gates(tesla_screen_card):
  toggles, sm, fp_cs = screen_toggles(), make_sm(), SimpleNamespace(distancePressed=False)
  sm["liveCalibration"].calPerc = 0
  assert not tesla_screen_card.update(screen_state(), fp_cs, sm, toggles).alwaysOnLateralEnabled
  sm["liveCalibration"].calPerc = 100
  sm["starpilotPlan"].lateralCheck = False
  assert not tesla_screen_card.update(make_car_state(), fp_cs, sm, toggles).alwaysOnLateralEnabled
  sm["starpilotPlan"].lateralCheck = True
  cs = make_car_state()
  cs.steeringDisengage = True
  assert not tesla_screen_card.update(cs, fp_cs, sm, toggles).alwaysOnLateralAllowed
  assert not tesla_screen_card.update(make_car_state(), fp_cs, sm, toggles).alwaysOnLateralAllowed


@pytest.mark.parametrize(("brand", "candidate", "flags", "enabled"), (
  ("tesla", spc.TESLA_CAR.TESLA_MODEL_3, 0, True),
  ("tesla", spc.TESLA_CAR.TESLA_MODEL_Y, spc.TeslaFlags.HAS_VEHICLE_BUS, True),
  ("tesla", spc.TESLA_CAR.TESLA_MODEL_X, spc.TeslaFlags.AOL_SCREEN_BUTTON, True),
  ("hyundai", spc.HYUNDAI_CAR.HYUNDAI_IONIQ_6, spc.TeslaFlags.AOL_SCREEN_BUTTON, True),
  ("tesla", spc.TESLA_CAR.TESLA_MODEL_3, spc.TeslaFlags.AOL_SCREEN_BUTTON, False),
))
def test_tesla_screen_toggle_cannot_affect_other_configs(monkeypatch, tmp_path, brand, candidate, flags, enabled):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)
  card = spc.StarPilotCard(SimpleNamespace(brand=brand, carFingerprint=candidate, flags=flags),
                           SimpleNamespace(alternativeExperience=32))
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=True, tesla_aol_screen_tap=enabled)
  assert not card.update(screen_state(), SimpleNamespace(distancePressed=False), make_sm(), toggles).alwaysOnLateralAllowed


def test_tesla_aol_can_be_manually_reenabled_after_brake_release(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="tesla", carFingerprint="TESLA_MODEL_3", pcmCruise=True),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  sm = make_sm()
  toggles = make_toggles(
    always_on_lateral=True,
    always_on_lateral_main=True,
    tesla_aol_disengage_on_brake=True,
  )
  starpilot_car_state = SimpleNamespace(distancePressed=False)

  card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)
  card.update(make_car_state(available=True, brake_pressed=True), starpilot_car_state, sm, toggles)
  released_state = make_car_state(available=True)
  card.update(released_state, starpilot_car_state, sm, toggles)

  assert card._toggle_controller_aol(released_state, toggles) is True
  ret = card.update(released_state, starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_tesla_aol_cannot_be_reenabled_while_brake_is_held(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="tesla", carFingerprint="TESLA_MODEL_Y", pcmCruise=True),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  toggles = make_toggles(
    always_on_lateral=True,
    always_on_lateral_main=True,
    tesla_aol_disengage_on_brake=True,
  )
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  brake_state = make_car_state(available=True, brake_pressed=True)

  card.update(make_car_state(available=True), starpilot_car_state, make_sm(), toggles)
  card.update(brake_state, starpilot_car_state, make_sm(), toggles)

  assert card._toggle_controller_aol(brake_state, toggles) is False
  assert card.always_on_lateral_allowed is False


def test_tesla_brake_disengage_toggle_does_not_change_other_brands(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="gm"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  toggles = make_toggles(
    always_on_lateral=True,
    always_on_lateral_main=True,
    tesla_aol_disengage_on_brake=True,
  )
  starpilot_car_state = SimpleNamespace(distancePressed=False)

  card.update(make_car_state(available=True), starpilot_car_state, make_sm(), toggles)
  card.update(make_car_state(available=True, brake_pressed=True), starpilot_car_state, make_sm(), toggles)
  ret = card.update(make_car_state(available=True), starpilot_car_state, make_sm(), toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_aol_persists_through_longitudinal_speed_too_low_disable(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="gm"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  sm = make_sm()
  sm["selfdriveState"].alertType = f"speedTooLow/{spc.ET.IMMEDIATE_DISABLE}"

  ret = card.update(
    make_car_state(available=True), SimpleNamespace(distancePressed=False), sm,
    make_toggles(always_on_lateral_main=True),
  )

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_aol_still_stops_for_other_immediate_disables(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="gm"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  sm = make_sm()
  sm["selfdriveState"].alertType = f"controlsMismatch/{spc.ET.IMMEDIATE_DISABLE}"

  ret = card.update(
    make_car_state(available=True), SimpleNamespace(distancePressed=False), sm,
    make_toggles(always_on_lateral_main=True),
  )

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is False


def test_non_button_aol_platform_keeps_main_aol_when_main_cruise_is_mapped(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(
    SimpleNamespace(brand="gm"),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )

  toggles = make_toggles(always_on_lateral_main=True, main_cruise_aol_toggle=True)
  ret = card.update(make_car_state(available=True), SimpleNamespace(distancePressed=False), make_sm(), toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


@pytest.mark.parametrize("brand", ["tesla", "gm", "toyota"])
def test_main_aol_without_controller_action_still_follows_cruise_main(monkeypatch, tmp_path, brand):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand=brand, pcmCruise=True),
                           SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL))

  sm = make_sm()
  toggles = make_toggles(always_on_lateral_main=True)
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  ret = card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)

  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True

  ret = card.update(make_car_state(available=False), starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is False
  assert ret.alwaysOnLateralEnabled is False

  ret = card.update(make_car_state(available=True), starpilot_car_state, sm, toggles)
  assert ret.alwaysOnLateralAllowed is True
  assert ret.alwaysOnLateralEnabled is True


def test_pacifica_hybrid_main_aol_waits_for_set_press(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
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


def test_pacifica_hybrid_controller_aol_still_requires_set_press(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)
  card = spc.StarPilotCard(
    SimpleNamespace(brand="chrysler", carFingerprint=CHRYSLER_CAR.CHRYSLER_PACIFICA_2019_HYBRID, pcmCruise=True),
    SimpleNamespace(alternativeExperience=spc.ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL),
  )
  toggles = make_toggles(always_on_lateral=True, always_on_lateral_main=True)
  starpilot_car_state = SimpleNamespace(distancePressed=False)
  counter = spc.CONTROLLER_ACTION_COUNTERS[spc.CONTROLLER_ACTION_TOGGLE_AOL]
  card.params_memory.put_int(counter, 1)

  before_set = card.update(make_car_state(available=True), starpilot_car_state, make_sm(), toggles)
  assert before_set.alwaysOnLateralEnabled is False
  assert card.controller_aol_override is None

  after_set = card.update(make_car_state(available=True, enabled=True), starpilot_car_state, make_sm(), toggles)
  assert after_set.alwaysOnLateralEnabled is True

  card.params_memory.put_int(counter, 2)
  disarmed = card.update(make_car_state(available=True, enabled=True), starpilot_car_state, make_sm(), toggles)
  assert disarmed.alwaysOnLateralEnabled is False
  card.params_memory.put_int(counter, 3)
  rearmed = card.update(make_car_state(available=True), starpilot_car_state, make_sm(), toggles)
  assert rearmed.alwaysOnLateralEnabled is True

  cruise_off = card.update(make_car_state(available=False), starpilot_car_state, make_sm(), toggles)
  assert cruise_off.alwaysOnLateralEnabled is False
  before_next_set = card.update(make_car_state(available=True), starpilot_car_state, make_sm(), toggles)
  assert before_next_set.alwaysOnLateralEnabled is False


def test_conditional_chill_wheel_override_cycles_manual_state(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
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


def test_lkas_button_press_creates_bookmark(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="toyota"), SimpleNamespace(alternativeExperience=0))
  car_state = make_car_state(button_events=[SimpleNamespace(type=spc.ButtonType.lkas, pressed=True)])

  card.update(car_state, SimpleNamespace(distancePressed=False), make_sm(), make_toggles(bookmark_via_lkas=True))

  assert card.params_memory.get_int("WheelButtonBookmarkCounter") == 1


def test_favorite_wheel_action_toggles_hidden_onroad_slot(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  card.params.put("RedneckCruise", False)
  card.params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": False, "key": "RedneckCruise", "label": "Redneck Cruise"},
  ])

  card.handle_button_event("lkas", make_sm(), make_toggles(favorite_1_via_lkas=True))

  assert card.params.get_bool("RedneckCruise") is True
  assert card.params_memory.get_bool("StarPilotTogglesUpdated") is True


def test_favorite_wheel_action_can_press_virtual_resume(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  card.params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": False, "key": FAVORITE_ACTION_DISTANCE_INCREASE, "label": "Distance + / RES"},
  ])

  card.handle_button_event("lkas", make_sm(), make_toggles(favorite_1_via_lkas=True))

  assert card.params_memory.get_int(FAVORITE_ACTION_ACCEL_COUNTER) == 1


def test_favorite_action_toggles_traffic_mode_when_longitudinal_control_is_active(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  card.params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": FAVORITE_ACTION_TOGGLE_TRAFFIC_MODE, "label": "Toggle Traffic Mode"},
  ])

  sm = make_sm()
  sm["carControl"].longActive = True
  card.handle_button_event("lkas", sm, make_toggles(favorite_1_via_lkas=True))

  card.update(make_car_state(), SimpleNamespace(distancePressed=False), sm, make_toggles())

  assert card.traffic_mode_enabled is True
  assert card.params_memory.get_int(FAVORITE_ACTION_TRAFFIC_MODE_COUNTER) == 1


def test_favorite_traffic_mode_action_is_consumed_when_not_active(monkeypatch, tmp_path):
  monkeypatch.setattr(spc, "Params", FakeParams)
  monkeypatch.setattr(spc, "ERROR_LOGS_PATH", tmp_path)

  card = spc.StarPilotCard(SimpleNamespace(brand="gm"), SimpleNamespace(alternativeExperience=0))
  card.params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": FAVORITE_ACTION_TOGGLE_TRAFFIC_MODE, "label": "Toggle Traffic Mode"},
  ])

  sm = make_sm()
  card.handle_button_event("lkas", sm, make_toggles(favorite_1_via_lkas=True))
  card.update(make_car_state(), SimpleNamespace(distancePressed=False), sm, make_toggles())

  assert card.traffic_mode_enabled is False
  assert card._favorite_traffic_mode_counter == 1
