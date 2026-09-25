"""Exact source-owned CAN FD identity/release and physical wire contracts."""
from types import SimpleNamespace
import pytest
from opendbc.car import gen_empty_fingerprint
from opendbc.car.ford.interface import CarInterface
from opendbc.car.ford.generic_canfd_lateral import GENERIC_CANFD_CARS, qualified, bounded_command, SOURCE_ACCEL_CAP
from opendbc.car.ford.lateral_strategy import FordLateralResult
from opendbc.car.ford.values import CAR, FordFlags


@pytest.mark.parametrize("car", sorted(GENERIC_CANFD_CARS))
@pytest.mark.parametrize("alpha,release", ((False,False),(True,False),(False,True),(True,True)))
def test_actual_profile_and_release_long_denial(car, alpha, release):
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  fp[2].update({0x3D6:8,0x186:8})
  cp = CarInterface.get_params(car, fp, [], alpha, release, False)
  assert cp.alphaLongitudinalAvailable == (not release)
  assert cp.openpilotLongitudinalControl == (alpha and not release)
  assert cp.safetyConfigs[-1].safetyParam == (67 if alpha and not release else 66)
  assert cp.steerActuatorDelay == pytest.approx(.22)
  assert qualified(cp)


def test_unknown_identity_flags_and_secoctopology_denied():
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  fp[2].update({0x3D6:8,0x186:8})
  cp = CarInterface.get_params(CAR.FORD_RANGER_MK2, fp, [], False, False, False)
  for flag in (FordFlags.NEW_PORT, FordFlags.LKA_STEERING, FordFlags.ALT_STEER_ANGLE):
    bad = cp.as_reader().as_builder()
    bad.flags = int(bad.flags) | int(flag)
    assert not qualified(bad)
  bad = cp.as_reader().as_builder()
  bad.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  assert not qualified(bad)
  fp[2][0x3D6] = 16
  bad = CarInterface.get_params(CAR.FORD_RANGER_MK2, fp, [], False, False, False)
  assert bad.dashcamOnly and not qualified(bad)


def test_old_canfd_cap_intersection_withdraws_without_history_leak():
  owner = SimpleNamespace(manual_turn_detected=False, curvature_last=.006, path_angle_last=0.)
  command = bounded_command(owner, FordLateralResult(active=True,curvature=.006), .006, 25., 0.)
  assert not command.active and owner.curvature_last == 0. and owner.path_angle_last == 0.
  owner = SimpleNamespace(manual_turn_detected=False, curvature_last=0., path_angle_last=0.)
  command = bounded_command(owner, FordLateralResult(active=True,curvature=.001), 0., 5., 0.)
  assert command.active and abs(command.curvature) <= SOURCE_ACCEL_CAP / 25.


def test_f150_source_metadata_reaches_dynamic_consumers():
  from opendbc.car import STD_CARGO_KG
  from opendbc.car.interfaces import scale_rot_inertia, scale_tire_stiffness
  from opendbc.car.vehicle_model import VehicleModel
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  cp = CarInterface.get_params(CAR.FORD_F_150_MK14, fp, [], False, False, False)
  assert cp.mass == pytest.approx(3334 + STD_CARGO_KG)
  assert cp.wheelbase == pytest.approx(3.99)
  assert cp.rotationalInertia == pytest.approx(scale_rot_inertia(cp.mass, cp.wheelbase))
  front,rear = scale_tire_stiffness(cp.mass, cp.wheelbase, cp.centerToFront, cp.tireStiffnessFactor)
  assert cp.tireStiffnessFront == pytest.approx(front)
  assert cp.tireStiffnessRear == pytest.approx(rear)
  vm = VehicleModel(cp)
  assert vm.m == cp.mass and vm.l == cp.wheelbase


@pytest.mark.parametrize("delay,expected", ((.1,.2),(.3,.3),(.8,.4)))
def test_live_preview_is_not_mache_or_explorer_override(delay, expected):
  from opendbc.car.ford.generic_canfd_lateral import GenericCanfdLateralController
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  cp = CarInterface.get_params(CAR.FORD_RANGER_MK2, fp, [], False, False, False)
  owner = GenericCanfdLateralController(cp)
  model = SimpleNamespace(orientationRate=SimpleNamespace(z=[i*.01 for i in range(33)]))
  owner.set_inputs(model, tuple(i*.1 for i in range(33)), delay, True)
  assert owner._curvature_lookahead() == expected
  assert owner._predicted_curvature(10.,expected) == pytest.approx(expected*.01)


def test_wire_rate_endpoint_does_not_wrap_sign():
  from opendbc.can import CANPacker
  from opendbc.car import Bus
  from opendbc.car.ford.values import DBC
  from opendbc.car.ford.fordcan import CanBus
  from opendbc.car.ford.generic_canfd_can import create_extended_canfd_msg
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  cp = CarInterface.get_params(CAR.FORD_RANGER_MK2, fp, [], False, False, False)
  packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
  for rate,raw in ((-.001024,0),(.001023,2047),(.001024,2047)):
    address,data,bus = create_extended_canfd_msg(packer,CanBus(cp),True,2,1,0.,rate,3)
    assert address == 0x3D6 and bus == 0
    assert ((data[6] << 3) | (data[7] >> 5)) == raw
    # Independent field-based checksum includes actual packed endpoint.
    mode = (data[0] >> 4) & 7
    counter = (data[7] >> 1) & 15
    fields = ((data[2] << 3) | (data[3] >> 5), raw,
              ((data[3] & 31) << 6) | (data[4] >> 2), ((data[4] & 3) << 8) | data[5])
    assert data[1] == 255-((mode+counter+sum(v+(v >> 8) for v in fields)) & 255)


@pytest.mark.parametrize("car", sorted(GENERIC_CANFD_CARS) + [CAR.FORD_MUSTANG_MACH_E_MK1])
def test_actual_camera_lead_parser_and_source_window(car):
  from opendbc.can import CANPacker
  from opendbc.car import Bus
  from opendbc.car.ford.values import DBC, RADAR
  from opendbc.car.ford.radar_interface import RadarInterface
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  cp = CarInterface.get_params(car, fp, [], False, False, False)
  assert not cp.radarUnavailable and DBC[car][Bus.radar] == RADAR.STEER_ASSIST_DATA
  radar = RadarInterface(cp)
  assert radar.rcp is not None and radar.rcp.bus == 2
  packer = CANPacker(RADAR.STEER_ASSIST_DATA)
  tick = 0

  def feed(distance=40., velocity=-1., confidence=3):
    nonlocal tick
    tick += 1
    msg = packer.make_can_msg("Steer_Assist_Data",2,{
      "CmbbObjConfdnc_D_Stat":confidence,"CmbbObjDistLong_L_Actl":distance,
      "CmbbObjRelLong_V_Actl":velocity,"CmbbObjDistLat_L_Actl":1.2})
    return radar.update([(1_000_000_000+tick*50_000_000,[msg])])

  for _ in range(30):
    result = feed()
  assert radar.rcp.can_valid and len(result.points) == 1
  point = result.points[0]
  assert point.dRel == pytest.approx(40.) and point.yRel == pytest.approx(1.2)
  assert point.vRel == pytest.approx(-1.)
  # Exercise the real radard point consumer and typed radarState lead carrier.
  from openpilot.selfdrive.controls.radard import Track, KalmanParams, get_lead, RADAR_TO_CAMERA
  from openpilot.cereal import messaging
  model = messaging.new_message('modelV2')
  model.modelV2.init('leadsV3', 2)
  vision = model.modelV2.leadsV3[0]
  vision.x = [point.dRel + RADAR_TO_CAMERA]
  vision.y = [-point.yRel]
  vision.v = [10. + point.vRel]
  vision.xStd = [1.]
  vision.yStd = [1.]
  vision.vStd = [1.]
  consumer = Track(point.trackId, 10.+point.vRel, KalmanParams(.05))
  consumer.update(point.dRel, point.yRel, point.vRel, 10.+point.vRel)
  lead = get_lead(10., True, {point.trackId:consumer}, vision.as_reader(), 10., .9)
  state = messaging.new_message('radarState')
  state.radarState.leadOne = lead
  decoded = state.as_reader().radarState.leadOne
  assert decoded.present and decoded.radar and decoded.radarTrackId == point.trackId
  assert decoded.dRel == pytest.approx(point.dRel) and decoded.yRel == pytest.approx(point.yRel)
  assert decoded.vRel == pytest.approx(point.vRel)
  track = point.trackId
  expected_window = []
  previous = 40.
  for i in range(1,24):
    distance = 40.-i*.1
    result = feed(distance,0.)
    expected_window.append(distance-previous)
    expected_window = expected_window[-20:]
    assert result.points[0].vRel == pytest.approx(sum(expected_window),abs=1e-5)
    assert result.points[0].trackId == track
    previous = distance
  result = feed(30.,-4.)
  assert result.points[0].trackId != track and not radar.v_rel_history
  assert not feed(confidence=0).points and not radar.v_rel_history
  assert feed(20.,-2.).points[0].vRel == pytest.approx(-2.)
  assert not feed(distance=0).points
  from opendbc.can.parser import CAN_INVALID_CNT
  for tick in range(CAN_INVALID_CNT):
    radar.rcp.update([(10_000_000_000 + tick * 50_000_000, [])])
    radar._update_steer_assist()
  assert not radar.rcp.can_valid and not radar.pts and not radar.v_rel_history


def test_camera_mapping_is_explicit_for_mache():
  from opendbc.car import Bus
  from opendbc.car.ford.values import DBC
  assert DBC[CAR.FORD_MUSTANG_MACH_E_MK1][Bus.radar] == "ford_lincoln_base_pt"


def test_f150_original_wheelbase_changes_real_plant_and_turn_gate():
  from opendbc.car import STD_CARGO_KG
  from opendbc.car.vehicle_model import VehicleModel
  from openpilot.selfdrive.controls.lib.longitudinal_planner import get_cruise_accel
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  cp = CarInterface.get_params(CAR.FORD_F_150_MK14, fp, [], False, False, False)
  assert cp.mass == pytest.approx(3334 + STD_CARGO_KG)
  assert cp.wheelbase == pytest.approx(3.99)
  vm = VehicleModel(cp)
  assert vm.calc_curvature(.1, 0., 0.) == pytest.approx(.1 / (17. * 3.99))
  assert vm.get_steer_from_curvature(.001, 0., 0.) == pytest.approx(.001 * 17. * 3.99)
  # Compare the actual reached turn gate to the prior upstream wheelbase,
  # not a speculative trim or a tuned controller gain. Only this consumer's
  # wheelbase is changed; no alternate source/plant is imported.
  prior = cp.as_reader().as_builder()
  prior.wheelbase = 3.69
  restored = get_cruise_accel(False, 35., 25., 0., 12.4, cp, 1., 0., True)
  upstream = get_cruise_accel(False, 35., 25., 0., 12.4, prior, 1., 0., True)
  assert upstream == pytest.approx(0.)
  assert 0. < restored <= .8


@pytest.mark.parametrize("alpha,release", ((False, False), (True, False), (False, True), (True, True)))
@pytest.mark.parametrize("bsm", (False, True))
def test_mache_camera_source_preserves_exact_factory_words(alpha, release, bsm):
  from opendbc.car.ford.radar_interface import RadarInterface
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  fp[2].update({0x3D6: 8, 0x186: 8})
  if bsm:
    fp[0].update({0x3A6: 8, 0x3A7: 8})
  cp = CarInterface.get_params(CAR.FORD_MUSTANG_MACH_E_MK1, fp, [], alpha, release, False)
  assert cp.safetyConfigs[-1].safetyParam == (19 if alpha and not release else 18)
  assert cp.openpilotLongitudinalControl == (alpha and not release)
  assert not cp.radarUnavailable
  radar = RadarInterface(cp)
  assert radar.rcp.bus == 2 and radar.generic_canfd_lead
