"""Published large-model loss uses the same soft-disable event for either owner."""
import unittest
from types import SimpleNamespace

from openpilot.cereal import messaging
from openpilot.selfdrive.selfdrived.events import Events, ET, EventName
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD


class Sources:
  def __init__(self):
    self.data = {name: getattr(messaging.new_message(name), name) for name in ('modelV2', 'deviceState', 'carControl')}
    self.seen = dict.fromkeys(self.data, True)
    self.alive = dict.fromkeys(self.data, True)
    self.valid = dict.fromkeys(self.data, True)

  def __getitem__(self, key):
    return self.data[key]


def fixture(chestnut=None):
  drive = SelfdriveD.__new__(SelfdriveD)
  vars(drive)['params'] = SimpleNamespace(get=lambda key: chestnut)
  vars(drive)['sm'] = Sources()
  drive.enabled = True
  drive.big_model_active = drive.big_model_chestnut = drive.big_model_failed = False
  drive.events = Events()
  return drive


class TestBigModelStatus(unittest.TestCase):
  def test_actual_remote_big_then_small_is_soft_disable_without_chestnut_claim(self):
    drive = fixture()
    drive.sm['modelV2'].big = True
    self.assertFalse(drive.update_big_model_status())
    self.assertTrue(drive.big_model_active)
    self.assertFalse(drive.big_model_chestnut)
    drive.sm['modelV2'].big = False
    self.assertTrue(drive.update_big_model_status())
    self.assertIn(EventName.bigModelFailed, drive.events.names)
    self.assertTrue(drive.events.contains(ET.SOFT_DISABLE))
    self.assertTrue(drive.events.contains(ET.PERMANENT))

  def test_remote_execution_does_not_inherit_failed_chestnut_startup_marker(self):
    drive = fixture(False)
    drive.sm['modelV2'].big = True
    self.assertFalse(drive.update_big_model_status())
    self.assertFalse(drive.big_model_chestnut)
    drive.sm['modelV2'].big = False
    self.assertTrue(drive.update_big_model_status())
    self.assertTrue(drive.events.contains(ET.SOFT_DISABLE))

  def test_stale_or_invalid_remote_output_cannot_clear_failure(self):
    for field in ('alive', 'valid'):
      with self.subTest(field=field):
        drive = fixture()
        drive.sm['modelV2'].big = True
        self.assertFalse(drive.update_big_model_status())
        getattr(drive.sm, field)['modelV2'] = False
        self.assertTrue(drive.update_big_model_status())
        self.assertIn(EventName.bigModelFailed, drive.events.names)

  def test_local_small_and_unseen_remote_never_report_execution(self):
    drive = fixture()
    self.assertFalse(drive.update_big_model_status())
    self.assertFalse(drive.big_model_active)
    drive.sm['modelV2'].big = True
    drive.sm.seen['modelV2'] = False
    self.assertFalse(drive.update_big_model_status())
    self.assertFalse(drive.big_model_active)
    self.assertNotIn(EventName.bigModelFailed, drive.events.names)

  def test_actual_aol_lateral_execution_latches_until_all_axes_disengage(self):
    for axis in ('latActive', 'longActive'):
      with self.subTest(axis=axis):
        drive = fixture()
        drive.enabled = False
        setattr(drive.sm['carControl'], axis, True)
        drive.sm['modelV2'].big = True
        self.assertFalse(drive.update_big_model_status())
        self.assertTrue(drive.big_model_active)
        drive.sm['modelV2'].big = False
        self.assertTrue(drive.update_big_model_status())
        self.assertTrue(drive.events.contains(ET.SOFT_DISABLE))
        setattr(drive.sm['carControl'], axis, False)
        drive.update_big_model_status()
        self.assertFalse(drive.big_model_active)
        self.assertFalse(drive.update_big_model_status())

  def test_chestnut_startup_invalid_frame_does_not_report_run_failure(self):
    drive = fixture(True)
    drive.sm['deviceState'].chestnutPresent = True
    drive.sm['modelV2'].big = True
    drive.sm.valid['modelV2'] = False
    self.assertFalse(drive.update_big_model_status())
    self.assertFalse(drive.big_model_active)
    self.assertNotIn(EventName.bigModelFailed, drive.events.names)
    drive.sm.valid['modelV2'] = True
    self.assertFalse(drive.update_big_model_status())
    self.assertTrue(drive.big_model_active)
    drive.sm.valid['modelV2'] = False
    self.assertTrue(drive.update_big_model_status())
    self.assertIn(EventName.bigModelFailed, drive.events.names)

  def test_fresh_chestnut_execution_overrides_cached_negative_load_marker(self):
    drive = fixture(False)
    drive.sm['deviceState'].chestnutPresent = True
    drive.sm['modelV2'].big = True
    self.assertFalse(drive.update_big_model_status())
    self.assertTrue(drive.big_model_chestnut)
    drive.sm['modelV2'].big = False
    self.assertTrue(drive.update_big_model_status())
    self.assertIn(EventName.bigModelFailed, drive.events.names)

  def test_loaded_chestnut_with_initial_valid_small_output_is_a_failure(self):
    drive = fixture(True)
    drive.sm['deviceState'].chestnutPresent = True
    drive.sm['modelV2'].big = False
    self.assertTrue(drive.update_big_model_status())
    self.assertFalse(drive.big_model_active)
    self.assertIn(EventName.bigModelFailed, drive.events.names)

  def test_chestnut_failure_and_physical_loss_are_preserved(self):
    drive = fixture(False)
    drive.sm['deviceState'].chestnutPresent = True
    self.assertTrue(drive.update_big_model_status())
    self.assertIn(EventName.bigModelFailed, drive.events.names)
    drive = fixture(True)
    drive.sm['modelV2'].big = True
    drive.sm['deviceState'].chestnutPresent = True
    self.assertFalse(drive.update_big_model_status())
    drive.sm['deviceState'].chestnutPresent = False
    self.assertTrue(drive.update_big_model_status())
    self.assertIn(EventName.bigModelFailed, drive.events.names)
