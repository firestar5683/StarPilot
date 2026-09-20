"""Read-only, bounded collection of car identity and parked health evidence."""
import argparse
import json
import time
from collections import Counter

CP_FIELDS = ('brand', 'carFingerprint', 'fingerprintSource', 'fuzzyFingerprint', 'dashcamOnly', 'passive',
             'flags', 'alphaLongitudinalAvailable', 'openpilotLongitudinalControl', 'pcmCruise',
             'steerControlType', 'safetyConfigs', 'alternativeExperience', 'carFw')
FIELDS = {
  'carState': ('vEgo', 'standstill', 'brakePressed', 'gasPressed', 'leftBlinker', 'rightBlinker', 'canValid',
               'canTimeout', 'gearShifter', 'steerFaultTemporary', 'steerFaultPermanent', 'steeringDisengage',
               'invalidLkasSetting', 'stockLkas', 'accFaulted', 'cruiseState'),
  'carControl': ('enabled', 'latActive', 'longActive'),
  'selfdriveState': ('enabled', 'active', 'state', 'alertType', 'alertText1', 'alertText2'),
  'liveCalibration': ('calStatus', 'calPerc'),
  'modelV2': ('frameId', 'modelExecutionTime', 'gpuExecutionTime'),
}
PARAMS = ('OpenpilotEnabledToggle', 'ExperimentalLongitudinalEnabled', 'AlphaLongitudinalEnabled',
          'AlwaysOnLateral', 'AlwaysOnLateralLKAS', 'AlwaysOnLateralMain', 'AlwaysOnLateralPauseSpeed',
          'ForceFingerprint', 'CarModel', 'TeslaCoopSteering', 'DisengageOnAccelerator')


def clean(value):
  if hasattr(value, 'to_dict'):
    value = value.to_dict()
  if isinstance(value, dict):
    return {str(k): clean(v) for k, v in value.items() if 'vin' not in str(k).lower()}
  if isinstance(value, (list, tuple)):
    return [clean(v) for v in value]
  if isinstance(value, bytes):
    return {'ascii': value.decode('ascii', errors='replace'), 'hex': value.hex()}
  if isinstance(value, (str, int, float, bool)) or value is None:
    return value
  return str(value)


def select(value, fields):
  result = {}
  for field in fields:
    try:
      raw = getattr(value, field)
      result[field] = [clean(item) for item in raw] if field in ('carFw', 'safetyConfigs') else clean(raw)
    except (AttributeError, RuntimeError):
      pass
  return result


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--seconds', type=float, default=20)
  args = parser.parse_args()
  if not 1 <= args.seconds <= 120:
    parser.error('--seconds must be between 1 and 120')
  from cereal import car, messaging
  from openpilot.common.params import Params
  params = Params()
  def emit(row):
    print(json.dumps(row, sort_keys=True), flush=True)
  identity = {'kind': 'identity', 'read_only': True, 'car_params_source': 'stored-unconfirmed', 'params': {}}
  for key in PARAMS:
    try:
      identity['params'][key] = clean(params.get(key))
    except Exception as exc:
      identity['params'][key] = {'unavailable': type(exc).__name__}
  raw = params.get('CarParams')
  if raw:
    with car.CarParams.from_bytes(raw) as cp:
      identity['car_params'] = select(cp, CP_FIELDS)
  emit(identity)
  topics = [*FIELDS, 'carParams', 'pandaStates', 'managerState', 'onroadEvents']
  sm = messaging.SubMaster(topics)
  can_socket = messaging.sub_sock('can')
  start = time.monotonic()
  next_report = start
  counts = Counter()
  brake_values = {0x145: set(), 0x39d: set()}
  last_can = None
  while time.monotonic() - start < args.seconds:
    sm.update(100)
    now = time.monotonic()
    for event in messaging.drain_sock(can_socket, wait_for_one=False):
      last_can = event.logMonoTime / 1e9
      for frame in event.can:
        if frame.src == 0 and frame.address in brake_values:
          counts[frame.address] += 1
          data = bytes(frame.dat)
          if frame.address == 0x145 and len(data) == 8:
            brake_values[frame.address].add((data[3] >> 5) & 3)
          elif frame.address == 0x39d and len(data) == 5:
            brake_values[frame.address].add(data[2] & 3)
    if now < next_report:
      continue
    next_report = now + 1
    row = {'kind': 'observation', 'elapsed': now-start, 'topics': {},
           'can_age_s': None if last_can is None else now-last_can,
           'brake_can_counts_total': {hex(k): v for k, v in counts.items()},
           'brake_raw_values_seen': {hex(k): sorted(v) for k, v in brake_values.items()}}
    for topic in topics:
      entry = {'seen': bool(sm.seen[topic]), 'valid': bool(sm.valid[topic]), 'alive': bool(sm.alive[topic]),
               'age_s': now-sm.logMonoTime[topic]/1e9 if sm.seen[topic] else None}
      if sm.seen[topic]:
        if topic in FIELDS:
          entry['data'] = select(sm[topic], FIELDS[topic])
        elif topic == 'carParams':
          entry['data'] = select(sm[topic], CP_FIELDS)
        elif topic in ('pandaStates', 'onroadEvents'):
          entry['data'] = [clean(item) for item in sm[topic]]
        else:
          entry['data'] = clean(sm[topic])
      row['topics'][topic] = entry
    emit(row)
  emit({'kind': 'complete', 'elapsed': time.monotonic()-start,
        'verdict': 'evidence-only; not automatic drive clearance'})


if __name__ == '__main__':
  main()
