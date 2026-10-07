from types import SimpleNamespace

import pytest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus
from opendbc.car.gps import (CarGpsTracker, get_car_gps_config, parse_ford_can_gps, parse_volkswagen_taos_can_gps,
                             VOLKSWAGEN_TAOS_GPS_MESSAGES)
from opendbc.car.gm.values import CAR as GM_CAR, DBC as GM_DBC
from opendbc.car.ford.values import DBC as FORD_DBC
from opendbc.car.volkswagen.values import CAR as VW_CAR, DBC as VW_DBC, VolkswagenFlags


VW_FRAMES = [(0x36F, bytes.fromhex('02688909e09da31d'), 0),
             (0x374, bytes.fromhex('02c0a83200000000'), 0),
             (0x378, bytes.fromhex('0221415290010000'), 0),
             (0x37B, bytes.fromhex('00d2496b7f4c0900'), 0)]


def config(brand, identity, flags=0):
  return SimpleNamespace(brand=brand, carFingerprint=identity, flags=flags)


def gm_tracker():
  owner = CarGpsTracker(config('gm', GM_CAR.CHEVROLET_BOLT_CC_2018_2021))
  parser = CANParser('gm_global_a_powertrain_generated', [('TCICOnStarGPSPosition', float('nan'))], 0)
  return owner, parser, CANPacker('gm_global_a_powertrain_generated')


def position(packer, lat=40., lon=-110.):
  return packer.make_can_msg('TCICOnStarGPSPosition', 0, {'GPSLatitude': lat * 3_600_000, 'GPSLongitude': lon * 3_600_000})


@pytest.mark.parametrize('brand,mapping,dbcs', [('gm', GM_DBC, {'gm_global_a_powertrain_generated', 'cadillac_ct6_powertrain'}),
                                              ('ford', FORD_DBC, {'ford_lincoln_base_pt'}),
                                              ('volkswagen', VW_DBC, {'vw_mqb'})])
def test_candidates_are_exact_dbc_contracts(brand, mapping, dbcs):
  for identity, dbcs_by_bus in mapping.items():
    selected = get_car_gps_config(config(brand, identity))
    assert (selected is not None) == (dbcs_by_bus.get(Bus.pt) in dbcs)
    if selected is not None:
      # Actual DBC parser verifies every subscribed message exists, not just brand.
      parser = CANParser(dbcs_by_bus[Bus.pt], [(name, float('nan')) for name in selected.messages], 0)
      assert all(state.ignore_alive for state in parser.message_states.values())


@pytest.mark.parametrize('flags', [VolkswagenFlags.PQ, VolkswagenFlags.MLB, VolkswagenFlags.MEB])
def test_incompatible_vw_topology_excluded(flags):
  assert get_car_gps_config(config('volkswagen', VW_CAR.VOLKSWAGEN_TAOS_MK1, flags)) is None


def test_optional_gps_does_not_create_car_health_dependency():
  owner, parser, packer = gm_tracker()
  for now in (1_000_000_000, 12_000_000_000):
    parser.update([(now, [(1, b'\x00', 0)])])
    owner.update(parser)
    assert parser.can_valid
    assert owner.get() is None
  parser.update([(13_000_000_000, [position(packer)])])
  owner.update(parser)
  assert owner.get()['hasFix']
  parser.update([(16_000_000_000, [(1, b'\x00', 0)])])
  owner.update(parser)
  assert parser.can_valid
  assert owner.get() is None


def test_gm_position_unknown_motion_and_fresh_coordinate_bearing():
  owner, parser, packer = gm_tracker()
  parser.update([(1_000_000_000, [position(packer)])])
  owner.update(parser, speed=10.)
  first = owner.get()
  assert first['latitude'] == pytest.approx(40.)
  assert first['longitude'] == pytest.approx(-110.)
  assert first['vNED'] == [0., 0., 0.]
  assert first['speedAccuracy'] == 100.
  assert first['verticalAccuracy'] == 500.
  parser.update([(2_000_000_000, [position(packer, lat=40.0001)])])
  owner.update(parser, speed=10.)
  assert owner.get()['vNED'] == pytest.approx([10., 0., 0.])
  parser.update([(3_000_000_000, [position(packer, lat=40.0002)])])
  owner.update(parser, speed=10., backward=True)
  assert owner.get()['speedAccuracy'] == 100.
  parser.update([(4_000_000_000, [position(packer, lat=0., lon=0.)])])
  owner.update(parser)
  assert not owner.get()['hasFix']


def test_tracker_requires_each_message_to_advance_and_expires():
  owner = CarGpsTracker(config('volkswagen', VW_CAR.VOLKSWAGEN_TAOS_MK1))
  parser = CANParser('vw_mqb', [(n, float('nan')) for n in VOLKSWAGEN_TAOS_GPS_MESSAGES], 0)
  parser.update([(1_000_000_000, VW_FRAMES)])
  owner.update(parser)
  assert owner.get()['hasFix']
  assert owner.get()['timestamp_nanos'] == 1_000_000_000
  parser.update([(2_000_000_000, VW_FRAMES[:1])])
  owner.update(parser)
  assert owner.get()['timestamp_nanos'] == 1_000_000_000
  parser.update([(3_600_000_000, VW_FRAMES[:1])])
  owner.update(parser)
  assert owner.get() is None
  parser.update([(4_000_000_000, VW_FRAMES[:2])])
  parser.update([(4_200_000_000, VW_FRAMES[2:])])
  owner.update(parser)
  assert owner.get()['hasFix']
  assert owner.get()['timestamp_nanos'] == 4_000_000_000
  parser.update([(3_000_000_000, VW_FRAMES)])
  owner.update(parser)
  assert owner.get() is None


def test_vw_original_hemisphere_and_packet_validation():
  parser = CANParser('vw_mqb', [(n, float('nan')) for n in VOLKSWAGEN_TAOS_GPS_MESSAGES], 0)
  parser.update([(1_000_000_000, VW_FRAMES)])
  values = [dict(parser.vl[n]) for n in VOLKSWAGEN_TAOS_GPS_MESSAGES]
  assert parse_volkswagen_taos_can_gps(*values)['hasFix']
  values[0]['GNSS_LongitudeWest'] = 0
  assert not parse_volkswagen_taos_can_gps(*values)['hasFix']
  values[1]['GNSS_Nachrichtenpaket_ID2'] = 1
  assert parse_volkswagen_taos_can_gps(*values) is None


def test_ford_no_fix_or_unknown_motion_does_not_become_velocity():
  nav1 = {'GpsHsphLattSth_D_Actl': 2, 'GpsHsphLongEast_D_Actl': 2, 'GPS_Latitude_Degrees': 40.,
          'GPS_Longitude_Degrees': 110., 'GPS_Latitude_Minutes': 0., 'GPS_Latitude_Min_dec': 0.,
          'GPS_Longitude_Minutes': 0., 'GPS_Longitude_Min_dec': 0.}
  nav2 = {'GpsUtcYr_No_Actl': 2026, 'GpsUtcMnth_No_Actl': 10, 'GpsUtcDay_No_Actl': 6,
          'GPS_UTC_hours': 12, 'GPS_UTC_minutes': 0, 'GPS_UTC_seconds': 0, 'Gps_B_Falt': 0}
  nav3 = {'GPS_dimension': 2, 'GPS_Speed': 10., 'GPS_Heading': 90., 'GPS_Vdop': 1., 'GPS_Hdop': 1.,
          'GPS_Sat_num_in_view': 8, 'GPS_MSL_altitude': 100.}
  assert parse_ford_can_gps(nav1, nav2, nav3)['hasFix']
  nav2['Gps_B_Falt'] = 1
  no_fix = parse_ford_can_gps(nav1, nav2, nav3)
  assert not no_fix['hasFix']
  assert no_fix['vNED'] == [0., 0., 0.]
  assert no_fix['speedAccuracy'] == 100.
  nav2['Gps_B_Falt'] = 0
  nav3['GPS_Speed'] = 255.
  assert parse_ford_can_gps(nav1, nav2, nav3)['speedAccuracy'] == 100.


@pytest.mark.parametrize('brand', ['gm', 'ford', 'volkswagen'])
def test_actual_carstate_optional_parser_hook(brand):
  from opendbc.car.gm.carstate import CarState as GmState
  from opendbc.car.gm.interface import CarInterface as GmInterface
  from opendbc.car.ford.carstate import CarState as FordState
  from opendbc.car.ford.interface import CarInterface as FordInterface
  from opendbc.car.ford.values import CAR as FORD_CAR
  from opendbc.car.volkswagen.carstate import CarState as VwState
  from opendbc.car.volkswagen.interface import CarInterface as VwInterface

  interface, state_class, identity = {
    'gm': (GmInterface, GmState, GM_CAR.CHEVROLET_BOLT_CC_2018_2021),
    'ford': (FordInterface, FordState, FORD_CAR.FORD_MUSTANG_MACH_E_MK1),
    'volkswagen': (VwInterface, VwState, VW_CAR.VOLKSWAGEN_TAOS_MK1),
  }[brand]
  cp = interface.get_non_essential_params(identity)
  state = state_class(cp)
  parsers = state.get_can_parsers(cp)
  pt = parsers[Bus.pt]
  gps_config = get_car_gps_config(cp)
  assert gps_config is not None
  assert state.car_gps_supported
  assert state.get_car_gps() is None
  for name in gps_config.messages:
    message = pt.dbc.name_to_msg[name]
    assert message.size == 8
    assert pt.message_states[message.address].ignore_alive
  packer = CANPacker(pt.dbc.name)
  if brand == 'gm':
    frames = [position(packer)]
  elif brand == 'volkswagen':
    frames = VW_FRAMES
  else:
    frames = [packer.make_can_msg('APIMGPS_Data_Nav_1_FD1', 0,
              {'GpsHsphLattSth_D_Actl': 2, 'GpsHsphLongEast_D_Actl': 2,
               'GPS_Latitude_Degrees': 40, 'GPS_Longitude_Degrees': 110}),
              packer.make_can_msg('APIMGPS_Data_Nav_2_FD1', 0,
              {'GpsUtcYr_No_Actl': 2026, 'GpsUtcMnth_No_Actl': 10, 'GpsUtcDay_No_Actl': 6}),
              packer.make_can_msg('APIMGPS_Data_Nav_3_FD1', 0, {'GPS_dimension': 2, 'GPS_Sat_num_in_view': 8})]
  frames = [(a, d, pt.bus) for a, d, _ in frames]
  pt.update([(1_000_000_000, frames)])
  state.update(parsers)
  assert state.get_car_gps()['hasFix']
  assert state.get_car_gps()['timestamp_nanos'] == 1_000_000_000


def test_wrong_bus_cannot_create_gps_fix():
  owner, parser, packer = gm_tracker()
  frame = position(packer)
  parser.update([(1_000_000_000, [(frame[0], frame[1], 2)])])
  owner.update(parser)
  assert owner.get() is None


def test_actual_gm_reverse_then_forward_gps_motion():
  from opendbc.car import structs
  from opendbc.car.gm.carstate import CarState
  from opendbc.car.gm.interface import CarInterface

  cp = CarInterface.get_non_essential_params(GM_CAR.CHEVROLET_BOLT_CC_2018_2021)
  state = CarState(cp)
  parsers = state.get_can_parsers(cp)
  pt = parsers[Bus.pt]
  packer = CANPacker(pt.dbc.name)
  for tick in range(120):
    # Reverse gear and reverse wheel travel independently suppress motion estimates.
    gear = 2 if tick < 20 else 4
    direction = 2 if tick < 40 else 1
    frames = [position(packer, lat=40. + tick * .00002),
              packer.make_can_msg('ECMPRDNL2', pt.bus, {'PRNDL2': gear}),
              packer.make_can_msg('EBCMWheelSpdFront', pt.bus, {'FLWheelSpd': 36., 'FRWheelSpd': 36.}),
              packer.make_can_msg('EBCMWheelSpdRear', pt.bus,
                                  {'RLWheelSpd': 36., 'RRWheelSpd': 36., 'RLWheelDir': direction, 'RRWheelDir': direction})]
    pt.update([(1_000_000_000 + tick * 10_000_000, frames)])
    observed = state.update(parsers)
    sample = state.get_car_gps()
    assert sample['hasFix']
    assert observed.gearShifter == (structs.CarState.GearShifter.reverse if gear == 2 else structs.CarState.GearShifter.drive)
    if tick < 40:
      assert sample['speedAccuracy'] == 100.
      assert sample['bearingAccuracyDeg'] == 180.
      assert sample['vNED'] == [0., 0., 0.]
  assert observed.vEgo > 1.
  assert sample['speed'] == observed.vEgo
  assert sample['bearingAccuracyDeg'] == 10.
  assert sample['vNED'][0] > 1.
