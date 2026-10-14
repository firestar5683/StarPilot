"""Separate AA placement document; native large/compact schemas stay fixed."""
import copy
import json
import math
from pathlib import Path

from openpilot.starpilot.system.android_auto.identity import DATA_DIR
from openpilot.starpilot.system.android_auto.display_profile import screen_geometry
from openpilot.starpilot.ui.onroad_customization import (CEM_GAUGE_WIDGET, CLOCK_WIDGET, MODE_WIDGET, STOPPED_TIMER_WIDGET, WHEEL_SIZES,
                                                         CEM_GAUGE_FRAME, CEM_GAUGE_INSET, SPEED_ALIGNMENTS, customization_metadata, validate_widget_order)
from openpilot.starpilot.ui.onroad_stopped_timer import timer_size
from openpilot.starpilot.ui.onroad_torque_geometry import maximum_footprint

MAX_BYTES = 16384
DOCUMENT_KEY = 'projection'
DOCUMENT_PATH = DATA_DIR / 'layouts/document.json'

# Android Auto only: the comma layout keeps its fixed schema. Layouts saved
# before these (or the driving-mode widget) existed gain them with their defaults.
NAV_CARD, NAV_MAP = 'nav_card', 'nav_map'
NAV_HOME, NAV_WORK = 'nav_home', 'nav_work'
FAVORITE_WIDGETS = (NAV_HOME, NAV_WORK)
BOOKMARK_WIDGET = 'bookmark'
DISPLAY_WIDGETS = (*FAVORITE_WIDGETS, BOOKMARK_WIDGET)
CAR_EXIT = 'car_exit'
ACTION_WIDGETS = (*DISPLAY_WIDGETS, CAR_EXIT)
FAVORITE_SIZE = (320, 110)
FAVORITE_ICON_SIZE = 110
CAR_EXIT_SIZE = (96, 96)
CAR_EXIT_MIN_OPACITY = 25
PROJECTION_WIDGETS = (NAV_CARD, NAV_MAP, *DISPLAY_WIDGETS, STOPPED_TIMER_WIDGET, CAR_EXIT)
NAV_CARD_SIZE = (560, 195)
MAP_MIN_SIZE = (280, 200)
MAP_OPACITY = (15, 100, 50)  # percent: min, max, default


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
  widgets[MODE_WIDGET]['default']['x'] += (width - 1860) / 2
  widgets[CLOCK_WIDGET]['default']['x'] += (width - 1860) / 2
  widgets['steering_wheel']['default']['x'] += width - 1860
  widgets['driver_monitor']['default']['y'] += height - 1080
  x, y, w, h = maximum_footprint(30, 30, width - 60, height - 60, width)
  widgets['torque_bar'].update(width=w, height=h)
  widgets['torque_bar']['default'].update(x=x, y=y)
  timer_w, timer_h = timer_size('large')
  widgets[STOPPED_TIMER_WIDGET] = {'label': 'Stopped timer', 'kind': STOPPED_TIMER_WIDGET,
                                  'width': timer_w, 'height': timer_h, 'colors': {},
                                  'note': 'Counts how long you have been stopped, after the first minute of the drive',
                                  'default': {'x': (width - timer_w) / 2, 'y': 520, 'enabled': False}}
  # The turn card keeps the comma's large-UI spot, following the right edge.
  card_w, card_h = NAV_CARD_SIZE
  widgets[NAV_CARD] = {'label': 'Turn-by-turn', 'kind': NAV_CARD, 'width': card_w, 'height': card_h, 'colors': {},
                       'note': 'The next maneuver while a route is active, in the comma style',
                       'default': {'x': 1230 + width - 1860, 'y': 415, 'enabled': True}}
  # The map scales with the screen: about 30% of its width in a 4:3 frame,
  # right-aligned with the turn card and sitting just below it.
  card_x, card_bottom = 1230 + width - 1860, 415 + card_h + 15
  map_w = max(MAP_MIN_SIZE[0], round(width * 0.3 / 10) * 10)
  map_h = max(MAP_MIN_SIZE[1], min(round(map_w * 0.75 / 10) * 10, (height - 30 - card_bottom) // 10 * 10))
  widgets[NAV_MAP] = {'label': 'Map overlay', 'kind': NAV_MAP, 'width': map_w, 'height': map_h, 'colors': {},
                      'note': 'Road lines and your route over the camera. Drag the corner to resize; opacity sets how much shows.',
                      'box': {'minWidth': MAP_MIN_SIZE[0], 'maxWidth': width - 60,
                              'minHeight': MAP_MIN_SIZE[1], 'maxHeight': height - 60},
                      'opacity': {'min': MAP_OPACITY[0], 'max': MAP_OPACITY[1], 'default': MAP_OPACITY[2]},
                      'default': {'x': max(30, card_x + card_w - map_w), 'y': min(card_bottom, height - 30 - map_h),
                                  'enabled': False, 'width': map_w, 'height': map_h, 'opacity': MAP_OPACITY[2]}}
  for index, key in enumerate(FAVORITE_WIDGETS):
    label = ('Home', 'Work')[index]
    widgets[key] = {'label': label, 'kind': key, 'width': FAVORITE_SIZE[0], 'height': FAVORITE_SIZE[1], 'colors': {},
                    'iconSize': FAVORITE_ICON_SIZE,
                    'note': f'Navigate to your saved {label} favorite. Tap again to end navigation. Set the address in The Galaxy.',
                    'default': {'x': width - 30 - 2 * FAVORITE_SIZE[0] - 15 + index * (FAVORITE_SIZE[0] + 15),
                                'y': 280, 'enabled': False, 'display': 'words'}}
  widgets[BOOKMARK_WIDGET] = {'label': 'Bookmark', 'kind': BOOKMARK_WIDGET,
                              'width': FAVORITE_SIZE[0], 'height': FAVORITE_SIZE[1], 'colors': {},
                              'iconSize': FAVORITE_ICON_SIZE,
                              'note': 'Save a bookmark in the current drive recording.',
                              'default': {'x': width - 30 - FAVORITE_SIZE[0], 'y': 155, 'enabled': False, 'display': 'words'}}
  exit_w, exit_h = CAR_EXIT_SIZE
  widgets[CAR_EXIT] = {'label': 'Exit to car', 'kind': CAR_EXIT, 'width': exit_w, 'height': exit_h, 'colors': {},
                       'required': True, 'frontmost': True,
                       'note': "Returns to the car's own screen without disconnecting Android Auto. Always enabled and above other widgets.",
                       'default': {'x': 30, 'y': height - 30 - exit_h, 'enabled': True}}
  for key in ACTION_WIDGETS:
    widgets[key].update(opacity={'min': CAR_EXIT_MIN_OPACITY if key == CAR_EXIT else 0, 'max': 100, 'default': 100}, backgroundToggle=True)
    widgets[key]['default'].update(opacity=100, background=True)
  # Background opacity for the cruise and speed-limit card; its text stays solid.
  widgets['cruise_limits'].update(opacity={'min': 0, 'max': 100, 'default': 100})
  widgets['cruise_limits']['default'].update(opacity=100)
  profile["widgetOrder"] = [NAV_MAP, *profile["widgetOrder"], STOPPED_TIMER_WIDGET, NAV_CARD, *DISPLAY_WIDGETS, CAR_EXIT]
  return profile


# Android Auto display switches, independent of the comma screen's preferences.
DISPLAY_DEFAULTS = {'blindSpotBorder': False, 'signalBorder': False, 'blindSpotCamera': False,
                    'hidePersonalityAlerts': False, 'wheelPedalFeedback': False,
                    'leadIndicator': False, 'leadInfo': 'Off', 'speedSources': False,
                    'speedSourcesCard': False, 'speedAlign': 'left'}
# Lead info shown above the lead marker, in LeadInfoMode order.
LEAD_INFO_CHOICES = ('Off', 'Distance', 'Speed')


def projection_appearance(appearance, document):
  """The comma's onroad appearance with every car-screen choice taken from the AA layout instead."""
  from dataclasses import replace
  from openpilot.starpilot.ui.appearance_preferences import CameraViewChoice, LeadInfoMode
  lead_indicator = document.get('leadIndicator', False) is True
  lead_info = document.get('leadInfo', 'Off')
  # Like the comma, lead info only shows with the lead marker on.
  lead_info_mode = LeadInfoMode(LEAD_INFO_CHOICES.index(lead_info)) if lead_indicator and lead_info in LEAD_INFO_CHOICES else LeadInfoMode.OFF
  # The car screen always shows the road camera; the comma's camera choices stay on the comma.
  return replace(appearance,
                 show_lead_indicator=lead_indicator, lead_info_mode=lead_info_mode,
                 show_blindspot_border=document.get('blindSpotBorder', False) is True,
                 show_signal_border=document.get('signalBorder', False) is True,
                 hide_personality_alerts=document.get('hidePersonalityAlerts', False) is True,
                 wheel_pedal_feedback=document.get('wheelPedalFeedback', False) is True,
                 camera_view=CameraViewChoice.STANDARD, driver_camera_on_reverse=False)


def comma_display(appearance):
  """The comma screen's display choices as AA switches, to start a car screen that has no saved layout."""
  lead_indicator = appearance.show_lead_indicator is True
  return {'blindSpotBorder': appearance.show_blindspot_border is True,
          'signalBorder': appearance.show_signal_border is True,
          'hidePersonalityAlerts': appearance.hide_personality_alerts is True,
          'wheelPedalFeedback': appearance.wheel_pedal_feedback is True,
          'leadIndicator': lead_indicator,
          'leadInfo': LEAD_INFO_CHOICES[appearance.lead_info_mode] if lead_indicator else 'Off'}


def default_layout(screen, display=None):
  geometry = screen_geometry(screen)
  return default_layout_for_viewport((geometry.logical_width, geometry.logical_height), display)


def default_layout_for_viewport(viewport, display=None):
  metadata = layout_metadata_for_viewport(viewport)
  display = {**DISPLAY_DEFAULTS, **{key: value for key, value in (display or {}).items() if key in DISPLAY_DEFAULTS}}
  return {'version': 3, 'clock24Hour': False, 'largeUiGammaTrial': False, **display, 'canvas': {key: metadata[key] for key in ('width', 'height')},
          'widgets': {key: {**widget['default'], **({'size': 192} if key == 'steering_wheel' else {})}
                      for key, widget in metadata['widgets'].items()}}


def placement_size(key, widget, placement):
  if key in DISPLAY_WIDGETS and placement.get('display') == 'icons':
    return FAVORITE_ICON_SIZE, FAVORITE_ICON_SIZE
  if key == 'steering_wheel':
    return placement.get('size', 192), placement.get('size', 192)
  if key == NAV_MAP:
    return placement['width'], placement['height']
  return widget['width'], widget['height']


def validate_layout(value, screen):
  geometry = screen_geometry(screen)
  return validate_layout_for_viewport(value, (geometry.logical_width, geometry.logical_height))


def validate_layout_for_viewport(value, viewport, *, _legacy_geometry=False):
  metadata = layout_metadata_for_viewport(viewport)
  if type(value) is dict and type(value.get('version')) is int and value['version'] == 1 and not _legacy_geometry:
    result = validate_layout_for_viewport(value, viewport, _legacy_geometry=True)
    card, actions = result['widgets']['cruise_limits'], result['widgets']['speed_limit_actions']
    if actions['x'] == card['x'] and actions['y'] - card['y'] in (372, 425):
      actions['y'] = card['y'] + 492
    for key in ('cruise_limits', 'speed_limit_actions'):
      widget, saved = metadata['widgets'][key], result['widgets'][key]
      for axis, extent in (('x', 'width'), ('y', 'height')):
        saved[axis] = min(saved[axis], metadata['bounds'][axis] + metadata['bounds'][extent] - widget[extent])
    result['version'] = 2
    return validate_layout_for_viewport(result, viewport)
  fields = {'version', 'canvas', 'widgets'}
  if type(value) is dict:
    fields |= {field for field in ('widgetOrder', 'clock24Hour', 'largeUiGammaTrial', *DISPLAY_DEFAULTS) if field in value}
  if (type(value) is not dict or set(value) != fields or
      type(value['version']) is not int or value['version'] not in (1, 2, 3) or
      value['canvas'] != {key: metadata[key] for key in ('width', 'height')} or
      type(value['widgets']) is not dict or not set(value['widgets']) <= set(metadata['widgets']) or
      not set(metadata['widgets']) - set(value['widgets']) <= {CEM_GAUGE_WIDGET, MODE_WIDGET, CLOCK_WIDGET, *PROJECTION_WIDGETS}):
    raise ValueError('Projection layout does not match saved screen')
  result = copy.deepcopy(value)
  if 'clock24Hour' in value and type(value['clock24Hour']) is not bool:
    raise ValueError('Invalid projection clock format')
  result.setdefault('clock24Hour', False)
  if 'largeUiGammaTrial' in value and type(value['largeUiGammaTrial']) is not bool:
    raise ValueError('Invalid large UI gamma trial')
  result.setdefault('largeUiGammaTrial', False)
  for field, default in DISPLAY_DEFAULTS.items():
    if field in value and (type(value[field]) is not type(default) or
                           (field == 'leadInfo' and value[field] not in LEAD_INFO_CHOICES) or
                           (field == 'speedAlign' and value[field] not in SPEED_ALIGNMENTS)):
      raise ValueError('Invalid projection display setting')
    result.setdefault(field, default)
  for key in set(metadata['widgets']) - set(value['widgets']):
    result['widgets'][key] = dict(metadata['widgets'][key]['default'])
  if 'widgetOrder' in value:
    order = value['widgetOrder']
    if type(order) is list:
      order = [*order, *(key for key in (CEM_GAUGE_WIDGET, MODE_WIDGET, CLOCK_WIDGET, *PROJECTION_WIDGETS) if key not in order)]
    order = validate_widget_order(order, metadata['widgets'])
    # Older or hand-edited documents may put the escape control underneath
    # another widget. Preserve their order while restoring this safety layer.
    result['widgetOrder'] = [key for key in order if key != CAR_EXIT] + [CAR_EXIT]
  bounds = metadata['bounds']
  for key, widget in metadata['widgets'].items():
    placement = result['widgets'][key]
    if key in DISPLAY_WIDGETS and type(placement) is dict:
      placement.setdefault('display', 'words')
    if key in ACTION_WIDGETS and type(placement) is dict:
      placement.setdefault('opacity', 100)
      placement.setdefault('background', True)
    if key == 'cruise_limits' and type(placement) is dict:
      placement.setdefault('opacity', 100)
    fields = ({'x', 'y', 'enabled'} | ({'size'} if key == 'steering_wheel' else set()) |
              ({'display'} if key in DISPLAY_WIDGETS else set()) |
              ({'opacity', 'background'} if key in ACTION_WIDGETS else set()) |
              ({'opacity'} if key == 'cruise_limits' else set()) |
              ({'width', 'height', 'opacity'} if key == NAV_MAP else set()))
    if type(placement) is not dict or set(placement) != fields or type(placement['enabled']) is not bool:
      raise ValueError('Invalid projection widget')
    if widget.get('required') is True and placement['enabled'] is not True:
      raise ValueError('Required projection widget is disabled')
    if key in DISPLAY_WIDGETS and placement['display'] not in ('words', 'icons'):
      raise ValueError('Invalid action widget display')
    if key in ACTION_WIDGETS and (type(placement['opacity']) is not int or not 0 <= placement['opacity'] <= 100 or
                                  type(placement['background']) is not bool):
      raise ValueError('Invalid action widget appearance')
    if key == 'cruise_limits' and (type(placement['opacity']) is not int or not 0 <= placement['opacity'] <= 100):
      raise ValueError('Invalid cruise card opacity')
    if key == CAR_EXIT and placement['opacity'] < CAR_EXIT_MIN_OPACITY:
      raise ValueError('Exit to car opacity must be at least 25%')
    size = placement.get('size', 192)
    if key == 'steering_wheel' and (type(size) is not int or not WHEEL_SIZES['large'][0] <= size <= WHEEL_SIZES['large'][2]):
      raise ValueError('Invalid steering wheel size')
    if key == NAV_MAP:
      box, opacity = widget['box'], widget['opacity']
      if (type(placement['width']) is not int or not box['minWidth'] <= placement['width'] <= box['maxWidth'] or
          type(placement['height']) is not int or not box['minHeight'] <= placement['height'] <= box['maxHeight'] or
          type(placement['opacity']) is not int or not opacity['min'] <= placement['opacity'] <= opacity['max']):
        raise ValueError('Invalid map overlay size or opacity')
    dimensions = placement_size(key, widget, placement)
    # Version 2 and older saved the CEM gauge's full drawing frame; check that, then move to the inset box.
    old_gauge = key == CEM_GAUGE_WIDGET and value['version'] < 3 and key in value['widgets']
    if old_gauge:
      dimensions = CEM_GAUGE_FRAME
    if _legacy_geometry and key in ('cruise_limits', 'speed_limit_actions'):
      historic = {'cruise_limits': ((176, 483), (280, 412)), 'speed_limit_actions': ((176, 58), (280, 96))}
      # Both shapes were published as v1; validate the whole footprint before migrating.
      dimensions = next((pair for pair in historic[key] if all(
        type(placement[axis]) in (int, float) and math.isfinite(placement[axis]) and
        bounds[axis] <= placement[axis] <= bounds[axis] + bounds[extent] - dimension
        for (axis, extent), dimension in zip((('x', 'width'), ('y', 'height')), pair, strict=True))), dimensions)
    for (axis, extent), dimension in zip((('x', 'width'), ('y', 'height')), dimensions, strict=True):
      number = placement[axis]
      if (type(number) not in (int, float) or not math.isfinite(number) or
          not bounds[axis] <= number <= bounds[axis] + bounds[extent] - dimension):
        raise ValueError('Projection widget outside screen')
    if old_gauge and not _legacy_geometry:
      placement.update(x=placement['x'] + CEM_GAUGE_INSET[0], y=placement['y'] + CEM_GAUGE_INSET[1])
  if not _legacy_geometry:
    result['version'] = 3
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
  value = json.loads(raw, object_pairs_hook=unique)
  # Lift older saved escape controls to the new minimum without losing the layout.
  widgets = value.get('widgets') if type(value) is dict else None
  exit_placement = widgets.get(CAR_EXIT) if type(widgets) is dict else None
  if type(exit_placement) is dict and type(exit_placement.get('opacity')) is int and 0 <= exit_placement['opacity'] < CAR_EXIT_MIN_OPACITY:
    exit_placement['opacity'] = CAR_EXIT_MIN_OPACITY
  return validate_layout_for_viewport(value, viewport)


def projection_customization(document, base_customization):
  """Convert validated AA placements to offsets consumed by the projected view.

  The view already applies its center/right/bottom anchors. Cancel those anchor
  shifts here so the independent saved coordinates are applied exactly once.
  Colors and native compact placement are copied from the caller's document.
  """
  from openpilot.starpilot.ui.onroad_customization import PROFILES
  width, height = document['canvas']['width'], document['canvas']['height']
  shifts = {'current_speed': ((width - 1860) / 2, 0),
            MODE_WIDGET: ((width - 1860) / 2, 0),
            CLOCK_WIDGET: ((width - 1860) / 2, 0),
            'steering_wheel': (width - 1860, 0), 'driver_monitor': (0, height - 1080)}
  native = PROFILES['large']['widgets']
  assert isinstance(native, dict)
  tx, ty, _, _ = maximum_footprint(30, 30, width - 60, height - 60, width)
  shifts['torque_bar'] = (tx - native['torque_bar']['default']['x'], ty - native['torque_bar']['default']['y'])
  result = copy.deepcopy(base_customization)
  result['clock24Hour'] = document.get('clock24Hour', False)
  result.setdefault('widgetOrder', {}).pop('large', None)
  if 'widgetOrder' in document:
    result['widgetOrder']['large'] = list(document['widgetOrder'])
  result['layouts']['large'] = {}
  for key, placement in document['widgets'].items():
    dx, dy = shifts.get(key, (0, 0))
    result['layouts']['large'][key] = {**placement, 'x': placement['x'] - dx, 'y': placement['y'] - dy}
  from openpilot.starpilot.ui.onroad_customization import rgba
  # Card opacity is a colour, not a placement: fold it into the fill and keep the native placement shape.
  opacity = result['layouts']['large'].get('cruise_limits', {}).pop('opacity', 100)
  if opacity != 100:
    red, green, blue, alpha = rgba(result, 'cardFill', 'large', 'cruise_limits')
    fill = f'#{red:02X}{green:02X}{blue:02X}{round(alpha * opacity / 100):02X}'
    result['widgetColors']['large'].setdefault('cruise_limits', {})['cardFill'] = fill
  for key in ('speedSources', 'speedSourcesCard', 'speedAlign'):
    if key in document:
      result[key] = document[key]
  return result
