"""Real disposable Params tests for the six saved Ioniq media assignments."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from openpilot.common.params import Params
from openpilot.starpilot.conditional_mode.button_actions import (
  CONFIG_KEY, MEDIA_KEYS, RUNTIME_KEYS, SAFE_KEY, capture_sources, commit_assignment,
  display_action, media_capability, runtime_map_ready,
)
from openpilot.starpilot.conditional_mode.manual import read_button_map
from openpilot.starpilot.saved_source import read_saved


def qualified_cp():
  cp = interfaces[CAR.HYUNDAI_IONIQ_6].get_non_essential_params(CAR.HYUNDAI_IONIQ_6)
  cp.flags = int(cp.flags | HyundaiFlags.CANFD_LKA_STEER_MSG)
  cp.openpilotLongitudinalControl = True
  return cp


class ButtonActionsTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.parked = True
    self.cp = qualified_cp()

  def snapshot(self):
    config, _ = read_saved(self.params, CONFIG_KEY, 4096)
    safe, _ = read_saved(self.params, SAFE_KEY, 8)
    return capture_sources(self.params, config, safe)

  def write(self, key, choice, sources=None):
    sources = sources or self.snapshot()
    cp = media_capability(self.cp)
    return commit_assignment(self.params, key=key, choice=choice, expected=sources.raw(key),
                             dependencies=sources.dependencies,
                             authorized=lambda: self.parked and cp is not None and media_capability(self.cp) == cp)

  def test_exact_platform_and_all_six_real_saved_actions(self):
    self.assertIsNotNone(media_capability(self.cp))
    wrong = qualified_cp()
    wrong.flags = int(wrong.flags & ~HyundaiFlags.CANFD_LKA_STEER_MSG)
    self.assertIsNone(media_capability(wrong))
    wrong = qualified_cp()
    wrong.passive = True
    self.assertIsNone(media_capability(wrong))
    self.assertTrue(runtime_map_ready(self.snapshot()))
    for key in MEDIA_KEYS:
      with self.subTest(key=key):
        self.assertTrue(self.write(key, "Cycle conditional mode").verified)
        self.assertEqual(read_saved(self.params, key, 8), (b"5", True))
        self.assertEqual(getattr(read_button_map(self.params, include_ioniq_media=True),
                                 {"ModeButtonControl": "mode", "LongModeButtonControl": "mode_long",
                                  "VeryLongModeButtonControl": "mode_very_long", "StarButtonControl": "custom",
                                  "LongStarButtonControl": "custom_long",
                                  "VeryLongStarButtonControl": "custom_very_long"}[key]), 5)
        self.assertTrue(self.write(key, "Off").verified)
        self.assertEqual(read_saved(self.params, key, 8), (b"0", True))
        self.assertTrue(self.write(key, "Toggle traffic mode").verified)
        self.assertEqual(read_saved(self.params, key, 8), (b"6", True))
        self.assertEqual(display_action(b"6")[:2], ("Toggle traffic mode", ("Off", "Cycle conditional mode", "Toggle traffic mode")))
        self.assertTrue(self.write(key, "Off").verified)

  def test_corrupt_or_unsupported_saved_value_requires_explicit_repair(self):
    key = MEDIA_KEYS[0]
    Path(self.params.get_param_path(key)).write_bytes(b"05")
    self.assertEqual(display_action(self.snapshot().raw(key)), ("Unsupported saved action", (), "Off"))
    self.assertFalse(self.write(key, "Cycle conditional mode").committed)
    self.assertTrue(self.write(key, "Off").verified)
    Path(self.params.get_param_path(key)).write_bytes(b"14")
    self.assertEqual(display_action(self.snapshot().raw(key))[2], "Off")
    self.assertFalse(self.write(key, "Cycle conditional mode").committed)
    self.assertTrue(self.write(key, "Off").verified)
    self.assertFalse(self.write(key, "Pause longitudinal").committed)
    self.assertFalse(self.write("CancelButtonControl", "Off").committed)

  def test_invalid_saved_config_or_safe_mode_cannot_bypass_page(self):
    key = MEDIA_KEYS[0]
    Path(self.params.get_param_path(CONFIG_KEY)).write_bytes(b'{"version":9}')
    self.assertFalse(self.write(key, "Off").committed)
    self.assertFalse(self.write(key, "Cycle conditional mode").committed)
    Path(self.params.get_param_path(CONFIG_KEY)).unlink()
    Path(self.params.get_param_path(SAFE_KEY)).write_bytes(b"yes")
    self.assertFalse(self.write(key, "Off").committed)

  def test_exact_sources_parked_cp_and_cancel_dependency(self):
    key = MEDIA_KEYS[0]
    captured = self.snapshot()
    Path(self.params.get_param_path("LongStarButtonControl")).write_bytes(b"5")
    self.assertFalse(self.write(key, "Cycle conditional mode", captured).committed)
    self.assertIsNone(read_saved(self.params, key, 8)[0])
    captured = self.snapshot()
    Path(self.params.get_param_path("CancelButtonControl")).write_bytes(b"5")
    self.assertFalse(runtime_map_ready(self.snapshot()))
    self.assertIsNone(read_button_map(self.params, include_ioniq_media=True))
    self.assertFalse(self.write(key, "Cycle conditional mode", captured).committed)
    captured = self.snapshot()
    self.params.put_bool(SAFE_KEY, True, block=True)
    self.assertFalse(self.write(key, "Cycle conditional mode", captured).committed)
    self.parked = False
    self.assertFalse(self.write(key, "Cycle conditional mode").committed)
    self.parked = True
    self.cp.flags = int(self.cp.flags & ~HyundaiFlags.CANFD_LKA_STEER_MSG)
    self.assertFalse(self.write(key, "Cycle conditional mode").committed)

  def test_unreadable_source_and_commit_uncertainty(self):
    key = MEDIA_KEYS[0]
    path = Path(self.params.get_param_path(key))
    path.write_bytes(b"5" * 9)
    self.assertFalse(self.snapshot().readable)
    self.assertFalse(self.write(key, "Off").committed)
    self.assertEqual(path.read_bytes(), b"5" * 9)
    path.write_bytes(b"0")
    from openpilot.starpilot import saved_document
    with patch.object(saved_document.os, "fsync", side_effect=[None, OSError("post-rename failure")]):
      result = self.write(key, "Cycle conditional mode")
    self.assertTrue(result.committed)
    self.assertFalse(result.verified)
    self.assertEqual(path.read_bytes(), b"5")

  def test_all_dependencies_captured_once_and_nonregular_source(self):
    sources = self.snapshot()
    self.assertEqual(tuple(name for name, _ in sources.dependencies), (CONFIG_KEY, SAFE_KEY, *RUNTIME_KEYS))
    key = MEDIA_KEYS[0]
    Path(self.params.get_param_path(key)).mkdir()
    self.assertFalse(self.snapshot().readable)
    self.assertFalse(self.write(key, "Cycle conditional mode").committed)

  def test_stage_to_lock_rechecks_parked_cp_and_config(self):
    from openpilot.starpilot import saved_document
    key = MEDIA_KEYS[0]
    original_fsync = saved_document.os.fsync
    for change in ("parked", "cp", "config"):
      with self.subTest(change=change):
        self.parked = True
        self.cp = qualified_cp()
        config_path = Path(self.params.get_param_path(CONFIG_KEY))
        config_path.unlink(missing_ok=True)
        def change_at_stage(fd, scenario=change, path=config_path):
          result = original_fsync(fd)
          if scenario == "parked":
            self.parked = False
          elif scenario == "cp":
            self.cp.flags = int(self.cp.flags & ~HyundaiFlags.CANFD_LKA_STEER_MSG)
          else:
            path.write_bytes(b'{"version":9}')
          return result
        with patch.object(saved_document.os, "fsync", side_effect=change_at_stage):
          self.assertFalse(self.write(key, "Cycle conditional mode").committed)
        self.assertFalse(Path(self.params.get_param_path(key)).exists())


if __name__ == "__main__":
  unittest.main()


def test_gm_distance_configuration_is_exact_and_preserves_other_actions(tmp_path):
  from opendbc.car.gm.tests.test_bolt_pedal import params as pedal_params
  from opendbc.car.gm.tests.test_ascm_intercept import params as ascm_params
  from opendbc.car.gm.values import CAR, PEDAL_BOLT_CAR
  from openpilot.starpilot.conditional_mode.button_actions import distance_capability
  from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
  from openpilot.starpilot.ui.feature_settings_state import FeaturePage
  params = Params(str(tmp_path))
  for cp in [*(pedal_params(car, setting=True, pedal=True) for car in PEDAL_BOLT_CAR),
             ascm_params(CAR.CHEVROLET_BOLT_EUV, alpha=True), ascm_params(CAR.CHEVROLET_VOLT, radar=True),
             ascm_params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True)]:
    assert distance_capability(cp) is not None
    owner = FeatureSettingsOwner(params, lambda group: True, vehicle_fingerprint=lambda cp=cp: cp.carFingerprint, vehicle_params=lambda cp=cp: cp)
    rows = owner.snapshot(FeaturePage.WHEEL, parked=True, system_long=True, lateral_context=False, metric=False).rows
    rows = [row for row in rows if row.key.startswith('conditional:button:')]
    assert len(rows) == 3
    assert all(row.available and row.choices == ('Off', 'Toggle traffic mode') for row in rows)
  for car in (CAR.CHEVROLET_BOLT_EUV, CAR.CHEVROLET_VOLT_CAMERA, CAR.CHEVROLET_VOLT_2019):
    assert distance_capability(ascm_params(car)) is None
  params.put('DistanceButtonControl', 3, block=True)
  rows = owner.snapshot(FeaturePage.WHEEL, parked=True, system_long=True, lateral_context=False, metric=False).rows
  row = next(row for row in rows if row.key == 'conditional:button:DistanceButtonControl')
  assert row.source == b'3' and not row.choices and row.repair_value == 'Off'
  assert params.get('DistanceButtonControl') == 3
