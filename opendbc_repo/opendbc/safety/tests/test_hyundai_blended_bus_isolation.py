"""An upstream RX API lift must preserve the blended PT bus boundary."""
import unittest

from opendbc.safety.tests import test_hyundai_blended
from opendbc.safety.tests.test_hyundai import checksum


class TestHyundaiBlendedBusIsolation(unittest.TestCase):
  def test_wrong_bus_cannot_change_driver_inputs_or_vehicle_moving(self):
    fixture = test_hyundai_blended.TestHyundaiBlendedStock()
    fixture.setUp()
    messages = (
      ('EMS16', {'CF_Ems_AclAct': 10, 'AliveCounter': 0}, checksum,
       lambda safety: safety.get_gas_pressed_prev()),
      ('TCS13', {'DriverOverride': 2, 'AliveCounterTCS': 0}, checksum,
       lambda safety: safety.get_brake_pressed_prev()),
      ('WHL_SPD11', {'WHL_SPD_FL': 10, 'WHL_SPD_RR': 10}, checksum,
       lambda safety: safety.get_vehicle_moving()),
      ('MDPS12', {'CR_Mdps_StrColTq': 100}, None,
       lambda safety: safety.get_torque_driver_max() != 0),
    )
    for name, values, fix, changed in messages:
      for wrong_bus in (0, 2):
        with self.subTest(name=name, wrong_bus=wrong_bus):
          fixture.select(True)  # HDA2 blended powertrain is bus 1.
          safety = fixture.safety
          self.assertFalse(changed(safety))
          packet = fixture.packer.make_can_msg_safety(name, wrong_bus, values, fix_checksum=fix)
          safety.safety_rx_hook(packet)
          self.assertFalse(changed(safety))
          packet = fixture.packer.make_can_msg_safety(name, fixture.bus, values, fix_checksum=fix)
          self.assertTrue(safety.safety_rx_hook(packet))
          self.assertTrue(changed(safety))
