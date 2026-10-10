import os
import unittest
from unittest import mock

from openpilot.cereal import log, messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.structs import car
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
from openpilot.selfdrive.selfdrived.alertmanager import AlertManager
from openpilot.selfdrive.selfdrived.events import Events, ET
from openpilot.selfdrive.selfdrived.state import StateMachine
from openpilot.starpilot.aol.runtime import AxisDecision, current_native
from openpilot.starpilot.aol.wire import IntentState, PandaSlot, SafetyState, encode_intent, encode_safety


def car_state(*, brake=False):
  return car.CarState(canValid=True, gearShifter=car.CarState.GearShifter.drive,
                      vEgo=20.0, brakePressed=brake)


class IoniqAvailabilityTests(unittest.TestCase):
  def _authority_callers(self, full_op, *, cp=None, intent_companion=None, genuine_events=False):
    self.enterContext(mock.patch('openpilot.selfdrive.selfdrived.selfdrived.REPLAY', False))
    from opendbc.car.gm.tests.test_bolt_volt_configurations import ordinary_params
    from opendbc.car.gm.values import CAR
    from openpilot.selfdrive.controls.controlsd import Controls
    from openpilot.starpilot.aol.vehicle import policy_for
    from openpilot.starpilot.controllers.mode_actions import SwitchbackCooldown
    from openpilot.starpilot.lateral.tests.test_lane_runtime import feed

    params = Params()
    params.put_bool('OpenpilotEnabledToggle', True, block=True)
    params.put_bool('SafeMode', False, block=True)
    params.put_bool('AlwaysOnLateral', True, block=True)
    supplied_cp = cp is not None
    if cp is None:
      cp = ordinary_params(CAR.CHEVROLET_VOLT_ASCM, alpha=True, sascm=True, radar=True)
    policy = policy_for(cp)
    cp.safetyConfigs[-1].safetyParam |= policy.safety_param_addition
    cp.alternativeExperience |= policy.alternative_experience_addition
    params.put('CarParams', cp.to_bytes(), block=True)
    controls = Controls()
    sd = SelfdriveD(CP=cp.as_reader()) if supplied_cp else SelfdriveD.__new__(SelfdriveD)
    sd.params = params
    sd.CP = cp.as_reader()
    services = ['deviceState', 'pandaStates', 'driverMonitoringState', 'extrinsicsCalibration', 'modelV2',
                'carState', 'aolIntentWire', 'aolSafetyWire', 'starpilotCarState']
    if not genuine_events:
      self.enterContext(mock.patch.object(sd, 'sm', messaging.SubMaster(services, ignore_avg_freq=services), create=True))
    sd.sm.update = mock.Mock()
    sd.events, sd.state_machine, sd.AM = Events(), StateMachine(), AlertManager()
    sd.state_machine.state = log.SelfdriveState.OpenpilotState.enabled if full_op else log.SelfdriveState.OpenpilotState.disabled
    sd.enabled = sd.active = full_op
    sd.mismatch_counter = 0
    sd.events_prev = []
    sd.experimental_mode = sd.requested_experimental_mode = False
    sd.initialized = sd.aol_replay = True
    sd.aol_authority_lost = sd.aol_dm_lateral_inhibit = False
    sd.aol_axis_decision = AxisDecision()
    sd.aol_settings = None
    sd.aol_car_state_log_ns = 0
    sd.conditional_car_state_valid = False
    sd.aol_last_intent = None
    if intent_companion is not None or not supplied_cp:
      sd.aol_intent_companion = intent_companion
    sd.aol_session_id, sd.aol_sequence = 'authority-session', 0
    from openpilot.starpilot.aol.transport_pause import TransportPause
    sd.aol_transport_pause = TransportPause(sd.CP, sd.aol_session_id)
    sd.conditional_replay = False
    sd.nostalgia_paddle_cancel = False
    sd.switchback_capable = False
    sd.switchback_cooldown = SwitchbackCooldown()
    sd.switchback_setting_ns, sd.switchback_cooldown_ns = 0, 300_000_000_000
    sd.personality, sd.is_metric = 1, False
    sd.CS_prev = car_state()
    sd.car_state_sock = object()
    original_optional_receive = messaging.recv_one_or_none

    def optional_receive(sock):
      return None if sock is sd.car_state_sock else original_optional_receive(sock)

    self.enterContext(mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=optional_receive))
    sd.update_conditional_mode = mock.Mock()
    if not genuine_events:
      self.enterContext(mock.patch.object(sd, 'update_events', lambda cs: (sd.events.clear(), sd._update_steering_authority(cs))))
    else:
      self.assertTrue(supplied_cp)
      self.assertFalse(sd.sm.simulation)
      sd.startup_event = None
      # Retain the real 100 Hz Ratekeeper created by SelfdriveD(CP=...).

    class Publisher:
      def __init__(self):
        self.messages = {}
      def send(self, service, message):
        self.messages[service] = messaging.log_from_bytes(message.to_bytes())
    self.enterContext(mock.patch.object(sd, 'pm', Publisher(), create=True))
    self.enterContext(mock.patch.object(controls, 'pm', Publisher()))
    clock = self.enterContext(mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=10_000_000_000))
    recv = self.enterContext(mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one'))
    base = 10_000_000_000
    seconds = (self.enterContext(mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic',
                                            return_value=base / 1e9)) if genuine_events else None)
    original_message = messaging.new_message
    def clocked_message(*args, **kwargs):
      message = original_message(*args, **kwargs)
      if 'logMonoTime' not in kwargs:
        message.logMonoTime = clock.return_value
      return message
    self.enterContext(mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.new_message', clocked_message))


    # The opt-in path keeps the constructor's production subscriptions and
    # frequency/validity checks. Only receive transport and the clock are synthetic.
    previous_control = [car.CarControl(enabled=full_op, latActive=full_op, longActive=full_op).as_reader()]
    due = {}
    def feed_event_sources(stamp, companions=(), *, car_output_valid=True):
      from openpilot.cereal.services import SERVICE_LIST
      names = ['deviceState', 'pandaStates', 'peripheralState', 'modelV2', 'extrinsicsCalibration',
               'carOutput', 'driverMonitoringState', 'longitudinalPlan', 'deviceMotion', 'lateralDelay',
               'managerState', 'vehicleParameters', 'radarState', 'lateralTorqueParameters',
               'controlsState', 'carControl', 'driverAssistance', *sd.camera_packets, *sd.sensor_packets]
      supplied = {sample.which(): sample for sample in companions}
      samples = []
      for name in dict.fromkeys([*names, *supplied]):
        frequency = SERVICE_LIST[name].frequency
        # Ignored authority wires remain fresh on every 100 Hz source tick.
        period = round(1e9 / min(frequency, 100)) if frequency > 0 else 0
        if (stamp < due.get(name, 0) and name not in ('aolIntentWire', 'aolSafetyWire', 'starpilotCarState') and
            not (name == 'pandaStates' and name in supplied and
                 any(p.safetyRxChecksInvalid or p.faults for p in supplied[name].pandaStates))):
          continue
        due[name] = stamp + period
        sample = supplied.get(name)
        if sample is None:
          sample = messaging.new_message(name, len(cp.safetyConfigs) if name == 'pandaStates' else None,
                                         valid=name != 'carOutput' or car_output_valid, logMonoTime=stamp)
          value = getattr(sample, name)
          if name == 'deviceState':
            value.started, value.startedMonoTime, value.freeSpacePercent = True, base - 1_000_000_000, 50.
          elif name == 'pandaStates':
            for panda, config in zip(value, cp.safetyConfigs, strict=True):
              panda.safetyModel, panda.safetyParam = config.safetyModel, config.safetyParam
              panda.alternativeExperience, panda.controlsAllowed = cp.alternativeExperience, full_op
          elif name == 'extrinsicsCalibration':
            value.calStatus, value.rpyCalib = 'calibrated', [0., 0., 0.]
          elif name == 'deviceMotion':
            value.inputsOK = value.posenetOK = True
          elif name == 'vehicleParameters':
            value.valid = True
          elif name == 'controlsState':
            value.lateralControlState.init('torqueState')
          elif name == 'carControl':
            sample.carControl = previous_control[0]
          sample = sample.as_reader()
        samples.append(sample)
      sd.sm.update_msgs(stamp / 1e9, samples)

    if genuine_events:
      # Prime actual cadence trackers before the initialized onroad baseline;
      # this advances fixture time only and neither sleeps nor skips a check.
      for prime in range(-110, 0):
        feed_event_sources(base + prime * 10_000_000)
      self.assertTrue(sd.sm.all_checks())

    def step(tick, *, timeout=False, old_intent=False, allowed=True, pause=False, latched=True,
             brake=False, steering=False, gas=False, user_disable=False, observed_state=None, authority_unavailable=False, companion=True,
             long_allowed=True, pause_long=False, state_stamp=None, intent_message=None, offset_ns=0,
             native_request_lat=True, native_request_long=None, native_valid=True, panda_fault=False,
             critical_event=None, calibrated=True, car_output_valid=True, relay_fault=False):
      now = base + tick * 10_000_000 + offset_ns
      clock.return_value = now
      if seconds is not None:
        seconds.return_value = now / 1e9
      state = car_state(brake=brake) if observed_state is None else observed_state
      state.cruiseState.available = True
      state.steeringPressed, state.gasPressed = steering, gas
      state_event = messaging.new_message('carState', valid=True, logMonoTime=now if state_stamp is None else state_stamp)
      state_event.carState = state
      recv.return_value = None if timeout else state_event.as_reader()
      frames = []
      for service in ('deviceState', 'driverMonitoringState', 'extrinsicsCalibration', 'modelV2'):
        message = messaging.new_message(service, valid=True, logMonoTime=now)
        if service == 'deviceState':
          message.deviceState.started, message.deviceState.startedMonoTime = True, base - 1_000_000_000
          if genuine_events:
            message.deviceState.freeSpacePercent = 50.
        elif service == 'extrinsicsCalibration':
          message.extrinsicsCalibration.calStatus = 'calibrated' if calibrated else 'uncalibrated'
          if genuine_events:
            message.extrinsicsCalibration.rpyCalib = [0., 0., 0.]
        frames.append(message.as_reader())
      pandas = messaging.new_message('pandaStates', len(cp.safetyConfigs), valid=True, logMonoTime=now)
      for panda, config in zip(pandas.pandaStates, cp.safetyConfigs, strict=True):
        panda.safetyModel, panda.safetyParam = config.safetyModel, config.safetyParam
        panda.alternativeExperience = cp.alternativeExperience
        panda.controlsAllowed = full_op
        panda.safetyRxChecksInvalid = panda_fault
        if relay_fault:
          panda.faults = ['relayMalfunction']
      frames.append(pandas.as_reader())
      intent_ns = base if old_intent else now
      intent = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=intent_ns)
      intent.aolIntentWire = encode_intent(IntentState('authority-card', tick + 1, intent_ns, intent_ns,
                                                     intent_ns + 200_000_000, latched, pause, pause_long, True, latched))
      if intent_message is not None:
        intent = intent_message
      native = messaging.new_message('aolSafetyWire', 0, valid=native_valid, logMonoTime=now)
      native.aolSafetyWire = encode_safety(SafetyState(1, True, now, now + 200_000_000,
        int(cp.safetyConfigs[-1].safetyModel.raw), cp.safetyConfigs[-1].safetyParam,
        allowed, full_op and long_allowed, native_request_lat,
        full_op if native_request_long is None else native_request_long, 'authority-panda', sd.aol_session_id,
        now if genuine_events else 0, tuple(
          PandaSlot(index, 'authority-panda' if index == len(cp.safetyConfigs) - 1 else f'silent-panda-{index}',
                    int(config.safetyModel.raw), config.safetyParam,
                    cp.alternativeExperience, full_op, panda_fault, False,
                    1 if relay_fault else 0)
          for index, config in enumerate(cp.safetyConfigs)) if genuine_events else ()))
      if companion:
        authority = messaging.new_message('starpilotCarState', valid=companion != 'invalid',
                                          logMonoTime=now - 1 if companion == 'wrong_stamp' else now)
        authority.starpilotCarState.sourceCarStateMonoTime = now - 1 if companion == 'wrong_source' else now
        authority.starpilotCarState.lateralAuthorityUnavailable = authority_unavailable
        frames.append(authority.as_reader())
      if genuine_events:
        feed_event_sources(now, frames + [intent.as_reader(), native.as_reader()], car_output_valid=car_output_valid)
      else:
        sd.sm.update_msgs(now / 1e9, frames + [intent.as_reader(), native.as_reader()])
      if user_disable:
        self.enterContext(mock.patch.object(sd, 'update_events', lambda cs: (
          sd.events.clear(), sd._update_steering_authority(cs), sd.events.add(log.OnroadEvent.EventName.pedalPressed))))
      if critical_event is not None:
        self.enterContext(mock.patch.object(sd, 'update_events', lambda cs: (
          sd.events.clear(), sd._update_steering_authority(cs), sd.events.add(critical_event))))
      sd.step()
      control_frames = []
      with mock.patch.object(controls.sm, 'update_msgs', side_effect=lambda _timestamp, messages: control_frames.extend(messages)):
        feed(controls, now, tick * 5, active=False, enabled=False)
      model = messaging.new_message('modelV2', valid=True, logMonoTime=now)
      model.modelV2 = next(message.modelV2 for message in control_frames if message.which() == 'modelV2')
      model.modelV2.action.desiredCurvature = 0.
      control_state = messaging.new_message('carState', valid=sd.conditional_car_state_valid,
                                            logMonoTime=sd.aol_car_state_log_ns)
      control_state.carState = sd.CS_prev
      replaced = ('carState', 'aolSafetyWire', 'modelV2', 'aolAxisState', 'selfdriveState')
      controls.sm.update_msgs(now / 1e9, [message for message in control_frames if message.which() not in replaced] +
                             [control_state.as_reader(), native.as_reader(), model.as_reader(),
                              sd.pm.messages['aolAxisState'], sd.pm.messages['selfdriveState']])
      command, lac_log = controls.state_control()
      controls.publish(command, lac_log)
      if genuine_events:
        previous_control[0] = command.as_reader()
      return sd.pm.messages['aolAxisState'].aolAxisState, sd.pm.messages['selfdriveState'].selfdriveState, command
    return sd, controls, step

  def _ioniq_availability_callers(self, full_op=True):
    from opendbc.car.hyundai.interface import CarInterface
    from opendbc.car.hyundai.radar_interface import RadarInterface
    from openpilot.selfdrive.car.card import Car
    from openpilot.selfdrive.car.tests.test_hyundai_aol import candidate

    previous_simulation = os.environ.get('SIMULATION')

    def restore_simulation():
      if previous_simulation is None:
        os.environ.pop('SIMULATION', None)
      else:
        os.environ['SIMULATION'] = previous_simulation

    self.addCleanup(restore_simulation)
    os.environ['SIMULATION'] = '0'
    _, cp = candidate(True)
    cp.safetyConfigs[-1].safetyParam |= 0x0800
    sd, controls, step = self._authority_callers(full_op, cp=cp, genuine_events=True)
    card_cp = cp.as_reader().as_builder()
    card = Car(CI=CarInterface(card_cp), RI=RadarInterface(card_cp))
    self.assertEqual(card.CP.to_dict(), sd.CP.to_dict())
    self.assertEqual(card.CP.safetyConfigs[-1].safetyParam, 0x8895)
    self.assertTrue(card.aol_card_intent.explicit_latch)
    card.slc_producer_session = 'authority-card'
    cs = car_state()
    cs.cruiseState.available = True
    card.aol_card_intent.update(cs, now_ns=9_980_000_000)
    cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    card.aol_card_intent.update(cs, now_ns=9_990_000_000)
    cs.buttonEvents = []
    self.assertTrue(card.aol_card_intent.allowed_latch)

    def receive(now, *, axis=None, event=None, state=None):
      frames = []
      for service in ('pandaStates', 'aolSafetyWire', 'deviceState', 'carControl'):
        message = messaging.new_message(service, len(sd.sm[service]) if service == 'pandaStates' else
                                        len(sd.sm[service]) if service == 'aolSafetyWire' else None,
                                        valid=sd.sm.valid[service], logMonoTime=sd.sm.logMonoTime[service])
        setattr(message, service, sd.sm[service])
        # Card receives the exact envelope bytes, including validity and stamps.
        frames.append(messaging.log_from_bytes(message.to_bytes()))
      card.sm.update_msgs(now / 1e9, frames + [m for m in (axis, event) if m is not None])
      observed = state if state is not None else car_state()
      observed.cruiseState.available = True
      card.CC_prev = card.sm['carControl']
      with mock.patch('openpilot.selfdrive.car.card.messaging.drain_sock_raw', return_value=[b'fixture']), \
           mock.patch('openpilot.selfdrive.car.card.can_capnp_to_list', return_value=[]), \
           mock.patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=now), \
           mock.patch('openpilot.selfdrive.car.card.REPLAY', False), \
           mock.patch.object(card.CI, 'update', return_value=observed), \
           mock.patch.object(card.RI, 'update', return_value=None), mock.patch.object(card.sm, 'update'):
        actual, _ = card.state_update()
      self.assertIs(actual, observed)
      return card.aol_card_intent.allowed_latch

    def drive(tick, **kwargs):
      kwargs.setdefault('latched', card.aol_card_intent.allowed_latch)
      return step(tick, **kwargs)

    for tick in (0, 1):
      axis, _, command = drive(tick)
      if full_op:
        self.assertTrue(axis.lateralActive and axis.longitudinalActive and command.latActive and command.longActive)
      else:
        self.assertTrue(axis.lateralActive and command.latActive)
        self.assertFalse(sd.enabled or sd.active or axis.longitudinalActive or command.longActive)
      self.assertTrue(receive(10_000_000_000 + tick * 10_000_000,
                              axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']))
    return sd, controls, drive, card, receive

  def test_ioniq_caroutput_communication_fault_joined_delivery_and_recovery(self):
    for order in ('axis_first', 'event_first', 'together'):
      with self.subTest(order=order), OpenpilotPrefix():
        sd, _, step, card, receive = self._ioniq_availability_callers()
        axis, state, command = step(2, car_output_valid=False)
        self.assertFalse(sd.sm.valid['carOutput'])
        self.assertTrue(sd.sm.all_checks(['carControl']))
        self.assertTrue(sd.CS_prev.canValid and not sd.CS_prev.canTimeout)
        self.assertIn(log.OnroadEvent.EventName.commIssue, sd.events.names)
        self.assertTrue(sd.events.contains(ET.SOFT_DISABLE))
        self.assertFalse(axis.lateralActive or axis.longitudinalActive or command.latActive or command.longActive)
        self.assertEqual(state.alertType, 'commIssue/softDisable')
        self.assertEqual(state.alertText2, 'Communication Issue Between Processes')
        # On the unmodified release this is 'critical', and actual Card clears
        # the latch. These expectations require the qualified availability path.
        proof, event = sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents']
        self.assertEqual(proof.aolAxisState.faultEventMonoTime, event.logMonoTime)
        now = 10_020_000_000
        if order == 'axis_first':
          self.assertTrue(receive(now, axis=proof))
          self.assertTrue(receive(now + 1_000_000, event=event))
        elif order == 'event_first':
          self.assertTrue(receive(now, event=event))
          self.assertTrue(receive(now + 1_000_000, axis=proof))
        else:
          self.assertTrue(receive(now, axis=proof, event=event))
        self.assertEqual(str(axis.faultReason), 'availabilityPause')
        self.assertFalse(sd.aol_authority_lost)
        self.assertTrue(card.aol_transport_feedback.retention_qualified)
        self.assertFalse(card.aol_transport_feedback.qualified)
        self.assertEqual(proof.aolAxisState.intentProducerSessionId, card.slc_producer_session)
        self.assertEqual(proof.aolAxisState.intentIntegrityEpoch, sd.aol_intent_companion.integrity_epoch)
        recovered, _, command = step(3, native_request_long=False)
        self.assertTrue(recovered.lateralActive and command.latActive)
        self.assertFalse(recovered.desiredLongitudinal or recovered.longitudinalActive or command.longActive)
        self.assertTrue(receive(10_030_000_000, axis=sd.pm.messages['aolAxisState'],
                                event=sd.pm.messages['onroadEvents']))

  def test_ioniq_availability_reengagement_requires_real_set_release_and_fresh_long_ack(self):
    from opendbc.car.hyundai.values import Buttons

    with OpenpilotPrefix():
      sd, _, step, card, receive = self._ioniq_availability_callers()
      occurrence = 0
      # Qualified availability keeps published ordinary state disabled;
      # retained lateral intent does not itself reengage LONG.
      for tick in range(2, 313):
        axis, _, command = step(tick, car_output_valid=False)
        self.assertFalse(axis.lateralActive or axis.longitudinalActive or command.latActive or command.longActive)
        published = sd.pm.messages['selfdriveState'].selfdriveState
        self.assertFalse(sd.enabled or sd.active or published.enabled or published.active)
        event = sd.pm.messages['onroadEvents'] if axis.faultEventMonoTime != occurrence else None
        occurrence = axis.faultEventMonoTime
        self.assertTrue(receive(10_000_000_000 + tick * 10_000_000,
                                axis=sd.pm.messages['aolAxisState'], event=event))
      self.assertFalse(sd.enabled or sd.active)
      recovered, _, command = step(313, native_request_long=False)
      self.assertTrue(recovered.lateralActive and command.latActive)
      published = sd.pm.messages['selfdriveState'].selfdriveState
      self.assertFalse(sd.enabled or sd.active or published.enabled or published.active)
      self.assertFalse(recovered.desiredLongitudinal or recovered.longitudinalActive or command.longActive)
      self.assertTrue(receive(13_130_000_000, axis=sd.pm.messages['aolAxisState'],
                              event=sd.pm.messages['onroadEvents']))

      pressed = car_state()
      pressed.cruiseState.available = True
      pressed.buttonEvents = card.CI.CS.create_cruise_button_events(Buttons.SET_DECEL, Buttons.NONE)
      pressed.buttonEnable = card.CI.CS.update_button_enable(pressed.buttonEvents)
      self.assertFalse(pressed.buttonEnable)
      axis, _, command = step(314, observed_state=pressed, native_request_long=False)
      self.assertNotIn(log.OnroadEvent.EventName.buttonEnable, sd.events.names)
      self.assertFalse(sd.enabled or axis.longitudinalActive or command.longActive)
      self.assertTrue(receive(13_140_000_000, axis=sd.pm.messages['aolAxisState'],
                              event=sd.pm.messages['onroadEvents'], state=pressed))

      released = car_state()
      released.cruiseState.available = True
      released.buttonEvents = card.CI.CS.create_cruise_button_events(Buttons.NONE, Buttons.SET_DECEL)
      released.buttonEnable = card.CI.CS.update_button_enable(released.buttonEvents)
      self.assertTrue(released.buttonEnable)
      pending, _, command = step(315, observed_state=released, native_request_long=False)
      self.assertIn(log.OnroadEvent.EventName.buttonEnable, sd.events.names)
      self.assertTrue(sd.events.contains(ET.ENABLE))
      self.assertFalse(sd.events.contains(ET.NO_ENTRY))
      self.assertTrue(sd.enabled and sd.active and pending.desiredLongitudinal)
      self.assertTrue(pending.lateralActive and command.latActive)
      self.assertFalse(pending.longitudinalActive or command.longActive)
      self.assertTrue(receive(13_150_000_000, axis=sd.pm.messages['aolAxisState'],
                              event=sd.pm.messages['onroadEvents'], state=released))

      combined, _, command = step(316, native_request_long=True)
      native = current_native(sd.sm, sd.CP, now_ns=13_160_000_000, axis_session_id=sd.aol_session_id)
      self.assertIsNotNone(native)
      self.assertTrue(native.requestedLongitudinal and native.longitudinalAllowed)
      self.assertEqual(native.observedMonoTime, 13_160_000_000)
      self.assertTrue(combined.lateralActive and combined.longitudinalActive and command.latActive and command.longActive)
      self.assertTrue(receive(13_160_000_000, axis=sd.pm.messages['aolAxisState'],
                              event=sd.pm.messages['onroadEvents']))

  def test_ioniq_aol_only_availability_prompt_reaches_controls_and_clears_on_recovery(self):
    with OpenpilotPrefix():
      sd, controls, step, card, receive = self._ioniq_availability_callers(full_op=False)
      axis, state, command = step(2, car_output_valid=False)
      self.assertEqual(str(axis.faultReason), 'availabilityPause')
      self.assertEqual(state.alertType, 'aolAvailability/warning')
      self.assertEqual((state.alertText1, state.alertText2), ('Steering Paused', 'Communication Issue'))
      self.assertEqual(str(state.alertSound), 'prompt')
      delivered = controls.sm['selfdriveState']
      self.assertEqual(delivered.alertType, state.alertType)
      self.assertEqual(str(delivered.alertSound), 'prompt')
      self.assertFalse(sd.enabled or sd.active or state.enabled or state.active or
                       axis.lateralActive or axis.longitudinalActive or command.latActive or command.longActive)
      self.assertTrue(receive(10_020_000_000, axis=sd.pm.messages['aolAxisState'],
                              event=sd.pm.messages['onroadEvents']))
      for tick in range(3, 45):
        axis, state, command = step(tick, car_output_valid=False)
        self.assertEqual(state.alertType, 'aolAvailability/warning')
        self.assertFalse(sd.enabled or sd.active or state.enabled or state.active)
        self.assertFalse(axis.lateralActive or axis.longitudinalActive or command.latActive or command.longActive)
        self.assertTrue(receive(10_000_000_000 + tick * 10_000_000, axis=sd.pm.messages['aolAxisState']))
      # The initial prompt has the candidate's bounded 0.4 s duration; visual
      # pause warning remains current after audio expires.
      self.assertEqual(str(state.alertSound), 'none')
      self.assertEqual(str(controls.sm['selfdriveState'].alertSound), 'none')
      for tick in range(45, 48):
        recovered, state, command = step(tick, native_request_long=False)
        self.assertTrue(recovered.lateralActive and command.latActive)
        self.assertFalse(sd.enabled or sd.active or state.enabled or state.active or recovered.desiredLongitudinal or
                         recovered.longitudinalActive or command.longActive)
        self.assertTrue(receive(10_000_000_000 + tick * 10_000_000, axis=sd.pm.messages['aolAxisState'],
                                event=sd.pm.messages['onroadEvents']))
      self.assertNotEqual(state.alertType, 'aolAvailability/warning')
      self.assertNotEqual(controls.sm['selfdriveState'].alertType, 'aolAvailability/warning')
      self.assertEqual(str(state.alertSound), 'none')
      self.assertEqual(str(controls.sm['selfdriveState'].alertSound), 'none')

  def test_ioniq_availability_sustained_advancing_proof_keeps_warning_and_no_long(self):
    with OpenpilotPrefix():
      sd, _, step, card, receive = self._ioniq_availability_callers()
      occurrences = set()
      for tick in range(2, 413):
        axis, state, command = step(tick, car_output_valid=False)
        now = 10_000_000_000 + tick * 10_000_000
        self.assertEqual(str(axis.faultReason), 'availabilityPause')
        self.assertTrue(axis.desiredLateral and axis.nativeAcknowledged)
        self.assertFalse(axis.lateralActive or axis.desiredLongitudinal or axis.longitudinalActive or
                         command.latActive or command.longActive)
        self.assertIn(log.OnroadEvent.EventName.commIssue, sd.events.names)
        self.assertTrue(state.alertText1 or state.alertText2)
        proof, event = sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents']
        advanced = axis.faultEventMonoTime not in occurrences
        occurrences.add(axis.faultEventMonoTime)
        self.assertTrue(receive(now, axis=proof, event=event if advanced else None))
        self.assertTrue(card.aol_transport_feedback.retention_qualified)
      # Real periodic SD publications advance the matched occurrence beyond the
      # initial 30 ms pairing window; they do not extend an unmatched occurrence.
      self.assertGreaterEqual(len(occurrences), 4)
      self.assertFalse(sd.enabled or sd.active)
      self.assertEqual(state.alertType, 'aolAvailability/warning')
      self.assertEqual((state.alertText1, state.alertText2), ('Steering Paused', 'Communication Issue'))
      recovered, _, command = step(413, native_request_long=False)
      self.assertTrue(recovered.lateralActive and command.latActive)
      self.assertFalse(recovered.desiredLongitudinal or recovered.longitudinalActive or command.longActive)
      self.assertFalse(sd.enabled or sd.active)
      self.assertTrue(receive(14_130_000_000, axis=sd.pm.messages['aolAxisState'],
                              event=sd.pm.messages['onroadEvents']))

  def test_ioniq_availability_missing_pair_has_fixed_deadline(self):
    for missing in ('axis', 'event'):
      with self.subTest(missing=missing), OpenpilotPrefix():
        sd, _, step, card, receive = self._ioniq_availability_callers()
        step(2, car_output_valid=False)
        proof, event = sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents']
        now = 10_020_000_000
        self.assertTrue(receive(now, axis=proof if missing == 'event' else None,
                                event=event if missing == 'axis' else None))
        step(4, car_output_valid=False, native_request_long=False)
        renewed = sd.pm.messages['aolAxisState']
        self.assertTrue(receive(now + 20_000_000, axis=renewed if missing == 'event' else None,
                                event=event if missing == 'axis' else None))
        self.assertFalse(receive(now + 31_000_000, axis=renewed if missing == 'event' else None))
        self.assertFalse(receive(now + 32_000_000, axis=proof, event=event))
        self.assertFalse(card.aol_card_intent.allowed_latch)

  def test_ioniq_availability_never_masks_native_can_or_integrity_fault(self):
    for fault in ('native_missing', 'native_denied', 'permanent_eps', 'can_invalid', 'relay',
                  'intent_invalid', 'producer_restart'):
      with self.subTest(fault=fault), OpenpilotPrefix():
        sd, _, step, card, receive = self._ioniq_availability_callers()
        step(2, car_output_valid=False)
        self.assertTrue(receive(10_020_000_000, axis=sd.pm.messages['aolAxisState'],
                                event=sd.pm.messages['onroadEvents']))
        kwargs = {'car_output_valid': False, 'native_request_long': False}
        observed = car_state()
        if fault == 'native_missing':
          kwargs['native_valid'] = False
        elif fault == 'native_denied':
          kwargs['allowed'] = False
        elif fault == 'permanent_eps':
          observed.steerFaultPermanent = True
        elif fault == 'can_invalid':
          observed.canValid = False
        elif fault == 'relay':
          kwargs['relay_fault'] = True
        else:
          stamp = 10_030_000_000
          intent = messaging.new_message('aolIntentWire', 0, valid=fault != 'intent_invalid', logMonoTime=stamp)
          intent.aolIntentWire = encode_intent(IntentState(
            'restarted-card' if fault == 'producer_restart' else card.slc_producer_session,
            1, stamp, stamp, stamp + 200_000_000, True, False, False, True, True))
          kwargs['intent_message'] = intent
        axis, _, command = step(3, observed_state=observed, **kwargs)
        self.assertFalse(axis.lateralActive or axis.longitudinalActive or command.latActive or command.longActive)
        self.assertEqual(str(axis.faultReason), 'critical')
        self.assertFalse(receive(10_030_000_000, axis=sd.pm.messages['aolAxisState'],
                                 event=sd.pm.messages['onroadEvents'], state=observed))
        self.assertFalse(card.aol_card_intent.allowed_latch)
