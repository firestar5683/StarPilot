import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.plannerd import conditional_handoff_for_frame, update_curve_frame
from openpilot.starpilot.conditional_mode.planner_host import ConditionalPlannerHost
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.preferences import SavedPreferences, encode_preferences
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner
from openpilot.starpilot.curve_speed.host import CurveHost
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import messages

NOW = 100_000_000_000
DRIVE = NOW - 10_000_000_000


class Frame(dict):
  def __init__(self):
    super().__init__(messages()[0])
    device = messaging.new_message('deviceState')
    device.deviceState.started = True
    device.deviceState.startedMonoTime = DRIVE
    self['deviceState'] = device.deviceState
    self.logMonoTime = dict.fromkeys(self, NOW - 5_000_000)
    self.valid = dict.fromkeys(self, True)
    self.alive = dict.fromkeys(self, True)
    self['carControl'].longActive = True
    self['carState'].canValid = True


class ConditionalHandoffTests(unittest.TestCase):
  def setUp(self):
    directory = tempfile.TemporaryDirectory()
    self.addCleanup(directory.cleanup)
    self.params = Params(directory.name)
    self.host = ConditionalPlannerHost(self.params)
    self.addCleanup(self.host.close)
    self.cp = CarInterface.get_non_essential_params(CAR.HYUNDAI_IONIQ_6)
    self.cp.openpilotLongitudinalControl = True
    self.sm = Frame()

  def key(self, now=NOW, drive=DRIVE):
    return conditional_handoff_for_frame(self.host, self.sm, self.cp, now, drive)

  def save(self, choice):
    self.params.put('ConditionalModeConfig', json.loads(encode_preferences(SavedPreferences(mode=choice))), block=True)

  def test_current_saved_owner_is_stable_across_bounded_refresh(self):
    key = self.key()
    self.assertEqual(key[2:], (DRIVE, ModeChoice.CEM.value))
    with patch('openpilot.starpilot.conditional_mode.runtime_settings.read_saved') as read:
      self.assertEqual(self.key(NOW + 100_000_000), key)
      read.assert_not_called()
    self.assertEqual(self.key(NOW + 500_000_000), key)
    self.save(ModeChoice.CCM)
    self.sm.logMonoTime['deviceState'] = NOW + 995_000_000
    changed = self.key(NOW + 1_000_000_000)
    self.assertEqual(changed[3], ModeChoice.CCM.value)
    self.assertNotEqual(changed[1], key[1])

  def test_stock_safe_mode_and_invalid_document_cannot_enable_restraint(self):
    for choice in ModeChoice:
      with self.subTest(choice=choice):
        self.save(choice)
        self.host.settings = ConditionalSettingsOwner(self.params)
        self.assertEqual(self.key() is None, choice is ModeChoice.STOCK)
    self.params.put_bool('SafeMode', True, block=True)
    self.host.settings = ConditionalSettingsOwner(self.params)
    self.assertIsNone(self.key())
    self.params.put_bool('SafeMode', False, block=True)
    Path(self.params.get_param_path('ConditionalModeConfig')).write_bytes(b'{')
    self.host.settings = ConditionalSettingsOwner(self.params)
    self.assertIsNone(self.key())

  def test_drive_identity_freshness_and_longitudinal_capability(self):
    self.assertIsNone(conditional_handoff_for_frame(None, self.sm, self.cp, NOW, DRIVE))
    for drive in (0, DRIVE - 1, NOW + 1):
      self.assertIsNone(self.key(drive=drive))
    for field in ('passive', 'dashcamOnly'):
      setattr(self.cp, field, True)
      self.assertIsNone(self.key())
      setattr(self.cp, field, False)
    self.cp.openpilotLongitudinalControl = False
    self.assertIsNone(self.key())
    self.cp.openpilotLongitudinalControl = True
    self.sm['deviceState'].started = False
    self.assertIsNone(self.key())
    self.sm['deviceState'].started = True
    for stamps in (self.sm.valid, self.sm.alive):
      stamps['deviceState'] = False
      self.assertIsNone(self.key())
      stamps['deviceState'] = True
    for stamp in (NOW + 1, NOW - 1_000_000_001):
      self.sm.logMonoTime['deviceState'] = stamp
      self.assertIsNone(self.key())
    self.sm.logMonoTime['deviceState'] = NOW - 750_000_000
    self.assertIsNotNone(self.key(), 'Device freshness must follow its two-Hz publisher, not the model rate')

  def test_actual_planner_receives_same_owner_with_and_without_curve_host(self):
    key = self.key()
    for curve in (None, CurveHost(enabled=False, replay=True)):
      with self.subTest(curve=curve):
        planner = LongitudinalPlanner(self.cp, init_v=20.0)
        with patch.object(planner, 'update', wraps=planner.update) as update:
          update_curve_frame(planner, self.sm, self.cp, NOW, host=curve, conditional_handoff=key)
          self.assertEqual(update.call_args.kwargs['conditional_handoff'], key)
          self.assertEqual(planner.mpc.solution_status, 0)
        self.assertEqual(planner.experimental_release.key, key)


if __name__ == '__main__':
  unittest.main()
