"""Palisade camera phase regression; real parser, controller and native hook."""
from unittest.mock import patch

import pytest

from opendbc.car import structs
from opendbc.car.hyundai.blended_stock_aol import MixedCameraSchedule
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.tests.test_blended_stock_aol import MixedReceiveStream, params
from opendbc.safety.tests.libsafety import libsafety_py


@pytest.mark.parametrize('age,delay,healthy,expected', [
  (0, 0, True, True), (10_000_000, 10_000_000, True, True),
  (20_000_001, 0, True, False), (0, 20_000_001, True, False),
  (-1, 0, True, False), (0, 0, False, False),
])
def test_source_age_includes_controller_delay(age, delay, healthy, expected):
  schedule = MixedCameraSchedule(clock=lambda: 1_000_000_000 + delay)
  # Deliberately unrelated BOOTTIME and MONOTONIC epochs.
  source = (900_000_000_000, age, 1_000_000_000)
  assert schedule.due(source, healthy) == expected
  if expected:
    assert not schedule.due(source, True)
    assert not schedule.due((source[0] - 1, 0, source[2]), True)
  assert not schedule.due(None, True)
  assert not schedule.due((source[0] + 1, 0, 2_000_000_000), True)


def test_controller_skips_old_timer_phase_and_sends_new_camera_off_phase():
  cp = params(hda2=True)
  cp.alternativeExperience = 32
  ci = CarInterface(cp)
  stream = MixedReceiveStream(ci)
  safety = libsafety_py.libsafety
  safety.set_alternative_experience(32)
  assert safety.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, 0x2010) == 0
  safety.init_tests()
  command = structs.CarControl()
  for tick in range(31):
    now = stream.now + tick * 10_000_000
    frames = stream.frames(tick)
    safety.set_timer((now // 1000) & 0xffffffff)
    for address, data, bus in frames:
      assert safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data))
    safety.set_aol_test_heartbeat(True)
    safety.safety_tick()
    with patch('time.clock_gettime_ns', return_value=now), patch('time.monotonic_ns', return_value=now):
      cs = ci.update([(now, frames)])
  assert cs.canValid and ci.CS.blended_camera_current
  # Old code would send this 40 ms old copy because controller frame is 0.
  ci.CS.blended_camera_snapshot = (now, 40_000_000, now)
  with patch('time.monotonic_ns', return_value=now):
    _, old = ci.apply(command.as_reader(), now)
  assert not any(address == 0x2a4 for address, _, _ in old)
  now += 50_000_000
  frames = stream.frames(35)
  safety.set_timer((now // 1000) & 0xffffffff)
  for address, data, bus in frames:
    assert safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data))
  with patch('time.clock_gettime_ns', return_value=now), patch('time.monotonic_ns', return_value=now):
    ci.update([(now, frames)])
    _, fresh = ci.apply(command.as_reader(), now)
    _, duplicate = ci.apply(command.as_reader(), now)
  copies = [(address, data, bus) for address, data, bus in fresh if address == 0x2a4]
  assert len(copies) == 1
  assert not any(address == 0x2a4 for address, _, _ in duplicate)
  for address, data, bus in copies:
    assert safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data))
  # A newer camera counter still makes the old copy unsafe; guard stays closed.
  for address, data, bus in stream.frames(40):
    if address == 0x2a4:
      assert safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data))
  for address, data, bus in copies:
    assert not safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data))
