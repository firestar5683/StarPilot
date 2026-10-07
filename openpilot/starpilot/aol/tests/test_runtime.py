import time
import unittest
from unittest import mock
from types import SimpleNamespace
from pathlib import Path

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.structs import car
from openpilot.selfdrive.car.cruise import CRUISE_LONG_PRESS
from openpilot.common.params import Params
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
from openpilot.selfdrive.selfdrived.alertmanager import AlertManager
from openpilot.selfdrive.selfdrived.events import Events, ET
from openpilot.selfdrive.selfdrived.state import StateMachine
from openpilot.starpilot.aol.intent import AolCardIntent, AolSettings, disarming_fault, read_settings
from openpilot.starpilot.aol.runtime import AxisDecision, current_intent, current_native, decide_axes
from openpilot.starpilot.aol.wire import IntentState, SafetyState, encode_intent, encode_safety


def car_state(*, brake=False):
  return car.CarState(canValid=True, gearShifter=car.CarState.GearShifter.drive,
                      vEgo=20.0, brakePressed=brake)


class CardIntentTests(unittest.TestCase):
  def test_seatbelt_blocks_standard_longitudinal_without_disarming_aol(self):
    from openpilot.starpilot.nostalgia import aol_no_entry

    owner = AolCardIntent(AolSettings(True, 0, 9, 0, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
    state = car_state()
    state.cruiseState.available = True
    state.seatbeltUnlatched = True
    events = Events()
    events.add(log.OnroadEvent.EventName.seatbeltNotLatched)
    self.assertTrue(events.contains(ET.NO_ENTRY))
    self.assertTrue(events.contains(ET.SOFT_DISABLE))
    owner.update(state, fault_active=disarming_fault(events.to_msg(), state))
    self.assertFalse(owner.allowed_latch)
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    owner.update(state, fault_active=disarming_fault(events.to_msg(), state))
    self.assertTrue(owner.allowed_latch)
    state.buttonEvents = []
    standard = StateMachine()
    events.add(log.OnroadEvent.EventName.buttonEnable)
    self.assertEqual(standard.update(events), (False, False))
    native = SimpleNamespace(requestedLateral=True, requestedLongitudinal=False,
                             lateralAllowed=True, longitudinalAllowed=True)
    for unlatched in (True, True, False):
      state.seatbeltUnlatched = unlatched
      events.clear()
      if unlatched:
        events.add(log.OnroadEvent.EventName.seatbeltNotLatched)
      owner.update(state, fault_active=disarming_fault(events.to_msg(), state))
      enabled, active = standard.update(events)
      self.assertFalse(enabled or active)  # Buckling alone is not an engagement gesture.
      allowed, pause_lat, pause_long = owner.output(state)
      decision = decide_axes(standard_lateral=active, standard_longitudinal=enabled,
        intent=SimpleNamespace(allowedLatch=allowed, pauseLateral=pause_lat, pauseLongitudinal=pause_long),
        native=native, car_state=state, initialized=True, model_ready=True,
        no_entry=aol_no_entry(events.names, state, paddle_only_cancel=False),
        immediate_disable=False, dm_lockout=False, pause_brake_mps=0.)
      self.assertTrue(decision.lateral_active)
      self.assertFalse(decision.desired_longitudinal or decision.longitudinal_active)
    state.seatbeltUnlatched = True
    direct = decide_axes(standard_lateral=True, standard_longitudinal=True,
      intent=SimpleNamespace(allowedLatch=True, pauseLateral=False, pauseLongitudinal=False),
      native=native, car_state=state, initialized=True, model_ready=True, no_entry=False,
      immediate_disable=False, dm_lockout=False, pause_brake_mps=0.)
    self.assertTrue(direct.lateral_active)
    self.assertFalse(direct.desired_longitudinal)
    events.add(log.OnroadEvent.EventName.doorOpen)
    self.assertTrue(disarming_fault(events.to_msg(), state))
    self.assertTrue(aol_no_entry(events.names, state, paddle_only_cancel=False))

  def test_temporary_eps_and_known_gears_preserve_latch_with_zero_steering(self):
    owner = AolCardIntent(AolSettings(True, 0, 0, 0, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
    state = car_state()
    owner.update(state)
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    owner.update(state)
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=False)]
    owner.update(state)
    state.buttonEvents = []
    for gear, temporary, name in (
        (car.CarState.GearShifter.drive, True, log.OnroadEvent.EventName.steerTempUnavailable),
        (car.CarState.GearShifter.neutral, False, log.OnroadEvent.EventName.wrongGear),
        (car.CarState.GearShifter.reverse, False, log.OnroadEvent.EventName.wrongGear),
        (car.CarState.GearShifter.park, False, log.OnroadEvent.EventName.wrongGear)):
      with self.subTest(gear=gear, temporary=temporary):
        state.gearShifter = gear
        state.steerFaultTemporary = temporary
        events = Events()
        events.add(name)
        fault = disarming_fault(events.to_msg(), state)
        self.assertFalse(fault)
        for _ in range(100):
          owner.update(state, fault_active=fault)
          self.assertTrue(owner.allowed_latch)
          allowed, pause_lat, pause_long = owner.output(state)
          decision = decide_axes(standard_lateral=False, standard_longitudinal=False,
            intent=SimpleNamespace(allowedLatch=allowed, pauseLateral=pause_lat, pauseLongitudinal=pause_long),
            native=SimpleNamespace(requestedLateral=False, requestedLongitudinal=False, lateralAllowed=False, longitudinalAllowed=False),
            car_state=state, initialized=True, model_ready=True, no_entry=True, immediate_disable=False,
            dm_lockout=False, pause_brake_mps=0)
          self.assertFalse(decision.desired_lateral)
          self.assertFalse(decision.lateral_active)
        state.gearShifter = car.CarState.GearShifter.drive
        state.steerFaultTemporary = False
        owner.update(state, fault_active=False)
        self.assertTrue(owner.output(state)[0])
        decision = decide_axes(standard_lateral=False, standard_longitudinal=False,
          intent=SimpleNamespace(allowedLatch=owner.output(state)[0], pauseLateral=False, pauseLongitudinal=False),
          native=SimpleNamespace(requestedLateral=True, requestedLongitudinal=False, lateralAllowed=True, longitudinalAllowed=False),
          car_state=state, initialized=True, model_ready=True, no_entry=False, immediate_disable=False,
          dm_lockout=False, pause_brake_mps=0)
        self.assertTrue(decision.lateral_active)

  def test_calibration_rearm_follows_live_mapping_without_arming_on_change(self):
    from dataclasses import replace
    from openpilot.starpilot.aol.intent import AOL_TOGGLE
    owner = AolCardIntent(AolSettings(True, 0., 0, 0, (0, 0, 0), (0, 0, 0)))
    state = car_state()
    state.cruiseState.available = True
    owner.update(state)
    owner.observe_calibration(state, events=[])
    self.assertTrue(owner.allowed_latch)
    invalid = Events()
    invalid.add(log.OnroadEvent.EventName.calibrationInvalid)
    owner.observe_calibration(state, events=invalid.to_msg())
    self.assertFalse(owner.allowed_latch)
    owner.settings = replace(owner.settings, lkas_action=AOL_TOGGLE)
    owner.update(state)
    owner.observe_calibration(state, events=invalid.to_msg())
    self.assertFalse(owner.allowed_latch)
    owner.update(state)
    owner.observe_calibration(state, events=[])
    self.assertFalse(owner.allowed_latch)  # The mapping change is not an arming gesture.
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    owner.update(state)
    owner.observe_calibration(state, events=[])
    self.assertTrue(owner.allowed_latch)

  def test_low_speed_brake_suppresses_output_without_destroying_explicit_latch(self):
    owner = AolCardIntent(AolSettings(True, 5.0, 0, 0, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
    state = car_state()
    owner.update(state)
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    owner.update(state)
    state.buttonEvents = []
    events = Events()
    events.add(log.OnroadEvent.EventName.pedalPressed)
    for speed, brake, expected in ((2., True, False), (2., False, True), (6., True, True)):
      state.vEgo, state.brakePressed = speed, brake
      owner.update(state, fault_active=disarming_fault(events.to_msg(), state))
      self.assertTrue(owner.allowed_latch)
      allowed, pause_lat, pause_long = owner.output(state)
      axes = decide_axes(standard_lateral=False, standard_longitudinal=False,
        intent=SimpleNamespace(allowedLatch=allowed, pauseLateral=pause_lat, pauseLongitudinal=pause_long),
        native=SimpleNamespace(requestedLateral=expected, requestedLongitudinal=False,
                               lateralAllowed=expected, longitudinalAllowed=False),
        car_state=state, initialized=True, model_ready=True, no_entry=False, immediate_disable=False,
        dm_lockout=False, pause_brake_mps=5.0)
      self.assertEqual(axes.lateral_active, expected)
      self.assertFalse(axes.longitudinal_active)

  def test_permanent_and_unrelated_faults_still_disarm(self):
    state = car_state()
    for name in (log.OnroadEvent.EventName.steerUnavailable, log.OnroadEvent.EventName.controlsMismatch,
                 log.OnroadEvent.EventName.overheat):
      events = Events()
      events.add(name)
      self.assertTrue(disarming_fault(events.to_msg(), state))
    events = Events()
    events.add(log.OnroadEvent.EventName.wrongGear)
    self.assertFalse(disarming_fault(events.to_msg(), state))  # Events may lag the return to Drive.
    state.gearShifter = car.CarState.GearShifter.unknown
    self.assertTrue(disarming_fault(events.to_msg(), state))
    state.steerFaultPermanent = True
    self.assertTrue(disarming_fault([], state))
    owner = AolCardIntent(AolSettings(True, 0, 0, 0, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
    owner.allowed_latch = True
    owner.update(state)
    self.assertFalse(owner.allowed_latch)

  def test_native_rejection_rearms_with_one_new_press_without_replaying_old_receipt(self):
    owner = AolCardIntent(AolSettings(True, 0, 0, 0, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
    state = car_state()
    lkas = car.CarState.ButtonEvent.Type.lkas
    owner.update(state, now_ns=100)
    state.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=True)]
    owner.update(state, now_ns=200)
    self.assertTrue(owner.allowed_latch)
    state.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=False)]
    owner.update(state, now_ns=300)
    state.buttonEvents = []
    owner.update(state, now_ns=400, native_rejection_ns=350)
    self.assertFalse(owner.allowed_latch)
    state.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=True)]
    owner.update(state, now_ns=500, native_rejection_ns=350)
    self.assertTrue(owner.allowed_latch)
    state.buttonEvents = []
    owner.update(state, now_ns=600, native_rejection_ns=450)
    self.assertTrue(owner.allowed_latch)  # Delayed denial predates the new press.
    owner.update(state, now_ns=700, native_rejection_ns=650)
    self.assertFalse(owner.allowed_latch)
    owner.update(state, now_ns=800)
    self.assertFalse(owner.allowed_latch)  # The held physical button cannot rearm.
    state.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=False)]
    owner.update(state, now_ns=900)
    state.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=True)]
    owner.update(state, now_ns=1000)
    self.assertTrue(owner.allowed_latch)

  def test_native_rejection_and_fresh_press_same_frame_preserve_fault_inhibit(self):
    for fault in (False, True):
      owner = AolCardIntent(AolSettings(True, 0, 0, 0, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
      state = car_state()
      owner.update(state, now_ns=100)
      owner.allowed_latch = True
      state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
      owner.update(state, now_ns=200, native_rejection_ns=150, fault_active=fault)
      self.assertEqual(owner.allowed_latch, not fault)

  def test_explicit_latch_requires_new_gesture_after_fault(self):
    owner = AolCardIntent(AolSettings(True, 0, 0, 0, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
    state = car_state()
    lkas = car.CarState.ButtonEvent.Type.lkas
    owner.update(state, fault_active=False)
    state.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=True)]
    owner.update(state)
    self.assertTrue(owner.allowed_latch)

    state.buttonEvents = []
    owner.update(state, fault_active=True)
    self.assertFalse(owner.allowed_latch)
    state.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=False)]
    owner.update(state, fault_active=True)
    state.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=True)]
    owner.update(state, fault_active=True)
    self.assertFalse(owner.allowed_latch)
    state.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=False)]
    owner.update(state)
    state.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=True)]
    owner.update(state)  # No fresh clear event yet.
    self.assertFalse(owner.allowed_latch)

    # A held button at recovery is not a new request. The driver must release it first.
    owner.update(state, fault_active=False)
    self.assertFalse(owner.allowed_latch)
    state.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=False)]
    owner.update(state)
    state.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=True)]
    owner.update(state)
    self.assertTrue(owner.allowed_latch)

  def test_persisted_preferences_and_fresh_defaults(self):
    with OpenpilotPrefix():
      params = Params()
      fresh = read_settings(params)
      self.assertFalse(fresh.enabled)
      self.assertEqual(fresh.pause_brake_mps, 0.0)
      self.assertEqual(fresh.distance_actions, (0, 0, 0))
      params.put_bool('AlwaysOnLateral', True, block=True)
      params.put('PauseAOLOnBrake', 10.0, block=True)
      params.put('DistanceButtonControl', 3, block=True)
      saved = read_settings(params)
      self.assertTrue(saved.enabled)
      self.assertEqual(saved.pause_brake_mps, 10.0)
      self.assertEqual(saved.distance_actions, (3, 0, 0))

  def test_brake_pause_units_preserve_legacy_until_explicit_si_override(self):
    with OpenpilotPrefix():
      params = Params()
      params.put_bool('AlwaysOnLateral', True, block=True)
      params.put('PauseAOLOnBrake', 10.0, block=True)
      for metric in (False, True):
        params.put_bool('IsMetric', metric, block=True)
        self.assertEqual(read_settings(params).pause_brake_mps, 10.0)
      params.put('AolBrakePauseSpeedMps', 4.4704, block=True)
      self.assertAlmostEqual(read_settings(params).pause_brake_mps, 4.4704)
      self.assertTrue(read_settings(params).enabled)
      params.put('AolBrakePauseSpeedMps', 0.0, block=True)
      self.assertEqual(read_settings(params).pause_brake_mps, 0.0)
      params.put('AolBrakePauseSpeedMps', -1.0, block=True)
      self.assertFalse(read_settings(params).enabled)
      self.assertTrue(params.get_bool('AlwaysOnLateral'))
      params.remove('AolBrakePauseSpeedMps')
      self.assertEqual(read_settings(params).pause_brake_mps, 10.0)

  def test_invalid_threshold_never_falls_back_to_permissive_value(self):
    with OpenpilotPrefix():
      params = Params()
      params.put_bool('AlwaysOnLateral', True, block=True)
      params.put('PauseAOLOnBrake', 10.0, block=True)
      for key in ('AolBrakePauseSpeedMps', 'PauseAOLOnBrake'):
        path = Path(params.get_param_path(key))
        for value in (b'', b'bad', b'\xff', b'nan', b'inf', b'-1', b'100.1'):
          with self.subTest(key=key, value=value):
            path.write_bytes(value)
            self.assertFalse(read_settings(params).enabled)
            self.assertTrue(params.get_bool('AlwaysOnLateral'))
        path.unlink()
      self.assertTrue(read_settings(params).enabled)
      self.assertEqual(read_settings(params).pause_brake_mps, 0.0)

  def test_saved_threshold_controls_actual_brake_boundary(self):
    with OpenpilotPrefix():
      params = Params()
      params.put_bool('AlwaysOnLateral', True, block=True)
      params.put('PauseAOLOnBrake', 10.0, block=True)
      state = car_state(brake=True)
      native = SimpleNamespace(requestedLateral=True, requestedLongitudinal=False,
                               lateralAllowed=True, longitudinalAllowed=False)
      intent = SimpleNamespace(allowedLatch=True, lateralArmed=True, pauseLateral=False, pauseLongitudinal=False)
      for metric in (False, True):
        params.put_bool('IsMetric', metric, block=True)
        for speed, mode in ((9.9, 'off'), (10.0, 'lateralOnly')):
          state.vEgo = speed
          result = decide_axes(standard_lateral=False, standard_longitudinal=False, intent=intent,
                               native=native, car_state=state, initialized=True, model_ready=True,
                               no_entry=False, immediate_disable=False, dm_lockout=False,
                               pause_brake_mps=read_settings(params).pause_brake_mps)
          self.assertEqual(result.mode, mode)

  def test_honda_main_lkas_pause_and_cancel_ownership(self):
    settings = AolSettings(True, 5.0, 9, 0, (3, 4, 0), (3, 0, 0))
    owner = AolCardIntent(settings)
    state = car_state()
    state.cruiseState.available = True
    owner.update(state)
    self.assertFalse(owner.output(state)[0])  # LKAS button owns the latch

    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    owner.update(state)
    self.assertTrue(owner.output(state)[0])

    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
    owner.update(state)
    self.assertFalse(owner.pause_lateral)  # Honda cancel never doubles as pause

    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.gapAdjustCruise, pressed=True)]
    owner.update(state)
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.gapAdjustCruise, pressed=False)]
    owner.update(state)
    self.assertTrue(owner.pause_lateral)
    self.assertEqual(owner.output(state), (True, True, False))

  def test_invalid_can_and_settings_disable_intent(self):
    owner = AolCardIntent(AolSettings(True, 0, 0, 0, (0, 0, 0), (0, 0, 0)))
    state = car_state()
    state.cruiseState.available = True
    owner.update(state)
    self.assertTrue(owner.output(state)[0])
    state.canValid = False
    owner.update(state)
    self.assertFalse(owner.output(state)[0])

  def test_interrupted_distance_hold_does_not_replay_and_keeps_deliberate_pause(self):
    settings = AolSettings(True, 0, 0, 0, (3, 4, 0), (0, 0, 0))
    owner = AolCardIntent(settings)
    state = car_state()
    state.cruiseState.available = True
    button = car.CarState.ButtonEvent.Type.gapAdjustCruise
    owner.update(state)
    state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=True)]
    owner.update(state)
    state.buttonEvents = []
    for _ in range(5):
      owner.update(state)
    state.canValid = False
    owner.update(state)
    self.assertFalse(owner._held[int(button)])
    self.assertEqual(owner._timers[int(button)], 0)
    state.canValid = True
    state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=False)]
    owner.update(state)
    self.assertFalse(owner.pause_lateral or owner.pause_longitudinal)

    # A complete user pause remains latched through CAN loss.
    state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=True)]
    owner.update(state)
    state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=False)]
    owner.update(state)
    self.assertTrue(owner.pause_lateral)
    state.canValid = False
    owner.update(state)
    self.assertTrue(owner.pause_lateral)

    # If another owner consumed a release, it cannot complete the held gesture.
    state.canValid = True
    state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=True)]
    owner.update(state)
    state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=False)]
    owner.update(state, consumed_buttons=frozenset((int(button),)))
    self.assertFalse(owner._held[int(button)])
    self.assertTrue(owner.pause_lateral)

    # CAN loss just before the long-press boundary cannot finish that gesture.
    state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=True)]
    owner.update(state)
    state.buttonEvents = []
    for _ in range(CRUISE_LONG_PRESS - 2):
      owner.update(state)
    self.assertFalse(owner.pause_longitudinal)
    state.canValid = False
    owner.update(state)
    state.canValid = True
    for _ in range(3):
      owner.update(state)
    self.assertFalse(owner.pause_longitudinal)
    self.assertTrue(owner.pause_lateral)

    # An owner can reserve the button on a tick with no new button event.
    state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=True)]
    owner.update(state)
    state.buttonEvents = []
    for _ in range(CRUISE_LONG_PRESS - 2):
      owner.update(state)
    owner.update(state, consumed_buttons=frozenset((int(button),)))
    state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=False)]
    owner.update(state)
    self.assertFalse(owner.pause_longitudinal)
    self.assertTrue(owner.pause_lateral)

  def test_held_at_start_distance_waits_for_neutral_before_all_press_lengths(self):
    button = car.CarState.ButtonEvent.Type.gapAdjustCruise
    for held_ticks, actions in ((1, (3, 0, 0)), (CRUISE_LONG_PRESS, (0, 4, 0)),
                                (CRUISE_LONG_PRESS * 5, (0, 0, 3))):
      with self.subTest(held_ticks=held_ticks):
        settings = AolSettings(True, 0, 0, 0, actions, (0, 0, 0))
        owner = AolCardIntent(settings, explicit_latch=True)
        state = car_state()
        state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=True)]
        owner.update(state)
        state.buttonEvents = []
        for _ in range(held_ticks):
          owner.update(state)
        state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=False)]
        owner.update(state)
        self.assertFalse(owner.pause_lateral or owner.pause_longitudinal)
        state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=True)]
        owner.update(state)
        state.buttonEvents = []
        for _ in range(held_ticks - 1):
          owner.update(state)
        state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=False)]
        owner.update(state)
        self.assertEqual((owner.pause_lateral, owner.pause_longitudinal),
                         (held_ticks != CRUISE_LONG_PRESS, held_ticks == CRUISE_LONG_PRESS))




class IpcAxisContractTests(unittest.TestCase):
  def test_car_state_timeout_retains_only_original_fresh_valid_sample(self):
    sd = SelfdriveD.__new__(SelfdriveD)
    sd.car_state_sock = object()
    sd.CS_prev = car_state()
    sd.aol_car_state_log_ns = 0
    sd.conditional_car_state_valid = False
    sd.initialized = True
    sd.enabled = False
    self.enterContext(mock.patch.object(sd, 'sm', SimpleNamespace(update=mock.Mock()), create=True))
    stamp = 1_000_000_000
    message = messaging.new_message('carState')
    message.logMonoTime = stamp
    message.valid = True
    message.carState = sd.CS_prev
    with (mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one', return_value=message) as recv,
          mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=stamp) as now):
      sd.CS_prev = sd.data_sample()
      self.assertEqual(sd.aol_car_state_log_ns, stamp)
      recv.return_value = None  # 20 ms socket timeout, still inside the existing 30 ms lease.
      now.return_value = stamp + 23_000_000
      self.assertIs(sd.data_sample(), sd.CS_prev)
      self.assertEqual(sd.aol_car_state_log_ns, stamp)
      self.assertTrue(sd.conditional_car_state_valid)
      now.return_value = stamp + 30_000_001
      sd.data_sample()
      self.assertEqual(sd.aol_car_state_log_ns, 0)
      self.assertFalse(sd.conditional_car_state_valid)

      # A next-drive/new process has no retained source, even if CS_prev exists.
      sd.data_sample()
      self.assertEqual(sd.aol_car_state_log_ns, 0)
      message.logMonoTime = stamp + 24_000_000
      recv.return_value = message
      sd.CS_prev = sd.data_sample()
      self.assertEqual(sd.aol_car_state_log_ns, stamp + 24_000_000)
      for invalid_kind in ('valid', 'canValid', 'canTimeout', 'clock'):
        with self.subTest(invalid_kind=invalid_kind):
          message.valid = invalid_kind != 'valid'
          message.carState.canValid = invalid_kind != 'canValid'
          message.carState.canTimeout = invalid_kind == 'canTimeout'
          recv.return_value = message
          sd.CS_prev = sd.data_sample()
          recv.return_value = None
          now.return_value = message.logMonoTime + (-1 if invalid_kind == 'clock' else 20_000_000)
          sd.data_sample()
          self.assertEqual(sd.aol_car_state_log_ns, 0)
          self.assertFalse(sd.conditional_car_state_valid)

  def test_lateral_only_receipt_loss_keeps_take_control_alert(self):
    class SM:
      frame = 0

      def __getitem__(self, service):
        if service == 'deviceState':
          return SimpleNamespace(started=True, startedMonoTime=1)
        if service == 'driverMonitoringState':
          return SimpleNamespace(alertLevel=0, lockout=False, alwaysOnLockout=False)
        if service == 'extrinsicsCalibration':
          return SimpleNamespace(calStatus=log.ExtrinsicsCalibration.Status.calibrated)
        raise KeyError(service)

      def all_checks(self, _services):
        return True

    sd = SelfdriveD.__new__(SelfdriveD)
    sd.CP = SimpleNamespace(passive=False, openpilotLongitudinalControl=True)
    self.enterContext(mock.patch.object(sd, 'sm', SM(), create=True))
    sd.events = Events()
    sd.state_machine = StateMachine()
    sd.AM = AlertManager()
    from openpilot.starpilot.controllers.mode_actions import SwitchbackCooldown
    sd.switchback_capable = False
    sd.switchback_cooldown = SwitchbackCooldown()
    sd.switchback_setting_ns = time.monotonic_ns()
    sd.switchback_cooldown_ns = 300_000_000_000
    sd.personality = 1
    sd.is_metric = False
    sd.enabled = sd.active = False
    sd.initialized = True
    sd.aol_replay = True
    sd.aol_car_state_log_ns = 0
    sd.aol_session_id = 'drive-session'
    sd.aol_axis_decision = AxisDecision()
    sd.aol_dm_lateral_inhibit = False
    sd.aol_settings = None
    sd.nostalgia_paddle_cancel = False
    self.enterContext(mock.patch.object(sd, 'data_sample', car_state))
    self.enterContext(mock.patch.object(sd, 'update_events', lambda _cs: sd.events.clear()))
    sd.update_conditional_mode = mock.Mock()
    sd.publish_selfdriveState = mock.Mock()

    native = SimpleNamespace(requestedLateral=True, requestedLongitudinal=False,
                             lateralAllowed=True, longitudinalAllowed=False)
    intent = SimpleNamespace(allowedLatch=True, lateralArmed=True, pauseLateral=False, pauseLongitudinal=False)
    with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.current_intent', return_value=intent), \
         mock.patch('openpilot.selfdrive.selfdrived.selfdrived.current_native', side_effect=(None, native, None, None)):
      sd.sm.frame = 1
      sd.step()
      self.assertEqual(sd.aol_axis_decision.mode, 'off')
      self.assertFalse(sd.enabled)
      self.assertNotIn(ET.IMMEDIATE_DISABLE, sd.state_machine.current_alert_types)
      self.assertNotEqual(sd.AM.current_alert.alert_text_1, 'TAKE CONTROL IMMEDIATELY')

      sd.sm.frame = 2
      sd.step()
      self.assertEqual(sd.aol_axis_decision.mode, 'lateralOnly')
      self.assertFalse(sd.enabled)

      sd.sm.frame = 3
      sd.step()
      self.assertEqual(sd.aol_axis_decision.mode, 'off')
      self.assertFalse(sd.enabled)
      self.assertIn(ET.IMMEDIATE_DISABLE, sd.state_machine.current_alert_types)
      self.assertEqual(sd.AM.current_alert.alert_text_1, 'TAKE CONTROL IMMEDIATELY')
      self.assertEqual(sd.AM.current_alert.alert_text_2, 'Controls Mismatch')
      alert_end_frame = sd.AM.alerts['controlsMismatch/immediateDisable'].end_frame
      self.assertGreater(alert_end_frame, sd.sm.frame)

      sd.sm.frame = 4
      sd.step()
      self.assertNotIn(ET.IMMEDIATE_DISABLE, sd.state_machine.current_alert_types)
      self.assertEqual(sd.AM.current_alert.alert_text_1, 'TAKE CONTROL IMMEDIATELY')
      self.assertEqual(sd.AM.alerts['controlsMismatch/immediateDisable'].end_frame, alert_end_frame)

  def test_lateral_only_temporary_fault_uses_existing_orange_warning(self):
    class SM:
      frame = 1

      def __getitem__(self, service):
        if service == 'deviceState':
          return SimpleNamespace(started=True, startedMonoTime=1)
        if service == 'driverMonitoringState':
          return SimpleNamespace(alertLevel=0, lockout=False, alwaysOnLockout=False)
        if service == 'extrinsicsCalibration':
          return SimpleNamespace(calStatus=log.ExtrinsicsCalibration.Status.calibrated)
        raise KeyError(service)

      def all_checks(self, _services):
        return True

    sd = SelfdriveD.__new__(SelfdriveD)
    sd.CP = SimpleNamespace(passive=False, openpilotLongitudinalControl=True)
    self.enterContext(mock.patch.object(sd, 'sm', SM(), create=True))
    sd.events, sd.state_machine, sd.AM = Events(), StateMachine(), AlertManager()
    from openpilot.starpilot.controllers.mode_actions import SwitchbackCooldown
    sd.switchback_capable = False
    sd.switchback_cooldown = SwitchbackCooldown()
    sd.switchback_setting_ns = time.monotonic_ns()
    sd.switchback_cooldown_ns = 300_000_000_000
    sd.personality, sd.is_metric = 1, False
    sd.enabled = sd.active = False
    sd.initialized = sd.aol_replay = True
    sd.aol_car_state_log_ns = 0
    sd.aol_session_id = 'drive-session'
    sd.aol_axis_decision = AxisDecision()
    sd.aol_dm_lateral_inhibit = False
    sd.aol_settings = None
    sd.nostalgia_paddle_cancel = False
    state = car_state()
    state.steerFaultTemporary = True
    self.enterContext(mock.patch.object(sd, 'data_sample', return_value=state))
    self.enterContext(mock.patch.object(sd, 'update_events', lambda _cs: sd.events.clear()))
    sd.update_conditional_mode = mock.Mock()
    sd.publish_selfdriveState = mock.Mock()
    native = SimpleNamespace(requestedLateral=False, requestedLongitudinal=False,
                             lateralAllowed=False, longitudinalAllowed=False)
    intent = SimpleNamespace(allowedLatch=True, lateralArmed=True, pauseLateral=False, pauseLongitudinal=False)
    with (mock.patch('openpilot.selfdrive.selfdrived.selfdrived.current_intent', return_value=intent),
          mock.patch('openpilot.selfdrive.selfdrived.selfdrived.current_native', return_value=native)):
      sd.step()
      self.assertFalse(sd.enabled)
      self.assertFalse(sd.aol_axis_decision.desired_lateral)
      self.assertFalse(sd.aol_axis_decision.lateral_active)
      self.assertEqual(sd.AM.current_alert.alert_type, 'steerTempUnavailableSilent/warning')
      self.assertEqual(sd.AM.current_alert.alert_status, log.SelfdriveState.AlertStatus.userPrompt)
      self.assertEqual(sd.AM.current_alert.alert_text_1, 'Steering Assist Temporarily Unavailable')
      state.steerFaultTemporary = False
      native.requestedLateral = native.lateralAllowed = True
      sd.sm.frame += 1
      sd.step()
      self.assertTrue(sd.aol_axis_decision.lateral_active)
      self.assertNotIn(log.OnroadEvent.EventName.steerTempUnavailableSilent, sd.events.names)

  def test_native_receipt_gates_engagement_and_disables_on_loss(self):
    class SM:
      def __getitem__(self, service):
        if service == 'deviceState':
          return SimpleNamespace(started=True, startedMonoTime=1)
        if service == 'driverMonitoringState':
          return SimpleNamespace(alertLevel=0, lockout=False, alwaysOnLockout=False)
        if service == 'extrinsicsCalibration':
          return SimpleNamespace(calStatus=log.ExtrinsicsCalibration.Status.calibrated)
        raise KeyError(service)

      def all_checks(self, _services):
        return True

    def driver(aol_enabled):
      sd = SelfdriveD.__new__(SelfdriveD)
      sd.CP = SimpleNamespace(passive=False, openpilotLongitudinalControl=True)
      self.enterContext(mock.patch.object(sd, 'sm', SM(), create=True))
      sd.events = Events()
      sd.state_machine = StateMachine()
      sd.enabled = sd.active = False
      sd.initialized = True
      sd.aol_replay = aol_enabled
      sd.aol_car_state_log_ns = 0
      sd.aol_session_id = 'drive-session'
      sd.aol_axis_decision = AxisDecision()
      sd.aol_dm_lateral_inhibit = False
      sd.aol_settings = None
      sd.nostalgia_paddle_cancel = False
      self.enterContext(mock.patch.object(sd, 'data_sample', car_state))
      sd.update_alerts = mock.Mock()
      sd.update_conditional_mode = mock.Mock()
      sd.publish_selfdriveState = mock.Mock()
      self.enterContext(mock.patch.object(sd, 'update_events',
                                          lambda _cs: (sd.events.clear(), sd.events.add(log.OnroadEvent.EventName.buttonEnable))))
      return sd

    native = SimpleNamespace(requestedLateral=True, requestedLongitudinal=True,
                             lateralAllowed=True, longitudinalAllowed=True)
    intent = SimpleNamespace(allowedLatch=True, lateralArmed=True, pauseLateral=False, pauseLongitudinal=False)
    sd = driver(True)
    sd.initialized = False
    with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.current_intent', return_value=intent), \
         mock.patch('openpilot.selfdrive.selfdrived.selfdrived.current_native', side_effect=(None, None, native, None)):
      sd.step()
      self.assertFalse(sd.enabled or sd.active)
      self.assertEqual(sd.aol_axis_decision.mode, 'off')
      self.assertNotIn(log.OnroadEvent.EventName.controlsMismatch, sd.events.names)
      self.assertFalse(disarming_fault(sd.events.to_msg(), car_state()))
      sd.publish_selfdriveState.assert_called_once()
      sd.publish_selfdriveState.reset_mock()
      sd.initialized = True
      sd.step()
      self.assertFalse(sd.enabled)
      self.assertTrue(sd.events.contains(ET.NO_ENTRY))
      self.assertEqual(sd.aol_axis_decision.mode, 'off')
      sd.publish_selfdriveState.assert_called_once()  # disabled bootstrap still publishes the zero-axis request
      sd.step()
      self.assertTrue(sd.enabled and sd.active)
      self.assertEqual(sd.aol_axis_decision.mode, 'combined')
      sd.step()
      self.assertFalse(sd.enabled or sd.active)
      self.assertTrue(sd.events.contains(ET.IMMEDIATE_DISABLE))
      alerts = sd.events.create_alerts(sd.state_machine.current_alert_types)
      self.assertTrue(any(alert.alert_text_1 == 'TAKE CONTROL IMMEDIATELY' and
                          alert.alert_text_2 == 'Controls Mismatch' for alert in alerts))

    stock = driver(False)
    with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.current_native') as read_native:
      stock.step()
    read_native.assert_not_called()
    self.assertTrue(stock.enabled and stock.active)

  def test_independent_ack_keeps_unchanged_axis(self):
    state = car_state()
    old_combined = SimpleNamespace(requestedLateral=True, requestedLongitudinal=True,
                                   lateralAllowed=True, longitudinalAllowed=True)
    intent = SimpleNamespace(allowedLatch=True, lateralArmed=True, pauseLateral=False, pauseLongitudinal=False)
    def decide(standard_long, native):
      return decide_axes(standard_lateral=False, standard_longitudinal=standard_long,
                         intent=intent, native=native, car_state=state, initialized=True,
                         model_ready=True, no_entry=False, immediate_disable=False,
                         dm_lockout=False, pause_brake_mps=5.0)
    self.assertEqual(decide(True, old_combined).mode, 'combined')
    self.assertEqual(decide(False, old_combined).mode, 'lateralOnly')
    old_lateral = SimpleNamespace(requestedLateral=True, requestedLongitudinal=False,
                                  lateralAllowed=True, longitudinalAllowed=False)
    self.assertEqual(decide(True, old_lateral).mode, 'lateralOnly')
    intent.pauseLateral = True
    self.assertEqual(decide(True, old_combined).mode, 'longitudinalOnly')
    intent.pauseLateral = False
    intent.pauseLongitudinal = True
    self.assertEqual(decide(True, old_combined).mode, 'lateralOnly')
    intent.pauseLongitudinal = False
    old_long = SimpleNamespace(requestedLateral=False, requestedLongitudinal=True,
                               lateralAllowed=False, longitudinalAllowed=True)
    self.assertEqual(decide(True, old_long).mode, 'longitudinalOnly')


  def test_card_selfdrive_panda_cadence_and_four_modes(self):
    with OpenpilotPrefix():
      messaging.reset_context()
      pm = messaging.PubMaster(['carState', 'aolIntentWire', 'aolAxisState', 'aolSafetyWire'])
      sm = messaging.SubMaster(['carState', 'aolIntentWire', 'aolAxisState', 'aolSafetyWire'])
      base = time.monotonic_ns() - 50_000_000
      from opendbc.car import gen_empty_fingerprint
      from opendbc.car.honda.interface import CarInterface
      from opendbc.car.honda.values import CAR
      from openpilot.starpilot.aol.vehicle import policy_for
      CP = CarInterface.get_params(CAR.HONDA_ACCORD, gen_empty_fingerprint(), [], True, False, False)
      policy = policy_for(CP)
      CP.alternativeExperience |= policy.alternative_experience_addition
      CP.safetyConfigs[-1].safetyParam |= policy.safety_param_addition
      self.assertEqual(CP.safetyConfigs[-1].safetyParam, 34)

      def publish_intent(stamp, *, pause_lat=False, pause_long=False):
        message = messaging.new_message('aolIntentWire', 0)
        message.logMonoTime = stamp
        message.valid = True
        message.aolIntentWire = encode_intent(IntentState(
          'card-session', stamp - base + 1, stamp, stamp, stamp + 100_000_000,
          True, pause_lat, pause_long, True))
        pm.send('aolIntentWire', message)

      def publish_native(stamp, lat, long, session='drive-session'):
        message = messaging.new_message('aolSafetyWire', 0)
        message.logMonoTime = stamp
        message.valid = True
        message.aolSafetyWire = encode_safety(SafetyState(
          1, True, stamp, stamp + 200_000_000, int(car.CarParams.SafetyModel.hondaBosch),
          34, lat, long, lat, long, 'panda', session))
        pm.send('aolSafetyWire', message)

      for index, (standard_long, pause_lat, pause_long, expected) in enumerate((
        (False, False, False, 'lateralOnly'),
        (True, False, False, 'combined'),
        (True, True, False, 'longitudinalOnly'),
        (False, True, False, 'off'),
      )):
        stamp = base + index * 10_000_000
        state_msg = messaging.new_message('carState')
        state_msg.logMonoTime = stamp
        state_msg.valid = True
        pm.send('carState', state_msg)
        publish_intent(stamp, pause_lat=pause_lat, pause_long=pause_long)
        desired_lat = not pause_lat
        desired_long = standard_long and not pause_long
        publish_native(stamp, desired_lat, desired_long)
        sm.update(100)
        intent = current_intent(sm, car_state_ns=stamp, now_ns=stamp + 1_000_000)
        native = current_native(sm, CP, now_ns=stamp + 1_000_000, axis_session_id='drive-session')
        decision = decide_axes(standard_lateral=False, standard_longitudinal=standard_long,
                               intent=intent, native=native, car_state=car_state(),
                               initialized=True, model_ready=True, no_entry=False,
                               immediate_disable=False, dm_lockout=False, pause_brake_mps=5.0)
        self.assertEqual(decision.mode, expected)

      self.assertIsNone(current_native(sm, CP, now_ns=base + 500_000_000, axis_session_id='drive-session'))
      self.assertIsNone(current_native(sm, CP, now_ns=base + 31_000_000, axis_session_id='new-session'))

  def test_no_native_ack_still_requests_but_does_not_actuate(self):
    intent = SimpleNamespace(pauseLateral=False, pauseLongitudinal=False, allowedLatch=True)
    decision = decide_axes(standard_lateral=False, standard_longitudinal=True,
                           intent=intent, native=None, car_state=car_state(), initialized=True,
                           model_ready=True, no_entry=False, immediate_disable=False,
                           dm_lockout=False, pause_brake_mps=5.0)
    self.assertTrue(decision.desired_lateral)
    self.assertTrue(decision.desired_longitudinal)
    self.assertEqual(decision.mode, 'off')
    self.assertFalse(decision.native_acknowledged)


class UiProcessIntentTests(unittest.TestCase):
  def make_card(self):
    from openpilot.selfdrive.car.card import Car
    from openpilot.starpilot.aol.intent import AolProcessFaultContext

    card = Car.__new__(Car)
    card.aol_process_fault_context = AolProcessFaultContext()
    class SM:
      seen = {'managerState': True}
      valid = {'managerState': True}
      alive = {'managerState': True}
      logMonoTime = {'managerState': 1_000_000_000}
      events = Events()
      processes = []

      def __getitem__(self, key):
        if key == 'managerState':
          return SimpleNamespace(processes=self.processes)
        if key == 'onroadEvents':
          return self.events.to_msg()
        raise KeyError(key)
    card.sm = SM()
    return card

  def observe(self, card, stamp, failed):
    card.sm.logMonoTime['managerState'] = stamp
    card.sm.processes = [SimpleNamespace(name=name, running=name not in failed, shouldBeRunning=True)
                         for name in ('ui', 'modeld', 'controlsd', 'card', 'pandad', 'unknown_service')]
    card.aol_process_fault_context.observe(card.sm, stamp + 1)

  def test_actual_card_ui_fault_pause_recovery_and_ordinary_cancel_handoff(self):
    from openpilot.starpilot.aol.tests.test_ioniq6_stock_repair import stock
    from openpilot.starpilot.car.hyundai.aol import create_intent, native_latch_rejected

    card = self.make_card()
    cp = stock(True)
    cp.openpilotLongitudinalControl, cp.pcmCruise = True, False
    cp.safetyConfigs[0].safetyParam = 0x8895
    owner = create_intent(cp, AolSettings(True, 0., 9, 0, (0, 0, 0), (0, 0, 0)))
    state = car_state()
    state.cruiseState.available = True
    owner.update(state, now_ns=100)
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    owner.update(state, now_ns=200)
    state.buttonEvents = []
    self.assertTrue(owner.allowed_latch)
    self.observe(card, 1_000_000_000, {'ui'})
    card.sm.events.add(log.OnroadEvent.EventName.processNotRunning)
    event_ns = 1_020_000_000
    self.assertTrue(card.sm.events.contains(ET.NO_ENTRY))
    self.assertTrue(card.sm.events.contains(ET.SOFT_DISABLE))
    fault = card.aol_disarming_fault(state, event_ns, event_ns + 1)
    self.assertFalse(fault)
    owner.update(state, fault_active=fault)
    self.assertTrue(owner.allowed_latch)
    native = SimpleNamespace(requestedLateral=False, requestedLongitudinal=False,
                             lateralAllowed=False, longitudinalAllowed=False)
    self.assertFalse(native_latch_rejected(cp, native))
    for standard in (True, False):
      paused = decide_axes(standard_lateral=standard, standard_longitudinal=standard, intent=SimpleNamespace(
        allowedLatch=owner.allowed_latch, pauseLateral=False, pauseLongitudinal=False), native=native,
        car_state=state, initialized=True, model_ready=True, no_entry=True, immediate_disable=False,
        dm_lockout=False, pause_brake_mps=0)
      self.assertTrue(owner.allowed_latch)
      self.assertEqual(paused.mode, 'off')
      self.assertFalse(paused.desired_lateral or paused.desired_longitudinal)
    # Manager recovery precedes clearing the old fault event, as in the route.
    self.observe(card, 1_400_000_000, set())
    self.assertFalse(card.aol_disarming_fault(state, event_ns, 1_410_000_000))
    card.sm.events.clear()
    owner.update(state, fault_active=card.aol_disarming_fault(state, 1_420_000_000, 1_420_000_001))
    native.requestedLateral = native.lateralAllowed = True
    recovered = decide_axes(standard_lateral=False, standard_longitudinal=False,
      intent=SimpleNamespace(allowedLatch=owner.allowed_latch, pauseLateral=False, pauseLongitudinal=False),
      native=native, car_state=state, initialized=True, model_ready=True, no_entry=False,
      immediate_disable=False, dm_lockout=False, pause_brake_mps=0)
    self.assertEqual(recovered.mode, 'lateralOnly')  # No normal engagement or fresh button required.
    self.assertTrue(recovered.desired_lateral)
    self.assertFalse(recovered.desired_longitudinal)
    native.requestedLongitudinal = native.longitudinalAllowed = True
    for standard, expected in ((True, 'combined'), (False, 'lateralOnly')):
      state.buttonEvents = ([] if standard else
        [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.altButton2, pressed=True)])
      owner.update(state, standard_enabled=standard)
      self.assertTrue(owner.allowed_latch)
      native.requestedLongitudinal = native.longitudinalAllowed = standard
      decision = decide_axes(standard_lateral=standard, standard_longitudinal=standard,
        intent=SimpleNamespace(allowedLatch=owner.allowed_latch, pauseLateral=False, pauseLongitudinal=False),
        native=native, car_state=state, initialized=True, model_ready=True, no_entry=False,
        immediate_disable=False, dm_lockout=False, pause_brake_mps=0)
      self.assertEqual(decision.mode, expected)
    # Real requested-lateral revocation and critical faults keep their authority.
    native.lateralAllowed = False
    self.assertTrue(native_latch_rejected(cp, native))
    owner.update(state, now_ns=2_000_000_000, native_rejection_ns=1_990_000_000)
    self.assertFalse(owner.allowed_latch)
    owner.allowed_latch = True
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
    owner.update(state)
    self.assertFalse(owner.allowed_latch)  # Physical CANCEL remains intentional withdrawal.

  def test_context_denies_unknown_mixed_stale_missing_and_critical_faults(self):
    card = self.make_card()
    state = car_state()
    card.sm.events.add(log.OnroadEvent.EventName.processNotRunning)
    event_ns = 1_020_000_000
    self.assertTrue(card.aol_disarming_fault(state, event_ns, event_ns + 1))
    for failures in ({'controlsd'}, {'unknown_service'}, {'ui', 'modeld'}, set()):
      with self.subTest(failures=failures):
        card.aol_process_fault_context.history.clear()
        self.observe(card, 1_000_000_000, failures)
        self.assertTrue(card.aol_disarming_fault(state, event_ns, event_ns + 1))
    self.observe(card, 1_100_000_000, {'ui'})
    self.assertTrue(card.aol_disarming_fault(state, 1_120_000_000, 2_600_000_001))
    self.observe(card, 1_150_000_000, {'ui', 'modeld'})
    self.assertTrue(card.aol_disarming_fault(state, 1_120_000_000, 1_160_000_000))
    card.aol_process_fault_context.history.clear()
    self.observe(card, 1_100_000_000, {'ui'})
    card.sm.processes[0].shouldBeRunning = False
    card.aol_process_fault_context.observe(card.sm, 1_120_000_000)
    self.assertTrue(card.aol_disarming_fault(state, 1_120_000_000, 1_120_000_001))
    self.observe(card, 1_100_000_000, {'ui'})
    for source_flag in ('seen', 'valid', 'alive'):
      with self.subTest(source_flag=source_flag):
        getattr(card.sm, source_flag)['managerState'] = False
        card.aol_process_fault_context.observe(card.sm, 1_120_000_000)
        self.assertTrue(card.aol_disarming_fault(state, 1_120_000_000, 1_120_000_001))
        getattr(card.sm, source_flag)['managerState'] = True
        self.observe(card, 1_100_000_000, {'ui'})
    for name in (log.OnroadEvent.EventName.controlsMismatch, log.OnroadEvent.EventName.steerUnavailable):
      with self.subTest(name=name):
        card.sm.events.add(name)
        self.assertTrue(card.aol_disarming_fault(state, 1_120_000_000, 1_120_000_001))
        card.sm.events.clear()
        card.sm.events.add(log.OnroadEvent.EventName.processNotRunning)
    state.steerFaultPermanent = True
    self.assertTrue(card.aol_disarming_fault(state, 1_120_000_000, 1_120_000_001))


if __name__ == '__main__':
  unittest.main()
