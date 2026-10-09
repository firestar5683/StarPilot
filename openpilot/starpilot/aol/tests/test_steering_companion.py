import time
import unittest
from unittest import mock

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.common.realtime import Ratekeeper
from openpilot.selfdrive.car.cruise import VCruiseHelper
from openpilot.selfdrive.car.tests.publication_fixture import initialize_publication_sources
from openpilot.starpilot.aol.tests import test_runtime as runtime_fixture
from openpilot.starpilot.car.gm.steering_companion import MAX_COMPANIONS, MAX_DRAIN, SteeringCompanion
from opendbc.car.structs import car


class SteeringCompanionContractTests(unittest.TestCase):
  _authority_callers = runtime_fixture.IpcAxisContractTests._authority_callers

  def test_card_socket_first_seen_companion_overrun_reaches_controls(self):
    from openpilot.selfdrive.car.card import Car
    real_recv = messaging.recv_one
    real_recv_optional = messaging.recv_one_or_none
    for full_op in (False, True):
      for case in ('healthy', 'old_fault', 'new_fault', 'missing_exact', 'invalid_latest', 'wrong_source',
                   'expired_source', 'future_latest', 'sm_fault_before_raw'):
        with self.subTest(full_op=full_op, case=case), OpenpilotPrefix():
          messaging.reset_context()
          sd, controls, step = self._authority_callers(full_op)
          self.assertTrue(step(0)[0].lateralActive)
          pm = messaging.PubMaster(['carState', 'carOutput', 'starpilotCarState'])
          sd.car_state_sock = messaging.sub_sock('carState', timeout=100)
          sd.steering_companion = SteeringCompanion(messaging.sub_sock('starpilotCarState', conflate=False))
          latest_sock = messaging.sub_sock('starpilotCarState', conflate=True, timeout=100)
          card = Car.__new__(Car)
          card.CP, card.pm = sd.CP, pm
          initialize_publication_sources(card)
          authority = card.CI.CS.steering_authority
          card.sm = messaging.SubMaster(['carControl'], ignore_avg_freq=['carControl'])
          control = messaging.new_message('carControl', valid=True, logMonoTime=10_000_000_000)
          card.sm.update_msgs(10., [control.as_reader()])
          card.sm.frame = 1
          card.car_params_published = True
          card.last_actuators_output = car.CarControl.Actuators.new_message()
          card.slc_replay = card.curve_replay = card.aol_replay = False
          card.can_rcv_cum_timeout_counter = 0
          card.rk = Ratekeeper(100., print_delay_threshold=None)
          card.v_cruise_helper = VCruiseHelper(card.CP)
          source_ns = 10_010_000_000
          later_ns = source_ns + 7_000_000
          now_ns = source_ns + (30_000_001 if case == 'expired_source' else 13_000_000)
          self.assertNotIn(source_ns, sd.steering_companion.samples)

          original_message = messaging.new_message

          def publish(stamp, *, fault=False, enabled=True, valid=True,
                      authority=authority, card=card, original_message=original_message):
            authority.enabled, authority.latched = enabled, fault
            state = runtime_fixture.car_state()
            state.canValid = valid
            state.cruiseState.available = True
            with mock.patch('openpilot.selfdrive.car.card.messaging.new_message', side_effect=lambda *args, **kwargs:
                            original_message(*args, **dict(kwargs, logMonoTime=stamp))):
              card.state_publish(state, None)

          consumer_clock = mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=now_ns)

          def receive_then_overtake(sock, *, publish=publish, source_ns=source_ns, case=case,
                                    now_ns=now_ns, later_ns=later_ns, original_message=original_message,
                                    pm=pm, consumer_clock=consumer_clock):
            publish(source_ns, fault=case == 'old_fault', enabled=case != 'missing_exact')
            first_seen = real_recv(sock)
            self.assertEqual(first_seen.logMonoTime, source_ns)
            publish(now_ns + 1 if case == 'future_latest' else later_ns, fault=case in ('new_fault', 'sm_fault_before_raw'),
                    valid=case != 'invalid_latest')
            if case == 'wrong_source':
              malformed = original_message('starpilotCarState', valid=True, logMonoTime=later_ns)
              malformed.starpilotCarState.sourceCarStateMonoTime = later_ns - 1
              pm.send('starpilotCarState', malformed)
            consumer_clock.start()
            self.addCleanup(consumer_clock.stop)
            return first_seen

          def update_latest(_timeout, *, latest_sock=latest_sock, source_ns=source_ns, sd=sd, now_ns=now_ns):
            latest = real_recv(latest_sock)
            self.assertIsNotNone(latest)
            self.assertGreater(latest.logMonoTime, source_ns)
            sd.sm.update_msgs(now_ns / 1e9, [latest])

          def deliver_raw(sock, *, case=case, source_ns=source_ns):
            message = real_recv_optional(sock)
            if case == 'sm_fault_before_raw' and message is not None and message.logMonoTime > source_ns:
              return None
            return message

          sd.sm.update.side_effect = update_latest
          with (mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one', side_effect=receive_then_overtake),
                mock.patch('openpilot.starpilot.car.gm.steering_companion.messaging.recv_one_or_none', side_effect=deliver_raw)):
            axis, state, command = step(1)
          if case == 'sm_fault_before_raw':
            assert sd.steering_companion.latest is not None
            self.assertEqual(sd.steering_companion.latest[0], source_ns)
            self.assertTrue(sd.sm['starpilotCarState'].lateralAuthorityUnavailable)
          self.assertEqual(axis.sourceCarStateMonoTime, source_ns)
          self.assertEqual(axis.lateralActive, case == 'healthy')
          self.assertEqual(command.latActive, case == 'healthy')
          self.assertEqual(command.longActive, full_op and case == 'healthy')
          self.assertEqual(log.OnroadEvent.EventName.controlsMismatch in sd.events.names, case != 'healthy')
          if case != 'healthy':
            self.assertFalse(sd.enabled or sd.active or axis.longitudinalActive)
            self.assertEqual(state.alertText1, 'TAKE CONTROL IMMEDIATELY')
            self.assertEqual(state.alertSound, log.SelfdriveState.AudibleAlert.warningImmediate)
          consumer_clock.stop()
          if case == 'healthy':
            sd.sm.update.side_effect = None
            for tick in (2, 4):
              retained, _, retained_command = step(tick, timeout=True)
              self.assertEqual(retained.sourceCarStateMonoTime, source_ns)
              self.assertTrue(retained.lateralActive and retained_command.latActive)
              self.assertNotIn(log.OnroadEvent.EventName.controlsMismatch, sd.events.names)
            expired, _, expired_command = step(5, timeout=True)
            self.assertEqual(expired.sourceCarStateMonoTime, 0)
            self.assertFalse(expired.lateralActive or expired_command.latActive or expired_command.longActive)
            self.assertIn(log.OnroadEvent.EventName.controlsMismatch, sd.events.names)

  def test_raw_queue_is_bounded_and_receipt_never_renews_source(self):
    for case in ('bounded', 'overrun', 'expired', 'invalid_exact', 'out_of_order_fault'):
      with self.subTest(case=case), OpenpilotPrefix():
        messaging.reset_context()
        pm = messaging.PubMaster(['starpilotCarState'])
        owner = SteeringCompanion(messaging.sub_sock('starpilotCarState', conflate=False))
        sm = messaging.SubMaster(['starpilotCarState'])
        stamp = time.monotonic_ns()
        count = MAX_DRAIN + 1 if case == 'overrun' else MAX_COMPANIONS + 2 if case == 'bounded' else 3 if case == 'out_of_order_fault' else 2
        for index in range(count):
          offset = (0, 2, 1)[index] if case == 'out_of_order_fault' else index
          message = messaging.new_message('starpilotCarState', valid=case != 'invalid_exact' or index != 0,
                                          logMonoTime=stamp + offset)
          message.starpilotCarState.sourceCarStateMonoTime = message.logMonoTime
          message.starpilotCarState.lateralAuthorityUnavailable = case == 'out_of_order_fault' and index == 1
          pm.send('starpilotCarState', message)
        sm.update(100)
        now = stamp + (30_000_001 if case == 'expired' else count)
        result = owner.current(sm, source_ns=stamp, now_ns=now)
        if case == 'out_of_order_fault':
          self.assertTrue(result)
          assert owner.latest is not None
          self.assertEqual(owner.latest[0], stamp + 2)
        else:
          self.assertIsNone(result)
        self.assertLessEqual(len(owner.samples), MAX_COMPANIONS)
        if case == 'expired':
          self.assertNotIn(stamp, owner.samples)
        if case == 'overrun':
          assert owner.latest is not None
          self.assertEqual(owner.latest[0], stamp + MAX_DRAIN - 1)
