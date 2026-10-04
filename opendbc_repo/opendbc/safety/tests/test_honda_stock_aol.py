import unittest

from opendbc.car import structs
from opendbc.can.dbc import DBC
from opendbc.safety.tests.common import CANPackerSafety
from opendbc.safety.tests.libsafety import libsafety_py


CASES = (
  ("classic", 20, 0, 1, "honda_civic_hatchback_ex_2017_can_generated", False, "GEARBOX_AUTO", 4),
  ("classic-alt-brake", 20, 1, 1, "acura_rdx_2020_can_generated", False, "GEARBOX_AUTO", 4),
  ("nidec", 1, 0, 0, "honda_civic_touring_2016_can_generated", False, "GEARBOX_CVT", 4),
  ("nidec-alt-six-byte-eps", 1, 4, 0, "acura_rdx_2018_can_generated", True, "GEARBOX_AUTO", 8),
  ("nidec-alt-other-eps", 1, 4, 0, "honda_accord_2017_can_ext_generated", True, "GEARBOX_AUTO", 8),
  ("twn", 1, 260, 0, "honda_odyssey_twn_2018_generated", True, "GEARBOX_AUTO", 4),
  ("radarless", 20, 8, 0, "honda_bosch_radarless_generated", False, "GEARBOX_AUTO", 4),
  ("radarless-alt-brake", 20, 9, 0, "honda_bosch_radarless_generated", False, "GEARBOX_AUTO", 4),
  ("radarless-long", 20, 10, 0, "honda_bosch_radarless_generated", False, "GEARBOX_AUTO", 4),
  ("radarless-long-alt-brake", 20, 11, 0, "honda_bosch_radarless_generated", False, "GEARBOX_AUTO", 4),
)


class TestHondaStockAol(unittest.TestCase):
  def configure(self, case, experience=32):
    self.case = case
    _, model, word, self.pt, dbc, self.alt, self.gear_name, self.drive_value = case
    self.safety = libsafety_py.libsafety
    self.debug = self.safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) == 0
    self.safety.set_safety_hooks(model, word)
    self.safety.init_tests()
    self.safety.set_alternative_experience(experience)
    self.safety.set_safety_hooks(model, word)
    self.safety.set_timer(1_000_000)
    self.safety.set_aol_test_heartbeat(True)
    self.packer = CANPackerSafety(dbc)
    self.dbc = DBC(dbc)
    self.scoped = experience == 32 and (word not in (10, 11) or self.debug)

  def packet(self, name, values, bus=None):
    expected = self.dbc.name_to_msg[name].sigs
    self.assertFalse(set(values) - set(expected), (name, set(values) - set(expected)))
    return self.packer.make_can_msg_safety(name, self.pt if bus is None else bus, values)

  def stream(self, *, main=True, lkas=0, eps=0, gear=None, cruise=0, omit=None):
    scm = {"CRUISE_BUTTONS": 0, "CRUISE_SETTING": lkas}
    if self.alt:
      scm["MAIN_ON"] = int(main)
    frames = [
      ("SCM_BUTTONS", self.packet("SCM_BUTTONS", scm)),
      ("ENGINE_DATA", self.packet("ENGINE_DATA", {"XMISSION_SPEED": 30})),
      ("POWERTRAIN_DATA", self.packet("POWERTRAIN_DATA", {"ACC_STATUS": cruise, "PEDAL_GAS": 0, "BRAKE_PRESSED": 0})),
      ("STEER_STATUS", self.packet("STEER_STATUS", {"STEER_STATUS": eps, "STEER_TORQUE_SENSOR": 0})),
      (self.gear_name, self.packet(self.gear_name, {"GEAR_SHIFTER": self.drive_value if gear is None else gear})),
    ]
    if not self.alt:
      frames.insert(0, ("SCM_FEEDBACK", self.packet("SCM_FEEDBACK", {"MAIN_ON": int(main)})))
    if self.case[1] == 1:
      frames.append(("BRAKE_COMMAND", self.packet("BRAKE_COMMAND", {}, 2)))
    elif self.case[2] & 1:
      frames.append(("BRAKE_MODULE", self.packet("BRAKE_MODULE", {"BRAKE_PRESSED": 0})))
    for name, frame in frames:
      if name != omit:
        self.assertTrue(self.safety.safety_rx_hook(frame), name)
    self.safety.aol_set_host_request(1)

  def arm(self):
    self.stream(main=False)
    self.stream(main=True)
    self.stream(main=True, lkas=1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1 if self.scoped else 0)

  def test_validated_sources_and_fresh_gesture(self):
    for case in CASES:
      with self.subTest(case=case[0]):
        self.configure(case)
        self.stream()
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)
        self.arm()

  def test_reverse_temporary_eps_and_heartbeat_loss(self):
    for case in CASES:
      with self.subTest(case=case[0]):
        self.configure(case)
        self.arm()
        self.stream(gear=2)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)
        self.safety.aol_set_host_request(0)
        self.stream(eps=6)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)
        self.stream()
        self.assertEqual(self.safety.aol_get_permission_mask(), 1 if self.scoped else 0)
        self.safety.set_aol_test_heartbeat(False)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)
        self.safety.set_aol_test_heartbeat(True)
        self.stream()
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)
        self.stream(lkas=1)
        self.assertEqual(self.safety.aol_get_permission_mask(), 1 if self.scoped else 0)

  def test_permanent_eps_then_clean_same_batch_does_not_rearm(self):
    for case in CASES:
      with self.subTest(case=case[0]):
        self.configure(case)
        self.arm()
        self.assertTrue(self.safety.safety_rx_hook(self.packet("STEER_STATUS", {"STEER_STATUS": 7})))
        self.assertTrue(self.safety.safety_rx_hook(self.packet("STEER_STATUS", {"STEER_STATUS": 0})))
        self.stream()
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)
        self.stream(lkas=1)
        self.assertEqual(self.safety.aol_get_permission_mask(), 1 if self.scoped else 0)

  def test_selected_eps_or_gear_loss_requires_new_gesture(self):
    for case in CASES:
      for source in ("STEER_STATUS", case[6]):
        with self.subTest(case=case[0], source=source):
          self.configure(case)
          self.arm()
          self.safety.set_timer(1_300_001)
          self.stream(omit=source)
          self.assertEqual(self.safety.aol_get_permission_mask(), 0)
          self.stream()
          self.assertEqual(self.safety.aol_get_permission_mask(), 0)
          self.stream(lkas=1)
          self.assertEqual(self.safety.aol_get_permission_mask(), 1 if self.scoped else 0)

  def test_ae0_remains_without_independent_permission(self):
    for case in CASES:
      if case[2] == 260:
        continue
      with self.subTest(case=case[0]):
        self.configure(case, experience=0)
        self.stream(main=False)
        self.stream(main=True, lkas=1)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)
