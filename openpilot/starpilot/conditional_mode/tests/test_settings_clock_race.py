"""Actual CEM host/consumer/caller; controlled settings-worker interleaving."""
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.cereal import messaging
from openpilot.selfdrive.selfdrived import selfdrived as module
from openpilot.starpilot.conditional_mode.policy import ManualIntent
from openpilot.starpilot.conditional_mode.runtime_settings import DOCUMENT_KEY, REFRESH_NS
from openpilot.starpilot.conditional_mode.tests import test_status_consumer as fixture
from openpilot.starpilot.conditional_mode.tests.test_projection import BOOT, MONO, owner_context


class TestSettingsClockRace(unittest.TestCase):
  def setUp(self):
    self.source = fixture.TestModeTransport(methodName='runTest')
    self.source.setUp()
    self.addCleanup(self.source.doCleanups)
    self.enterContext(patch.object(module, 'REPLAY', False))
    self.drive = module.SelfdriveD.__new__(module.SelfdriveD)
    self.drive.CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC_BOSCH)
    self.drive.CP.openpilotLongitudinalControl = True
    self.drive.params = self.source.params
    self.drive.conditional_replay = True
    self.drive.conditional_settings = self.source.owner
    self.drive.conditional_consumer = self.source.consumer
    self.drive.conditional_car_state_valid = self.drive.initialized = self.drive.enabled = True
    self.drive.aol_replay = False
    self.scene = {'speed': 10.0, 'horizon': 40.0, 'lead_present': False}
    for tick in range(1, 31):
      now = MONO + tick * 50_000_000
      event, _, _ = self.source.produce(now, intent=ManualIntent.NONE, scene=self.scene,
        context=owner_context(now - 2_000_000))
      self.source.consume(event, now)
    self.assertTrue(self.source.host.projector.stop_detector.committed)

  def call(self, during_clock=None, before_verdict=None, *, can_valid=True):
    now = MONO + 31 * 50_000_000
    event, proposal, sm = self.source.produce(now, intent=ManualIntent.NONE, scene=self.scene,
      context=owner_context(now - 2_000_000))
    assert proposal.decision is not None
    self.assertEqual(proposal.decision.reason.value, 'cem_stop')
    device = messaging.new_message('deviceState', valid=True)
    device.deviceState.started = True
    device.deviceState.startedMonoTime = self.source.drive_id
    sm.payloads['deviceState'] = messaging.log_from_bytes(device.to_bytes()).deviceState
    sm.payloads['slcState'] = messaging.log_from_bytes(event.to_bytes()).slcState
    for service in ('deviceState', 'slcState'):
      sm.logMonoTime[service] = now
      sm.recv_time[service] = now / 1e9
      sm.seen[service] = sm.alive[service] = sm.valid[service] = True
    self.drive.sm, self.drive.aol_car_state_log_ns = sm, now - 2_000_000
    cs = sm['carState'].as_builder()
    cs.canValid = can_valid
    verdict = self.source.owner.verdict

    def clocks():
      if during_clock is not None:
        during_clock(now)
      return now, BOOT + now - MONO, 1000

    def interleaved(snapshot, **kwargs):
      if before_verdict is not None:
        before_verdict(now)
      return verdict(snapshot, **kwargs)
    with patch.object(module, 'paired_clocks_ns', side_effect=clocks), \
         patch.object(self.source.owner, 'verdict', side_effect=interleaved):
      self.drive.update_conditional_mode(cs)
    self.assertTrue(self.source.host.projector.stop_detector.committed)
    return now

  def reverify(self, now):
    old = self.source.owner.current
    self.assertIsNotNone(old)
    assert old is not None
    new = self.source.owner.refresh(now + 1_000_000, force=True)
    self.assertEqual(new.revision, old.revision)
    self.assertEqual(new.observed_mono_ns, old.observed_mono_ns)
    self.assertGreater(new.verified_mono_ns, now)

  def test_same_revision_worker_after_cycle_clock_preserves_actual_cem(self):
    self.call(during_clock=self.reverify)
    self.assertTrue(self.drive.conditional_result.accepted)
    self.assertTrue(self.drive.experimental_mode)

  def test_same_revision_worker_before_verdict_preserves_actual_cem(self):
    self.call(before_verdict=self.reverify)
    self.assertTrue(self.drive.conditional_result.accepted)
    self.assertTrue(self.drive.experimental_mode)

  def test_changed_source_rejects_captured_revision(self):
    def change(now):
      self.source.params.put_bool('ExperimentalMode', True, block=True)
      self.source.owner.refresh(now + 1_000_000, force=True)
    self.call(during_clock=change)
    self.assertFalse(self.drive.conditional_result.accepted)
    self.assertFalse(self.drive.experimental_mode)

  def test_corrupt_source_rejects_captured_revision(self):
    def change(now):
      Path(self.source.params.get_param_path(DOCUMENT_KEY)).write_bytes(b'malformed')
      self.source.owner.refresh(now + 1_000_000, force=True)
    self.call(during_clock=change)
    self.assertFalse(self.drive.conditional_result.accepted)
    self.assertFalse(self.drive.experimental_mode)

  def test_current_vehicle_fault_remains_rejected_during_reverification(self):
    self.call(during_clock=self.reverify, can_valid=False)
    self.assertFalse(self.drive.conditional_result.accepted)
    self.assertFalse(self.drive.experimental_mode)

  def test_captured_verification_cannot_borrow_newer_expiry(self):
    old = self.source.owner.current
    self.assertIsNotNone(old)
    assert old is not None
    now = old.verified_mono_ns + REFRESH_NS + 1
    self.source.owner.refresh(now + 1_000_000, force=True)
    self.assertFalse(self.source.owner.affirm(old, now_mono_ns=now))

  def test_snapshot_source_fields_cannot_be_forged(self):
    old = self.source.owner.current
    self.assertIsNotNone(old)
    assert old is not None
    self.assertFalse(self.source.owner.affirm(replace(old, experimental_raw=b'1'), now_mono_ns=old.verified_mono_ns))
