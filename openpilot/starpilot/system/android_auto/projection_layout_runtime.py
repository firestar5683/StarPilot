"""Read a saved projection layout once per connection, never in the frame loop."""
from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.system.android_auto.projection_layout import (
  DOCUMENT_KEY, MAX_BYTES, ProjectionLayoutSource, default_layout_for_viewport, decode_layout_for_viewport,
)


def load_projection_layout(viewport, source=None):
  raw, readable = read_saved(source or ProjectionLayoutSource(), DOCUMENT_KEY, MAX_BYTES)
  if not readable or raw is None:
    return default_layout_for_viewport(viewport)
  try:
    return decode_layout_for_viewport(raw, viewport)
  except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
    return default_layout_for_viewport(viewport)
