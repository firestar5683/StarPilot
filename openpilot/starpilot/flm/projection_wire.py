"""Exact bounded CarController emission metadata; no permission or plant claim."""

from typing import cast

FIELDS = (
  ('version', 'version'),
  ('family', 'family'),
  ('fingerprint', 'fingerprint'),
  ('flags', 'flags'),
  ('codecId', 'codec_id'),
  ('mappingKind', 'mapping_kind'),
  ('frame', 'frame'),
  ('requestedTorque', 'requested_torque'),
  ('codecInputTorque', 'codec_input_torque'),
  ('unlimitedRaw', 'unlimited_raw'),
  ('finalRaw', 'final_raw'),
  ('effectiveMax', 'effective_max'),
  ('lookupX', 'lookup_x'),
  ('lookupY', 'lookup_y'),
  ('limiterKind', 'limiter_kind'),
  ('previousTorque', 'previous_torque'),
  ('measuredTorque', 'measured_torque'),
  ('steerRequested', 'steer_requested'),
  ('canAddress', 'can_address'),
  ('canBus', 'can_bus'),
  ('canData', 'can_data'),
  ('reportedTorque', 'reported_torque'),
)


def write_projection(value):
  from opendbc.car.steering_projection import projection_to_dict
  from openpilot.starpilot.flm.learning_wire import _named_values

  data = cast(dict[str, object], projection_to_dict(value))
  result = {wire: data[key] for wire, key in FIELDS}
  # Honda's normalized limiter can have no unlimited integer command: its
  # lookup encoder runs AFTER limiting. Preserve absence rather than inventing
  # an unclipped integer or dropping the original clipped context.
  result['version'] = 2
  result['unlimitedRawPresent'] = data['unlimited_raw'] is not None
  result['unlimitedRaw'] = 0 if data['unlimited_raw'] is None else data['unlimited_raw']
  result['limits'] = [{'name': name, 'value': amount} for name, amount in cast(tuple[tuple[str, float], ...], data['limits'])]
  result['shape'] = _named_values(tuple((str(index), item) for index, item in enumerate(cast(tuple[float | bool, ...], data['shape']))))
  return result


def read_projection(value):
  if value.version == 0:
    return None
  if value.version not in (1, 2):
    raise ValueError('steering projection wire version')
  from opendbc.car.steering_projection import projection_from_dict
  from openpilot.starpilot.flm.learning_wire import _read_named_values

  if len(value.lookupX) > 16 or len(value.lookupY) > 16 or len(value.limits) > 5 or len(value.shape) > 7 or len(value.canData) > 64:
    raise ValueError('steering projection wire bounds')
  strings = ('family', 'fingerprint', 'codec_id', 'mapping_kind', 'limiter_kind')
  integers = ('version', 'flags', 'frame', 'unlimited_raw', 'final_raw', 'can_address', 'can_bus')
  data = {}
  for wire, key in FIELDS:
    item = getattr(value, wire)
    data[key] = (
      str(item)
      if key in strings
      else int(item)
      if key in integers
      else bool(item)
      if key == 'steer_requested'
      else bytes(item)
      if key == 'can_data'
      else tuple(float(v) for v in item)
      if key in ('lookup_x', 'lookup_y')
      else float(item)
    )
  if value.version == 2:
    # Version1 always carried an actual integer. Version2 explicitly preserves
    # the observer's optional integer without making zero mean unavailable.
    if not value.unlimitedRawPresent:
      if (value.unlimitedRaw != 0 or value.family != 'honda' or
          value.mappingKind != 'honda_lookup' or value.limiterKind != 'normalized_rate'):
        raise ValueError('invalid absent normalized Honda command')
      data['unlimited_raw'] = None
    data['version'] = 1  # Immutable observer/codec contract remains version1.
  shape = _read_named_values(value.shape, 7)
  if tuple(name for name, _ in shape) != tuple(str(index) for index in range(len(shape))):
    raise ValueError('steering projection shape order')
  data['shape'] = tuple(item for _, item in shape)
  data['limits'] = tuple((str(item.name), float(item.value)) for item in value.limits)
  return projection_from_dict(data)
