import unittest
import numpy as np
from types import SimpleNamespace as N
from unittest.mock import patch

from openpilot.cereal import messaging, log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.selfdrived.alertmanager import AlertManager
from openpilot.selfdrive.selfdrived.events import Alert, ET, Priority, VisualAlert
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
from openpilot.selfdrive.ui.soundd import Soundd, AudibleAlert
from openpilot.starpilot.audio.axis_alerts import AxisAlerts
from openpilot.starpilot.audio.availability_warning import AvailabilityWarningDelivery

class TestAvailabilityWarningDelivery(unittest.TestCase):
  def fixture_attr(self, obj, name, value):
    replacement = patch.object(obj, name, value, create=True)
    replacement.start()
    self.addCleanup(replacement.stop)

  def publisher(self, pm):
    sd = SelfdriveD.__new__(SelfdriveD)
    sd.enabled = sd.active = False
    self.fixture_attr(sd, 'state_machine', N(state=log.SelfdriveState.OpenpilotState.disabled))
    self.fixture_attr(sd, 'events', N(contains=lambda _: False))
    sd.experimental_mode = False
    sd.personality = log.LongitudinalPersonality.standard
    sd.AM = AlertManager()
    sd.pm = pm
    sd.conditional_replay = False
    sd.aol_session_id = 'delivery-session'
    self.fixture_attr(sd, 'sm', {'deviceState': N(started=True, startedMonoTime=1)})
    sd.availability_warning_delivery = AvailabilityWarningDelivery()
    return sd

  def issue(self, sd, now):
    alert = Alert('Steering Paused', 'Communication Issue', log.SelfdriveState.AlertStatus.normal,
      log.SelfdriveState.AlertSize.small, Priority.LOW, VisualAlert.none, AudibleAlert.prompt, 0.)
    alert.alert_type, alert.event_type = 'aolAvailability/warning', ET.WARNING
    sd.AM.add_many(10, [alert])
    sd.AM.process_alerts(10, set())
    sd.availability_warning_delivery.observe(session=sd.aol_session_id, drive=1, now_ns=now,
      selected=True, requested_until_ns=now + 400_000_000)

  def sound(self):
    sound = Soundd.__new__(Soundd)
    sound.axis_alerts = AxisAlerts()
    sound.current_alert = sound.current_sound = AudibleAlert.none
    sound.current_sound_frame = 0
    sound.pending_stop = False
    sound.selfdrive_timeout_alert = False
    sound.loaded_sounds = {AudibleAlert.prompt: np.full(16, 0.25, dtype=np.float32),
                           AudibleAlert.none: np.zeros(16, dtype=np.float32)}
    sound.current_volume = 1.0
    sound.saved_volumes = {}
    self.fixture_attr(sound, 'pack_loader', N(is_builtin=lambda _: False))
    return sound

  def test_actual_serialized_publisher_latest_conflation_delivers_after_five_ms_recovery(self):
    with OpenpilotPrefix():
      pm = messaging.PubMaster(['selfdriveState'])
      sm = messaging.SubMaster(['selfdriveState'])  # production conflate=True
      sd = self.publisher(pm)
      now = 10_000_000_000
      self.issue(sd, now)
      with patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=now):
        sd.publish_selfdriveState(N(), axis_published=True)
      sd.AM.process_alerts(11, {ET.WARNING})
      for delta in (5_000_000, 10_000_000, 20_000_000, 30_000_000, 40_000_000):
        with patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=now + delta):
          sd.publish_selfdriveState(N(), axis_published=True)
      sm.update(1000)  # first soundd read after all producer publications
      self.assertTrue(sm.updated['selfdriveState'])
      self.assertEqual(sm['selfdriveState'].alertType, '')
      self.assertEqual(str(sm['selfdriveState'].alertSound), 'prompt')
      self.assertFalse(sm['selfdriveState'].enabled or sm['selfdriveState'].active)
      sound = self.sound()
      with patch('openpilot.selfdrive.ui.soundd.time.monotonic_ns', return_value=now + 50_000_000):
        sound.get_audible_alert(sm)  # actual 20 Hz first receive boundary, no audio device
      self.assertEqual(sound.current_alert, AudibleAlert.prompt)
      self.assertEqual(sound.current_sound_frame, 0)
      pcm = sound.get_sound_data(16)
      self.assertTrue(np.all(pcm > 0))
      self.assertEqual(sound.current_sound_frame, 16)
      with patch('openpilot.selfdrive.ui.soundd.time.monotonic_ns', return_value=now + 100_000_000):
        sound.get_audible_alert(sm)
      self.assertEqual(sound.current_sound_frame, 16)  # repeated prompt cannot restart the sample
      self.assertTrue(np.all(sound.get_sound_data(16) == 0))

  def test_deadline_does_not_extend_on_healthy_frames(self):
    d = AvailabilityWarningDelivery()
    d.observe(session='s', drive=1, now_ns=100, selected=True, requested_until_ns=400_000_100)
    d.observe(session='s', drive=1, now_ns=300_000_100, selected=False, requested_until_ns=999_000_100)
    self.assertTrue(d.pending(session='s', drive=1, now_ns=400_000_100, audible_none=True, priority=0, low_priority=1))
    self.assertFalse(d.pending(session='s', drive=1, now_ns=400_000_101, audible_none=True, priority=0, low_priority=1))

  def test_never_issued_stays_quiet(self):
    d = AvailabilityWarningDelivery()
    d.observe(session='s', drive=1, now_ns=100, selected=False, requested_until_ns=400_000_100)
    self.assertFalse(d.pending(session='s', drive=1, now_ns=100, audible_none=True, priority=0, low_priority=1))

  def test_urgent_and_existing_audible_preempt(self):
    d = AvailabilityWarningDelivery()
    d.observe(session='s', drive=1, now_ns=100, selected=True, requested_until_ns=400_000_100)
    self.assertFalse(d.pending(session='s', drive=1, now_ns=101, audible_none=True, priority=2, low_priority=1))
    self.assertFalse(d.pending(session='s', drive=1, now_ns=101, audible_none=False, priority=0, low_priority=1))

  def test_context_changes_between_observation_and_publication_deny(self):
    d = AvailabilityWarningDelivery()
    d.observe(session='s', drive=1, now_ns=100, selected=True, requested_until_ns=400_000_100)
    for session,drive in [('new',1),('s',2),('s',0),(None,1)]:
      with self.subTest(session=session,drive=drive):
        self.assertFalse(d.pending(session=session, drive=drive, now_ns=101, audible_none=True, priority=0, low_priority=1))

  def test_clock_rollback_and_offroad_reset(self):
    d = AvailabilityWarningDelivery()
    d.observe(session='s', drive=1, now_ns=100, selected=True, requested_until_ns=400_000_100)
    d.observe(session='s', drive=1, now_ns=99, selected=False, requested_until_ns=400_000_100)
    self.assertFalse(d.pending(session='s', drive=1, now_ns=101, audible_none=True, priority=0, low_priority=1))
    d.observe(session='s', drive=1, now_ns=102, selected=True, requested_until_ns=400_000_102)
    d.observe(session='s', drive=0, now_ns=103, selected=False, requested_until_ns=400_000_102)
    self.assertFalse(d.pending(session='s', drive=1, now_ns=104, audible_none=True, priority=0, low_priority=1))

  def test_new_episode_after_deadline_can_issue(self):
    d = AvailabilityWarningDelivery()
    d.observe(session='s', drive=1, now_ns=100, selected=True, requested_until_ns=400_000_100)
    d.observe(session='s', drive=1, now_ns=500_000_100, selected=True, requested_until_ns=900_000_100)
    self.assertTrue(d.pending(session='s', drive=1, now_ns=550_000_100, audible_none=True, priority=0, low_priority=1))
