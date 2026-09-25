import time
import unittest
from unittest.mock import patch


INVENTORY = (
  ('ACCELERATOR', 1, 1), ('TCS', 1, 2), ('WHEEL_SPEEDS', 1, 1), ('MDPS', 1, 1),
  ('STEERING_SENSORS', 1, 1), ('DOORS_SEATBELTS', 1, 10), ('BLINKERS', 1, 10),
  ('MANUAL_SPEED_LIMIT_ASSIST', 1, 10), ('CRUISE_BUTTONS', 1, 2),
  ('FR_CMR_02_100ms', 1, 10),
)


def run_context(identity, alternate, aol):
  from opendbc.can import CANPacker
  from opendbc.car import Bus, gen_empty_fingerprint, structs
  from opendbc.car.hyundai.interface import CarInterface
  from opendbc.car.hyundai.tests.test_torque_ev_startup import owner
  from opendbc.car.hyundai.values import DBC
  from opendbc.safety.tests.libsafety import libsafety_py
  from openpilot.starpilot.aol.intent import AolSettings, AOL_TOGGLE
  from openpilot.starpilot.car.hyundai.aol import create_intent, policy_for
  from openpilot.starpilot.vehicle_startup import VehicleStartupOwner
  from openpilot.selfdrive.car.car_events import CarEvents
  from openpilot.selfdrive.selfdrived.events import EventName, ET
  from openpilot.selfdrive.selfdrived.state import StateMachine

  fp = gen_empty_fingerprint()
  fp[2].update({0x110: 32, 0x362: 32} if alternate else {0x50: 16, 0x2A4: 24})
  fp[1].update({0x1CF: 8, 0x35: 32, 0x175: 24, 0xA0: 24, 0xEA: 24, 0x130: 32})
  stock = CarInterface.get_params(identity, fp, [], True, False, False)
  startup, emitted = owner(stock)
  holder = VehicleStartupOwner()
  holder.owner = startup
  with patch('opendbc.car.hyundai.torque_ev_startup.time.sleep'):
    cp = startup.prepare(admission=lambda: True)
  ci = CarInterface(cp)
  holder.configure(ci)
  if aol:
    policy = policy_for(cp)
    assert policy.safety_param_addition == 0x800 and policy.alternative_experience_addition == 32
    cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
    cp.alternativeExperience |= policy.alternative_experience_addition
  holder.finalize_aol_configuration(ci)
  holder.seal_publication()
  assert startup.published and startup.disable_attempted and not startup.restored
  assert int(cp.safetyConfigs[0].safetyParam) == ((0x95 if alternate else 0x15) | (0x800 if aol else 0))
  assert emitted and all(address == 0x730 and bus == 1 for address, _, bus in emitted)
  packer = CANPacker(DBC[identity][Bus.pt])
  intent = create_intent(cp, AolSettings(aol, 0., AOL_TOGGLE, AOL_TOGGLE, (0, 0, 0), (0, 0, 0)))
  safety = libsafety_py.libsafety
  safety.init_tests()
  safety.set_alternative_experience(int(cp.alternativeExperience))
  assert safety.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam) == 0
  camera = 'CAM_0x362' if alternate else 'CAM_0x2a4'
  inventory = (*INVENTORY, (camera, 2, 5))
  epoch = time.clock_gettime_ns(time.CLOCK_BOOTTIME) + 10_000_000
  counters = {}
  state_machine = StateMachine()
  car_events = CarEvents(cp)
  previous_state = structs.CarState()
  previous_control = structs.CarControl()
  active_long = False
  independent_lateral = False
  try:
    for tick in range(340):
      now = epoch + tick * 10_000_000
      lda = tick in (40, 41, 150, 151, 300, 301)
      set_pressed = tick in (80, 81, 180, 181, 212, 213, 304, 305)
      cancel = tick in (120, 121)
      gas = 200 <= tick < 210
      brake = 230 <= tick < 240
      frames = []
      for name, bus, period in inventory:
        if tick % period:
          continue
        values = {}
        signals = packer.dbc.name_to_msg[name].sigs
        if 'COUNTER' in signals:
          count = counters.get(name, 0)
          counters[name] = count + 1
          values['COUNTER'] = count % (1 << signals['COUNTER'].size)
        if name == 'ACCELERATOR':
          values.update(GEAR=5, ACCELERATOR_PEDAL=100 if gas else 0)
        elif name == 'TCS':
          values.update(ACCEnable=0, ACC_REQ=int(82 <= tick < 120 or 182 <= tick), DriverBraking=int(brake))
        elif name == 'WHEEL_SPEEDS':
          values.update(dict.fromkeys(('WHL_SpdFLVal', 'WHL_SpdFRVal', 'WHL_SpdRLVal', 'WHL_SpdRRVal'), 72))
        elif name == 'MDPS':
          values.update(MDPS_StrTqSnsrVal=0, MDPS_OutTqVal=0)
        elif name == 'DOORS_SEATBELTS':
          values['DRIVER_SEATBELT'] = 1
        elif name == 'CRUISE_BUTTONS':
          values.update(LDA_BTN=int(lda), ADAPTIVE_CRUISE_MAIN_BTN=0,
                        CRUISE_BUTTONS=4 if cancel else 2 if set_pressed else 0)
        assert set(values) <= set(signals), (name, set(values) - set(signals))
        frames.append(packer.make_can_msg(name, bus, values))
      assert all(address != 0x1A0 for address, _, _ in frames), 'Removed ADAS SCC cannot supply RX authority'
      safety.set_timer((now // 1000) & 0xFFFFFFFF)
      for address, data, bus in frames:
        assert safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data)), (tick, hex(address), bus)
      safety.safety_tick()
      cs = ci.update([(now, frames)])
      if tick >= 20:
        assert cs.canValid and not cs.canTimeout, (tick, cs.canValid, cs.canTimeout)
      ready = tick >= 20 and holder.before_control(configured=True, ci=ci, now_ns=now, control_current=True)
      events = car_events.update(cs, previous_state, previous_control)
      if cs.brakePressed and (not previous_state.brakePressed or not cs.standstill):
        events.add(EventName.pedalPressed)
      if not ready:
        events.add(EventName.canError)
      enabled, active = state_machine.update(events)
      intent.update(cs, now_ns=now, fault_active=not ready, standard_enabled=enabled)
      requested = bool(intent.output(cs)[0]) if aol else False
      host_lateral = ready and (requested or active)
      host_long = ready and enabled and not events.contains(ET.OVERRIDE_LONGITUDINAL) and cp.openpilotLongitudinalControl
      safety.set_aol_test_heartbeat(ready and (intent.allowed_latch or enabled))
      if aol:
        safety.aol_set_host_request(int(host_lateral) | (2 if host_long else 0))
        mask = int(safety.aol_get_permission_mask())
        if host_lateral:
          assert mask & 1, (tick, "host requested lateral but native denied")
        if host_long:
          assert mask & 2, (tick, "physical cruise requested LONG but native denied")
      cc = structs.CarControl(enabled=enabled, latActive=host_lateral, longActive=host_long)
      cc.cruiseControl.override = cc.enabled and not cc.longActive and cp.openpilotLongitudinalControl
      cc.cruiseControl.cancel = cs.cruiseState.enabled and (not cc.enabled or not cp.pcmCruise)
      previous_state, previous_control = cs, cc
      cc.actuators.torque = .005 if cc.latActive else 0.
      cc.actuators.accel = .1 if cc.longActive else 0.
      cc.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid if cc.longActive else structs.CarControl.Actuators.LongControlState.off
      _, tx = ci.apply(cc.as_reader(), now)
      for address, data, bus in tx:
        ok = bool(safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data)))
        assert ok, (tick, 'actual TX admission', hex(address), bus, data.hex())
      steering_index = next(i for i, (address, _, _) in enumerate(tx) if address == 0x12A)
      assert [(a, b) for a, _, b in tx[steering_index:steering_index + 2]] == [(0x12A, 1), (0x110 if alternate else 0x50, 0)]
      assert sum(a in (0x12A, 0x50, 0x110) for a, _, _ in tx) == 2
      assert sum(a == 0x1A0 for a, _, _ in tx) == int(tick % 2 == 0), tick
      assert sum(a == 0x1E0 for a, _, _ in tx) == int(tick % 5 == 0), tick
      assert any(a == (0x362 if alternate else 0x2A4) for a, _, _ in tx) == (tick % 5 == 0), tick
      if not cc.longActive:
        for address, data, _ in tx:
          if address == 0x1A0:
            raw = (((data[17] & 7) << 8) | data[16]) - 1023
            value = ((data[18] << 4) | (data[17] >> 4)) - 1023
            assert raw == value == 0, (tick, raw, value)
      if 90 <= tick < 118:
        active_long |= bool(cc.longActive)
      if aol and 50 <= tick < 78:
        independent_lateral |= bool(cc.latActive and not cc.longActive)
      if 202 <= tick < 210 or 232 <= tick < 240:
        assert not cc.longActive, (tick, 'physical pedal must withdraw LONG')
      if aol and 124 <= tick < 148:
        assert not cc.latActive, (tick, 'cancel must revoke lateral')
    assert active_long, 'No physical SET LONG epoch'
    assert independent_lateral == aol, 'Independent physical LDA epoch mismatch'

  finally:
    holder.close()
    safety.init_tests()
    safety.set_alternative_experience(0)
    safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)


class TestPreparedTorqueEvNative(unittest.TestCase):
  def tearDown(self):
    from opendbc.car import structs
    from opendbc.safety.tests.libsafety import libsafety_py

    safety = libsafety_py.libsafety
    safety.init_tests()
    safety.set_alternative_experience(0)
    safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)

  def test_prepared_controller_all_tx_and_physical_axes(self):
    from opendbc.car import structs
    from opendbc.car.hyundai.values import CAR
    from opendbc.safety.tests.libsafety import libsafety_py

    safety = libsafety_py.libsafety
    release = safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    if release:
      for raw in (0x815, 0x895):
        safety.init_tests()
        safety.set_alternative_experience(32)
        self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd, raw), 0)
        self.assertFalse(safety.safety_tx_hook(libsafety_py.make_CANPacket(0x1E0, 1, bytes(16))))
      return
    for identity in (CAR.HYUNDAI_IONIQ_5, CAR.HYUNDAI_KONA_EV_2ND_GEN):
      for alternate in (False, True):
        for aol in (False, True):
          with self.subTest(identity=identity, alternate=alternate, aol=aol):
            run_context(identity, alternate, aol)

  def test_release_raw_long_preserves_stock_neutral_contract(self):
    from opendbc.can import CANPacker
    from opendbc.car import structs
    from opendbc.car.hyundai.hyundaicanfd import create_steering_messages
    from opendbc.safety.tests.libsafety import libsafety_py
    from openpilot.starpilot.aol.tests.test_canfd_stock_profiles import params
    from opendbc.car.hyundai.values import CAR
    from types import SimpleNamespace

    safety = libsafety_py.libsafety
    release = safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    if not release:
      return
    packer = CANPacker('hyundai_canfd_generated')
    try:
      for alternate, raw in ((False, 0x15), (True, 0x95)):
        safety.init_tests()
        safety.set_alternative_experience(0)
        self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd, raw), 0)
        cp = params(CAR.HYUNDAI_IONIQ_5, alternate)
        neutral = create_steering_messages(packer, cp, SimpleNamespace(ECAN=1, ACAN=0), False, False, 0)[0]
        self.assertTrue(safety.safety_tx_hook(libsafety_py.make_CANPacket(neutral[0], neutral[2], neutral[1])))
        active = create_steering_messages(packer, cp, SimpleNamespace(ECAN=1, ACAN=0), True, True, 1)[0]
        self.assertFalse(safety.safety_tx_hook(libsafety_py.make_CANPacket(active[0], active[2], active[1])))
        wrong_layout = create_steering_messages(packer, params(CAR.HYUNDAI_IONIQ_5, not alternate),
                                                SimpleNamespace(ECAN=1, ACAN=0), False, False, 0)[0]
        self.assertFalse(safety.safety_tx_hook(libsafety_py.make_CANPacket(wrong_layout[0], wrong_layout[2], wrong_layout[1])))
        self.assertFalse(safety.safety_tx_hook(libsafety_py.make_CANPacket(neutral[0], 1, neutral[1])))
        self.assertFalse(safety.safety_tx_hook(libsafety_py.make_CANPacket(0x12A, 1, bytes(16))))
        self.assertFalse(safety.safety_tx_hook(libsafety_py.make_CANPacket(0x1A0, 1, bytes(32))))
    finally:
      safety.init_tests()
      safety.set_alternative_experience(0)
      safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)
