"""Ford detected BSM must not change the physical steering decoder."""
from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.car.ford.values import CAR, FordFlags
from opendbc.car.ford.interface import CarInterface
from opendbc.car.ford.carstate import CarState


def params(candidate, bsm):
  fingerprint = gen_empty_fingerprint()
  fingerprint[0][0x5A] = 8
  fingerprint[2][0x3D6] = 8
  fingerprint[2][0x186] = 8
  if bsm:
    fingerprint[0][0x3A6] = fingerprint[0][0x3A7] = 8
  return CarInterface.get_params(candidate, fingerprint, [], False, False, False)


def test_edge_alternate_decoder_does_not_create_bsm_subscriptions():
  cp = params(CAR.FORD_EDGE_MK2, False)
  assert cp.flags & FordFlags.ALT_STEER_ANGLE
  assert not cp.flags & FordFlags.HAS_BSM
  state = CarState(cp)
  parsers = state.get_can_parsers(cp)
  result = state.update(parsers)  # actual lazy decoder discovery, no fake health
  names = {message.name for message in parsers[Bus.pt].message_states.values()}
  assert {'ParkAid_Data', 'SteeringPinion_Data_Alt', 'TransGearData'} <= names
  assert 'Side_Detect_L_Stat' not in names and 'Side_Detect_R_Stat' not in names
  assert not result.leftBlindspot and not result.rightBlindspot


def test_detected_bsm_does_not_select_alternate_steering_on_mach_e():
  cp = params(CAR.FORD_MUSTANG_MACH_E_MK1, True)
  assert cp.flags & FordFlags.HAS_BSM
  assert not cp.flags & FordFlags.ALT_STEER_ANGLE
  state = CarState(cp)
  parsers = state.get_can_parsers(cp)
  state.update(parsers)
  pt = {message.name for message in parsers[Bus.pt].message_states.values()}
  camera = {message.name for message in parsers[Bus.cam].message_states.values()}
  assert 'SteeringPinion_Data' in pt
  assert 'ParkAid_Data' not in pt and 'SteeringPinion_Data_Alt' not in pt
  assert {'Side_Detect_L_Stat', 'Side_Detect_R_Stat'} <= camera


def test_edge_bsm_and_alternate_decoder_coexist_with_separate_bits():
  cp = params(CAR.FORD_EDGE_MK2, True)
  assert FordFlags.HAS_BSM & FordFlags.ALT_STEER_ANGLE == 0
  assert cp.flags & FordFlags.HAS_BSM and cp.flags & FordFlags.ALT_STEER_ANGLE
  state = CarState(cp)
  parsers = state.get_can_parsers(cp)
  state.update(parsers)
  names = {message.name for message in parsers[Bus.pt].message_states.values()}
  assert {'ParkAid_Data', 'SteeringPinion_Data_Alt', 'TransGearData',
          'Side_Detect_L_Stat', 'Side_Detect_R_Stat'} <= names
