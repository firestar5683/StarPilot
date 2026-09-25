import unittest

from openpilot.starpilot.longitudinal.profile_document import default_personality_profiles, update_personality_profile


class TrafficDocumentBoundsTests(unittest.TestCase):
  def test_traffic_braking_accepts_existing_runtime_floor_without_relaxing_ordinary_profiles(self):
    profiles = default_personality_profiles(False)
    updated = update_personality_profile(profiles, "traffic", "braking", "custom", [0.35] * 10, False)
    self.assertEqual(updated["traffic"]["braking"]["curve"], [0.35] * 10)
    with self.assertRaises(ValueError):
      update_personality_profile(profiles, "standard", "braking", "custom", [0.35] * 10, False)
    with self.assertRaises(ValueError):
      update_personality_profile(profiles, "traffic", "braking", "custom", [0.34] * 10, False)


if __name__ == "__main__":
  unittest.main()
