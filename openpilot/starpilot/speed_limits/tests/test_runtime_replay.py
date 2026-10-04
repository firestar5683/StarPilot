"""Native parser packets through typed SLC state and the opt-in planner ceiling."""

import math
import json
import tempfile
import time
import unittest
from collections import deque
from contextlib import ExitStack
from types import SimpleNamespace
from typing import cast
from unittest import mock

from opendbc.can import CANPacker, CANParser
from opendbc.car.dashboard_speed_limit import Tracker, Status, ford_sign, honda_sign, hyundai_canfd_sign, parser_expiry, toyota_sign
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from opendbc.car.hyundai.carstate import CarState as HyundaiCarState
from opendbc.car.hyundai.interface import CarInterface as HyundaiCarInterface
from opendbc.car.hyundai.values import CAR as HyundaiCAR, HyundaiFlags
from opendbc.car import Bus
from opendbc.car.honda.carstate import CarState as HondaCarState
from opendbc.car.toyota.carstate import CarState as ToyotaCarState
from opendbc.car.toyota.interface import CarInterface as ToyotaCarInterface
from opendbc.car.toyota.values import CAR as ToyotaCAR
from opendbc.car.ford.carstate import CarState as FordCarState
from opendbc.car.ford.interface import CarInterface as FordCarInterface
from opendbc.car.ford.values import CAR as FordCAR
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import messages
from openpilot.starpilot.speed_limits.runtime import Action, CruiseEvent, Runtime
from openpilot.starpilot.speed_limits.runtime_settings import parse
from openpilot.starpilot.speed_limits.runtime_settings import read_params
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.speed_limits.selection import Source
from openpilot.starpilot.speed_limits.acceptance import ObservationKind
from openpilot.starpilot.speed_limits import acceptance as acc, history
from openpilot.starpilot.speed_limits import physical_actions
from openpilot.selfdrive.car.cruise import VCruiseHelper, SlcPendingConfirmation
from opendbc.car.structs import car


class ReplaySM:
  def __init__(self, data, timestamp):
    self.data = data
    self.valid = dict.fromkeys(data, True)
    self.updated = dict.fromkeys(data, True)
    self.alive = dict.fromkeys(data, True)
    self.logMonoTime = dict.fromkeys(data, timestamp)

  def __getitem__(self, name):
    return self.data[name]

  def advance(self, timestamp):
    self.logMonoTime = dict.fromkeys(self.data, timestamp)
    self.data['slcDashboardObservation'].carStateLogMonoTime = timestamp

  def update(self, timeout: int = 100) -> None:
    pass


class NativeSourceTests(unittest.TestCase):
  def test_brand_carstate_trackers_receive_real_packets(self):
    cases = (
      (CarInterface, CAR.HONDA_CIVIC_BOSCH, HondaCarState, 'CAMERA_MESSAGES',
       {'SPEED_LIMIT_SIGN': 104}, {'SPEED_LIMIT_SIGN': 1}, 17.8816),
      (ToyotaCarInterface, ToyotaCAR.TOYOTA_RAV4, ToyotaCarState, 'RSA1',
       {'TSGN1': 36, 'SPDVAL1': 45}, {'TSGN1': 35, 'SPDVAL1': 45}, 20.1168),
      (FordCarInterface, FordCAR.FORD_ESCAPE_MK4, FordCarState, 'Traffic_RecognitnData',
       {'TsrVLim1MsgTxt_D_Rq': 45, 'TsrVlUnitMsgTxt_D_Rq': 2},
       {'TsrVLim1MsgTxt_D_Rq': 45, 'TsrVlUnitMsgTxt_D_Rq': 0}, 20.1168),
      (HyundaiCarInterface, HyundaiCAR.HYUNDAI_IONIQ_6, HyundaiCarState, 'FR_CMR_02_100ms',
       {'ISLW_SysSta': 0, 'ISLW_SpdCluMainDis': 72},
       {'ISLW_SysSta': 1, 'ISLW_SpdCluMainDis': 72}, 20.0),
    )
    for interface, fingerprint, state_type, message, signals, unsupported, expected in cases:
      with self.subTest(fingerprint=fingerprint):
        cp = interface.get_non_essential_params(fingerprint)
        state = state_type(cp)
        parsers = state.get_can_parsers(cp)
        subscribed = [(bus, parser) for bus, parser in parsers.items()
                      if (definition := parser.dbc.name_to_msg.get(message)) is not None and
                      definition.address in parser.message_states]
        self.assertEqual(len(subscribed), 1)
        _, parser = subscribed[0]
        packer = CANPacker(parser.dbc.name)
        for i in range(6):
          timestamp = 1_000_000_000 + i * 300_000_000
          parser.update([timestamp, [packer.make_can_msg(message, parser.bus, {key: float(value) for key, value in signals.items()})]])
        state.update(parsers)
        observation = state.dashboard_limit.observation
        self.assertEqual(observation.status, Status.VALID)
        self.assertAlmostEqual(observation.speed_mps, expected)
        self.assertEqual(observation.observed_ns, timestamp)
        self.assertGreater(observation.valid_until_ns, timestamp)
        parser.update([timestamp + 300_000_000, [packer.make_can_msg(message, parser.bus, {key: float(value) for key, value in unsupported.items()})]])
        state.update(parsers)
        self.assertEqual(state.dashboard_limit.observation.status, Status.UNKNOWN)
        self.assertEqual(state.dashboard_limit.observation.speed_mps, 0.0)

  def test_real_dbc_packets_and_parser_expiry(self):
    cases = (
      ('honda_civic_hatchback_ex_2017_can_generated', 'CAMERA_MESSAGES',
       {'SPEED_LIMIT_SIGN': 104}, 'SPEED_LIMIT_SIGN', lambda: honda_sign(104), 17.8816),
      ('toyota_nodsu_pt_generated', 'RSA1', {'TSGN1': 36, 'SPDVAL1': 45},
       'TSGN1', lambda: toyota_sign(36, 45), 20.1168),
      ('ford_lincoln_base_pt', 'Traffic_RecognitnData',
       {'TsrVLim1MsgTxt_D_Rq': 45, 'TsrVlUnitMsgTxt_D_Rq': 2},
       'TsrVLim1MsgTxt_D_Rq', lambda: ford_sign(45, 2), 20.1168),
      ('hyundai_canfd_generated', 'FR_CMR_02_100ms',
       {'ISLW_SysSta': 0, 'ISLW_SpdCluMainDis': 72},
       'ISLW_SpdCluMainDis', lambda: hyundai_canfd_sign(72, 0, True), 20.0),
    )
    for dbc, message, signals, signal, decode, expected_mps in cases:
      with self.subTest(message=message):
        packer = CANPacker(dbc)
        parser = CANParser(dbc, [(message, math.nan)], 0)
        self.assertEqual(parser_expiry(parser, message, signal), (0, 0))
        for i in range(6):
          timestamp = 1_000_000_000 + i * 300_000_000
          parser.update([timestamp, [packer.make_can_msg(message, 0, {key: float(value) for key, value in signals.items()})]])
        observed, expiry = parser_expiry(parser, message, signal)
        self.assertEqual(observed, timestamp)
        self.assertGreater(expiry, observed)
        self.assertEqual(parser.vl[message][signal], signals[signal])
        kind, value = decode()
        self.assertIs(kind, Status.VALID)
        self.assertAlmostEqual(value, expected_mps)

  def test_invalid_sign_does_not_preserve_previous_limit_and_reconnects(self):
    tracker = Tracker()
    first = tracker.update(100, *honda_sign(104), valid_until_ns=200)
    self.assertEqual(first.status, Status.VALID)
    unknown = tracker.update(150, *honda_sign(1), valid_until_ns=250)
    self.assertEqual(unknown.status, Status.UNKNOWN)
    self.assertEqual(unknown.speed_mps, 0)
    again = tracker.update(300, *honda_sign(104), valid_until_ns=400)
    self.assertEqual(again.status, Status.VALID)
    self.assertGreater(again.episode, first.episode)
    self.assertEqual(tracker.update(350, Status.VALID, math.inf, valid_until_ns=450), again)
    self.assertEqual(hyundai_canfd_sign(0, 0, True), (Status.ABSENT, 0.0))
    self.assertEqual(hyundai_canfd_sign(253, 0, True), (Status.ABSENT, 0.0))
    self.assertEqual(hyundai_canfd_sign(72, 1, True), (Status.UNKNOWN, 0.0))

  def test_hyundai_optional_sign_subscription_follows_source_bus(self):
    cp = HyundaiCarInterface.get_non_essential_params(HyundaiCAR.HYUNDAI_IONIQ_6)
    for hda2, expected_bus in ((False, Bus.cam), (True, Bus.pt)):
      with self.subTest(hda2=hda2):
        if hda2:
          cp.flags = int(cp.flags | HyundaiFlags.CANFD_LKA_STEER_MSG)
        parsers = HyundaiCarState(cp).get_can_parsers(cp)
        for bus, parser in parsers.items():
          message = parser.dbc.name_to_msg['FR_CMR_02_100ms']
          subscribed = message.address in parser.message_states
          self.assertEqual(subscribed, bus == expected_bus)
          if subscribed:
            self.assertTrue(parser.message_states[message.address].ignore_alive)


class RuntimeReplayTests(unittest.TestCase):
  def test_isolated_ipc_submaster_handles_independent_card_and_model_cadences(self):
    from openpilot.cereal import messaging
    with OpenpilotPrefix():
      messaging.reset_context()
      pm = messaging.PubMaster(['carState', 'slcDashboardObservation', 'slcState', 'modelV2'])
      sm = messaging.SubMaster(['carState', 'slcDashboardObservation', 'slcState', 'modelV2'], poll='modelV2')
      base_ns = time.monotonic_ns() - 50_000_000

      def publish(service, stamp_ns):
        message = messaging.new_message(service)
        message.valid = True
        message.logMonoTime = stamp_ns
        pm.send(service, message)
        return message

      car = messaging.new_message('carState')
      car.valid = True
      car.logMonoTime = base_ns + 10_000_000
      pm.send('carState', car)
      source = messaging.new_message('slcDashboardObservation')
      source.valid = True
      source.logMonoTime = base_ns
      source.slcDashboardObservation.producerSessionId = 'ipc-card'
      source.slcDashboardObservation.carStateLogMonoTime = base_ns
      source.slcDashboardObservation.status = 'valid'
      source.slcDashboardObservation.speedMps = 25.0
      source.slcDashboardObservation.observedMonoTime = base_ns - 20_000_000
      source.slcDashboardObservation.validUntilMonoTime = base_ns + 1_000_000_000
      source.slcDashboardObservation.episode = 1
      pm.send('slcDashboardObservation', source)
      state = messaging.new_message('slcState')
      state.valid = True
      state.logMonoTime = base_ns + 5_000_000
      state.slcState.sessionId = 'ipc-drive'
      state.slcState.frameMonoTime = base_ns + 5_000_000
      state.slcState.enabled = True
      state.slcState.observationKind = 'valid'
      state.slcState.source = 'dashboard'
      state.slcState.speedLimit = 25.0
      state.slcState.hasPending = True
      state.slcState.pendingSpeedLimit = 25.0
      state.slcState.decisionId = 1
      state.slcState.presentationId = 1
      state.slcState.sourceProducerSessionId = 'ipc-card'
      state.slcState.sourceEpisode = 1
      state.slcState.sourceObservedMonoTime = base_ns - 20_000_000
      state.slcState.sourceValidUntilMonoTime = base_ns + 1_000_000_000
      pm.send('slcState', state)
      publish('modelV2', base_ns + 5_000_000)
      sm.update(100)
      now_ns = time.monotonic_ns()
      self.assertGreater(sm.logMonoTime['carState'], sm.logMonoTime['modelV2'])
      self.assertEqual(sm.logMonoTime['carState'] - sm.logMonoTime['slcDashboardObservation'], 10_000_000)
      self.assertTrue(physical_actions.pending_confirmation(
        sm, SimpleNamespace(status='valid', speed_mps=25.0, observed_ns=base_ns - 20_000_000,
                            valid_until_ns=base_ns + 1_000_000_000, episode=1), 'ipc-card', now_ns,
        long_active=True, pcm_cruise=False))
      runtime = Runtime(parse({'SpeedLimitController': True}), session_id='ipc-drive')
      self.assertEqual(runtime._observations(sm, self.cp, now_ns)[Source.DASHBOARD].kind, ObservationKind.VALID)

      newer = messaging.new_message('carState')
      newer.valid = True
      newer.logMonoTime = base_ns + 35_000_000
      pm.send('carState', newer)
      publish('modelV2', base_ns + 40_000_000)
      sm.update(100)
      self.assertNotEqual(runtime._observations(sm, self.cp, time.monotonic_ns())[Source.DASHBOARD].kind,
                          ObservationKind.VALID)

      # Card runs at 100 Hz while the planner state runs at 20 Hz. A new TSR
      # packet can briefly outrun the planner, but the old episode never qualifies.
      local = SimpleNamespace(status=Status.VALID, speed_mps=25.0, observed_ns=base_ns - 20_000_000,
                              valid_until_ns=base_ns + 1_000_000_000, episode=1)
      qualified = 0
      mismatched_ticks = 0
      for tick in range(20):
        if tick in (7, 17):
          local.observed_ns = time.monotonic_ns()
          local.episode += 1
        if tick % 5 == 0:
          stamp = time.monotonic_ns()
          cadence_state = messaging.new_message('slcState')
          cadence_state.valid = True
          cadence_state.logMonoTime = stamp
          snapshot = cadence_state.slcState
          snapshot.frameMonoTime = stamp
          snapshot.sessionId = 'ipc-drive'
          snapshot.enabled = True
          snapshot.observationKind = 'valid'
          snapshot.source = 'dashboard'
          snapshot.speedLimit = 25.0
          snapshot.hasPending = True
          snapshot.pendingSpeedLimit = 25.0
          snapshot.decisionId = 1
          snapshot.presentationId = 1
          snapshot.sourceProducerSessionId = 'ipc-card'
          snapshot.sourceEpisode = local.episode
          snapshot.sourceObservedMonoTime = local.observed_ns
          snapshot.sourceValidUntilMonoTime = local.valid_until_ns
          pm.send('slcState', cadence_state)
        sm.update(0)
        pending = physical_actions.pending_confirmation(sm, local, 'ipc-card', time.monotonic_ns(),
                                                        long_active=True, pcm_cruise=False)
        qualified += pending is not None
        mismatched_ticks += pending is None and tick in (7, 8, 9, 17, 18, 19)
        time.sleep(0.01)
      self.assertGreaterEqual(qualified, 12)
      self.assertEqual(mismatched_ticks, 6)

  def test_card_consumes_physical_press_through_release_without_replay(self):
    helper = VCruiseHelper(car.CarParams(pcmCruise=False))
    helper.v_cruise_kph = 70.0
    pending = SlcPendingConfirmation('drive', 1, 1)
    press = car.CarState(cruiseState={'available': True}, buttonEvents=[car.CarState.ButtonEvent(type='accelCruise', pressed=True)])
    held = car.CarState(cruiseState={'available': True})
    release = car.CarState(cruiseState={'available': True}, buttonEvents=[car.CarState.ButtonEvent(type='accelCruise', pressed=False)])
    helper.update_v_cruise(press, True, False, pending)
    self.assertEqual(helper.slc_consumed_button.pending, pending)
    self.assertEqual(helper.v_cruise_kph, 70.0)
    for _ in range(55):
      helper.update_v_cruise(held, True, False)
      self.assertEqual(helper.v_cruise_kph, 70.0)
      self.assertIsNone(helper.slc_consumed_button)
    helper.update_v_cruise(release, True, False)
    self.assertEqual(helper.v_cruise_kph, 70.0)
    self.assertFalse(helper.slc_suppressed_buttons)
    helper.update_v_cruise(press, True, False)
    helper.update_v_cruise(release, True, False)
    self.assertGreater(helper.v_cruise_kph, 70.0)

    helper.v_cruise_kph = 70.0
    helper.update_v_cruise(press, True, False, pending)
    helper.update_v_cruise(held, False, False)
    for _ in range(55):
      helper.update_v_cruise(held, True, False)
      self.assertEqual(helper.v_cruise_kph, 70.0)
    helper.update_v_cruise(release, True, False)
    self.assertEqual(helper.v_cruise_kph, 70.0)
    self.assertFalse(helper.slc_suppressed_buttons)

  def test_physical_accept_creates_bounded_card_command_and_receipt(self):
    settings = parse({'SpeedLimitController': True, 'SLCConfirmation': True,
                      'SLCConfirmationHigher': True, 'SLCPriority1': 'Dashboard'})
    runtime = Runtime(settings, session_id='physical-drive')
    self.sm['carState'].vCruise = 60.0
    self.sm['carState'].vCruiseCluster = 60.0
    first = runtime.step(self.sm, self.cp, now_ns=2_000_000_000)
    self.assertTrue(first.message.slcState.hasPending)
    self.sm.advance(2_010_000_000)
    initial = runtime.step(self.sm, self.cp, now_ns=2_010_000_000,
                           request=Action(runtime.session_id, 1, first.message.slcState.decisionId,
                                          first.message.slcState.presentationId, 'accept'))
    self.assertTrue(initial.message.slcState.hasAccepted)
    source = self.sm['slcDashboardObservation']
    source.speedMps = 30.0
    source.observedMonoTime = 2_040_000_000
    source.episode = 2
    self.sm.advance(2_050_000_000)
    state = runtime.step(self.sm, self.cp, now_ns=2_050_000_000).message.slcState
    self.assertTrue(state.hasPending)
    self.assertEqual(state.sourceProducerSessionId, 'card-producer')
    self.sm.advance(2_100_000_000)
    accepted = runtime.step(self.sm, self.cp, now_ns=2_100_000_000,
                            cruise_event=CruiseEvent(1, 2_100_000_000, 0.0, 0.0, 'accel', 'card-producer',
                                                     2_100_000_000, 'confirmationAccept', runtime.session_id,
                                                     state.decisionId, state.presentationId))
    self.assertEqual(accepted.action_result.status, 'resolved')
    self.assertTrue(accepted.message.slcState.hasAccepted)
    self.assertFalse(accepted.message.slcState.hasPending)
    self.assertEqual(accepted.message.slcState.actionStatus, 'accept')
    self.assertEqual(runtime.ledger.transactions, ())
    self.assertIsNotNone(accepted.command)
    command = accepted.command.slcCruiseCommand
    self.assertLessEqual(command.expiresMonoTime - command.issuedMonoTime, physical_actions.COMMAND_MAX_AGE_NS)
    card_sm = ReplaySM({'slcState': accepted.message.slcState}, 2_100_000_000)
    observation = SimpleNamespace(status=Status.VALID, speed_mps=30.0, observed_ns=2_040_000_000,
                                  valid_until_ns=9_000_000_000, episode=2)
    current = physical_actions.state_current(card_sm, observation, 'card-producer', 2_100_000_000)
    self.assertIsNotNone(current)
    self.assertTrue(physical_actions.command_applicable(command, current, observation, 'card-producer',
                                                        2_100_000_000, 60.0 / 3.6,
                                                        long_active=True, pcm_cruise=False, button_event=False))
    self.assertFalse(physical_actions.command_applicable(command, current, observation, 'card-producer',
                                                         2_100_000_000, 65.0 / 3.6,
                                                         long_active=True, pcm_cruise=False, button_event=False))
    self.assertFalse(physical_actions.command_applicable(command, current, observation, 'card-producer',
                                                         2_100_000_000, 60.0 / 3.6,
                                                         long_active=True, pcm_cruise=False, button_event=True))
    self.assertFalse(physical_actions.command_applicable(command, current, observation, 'card-producer',
                                                         2_100_000_000, 60.0 / 3.6,
                                                         long_active=True, pcm_cruise=True, button_event=False))
    command.commandId += 1
    self.assertFalse(physical_actions.command_applicable(command, current, observation, 'card-producer',
                                                         2_100_000_000, 60.0 / 3.6,
                                                         long_active=True, pcm_cruise=False, button_event=False))
    command.commandId -= 1
    command.presentationId += 1
    self.assertFalse(physical_actions.command_applicable(command, current, observation, 'card-producer',
                                                         2_100_000_000, 60.0 / 3.6,
                                                         long_active=True, pcm_cruise=False, button_event=False))
    command.presentationId -= 1
    command.sourceEpisode = 99
    self.assertFalse(physical_actions.command_applicable(command, current, observation, 'card-producer',
                                                         2_100_000_000, 60.0 / 3.6,
                                                         long_active=True, pcm_cruise=False, button_event=False))
    command.sourceEpisode = 2
    command.expiresMonoTime = 2_099_000_000
    self.assertFalse(physical_actions.command_applicable(command, current, observation, 'card-producer',
                                                         2_100_000_000, 60.0 / 3.6,
                                                         long_active=True, pcm_cruise=False, button_event=False))
    command.expiresMonoTime = 2_200_000_000
    command.targetMps = math.nan
    self.assertFalse(physical_actions.command_applicable(command, current, observation, 'card-producer',
                                                         2_100_000_000, 60.0 / 3.6,
                                                         long_active=True, pcm_cruise=False, button_event=False))
    command.targetMps = 30.0
    self.assertIsNone(physical_actions.state_current(card_sm, observation, 'card-producer', 2_210_000_000))
    # The latest conflated CarState can already contain a newer driver choice
    # when the historical card-owned application receipt reaches plannerd.
    self.sm.advance(2_160_000_000)
    self.sm['carState'].vCruise = 115.0
    self.sm['carState'].vCruiseCluster = 115.0
    def receipt(event_id, observed_ns, previous_mps, selected_mps):
      return CruiseEvent(event_id, observed_ns, previous_mps, selected_mps, 'unknown', 'card-producer',
                         2_150_000_000, 'commandApplied', runtime.session_id, state.decisionId,
                         state.presentationId, command.commandId)
    wrong_time = runtime.step(self.sm, self.cp, now_ns=2_160_000_000,
                              cruise_event=receipt(2, 2_090_000_000, 60.0 / 3.6, 30.0))
    self.assertEqual(wrong_time.message.slcState.commandStatus, 'issued')
    wrong_previous = runtime.step(self.sm, self.cp, now_ns=2_160_000_000,
                                  cruise_event=receipt(3, 2_150_000_000, 20.0, 30.0))
    self.assertEqual(wrong_previous.message.slcState.commandStatus, 'issued')
    wrong_target = runtime.step(self.sm, self.cp, now_ns=2_160_000_000,
                                cruise_event=receipt(4, 2_150_000_000, 60.0 / 3.6, 20.0))
    self.assertEqual(wrong_target.message.slcState.commandStatus, 'issued')
    applied = runtime.step(self.sm, self.cp, now_ns=2_160_000_000,
                           cruise_event=receipt(5, 2_150_000_000, 60.0 / 3.6, 30.0))
    self.assertEqual(applied.message.slcState.commandStatus, 'applied')
    self.sm.advance(2_170_000_000)
    newer_driver = runtime.step(self.sm, self.cp, now_ns=2_170_000_000,
                                cruise_event=CruiseEvent(6, 2_160_000_000, 30.0, 115.0 / 3.6, 'accel',
                                                         'card-producer', 2_160_000_000))
    self.assertEqual(newer_driver.message.slcState.commandStatus, 'applied')

  def test_first_action_zero_can_issue_and_apply_command(self):
    settings = parse({'SpeedLimitController': True, 'SLCConfirmation': True, 'SLCConfirmationHigher': True})
    runtime = Runtime(settings, session_id='first-action')
    self.sm['carState'].vCruise = 60.0
    self.sm['carState'].vCruiseCluster = 60.0
    pending = runtime.step(self.sm, self.cp, now_ns=2_000_000_000).message.slcState
    self.assertTrue(pending.hasPending)
    self.sm.advance(2_050_000_000)
    accepted = runtime.step(self.sm, self.cp, now_ns=2_050_000_000,
                            cruise_event=CruiseEvent(1, 2_050_000_000, 0.0, 0.0, 'accel', 'card-producer',
                                                     2_050_000_000, 'confirmationAccept', runtime.session_id,
                                                     pending.decisionId, pending.presentationId))
    self.assertIsNotNone(accepted.command)
    self.assertEqual(accepted.command.slcCruiseCommand.actionId, 0)
    self.assertEqual(accepted.message.slcState.commandId, accepted.command.slcCruiseCommand.commandId)
    card_sm = ReplaySM({'slcState': accepted.message.slcState}, 2_050_000_000)
    observation = SimpleNamespace(status=Status.VALID, speed_mps=25.0, observed_ns=1_900_000_000,
                                  valid_until_ns=9_000_000_000, episode=1)
    self.assertTrue(physical_actions.command_applicable(
      accepted.command.slcCruiseCommand, card_sm['slcState'], observation, 'card-producer',
      2_050_000_000, 60.0 / 3.6, long_active=True, pcm_cruise=False, button_event=False))

  def test_late_bounded_card_receipt_supersedes_clock_expiry(self):
    settings = parse({'SpeedLimitController': True, 'SLCConfirmation': True, 'SLCConfirmationHigher': True})
    runtime = Runtime(settings, session_id='late-receipt')
    self.sm['carState'].vCruise = 60.0
    self.sm['carState'].vCruiseCluster = 60.0
    pending = runtime.step(self.sm, self.cp, now_ns=2_000_000_000).message.slcState
    self.sm.advance(2_010_000_000)
    accepted = runtime.step(self.sm, self.cp, now_ns=2_010_000_000,
                            cruise_event=CruiseEvent(1, 2_010_000_000, 0.0, 0.0, 'accel', 'card-producer',
                                                     2_010_000_000, 'confirmationAccept', runtime.session_id,
                                                     pending.decisionId, pending.presentationId))
    self.assertIsNotNone(accepted.command)
    command = accepted.command.slcCruiseCommand
    after_expiry = int(command.expiresMonoTime) + 10_000_000
    actual_application = int(command.expiresMonoTime) - 10_000_000
    self.sm.advance(after_expiry)
    result = runtime.step(self.sm, self.cp, now_ns=after_expiry,
                          cruise_event=CruiseEvent(2, actual_application, 60.0 / 3.6, 25.0, 'unknown',
                                                   'card-producer', actual_application, 'commandApplied',
                                                   runtime.session_id, pending.decisionId, pending.presentationId,
                                                   command.commandId))
    self.assertEqual(result.message.slcState.commandStatus, 'applied')

  def test_physical_decel_rejects_without_selected_speed_command(self):
    settings = parse({'SpeedLimitController': True, 'SLCConfirmation': True, 'SLCConfirmationLower': True})
    runtime = Runtime(settings, session_id='physical-reject')
    first = runtime.step(self.sm, self.cp, now_ns=2_000_000_000)
    self.assertTrue(first.message.slcState.hasAccepted)
    source = self.sm['slcDashboardObservation']
    source.speedMps = 15.0
    source.observedMonoTime = 2_040_000_000
    source.episode = 2
    self.sm.advance(2_050_000_000)
    pending = runtime.step(self.sm, self.cp, now_ns=2_050_000_000).message.slcState
    self.assertTrue(pending.hasPending)
    self.sm.advance(2_100_000_000)
    rejected = runtime.step(self.sm, self.cp, now_ns=2_100_000_000,
                            cruise_event=CruiseEvent(1, 2_100_000_000, 0.0, 0.0, 'decel', 'card-producer',
                                                     2_100_000_000, 'confirmationReject', runtime.session_id,
                                                     pending.decisionId, pending.presentationId))
    self.assertEqual(rejected.message.slcState.actionStatus, 'reject')
    self.assertFalse(rejected.message.slcState.hasPending)
    self.assertIsNone(rejected.command)
    self.assertEqual(runtime.ledger.transactions, ())

  def test_identified_ui_adopt_uses_same_card_owned_command_path(self):
    runtime = Runtime(parse({'SpeedLimitController': True}), session_id='ui-adopt-drive')
    self.sm['carState'].vCruise = 60.0
    self.sm['carState'].vCruiseCluster = 60.0
    shown = runtime.step(self.sm, self.cp, now_ns=2_000_000_000).message.slcState
    self.assertTrue(shown.hasAccepted)
    self.sm.advance(2_050_000_000)
    adopted = runtime.step(self.sm, self.cp, now_ns=2_050_000_000,
                           request=Action(runtime.session_id, 1, 0, shown.presentationId, 'adopt'))
    self.assertEqual(adopted.message.slcState.actionStatus, 'adopt')
    self.assertIsNotNone(adopted.command)
    self.assertEqual(adopted.command.slcCruiseCommand.presentationId, shown.presentationId)
    self.assertEqual(adopted.command.slcCruiseCommand.actionId, 0)
    self.assertEqual(adopted.command.slcCruiseCommand.decisionId, 0)
    card_sm = ReplaySM({'slcState': adopted.message.slcState}, 2_050_000_000)
    observation = SimpleNamespace(status=Status.VALID, speed_mps=25.0, observed_ns=1_900_000_000,
                                  valid_until_ns=9_000_000_000, episode=1)
    self.assertTrue(physical_actions.command_applicable(
      adopted.command.slcCruiseCommand, card_sm['slcState'], observation, 'card-producer',
      2_050_000_000, 60.0 / 3.6, long_active=True, pcm_cruise=False, button_event=False))

  def test_native_card_applies_one_shot_command_only_with_current_state(self):
    from openpilot.cereal import messaging
    from openpilot.selfdrive.car import card
    now_ns = time.monotonic_ns()
    observation = SimpleNamespace(status=Status.VALID, speed_mps=30.0, observed_ns=now_ns - 20_000_000,
                                  valid_until_ns=now_ns + 1_000_000_000, episode=4)
    state = messaging.new_message('slcState')
    state.valid = True
    state.logMonoTime = now_ns - 10_000_000
    state.slcState.frameMonoTime = state.logMonoTime
    state.slcState.sessionId = 'card-drive'
    state.slcState.enabled = True
    state.slcState.source = 'dashboard'
    state.slcState.observationKind = 'valid'
    state.slcState.speedLimit = 30.0
    state.slcState.hasAccepted = True
    state.slcState.acceptedSpeedLimit = 30.0
    state.slcState.commandId = 1
    state.slcState.presentationId = 1
    state.slcState.sourceProducerSessionId = 'card-producer'
    state.slcState.sourceEpisode = 4
    state.slcState.sourceObservedMonoTime = observation.observed_ns
    state.slcState.sourceValidUntilMonoTime = observation.valid_until_ns
    command = messaging.new_message('slcCruiseCommand')
    command.valid = True
    command.slcCruiseCommand.kind = 'adoptAcceptedHigherLimit'
    command.slcCruiseCommand.sessionId = 'card-drive'
    command.slcCruiseCommand.commandId = 1
    command.slcCruiseCommand.actionId = 1
    command.slcCruiseCommand.presentationId = 1
    command.slcCruiseCommand.sourceProducerSessionId = 'card-producer'
    command.slcCruiseCommand.sourceEpisode = 4
    command.slcCruiseCommand.sourceObservedMonoTime = observation.observed_ns
    command.slcCruiseCommand.sourceValidUntilMonoTime = observation.valid_until_ns
    command.slcCruiseCommand.issuedMonoTime = now_ns - 10_000_000
    command.slcCruiseCommand.expiresMonoTime = now_ns + 80_000_000
    command.slcCruiseCommand.expectedSelectedMps = 60.0 / 3.6
    command.slcCruiseCommand.targetMps = 30.0
    fake = card.Car.__new__(card.Car)
    fake.conditional_replay = False
    fake.switchback_button_tracker = None
    fake.switchback_settings_owner = None
    from openpilot.starpilot.controllers.wheel_actions import WheelPublisher
    fake.params = Params()
    from openpilot.starpilot.vehicle_startup import VehicleStartupOwner
    fake.vehicle_startup = VehicleStartupOwner()
    fake.wheel_publisher = WheelPublisher(fake.params)
    fake.ioniq6_long_prearmed = False
    fake.slc_replay = True
    fake.aol_card_intent = None
    fake.slc_producer_session = 'card-producer'
    fake.slc_command_sock = object()
    fake.slc_commands = deque(maxlen=8)
    fake.slc_command_session = ''
    fake.slc_last_command_id = 0
    fake.slc_receipts = []
    fake.can_sock = object()
    fake.can_rcv_cum_timeout_counter = 0
    fake.is_metric = False
    fake.CP = car.CarParams(openpilotLongitudinalControl=True, pcmCruise=False)
    fake.CC_prev = car.CarControl(enabled=True)
    fake.v_cruise_helper = VCruiseHelper(fake.CP)
    fake.v_cruise_helper.v_cruise_kph = 60.0
    fake.sm = cast(messaging.SubMaster, ReplaySM(
      {'carControl': car.CarControl(enabled=True, longActive=True), 'slcState': state.slcState,
       'deviceState': SimpleNamespace(startedMonoTime=1)}, now_ns - 10_000_000))
    self.enterContext(mock.patch.object(fake, 'CI', SimpleNamespace(
      CS=SimpleNamespace(dashboard_limit=SimpleNamespace(observation=observation)),
      update=lambda packets: car.CarState(canValid=True, cruiseState={'available': True})), create=True))
    self.enterContext(mock.patch.object(fake, 'RI', SimpleNamespace(update=lambda packets: None), create=True))
    with (mock.patch.object(card.messaging, 'drain_sock_raw', return_value=[]),
          mock.patch.object(card.messaging, 'recv_one_or_none', side_effect=[command.as_reader(), None, command.as_reader(), None])):
      selected, _ = fake.state_update()
      self.assertGreater(selected.vCruise, 60.0)
      self.assertEqual(fake.slc_receipts[0][0], 'commandApplied')
      first_selected = selected.vCruise
      selected_again, _ = fake.state_update()
      self.assertEqual(selected_again.vCruise, first_selected)
      self.assertEqual(fake.slc_receipts, [])
    fake.CC_prev.enabled = False
    fake.CS_prev = car.CarState(vEgo=20.0)
    fake.experimental_mode = False
    fake.slc_last_command_id = 0
    fake.slc_command_session = ''
    fake.v_cruise_helper.v_cruise_kph = 60.0
    with (mock.patch.object(card.messaging, 'drain_sock_raw', return_value=[]),
          mock.patch.object(card.messaging, 'recv_one_or_none', side_effect=[command.as_reader(), None])):
      edge, _ = fake.state_update()
    self.assertNotEqual(edge.vCruise, first_selected)
    self.assertEqual(fake.slc_receipts[0][0], 'commandRejected')

    # The command socket can beat the conflated slcState socket by one card tick.
    fake.CC_prev.enabled = True
    fake.slc_last_command_id = 0
    fake.slc_command_session = 'card-drive'
    fake.v_cruise_helper.v_cruise_kph = 60.0
    fake.slc_commands.clear()
    stale_snapshot = messaging.new_message('slcState')
    stale_snapshot.slcState = state.slcState
    stale_snapshot.slcState.commandId = 0
    fake.sm.data['slcState'] = stale_snapshot.slcState
    fake.sm.logMonoTime['slcState'] = command.slcCruiseCommand.issuedMonoTime - 1
    with (mock.patch.object(card.messaging, 'drain_sock_raw', return_value=[]),
          mock.patch.object(card.messaging, 'recv_one_or_none', side_effect=[command.as_reader(), None])):
      waiting, _ = fake.state_update()
    self.assertEqual(waiting.vCruise, 60.0)
    self.assertEqual(fake.slc_receipts, [])
    self.assertEqual(len(fake.slc_commands), 1)
    fake.sm.data['slcState'] = state.slcState
    fake.sm.logMonoTime['slcState'] = state.logMonoTime
    with (mock.patch.object(card.messaging, 'drain_sock_raw', return_value=[]),
          mock.patch.object(card.messaging, 'recv_one_or_none', return_value=None)):
      caught_up, _ = fake.state_update()
    self.assertGreater(caught_up.vCruise, 60.0)
    self.assertEqual(fake.slc_receipts[0][0], 'commandApplied')

  def test_card_runtime_consumed_press_hold_command_release(self):
    from openpilot.selfdrive.car import card
    now_ns = time.monotonic_ns()
    source = self.sm['slcDashboardObservation']
    source.producerSessionId = 'card-producer'
    source.observedMonoTime = now_ns - 20_000_000
    source.validUntilMonoTime = now_ns + 1_000_000_000
    source.carStateLogMonoTime = now_ns
    self.sm.advance(now_ns)
    self.sm['carState'].vCruise = 60.0
    self.sm['carState'].vCruiseCluster = 60.0
    runtime = Runtime(parse({'SpeedLimitController': True, 'SLCConfirmation': True,
                             'SLCConfirmationHigher': True}), session_id='held-press-drive')
    pending = runtime.step(self.sm, self.cp, now_ns=now_ns).message.slcState
    self.assertTrue(pending.hasPending)
    observation = SimpleNamespace(status=Status.VALID, speed_mps=25.0, observed_ns=source.observedMonoTime,
                                  valid_until_ns=source.validUntilMonoTime, episode=1)
    fake = card.Car.__new__(card.Car)
    fake.conditional_replay = False
    fake.switchback_button_tracker = None
    fake.switchback_settings_owner = None
    from openpilot.starpilot.controllers.wheel_actions import WheelPublisher
    fake.params = Params()
    from openpilot.starpilot.vehicle_startup import VehicleStartupOwner
    fake.vehicle_startup = VehicleStartupOwner()
    fake.wheel_publisher = WheelPublisher(fake.params)
    fake.ioniq6_long_prearmed = False
    fake.slc_replay = True
    fake.aol_card_intent = None
    fake.slc_producer_session = 'card-producer'
    fake.slc_command_sock = object()
    fake.slc_commands = deque(maxlen=8)
    fake.slc_command_session = ''
    fake.slc_last_command_id = 0
    fake.slc_receipts = []
    fake.can_sock = object()
    fake.can_rcv_cum_timeout_counter = 0
    fake.is_metric = False
    fake.CP = car.CarParams(openpilotLongitudinalControl=True, pcmCruise=False)
    fake.CC_prev = car.CarControl(enabled=True)
    fake.v_cruise_helper = VCruiseHelper(fake.CP)
    fake.v_cruise_helper.v_cruise_kph = 60.0
    fake.sm = cast(card.messaging.SubMaster, ReplaySM(
      {'carControl': car.CarControl(enabled=True, longActive=True), 'slcState': pending, 'deviceState': SimpleNamespace(startedMonoTime=1)}, now_ns))
    current_cs = [car.CarState(canValid=True, cruiseState={'available': True},
                               buttonEvents=[car.CarState.ButtonEvent(type='accelCruise', pressed=True)])]
    self.enterContext(mock.patch.object(fake, 'CI', SimpleNamespace(
      CS=SimpleNamespace(dashboard_limit=SimpleNamespace(observation=observation)),
      update=lambda packets: current_cs[0]), create=True))
    self.enterContext(mock.patch.object(fake, 'RI', SimpleNamespace(update=lambda packets: None), create=True))
    with (mock.patch.object(card.messaging, 'drain_sock_raw', return_value=[]),
          mock.patch.object(card.messaging, 'recv_one_or_none', return_value=None)):
      pressed, _ = fake.state_update()
    self.assertEqual(pressed.vCruise, 60.0)
    consumed = fake.v_cruise_helper.slc_consumed_button
    self.assertIsNotNone(consumed)
    self.assertEqual(consumed.pending.decision_id, pending.decisionId)

    press_ns = time.monotonic_ns()
    self.sm.advance(press_ns)
    accepted = runtime.step(self.sm, self.cp, now_ns=press_ns,
                            cruise_event=CruiseEvent(1, press_ns, 0.0, 0.0, 'accel', 'card-producer', press_ns,
                                                     'confirmationAccept', runtime.session_id,
                                                     pending.decisionId, pending.presentationId))
    self.assertIsNotNone(accepted.command)
    self.assertEqual(accepted.command.slcCruiseCommand.actionId, 0)
    fake.sm.data['slcState'] = accepted.message.slcState
    fake.sm.logMonoTime['slcState'] = press_ns
    current_cs[0] = car.CarState(canValid=True, cruiseState={'available': True})
    with (mock.patch.object(card.messaging, 'drain_sock_raw', return_value=[]),
          mock.patch.object(card.messaging, 'recv_one_or_none', side_effect=[accepted.command.as_reader(), None])):
      applied, _ = fake.state_update()
    self.assertGreater(applied.vCruise, 60.0)
    self.assertEqual([receipt[0] for receipt in fake.slc_receipts], ['commandApplied'])
    applied_speed = applied.vCruise
    current_cs[0] = car.CarState(canValid=True, cruiseState={'available': True},
                                 buttonEvents=[car.CarState.ButtonEvent(type='accelCruise', pressed=False)])
    with (mock.patch.object(card.messaging, 'drain_sock_raw', return_value=[]),
          mock.patch.object(card.messaging, 'recv_one_or_none', return_value=None)):
      released, _ = fake.state_update()
    self.assertEqual(released.vCruise, applied_speed)
    self.assertFalse(fake.v_cruise_helper.slc_suppressed_buttons)
    self.assertEqual(fake.slc_receipts, [])

    def accept_next_limit(speed_mps, episode):
      stamp = time.monotonic_ns()
      source.speedMps = speed_mps
      source.observedMonoTime = stamp
      source.validUntilMonoTime = stamp + 1_000_000_000
      source.episode = episode
      observation.speed_mps = speed_mps
      observation.observed_ns = stamp
      observation.valid_until_ns = source.validUntilMonoTime
      observation.episode = episode
      self.sm['carState'].vCruise = fake.v_cruise_helper.v_cruise_kph
      self.sm['carState'].vCruiseCluster = fake.v_cruise_helper.v_cruise_kph
      self.sm.advance(stamp)
      next_pending = runtime.step(self.sm, self.cp, now_ns=stamp).message.slcState
      self.assertTrue(next_pending.hasPending)
      fake.sm.data['slcState'] = next_pending
      fake.sm.logMonoTime['slcState'] = stamp
      fake.sm.logMonoTime['carControl'] = stamp
      current_cs[0] = car.CarState(canValid=True, cruiseState={'available': True},
                                   buttonEvents=[car.CarState.ButtonEvent(type='accelCruise', pressed=True)])
      with (mock.patch.object(card.messaging, 'drain_sock_raw', return_value=[]),
            mock.patch.object(card.messaging, 'recv_one_or_none', return_value=None)):
        fake.state_update()
      accepted_ns = time.monotonic_ns()
      self.sm.advance(accepted_ns)
      next_accepted = runtime.step(self.sm, self.cp, now_ns=accepted_ns,
                                   cruise_event=CruiseEvent(episode, accepted_ns, 0.0, 0.0, 'accel', 'card-producer',
                                                            accepted_ns, 'confirmationAccept', runtime.session_id,
                                                            next_pending.decisionId, next_pending.presentationId))
      self.assertIsNotNone(next_accepted.command)
      fake.sm.data['slcState'] = next_accepted.message.slcState
      fake.sm.logMonoTime['slcState'] = accepted_ns
      return next_accepted.command

    release_command = accept_next_limit(30.0, 2)
    current_cs[0] = car.CarState(canValid=True, cruiseState={'available': True},
                                 buttonEvents=[car.CarState.ButtonEvent(type='accelCruise', pressed=False)])
    with (mock.patch.object(card.messaging, 'drain_sock_raw', return_value=[]),
          mock.patch.object(card.messaging, 'recv_one_or_none', side_effect=[release_command.as_reader(), None])):
      same_tick_release, _ = fake.state_update()
    self.assertGreater(same_tick_release.vCruise, applied_speed)
    self.assertEqual([receipt[0] for receipt in fake.slc_receipts], ['commandApplied'])
    self.assertFalse(fake.v_cruise_helper.slc_suppressed_buttons)

    unrelated_command = accept_next_limit(35.0, 3)
    before_unrelated = fake.v_cruise_helper.v_cruise_kph
    current_cs[0] = car.CarState(canValid=True, cruiseState={'available': True},
                                 buttonEvents=[car.CarState.ButtonEvent(type='decelCruise', pressed=True)])
    with (mock.patch.object(card.messaging, 'drain_sock_raw', return_value=[]),
          mock.patch.object(card.messaging, 'recv_one_or_none', side_effect=[unrelated_command.as_reader(), None])):
      blocked, _ = fake.state_update()
    self.assertAlmostEqual(blocked.vCruise, before_unrelated, delta=1e-4)
    self.assertEqual([receipt[0] for receipt in fake.slc_receipts], ['commandRejected'])

  def test_malformed_saved_priorities_disable_runtime_without_crashing(self):
    for key in ('SLCPriority1', 'SLCPriority2'):
      for malformed in ([], {}, 1, None):
        with self.subTest(key=key, malformed=malformed):
          settings = parse({'SpeedLimitController': True, key: malformed})
          self.assertFalse(settings.enabled)
          self.assertTrue(settings.errors)

  def test_actual_plannerd_loop_publishes_same_tick_state_and_plan(self):
    from openpilot.selfdrive.controls import plannerd
    from openpilot.cereal import messaging

    class StopReplay(Exception):
      pass

    class Publisher:
      def __init__(self, services):
        self.services = services
        self.sent = []

      def send(self, service, message):
        self.sent.append((service, message))

    self.sm.data['deviceState'] = messaging.new_message('deviceState').deviceState
    self.sm['deviceState'].startedMonoTime = 1_000_000_000
    self.sm.valid['deviceState'] = True
    self.sm.updated['deviceState'] = True
    self.sm.alive['deviceState'] = True
    self.sm.logMonoTime['deviceState'] = 2_000_000_000
    self.sm.frame = 0
    self.sm.all_checks = lambda services=None: True
    calls = 0

    def update(timeout=100):
      nonlocal calls
      calls += 1
      if calls > 1:
        raise StopReplay
      self.sm.logMonoTime['modelV2'] = 2_010_000_000
      self.sm.logMonoTime['carState'] = 2_010_000_000  # latest CarState arrives one card tick ahead of source

    publisher = Publisher([])
    with tempfile.TemporaryDirectory() as directory, ExitStack() as resources:
      params = Params(directory)
      # Drain native asynchronous writes before deleting their temporary directory.
      resources.callback(params._finalizer)
      params.put('CarParams', self.cp.to_bytes(), block=True)
      params.put_bool('SpeedLimitController', True, block=True)
      with (mock.patch.object(self.sm, 'update', side_effect=update),
            mock.patch.object(plannerd, 'Params', return_value=params),
            mock.patch.object(plannerd, 'config_realtime_process'),
            mock.patch.object(plannerd.messaging, 'SubMaster', return_value=self.sm),
            mock.patch.object(plannerd.messaging, 'PubMaster', return_value=publisher),
            mock.patch.object(plannerd.messaging, 'sub_sock', return_value=object()),
            mock.patch.object(plannerd.messaging, 'recv_one_or_none', return_value=None),
            mock.patch.dict('os.environ', {'SLC_REPLAY_RUNTIME': '1', 'REPLAY': '1'})):
        with self.assertRaises(StopReplay):
          plannerd.main()
    services = [service for service, _ in publisher.sent]
    self.assertIn('slcState', services)
    self.assertIn('longitudinalPlan', services)
    state = next(message.slcState for service, message in publisher.sent if service == 'slcState')
    self.assertTrue(state.hasCeiling)
    self.assertEqual(state.observationKind, 'valid')
    self.assertEqual(state.frameMonoTime, 2_010_000_000)

  def test_stored_history_is_schema_bound_and_not_reused_for_new_dashboard_episode(self):
    candidate = acc.Candidate('dashboard', acc.ObservationIdentity(acc.IdentityKind.PRODUCER_EPISODE,
                                                                     value='drive:card:car:1'), 20.0)
    raw = history.encode(acc.AcceptedLimit(candidate, 'drive', 2), 1000)
    self.assertIn('source_schema', json.loads(raw))
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      params.put('SLCQualifiedHistory', json.loads(raw), block=True)
      self.assertEqual(params.get('SLCQualifiedHistory')['source_schema'], json.loads(raw)['source_schema'])
      self.assertIsNone(history.decode(params.get('SLCQualifiedHistory'), session_id='next-drive',
                                       current=acc.Observation(acc.ObservationKind.VALID, candidate),
                                       now_wall_ns=1000, max_age_ns=1_000_000))
    self.assertIsNone(history.decode(raw, session_id='next-drive',
                                     current=acc.Observation(acc.ObservationKind.VALID, candidate),
                                     now_wall_ns=1000, max_age_ns=1_000_000))
    tampered = json.loads(raw)
    tampered['source_schema'] = 'wrong'
    self.assertIsNone(history.decode(json.dumps(tampered), session_id='next-drive',
                                     current=acc.Observation(acc.ObservationKind.VALID, candidate),
                                     now_wall_ns=1000, max_age_ns=1_000_000))

  def test_native_saved_settings_default_off_and_preserve_choices(self):
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      fresh = read_params(params)
      self.assertFalse(fresh.enabled)
      params.put_bool('SpeedLimitController', True, block=True)
      params.put_bool('SLCConfirmation', True, block=True)
      params.put_bool('SLCConfirmationLower', True, block=True)
      params.put('SLCFallback', 2, block=True)
      params.put('SLCPriority1', 'Map Data', block=True)
      params.put('SLCPriority2', 'Dashboard', block=True)
      params.put('Offset3', 5.0, block=True)
      restored = read_params(params)
      self.assertTrue(restored.enabled)
      self.assertTrue(restored.acceptance.confirm_lower)
      self.assertTrue(restored.acceptance.fallback_previous)
      self.assertEqual(restored.selection.slots[0], Source.MAP)
      self.assertEqual(restored.selection.slots[1], Source.DASHBOARD)
      self.assertFalse(restored.errors)

  def setUp(self):
    self.cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    self.assertTrue(self.cp.openpilotLongitudinalControl)
    data, self.envelopes = messages()
    from openpilot.cereal import messaging
    data['slcDashboardObservation'] = messaging.new_message('slcDashboardObservation').slcDashboardObservation
    self.sm = ReplaySM(data, 2_000_000_000)
    self.sm['carState'].vCruiseCluster = 100.0
    self.sm['carState'].vEgoCluster = 20.0
    self.sm['carControl'].enabled = True
    self.sm['carControl'].longActive = True
    self.sm['carControl'].latActive = False
    source = self.sm['slcDashboardObservation']
    source.producerSessionId = 'card-producer'
    source.carStateLogMonoTime = 2_000_000_000
    source.status = 'valid'
    source.speedMps = 25.0
    source.observedMonoTime = 1_900_000_000
    source.validUntilMonoTime = 9_000_000_000
    source.episode = 1

  def test_saved_choice_and_native_planner_replay(self):
    settings = parse({'SpeedLimitController': True, 'SLCFallback': 2, 'SLCPriority1': 'Dashboard'})
    runtime = Runtime(settings, session_id='replay-drive')
    planner = LongitudinalPlanner(self.cp, init_v=20.0)
    first = runtime.step(self.sm, self.cp, now_ns=2_000_000_000)
    self.assertEqual(first.message.slcState.observationKind, 'valid')
    self.assertTrue(first.message.slcState.hasCeiling)
    self.assertLess(first.result.ceiling.speed_mps, 100 / 3.6)
    planner.update(self.sm, cruise_ceiling=first.result.ceiling)
    self.assertEqual(planner.last_cruise_ceiling_status, 'applied')

    self.sm['carState'].vCruise = 105.0
    self.sm['carState'].vCruiseCluster = 105.0
    self.sm.advance(2_050_000_000)
    button = runtime.step(self.sm, self.cp, now_ns=2_050_000_000,
                          cruise_event=CruiseEvent(1, 2_010_000_000, 100 / 3.6, 105 / 3.6, 'accel',
                                                   'replay-card', 2_020_000_000))
    self.assertFalse(button.result.errors)
    self.assertTrue(button.result.override.event_receipt.consumed)
    self.assertEqual(button.result.override.event_receipt.status, 'driver_intent')

    self.sm.advance(9_100_000_000)
    stale = runtime.step(self.sm, self.cp, now_ns=9_100_000_000)
    self.assertEqual(runtime._observations(self.sm, self.cp, 9_100_000_000)[Source.DASHBOARD].kind, ObservationKind.STALE)
    self.assertEqual(stale.message.slcState.observationKind, 'unknown')  # unimplemented map source remains unknown
    self.assertFalse(stale.message.slcState.hasCeiling)
    planner.update(self.sm, cruise_ceiling=stale.result.ceiling)
    self.assertEqual(planner.last_cruise_ceiling_status, 'absent')

  def test_pending_action_receipt_and_stock_gate(self):
    settings = parse({'SpeedLimitController': True, 'SLCConfirmation': True, 'SLCConfirmationLower': True})
    runtime = Runtime(settings, session_id='receipt-drive')
    runtime.step(self.sm, self.cp, now_ns=2_000_000_000)
    source = self.sm['slcDashboardObservation']
    source.speedMps = 15.0
    source.observedMonoTime = 2_040_000_000
    source.validUntilMonoTime = 9_000_000_000
    source.episode = 2
    self.sm.advance(2_050_000_000)
    pending = runtime.step(self.sm, self.cp, now_ns=2_050_000_000)
    self.assertTrue(pending.message.slcState.hasPending)
    self.sm.advance(2_100_000_000)
    request = Action(runtime.session_id, 17, pending.message.slcState.decisionId, 0, 'reject')
    rejected = runtime.step(self.sm, self.cp, now_ns=2_100_000_000, request=request)
    self.assertEqual(rejected.action_result.status, 'resolved')
    self.assertEqual(rejected.message.slcState.actionSequenceId, 17)
    self.assertEqual(rejected.message.slcState.actionStatus, 'reject')

    self.cp.openpilotLongitudinalControl = False
    self.sm.advance(2_150_000_000)
    stock = runtime.step(self.sm, self.cp, now_ns=2_150_000_000)
    self.assertFalse(stock.message.slcState.hasCeiling)
    self.assertIsNone(stock.result.ceiling)

  def test_source_requires_matching_car_frame_and_restart_changes_identity(self):
    runtime = Runtime(parse({'SpeedLimitController': True}), session_id='paired-drive')
    source = self.sm['slcDashboardObservation']
    source.carStateLogMonoTime = 1_950_000_000
    mismatched = runtime.step(self.sm, self.cp, now_ns=2_000_000_000)
    self.assertEqual(runtime._observations(self.sm, self.cp, 2_000_000_000)[Source.DASHBOARD].kind,
                     ObservationKind.UNKNOWN)
    self.assertFalse(mismatched.message.slcState.hasCeiling)

    source.carStateLogMonoTime = 2_000_000_000
    matched = runtime.step(self.sm, self.cp, now_ns=2_000_000_000)
    first_identity = matched.result.selection.observation.candidate.observation_identity.value
    self.assertTrue(matched.message.slcState.hasCeiling)
    self.sm.logMonoTime['carState'] = 2_010_000_000  # independent sockets deliver the next card tick first
    lagged = runtime.step(self.sm, self.cp, now_ns=2_010_000_000)
    self.assertTrue(lagged.message.slcState.hasCeiling)
    source.producerSessionId = 'restarted-card'
    restarted = runtime.step(self.sm, self.cp, now_ns=2_010_000_000)
    second_identity = restarted.result.selection.observation.candidate.observation_identity.value
    self.assertNotEqual(first_identity, second_identity)

  def test_lateral_authority_uses_car_control_axis(self):
    runtime = Runtime(parse({'SpeedLimitController': True}), session_id='axis-drive')
    self.sm['selfdriveState'].active = True
    long_only = runtime.step(self.sm, self.cp, now_ns=2_000_000_000)
    self.assertEqual(long_only.result.ceiling.authority.mode.value, 'longitudinal_only')
    self.sm['carControl'].latActive = True
    combined = runtime.step(self.sm, self.cp, now_ns=2_000_000_000)
    self.assertEqual(combined.result.ceiling.authority.mode.value, 'combined')

  def test_rejected_and_malformed_ui_requests_do_not_fill_action_ledger(self):
    runtime = Runtime(parse({'SpeedLimitController': True}), session_id='many-actions')
    runtime.step(self.sm, self.cp, now_ns=2_000_000_000)
    wrong = Action(runtime.session_id, 1, 0, 99999, 'adopt')
    runtime.step(self.sm, self.cp, now_ns=2_000_000_000, request=wrong)
    self.assertEqual(runtime.ledger.transactions, ())
    self.assertEqual(runtime.ledger.last_action_id, -1)
    for sequence in range(2, 202):
      timestamp = 2_000_000_000 + sequence
      self.sm.advance(timestamp)
      runtime.step(self.sm, self.cp, now_ns=timestamp,
                   request=Action(runtime.session_id, sequence, 99999, 0, 'reject'))
      self.assertFalse(runtime.ledger.reset_required)
      self.assertEqual(runtime.ledger.transactions, ())


if __name__ == '__main__':
  unittest.main()
