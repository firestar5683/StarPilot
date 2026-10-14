from typing import cast
import json
import struct
import zlib

import pytest

from openpilot.starpilot.ui.layout_preview_renderer import _png_rgba, _straight_rgba
from openpilot.starpilot.ui.layout_preview_transport import _payload, validate_png, PreviewInvalid
from openpilot.starpilot.ui.onroad_customization import RUNTIME_PREVIEW_WIDGETS, customization_metadata, default_document


def test_widget_art_request_uses_same_validated_document_and_scene():
  request = {'document': default_document(), 'profile': 'compact', 'scene': 'cem_curve', 'art': True}
  assert _payload(request) == request
  for art in (False, None, 1, 'yes'):
    with pytest.raises(PreviewInvalid):
      _payload({**request, 'art': art})
  with pytest.raises(PreviewInvalid):
    _payload({**request, 'scene': 'live'})
  without = {key: value for key, value in request.items() if key != 'art'}
  assert _payload(without) == without


def test_widget_art_registry_is_shared_with_native_and_projection_metadata():
  from openpilot.starpilot.system.android_auto.projection_layout import layout_metadata_for_viewport
  metadata = customization_metadata()['profiles']
  for profile, ids in RUNTIME_PREVIEW_WIDGETS.items():
    assert metadata[profile]['runtimePreviewWidgets'] == list(ids)
    assert all(key in metadata[profile]['widgets'] for key in ids)
  assert layout_metadata_for_viewport((2880, 1080))['runtimePreviewWidgets'] == list(RUNTIME_PREVIEW_WIDGETS['large'])


def test_transparent_render_coverage_exports_straight_alpha_without_darkening():
  straight = _straight_rgba(bytes((128, 64, 0, 128, 9, 8, 7, 0, 255, 255, 255, 255)))
  assert straight == bytes((255, 128, 0, 128, 0, 0, 0, 0, 255, 255, 255, 255))
  # Browser source-over reconstructs the native scratch RGB to within one byte.
  assert [round(value * 128 / 255) for value in straight[:3]] == [128, 64, 0]


def test_sprite_sheet_metadata_and_pixels_share_actual_png_dimensions():
  metadata = {'version': 1, 'width': 2, 'height': 1, 'sprites': {'conditional_mode': {'x': 0, 'y': 0, 'width': 2, 'height': 1}}}
  pixels = bytes((255, 255, 255, 255, 0, 0, 0, 0))
  image = _png_rgba(2, 1, pixels, widget_art=metadata)
  assert validate_png(image) == image
  offset = 8
  chunks = {}
  while offset < len(image):
    size = struct.unpack('!I', image[offset:offset + 4])[0]
    tag, data = image[offset + 4:offset + 8], image[offset + 8:offset + 8 + size]
    assert zlib.crc32(tag + data) & 0xffffffff == struct.unpack('!I', image[offset + 8 + size:offset + 12 + size])[0]
    chunks[tag] = data
    offset += size + 12
  assert json.loads(chunks[b'tEXt'].split(b'\0', 1)[1]) == metadata
  assert zlib.decompress(chunks[b'IDAT']) == b'\0' + pixels


def test_static_compact_sample_settles_actual_hud_without_changing_live_blink_policy():
  from pathlib import Path
  from types import SimpleNamespace as NS
  from unittest.mock import Mock
  import time
  from openpilot.starpilot.ui.layout_preview_renderer import _Canvas, sample_state
  from openpilot.starpilot.ui.onroad_compact_widgets import CompactHudRenderer
  from openpilot.starpilot.ui.presentation import Profile
  from openpilot.starpilot.ui.onroad import OnroadView

  hud = CompactHudRenderer(Mock(), Path('/unused-assets'))
  canvas = _Canvas.__new__(_Canvas)
  canvas.profile = Profile.COMPACT
  canvas.view = cast(OnroadView, NS(compact_hud=hud, torque_bar=NS(_torque_filter=NS(x=0), _alpha_filter=NS(x=0))))
  sample = sample_state('engaged', default_document())
  for _ in range(2):
    canvas._settle(sample)
    assert hud._set_speed_opacity(sample, time.monotonic_ns()) == pytest.approx(1.)
  lateral_only = sample_state('aol', default_document())
  canvas._settle(lateral_only)
  assert hud._set_speed_opacity(lateral_only, time.monotonic_ns()) == 0.
