"""Exact first-generation GV70 startup with synthetic captured-CAN evidence."""
import unittest

from opendbc.can.packer import CANPacker
from opendbc.car import Bus, CanData, structs
from opendbc.car.hyundai.ecu_startup import Outcome, stock_copy
from opendbc.car.hyundai.ev6_template import EV6Template
from opendbc.car.hyundai.gv70_startup import eligible
from opendbc.car.hyundai.gv70_template import GV70Template
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC
from openpilot.starpilot.tests import test_ev6_startup as fixture
from openpilot.starpilot.vehicle_startup import VehicleStartupOwner
from opendbc.car.hyundai.tests.test_gv70_template import capture


CAR_ID = CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN


class TestGV70Startup(unittest.TestCase):
  def exercise(self, *args, **kwargs):
    harness = fixture.TestEV6Startup('runTest')
    return harness.exercise(*args, car=CAR_ID, **kwargs)

  def test_actual_prepublication_capture_type_cp_and_suppressed_protocol(self):
    ci, holder, requests = self.exercise()
    self.assertIs(holder.owner.outcome, Outcome.SENT_UNCONFIRMED)
    self.assertIsInstance(ci.CC.adrv_template, GV70Template)
    self.assertNotIsInstance(ci.CC.adrv_template, EV6Template)
    self.assertEqual(ci.CP.safetyConfigs[-1].safetyParam, 0x15)
    self.assertIn(b'\x28\x83\x01', requests)
    self.assertNotIn(b'\x28\x03\x01', requests)
    ci.CP.safetyConfigs[-1].safetyParam ^= 4
    with self.assertRaisesRegex(RuntimeError, 'prepared'):
      holder.seal_publication()

  def test_stock_fallback_and_full_radar_present_absent_cp_equality(self):
    for radar in (False, True):
      candidate, stock = fixture.params(radar=radar, car=CAR_ID), fixture.params(False, radar, CAR_ID)
      self.assertEqual(stock_copy(candidate).to_dict(), stock.to_dict())
      self.assertEqual(candidate.radarUnavailable, not radar)
    for mode, has_capture, expected in (('sent', False, Outcome.STOCK_UNTOUCHED),
                                     ('restored', True, Outcome.STOCK_RESTORED)):
      ci, holder, requests = self.exercise(mode, capture=has_capture)
      self.assertIs(holder.owner.outcome, expected)
      self.assertFalse(ci.CP.openpilotLongitudinalControl)
      self.assertEqual(ci.CP.safetyConfigs[-1].safetyParam, 0x11)
      self.assertIsNone(ci.CC.adrv_template)
      self.assertEqual(b'\x28\x00\x01' in requests, has_capture)
      if not has_capture:
        self.assertEqual(requests, [])

  def test_uncertain_failure_required_owner_and_topology_exclusions(self):
    with self.assertRaisesRegex(RuntimeError, 'restoration unverified'):
      self.exercise('uncertain')
    candidate = fixture.params(car=CAR_ID)
    self.assertTrue(eligible(candidate))
    with self.assertRaisesRegex(RuntimeError, 'matching prepared'):
      VehicleStartupOwner().configure(CarInterface(candidate))
    self.assertIsNone(CarInterface.startup_owner(candidate, (list, lambda frames: None), requested=False))
    candidate.carFingerprint = CAR.GENESIS_GV70_ELECTRIFIED_2ND_GEN
    self.assertFalse(eligible(candidate))
    candidate.carFingerprint = CAR.GENESIS_GV70_1ST_GEN
    self.assertFalse(eligible(candidate))

  def test_actual_wheel_source_to_ordered_controller_gv70_speed_and_ev6_preservation(self):
    for car, template_type in ((CAR_ID, GV70Template), (CAR.KIA_EV6, EV6Template)):
      cp = fixture.params(car=car)
      ci = CarInterface(cp)
      ci.CC.adrv_template = template_type.capture(capture(7))
      packer = CANPacker(DBC[car][Bus.pt])
      command = structs.CarControl()
      command.enabled = True
      outputs = []
      for tick in range(4):
        # Actual four-wheel source feeds CarState raw speed before its KF.
        wheels = dict.fromkeys(('WHL_SpdFLVal', 'WHL_SpdFRVal', 'WHL_SpdRLVal', 'WHL_SpdRRVal'), 36.)
        ci.update([((tick+1)*10_000_000, [CanData(*packer.make_can_msg('WHEEL_SPEEDS', 1, wheels)),
                                        CanData(*packer.make_can_msg('ACCELERATOR', 1, {'GEAR': 4})),
                                        CanData(*packer.make_can_msg('CAM_0x2a4', 2, {}))])])
        _, frames = ci.apply(command.as_reader(), (tick+1)*10_000_000)
        outputs.extend(CanData(*frame) for frame in frames if frame[0] == 0x51)
      self.assertAlmostEqual(ci.CS.out.vEgoRaw, 10.*cp.wheelSpeedFactor)
      self.assertEqual(len(outputs), 4)
      if car == CAR_ID:
        self.assertEqual(int.from_bytes(outputs[-1].dat[8:10], 'little'), round(ci.CS.out.vEgoRaw*100))
      else:
        self.assertEqual(outputs[-1].dat[8:10], capture(7)[8:10])
      self.assertTrue(all(frame.src == 0 and len(frame.dat) == 32 for frame in outputs))
