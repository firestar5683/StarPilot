from types import SimpleNamespace

import pytest

from opendbc.car.subaru.carcontroller import CarController
from opendbc.car.subaru.fingerprints import FW_VERSIONS
from opendbc.car.subaru.interface import CarInterface
from opendbc.car.subaru.values import CAR, SubaruFlags, SubaruSafetyFlags
from opendbc.car.structs import CarParams


def make_sng_controller(flags=0, prev_close_distance=4.0):
  controller = object.__new__(CarController)
  controller.CP = SimpleNamespace(flags=flags)
  controller.frame = 60
  controller.last_standstill_frame = 0
  controller.prev_close_distance = prev_close_distance
  controller.epb_resume_frames_remaining = -1
  return controller


def make_sng_state(close_distance=4.0, standstill=True):
  cc = SimpleNamespace(enabled=True, hudControl=SimpleNamespace(leadVisible=True))
  cs = SimpleNamespace(
    close_distance=close_distance,
    out=SimpleNamespace(standstill=standstill),
  )
  return cc, cs


def test_global_sng_keeps_standstill_alive_without_manual_parking_brake_toggle():
  controller = make_sng_controller()
  cc, cs = make_sng_state()

  throttle_cmd, speed_cmd = controller.stop_and_go(cc, cs, manual_parking_brake=False)

  assert throttle_cmd is False
  assert speed_cmd is True


def test_manual_parking_brake_sng_still_sends_resume_throttle():
  controller = make_sng_controller(prev_close_distance=3.9)
  cc, cs = make_sng_state(close_distance=4.0)

  throttle_cmd, speed_cmd = controller.stop_and_go(cc, cs, manual_parking_brake=True)

  assert throttle_cmd is True
  assert speed_cmd is True


def test_preglobal_sng_does_not_send_standstill_keepalive_without_manual_toggle():
  controller = make_sng_controller(flags=SubaruFlags.PREGLOBAL)
  cc, cs = make_sng_state()

  throttle_cmd, speed_cmd = controller.stop_and_go(cc, cs, manual_parking_brake=False)

  assert throttle_cmd is False
  assert speed_cmd is False


class TestSubaruFingerprint:
  def test_fw_version_format(self):
    for platform, fws_per_ecu in FW_VERSIONS.items():
      for (ecu, _, _), fws in fws_per_ecu.items():
        fw_size = len(fws[0])
        for fw in fws:
          assert len(fw) == fw_size, f"{platform} {ecu}: {len(fw)} {fw_size}"


ANGLE_PLATFORMS = (
  CAR.SUBARU_FORESTER_2022,
  CAR.SUBARU_OUTBACK_2023,
  CAR.SUBARU_ASCENT_2023,
  CAR.SUBARU_CROSSTREK_2025,
)


@pytest.mark.parametrize("platform", ANGLE_PLATFORMS)
def test_angle_platform_params(platform):
  CP = CarInterface.get_non_essential_params(platform)

  assert CP.flags & SubaruFlags.LKAS_ANGLE
  assert CP.steerControlType == CarParams.SteerControlType.angle
  assert CP.safetyConfigs[0].safetyParam & SubaruSafetyFlags.LKAS_ANGLE
  assert not CP.dashcamOnly
  assert not CP.alphaLongitudinalAvailable


def test_torque_platform_does_not_enable_angle_safety():
  CP = CarInterface.get_non_essential_params(CAR.SUBARU_IMPREZA_2020)

  assert not (CP.flags & SubaruFlags.LKAS_ANGLE)
  assert CP.steerControlType == CarParams.SteerControlType.torque
  assert not (CP.safetyConfigs[0].safetyParam & SubaruSafetyFlags.LKAS_ANGLE)


def test_angle_controller_tracks_driver_override():
  CP = CarInterface.get_non_essential_params(CAR.SUBARU_CROSSTREK_2025)
  controller = CarController({}, CP)
  CC = SimpleNamespace(latActive=True, actuators=SimpleNamespace(steeringAngleDeg=15.0))
  CS = SimpleNamespace(out=SimpleNamespace(vEgoRaw=15.0, steeringAngleDeg=2.0, steeringTorque=250.0))

  msg = controller.lateral_angle(CC, CS)

  assert controller.driver_override
  assert controller.apply_steer_last == CS.out.steeringAngleDeg
  assert msg[0] == 0x124
