"""Separate AA placement document; native large/compact schemas stay fixed."""
import copy
import json
import math
from pathlib import Path

from openpilot.starpilot.system.android_auto.identity import DATA_DIR
from openpilot.starpilot.system.android_auto.display_profile import screen_geometry
from openpilot.starpilot.ui.onroad_customization import customization_metadata, WHEEL_SIZES
from openpilot.starpilot.ui.onroad_torque_geometry import maximum_footprint

MAX_BYTES = 16384
DOCUMENT_KEY = 'projection'
DOCUMENT_PATH = DATA_DIR / 'layouts/document.json'


class ProjectionLayoutSource:
  """Path adapter for existing read_saved/commit_exact file ownership semantics."""
  def __init__(self, path=None):
    self.path = Path(path or DOCUMENT_PATH)

  def get_param_path(self, key):
    if key != DOCUMENT_KEY:
      raise ValueError('Unknown projection document')
    return str(self.path)

  def prepare(self):
    self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)


def layout_metadata(screen):
  geometry = screen_geometry(screen)
  return layout_metadata_for_viewport((geometry.logical_width, geometry.logical_height))


def layout_metadata_for_viewport(viewport):
  width, height = viewport
  if any(type(n) is not int for n in viewport) or not 1860 <= width <= 4096 or not 1080 <= height <= 2160:
    raise ValueError('Invalid projection canvas')
  profile = copy.deepcopy(customization_metadata()['profiles']['large'])
  profile.update(label='Android Auto', width=width, height=height,
                 bounds={'x': 30, 'y': 30, 'width': width - 60, 'height': height - 60},
                 reservedZones=[], inputZones=[])
  profile.pop('inputZonePriority', None)
  widgets = profile['widgets']
  widgets['current_speed']['default']['x'] += (width - 1860) / 2
  widgets['steering_wheel']['default']['x'] += width - 1860
  widgets['driver_monitor']['default']['y'] += height - 1080
  x, y, w, h = maximum_footprint(30, 30, width - 60, height - 60, width)
  widgets['torque_bar'].update(width=w, height=h)
  widgets['torque_bar']['default'].update(x=x, y=y)
  return profile


def default_layout(screen):
  geometry = screen_geometry(screen)
  return default_layout_for_viewport((geometry.logical_width, geometry.logical_height))


def default_layout_for_viewport(viewport):
  metadata = layout_metadata_for_viewport(viewport)
  return {'version': 1, 'canvas': {key: metadata[key] for key in ('width', 'height')},
          'widgets': {key: {**widget['default'], **({'size': 192} if key == 'steering_wheel' else {})}
                      for key, widget in metadata['widgets'].items()}}


def validate_layout(value, screen):
  geometry = screen_geometry(screen)
  return validate_layout_for_viewport(value, (geometry.logical_width, geometry.logical_height))


def validate_layout_for_viewport(value, viewport):
  metadata = layout_metadata_for_viewport(viewport)
  if (type(value) is not dict or set(value) != {'version', 'canvas', 'widgets'} or
      type(value['version']) is not int or value['version'] != 1 or
      value['canvas'] != {key: metadata[key] for key in ('width', 'height')} or
      type(value['widgets']) is not dict or set(value['widgets']) != set(metadata['widgets'])):
    raise ValueError('Projection layout does not match saved screen')
  result = copy.deepcopy(value)
  bounds = metadata['bounds']
  for key, widget in metadata['widgets'].items():
    placement = value['widgets'][key]
    fields = {'x', 'y', 'enabled'} | ({'size'} if key == 'steering_wheel' else set())
    if type(placement) is not dict or set(placement) != fields or type(placement['enabled']) is not bool:
      raise ValueError('Invalid projection widget')
    size = placement.get('size', 192)
    if key == 'steering_wheel' and (type(size) is not int or not WHEEL_SIZES['large'][0] <= size <= WHEEL_SIZES['large'][2]):
      raise ValueError('Invalid steering wheel size')
    for axis, extent in (('x', 'width'), ('y', 'height')):
      number = placement[axis]
      dimension = size if key == 'steering_wheel' else widget[extent]
      if (type(number) not in (int, float) or not math.isfinite(number) or
          not bounds[axis] <= number <= bounds[axis] + bounds[extent] - dimension):
        raise ValueError('Projection widget outside screen')
  if len(json.dumps(result, separators=(',', ':'), allow_nan=False).encode()) > MAX_BYTES:
    raise ValueError('Projection layout too large')
  return result


def decode_layout(raw, screen):
  geometry = screen_geometry(screen)
  return decode_layout_for_viewport(raw, (geometry.logical_width, geometry.logical_height))


def decode_layout_for_viewport(raw, viewport):
  def unique(pairs):
    result = {}
    for key, value in pairs:
      if key in result:
        raise ValueError('Duplicate projection field')
      result[key] = value
    return result
  if len(raw) > MAX_BYTES:
    raise ValueError('Projection layout too large')
  return validate_layout_for_viewport(json.loads(raw, object_pairs_hook=unique), viewport)


def projection_customization(document, base_customization):
  """Convert validated AA placements to offsets consumed by the projected view.

  The view already applies its center/right/bottom anchors. Cancel those anchor
  shifts here so the independent saved coordinates are applied exactly once.
  Colors and native compact placement are copied from the caller's document.
  """
  from openpilot.starpilot.ui.onroad_customization import PROFILES
  width, height = document['canvas']['width'], document['canvas']['height']
  shifts = {'current_speed': ((width - 1860) / 2, 0),
            'steering_wheel': (width - 1860, 0), 'driver_monitor': (0, height - 1080)}
  native = PROFILES['large']['widgets']
  assert isinstance(native, dict)
  tx, ty, _, _ = maximum_footprint(30, 30, width - 60, height - 60, width)
  shifts['torque_bar'] = (tx - native['torque_bar']['default']['x'], ty - native['torque_bar']['default']['y'])
  result = copy.deepcopy(base_customization)
  result['layouts']['large'] = {}
  for key, placement in document['widgets'].items():
    dx, dy = shifts.get(key, (0, 0))
    result['layouts']['large'][key] = {**placement, 'x': placement['x'] - dx, 'y': placement['y'] - dy}
  return result
