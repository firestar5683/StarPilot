"""Actual family caller fixtures with synthetic transport and explicit clocks."""

from contextlib import ExitStack, contextmanager
import os
import time
from unittest import mock

from opendbc.car import gen_empty_fingerprint
from opendbc.car.car_helpers import interfaces
from opendbc.car.structs import car
from openpilot.cereal import log, messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car import card as card_module
from openpilot.starpilot.aol.runtime import current_native
from openpilot.starpilot.aol.vehicle import native_matches_cp, policy_for
from openpilot.starpilot.aol.tests.test_ioniq_availability import IoniqAvailabilityTests as _IoniqAvailabilityTests, car_state


def authority_case():
  return _IoniqAvailabilityTests(methodName='runTest')


def callers(cleanup, family, lateral_only):
  cleanup.enter_context(OpenpilotPrefix())
  cleanup.enter_context(mock.patch.dict(os.environ, {'SIMULATION': '0', 'AOL_REPLAY_RUNTIME': '1'}))
  saved = Params()
  saved.put_bool('AlwaysOnLateral', True, block=True)
  if family == 'gm':
    from opendbc.car.gm.tests.test_bolt_pedal import params
    from opendbc.car.gm.values import CAR

    cp = params(CAR.CHEVROLET_BOLT_CC_2018_2021, pedal=True, camera=True)
  else:
    from openpilot.starpilot.lateral.tests.test_lane_runtime import publish_corolla_params

    cp = publish_corolla_params(saved)
  assert cp.openpilotLongitudinalControl and policy_for(cp).intent_supported
  case = authority_case()
  cleanup.callback(case.doCleanups)
  sd, controls, raw_drive = case._authority_callers(not lateral_only, cp=cp, genuine_events=True)

  def drive(tick, **kwargs):
    state = kwargs.get('observed_state')
    if state is None:
      state = car_state()
      kwargs['observed_state'] = state
    # Toyota's real pcmCruise events require the accepted stock cruise source.
    # This supplies parsed physical input; no SelfdriveD enabled flag is changed.
    state.cruiseState.available = True
    state.cruiseState.enabled = bool(sd.CP.pcmCruise and not lateral_only)
    return raw_drive(tick, **kwargs)

  interface = interfaces[str(cp.carFingerprint)]
  parsed_cp = cp.as_reader().as_builder()
  card = card_module.Car(CI=interface(parsed_cp), RI=interface.RadarInterface(parsed_cp))
  assert card.CP.to_dict() == sd.CP.to_dict(), 'Family startup CP must match actual SD owner'
  card.slc_producer_session = 'authority-card'
  physical = car_state()
  physical.cruiseState.available = True
  card.aol_card_intent.update(physical, now_ns=9_990_000_000)
  assert card.aol_card_intent.allowed_latch, 'Actual family main-edge owner did not arm'

  def receive(now, state=None):
    frames = []
    for name in ('pandaStates', 'aolSafetyWire', 'deviceState', 'carControl'):
      source = controls.pm.messages['carControl'] if name == 'carControl' else None
      message = messaging.new_message(
        name,
        len(sd.sm[name]) if name in ('pandaStates', 'aolSafetyWire') else None,
        valid=True if source is not None else sd.sm.valid[name],
        logMonoTime=int(source.logMonoTime) if source is not None else int(sd.sm.logMonoTime[name]),
      )
      setattr(message, name, getattr(source, name) if source is not None else sd.sm[name])
      frames.append(messaging.log_from_bytes(message.to_bytes()))
    frames.extend(sd.pm.messages[name] for name in ('aolAxisState', 'onroadEvents'))
    card.sm.update_msgs(now / 1e9, frames)
    physical = car_state() if state is None else state
    physical.cruiseState.available = True
    with (
      mock.patch.object(card_module.messaging, 'drain_sock_raw', return_value=[b'fixture']),
      mock.patch.object(card_module, 'can_capnp_to_list', return_value=[]),
      mock.patch.object(card_module.time, 'monotonic_ns', return_value=now),
      mock.patch.object(card_module, 'REPLAY', False),
      mock.patch.object(card.sm, 'update'),
      mock.patch.object(card.CI, 'update', return_value=physical),
    ):
      actual, rd = card.state_update()
    assert actual is physical
    return card.aol_card_intent.allowed_latch

  for tick in (0, 1):
    axis, state, command = drive(tick, native_request_long=not lateral_only)
    assert axis.lateralActive and command.latActive
    assert axis.longitudinalActive == command.longActive == (not lateral_only)
    native = current_native(sd.sm, sd.CP, now_ns=10_000_000_000 + tick * 10_000_000, axis_session_id=sd.aol_session_id)
    assert native is not None and native.pandaInventory
    assert native_matches_cp(sd.CP, native.safetyModel, native.safetyParam)
    assert len(native.pandaInventory) == len(sd.CP.safetyConfigs)
    assert receive(10_000_000_000 + tick * 10_000_000)
  return sd, controls, drive, card, receive


def _hkg_family_callers(self, full_op=True):
  CarInterface = self.interface_type
  RadarInterface = self.radar_type
  from openpilot.selfdrive.car.card import Car

  previous_simulation = os.environ.get('SIMULATION')

  def restore_simulation():
    if previous_simulation is None:
      os.environ.pop('SIMULATION', None)
    else:
      os.environ['SIMULATION'] = previous_simulation

  self.addCleanup(restore_simulation)
  os.environ['SIMULATION'] = '0'
  cp = self.family_cp.as_builder()
  sd, controls, step = self._authority_callers(full_op, cp=cp, genuine_events=True)
  card_cp = cp.as_reader().as_builder()
  card = Car(CI=CarInterface(card_cp), RI=RadarInterface(card_cp))
  self.assertEqual(card.CP.to_dict(), sd.CP.to_dict())
  from openpilot.starpilot.aol.vehicle import policy_for

  self.assertEqual(card.aol_card_intent.explicit_latch, policy_for(card.CP).explicit_latch)
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
      message = messaging.new_message(
        service,
        len(sd.sm[service]) if service == 'pandaStates' else len(sd.sm[service]) if service == 'aolSafetyWire' else None,
        valid=sd.sm.valid[service],
        logMonoTime=sd.sm.logMonoTime[service],
      )
      setattr(message, service, sd.sm[service])
      # Card receives the exact envelope bytes, including validity and stamps.
      frames.append(messaging.log_from_bytes(message.to_bytes()))
    card.sm.update_msgs(now / 1e9, frames + [m for m in (axis, event) if m is not None])
    observed = state if state is not None else car_state()
    observed.cruiseState.available = True
    card.CC_prev = card.sm['carControl']
    with (
      mock.patch('openpilot.selfdrive.car.card.messaging.drain_sock_raw', return_value=[b'fixture']),
      mock.patch('openpilot.selfdrive.car.card.can_capnp_to_list', return_value=[]),
      mock.patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=now),
      mock.patch('openpilot.selfdrive.car.card.REPLAY', False),
      mock.patch.object(card.CI, 'update', return_value=observed),
      mock.patch.object(card.RI, 'update', return_value=None),
      mock.patch.object(card.sm, 'update'),
    ):
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
    self.assertTrue(receive(10_000_000_000 + tick * 10_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']))
  return sd, controls, drive, card, receive


def hkg_family_case(family, full):
  class FamilyCase(_IoniqAvailabilityTests):
    family_callers = _hkg_family_callers

  case = FamilyCase(methodName='runTest')
  fp = gen_empty_fingerprint()
  if family == 'honda':
    from opendbc.car.honda.interface import CarInterface
    from opendbc.car.honda.radar_interface import RadarInterface
    from opendbc.car.honda.values import CAR

    # Existing HondaFamilyQualificationTests: Accord stock radar on bus1,
    # classic Bosch alpha LONG uses the factory interface option, no marker.
    fp[1][0x1A3] = 8
    cp = CarInterface.get_params(CAR.HONDA_ACCORD, fp, [], full, False, False)
  else:
    from opendbc.car.hyundai.interface import CarInterface
    from opendbc.car.hyundai.radar_interface import RadarInterface
    from opendbc.car.hyundai.values import CAR

    model = CAR.HYUNDAI_SONATA if family == 'hkg_classic' else CAR.KIA_EV6
    if family == 'hkg_canfd':
      # Existing test_hyundai.TestHyundai.test_feature_detection LKA topology.
      from opendbc.car.hyundai.hyundaicanfd import CanBus

      fp[CanBus(None, fp).CAM][0x50] = 16
    else:
      # Existing feature_detection radar available case.
      from opendbc.car.hyundai.radar_interface import RADAR_START_ADDR

      fp[1][RADAR_START_ADDR] = 8
    cp = CarInterface.get_params(model, fp, [], full, False, False)
  case.family_cp = cp.as_reader()
  case.interface_type, case.radar_type = CarInterface, RadarInterface
  assert cp.openpilotLongitudinalControl == full, f"{family}: declared factory alpha option did not admit requested axis"
  return case


def _honda_family_callers(self, full_op=True):
  CarInterface = self.interface_type
  RadarInterface = self.radar_type
  from openpilot.selfdrive.car.card import Car

  previous_simulation = os.environ.get('SIMULATION')

  def restore_simulation():
    if previous_simulation is None:
      os.environ.pop('SIMULATION', None)
    else:
      os.environ['SIMULATION'] = previous_simulation

  self.addCleanup(restore_simulation)
  os.environ['SIMULATION'] = '0'
  from openpilot.common.params import Params

  params = Params()
  params.put_bool('OpenpilotEnabledToggle', True, block=True)
  params.put_bool('AlwaysOnLateral', True, block=True)
  params.put_bool('SafeMode', False, block=True)
  # Production Card owns CP qualification/marker and publishes it first.
  card_cp = self.family_cp.as_builder()
  card = Car(CI=CarInterface(card_cp), RI=RadarInterface(card_cp))
  with car.CarParams.from_bytes(params.get('CarParams')) as published:
    cp = published.as_builder()
  self.assertEqual(cp.to_dict(), card.CP.to_dict())
  self.assertTrue(card.aol_qualified)
  sd, controls, step = self._authority_callers(full_op, cp=cp, genuine_events=True)
  self.assertTrue(sd.aol_replay)
  self.assertIn('aolIntentWire', sd.sm.services)
  from opendbc.car.honda.stock_aol import qualified
  from openpilot.selfdrive.selfdrived.events import ET

  self.assertTrue(qualified(card.CP, marked_only=True))
  self.assertIn(card.CP.transmissionType, (car.CarParams.TransmissionType.automatic, car.CarParams.TransmissionType.cvt))
  rules = sd.events.event_rules[log.OnroadEvent.EventName.cruiseDisabled]
  self.assertIn(ET.USER_DISABLE, rules)
  self.assertNotIn(ET.IMMEDIATE_DISABLE, rules)
  self.assertEqual(card.CP.to_dict(), sd.CP.to_dict())
  from openpilot.starpilot.aol.vehicle import policy_for

  self.assertEqual(card.aol_card_intent.explicit_latch, policy_for(card.CP).explicit_latch)
  card.slc_producer_session = 'authority-card'
  cs = car_state()
  cs.cruiseState.available = False
  card.aol_card_intent.update(cs, now_ns=9_970_000_000)
  cs.cruiseState.available = True
  card.aol_card_intent.update(cs, now_ns=9_980_000_000)
  cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
  card.aol_card_intent.update(cs, now_ns=9_990_000_000)
  cs.buttonEvents = []
  self.assertTrue(card.aol_card_intent.allowed_latch)

  actual_clock_gettime_ns = time.clock_gettime_ns

  def receive(now, *, axis=None, event=None, state=None):
    frames = []
    for service in ('pandaStates', 'aolSafetyWire', 'deviceState', 'carControl'):
      message = messaging.new_message(
        service,
        len(sd.sm[service]) if service == 'pandaStates' else len(sd.sm[service]) if service == 'aolSafetyWire' else None,
        valid=sd.sm.valid[service],
        logMonoTime=sd.sm.logMonoTime[service],
      )
      setattr(message, service, sd.sm[service])
      # Card receives the exact envelope bytes, including validity and stamps.
      frames.append(messaging.log_from_bytes(message.to_bytes()))
    card.sm.update_msgs(now / 1e9, frames + [m for m in (axis, event) if m is not None])
    observed = state if state is not None else car_state()
    observed.cruiseState.available = True
    card.CC_prev = card.sm['carControl']
    with (
      mock.patch('openpilot.selfdrive.car.card.messaging.drain_sock_raw', return_value=[b'fixture']),
      mock.patch('openpilot.selfdrive.car.card.can_capnp_to_list', return_value=[]),
      mock.patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=now),
      mock.patch(
        'openpilot.selfdrive.car.card.time.clock_gettime_ns', side_effect=lambda clock: now if clock == time.CLOCK_BOOTTIME else actual_clock_gettime_ns(clock)
      ),
      mock.patch('openpilot.selfdrive.car.card.REPLAY', False),
      mock.patch.object(card.CI, 'update', return_value=observed),
      mock.patch.object(card.RI, 'update', return_value=None),
      mock.patch.object(card.sm, 'update'),
    ):
      self.assertTrue(card.startup_panda_configured())
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
    self.assertTrue(receive(10_000_000_000 + tick * 10_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']))
  return sd, controls, drive, card, receive


def honda_family_case(family, full):
  class FamilyCase(_IoniqAvailabilityTests):
    family_callers = _honda_family_callers

  case = FamilyCase(methodName='runTest')
  fp = gen_empty_fingerprint()
  if family == 'honda':
    from opendbc.car.honda.interface import CarInterface
    from opendbc.car.honda.radar_interface import RadarInterface
    from opendbc.car.honda.values import CAR

    # Existing HondaFamilyQualificationTests: Accord stock radar on bus1,
    # classic Bosch alpha LONG uses the factory interface option, no marker.
    model = CAR.HONDA_ACCORD if full else CAR.HONDA_CIVIC_BOSCH
    cp = CarInterface.get_params(model, fp, [], full, False, False)
  else:
    from opendbc.car.hyundai.interface import CarInterface
    from opendbc.car.hyundai.radar_interface import RadarInterface
    from opendbc.car.hyundai.values import CAR

    model = CAR.HYUNDAI_SONATA if family == 'hkg_classic' else CAR.KIA_EV6
    if family == 'hkg_canfd':
      # Existing test_hyundai.TestHyundai.test_feature_detection LKA topology.
      from opendbc.car.hyundai.hyundaicanfd import CanBus

      fp[CanBus(None, fp).CAM][0x50] = 16
    else:
      # Existing feature_detection radar available case.
      from opendbc.car.hyundai.radar_interface import RADAR_START_ADDR

      fp[1][RADAR_START_ADDR] = 8
    cp = CarInterface.get_params(model, fp, [], full, False, False)
  case.family_cp = cp.as_reader()
  case.interface_type, case.radar_type = CarInterface, RadarInterface
  assert cp.openpilotLongitudinalControl == full, f"{family}: declared factory alpha option did not admit requested axis"
  return case


@contextmanager
def stock_family(family):
  with ExitStack() as cleanup:
    if family == 'toyota':
      yield callers(cleanup, 'toyota', True)
      return
    cleanup.enter_context(OpenpilotPrefix())
    case = honda_family_case('honda', False) if family == 'honda' else hkg_family_case(family, False)
    cleanup.callback(case.doCleanups)
    yield case.family_callers(False)
