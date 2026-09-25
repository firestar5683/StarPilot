"""Explorer fixed preview must not broaden the admitted Mach-E strategy."""
from types import SimpleNamespace

import pytest

from opendbc.car.ford.explorer_lateral import ExplorerLateralController
from opendbc.car.ford.mache_lateral import MachELateralController
from opendbc.car.ford.values import CAR, CarControllerParams, FordFlags


def model():
  return SimpleNamespace(orientationRate=SimpleNamespace(z=[i * 0.01 for i in range(33)]))


@pytest.mark.parametrize("delay", (0.20, 0.30, 0.40))
def test_explorer_fixed_lookahead_selects_original_model_sample(delay):
  owner = ExplorerLateralController(SimpleNamespace(carFingerprint=CAR.FORD_EXPLORER_MK6, flags=0))
  owner.set_inputs(model(), tuple(i * 0.1 for i in range(33)), delay, True)
  assert owner._curvature_lookahead() == 0.20
  assert owner._predicted_curvature(10.0, owner._curvature_lookahead()) == pytest.approx(0.002)


def test_mach_e_compatibility_keeps_current_provider_lookahead():
  owner = MachELateralController(SimpleNamespace(carFingerprint=CAR.FORD_MUSTANG_MACH_E_MK1, flags=FordFlags.CANFD))
  owner.set_inputs(model(), tuple(i * 0.1 for i in range(33)), 0.40, True)
  assert owner._curvature_lookahead() == 0.40
  assert owner._predicted_curvature(10.0, owner._curvature_lookahead()) == pytest.approx(0.004)


def test_explorer_strategy_rejects_unrelated_topology():
  for car, flags in ((CAR.FORD_EXPLORER_MK6, FordFlags.CANFD),
                     (CAR.FORD_EDGE_MK2, FordFlags.ALT_STEER_ANGLE | FordFlags.NEW_PORT)):
    with pytest.raises(ValueError):
      ExplorerLateralController(SimpleNamespace(carFingerprint=car, flags=flags))


@pytest.mark.parametrize("alpha,release", ((False, False), (True, False), (False, True), (True, True)))
def test_actual_interface_restores_explicit_longitudinal_ownership(alpha, release):
  from opendbc.car import gen_empty_fingerprint
  from opendbc.car.ford.interface import CarInterface
  from opendbc.car.ford.explorer_lateral import qualified
  from opendbc.car.ford.stock_cruise import qualified as stock_switch_qualified
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  cp = CarInterface.get_params(CAR.FORD_EXPLORER_MK6, fp, [], alpha, release, False)
  assert cp.alphaLongitudinalAvailable
  assert cp.openpilotLongitudinalControl == alpha
  assert cp.safetyConfigs[-1].safetyParam == (33 if alpha else 32)
  assert cp.steerActuatorDelay == pytest.approx(.22)
  from openpilot.selfdrive.controls.lib.longcontrol import LongControl
  control = LongControl(cp)
  assert control.pid.k_p == 0.
  assert control.pid.k_i == .5
  assert list(cp.longitudinalTuning.kiV) == [.5]
  assert qualified(cp)
  assert stock_switch_qualified(cp) == (not alpha)


def test_classic_modern_envelope_withdraws_infeasible_speed_transition():
  from opendbc.car.ford.explorer_lateral import bounded_command
  from opendbc.car.ford.lateral_strategy import FordLateralResult
  owner = ExplorerLateralController(SimpleNamespace(carFingerprint=CAR.FORD_EXPLORER_MK6, flags=0))
  result = bounded_command(owner, FordLateralResult(curvature=.02, active=True), .02, 20., .02)
  assert not result.active
  assert result.curvature == owner.curvature_last == 0.
  assert result.path_angle == owner.path_angle_last == 0.


def test_manual_turn_withdraws_without_mach_e_latch_or_gain_compensation():
  from opendbc.car.ford.explorer_lateral import bounded_command
  from opendbc.car.ford.lateral_strategy import FordLateralResult
  owner = ExplorerLateralController(SimpleNamespace(carFingerprint=CAR.FORD_EXPLORER_MK6, flags=0))
  owner.manual_turn_detected = True
  result = bounded_command(owner, FordLateralResult(active=True), .002, 10., .002)
  assert not result.active
  assert result.curvature == 0.
  assert not owner.manual_turn_latched


def test_speed_change_cap_cannot_escape_original_rate_interval():
  from opendbc.car.ford.explorer_lateral import bounded_command
  from opendbc.car.ford.lateral_strategy import FordLateralResult
  owner = ExplorerLateralController(SimpleNamespace(carFingerprint=CAR.FORD_EXPLORER_MK6, flags=0))
  # At26m/s modernjerk admits~.000265, originalnative lookup only.000180.
  # Modern bank-tolerant cap~.005309 requires.000211 fromprevious.005520.
  result = bounded_command(owner, FordLateralResult(curvature=.00552, active=True), .00552, 26., .00552)
  assert not result.active
  assert result.curvature == owner.curvature_last == 0.


def test_actual_long_control_uses_original_zero_p_half_i_and_physical_units():
  from opendbc.car import gen_empty_fingerprint
  from opendbc.car.ford.interface import CarInterface
  from openpilot.selfdrive.controls.lib.longcontrol import LongControl
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  cp = CarInterface.get_params(CAR.FORD_EXPLORER_MK6, fp, [], True, False, False)
  owner = LongControl(cp)
  assert owner.extension is None
  assert owner.pid.k_p == 0.
  assert owner.pid.k_i == .5
  limits = CarInterface.get_pid_accel_limits(cp, 10., 20.)
  assert limits == pytest.approx((-3.5, 2.))
  assert owner.pid.update(0., speed=10., feedforward=.2) == pytest.approx(.2)


def test_typed_offset_eps_and_namespace_guards():
  from opendbc.car import gen_empty_fingerprint, structs
  from opendbc.car.ford.interface import CarInterface
  from opendbc.car.ford.explorer_lateral import qualified
  fp = gen_empty_fingerprint()
  fp[4][0x5A] = 8
  cp = CarInterface.get_params(CAR.FORD_EXPLORER_MK6, fp, [], False, False, False)
  assert len(cp.safetyConfigs) == 2
  assert cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.noOutput
  assert cp.safetyConfigs[-1].safetyParam == 32
  assert qualified(cp)
  cp.alternativeExperience = 1
  assert not qualified(cp)
  cp.alternativeExperience = 0
  cp.safetyConfigs[0].safetyParam = 1
  assert not qualified(cp)
  invalid = structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.eps, request=[b"\x22\xde\x01"], fwVersion=b"bad")
  bad = CarInterface.get_params(CAR.FORD_EXPLORER_MK6, fp, [invalid], False, False, False)
  assert bad.dashcamOnly
  assert bad.safetyConfigs[-1].safetyParam == 0
  assert not qualified(bad)


@pytest.mark.parametrize("sign", (-1., 1.))
def test_final_intersection_preserves_source_rise_and_unwind(sign):
  from opendbc.car.ford.explorer_lateral import bounded_command
  from opendbc.car.ford.lateral_strategy import FordLateralResult
  owner = ExplorerLateralController(SimpleNamespace(carFingerprint=CAR.FORD_EXPLORER_MK6, flags=0))
  rise = bounded_command(owner, FordLateralResult(curvature=sign*.0015, active=True), sign*.001, 26., sign*.001)
  assert rise.curvature == pytest.approx(sign*.00108)
  fall = bounded_command(owner, FordLateralResult(curvature=0., active=True), sign*.001, 26., sign*.001)
  assert fall.curvature == pytest.approx(sign*.00082)


@pytest.mark.parametrize("rate,expected", ((.001024, .00102375), (-.001024, -.001024),
                                           (.00102375, .00102375), (-.00102425, -.001024)))
def test_classic_rate_endpoint_has_correct_decoded_sign(rate, expected):
  from opendbc.can import CANPacker, CANParser
  from opendbc.car import Bus
  from opendbc.car.ford.values import DBC
  from opendbc.car.ford.extended_classic_can import create_extended_classic_lat_ctl_msg
  dbc = DBC[CAR.FORD_EXPLORER_MK6][Bus.pt]
  frame = create_extended_classic_lat_ctl_msg(CANPacker(dbc), SimpleNamespace(main=0), True, 2, 1, 0., rate)
  parser = CANParser(dbc, [("LateralMotionControl", 20)], 0)
  parser.update([(50_000_000, [frame])])
  actual = parser.vl["LateralMotionControl"]["LatCtlCurv_NoRate_Actl"]
  assert actual == pytest.approx(expected, abs=1e-10)
  assert actual * rate > 0.


@pytest.mark.parametrize("sign", (-1., 1.))
def test_measured_recovery_with_empty_source_interval_withdraws(sign):
  from opendbc.car.ford.explorer_lateral import bounded_command
  from opendbc.car.ford.lateral_strategy import FordLateralResult
  owner = ExplorerLateralController(SimpleNamespace(carFingerprint=CAR.FORD_EXPLORER_MK6, flags=0))
  command = bounded_command(owner, FordLateralResult(curvature=sign*.008, active=True), 0., 35., sign*.008)
  assert not command.active and command.curvature == 0.
  assert owner.curvature_last == owner.path_angle_last == 0.


@pytest.mark.parametrize("sign", (-1., 1.))
def test_measured_window_requires_recovery_and_bounds_unwind(sign):
  from opendbc.car.ford.explorer_lateral import bounded_command
  from opendbc.car.ford.lateral_strategy import FordLateralResult
  owner = ExplorerLateralController(SimpleNamespace(carFingerprint=CAR.FORD_EXPLORER_MK6, flags=0))
  # Recovery outside the error window may proceed when source fall permits it.
  recovery = bounded_command(owner, FordLateralResult(curvature=sign*.001, active=True), sign*.003, 35., 0.)
  delta = CarControllerParams.CURVATURE_LIMITS.MAX_LATERAL_JERK / 35.**2 * .05
  assert recovery.active
  assert recovery.curvature == pytest.approx(sign*(.003-delta))
  # Once inside, even an unwind demand cannot leave the measured error window.
  unwind = bounded_command(owner, FordLateralResult(curvature=0., active=True), sign*.00195, 20., sign*.00395)
  assert unwind.active and unwind.curvature == pytest.approx(sign*.00195)
