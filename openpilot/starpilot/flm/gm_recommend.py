"""Exact selected-GM adapters for original evidence-derived trial profiles.

Recommendations are human-selected trials, never a fitted learner, actuation
permission or evidence that a physical vehicle received a command.
"""
import hashlib
import json
import math

from opendbc.car.lateral import FRICTION_THRESHOLD
from openpilot.starpilot.flm.torque_surface import GmSurface, _GM_BOUNDS, _GM_RICH_BOUNDS

_PRECISIONS = {
  'torque_universal.ff_gain_left': 0.001,
  'torque_universal.ff_gain_right': 0.001,
  'torque_universal.turn_in_boost_left': 0.001,
  'torque_universal.turn_in_boost_right': 0.001,
  'torque_universal.unwind_taper_left': 0.001,
  'torque_universal.unwind_taper_right': 0.001,
  'torque_universal.center_taper_max': 0.001,
  'torque_universal.highway_center_taper_max': 0.001,
  'torque_universal.center_deadband_crawl_deg': 0.005,
  'torque_universal.center_deadband_low_deg': 0.005,
  'torque_universal.center_deadband_mid_deg': 0.005,
  'torque_universal.center_deadband_fast_deg': 0.005,
  'torque_universal.center_deadband_highway_deg': 0.005,
  'torque_universal.turn_in_threshold_reduction_left': 0.001,
  'torque_universal.turn_in_threshold_reduction_right': 0.001,
  'torque_universal.unwind_threshold_increase_left': 0.001,
  'torque_universal.unwind_threshold_increase_right': 0.001,
  'torque_universal.crawl_turn_in_ff_boost_left': 0.001,
  'torque_universal.crawl_turn_in_ff_boost_right': 0.001,
  'torque_universal.low_speed_angle_assist_max_torque': 0.001,
  'torque_universal.curvy_speed_min': 0.1,
  'torque_universal.curvy_speed_max': 0.1,
  'torque_universal.curvy_turn_in_trim_speed_min': 0.1,
  'torque_universal.curvy_turn_in_trim_speed_max': 0.1,
  'torque_universal.curvy_turn_in_trim_left': 0.001,
  'torque_universal.curvy_turn_in_trim_right': 0.001,
  'torque_universal.curvy_unwind_floor_relief_left': 0.001,
  'torque_universal.curvy_unwind_floor_relief_right': 0.001,
  'torque_universal.curvy_unwind_extra_reduction_left': 0.001,
  'torque_universal.curvy_unwind_extra_reduction_right': 0.001,
  'gm_bolt_2022_2023.ff_gain_left': 0.001,
  'gm_bolt_2022_2023.ff_gain_right': 0.001,
  'gm_bolt_2022_2023.turn_in_boost_left': 0.001,
  'gm_bolt_2022_2023.turn_in_boost_right': 0.001,
  'gm_bolt_2022_2023.unwind_taper_left': 0.001,
  'gm_bolt_2022_2023.unwind_taper_right': 0.001,
  'gm_bolt_2022_2023.center_taper_max': 0.001,
  'gm_bolt_2022_2023.turn_in_threshold_reduction_left': 0.001,
  'gm_bolt_2022_2023.turn_in_threshold_reduction_right': 0.001,
  'gm_bolt_2022_2023.unwind_threshold_increase_left': 0.001,
  'gm_bolt_2022_2023.unwind_threshold_increase_right': 0.001,
}

FLM_FRICTION_SPEED_KNOTS = (0., 5., 10., 15., 25.)


def get_standard_friction_threshold(speed):
  return FRICTION_THRESHOLD


def get_gm_base_friction_threshold(speed):
  return GmSurface('torque_universal', {}).base_threshold(speed)


def get_hkg_canfd_base_friction_threshold(speed):
  raise ValueError('This recommendation owner is exact GM only')


def get_flm_supported_vehicle_knobs():
  result = {}
  for profile in ('torque_universal', 'gm_bolt_2022_2023'):
    source = GmSurface(profile, {})
    limits = dict(_GM_BOUNDS)
    limits.update(_GM_RICH_BOUNDS if profile == 'gm_bolt_2022_2023' else {'ff_gain_left': (-.4, .6), 'ff_gain_right': (-.4, .6)})
    for name, (low, high) in limits.items():
      symbol = f'{profile}.{name}'
      result[symbol] = {'min': low, 'max': high, 'precision': _PRECISIONS.get(symbol, _PRECISIONS[f'torque_universal.{name}']),
                        'defaultValue': source.knobs[name]}
  return result


def normalize_flm_overrides(value):
  if type(value) is not dict or set(value) != {'schemaVersion', 'baseFrictionThresholds', 'vehicleKnobs'} or value['schemaVersion'] != 1:
    raise ValueError('Malformed recommendation surface')
  curves, knobs = value['baseFrictionThresholds'], value['vehicleKnobs']
  if type(curves) is not dict or set(curves) - {'gm', 'standard'} or type(knobs) is not dict or len(knobs) > 60:
    raise ValueError('Wrong recommendation surface family')
  supported = get_flm_supported_vehicle_knobs()
  for symbol, number in knobs.items():
    if symbol not in supported or type(number) not in (int, float) or not math.isfinite(number):
      raise ValueError('Malformed recommendation knob')
    limits = supported[symbol]
    if not limits['min'] <= number <= limits['max']:
      raise ValueError('Out-of-range recommendation knob')
  for curve in curves.values():
    if type(curve) is not dict or set(curve) != {'speedKnots', 'values'} or curve['speedKnots'] != list(FLM_FRICTION_SPEED_KNOTS):
      raise ValueError('Wrong recommendation curve source')
    GmSurface('torque_universal', {}, tuple(curve['values']))
  return {'schemaVersion': 1, 'baseFrictionThresholds': curves, 'vehicleKnobs': knobs}


def cp_signature(cp):
  def binary(value):
    if type(value) is bytes:
      return {'bytes': value.hex()}
    raise TypeError('Unsupported CarParams value')
  return hashlib.sha256(json.dumps(cp.to_dict(), sort_keys=True, allow_nan=False,
                                  separators=(',', ':'), default=binary).encode()).hexdigest()


def source_context(cp, controller, params, token, profile):
  from openpilot.starpilot.flm.live import gm_capability
  from openpilot.starpilot.flm.manual_trial import manual_snapshot, manual_preconditions
  from openpilot.starpilot.lateral.gm_geometry_runtime import geometry_basis
  from openpilot.starpilot.lateral.torque_runtime import factor_edit_supported
  from openpilot.starpilot.saved_source import read_saved
  capability = gm_capability(cp, controller)
  if capability is None:
    raise ValueError('Unsupported GM recommendation owner')
  advanced, readable = read_saved(params, 'AdvancedLateralTune', 64)
  off, off_readable = read_saved(params, 'ForceAutoTuneOff', 1)
  if not readable or advanced not in (None, b'0', b'1') or not off_readable or off not in (None, b'0', b'1'):
    raise ValueError('Unreadable recommendation guard')
  manual_preconditions(params, cp, controller, profile)  # Reject changed gain/geometry basis, never reinterpret it.
  selected = profile.flm.selected() if profile.flm is not None else None
  surface = selected or GmSurface(capability['profile'], {})
  if surface.profile != capability['profile']:
    raise ValueError('Review changed surface before training')
  context = {'version': 1, 'capability': capability, 'manual': manual_snapshot(profile, capability['fingerprint']),
             'surface': surface.document(), 'geometryBasis': geometry_basis(cp), 'cpSignature': cp_signature(cp),
             'sourceToken': token, 'advancedEnabled': advanced == b'1', 'forceOff': off == b'1',
             'factorSupported': factor_edit_supported(cp, controller), 'gainTable': gain_table(controller),
             'cleanupProgress': profile.flm is not None and profile.flm.cleanup_progress}
  return json.loads(json.dumps(context, allow_nan=False))


def validate_context(value):
  import re
  from openpilot.starpilot.flm.torque_surface import GmFlmBinding
  from openpilot.starpilot.flm.manual_trial import manual_profile
  from openpilot.starpilot.lateral.torque_supported import GM_VEHICLES
  expected = {'version', 'capability', 'manual', 'surface', 'geometryBasis', 'cpSignature', 'sourceToken',
              'advancedEnabled', 'forceOff', 'factorSupported', 'gainTable', 'cleanupProgress'}
  if type(value) is not dict or set(value) != expected or type(value['version']) is not int or value['version'] != 1:
    raise ValueError('Malformed GM analysis context')
  cap = value['capability']
  if type(cap) is not dict or set(cap) != {'fingerprint', 'controller', 'policy', 'basis', 'profile'} or cap['fingerprint'] not in GM_VEHICLES:
    raise ValueError('Wrong GM analysis vehicle')
  owner = GmFlmBinding(cap['controller'], cap['policy'], tuple(cap['basis']))
  surface = GmSurface.from_document(value['surface'])
  if surface.profile != cap['profile']:
    raise ValueError('Wrong GM analysis surface')
  manual_profile(value['manual'], cap['fingerprint'], owner.basis)
  if value['gainTable'] != [list(row) for row in gain_table(cap['controller'])]:
    raise ValueError('Wrong selected gain source')
  for key in ('cpSignature', 'sourceToken'):
    if type(value[key]) is not str or re.fullmatch(r'[a-f0-9]{64}', value[key]) is None:
      raise ValueError('Malformed GM analysis source')
  if any(type(value[key]) is not bool for key in ('advancedEnabled', 'forceOff', 'factorSupported', 'cleanupProgress')):
    raise ValueError('Malformed GM analysis guard')
  geometry = value['geometryBasis']
  if type(geometry) is not list or len(geometry) != 2 or any(type(n) not in (int, float) or not math.isfinite(n) or n <= 0 for n in geometry):
    raise ValueError('Malformed GM geometry source')
  return value


def matches_recording(cp, context):
  from openpilot.starpilot.flm.live import gm_capability
  context = validate_context(context)
  capability = gm_capability(cp, context['capability']['controller'])
  return capability is not None and json.loads(json.dumps(capability)) == context['capability'] and cp_signature(cp) == context['cpSignature']


def gain_table(controller):
  if controller == 'starpilot':
    return ((0,), (.6,))
  if controller != 'standard':
    raise ValueError('Wrong recommendation controller')
  from openpilot.selfdrive.controls.lib.latcontrol_torque import INTERP_SPEEDS, KP_INTERP
  return tuple(INTERP_SPEEDS), tuple(KP_INTERP)


def current_values(context):
  from openpilot.starpilot.flm.manual_trial import manual_profile
  context = validate_context(context)
  cap = context['capability']
  profile = manual_profile(context['manual'], cap['fingerprint'], tuple(cap['basis']))
  geometry = profile.geometry
  force_auto = geometry is not None and geometry.learning == 'force_auto' and not context['forceOff']
  force_off = context['forceOff'] or geometry is not None and geometry.learning == 'force_off'
  def number(choice, source, suppressed=False):
    return choice.custom_value if choice.mode == 'custom' and not suppressed else source
  from openpilot.starpilot.lateral.torque_supported import BOLT_VEHICLES
  gain_suppressed = cap['fingerprint'] in BOLT_VEHICLES and not context['advancedEnabled']
  ratio, delay = context['geometryBasis']
  surface = GmSurface.from_document(context['surface'])
  family = 'standard' if cap['controller'] == 'standard' else 'gm'
  return {'AdvancedLateralTune': True, 'ForceAutoTune': force_auto, 'ForceAutoTuneOff': force_off,
          'UseAutoSteerDelay': geometry is None or geometry.automatic_delay,
          'SteerLatAccel': number(profile.factor, cap['basis'][0], force_auto),
          'SteerFriction': number(profile.friction, cap['basis'][2], force_auto),
          'SteerKP': number(profile.proportional_gain, context['gainTable'][1][-1], gain_suppressed),
          'SteerRatio': ratio if geometry is None else number(geometry.ratio, ratio, force_auto),
          'SteerDelay': delay if geometry is None else number(geometry.full_delay, delay),
          'FLMActiveOverrides': {'schemaVersion': 1, 'baseFrictionThresholds': {} if surface.base_values is None else
                                {family: {'speedKnots': list(FLM_FRICTION_SPEED_KNOTS), 'values': list(surface.base_values)}},
                                'vehicleKnobs': {f'{surface.profile}.{key}': value for key, value in surface.knobs.items()}}}


def recommendation_capabilities(context):
  cap = context['capability']
  return {'torqueControl': True, 'richProfileKey': cap['profile'],
          'frictionFamily': 'standard' if cap['controller'] == 'standard' else 'gm',
          'nonlinearTorqueMap': {} if context['factorSupported'] else {'type': 'fixed_source_conversion', 'asymmetric': False}}


def canonical_trial(context, generated):
  """Translate original numerical intent to one exact-vehicle document, never global writes."""
  from dataclasses import replace
  from openpilot.starpilot.flm.manual_trial import manual_profile, manual_snapshot
  from openpilot.starpilot.lateral.torque_settings import FieldChoice, GainBasis, GeometryProfile
  cap = context['capability']
  profile = manual_profile(context['manual'], cap['fingerprint'], tuple(cap['basis']))
  delta = generated['genericParams']
  known = {'AdvancedLateralTune', 'ForceAutoTune', 'ForceAutoTuneOff', 'UseAutoSteerDelay',
           'SteerDelay', 'SteerFriction', 'SteerKP', 'SteerLatAccel', 'SteerRatio'}
  if set(delta) - known:
    raise ValueError('Unsupported original manual choice')
  if 'SteerLatAccel' in delta:
    if not context['factorSupported']:
      raise ValueError('The selected fixed conversion does not consume a custom factor')
    profile = replace(profile, factor=FieldChoice('custom', delta['SteerLatAccel']))
  if 'SteerFriction' in delta:
    profile = replace(profile, friction=FieldChoice('custom', delta['SteerFriction']))
  if 'SteerKP' in delta:
    basis = GainBasis(cap['controller'], tuple(tuple(row) for row in context['gainTable']), tuple(cap['basis']))
    profile = replace(profile, proportional_gain=FieldChoice('custom', delta['SteerKP']), gain_basis=basis)
  geometry = profile.geometry or GeometryProfile(tuple(context['geometryBasis']))
  if any(key in delta for key in ('SteerRatio', 'SteerDelay', 'UseAutoSteerDelay', 'ForceAutoTune', 'ForceAutoTuneOff')):
    learning = geometry.learning
    if delta.get('ForceAutoTuneOff') is True:
      learning = 'force_off'
    elif delta.get('ForceAutoTune') is True:
      learning = 'force_auto'
    elif 'ForceAutoTune' in delta or 'ForceAutoTuneOff' in delta:
      learning = 'source'
    geometry = replace(geometry,
      ratio=FieldChoice('custom', delta['SteerRatio']) if 'SteerRatio' in delta else geometry.ratio,
      full_delay=FieldChoice('custom', delta['SteerDelay']) if 'SteerDelay' in delta else geometry.full_delay,
      automatic_delay=delta.get('UseAutoSteerDelay', geometry.automatic_delay), learning=learning)
    profile = replace(profile, geometry=geometry)
  manual = manual_snapshot(profile, cap['fingerprint'])
  # Reparse enforces the existing exact selected basis and manual numeric bounds.
  manual_profile(manual, cap['fingerprint'], tuple(cap['basis']))
  raw = generated['flmOverrides']
  if not raw:
    raw = {'schemaVersion': 1, 'baseFrictionThresholds': {}, 'vehicleKnobs': {}}
  raw = normalize_flm_overrides(raw)
  source = GmSurface.from_document(context['surface'])
  prefix = cap['profile'] + '.'
  if any(not key.startswith(prefix) for key in raw['vehicleKnobs']):
    raise ValueError('Wrong selected surface profile')
  knobs = dict(source.knobs)
  knobs.update({key[len(prefix):]: value for key, value in raw['vehicleKnobs'].items()})
  curves = raw['baseFrictionThresholds']
  family = 'standard' if cap['controller'] == 'standard' else 'gm'
  if set(curves) - {family}:
    raise ValueError('Wrong selected friction family')
  surface = GmSurface(cap['profile'], knobs, tuple(curves[family]['values']) if family in curves else source.base_values)
  return {'manual': manual, 'surface': surface.document()}


def build_report(context, summaries, stats, *, feedback=None):
  from openpilot.starpilot.flm.gm_evidence import build_recommendation_paths
  context = validate_context(context)
  feedback = {} if feedback is None else feedback
  allowed = {row['dimensionId'] for row in summaries}
  if type(feedback) is not dict or set(feedback) - {'acceptedDimensions', 'ignoredDimensions'}:
    raise ValueError('Malformed evidence feedback')
  for choices in feedback.values():
    if type(choices) is not list or len(choices) > 128 or any(type(key) is not str or key not in allowed for key in choices):
      raise ValueError('Unknown evidence dimension')
  identity = hashlib.sha256(json.dumps({'source': context['sourceToken'], 'summaries': summaries, 'stats': stats},
                                     sort_keys=True, allow_nan=False).encode()).hexdigest()[:16]
  paths, decision = build_recommendation_paths(identity, summaries, stats, recommendation_capabilities(context),
                                               current_values(context), feedback, cleanup_progress_locked=context['cleanupProgress'])
  for path in paths:
    for generated in path['profiles']:
      try:
        generated['canonical'] = canonical_trial(context, generated)
        generated['unavailableReason'] = None
      except (ValueError, TypeError, OverflowError) as error:
        generated['canonical'] = None
        generated['unavailableReason'] = str(error)
  return {'context': context, 'summaries': summaries, 'stats': stats, 'feedback': feedback,
          'paths': paths, 'decision': decision, 'fit': False, 'vehicleQualification': False}


def classify_groups(groups):
  """Original classifier runs separately on each real contiguous joined epoch."""
  from openpilot.starpilot.flm.gm_evidence import _build_event_summaries
  summaries = []
  stats = {'sampleCount': 0, 'excludedDriverOverrideSamples': 0, 'qlogFallback': False,
           'meanDesiredAbs': 0., 'meanErrorAbs': 0., 'leftBias': 0., 'rightBias': 0.,
           'highwayStraightAngleP2P': 0., 'meanOutputAbs': 0.}
  for group in groups:
    rows, measured = _build_event_summaries(group)
    count = measured['sampleCount']
    if not count:
      continue
    summaries.extend(rows)
    stats['sampleCount'] += count
    stats['excludedDriverOverrideSamples'] += measured['excludedDriverOverrideSamples']
    for key in ('meanDesiredAbs', 'meanErrorAbs', 'leftBias', 'rightBias', 'meanOutputAbs'):
      stats[key] += measured[key] * count
    stats['highwayStraightAngleP2P'] = max(stats['highwayStraightAngleP2P'], measured['highwayStraightAngleP2P'])
  if stats['sampleCount']:
    for key in ('meanDesiredAbs', 'meanErrorAbs', 'leftBias', 'rightBias', 'meanOutputAbs'):
      stats[key] /= stats['sampleCount']
  stats['continuousGroups'] = len(groups)
  stats['summariesTruncated'] = len(summaries) > 128
  return sorted(summaries, key=lambda row: row['severity'], reverse=True)[:128], stats


def same_numerical_context(current, recorded):
  # Saving another inactive preset or recording monotonic cleanup progress
  # changes the document token, not its selected controller/manual/surface law.
  # Current exact token still guards the eventual atomic write. Every numerical,
  # CP, controller and explicit winning-global guard remains identical.
  if recorded['cleanupProgress'] and not current['cleanupProgress']:
    return False
  return {key: value for key, value in current.items() if key not in ('sourceToken', 'cleanupProgress')} == {
    key: value for key, value in recorded.items() if key not in ('sourceToken', 'cleanupProgress')}
