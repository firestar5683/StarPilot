from openpilot.starpilot.common.safe_mode import SAFE_MODE_MANAGED_KEYS


def test_safe_mode_manages_lane_centering_settings():
  assert {
    "CameraOffset",
    "LaneCentering",
    "LaneCenteringPauseOnSignal",
    "LaneCenteringE2EAuthority",
    "LaneCenterOffset",
  } <= set(SAFE_MODE_MANAGED_KEYS)
