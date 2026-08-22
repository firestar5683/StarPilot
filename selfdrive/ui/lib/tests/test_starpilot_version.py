from openpilot.selfdrive.ui.lib.starpilot_version import (
  DEFAULT_HOME_SCREEN_NAME,
  HOME_SCREEN_NAME_MAX_LENGTH,
  normalize_home_screen_name,
)


def test_home_screen_name_defaults_and_truncates():
  assert normalize_home_screen_name("") == DEFAULT_HOME_SCREEN_NAME
  assert normalize_home_screen_name("  Custom Name  ") == "Custom Name"
  assert len(normalize_home_screen_name("abcdefghijklmnop")) == HOME_SCREEN_NAME_MAX_LENGTH
