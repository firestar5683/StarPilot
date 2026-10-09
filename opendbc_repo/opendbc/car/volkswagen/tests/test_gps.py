import pytest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus
from opendbc.car.gps import VOLKSWAGEN_TAOS_GPS_MESSAGES, get_car_gps_config, parse_volkswagen_taos_can_gps
from opendbc.car.volkswagen.carstate import CarState
from opendbc.car.volkswagen.interface import CarInterface
from opendbc.car.volkswagen.values import CAR, DBC


# Synthetic frames, not route data: 40 N / 110 W, 12.5 m/s westbound,
# altitude 300 m, UTC 1,800,000,000, ten satellites, packet ID 2.
GPS_FRAMES = (
  (0x36F, bytes.fromhex("02688909e09da31d"), 0),
  (0x374, bytes.fromhex("02c0a83200000000"), 0),
  (0x378, bytes.fromhex("0221415290010000"), 0),
  (0x37B, bytes.fromhex("00d2496b7f4c0900"), 0),
)


@pytest.fixture
def gps_state():
  cp = CarInterface.get_non_essential_params(CAR.VOLKSWAGEN_TAOS_MK1)
  state = CarState(cp, None)
  parsers = state.get_can_parsers(cp)
  return state, parsers


def decode_frames(frames=GPS_FRAMES):
  parser = CANParser("vw_mqb", [(name, 0) for name in VOLKSWAGEN_TAOS_GPS_MESSAGES], 0)
  parser.update([(1_000_000_000, list(frames))])
  return parser, [parser.vl[name] for name in VOLKSWAGEN_TAOS_GPS_MESSAGES]


def test_synthetic_gps_frame_decode():
  parser, values = decode_frames()
  gps = parse_volkswagen_taos_can_gps(*values)
  assert parser.can_valid
  assert gps["hasFix"]
  assert gps["latitude"] == pytest.approx(40.0)
  assert gps["longitude"] == pytest.approx(-110.0)
  assert gps["speed"] == 12.5
  assert gps["bearingDeg"] == 270.0
  assert gps["altitude"] == 300.0
  assert gps["unixTimestampMillis"] == 1_800_000_000_000
  assert gps["satelliteCount"] == 10
  assert gps["vNED"] == pytest.approx([0.0, -12.5, 0.0])


def test_unvalidated_hemisphere_is_not_a_fix():
  frames = ((0x36F, bytes.fromhex("02688929e09da319"), 0), *GPS_FRAMES[1:])
  _, values = decode_frames(frames)
  gps = parse_volkswagen_taos_can_gps(*values)
  assert not gps["hasFix"]
  assert gps["vNED"] == [0.0, 0.0, 0.0]


@pytest.mark.parametrize("message,signal,value", (
  (0, "GNSS_LatitudeMagnitude", 91.0),
  (0, "GNSS_LongitudeMagnitude", 181.0),
  (0, "GNSS_LatitudeMagnitude", float("nan")),
  (0, "GNSS_PositionStatus", 0),
  (0, "GNSS_PositionStatus", 1),
  (0, "GNSS_PositionStatus", 2),
  (3, "GNSS_Empfaenger_Status", 0),
  (3, "GNSS_Genutzte_Satelliten", 0),
  (3, "GNSS_Genutzte_Satelliten", 3),
))
def test_invalid_solution_is_not_a_fix(message, signal, value):
  _, values = decode_frames()
  values[message][signal] = value
  gps = parse_volkswagen_taos_can_gps(*values)
  assert not gps["hasFix"]
  assert gps["speed"] == 0.0
  assert gps["vNED"] == [0.0, 0.0, 0.0]


def test_no_constellation_or_null_position_is_not_a_fix():
  _, values = decode_frames()
  values[3]["GNSS_GPS_in_Nutzung"] = values[3]["GNSS_GLONASS_in_Nutzung"] = 0
  assert not parse_volkswagen_taos_can_gps(*values)["hasFix"]
  values[3]["GNSS_GPS_in_Nutzung"] = 1
  values[0]["GNSS_LatitudeMagnitude"] = values[0]["GNSS_LongitudeMagnitude"] = 0
  assert not parse_volkswagen_taos_can_gps(*values)["hasFix"]


def test_initial_clock_and_mixed_epochs_are_rejected():
  _, values = decode_frames()
  values[3]["GNSS_UTC_Zeit"] = 0
  assert parse_volkswagen_taos_can_gps(*values) is None
  values[3]["GNSS_UTC_Zeit"] = 1_800_000_000
  values[1]["GNSS_Nachrichtenpaket_ID2"] = 1
  assert parse_volkswagen_taos_can_gps(*values) is None


def test_invalid_motion_and_altitude_have_unknown_accuracy():
  _, values = decode_frames()
  values[1]["GNSS_Speed"] = 127.75
  values[1]["GNSS_Bearing"] = 409.5
  values[2]["GNSS_Ortung_Hoehe"] = 7690.0
  gps = parse_volkswagen_taos_can_gps(*values)
  assert gps["hasFix"]
  assert gps["speed"] == gps["bearingDeg"] == gps["altitude"] == 0.0
  assert gps["bearingAccuracyDeg"] == 180.0
  assert gps["speedAccuracy"] == 100.0
  assert gps["verticalAccuracy"] == 500.0
  assert gps["vNED"] == [0.0, 0.0, 0.0]


def test_unknown_course_does_not_report_accurate_zero_velocity():
  _, values = decode_frames()
  values[1]["GNSS_Bearing"] = 409.5
  gps = parse_volkswagen_taos_can_gps(*values)
  assert gps["hasFix"]
  assert gps["speed"] == 12.5
  assert gps["speedAccuracy"] == 100.0
  assert gps["vNED"] == [0.0, 0.0, 0.0]


def test_gps_is_only_enabled_for_the_taos():
  for model in (CAR.VOLKSWAGEN_TAOS_MK1, CAR.VOLKSWAGEN_GOLF_MK7, CAR.VOLKSWAGEN_ID4_MK1):
    cp = CarInterface.get_non_essential_params(model)
    state = CarState(cp, None)
    config = get_car_gps_config(cp)
    expected = model == CAR.VOLKSWAGEN_TAOS_MK1
    assert state.car_gps_supported is expected
    assert (config is not None) is expected
    if expected:
      assert config.messages == VOLKSWAGEN_TAOS_GPS_MESSAGES
    cp.brand = "mock"
    assert get_car_gps_config(cp) is None


def test_carstate_update_reads_gps(gps_state):
  state, parsers = gps_state
  parsers[Bus.pt].update([(1_000_000_000, list(GPS_FRAMES))])
  state.update(parsers, None)
  gps = state.get_car_gps()
  assert gps["hasFix"]
  assert gps["timestamp_nanos"] == 1_000_000_000
  assert gps["longitude"] == pytest.approx(-110.0)


def test_partial_startup_and_missing_gps_are_optional(gps_state):
  state, parsers = gps_state
  parser = parsers[Bus.pt]
  packer = CANPacker(DBC[state.CP.carFingerprint][Bus.pt])
  blink = packer.make_can_msg("Blinkmodi_02", parser.bus, {})
  for time in (1_000_000_000, 2_000_000_000):
    parser.update([(time, [blink])])
    state._update_car_gps(parser)
    assert state.get_car_gps() is None
    assert parser.can_valid
  parser.update([(3_000_000_000, list(GPS_FRAMES[:3]))])
  state._update_car_gps(parser)
  assert state.get_car_gps() is None
  assert all(parser.message_states[address].ignore_alive for address, _, _ in GPS_FRAMES)


@pytest.mark.parametrize("dropout", ("missing_position", "frozen_clock", "missing_all"))
def test_gps_dropout_and_recovery(gps_state, dropout):
  state, parsers = gps_state
  parser = parsers[Bus.pt]
  parser.update([(1_000_000_000, list(GPS_FRAMES))])
  state._update_car_gps(parser)
  assert state.get_car_gps()["hasFix"]

  frames = list(GPS_FRAMES)
  if dropout == "missing_position":
    frames = frames[1:]
  elif dropout == "missing_all":
    frames = []
  parser.update([(4_000_000_000, frames)])
  state._update_car_gps(parser)
  assert not state.get_car_gps()["hasFix"]
  assert state.get_car_gps()["timestamp_nanos"] == 4_000_000_000
  assert state.get_car_gps()["speed"] == 0.0

  packer = CANPacker("vw_mqb")
  status = {**parser.vl["GNSS_05"], "GNSS_UTC_Zeit": 1_800_000_004}
  parser.update([(5_000_000_000, [*GPS_FRAMES[:3], packer.make_can_msg("GNSS_05", parser.bus, status)])])
  state._update_car_gps(parser)
  assert state.get_car_gps()["hasFix"]
  assert state.get_car_gps()["unixTimestampMillis"] == 1_800_000_004_000


def test_invalid_receiver_status_clears_existing_fix(gps_state):
  state, parsers = gps_state
  parser = parsers[Bus.pt]
  parser.update([(1_000_000_000, list(GPS_FRAMES))])
  state._update_car_gps(parser)
  status = {**parser.vl["GNSS_05"], "GNSS_Empfaenger_Status": 0}
  packer = CANPacker("vw_mqb")
  parser.update([(2_000_000_000, [*GPS_FRAMES[:3], packer.make_can_msg("GNSS_05", parser.bus, status)])])
  state._update_car_gps(parser)
  assert not state.get_car_gps()["hasFix"]
