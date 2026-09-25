"""Same-cycle SLC fallback evidence through actual Runtime and serialized state."""

import unittest
from dataclasses import replace

from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.cereal import messaging
from openpilot.starpilot.conditional_mode.slc_fallback import Reason, evaluate, evaluate_runtime
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import messages
from openpilot.starpilot.speed_limits.runtime import Output, Runtime
from openpilot.starpilot.speed_limits.runtime_settings import parse


NOW = 2_000_000_000


class ReplaySM:
  def __init__(self):
    self.data, _ = messages()
    self.data['slcDashboardObservation'] = messaging.new_message('slcDashboardObservation').slcDashboardObservation
    self.valid = dict.fromkeys(self.data, True)
    self.alive = dict.fromkeys(self.data, True)
    self.logMonoTime = dict.fromkeys(self.data, NOW)
    self.data['carControl'].enabled = True
    self.data['carControl'].longActive = True
    self.data['carState'].vCruiseCluster = 100.0
    self.data['carState'].vEgoCluster = 20.0
    source = self.data['slcDashboardObservation']
    source.producerSessionId = 'card'
    source.carStateLogMonoTime = NOW
    source.status = 'absent'
    source.observedMonoTime = NOW - 100_000_000
    source.validUntilMonoTime = NOW + 1_000_000_000

  def __getitem__(self, name):
    return self.data[name]


class SlcFallbackTests(unittest.TestCase):
  def setUp(self):
    self.cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    self.sm = ReplaySM()
    self.settings = parse({'SpeedLimitController': True, 'SLCFallback': 1,
                           'SLCPriority1': 'Dashboard', 'SLCPriority2': 'Dashboard'})

  def step(self, settings=None, *, serialize=True):
    settings = settings or self.settings
    output = Runtime(settings, session_id='fallback-drive').step(self.sm, self.cp, now_ns=NOW)
    # Exercise the actual serialized SLC receipt without opening an IPC service.
    decoded = messaging.log_from_bytes(output.message.to_bytes()) if serialize else output.message
    self.assertEqual(decoded.slcState.sessionId, 'fallback-drive')
    return Output(output.result, decoded, output.action_result, output.command, output.settings)

  def test_qualified_absence_is_advisory_not_a_control_target(self):
    output = self.step()
    self.assertEqual(output.message.slcState.observationKind, 'absent')
    self.assertFalse(output.message.slcState.hasCeiling)
    evidence = evaluate(output, self.settings)
    self.assertEqual((evidence.reason, evidence.proposed_experimental), (Reason.QUALIFIED_ABSENCE, True))
    self.assertIsNone(evidence.current_control_target_mps)
    self.assertIsNone(evidence.effective_cap_mps)
    self.assertFalse(evidence.historical_accepted)

  def test_valid_pending_and_previous_accepted_are_not_zero_target_fallback(self):
    source = self.sm['slcDashboardObservation']
    source.status = 'valid'
    source.speedMps = 25.0
    source.episode = 1
    output = self.step()
    self.assertEqual(output.message.slcState.observationKind, 'valid')
    self.assertEqual(evaluate(output, self.settings).reason, Reason.CURRENT_LIMIT)

    pending_settings = parse({'SpeedLimitController': True, 'SLCFallback': 1,
                              'SLCPriority1': 'Dashboard', 'SLCPriority2': 'Dashboard',
                              'SLCConfirmation': True, 'SLCConfirmationHigher': True})
    pending = self.step(pending_settings)
    self.assertTrue(pending.message.slcState.hasPending)
    self.assertEqual(evaluate(pending, pending_settings).reason, Reason.CURRENT_LIMIT)

    source.status = 'absent'
    runtime = Runtime(self.settings, session_id='fallback-drive')
    source.status = 'valid'
    accepted = runtime.step(self.sm, self.cp, now_ns=NOW)
    self.assertTrue(accepted.message.slcState.hasAccepted)
    source.status = 'absent'
    self.sm.logMonoTime = dict.fromkeys(self.sm.data, NOW + 50_000_000)
    source.carStateLogMonoTime = NOW + 50_000_000
    later = runtime.step(self.sm, self.cp, now_ns=NOW + 50_000_000)
    evidence = evaluate(later, self.settings)
    self.assertTrue(evidence.historical_accepted)
    self.assertFalse(evidence.pending)
    self.assertEqual((evidence.reason, evidence.proposed_experimental), (Reason.QUALIFIED_ABSENCE, True))

  def test_unknown_stale_and_settings_states(self):
    source = self.sm['slcDashboardObservation']
    source.status = 'unknown'
    unknown = self.step()
    self.assertEqual(evaluate(unknown, self.settings).reason, Reason.SOURCE_UNKNOWN)
    source.status = 'stale'
    stale = self.step()
    self.assertEqual(evaluate(stale, self.settings).reason, Reason.SOURCE_STALE)
    source.status = 'absent'
    absent = self.step()
    for choice in (0, 2):
      settings = parse({'SpeedLimitController': True, 'SLCFallback': choice,
                        'SLCPriority1': 'Dashboard', 'SLCPriority2': 'Dashboard'})
      self.assertEqual(evaluate(self.step(settings), settings).reason, Reason.OTHER_FALLBACK)
    self.assertEqual(evaluate(absent, replace(self.settings, fallback_choice=True)).reason, Reason.INVALID_FALLBACK)
    disabled = parse({'SpeedLimitController': False})
    self.assertEqual(evaluate(self.step(disabled), disabled).reason, Reason.DISABLED)
    display = parse({'SpeedLimitController': False, 'ShowSpeedLimits': True})
    self.assertEqual(evaluate(self.step(display), display).reason, Reason.DISPLAY_ONLY)
    corrupt = parse({'SpeedLimitController': True, 'SLCFallback': 'bad'})
    self.assertEqual(evaluate(self.step(corrupt), corrupt).reason, Reason.INVALID_SETTINGS)
    mixed = parse({'SpeedLimitController': True, 'SLCFallback': 1})
    # The map producer is unknown, so one absent dashboard source is insufficient.
    self.assertEqual(evaluate(self.step(mixed), mixed).reason, Reason.SOURCE_UNKNOWN)
    previous = parse({'SpeedLimitController': True, 'SLCFallback': 2,
                      'SLCPriority1': 'Dashboard', 'SLCPriority2': 'Dashboard'})
    self.assertEqual(evaluate(self.step(previous), replace(previous, fallback_choice=1)).reason,
                     Reason.INCONSISTENT_CYCLE)

  def test_same_cycle_receipt_and_zero_cap_cannot_forge_absence(self):
    source = self.sm['slcDashboardObservation']
    source.status = 'valid'
    source.speedMps = 25.0
    source.episode = 1
    output = self.step(serialize=False)
    self.assertIsNotNone(output.result.acceptance.control_target_mps)
    # Even a displayed zero cap is not proof that no limit was accepted.
    output.message.slcState.effectiveCap = 0.0
    decoded = Output(output.result, messaging.log_from_bytes(output.message.to_bytes()))
    self.assertEqual(evaluate(decoded, self.settings).reason, Reason.CURRENT_LIMIT)
    forged = Output(output.result, messaging.new_message('slcState'))
    self.assertEqual(evaluate(forged, self.settings).reason, Reason.INCONSISTENT_CYCLE)

  def test_live_snapshot_rejects_prior_and_foreign_runtime_outputs(self):
    runtime = Runtime(self.settings, session_id='bound-drive')
    first = runtime.step(self.sm, self.cp, now_ns=NOW)
    self.assertEqual(evaluate_runtime(runtime, first).reason, Reason.QUALIFIED_ABSENCE)
    foreign = Runtime(self.settings, session_id='bound-drive')
    self.assertEqual(evaluate_runtime(foreign, first).reason, Reason.INCONSISTENT_CYCLE)
    # Choices 0 and 1 share the same acceptance policy and wire output. The
    # settings identity, rather than that policy, binds the saved revision.
    original_settings = runtime.settings
    runtime.settings = replace(original_settings, fallback_choice=0)
    self.assertEqual(evaluate_runtime(runtime, first).reason, Reason.INCONSISTENT_CYCLE)
    runtime.settings = original_settings
    later_ns = NOW + 50_000_000
    self.sm.logMonoTime = dict.fromkeys(self.sm.data, later_ns)
    self.sm['slcDashboardObservation'].carStateLogMonoTime = later_ns
    later = runtime.step(self.sm, self.cp, now_ns=later_ns)
    self.assertEqual(evaluate_runtime(runtime, first).reason, Reason.INCONSISTENT_CYCLE)
    self.assertEqual(evaluate_runtime(runtime, later).reason, Reason.QUALIFIED_ABSENCE)


if __name__ == '__main__':
  unittest.main()
