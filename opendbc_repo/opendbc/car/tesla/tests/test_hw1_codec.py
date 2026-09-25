import unittest
import pytest
from opendbc.can.packer import CANPacker
from opendbc.can.parser import CANParser
from opendbc.car.interfaces import V_CRUISE_MAX
from opendbc.car.tesla.teslacan_legacy import ModelSHW1CAN
from opendbc.car.tesla.values import CarControllerParams


def codec():
  return ModelSHW1CAN(CANPacker('tesla_can'))


def decode(message, name):
  address, data, bus = message
  parser = CANParser('tesla_can', [(name, 0)], bus)
  parser.update([(1000000000, [(address, data, bus)])])
  return parser.vl[name]


class TestModelSHW1Codec(unittest.TestCase):
  def test_hw1_steering_counter_checksum_and_sign(self):
    for counter in range(32):
      for enabled in [False, True]:
        with self.subTest(counter=counter, enabled=enabled):
          message = codec().create_steering_control(counter, 12.5, enabled)
          address, data, bus = message
          assert (address, len(data), bus) == (1160, 4, 0)
          assert data[-1] == (address & 255) + (address >> 8) + sum(data[:-1]) & 255
          signals = decode(message, 'DAS_steeringControl')
          assert signals['DAS_steeringControlCounter'] == counter % 16
          assert signals['DAS_steeringControlType'] == int(enabled)
          assert signals['DAS_steeringAngleRequest'] == pytest.approx(-12.5, abs=0.05)

  def test_hw1_longitudinal_inactive_cancel_and_command_bounds(self):
    for counter in range(16):
      for accel in [-10.0, -1.0, 0.0, 1.0, 10.0]:
        for active, cancel in [(False, False), (False, True), (True, False), (True, True)]:
          with self.subTest(counter=counter, accel=accel, active=active, cancel=cancel):
            message = codec().create_longitudinal_command(13 if cancel else 4, accel, counter, 10.0, active, False)
            address, data, bus = message
            assert (address, len(data), bus) == (697, 8, 0)
            assert data[-1] == (address & 255) + (address >> 8) + sum(data[:-1]) & 255
            signals = decode(message, 'DAS_control')
            effective = active and (not cancel)
            expected = min(max(accel, CarControllerParams.ACCEL_MIN), CarControllerParams.ACCEL_MAX) if effective else 0.0
            assert signals['DAS_controlCounter'] == counter % 8
            assert signals['DAS_accState'] == (13 if cancel else 4)
            assert signals['DAS_accelMin'] == pytest.approx(expected, abs=0.05)
            assert signals['DAS_accelMax'] == pytest.approx(max(expected, 0), abs=0.05)
            expected_speed = (0 if expected < 0 else V_CRUISE_MAX) if effective else 36.0
            assert signals['DAS_setSpeed'] == pytest.approx(expected_speed, abs=0.1)

  def test_hw1_gas_release_restores_jerk_per_command_and_repress_resets(self):
    commands = codec()
    commands.create_longitudinal_command(4, 0, 0, 10, True, True)
    assert commands.jerk_lower == commands.jerk_upper == 0.0
    for index in range(1, 601):
      message = commands.create_longitudinal_command(4, 0, index, 10, True, False)
      assert commands.jerk_upper == pytest.approx(min(index * 0.0098, 4.9))
      assert commands.jerk_lower == pytest.approx(max(-index * 0.0098, -4.9))
    signals = decode(message, 'DAS_control')
    assert signals['DAS_jerkMin'] == pytest.approx(-4.9, abs=0.04)
    assert signals['DAS_jerkMax'] == pytest.approx(4.9, abs=0.06)
    commands.create_longitudinal_command(4, 0, 0, 10, True, True)
    assert commands.jerk_lower == commands.jerk_upper == 0.0
