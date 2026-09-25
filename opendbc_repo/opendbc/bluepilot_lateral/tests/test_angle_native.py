"""Public packed angle/native boundaries; uses the runner-selected safety library."""
from opendbc.bluepilot_lateral.core.angle import AngleController, Inputs, Command
from opendbc.bluepilot_lateral.can.ford import lateral, lka, checksum4
from opendbc.safety.tests import common
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.car.structs import CarParams
from opendbc.can import CANPacker


class TestFordAngleNative(common.SafetyTestBase):
  DBC = "ford_lincoln_base_pt"
  SAFETY_MODEL = CarParams.SafetyModel.ford
  SAFETY_PARAM = 128

  def setUp(self):
    super().setUp()
    self.debug = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) == 0
    self.safety.set_safety_hooks(self.SAFETY_MODEL, self.SAFETY_PARAM)
    self.safety.init_tests()
    self.now = 1_000_000
    self.lka_count = 0
    self.control_count = 0
    self.word = self.SAFETY_PARAM

  def packet(self, msg):
    addr, dat, bus = msg
    return libsafety_py.make_CANPacket(addr, bus, dat)

  def rx(self, name, values, *, bus=0):
    self.assertTrue(self._rx(self.packer.make_can_msg_safety(name, bus, values)))

  def warm(self, speed=15.0, curvature=0.0):
    self.safety.set_timer(self.now)
    for _ in range(6):
      self.rx("BrakeSysFeatures", {"Veh_V_ActlBrk": speed * 3.6, "VehVActlBrk_D_Qf": 3})
      self.rx("EngVehicleSpThrottle2", {"Veh_V_ActlEng": speed * 3.6, "VehVActlEng_D_Qf": 3})
      self.rx("Yaw_Data_FD1", {"VehYaw_W_Actl": curvature * speed, "VehYawWActl_D_Qf": 3})
    self.rx("EngVehicleSpThrottle", {"ApedPos_Pc_ActlArb": 0})
    self.rx("DesiredTorqBrk", {"VehStop_D_Stat": 0})
    self.rx("Steering_Data_FD1", {"CcAslButtnCnclResPress": 0})
    if not self.safety.get_controls_allowed():
      self.rx("EngBrakeData", {"BpedDrvAppl_D_Actl": 1, "CcStat_D_Actl": 0})
    self.rx("EngBrakeData", {"BpedDrvAppl_D_Actl": 1, "CcStat_D_Actl": 5})
    self.assertTrue(self.safety.get_controls_allowed())

  def reset_word(self, word):
    self.safety.set_alternative_experience(0)
    self.safety.set_safety_hooks(self.SAFETY_MODEL, word)
    self.word = word
    self.lka_count = self.control_count = 0
    self.now += 1_000_000
    self.warm()

  def shadow(self, command):
    msg = lka(self.packer, 0, command.shadow_curvature, self.lka_count)
    self.lka_count = (self.lka_count + 1) % 8
    return msg

  def control(self, command):
    msg = lateral(self.packer, 0, command, canfd=bool(self.word & 2), counter=self.control_count)
    self.control_count = (self.control_count + 1) % 16
    return msg

  def send(self, msg, expected=True):
    self.assertEqual(bool(self._tx(self.packet(msg))), expected)

  def tick(self, command):
    self.now += 50_000
    self.warm()
    self.send(self.shadow(command))
    self.send(self.control(command))

  def test_real_packer_physical_neutral_shadow_and_corruptions(self):
    packer = CANPacker(self.DBC)
    for word in (128, 130):
      for direction in (-1, 1):
        for fault in ("angle", "curvature", "checksum", "version", "counter", "replay"):
          with self.subTest(word=word, direction=direction, fault=fault):
            self.reset_word(word)
            command = Command(True, direction * 0.005, direction * 0.005 / 15.0)
            # Real RX and PCM edges in warm() establish permission, with no allowance setter.
            self.assertTrue(self.safety.get_controls_allowed())
            good = lka(packer, 0, command.shadow_curvature, 0)
            addr, data, bus = good
            self.assertEqual((addr, bus), (0x3CA, 0))
            self.assertEqual(data[:4], b"\x00\x80\x08\x00")
            self.assertEqual(((data[2] & 15) << 8) | data[3], 2048)
            self.assertEqual((data[1] << 4) | (data[2] >> 4), 2048)
            self.assertEqual(data[7] & 15, 1)
            self.assertEqual(data[7] >> 4, checksum4(data))
            self.assertEqual(int.from_bytes(data[5:7], "big", signed=True), round(-command.shadow_curvature * 1e6))
            self.send(good)
            self.send(lateral(packer, 0, command, canfd=bool(word & 2), counter=0))
            self.now += 50_000
            self.warm()
            next_good = lka(packer, 0, command.shadow_curvature, 1)
            mutated = bytearray(next_good[1])
            if fault == "angle":
              mutated[3] ^= 1
            elif fault == "curvature":
              mutated[1] ^= 1
            elif fault == "checksum":
              mutated[7] ^= 16
            elif fault == "version":
              mutated[7] ^= 1
            elif fault == "counter":
              mutated[4] ^= 4
            if fault in ("angle", "curvature", "counter"):
              mutated[7] = 1 | (checksum4(mutated) << 4)
            bad = good if fault == "replay" else (addr, bytes(mutated), bus)
            self.send(bad, False)
            self.assertTrue(self.safety.get_controls_allowed())
            self.send(lateral(packer, 0, command, canfd=bool(word & 2), counter=1), False)
            # A new valid announcement restores the same bounded path without relaxing native checks.
            self.now += 50_000
            self.warm()
            self.send(next_good)
            self.send(lateral(packer, 0, command, canfd=bool(word & 2), counter=1))

  def test_actual_core_packer_boundary_all_namespaces(self):
    words = [128, 129, 130]
    if self.debug:
      words.append(131)
    for word in words:
      for direction in (-1, 1):
        self.reset_word(word)
        core = AngleController(low_gain=0.95, high_gain=0.95)
        active_seen = False
        for _ in range(40):
          command = core.step(Inputs(True, 15.0, 0.0, direction * 0.02))
          active_seen |= command.active
          self.tick(command)
        self.assertTrue(active_seen)
        self.tick(Command())

  def test_cold_and_stale_shadow_require_new_valid_announcement(self):
    command = Command(True, 0.005, 0.005 / 15.0)
    self.warm()
    self.send(self.control(command), False)
    self.send(self.shadow(command))
    self.send(self.control(command))
    self.now += 60_001
    self.warm()
    self.send(self.control(command), False)
    self.now += 50_000
    self.warm()
    self.send(self.shadow(command))
    self.send(self.control(command))

  def test_invalid_shadow_version_checksum_and_dbc_bits_withdraw(self):
    command = Command(True, 0.005, 0.005 / 15.0)
    for index, mask in ((7, 1), (7, 16), (0, 32), (4, 2), (4, 32)):
      self.reset_word(128)
      valid = self.shadow(command)
      addr, data, bus = valid
      mutated = bytearray(data)
      mutated[index] ^= mask
      if index != 7:
        mutated[7] = 1 | (checksum4(mutated) << 4)
      self.send((addr, bytes(mutated), bus), False)
      self.send(self.control(command), False)
      self.send(valid)
      self.send(self.control(command))

  def test_replay_wrong_bus_and_length_cannot_refresh_shadow(self):
    command = Command(True, 0.005, 0.005 / 15.0)
    self.warm()
    msg = self.shadow(command)
    self.send(msg)
    self.send(msg, False)
    self.send(self.control(command), False)
    for bus, size in ((2, 8), (0, 7), (0, 16)):
      addr, dat, _ = self.shadow(command)
      self.send((addr, (dat + b"\x00" * 8)[:size], bus), False)
    self.now += 30_000
    self.rx("EngBrakeData", {"BpedDrvAppl_D_Actl": 1, "CcStat_D_Actl": 0})
    self.send(self.shadow(Command()))
    self.now += 30_000
    self.warm()
    self.send(self.shadow(command))
    self.send(self.control(command))

  def test_native_actual_path_cannot_be_laundered_by_shadow(self):
    for command in (Command(True, 0.0005, 0.0), Command(True, -0.0005, 0.0), Command(True, 0.5, 0.0), Command(True, -0.01, 0.001),
                    Command(True, 0.04, 0.002), Command(True, 0.10, 0.005)):
      self.reset_word(128)
      self.send(self.shadow(command))
      self.send(self.control(command), False)
    # A rejected command does not seed an excessive subsequent ROC.
    self.reset_word(128)
    large = Command(True, 0.20, 0.01)
    self.send(self.shadow(large))
    self.send(self.control(large), False)
    self.now += 50_000
    self.warm()
    small = Command(True, 0.005, 0.005 / 15.0)
    self.send(self.shadow(small))
    self.send(self.control(small))

  def test_permission_and_rx_withdrawals(self):
    command = Command(True, 0.005, 0.005 / 15.0)
    for source in ("brake", "gas", "cruise", "speed_quality", "yaw_checksum", "stale"):
      self.reset_word(128)
      self.send(self.shadow(command))
      self.send(self.control(command))
      self.now += 50_000
      self.warm()
      self.send(self.shadow(command))
      if source == "brake":
        self.rx("EngBrakeData", {"BpedDrvAppl_D_Actl": 2, "CcStat_D_Actl": 5})
      elif source == "gas":
        self.rx("EngVehicleSpThrottle", {"ApedPos_Pc_ActlArb": 50})
      elif source == "cruise":
        self.rx("EngBrakeData", {"BpedDrvAppl_D_Actl": 1, "CcStat_D_Actl": 3})
      elif source == "speed_quality":
        self.assertFalse(self._rx(self.packer.make_can_msg_safety("BrakeSysFeatures", 0, {"VehVActlBrk_D_Qf": 0})))
      elif source == "yaw_checksum":
        packet = self.packer.make_can_msg_safety("Yaw_Data_FD1", 0, {"VehYawWActl_D_Qf": 3})
        packet[0].data[4] ^= 1
        self.assertFalse(self._rx(packet))
      else:
        self.now += 200_001
        self.safety.set_timer(self.now)
      self.send(self.control(command), False)
      self.send(self.control(Command()))

  def test_fd_bad_crc_counter_and_mode_neutral_recovery(self):
    self.reset_word(130)
    command = Command(True, 0.005, 0.005 / 15.0)
    self.send(self.shadow(command))
    good = self.control(command)
    addr, dat, bus = good
    bad = bytearray(dat)
    bad[1] ^= 1
    self.send((addr, bytes(bad), bus), False)
    self.send(good, False)  # bad CRC withdrew shadow
    self.now += 50_000
    self.warm()
    self.send(self.shadow(command))
    self.send(self.control(Command()))  # valid mode0 resynchronizes skipped counters
    self.now += 50_000
    self.warm()
    self.send(self.shadow(command))
    self.send(self.control(command))
    self.now += 50_000
    self.warm()
    self.send(self.shadow(command))
    self.control_count = (self.control_count + 1) % 16
    self.send(self.control(command), False)

  def test_adjacent_profile_version_and_release_long_denials(self):
    command = Command(True, 0.005, 0.005 / 15.0)
    for word in (0, 2, 4, 8, 10, 12, 18, 32, 66, 132, 134, 136, 160, 194, 256):
      self.reset_word(word)
      announcement = self.shadow(command)
      if word & 128:
        self.send(announcement, False)
      else:
        self._tx(self.packet(announcement))  # Existing neutral metadata is not angle authority.
      self.send(self.control(command), False)
    self.reset_word(131)
    expected = bool(self.debug)
    self.send(self.shadow(command), expected)
    self.send(self.control(command), expected)

  def test_rejected_metadata_does_not_erase_last_accepted_path_and_neutral_resync(self):
    self.reset_word(128)
    # At25m/s ROC is tight enough that erasing the accepted path would reject a same-path retry.
    core = AngleController(low_gain=.95, high_gain=.95)
    for _ in range(30):
      self.now += 50_000
      self.warm(speed=25., curvature=.001)
      command = core.step(Inputs(True, 25., -.001, -.001))
      self.send(self.shadow(command))
      self.send(self.control(command))
    self.assertGreater(abs(command.path_angle), .01)
    self.now += 50_000
    self.warm(speed=25., curvature=.001)
    good = self.shadow(command)
    addr, data, bus = good
    bad = bytearray(data)
    bad[7] ^= 16
    self.send((addr, bytes(bad), bus), False)
    self.send(good)
    self.send(self.control(command))
    self.now += 50_000
    self.warm(speed=25., curvature=.001)
    self.send(self.control(Command()))
    self.now += 50_000
    self.warm(speed=25., curvature=.001)
    recovery = AngleController(low_gain=.95, high_gain=.95).step(Inputs(True, 25., -.001, -.001))
    self.send(self.shadow(recovery))
    self.send(self.control(recovery))

  def test_rt_rate_denial_expires_and_neutral_can_recover(self):
    self.reset_word(130)
    for _ in range(8):
      self.send(self.control(Command()))
    self.send(self.control(Command()), False)
    self.now += 250_000
    self.warm()
    self.send(self.control(Command()))
    self.now += 50_000
    self.warm()
    command = Command(True, .005, .005 / 15.)
    self.send(self.shadow(command))
    self.send(self.control(command))
