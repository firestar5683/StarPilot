"""One validated, exact-source saved Sentry document replacement."""

from collections.abc import Callable

from openpilot.starpilot.saved_document import WriteResult, commit_exact
from openpilot.starpilot.sentry_mode.preferences import KEY, MAX_BYTES, decode, encode


def commit(params, raw: bytes, expected: bytes | None, authorized: Callable[[], bool]) -> WriteResult:
  preferences = decode(raw) if type(raw) is bytes else None
  if preferences is None or encode(preferences) != raw:
    return WriteResult(False, False)
  return commit_exact(params, key=KEY, max_bytes=MAX_BYTES, raw=raw, expected=expected,
                      authorized=authorized, temp_prefix=".tmp_sentry_")
