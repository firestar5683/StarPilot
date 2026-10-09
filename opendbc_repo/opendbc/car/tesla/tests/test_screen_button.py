from types import SimpleNamespace

import pytest

from cereal import custom
from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.car.tesla.carstate import ButtonType, CarState
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.values import CANBUS, CAR, TeslaFlags, TeslaSafetyFlags


def screen_params(candidate=CAR.TESLA_MODEL_3, enabled=True, bus=CANBUS.vehicle, length=8, alpha_long=False):
  fingerprint = gen_empty_fingerprint()
  if bus is not None:
    fingerprint[bus][0x3DF] = length
  toggles = SimpleNamespace(tesla_aol_screen_tap_requested=enabled, trailer_load_kg=0.0)
  return CarInterface.get_params(candidate, fingerprint, [], alpha_long, False, False, toggles)


@pytest.mark.parametrize("candidate", tuple(CAR))
@pytest.mark.parametrize("enabled", (False, True))
def test_detection_and_safety_flags_are_model_3_y_only(candidate, enabled):
  cp = screen_params(candidate, enabled)
  detected = candidate in (CAR.TESLA_MODEL_3, CAR.TESLA_MODEL_Y)
  assert bool(cp.flags & TeslaFlags.HAS_VEHICLE_BUS) == detected
  assert bool(cp.flags & TeslaFlags.AOL_SCREEN_BUTTON) == (detected and enabled)
  assert any(config.safetyParam & TeslaSafetyFlags.AOL_SCREEN_BUTTON for config in cp.safetyConfigs) == (detected and enabled)


@pytest.mark.parametrize(("bus", "length"), ((None, 8), (0, 8), (2, 8), (1, 7), (1, 4)))
def test_harness_requires_correct_bus_and_length(bus, length):
  cp = screen_params(bus=bus, length=length)
  assert not cp.flags & (TeslaFlags.HAS_VEHICLE_BUS | TeslaFlags.AOL_SCREEN_BUTTON)
  assert not cp.safetyConfigs[0].safetyParam & TeslaSafetyFlags.AOL_SCREEN_BUTTON
  assert Bus.adas not in CarState.get_can_parsers(cp)


@pytest.mark.parametrize("alpha_long", (False, True))
def test_gesture_does_not_select_longitudinal(alpha_long):
  baseline = screen_params(enabled=False, alpha_long=alpha_long)
  enabled = screen_params(alpha_long=alpha_long)
  assert enabled.openpilotLongitudinalControl == baseline.openpilotLongitudinalControl
  assert enabled.pcmCruise == baseline.pcmCruise
  assert enabled.safetyConfigs[0].safetyParam == baseline.safetyConfigs[0].safetyParam | TeslaSafetyFlags.AOL_SCREEN_BUTTON


@pytest.mark.parametrize("enabled", (False, True))
def test_screen_brake_safety_flag_requires_the_gesture_feature(enabled):
  fingerprint = gen_empty_fingerprint()
  fingerprint[1][0x3DF] = 8
  toggles = SimpleNamespace(tesla_aol_screen_tap_requested=enabled, tesla_aol_screen_brake_disengage_requested=True,
                           trailer_load_kg=0.0)
  cp = CarInterface.get_params(CAR.TESLA_MODEL_3, fingerprint, [], False, False, False, toggles)
  assert bool(cp.safetyConfigs[0].safetyParam & TeslaSafetyFlags.AOL_SCREEN_DISENGAGE_ON_BRAKE) == enabled


def test_parser_only_added_with_setting_and_detected_addon():
  assert Bus.adas not in CarState.get_can_parsers(screen_params(enabled=False))
  parser = CarState.get_can_parsers(screen_params())[Bus.adas]
  assert parser.bus == CANBUS.vehicle
  assert parser.message_states[0x3DF].ignore_alive


@pytest.mark.parametrize(("counts", "expected"), (
  ([0, 3, 3, 3, 0, 0, 3, 0], [True, False, True, False]),
  ([3, 3, 0, 3, 0], [False, True, False]),
  ([0, 1, 2, 4, 5, 0], []),
))
def test_touch_edges_and_startup_baseline(counts, expected):
  cp = screen_params()
  fp_cp = custom.StarPilotCarParams.new_message()
  cs = CarState(cp, fp_cp)
  parser = CarState.get_can_parsers(cp)[Bus.adas]
  packer = CANPacker("tesla_model3_vehicle")
  events = []
  for i, count in enumerate(counts):
    parser.update([[int((i + 1) * 0.5e9), [packer.make_can_msg("UI_status2", CANBUS.vehicle, {"UI_activeTouchPoints": count})]]])
    events.extend(cs.update_screen_button(parser))
  assert [event.pressed for event in events if event.type == ButtonType.lkas] == expected
  parser.update([[60_000_000_000, []]])
  assert cs.update_screen_button(parser) == []
  assert parser.can_valid
  assert not parser.bus_timeout


def test_multiple_touch_edges_in_one_update_are_not_lost():
  cp = screen_params()
  fp_cp = custom.StarPilotCarParams.new_message()
  cs = CarState(cp, fp_cp)
  parser = CarState.get_can_parsers(cp)[Bus.adas]
  packer = CANPacker("tesla_model3_vehicle")
  parser.update([[i * 10_000_000, [packer.make_can_msg("UI_status2", 1, {"UI_activeTouchPoints": count})]]
                 for i, count in enumerate((0, 3, 0, 3, 0), 1)])
  assert [event.pressed for event in cs.update_screen_button(parser) if event.type == ButtonType.lkas] == [True, False, True, False]


@pytest.mark.parametrize("length", (0, 3, 4, 5, 6, 7, 9, 12))
def test_malformed_touch_frames_do_not_produce_button_events(length):
  cp = screen_params()
  cs = CarState(cp, custom.StarPilotCarParams.new_message())
  parser = CarState.get_can_parsers(cp)[Bus.adas]
  packer = CANPacker("tesla_model3_vehicle")
  parser.update([[1_000_000_000, [packer.make_can_msg("UI_status2", 1, {"UI_activeTouchPoints": 0})]]])
  cs.update_screen_button(parser)
  address, data, bus = packer.make_can_msg("UI_status2", 1, {"UI_activeTouchPoints": 3})
  parser.update([[2_000_000_000, [(address, data[:length].ljust(length, b"\x00"), bus)]]])
  assert cs.update_screen_button(parser) == []
  assert cs.active_touch_points == 0
  parser.update([[3_000_000_000, [(address, data, bus)]]])
  assert any(event.type == ButtonType.lkas and event.pressed for event in cs.update_screen_button(parser))


def test_button_is_appended_without_changing_cruise_state():
  cp = screen_params()
  fp_cp = custom.StarPilotCarParams.new_message()
  cs = CarState(cp, fp_cp)
  parsers = CarState.get_can_parsers(cp)
  parsers[Bus.party].vl["DI_state"]["DI_cruiseState"] = 0
  packer = CANPacker("tesla_model3_vehicle")
  for count in (0, 3):
    parsers[Bus.adas].update([[1_000_000_000, [packer.make_can_msg("UI_status2", 1, {"UI_activeTouchPoints": count})]]])
    ret, _ = cs.update(parsers, SimpleNamespace())
  assert any(event.type == ButtonType.lkas and event.pressed for event in ret.buttonEvents)
  assert not ret.cruiseState.enabled
  assert not ret.cruiseState.available
