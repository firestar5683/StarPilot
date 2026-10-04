import unittest

from opendbc.can import CANPacker
from opendbc.car import gen_empty_fingerprint
from opendbc.car.ford.fordcan import CanBus, create_acc_msg, create_lat_ctl_msg, create_lka_msg
from opendbc.car.ford.values import FordSafetyFlags
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py


class TestFordThreeSafety(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPacker("ford_lincoln_base_pt")
    self.bus = CanBus(fingerprint=gen_empty_fingerprint())

  @staticmethod
  def packet(msg):
    return libsafety_py.make_CANPacket(msg[0], msg[2], msg[1])

  def init_mode(self, flags):
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.ford, int(flags)), 0)
    self.safety.init_tests()

  def source(self, available):
    return self.packet(self.packer.make_can_msg("Lane_Assist_Data3_FD1", 0,
                                                {"LaActAvail_D_Actl": 3 if available else 0}))

  def denied_source(self):
    return self.packet(self.packer.make_can_msg("Lane_Assist_Data3_FD1", 0,
                                                {"LaActAvail_D_Actl": 3, "LaActDeny_B_Actl": 1}))

  def healthy_inputs(self, speed=20., curvature=0., cruise=True, omit=None):
    for count in range(1, 7):
      self.safety.set_timer(count * 10_000)
      packets = (
        ("BrakeSysFeatures", {"Veh_V_ActlBrk": speed * 3.6, "VehVActlBrk_D_Qf": 3, "VehVActlBrk_No_Cnt": count}),
        ("EngVehicleSpThrottle2", {"Veh_V_ActlEng": speed * 3.6, "VehVActlEng_D_Qf": 3}),
        ("Yaw_Data_FD1", {"VehYaw_W_Actl": curvature * speed, "VehYawWActl_D_Qf": 3, "VehRollYaw_No_Cnt": count}),
        ("EngBrakeData", {"BpedDrvAppl_D_Actl": 1, "CcStat_D_Actl": 5 if cruise else 0}),
        ("EngVehicleSpThrottle", {"ApedPos_Pc_ActlArb": 0}),
        ("DesiredTorqBrk", {"VehStop_D_Stat": 0}),
      )
      for name, values in packets:
        if name == omit:
          continue
        msg = self.packer.make_can_msg(name, 0, values)
        self.assertTrue(self.safety.safety_rx_hook(self.packet(msg)), name)
    self.assertTrue(self.safety.safety_rx_hook(self.source(True)))

  def test_stock_can_ownership_and_existing_mode_is_unchanged(self):
    acc = self.packet(create_acc_msg(self.packer, self.bus, False, -5., 0., False, False, 255.))
    for variant in (FordSafetyFlags.NEW_PORT, FordSafetyFlags.NEW_PORT | FordSafetyFlags.CANFD,
                    FordSafetyFlags.NEW_PORT | FordSafetyFlags.LKA_STEERING):
      with self.subTest(variant=variant):
        self.init_mode(variant)
        self.assertFalse(self.safety.safety_tx_hook(acc))
        self.assertTrue(self.safety.safety_tx_hook(self.packet(create_lka_msg(self.packer, self.bus, transit=True))))
    self.init_mode(FordSafetyFlags.NEW_PORT | FordSafetyFlags.LONG_CONTROL)
    self.assertTrue(self.safety.safety_tx_hook(acc))
    self.init_mode(0)
    self.assertTrue(self.safety.safety_tx_hook(self.packet(create_lka_msg(self.packer, self.bus))))

  def test_transit_lka_requires_source_control_shape_and_rate(self):
    self.init_mode(FordSafetyFlags.NEW_PORT | FordSafetyFlags.LKA_STEERING)
    active = self.packet(create_lka_msg(self.packer, self.bus, True, 1., 2, .0002, transit=True))
    inactive = self.packet(create_lka_msg(self.packer, self.bus, transit=True))
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(active))
    wrong_bus = self.packet(self.packer.make_can_msg("Lane_Assist_Data3_FD1", 2,
                                                      {"LaActAvail_D_Actl": 3}))
    self.safety.safety_rx_hook(wrong_bus)
    self.assertFalse(self.safety.safety_tx_hook(active))
    self.assertTrue(self.safety.safety_rx_hook(self.source(True)))
    self.assertFalse(self.safety.safety_tx_hook(active))  # no speed, yaw or cruise source yet
    self.healthy_inputs()
    self.assertTrue(self.safety.safety_tx_hook(active))
    self.assertFalse(self.safety.safety_tx_hook(self.packet(create_lat_ctl_msg(self.packer, self.bus, True, 0., 0., 0., 0.))))
    self.assertTrue(self.safety.safety_tx_hook(self.packet(create_lat_ctl_msg(self.packer, self.bus, False, 0., 0., 0., 0.))))
    jump = self.packet(create_lka_msg(self.packer, self.bus, True, 5.8, 2, .01023, transit=True))
    self.assertFalse(self.safety.safety_tx_hook(jump))
    malformed = bytearray(active[0].data[0:8])
    malformed[0] = (malformed[0] & 0x1f) | 0x60  # action 3 is not a steering request
    self.assertFalse(self.safety.safety_tx_hook(self.packet((0x3CA, bytes(malformed), 0))))
    self.assertTrue(self.safety.safety_tx_hook(inactive))
    self.assertTrue(self.safety.safety_rx_hook(self.source(False)))
    self.assertFalse(self.safety.safety_tx_hook(active))
    self.assertTrue(self.safety.safety_rx_hook(self.denied_source()))
    self.assertFalse(self.safety.safety_tx_hook(active))
    self.assertTrue(self.safety.safety_rx_hook(self.source(True)))
    self.safety.set_timer(160001)
    self.assertFalse(self.safety.safety_tx_hook(active))

  def test_transit_dynamic_speed_jerk_and_measured_curvature(self):
    self.init_mode(FordSafetyFlags.NEW_PORT | FordSafetyFlags.LKA_STEERING)
    self.healthy_inputs(speed=30.)
    self.assertTrue(self.safety.get_controls_allowed())
    small = self.packet(create_lka_msg(self.packer, self.bus, True, 1., 2, .0001, transit=True))
    jump = self.packet(create_lka_msg(self.packer, self.bus, True, 1., 2, .0006, transit=True))
    static_max = self.packet(create_lka_msg(self.packer, self.bus, True, 1., 2, .01023, transit=True))
    self.assertTrue(self.safety.safety_tx_hook(small))
    self.assertFalse(self.safety.safety_tx_hook(jump))  # 33 Hz jerk envelope
    self.assertFalse(self.safety.safety_tx_hook(static_max))  # speed-based lateral acceleration

    self.init_mode(FordSafetyFlags.NEW_PORT | FordSafetyFlags.LKA_STEERING)
    self.healthy_inputs(speed=30., curvature=-.004)
    self.assertFalse(self.safety.safety_tx_hook(small))  # measured curvature error

  def test_transit_missing_sources_brake_cancel_and_relay(self):
    active = self.packet(create_lka_msg(self.packer, self.bus, True, 1., 2, .0001, transit=True))
    for missing in ("BrakeSysFeatures", "EngVehicleSpThrottle2", "Yaw_Data_FD1", "EngBrakeData"):
      with self.subTest(missing=missing):
        self.init_mode(FordSafetyFlags.NEW_PORT | FordSafetyFlags.LKA_STEERING)
        self.healthy_inputs(omit=missing)
        self.safety.set_controls_allowed(True)
        self.assertFalse(self.safety.safety_tx_hook(active))

    self.init_mode(FordSafetyFlags.NEW_PORT | FordSafetyFlags.LKA_STEERING)
    self.healthy_inputs()
    self.assertTrue(self.safety.safety_tx_hook(active))
    brake = self.packet(self.packer.make_can_msg("EngBrakeData", 0,
                                                 {"BpedDrvAppl_D_Actl": 2, "CcStat_D_Actl": 5}))
    self.assertTrue(self.safety.safety_rx_hook(brake))
    self.assertFalse(self.safety.safety_tx_hook(active))
    cancel = self.packet(self.packer.make_can_msg("EngBrakeData", 0,
                                                  {"BpedDrvAppl_D_Actl": 1, "CcStat_D_Actl": 0}))
    self.assertTrue(self.safety.safety_rx_hook(cancel))
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(active))

    self.init_mode(FordSafetyFlags.NEW_PORT | FordSafetyFlags.LKA_STEERING)
    self.healthy_inputs()
    self.safety.safety_rx_hook(active)
    self.assertFalse(self.safety.safety_tx_hook(active))

  def test_transit_independent_native_permission_keeps_ae0_stock_requirement(self):
    try:
      for experience in (0, 32):
        with self.subTest(experience=experience):
          self.safety.set_alternative_experience(experience)
          self.init_mode(FordSafetyFlags.NEW_PORT | FordSafetyFlags.LKA_STEERING)
          self.healthy_inputs(cruise=False)
          for name, values in (
            ("EPAS_INFO", {"EPAS_Failure": 0}),
            ("Steering_Data_FD1", {"TjaButtnOnOffPress": 0}),
            ("PowertrainData_10", {"TrnRng_D_Rq": 3}),
          ):
            self.assertTrue(self.safety.safety_rx_hook(self.packet(self.packer.make_can_msg(name, 0, values))))
          self.safety.set_aol_test_heartbeat(True)
          self.assertTrue(self.safety.safety_rx_hook(self.packet(self.packer.make_can_msg(
            "EngBrakeData", 0, {"BpedDrvAppl_D_Actl": 1, "CcStat_D_Actl": 3}))))
          self.safety.aol_set_host_request(1)
          self.assertFalse(self.safety.get_controls_allowed())
          self.assertEqual(self.safety.aol_get_permission_mask(), 1 if experience == 32 else 0)
          active = self.packet(create_lka_msg(self.packer, self.bus, True, 1., 2, .0001, transit=True))
          self.assertEqual(bool(self.safety.safety_tx_hook(active)), experience == 32)
    finally:
      self.safety.set_alternative_experience(0)
      self.safety.set_safety_hooks(CarParams.SafetyModel.noOutput, 0)
