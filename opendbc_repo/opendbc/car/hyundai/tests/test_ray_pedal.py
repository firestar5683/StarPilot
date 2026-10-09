from types import SimpleNamespace

import pytest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC, HyundaiSafetyFlags
from opendbc.car.structs import CarControl


def ray_fingerprint(sensor_length=6, lfa_length=8):
  fingerprint = gen_empty_fingerprint()
  fingerprint[0][0x201] = sensor_length
  fingerprint[0][0x391] = 8
  fingerprint[2][0x485] = lfa_length
  return fingerprint


@pytest.mark.parametrize(("candidate", "fingerprint", "has_pedal"), [
  (CAR.KIA_RAY_EV, ray_fingerprint(), True),
  (CAR.KIA_RAY_EV, ray_fingerprint(sensor_length=8), False),
  (CAR.KIA_RAY_EV, ray_fingerprint(lfa_length=4), False),
  (CAR.HYUNDAI_KONA_EV_NON_SCC, ray_fingerprint(), False),
])
def test_ray_pedal_fingerprint_isolation(candidate, fingerprint, has_pedal):
  CP = CarInterface.get_params(candidate, fingerprint, [], False, False, False, None)
  assert CP.enableGasInterceptorDEPRECATED is has_pedal
  assert CP.openpilotLongitudinalControl is has_pedal
  if has_pedal:
    assert not CP.pcmCruise
    assert CP.safetyConfigs[-1].safetyParam == 0x9405
    assert CP.minEnableSpeed == -1.0
    assert not CP.autoResumeSng
    FPCP = CarInterface.get_starpilot_params(candidate, fingerprint, [], CP, SimpleNamespace())
    assert FPCP.canUsePedal
    assert not FPCP.pcmCruiseSpeed
    assert not FPCP.redneckCruiseAvailable
  else:
    assert CP.pcmCruise
    assert not (CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)


def test_ray_pedal_safety_signature_is_unique_across_hyundai_platforms():
  for candidate in CAR:
    for alpha_long in (False, True):
      CP = CarInterface.get_params(candidate, ray_fingerprint(), [],
                                   alpha_long, False, False, None)
      has_ray_signature = (CP.safetyConfigs[-1].safetyParam & ~(32 | 128 | 2048)) == 0x9405
      assert has_ray_signature is (candidate == CAR.KIA_RAY_EV)
      assert CP.enableGasInterceptorDEPRECATED is (candidate == CAR.KIA_RAY_EV)


def test_ray_pedal_parser_validates_actual_route_frames():
  CP = CarInterface.get_params(CAR.KIA_RAY_EV, ray_fingerprint(), [], False, False, False, None)
  parser = CarState(CP, None).get_can_parsers(CP)[Bus.party]
  assert parser.dbc_name == "hyundai_kia_ray_pedal"
  # Consecutive bus-0 GAS_SENSOR frames from Sept. 15 Ray rlog segment 4.
  samples = [bytes.fromhex(s) for s in (
    "01f403d55de8", "01f603d55ef1", "01f403d55f51", "01f603d3503f",
    "01f903d551ab", "01f903d552a4", "01f703d55370",
  )]
  for idx, dat in enumerate(samples):
    parser.update([(1_000_000_000 + idx * 20_000_000, [(0x201, dat, 0)])])
    assert parser.can_valid
    assert parser.vl["GAS_SENSOR"]["STATE"] == 5  # FAULT_TIMEOUT: no 0x200 was sent

  prior = parser.vl_raw["GAS_SENSOR"]
  bad = bytearray(samples[-1])
  bad[-1] ^= 1
  parser.update([(1_160_000_000, [(0x201, bytes(bad), 0)])])
  assert parser.vl_raw["GAS_SENSOR"] == prior


def test_ray_pedal_fault_clears_only_with_healthy_sensor_state():
  CP = CarInterface.get_params(CAR.KIA_RAY_EV, ray_fingerprint(), [], False, False, False, None)
  state = CarState(CP, None)
  parsers = state.get_can_parsers(CP)
  packer = CANPacker("hyundai_kia_ray_pedal")
  sensor = packer.make_can_msg("GAS_SENSOR", 0, {
    "INTERCEPTOR_GAS": 0, "INTERCEPTOR_GAS2": 0,
    "STATE": 0, "COUNTER_PEDAL": 1,
  })
  for parser in parsers.values():
    parser.update([(1_000_000_000, [sensor])])
  ret, _ = state.update(parsers, SimpleNamespace())
  assert state.ray_pedal_valid
  assert state.ray_pedal_state == 0
  assert not ret.accFaulted


def test_ray_driver_override_uses_physical_interceptor_tracks():
  CP = CarInterface.get_params(CAR.KIA_RAY_EV, ray_fingerprint(), [], False, False, False, None)
  state = CarState(CP, None)
  parsers = state.get_can_parsers(CP)
  native_gas = (0x371, bytes.fromhex("004e008000ae0700"), 0)
  physical_rest = (0x201, bytes.fromhex("010801f30cef"), 0)
  for parser in parsers.values():
    parser.update([(1_000_000_000, [native_gas, physical_rest])])
  ret, _ = state.update(parsers, SimpleNamespace())
  assert state.ray_pedal_valid
  assert not ret.gasPressed

  packer = CANPacker("hyundai_kia_ray_pedal")
  physical_press = packer.make_can_msg("GAS_SENSOR", 0, {
    "INTERCEPTOR_GAS": (310 - 264) * 0.672,
    "INTERCEPTOR_GAS2": (593 - 497) * 0.332,
    "STATE": 0, "COUNTER_PEDAL": 13,
  })
  for parser in parsers.values():
    parser.update([(1_020_000_000, [physical_press])])
  ret, _ = state.update(parsers, SimpleNamespace())
  assert ret.gasPressed


def test_ray_without_pedal_keeps_native_gas_detection():
  CP = CarInterface.get_params(CAR.KIA_RAY_EV, ray_fingerprint(sensor_length=8), [], False, False, False, None)
  assert not CP.enableGasInterceptorDEPRECATED
  state = CarState(CP, None)
  parsers = state.get_can_parsers(CP)
  assert Bus.party not in parsers
  native_gas = (0x371, bytes.fromhex("004e008000ae0700"), 0)
  for parser in parsers.values():
    parser.update([(1_000_000_000, [native_gas])])
  ret, _ = state.update(parsers, SimpleNamespace())
  assert ret.gasPressed


@pytest.mark.parametrize("speed", [0.0, 0.1, 1.0, 4.9, 5.0, 12.0])
def test_ray_controller_heartbeats_and_only_actuates_when_ready(speed):
  CP = CarInterface.get_params(CAR.KIA_RAY_EV, ray_fingerprint(), [], False, False, False, None)
  controller = CarController(DBC[CP.carFingerprint], CP)
  parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS11", 0), ("CLU11", 0)], 0)
  CS = SimpleNamespace(
    lkas11=parser.vl["LKAS11"], clu11=parser.vl["CLU11"],
    out=SimpleNamespace(vEgo=speed, gasPressed=False, brakePressed=False,
                        cruiseState=SimpleNamespace(enabled=False)),
    ray_pedal_valid=True, ray_pedal_state=5, is_metric=True,
  )
  CC = SimpleNamespace(
    enabled=True, longActive=True, latActive=True,
    cruiseControl=SimpleNamespace(cancel=False, resume=False, override=False),
  )
  hud = SimpleNamespace(
    visualAlert=CarControl.HUDControl.VisualAlert.none,
    setSpeed=20.0,
    leftLaneVisible=True, rightLaneVisible=True,
    leftLaneDepart=False, rightLaneDepart=False,
  )
  actuators = SimpleNamespace(longControlState=CarControl.Actuators.LongControlState.pid)

  def pedal_msg(accel, frame):
    controller.frame = frame
    messages = controller.create_can_msgs(True, 0, False, 0.0, accel, False,
                                          hud, actuators, CS, CC, 2, 0)
    return next(dat for addr, dat, bus in messages if addr == 0x200 and bus == 0)

  assert pedal_msg(2.0, 0)[:4] == bytes(4)  # fault timeout: heartbeat only
  CS.ray_pedal_state = 0
  assert pedal_msg(2.0, 4)[:4] != bytes(4)
  CS.out.gasPressed = True
  assert pedal_msg(2.0, 8)[:4] == bytes(4)
  CS.out.gasPressed = False
  assert pedal_msg(-1.0, 12)[:4] == bytes(4)  # decel = EV lift/regen, not gas
  CS.out.cruiseState.enabled = True
  controller.frame = 16
  messages = controller.create_can_msgs(True, 0, False, 0.0, 2.0, False,
                                        hud, actuators, CS, CC, 2, 0)
  assert next(dat for addr, dat, bus in messages if addr == 0x200 and bus == 0)[4] & 0x80
  assert any(addr == 0x4F1 and bus == 0 and dat[0] & 7 == 4 for addr, dat, bus in messages)

  CS.out.cruiseState.enabled = False
  CS.out.brakePressed = True
  assert pedal_msg(2.0, 20)[:4] == bytes(4)
  CS.out.brakePressed = False
  assert pedal_msg(2.0, 24)[4] & 0x80
  assert controller._ray_pedal_gas_last == pytest.approx(0.02)
  assert pedal_msg(2.0, 28)[4] & 0x80
  assert controller._ray_pedal_gas_last == pytest.approx(0.04)
  CS.out.brakePressed = True
  assert pedal_msg(2.0, 32)[:4] == bytes(4)
  assert controller._ray_pedal_gas_last == 0.0
  CS.out.brakePressed = False
  assert pedal_msg(2.0, 36)[4] & 0x80
  assert controller._ray_pedal_gas_last == pytest.approx(0.02)

  CC.longActive = False
  assert pedal_msg(2.0, 40)[:4] == bytes(4)
  CC.longActive = True
  CC.cruiseControl.override = True
  assert pedal_msg(2.0, 44)[:4] == bytes(4)
  CC.cruiseControl.override = False
  CS.ray_pedal_valid = False
  assert pedal_msg(2.0, 48)[:4] == bytes(4)
  CS.ray_pedal_valid = True
  for fault in range(1, 6):
    CS.ray_pedal_state = fault
    assert pedal_msg(2.0, 48 + 4 * fault)[:4] == bytes(4)

  CS.ray_pedal_state = 0
  CS.out.vEgo = 10.0
  assert pedal_msg(0.0, 72)[4] & 0x80
  assert pedal_msg(-1.0, 76)[:4] == bytes(4)

  CS.out.vEgo = 12.0
  for frame in range(80, 80 + 4 * 40, 4):
    pedal_msg(1.5, frame)
  assert controller._ray_pedal_gas_last == pytest.approx(0.55)
  for frame in range(240, 240 + 4 * 12, 4):
    dat = pedal_msg(-1.5, frame)
  assert dat[:4] == bytes(4)

  for frame in range(288, 288 + 4 * 40, 4):
    pedal_msg(1.5, frame)
  assert controller._ray_pedal_gas_last == pytest.approx(0.55)
  hud.setSpeed = 12.0
  pedal_msg(1.5, 448)
  assert controller._ray_pedal_gas_last == pytest.approx(0.55 * 0.65)
  hud.setSpeed = 11.8
  dat = pedal_msg(1.5, 452)
  assert controller._ray_pedal_gas_last == pytest.approx(0.55 * 0.65 * 0.6)
  assert dat[4] & 0x80
  hud.setSpeed = 11.4
  assert pedal_msg(1.5, 456)[:4] == bytes(4)
  hud.setSpeed = float('nan')
  assert pedal_msg(1.5, 460)[:4] == bytes(4)
  hud.setSpeed = 20.0
  assert pedal_msg(-0.3, 464)[:4] == bytes(4)
  CS.out.vEgo = 15.0
  hud.setSpeed = 53.0 / 3.6
  pedal_msg(-0.16, 468)
  assert controller._ray_pedal_gas_last < 0.1
  CS.out.vEgo = 12.0
  hud.setSpeed = 8.0 / 3.6
  assert pedal_msg(-0.3, 472)[:4] == bytes(4)
  hud.setSpeed = 145.0 / 3.6
  assert pedal_msg(1.5, 476)[4] & 0x80
  assert controller._ray_pedal_gas_last == pytest.approx(0.02)
  assert pedal_msg(1.5, 480)[4] & 0x80
  assert controller._ray_pedal_gas_last == pytest.approx(0.04)
  assert pedal_msg(-0.3, 484)[:4] == bytes(4)


@pytest.mark.parametrize("candidate", [CAR.KIA_RAY_EV, CAR.HYUNDAI_KONA_EV_NON_SCC])
def test_ray_stock_cruise_cancellation_survives_accelerator_override(candidate):
  CP = CarInterface.get_params(candidate, ray_fingerprint(), [], False, False, False, None)
  controller = CarController(DBC[CP.carFingerprint], CP)
  parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS11", 0), ("CLU11", 0)], 0)
  CS = SimpleNamespace(
    lkas11=parser.vl["LKAS11"], clu11=parser.vl["CLU11"],
    out=SimpleNamespace(vEgo=12.0, gasPressed=True, brakePressed=False,
                        cruiseState=SimpleNamespace(enabled=True)),
    ray_pedal_valid=True, ray_pedal_state=0, is_metric=True,
  )
  CC = SimpleNamespace(
    enabled=True, longActive=False, latActive=True,
    cruiseControl=SimpleNamespace(cancel=False, resume=False, override=True),
  )
  hud = SimpleNamespace(
    visualAlert=CarControl.HUDControl.VisualAlert.none,
    setSpeed=20.0,
    leftLaneVisible=True, rightLaneVisible=True, leftLaneDepart=False, rightLaneDepart=False,
  )
  actuators = SimpleNamespace(longControlState=CarControl.Actuators.LongControlState.off)
  controller._create_can_redneck_button_messages = lambda _: []

  def messages(frame):
    controller.frame = frame
    return controller.create_can_msgs(True, 0, False, 0.0, 2.0, False,
                                      hud, actuators, CS, CC, 2, 0)

  def cancel_frames(msgs):
    return [dat for addr, dat, bus in msgs if addr == 0x4F1 and bus == 0 and dat[0] & 7 == 4]

  msgs = messages(20)
  assert bool(cancel_frames(msgs)) is (candidate == CAR.KIA_RAY_EV)
  if candidate == CAR.KIA_RAY_EV:
    pedal = next(dat for addr, dat, bus in msgs if addr == 0x200 and bus == 0)
    assert pedal[:4] == bytes(4)
    assert not (pedal[4] & 0x80)
    assert not cancel_frames(messages(24))  # retain the existing cancellation rate limit
    assert cancel_frames(messages(25))
    assert cancel_frames(messages(32))

  CS.out.cruiseState.enabled = False
  assert not cancel_frames(messages(44))
  CS.out.cruiseState.enabled = True
  CC.enabled = False
  assert not cancel_frames(messages(56))  # AOL alone must not cancel native cruise
