"""One classic contract, distinct preview and equipment identities."""
from types import SimpleNamespace

import pytest

from opendbc.car import gen_empty_fingerprint
from opendbc.car.ford.classic_lateral import GENERIC_CLASSIC_CARS, create_controller, qualified
from opendbc.car.ford.interface import CarInterface
from opendbc.car.ford.values import CAR, FordFlags


@pytest.mark.parametrize("car", sorted(GENERIC_CLASSIC_CARS))
@pytest.mark.parametrize("alpha,release", ((False, False), (True, False), (False, True), (True, True)))
def test_actual_classic_identity_and_explicit_long_owner(car, alpha, release):
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  cp = CarInterface.get_params(car, fp, [], alpha, release, False)
  assert cp.alphaLongitudinalAvailable
  assert cp.openpilotLongitudinalControl == alpha
  assert cp.safetyConfigs[-1].safetyParam == (33 if alpha else 32)
  assert cp.steerActuatorDelay == pytest.approx(.22)
  assert qualified(cp)
  from openpilot.selfdrive.controls.lib.longcontrol import LongControl
  control = LongControl(cp)
  assert control.pid.k_p == 0.
  assert control.pid.k_i == .5


@pytest.mark.parametrize("car", sorted(GENERIC_CLASSIC_CARS))
@pytest.mark.parametrize("delay,expected", ((.1, .2), (.3, .3), (.8, .4)))
def test_generic_model_preview_remains_live_delay(car, delay, expected):
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  cp = CarInterface.get_params(car, fp, [], False, False, False)
  owner = create_controller(cp)
  model = SimpleNamespace(orientationRate=SimpleNamespace(z=[i * .01 for i in range(33)]))
  owner.set_inputs(model, tuple(i * .1 for i in range(33)), delay, True)
  assert owner._curvature_lookahead() == expected
  assert owner._predicted_curvature(10., expected) == pytest.approx(expected * .01)


def test_explorer_fixed_preview_is_not_generalized():
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  cp = CarInterface.get_params(CAR.FORD_EXPLORER_MK6, fp, [], False, False, False)
  owner = create_controller(cp)
  owner.set_inputs(None, (), .4, True)
  assert owner._curvature_lookahead() == .2
  cp.flags = int(cp.flags) | int(FordFlags.CANFD)
  assert not qualified(cp)
  assert create_controller(cp) is None


@pytest.mark.parametrize("car", sorted(GENERIC_CLASSIC_CARS))
@pytest.mark.parametrize("automatic,bsm", ((False, False), (True, False), (False, True), (True, True)))
def test_equipment_does_not_change_shared_profile(car, automatic, bsm):
  from opendbc.car import structs
  fp = gen_empty_fingerprint()
  if automatic:
    fp[0][0x5A] = 8
  if bsm:
    fp[0][0x3A6] = fp[0][0x3A7] = 8
  cp = CarInterface.get_params(car, fp, [], False, False, False)
  assert bool(cp.flags & FordFlags.HAS_BSM) == bsm
  assert cp.transmissionType == (structs.CarParams.TransmissionType.automatic if automatic else structs.CarParams.TransmissionType.manual)
  assert cp.minEnableSpeed == pytest.approx(-1. if automatic else 20. * .44704)
  assert cp.safetyConfigs[-1].safetyParam == 32
  assert qualified(cp)


@pytest.mark.parametrize("car", sorted(GENERIC_CLASSIC_CARS))
def test_namespace_and_topology_fail_closed(car):
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  cp = CarInterface.get_params(car, fp, [], False, False, False)
  for word in (0, 1, 2, 18, 34, 35, 65535):
    cp.safetyConfigs[-1].safetyParam = word
    assert not qualified(cp)
  cp.safetyConfigs[-1].safetyParam = 32
  cp.alternativeExperience = 32
  assert qualified(cp)
  cp.safetyConfigs = [cp.safetyConfigs[0], cp.safetyConfigs[0]]
  assert not qualified(cp)
  cp.safetyConfigs = [cp.safetyConfigs[0]]
  for experience in (1, 64, 96):
    cp.alternativeExperience = experience
    assert not qualified(cp)
  cp.alternativeExperience = 0
  for flag in (FordFlags.CANFD, FordFlags.NEW_PORT, FordFlags.LKA_STEERING, FordFlags.ALT_STEER_ANGLE):
    cp.flags = int(flag)
    assert not qualified(cp)
  cp.flags = 0
  cp.passive = True
  assert create_controller(cp) is None


@pytest.mark.parametrize("car", sorted(GENERIC_CLASSIC_CARS))
@pytest.mark.parametrize("valid", (False, True))
def test_actual_eps_capability_gate(car, valid):
  from opendbc.car import structs
  fp = gen_empty_fingerprint()
  fp[0][0x5A] = 8
  fw = structs.CarParams.CarFw.new_message()
  fw.ecu = structs.CarParams.Ecu.eps
  fw.request = [b"\x22\xde\x01"]
  payload = bytearray(24)
  payload[7] = payload[8] = 255 if valid else 0
  fw.fwVersion = bytes(payload)
  cp = CarInterface.get_params(car, fp, [fw.as_reader()], False, False, False)
  assert cp.dashcamOnly == (not valid)
  assert qualified(cp) == valid


def test_actual_explorer_factory_provider_controller_keeps_fixed_preview():
  from unittest.mock import patch
  from opendbc.car import structs
  from opendbc.car.ford.explorer_lateral import ExplorerLateralController
  from openpilot.cereal import messaging
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.selfdrive.modeld.constants import ModelConstants
  from openpilot.starpilot.controller_extensions import configure_controller
  with OpenpilotPrefix():
    params = Params()
    params.put_bool("FordHumanTurnDetection", True, block=True)
    fp = gen_empty_fingerprint()
    fp[0][0x5A] = 8
    cp = CarInterface.get_params(CAR.FORD_EXPLORER_MK6, fp, [], False, False, False)
    ci = CarInterface(cp)
    configure_controller(ci, params)
    assert isinstance(ci.CC.classic_lateral, ExplorerLateralController)
    import time
    now = time.monotonic_ns()
    ci.update([(now - 10_000_000, [])])
    assert not ci.CS.out.canValid  # This is dispatch/transport, not healthy raw-CAN qualification.
    from opendbc.can import CANPacker
    from opendbc.car import Bus
    from opendbc.car.ford.values import DBC
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    speed_frame = packer.make_can_msg("BrakeSysFeatures", 0, {"Veh_V_ActlBrk":36., "VehVActlBrk_D_Qf":3, "VehVActlBrk_No_Cnt":1})
    out = ci.update([(now, [speed_frame])])
    assert out.vEgoRaw == pytest.approx(10., abs=.03)
    assert not out.canValid  # The deliberately partial raw fixture makes no complete health claim.
    model = messaging.new_message("modelV2")
    model.valid = True
    model.logMonoTime = now
    model.modelV2.orientationRate.z = [float(t) * .1 for t in ModelConstants.T_IDXS]
    delay = messaging.new_message("lateralDelay")
    delay.valid = True
    delay.logMonoTime = now
    delay.lateralDelay.lateralDelay = .4
    owner = ci.CC.manual_turn_inputs
    try:
      with patch("openpilot.starpilot.controller_extensions.time.monotonic_ns", return_value=now), \
           patch.object(owner.sm, "update", side_effect=lambda timeout=0: owner.sm.update_msgs(now / 1e9, [model.as_reader(), delay.as_reader()])):
        # An inactive actual controller tick must still transport inputs into the selected owner.
        ci.apply(structs.CarControl().as_reader(), now)
        assert ci.CC.classic_lateral._curvature_lookahead() == .2
        assert ci.CC.classic_lateral._predicted_curvature(10., .2) == pytest.approx(.002)
        assert owner.lateral_snapshot(10.)[2] == pytest.approx(.4)
    finally:
      owner.sm.sock.clear()
      owner.sm.poller = None
      owner.sm = None
      owner.params = None
      params = None
