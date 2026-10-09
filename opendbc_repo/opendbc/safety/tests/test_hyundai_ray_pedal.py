import pytest

from opendbc.can import CANPacker
from opendbc.car import create_gas_interceptor_command
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests.test_hyundai import checksum


@pytest.mark.parametrize("param", [0x9405, 0x9C05, 0x9401, 0x1005, 0])
def test_ray_pedal_tx_isolation_and_limits(param):
  safety = libsafety_py.libsafety
  safety.set_safety_hooks(CarParams.SafetyModel.hyundai, param)
  safety.init_tests()
  safety.set_controls_allowed(True)
  packer = CANPacker("hyundai_kia_ray_pedal")

  def tx(gas):
    addr, dat, bus = create_gas_interceptor_command(packer, gas, 3)
    return safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, dat))

  has_ray_signature = param in (0x9405, 0x9C05)
  assert tx(0) is has_ray_signature
  assert tx(0.55) is has_ray_signature
  assert not tx(0.56)
  assert not tx(0.70)
  assert not tx(1.0)

  if has_ray_signature:
    safety.set_controls_allowed(False)
    assert tx(0)
    assert not tx(0.1)
    safety.set_controls_allowed(True)
    safety.set_gas_pressed_prev(True)
    assert not tx(0.1)
    safety.set_gas_pressed_prev(False)
    addr, dat, bus = create_gas_interceptor_command(packer, 0.1, 3)
    bad_crc = bytearray(dat)
    bad_crc[-1] ^= 1
    assert not safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, bytes(bad_crc)))


def test_ray_pedal_rx_crc_is_checked_only_for_ray_signature():
  safety = libsafety_py.libsafety
  safety.set_safety_hooks(CarParams.SafetyModel.hyundai, 0x9405)
  safety.init_tests()
  dat = bytes.fromhex("01f403d55de8")
  assert safety.safety_rx_hook(libsafety_py.make_CANPacket(0x201, 0, dat))
  bad_crc = bytearray(dat)
  bad_crc[-1] ^= 1
  assert not safety.safety_rx_hook(libsafety_py.make_CANPacket(0x201, 0, bytes(bad_crc)))


def test_ray_native_commanded_gas_does_not_cancel_driver_override_safety():
  safety = libsafety_py.libsafety
  safety.set_safety_hooks(CarParams.SafetyModel.hyundai, 0x9405)
  safety.init_tests()
  safety.set_controls_allowed(True)
  packer = CANPacker("hyundai_kia_ray_pedal")

  physical_rest = bytes.fromhex("010801f30cef")
  native_gas = bytes.fromhex("004e008000ae0700")
  assert safety.safety_rx_hook(libsafety_py.make_CANPacket(0x201, 0, physical_rest))
  assert safety.safety_rx_hook(libsafety_py.make_CANPacket(0x371, 0, native_gas))
  assert not safety.get_gas_pressed_prev()
  addr, dat, bus = create_gas_interceptor_command(packer, 0.1, 3)
  assert safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, dat))

  physical_press = packer.make_can_msg("GAS_SENSOR", 0, {
    "INTERCEPTOR_GAS": (310 - 264) * 0.672,
    "INTERCEPTOR_GAS2": (593 - 497) * 0.332,
    "STATE": 0, "COUNTER_PEDAL": 13,
  })
  press_addr, press_dat, press_bus = physical_press
  assert safety.safety_rx_hook(libsafety_py.make_CANPacket(press_addr, press_bus, press_dat))
  assert safety.get_gas_pressed_prev()
  assert not safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, dat))


def test_non_ray_hyundai_ev_keeps_native_driver_gas_detection():
  safety = libsafety_py.libsafety
  safety.set_safety_hooks(CarParams.SafetyModel.hyundai, 0x1001)
  safety.init_tests()
  native_gas = bytes.fromhex("004e008000ae0700")
  assert safety.safety_rx_hook(libsafety_py.make_CANPacket(0x371, 0, native_gas))
  assert safety.get_gas_pressed_prev()


@pytest.mark.parametrize("controls_allowed", [False, True])
def test_ray_native_cruise_cancel_allowed_during_pedal_override(controls_allowed):
  safety = libsafety_py.libsafety
  safety.set_safety_hooks(CarParams.SafetyModel.hyundai, 0x9405)
  safety.init_tests()
  safety.set_controls_allowed(controls_allowed)
  safety.set_gas_pressed_prev(True)
  packer = CANPacker("hyundai_can_refresh_generated")
  addr, dat, bus = packer.make_can_msg("CLU11", 0, {"CF_Clu_CruiseSwState": 4})
  assert safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, dat))

  pedal_packer = CANPacker("hyundai_kia_ray_pedal")
  addr, dat, bus = create_gas_interceptor_command(pedal_packer, 0.1, 3)
  assert not safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, dat))


def test_ray_standstill_launch_obeys_hardware_brake_override():
  safety = libsafety_py.libsafety
  safety.set_safety_hooks(CarParams.SafetyModel.hyundai, 0x9405)
  safety.init_tests()
  packer = CANPacker("hyundai_can_refresh_generated")
  pedal_packer = CANPacker("hyundai_kia_ray_pedal")

  def rx(name, values):
    addr, dat, bus = checksum(packer.make_can_msg(name, 0, values))
    assert safety.safety_rx_hook(libsafety_py.make_CANPacket(addr, bus, dat))

  def tx(gas):
    addr, dat, bus = create_gas_interceptor_command(pedal_packer, gas, 0)
    return safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, dat))

  rx("WHL_SPD11", {"WHL_SPD_FL": 0, "WHL_SPD_RR": 0})
  assert not safety.get_vehicle_moving()
  rx("TCS13", {"DriverOverride": 2})
  safety.set_controls_allowed(True)
  assert safety.get_brake_pressed_prev()
  assert tx(0)
  assert not tx(0.012)
  rx("TCS13", {"DriverOverride": 0})
  assert not safety.get_brake_pressed_prev()
  assert tx(0.012)
  rx("TCS13", {"DriverOverride": 2})
  assert not tx(0.012)
  assert tx(0)
