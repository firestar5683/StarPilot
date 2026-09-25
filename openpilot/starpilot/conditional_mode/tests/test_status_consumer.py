"""Actual host proposals, serialized transport and the effective-mode owner."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
import json
import tempfile
import unittest

from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
from openpilot.starpilot.conditional_mode.consumer import ModeConsumer
from openpilot.starpilot.conditional_mode.host import ConditionalModeHost
from openpilot.starpilot.conditional_mode.policy import ManualIntent, ModeChoice
from openpilot.starpilot.conditional_mode.preferences import SavedPreferences, encode_preferences, manual_for_drive
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner, DOCUMENT_KEY
from openpilot.starpilot.conditional_mode.status import StatusPublisher, observation, settings_fingerprint
from openpilot.starpilot.conditional_mode.tests.test_projection import BOOT, CP, MONO, FakeSubMaster, serialized_scene


class TestModeTransport(unittest.TestCase):
  def setUp(self):
    directory = self.enterContext(tempfile.TemporaryDirectory())
    self.params = Params(directory)
    self.params.put(DOCUMENT_KEY, json.loads(encode_preferences(SavedPreferences(mode=ModeChoice.CEM))), block=True)
    self.owner = ConditionalSettingsOwner(self.params)
    self.host = ConditionalModeHost()
    self.publisher = StatusPublisher()
    self.consumer = ModeConsumer()
    self.drive_id = MONO - 1_000_000_000
    self.produce(MONO)
    self.consume(None, MONO)

  def produce(self, now, *, intent=ManualIntent.FORCE_EXPERIMENTAL, lat=False, long=True, outer=None):
    sm = FakeSubMaster(serialized_scene(stamp=BOOT + now - MONO - 2_000_000), now - 2_000_000)
    control = messaging.new_message('carControl')
    control.carControl.longActive = long
    control.carControl.latActive = lat
    sm.payloads['carControl'] = messaging.log_from_bytes(control.to_bytes()).carControl
    proposal = self.host.sample(
      sm,
      CP,
      now_mono_ns=now,
      now_boot_ns=BOOT + now - MONO,
      sample_skew_ns=1000,
      drive_id=self.drive_id,
      settings_owner=self.owner,
      manual=manual_for_drive(intent, self.drive_id, self.drive_id + 1),
      selected_t_follow_s=1.45,
      selected_t_follow_observed_mono_ns=now - 2_000_000,
    )
    event = self.publisher.attach(
      outer, proposal, self.owner.current, now_ns=now, drive_id=self.drive_id, model_ns=now - 2_000_000, car_state_ns=now - 2_000_000
    )
    return event, proposal, sm

  def consume(self, event, now, **changes):
    payload = messaging.log_from_bytes(event.as_reader().as_builder().to_bytes()).slcState if event is not None else None
    values = {
      'now_ns': now,
      'now_boot_ns': BOOT + now - MONO,
      'sample_skew_ns': 1000,
      'message_ns': now,
      'receipt_ns': now,
      'drive_id': self.drive_id,
      'model_ns': now - 2_000_000,
      'car_state_ns': now - 2_000_000,
      'authority': True,
      'stock_experimental': False,
      'choice': ModeChoice.CEM,
      'settings_fingerprint': settings_fingerprint(self.owner.current),
    }
    values.update(changes)
    return self.consumer.sample(payload, **values)

  def test_both_directions_and_independent_longitudinal_authority(self):
    now = MONO + 50_000_000
    event, proposal, _ = self.produce(now)
    self.assertTrue(proposal.override_experimental)
    self.assertTrue(self.consume(event, now).experimental)
    event, proposal, _ = self.produce(now + 50_000_000, intent=ManualIntent.FORCE_CHILL)
    self.assertFalse(proposal.override_experimental)
    chill = self.consume(event, now + 50_000_000, stock_experimental=True)
    self.assertTrue(chill.accepted)
    self.assertFalse(chill.experimental)
    lateral, _, _ = self.produce(now + 100_000_000, lat=True, long=False)
    self.assertFalse(lateral.slcState.conditionalMode.hasOverride)
    denied = self.consume(event, now + 60_000_000, authority=False, stock_experimental=True)
    self.assertFalse(denied.accepted)
    self.assertTrue(denied.experimental)

  def test_invalid_or_old_nested_state_never_uses_outer_slc_availability(self):
    now = MONO + 50_000_000
    outer = messaging.new_message('slcState', valid=False)
    outer.logMonoTime = now
    outer.slcState.sessionId = 'original-slc-session'
    event, _, _ = self.produce(now, outer=outer)
    self.assertEqual(event.slcState.sessionId, 'original-slc-session')
    self.assertTrue(self.consume(event, now).accepted)
    self.assertIsNone(observation(messaging.new_message('slcState').slcState, now))
    for field, bad in (
      ('version', 99),
      ('sessionId', ''),
      ('settingsFingerprint', 'x'),
      ('modelMonoTime', 0),
      ('validUntilMonoTime', now + 1_000_000_000),
      ('choice', 'stock'),
      ('status', 'stock'),
    ):
      changed = messaging.log_from_bytes(event.as_reader().as_builder().to_bytes()).as_builder()
      setattr(changed.slcState.conditionalMode, field, bad)
      with self.subTest(field=field):
        self.assertFalse(self.consume(changed, now).accepted)

  def test_repeat_has_original_expiry_and_changed_sequence_is_rejected(self):
    now = MONO + 50_000_000
    event, _, _ = self.produce(now)
    self.assertTrue(self.consume(event, now).accepted)
    self.assertTrue(self.consume(event, now + 20_000_000, message_ns=now, receipt_ns=now).accepted)
    changed = messaging.log_from_bytes(event.as_reader().as_builder().to_bytes()).as_builder()
    changed.slcState.conditionalMode.experimental = False
    self.assertFalse(self.consume(changed, now + 20_000_000, message_ns=now, receipt_ns=now).accepted)
    self.assertFalse(self.consume(event, now + 101_000_000, message_ns=now, receipt_ns=now).accepted)
    later, _, _ = self.produce(now + 150_000_000)
    self.assertTrue(self.consume(later, now + 150_000_000).accepted)
    self.assertFalse(self.consume(event, now + 150_000_000).accepted)

  def test_new_session_resume_and_drive_wait_for_new_sources(self):
    now = MONO + 50_000_000
    event, _, _ = self.produce(now)
    self.assertTrue(self.consume(event, now).accepted)
    self.publisher = StatusPublisher()
    new, _, _ = self.produce(now + 50_000_000)
    self.assertFalse(self.consume(new, now + 50_000_000).accepted)
    self.assertFalse(self.consume(new, now + 55_000_000, message_ns=now + 50_000_000).accepted)
    next_event, _, _ = self.produce(now + 100_000_000)
    self.assertTrue(self.consume(next_event, now + 100_000_000).accepted)
    self.assertFalse(self.consume(next_event, now + 110_000_000, now_boot_ns=BOOT + 5_000_000_000).accepted)
    self.assertFalse(self.consume(next_event, now + 120_000_000, drive_id=self.drive_id + 1).accepted)

  def test_settings_identity_and_malformed_stock_request(self):
    now = MONO + 50_000_000
    event, proposal, _ = self.produce(now)
    self.assertFalse(self.consume(event, now, settings_fingerprint='0' * 64).accepted)
    self.assertFalse(self.consume(event, now, stock_experimental='false').experimental)
    current = self.owner.current
    assert current is not None
    newer = replace(current, revision=current.revision + 1)
    rejected = self.publisher.attach(None, proposal, newer, now_ns=now, drive_id=self.drive_id, model_ns=now - 2_000_000, car_state_ns=now - 2_000_000)
    self.assertFalse(rejected.slcState.conditionalMode.hasOverride)

  def test_actual_selfdrived_owner_preserves_stock_and_separates_axes(self):
    drive = SelfdriveD.__new__(SelfdriveD)
    drive.conditional_replay = False
    drive.requested_experimental_mode = True
    drive.update_conditional_mode(None)
    self.assertTrue(drive.experimental_mode)
    drive.conditional_replay = True
    drive.conditional_settings = self.owner
    drive.conditional_consumer = self.consumer
    drive.conditional_car_state_valid = True
    drive.initialized = True
    drive.enabled = True
    drive.aol_replay = True
    axes = SimpleNamespace(longitudinal_active=True, lateral_active=False)
    self.enterContext(patch.object(drive, "aol_axis_decision", axes, create=True))
    drive.CP = SimpleNamespace(openpilotLongitudinalControl=True, passive=False)
    for index, intent in enumerate((ManualIntent.FORCE_CHILL, ManualIntent.FORCE_EXPERIMENTAL), start=1):
      now = MONO + index * 50_000_000
      event, _, sm = self.produce(now, intent=intent)
      device = messaging.new_message('deviceState', valid=True)
      device.deviceState.started = True
      device.deviceState.startedMonoTime = self.drive_id
      sm.payloads['deviceState'] = messaging.log_from_bytes(device.to_bytes()).deviceState
      sm.payloads['slcState'] = messaging.log_from_bytes(event.as_reader().as_builder().to_bytes()).slcState
      for service in ('deviceState', 'slcState'):
        sm.logMonoTime[service] = now
        sm.recv_time[service] = now / 1e9
        sm.seen[service] = sm.alive[service] = sm.valid[service] = True
      sm.valid['slcState'] = False  # Unavailable SLC does not invalidate this nested proposal.
      drive.sm = sm
      drive.aol_car_state_log_ns = now - 2_000_000
      with patch('openpilot.selfdrive.selfdrived.selfdrived.paired_clocks_ns', return_value=(now, BOOT + now - MONO, 1000)):
        drive.update_conditional_mode(sm['carState'])
        self.assertEqual(drive.experimental_mode, intent is ManualIntent.FORCE_EXPERIMENTAL)
        axes.longitudinal_active = False
        drive.update_conditional_mode(sm['carState'])
        self.assertTrue(drive.experimental_mode)  # Exact existing stock request; no conditional override.
        axes.longitudinal_active = True
