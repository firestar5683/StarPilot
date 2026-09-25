from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from opendbc.car.toyota.interface import CarInterface as ToyotaCarInterface
from opendbc.car.toyota.values import CAR as TOYOTA_CAR
from openpilot.starpilot.longitudinal.lead_approach_runtime import KEY, LeadApproachPreferences
from openpilot.starpilot.saved_source import read_saved


class FileParams:
  def __init__(self, root):
    self.root = Path(root)

  def get_param_path(self, key):
    return str(self.root / key)


class TestLeadApproachPreferences(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = FileParams(temporary.name)
    self.cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    self.assertTrue(self.cp.openpilotLongitudinalControl)
    self.assertTrue(self.cp.pcmCruise)
    self.owner = LeadApproachPreferences(self.params)
    self.now = 2_000_000_000

  def write(self, key, raw):
    path = Path(self.params.get_param_path(key))
    if raw is None:
      path.unlink(missing_ok=True)
    else:
      path.write_bytes(raw)

  def sample(self, *, now=None, drive=1_000_000_000):
    return self.owner.sample(self.cp, self.now if now is None else now, drive)

  def test_exact_opt_in_safe_mode_and_bounded_refresh(self):
    for raw in (None, b"0", b"true", b"1\n", b"1" * 20):
      with self.subTest(raw=raw):
        self.write(KEY, raw)
        self.assertIsNone(self.sample())
        self.now += self.owner.REFRESH_NS
    self.write(KEY, b"1")
    key = self.sample()
    self.assertIsNotNone(key)
    self.assertEqual(key.drive_id, 1_000_000_000)
    for safe in (b"1", b"invalid", b"", b"1" * 20):
      with self.subTest(safe=safe):
        self.write("SafeMode", safe)
        self.now += self.owner.REFRESH_NS
        self.assertIsNone(self.sample())
    self.write("SafeMode", b"0")
    self.now += self.owner.REFRESH_NS
    self.assertEqual(self.sample(), key)
    self.write(KEY, b"0")
    self.assertEqual(self.sample(), key)
    self.now += self.owner.REFRESH_NS
    self.assertIsNone(self.sample())
    self.write(KEY, b"1")
    self.now += self.owner.REFRESH_NS
    self.assertEqual(self.sample(), key)

  def test_bounded_reads_and_forced_context_refresh(self):
    self.write(KEY, b"1")
    with patch("openpilot.starpilot.longitudinal.lead_approach_runtime.read_saved", wraps=read_saved) as source:
      first = self.sample()
      self.assertEqual(source.call_count, 2)
      for delta in (50_000_000, 100_000_000, 500_000_000, 999_000_000):
        self.assertEqual(self.sample(now=self.now + delta), first)
      self.assertEqual(source.call_count, 2)
      self.now += self.owner.REFRESH_NS
      self.assertEqual(self.sample(), first)
      self.assertEqual(source.call_count, 4)
      new_drive = self.sample(drive=1_100_000_000)
      self.assertNotEqual(new_drive, first)
      self.assertEqual(source.call_count, 6)
      self.cp.carVin = "changed-vin"
      changed_cp = self.sample(drive=1_100_000_000)
      self.assertNotEqual(changed_cp, new_drive)
      self.assertEqual(source.call_count, 8)

  def test_backwards_clock_and_read_failure_clear_cached_positive(self):
    self.write(KEY, b"1")
    first = self.sample()
    self.assertIsNotNone(first)
    self.write(KEY, b"0")
    self.assertEqual(self.sample(now=self.now + 100_000_000), first)
    self.now -= 1
    with patch("openpilot.starpilot.longitudinal.lead_approach_runtime.read_saved", wraps=read_saved) as source:
      self.assertIsNone(self.sample())
      self.assertEqual(source.call_count, 1)
    self.write(KEY, b"1")
    self.now += self.owner.REFRESH_NS
    self.assertIsNotNone(self.sample())
    self.now += self.owner.REFRESH_NS
    with patch("openpilot.starpilot.longitudinal.lead_approach_runtime.read_saved", return_value=(b"", False)) as source:
      self.assertIsNone(self.sample())
      self.assertEqual(source.call_count, 1)
    self.now += self.owner.REFRESH_NS
    self.assertIsNotNone(self.sample())
    self.now += self.owner.REFRESH_NS
    with patch("openpilot.starpilot.longitudinal.lead_approach_runtime.read_saved", side_effect=OSError("source unavailable")):
      self.assertIsNone(self.sample())

  def test_current_drive_and_cp_capability_are_required(self):
    self.write(KEY, b"1")
    key = self.sample()
    self.assertIsNotNone(key)
    next_drive = self.sample(drive=1_100_000_000)
    self.assertNotEqual(next_drive, key)
    self.assertNotEqual(next_drive.settings_fingerprint, key.settings_fingerprint)
    for now, drive in ((0, 1), (1, 0), (1, 2), (1.0, 1), (2, True)):
      with self.subTest(now=now, drive=drive):
        self.assertIsNone(self.sample(now=now, drive=drive))
    for field in ("openpilotLongitudinalControl", "passive", "dashcamOnly", "notCar"):
      with self.subTest(field=field):
        setattr(self.cp, field, field != "openpilotLongitudinalControl")
        self.assertIsNone(self.sample())
        setattr(self.cp, field, field == "openpilotLongitudinalControl")
    self.cp.carFingerprint = ""
    self.assertIsNone(self.sample())

  def test_second_real_brand_is_eligible_without_profile_master(self):
    self.write(KEY, b"1")
    honda = self.sample()
    toyota = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_COROLLA_TSS2)
    self.assertTrue(toyota.openpilotLongitudinalControl)
    other = self.owner.sample(toyota, 2_000_000_000, 1_000_000_000)
    self.assertIsNotNone(other)
    self.assertNotEqual(other.settings_fingerprint, honda.settings_fingerprint)

  def test_unreadable_saved_source_is_inert(self):
    self.write(KEY, b"1")
    path = Path(self.params.get_param_path(KEY))
    path.unlink()
    path.symlink_to("SafeMode")
    self.assertIsNone(self.sample())


if __name__ == "__main__":
  unittest.main()
