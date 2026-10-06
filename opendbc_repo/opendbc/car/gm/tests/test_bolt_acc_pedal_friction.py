import unittest
from types import SimpleNamespace

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.gm.carcontroller import CarController, bolt_acc_pedal_friction_brake
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR, DBC


def pedal_params(candidate=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL):
  fingerprint = gen_empty_fingerprint()
  fingerprint[2][0x320] = 8
  fingerprint[0][0x201] = 6
  return CarInterface.get_params(candidate, fingerprint, [], False, False, False)


def brake_frames(messages):
  return [m for m in messages if m[0] == 0x315]


def brake_fields(message):
  data = message[1]
  mode = data[0] >> 4
  brake = (0x1000 - (((data[0] & 0xF) << 8) | data[1])) & 0xFFF
  counter = data[4] & 0x3
  checksum = (data[2] << 8) | data[3]
  assert checksum == (0x10000 - (mode << 12) - ((0x1000 - brake) & 0xFFF) - counter) & 0xFFFF
  return mode, brake, counter


class TestBoltAccPedalFriction(unittest.TestCase):
  def fixture(self, candidate=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL):
    cp = pedal_params(candidate)
    controller = CarController(DBC[candidate], cp)
    controller.frame = 4
    controller.last_steer_frame = 4
    controller.last_button_frame = -10
    control = structs.CarControl()
    control.enabled = True
    control.longActive = True
    control.actuators.accel = -3.
    state = structs.CarState()
    state.vEgo = 12.
    state.gearShifter = structs.CarState.GearShifter.low
    state.cruiseState.available = True
    cs = SimpleNamespace(out=state.as_reader(), pedal_sensor_healthy=True,
                         pedal_sensor_ts_nanos=950_000_000, stock_acc_status_ts_nanos=950_000_000,
                         bolt_pedal_gear_ts_nanos=950_000_000, bolt_pedal_main_ts_nanos=950_000_000,
                         cam_lka_steering_cmd_counter=0, loopback_lka_steering_cmd_updated=False,
                         loopback_lka_steering_cmd_ts_nanos=1_000_000_000, pt_lka_steering_cmd_counter=0,
                         buttons_counter=0,
                         pscm_status=dict.fromkeys(("HandsOffSWDetectionMode", "HandsOffSWlDetectionStatus", "LKATorqueDeliveredStatus",
                                        "LKADriverAppldTrq", "LKATorqueDelivered", "LKATotalTorqueDelivered", "RollingCounter", "PSCMStatusChecksum"), 0))
    return controller, control, state, cs

  def step(self, fixture, frame, now=1_000_000_000):
    controller, control, state, cs = fixture
    controller.frame = frame
    cs.out = state.as_reader()
    _, messages = controller.update(control.as_reader(), cs, now)
    return messages

  def test_brake_curve_and_stop_fade(self):
    cp = pedal_params()
    for accel, speed, stopping, expected in ((-1.5, 12.0, False, (98, True)),
                                             (-3.0, 12.0, False, (343, True)),
                                             (-3.0, 8.0, False, (327, True)),
                                             (-3.0, 1.5, True, (70, True)),
                                             (-3.0, 0.0, True, (0, False))):
      with self.subTest(accel=accel, speed=speed, stopping=stopping):
        self.assertEqual(bolt_acc_pedal_friction_brake(accel, speed, stopping, False,
                                                       cp.mass, cp.wheelbase, 400), expected)

  def test_positive_brake_only_after_fresh_stock_release_and_zero_unwind(self):
    fixture = self.fixture()
    controller, control, state, cs = fixture
    state.cruiseState.enabled = True
    messages = self.step(fixture, 4)
    self.assertEqual(brake_frames(messages), [])
    self.assertIn((0x1E1, 2), [(m[0], m[2]) for m in messages])
    self.assertEqual(messages[0][1][:4], b"\x00" * 4)

    state.cruiseState.enabled = False
    messages = self.step(fixture, 8)
    self.assertEqual([m[0] for m in messages if m[0] in (0x200, 0x315)], [0x200, 0x315])
    self.assertEqual(brake_frames(messages)[0][2], 0)
    mode, brake, counter = brake_fields(brake_frames(messages)[0])
    self.assertEqual(mode, 0xA)
    self.assertEqual(counter, 2)
    self.assertGreater(brake, 0)
    self.assertEqual(controller.apply_brake, brake)

    cs.pedal_sensor_healthy = False
    for frame in (12, 16, 20, 24):
      messages = self.step(fixture, frame)
      self.assertEqual(brake_fields(brake_frames(messages)[0])[:2], (0x1, 0))
      self.assertEqual(messages[0][1][:4], b"\x00" * 4)
    state.cruiseState.available = False
    self.assertEqual(brake_frames(self.step(fixture, 28)), [])

  def test_no_friction_when_owner_or_driver_gate_is_lost(self):
    for gate in ("stale_stock", "neutral", "brake", "regen", "no_main"):
      with self.subTest(gate=gate):
        fixture = self.fixture()
        _, _, state, cs = fixture
        if gate == "stale_stock":
          cs.stock_acc_status_ts_nanos = 600_000_000
        elif gate == "neutral":
          state.gearShifter = structs.CarState.GearShifter.neutral
        elif gate == "brake":
          state.brakePressed = True
        elif gate == "regen":
          state.regenBraking = True
        else:
          state.cruiseState.available = False
        messages = self.step(fixture, 4)
        self.assertFalse(any(brake_fields(m)[1] > 0 for m in brake_frames(messages)))

  def test_drive_keeps_friction_without_gear_or_paddle_spoof(self):
    fixture = self.fixture()
    fixture[2].gearShifter = structs.CarState.GearShifter.drive
    messages = self.step(fixture, 4)
    self.assertGreater(brake_fields(brake_frames(messages)[0])[1], 0)
    self.assertFalse(any(m[0] in (0x1F5, 0xBD) for m in messages))

  def test_stock_acc_return_stops_host_brake_and_unwind(self):
    fixture = self.fixture()
    _, _, state, _ = fixture
    self.assertGreater(brake_fields(brake_frames(self.step(fixture, 4))[0])[1], 0)
    state.cruiseState.enabled = True
    self.assertEqual(brake_frames(self.step(fixture, 8)), [])
    state.cruiseState.enabled = False
    state.cruiseState.available = False
    self.assertEqual(brake_frames(self.step(fixture, 12)), [])

  def test_main_off_releases_pedal_despite_lagging_long_active(self):
    fixture = self.fixture()
    _, control, state, _ = fixture
    control.actuators.accel = 1.0
    messages = self.step(fixture, 4)
    self.assertNotEqual(messages[0][1][:4], b"\x00" * 4)
    state.cruiseState.available = False
    messages = self.step(fixture, 8)
    self.assertEqual(messages[0][1][:4], b"\x00" * 4)
    self.assertEqual(brake_frames(messages), [])

  def test_other_pedal_bolts_do_not_emit_friction(self):
    for candidate in (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021,
                      CAR.CHEVROLET_BOLT_CC_2022_2023):
      with self.subTest(candidate=candidate):
        self.assertEqual(brake_frames(self.step(self.fixture(candidate), 4)), [])

  def test_low_speed_pedal_output_serializes_for_all_variants(self):
    for candidate in (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021,
                      CAR.CHEVROLET_BOLT_CC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL):
      with self.subTest(candidate=candidate):
        fixture = self.fixture(candidate)
        controller, control, state, cs = fixture
        state.vEgo = 2.8
        control.actuators.accel = 0.4
        cs.out = state.as_reader()
        output, _ = controller.update(control.as_reader(), cs, 1_000_000_000)
        self.assertAlmostEqual(output.gas, 0.30125)
        self.assertGreater(len(output.to_bytes()), 0)

  def test_regen_paddle_takeover_uses_new_physical_pedal_demand(self):
    fixture = self.fixture()
    controller, control, state, _ = fixture
    state.aEgo = -1.0
    control.actuators.accel = 0.5
    for slot in range(1, 8):
      messages = self.step(fixture, slot * 4)
      self.assertFalse(controller.regen_paddle_pressed)
    self.assertAlmostEqual(controller.pedal_steady, 0.4452777777777778)
    self.assertEqual(next(m for m in messages if m[0] == 0x200)[1].hex(), "05e302f3877d")

    messages = self.step(fixture, 32)
    self.assertTrue(controller.regen_paddle_pressed)
    # Original physical-demand curve selects the new paddle target immediately
    # above 1 m/s; a one-frame slew would retain a higher stale command.
    self.assertAlmostEqual(controller.pedal_steady, 0.3877844276280657)
    payloads = {m[0]: m[1].hex() for m in messages if m[0] in (0x200, 0x1F5, 0xBD, 0x315)}
    self.assertEqual(payloads, {0x200: "056f02b888ce", 0x1F5: "0c0c000500020100",
                                0xBD: "20000000000000", 0x315: "9000700000"})
