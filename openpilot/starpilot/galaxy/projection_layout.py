"""Authenticated Galaxy owner for a separate, negotiated AA layout document."""
import hashlib
import json
from pathlib import Path

from openpilot.starpilot.galaxy.onroad_layout import LayoutChanged
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.system.android_auto.display_profile import SCREEN_PATH, MAX_BYTES as SCREEN_MAX_BYTES, validate_screen
from openpilot.starpilot.system.android_auto.projection_layout import (
  DOCUMENT_KEY, MAX_BYTES, ProjectionLayoutSource, decode_layout, default_layout, layout_metadata, validate_layout,
)
from openpilot.starpilot.ui.onroad_customization import read_customization


class _ScreenSource:
  def __init__(self, path):
    self.path = Path(path)

  def get_param_path(self, _key):
    return str(self.path)


def _revision(screen, document):
  digest = hashlib.sha256(b'StarPilot projection layout v1\0')
  for raw in (screen, document):
    digest.update(b'absent\0' if raw is None else b'present\0' + len(raw).to_bytes(8, 'big') + raw)
  return digest.hexdigest()


def _unique(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError('Duplicate screen field')
    result[key] = value
  return result


class ProjectionLayoutOwner:
  def __init__(self, params, parked, source=None, screen_path=None):
    self.params, self.parked = params, parked
    self.source = source if source is not None else ProjectionLayoutSource()
    self.screen_source = _ScreenSource(screen_path if screen_path is not None else SCREEN_PATH)

  def _screen(self):
    raw, readable = read_saved(self.screen_source, 'screen', SCREEN_MAX_BYTES)
    screen = None
    if readable and raw is not None:
      try:
        screen = validate_screen(json.loads(raw, object_pairs_hook=_unique))
      except (ValueError, TypeError, UnicodeError, RecursionError):
        pass
    return raw, readable, screen

  def snapshot(self):
    screen_raw, screen_readable, screen = self._screen()
    raw, readable = read_saved(self.source, DOCUMENT_KEY, MAX_BYTES)
    defaults = default_layout(screen) if screen is not None else None
    document = defaults
    valid = False
    if readable and raw is not None and screen is not None:
      try:
        document = decode_layout(raw, screen)
        valid = True
      except (ValueError, TypeError, UnicodeError, RecursionError):
        pass
    enabled = self.params.get_bool('AndroidAutoEnabled')
    available = bool(enabled and screen is not None and screen_readable and readable)
    reason = ('Enable Android Auto to edit its layout' if not enabled else
              'Connect Android Auto once to obtain the actual screen' if screen is None else
              'Saved projection layout is unavailable' if not readable else None)
    base = read_customization(self.params)
    return {'version': 1, 'document': document, 'defaults': defaults,
            'metadata': layout_metadata(screen) if screen is not None else None,
            'screen': screen, 'revision': _revision(screen_raw, raw),
            'available': available, 'editable': bool(available and self.parked()), 'valid': valid,
            'reason': reason, 'retainedLayout': raw is not None,
            'colors': {'palette': base['palette'], 'widgetColors': base['widgetColors']['large'],
                       'roadColors': base['roadColors']['large']}}

  def save(self, payload, *, session_valid):
    if type(payload) is not dict or set(payload) != {'revision', 'document'} or type(payload['revision']) is not str:
      raise ValueError('Invalid projection layout request')
    screen_raw, screen_readable, screen = self._screen()
    raw, readable = read_saved(self.source, DOCUMENT_KEY, MAX_BYTES)
    if not readable or not screen_readable or screen is None:
      raise LayoutChanged('Projection screen or layout is unavailable; reconnect and reload')
    if payload['revision'] != _revision(screen_raw, raw):
      raise LayoutChanged('Projection screen or layout changed; reload before saving')
    document = validate_layout(payload['document'], screen)
    encoded = json.dumps(document, separators=(',', ':'), allow_nan=False).encode()

    def authorized():
      if not session_valid() or not self.parked() or not self.params.get_bool('AndroidAutoEnabled'):
        return False
      current, current_readable, current_screen = self._screen()
      return current_readable and current_screen is not None and current == screen_raw

    if not authorized():
      raise LayoutChanged('Projection layout requires a current session, parked device and unchanged screen')
    self.source.prepare()
    result = commit_exact(self.source, key=DOCUMENT_KEY, max_bytes=MAX_BYTES, raw=encoded, expected=raw,
                          authorized=authorized, temp_prefix='.projection-layout-')
    if not result.committed or not result.verified:
      raise LayoutChanged('Projection layout could not be saved; reload while parked')
    return self.snapshot()
