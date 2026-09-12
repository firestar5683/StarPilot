"""Keep native screen controls usable after a rejected or failed settings write."""

from collections.abc import Callable

from openpilot.common.params import UnknownKeyName


def try_screen_setting(write: Callable[[], object], on_error: Callable[[], None]) -> bool:
  try:
    write()
  except (OSError, ValueError, UnknownKeyName):
    on_error()
    return False
  return True
