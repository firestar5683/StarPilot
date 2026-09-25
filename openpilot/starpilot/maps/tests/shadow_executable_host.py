"""Required disposable host GPS -> executable shadow -> MapStatus IPC proof."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from openpilot.cereal import log, messaging
from openpilot.starpilot.galaxy.map_status import MapStatus


def gps(source: str, *, event_valid: bool = True, has_fix: bool = True):
  event = messaging.new_message(source, valid=event_valid)
  location = getattr(event, source)
  location.flags = 1 if has_fix else 0
  location.hasFix = has_fix
  location.horizontalAccuracy = 1.0
  location.bearingDeg = 0.0
  location.latitude = 35.15
  location.longitude = -97.9
  location.speed = 8.0
  return event


def until(source: MapStatus, predicate, publish=None, *, seconds=2.0):
  deadline = time.monotonic() + seconds
  last = None
  seen = set()
  while time.monotonic() < deadline:
    if publish is not None:
      publish()
    last = source.snapshot()
    seen.add((last['state'], last['roadStatus'], last['gpsSource']))
    if predicate(last):
      return last
    time.sleep(0.025)
  raise AssertionError(f'expected map state did not arrive: {last}; seen={sorted(map(str, seen))}')


def main():
  binary = Path(os.environ['STARPILOT_SHADOW_BINARY'])
  root = Path(os.environ['STARPILOT_SHADOW_ROOT'])
  assert binary.is_file() and root.is_dir()
  prefix = f'mapshadow_exec_{uuid.uuid4().hex}'
  with tempfile.TemporaryDirectory(prefix='mapshadow-params-') as params_root:
    os.environ['PARAMS_ROOT'] = params_root
    os.environ['OPENPILOT_PREFIX'] = prefix
    messaging.set_fake_prefix(prefix)
    queue_root = Path('/dev/shm' if Path('/dev/shm').is_dir() else '/tmp') / f'msgq_{prefix}'
    queue_root.mkdir(mode=0o700)
    source = MapStatus()
    external = messaging.pub_sock('gpsLocationExternal')
    internal = messaging.pub_sock('gpsLocation')
    ignored = {name: messaging.pub_sock(name) for name in ('carState', 'modelV2', 'selfdriveState', 'mapdIn')}
    processes = []
    provider_log = tempfile.TemporaryFile()
    def launch():
      child = subprocess.Popen([str(binary), '--shadow', '--offline-root', str(root)],
                               stdin=subprocess.DEVNULL, stdout=provider_log, stderr=provider_log,
                               env=os.environ.copy())
      processes.append(child)
      return child

    def stop(child):
      if child.poll() is not None:
        return
      child.terminate()
      try:
        child.wait(timeout=3)
      except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=3)

    try:
      child = launch()
      deadline = time.monotonic() + 2
      while not (queue_root / 'mapdOut').exists() and time.monotonic() < deadline:
        time.sleep(0.01)
      source.snapshot()
      raw_output = messaging.sub_sock('mapdOut', conflate=True)
      try:
        first = until(source, lambda item: item['state'] == 'matched_limit_unqualified' and item['gpsSource'] == 'external',
                      lambda: external.send(gps('gpsLocationExternal').to_bytes()))
      except AssertionError as error:
        provider_log.seek(0)
        raise AssertionError(f'{error}; child exit={child.poll()}; provider={provider_log.read().decode(errors="replace")}') from error
      assert abs(first['candidateSpeedMps'] - 13.4112) < 0.01
      old = gps('gpsLocationExternal')
      old.logMonoTime = time.monotonic_ns() - 3_000_000_000
      external.send(old.to_bytes())
      time.sleep(0.12)  # two provider ticks; old fix must not replace the recent one
      retained = until(source, lambda item: item['state'] == 'matched_limit_unqualified' and
                       item['gpsSource'] == 'external' and item['sourceSwitches'] == first['sourceSwitches'])
      assert abs(retained['candidateSpeedMps'] - 13.4112) < 0.01
      invalid = gps('gpsLocationExternal', event_valid=False)
      external.send(invalid.to_bytes())
      until(source, lambda item: item['roadStatus'] == 'noGps' and item['candidateSpeedMps'] is None, seconds=1.0)
      until(source, lambda item: item['state'] == 'matched_limit_unqualified' and item['gpsSource'] == 'external',
            lambda: external.send(gps('gpsLocationExternal').to_bytes()))
      no_fix = gps('gpsLocationExternal', has_fix=False)
      external.send(no_fix.to_bytes())
      until(source, lambda item: item['roadStatus'] == 'noGps' and item['candidateSpeedMps'] is None, seconds=1.0)
      until(source, lambda item: item['state'] == 'matched_limit_unqualified' and item['gpsSource'] == 'external',
            lambda: external.send(gps('gpsLocationExternal').to_bytes()))
      for name, publisher in ignored.items():
        message = messaging.new_message(name, valid=True)
        if name == 'carState':
          message.carState.vEgo = 32
        elif name == 'modelV2':
          message.modelV2.frameId = 12345
        elif name == 'selfdriveState':
          message.selfdriveState.personality = 'relaxed'
        else:
          message.mapdIn.type = 'setSpeedLimitControl'
          message.mapdIn.bool = True
        publisher.send(message.to_bytes())
      observed = until(source, lambda item: item['state'] == 'matched_limit_unqualified' and item['gpsSource'] == 'external',
                       lambda: external.send(gps('gpsLocationExternal').to_bytes()))
      assert abs(observed['candidateSpeedMps'] - 13.4112) < 0.01
      deadline = time.monotonic() + 1
      packet = None
      while packet is None and time.monotonic() < deadline:
        packet = raw_output.receive(non_blocking=True)
        if packet is None:
          time.sleep(0.01)
      assert packet is not None
      with log.Event.from_bytes(packet) as event:
        output = event.mapdOut
        assert output.suggestedSpeed == 0 and output.nextSpeedLimit == 0
        assert not output.speedLimitAccepted and output.visionCurveSpeed == 0 and output.mapCurveSpeed == 0
      fallback = until(source, lambda item: item['state'] == 'matched_limit_unqualified' and item['gpsSource'] == 'internal',
                       lambda: internal.send(gps('gpsLocation').to_bytes()), seconds=2.0)
      assert abs(fallback['candidateSpeedMps'] - 13.4112) < 0.01
      stale = until(source, lambda item: item['state'] in ('loss', 'stale', 'unknown') and
                    item['gpsSource'] == 'none' and item['candidateSpeedMps'] is None,
                    seconds=3.0)
      stop(child)
      restart_count = stale['producerRestarts']
      child = launch()
      restarted = until(source, lambda item: item['state'] == 'matched_limit_unqualified' and
                        item['gpsSource'] == 'external' and item['producerRestarts'] > restart_count,
                        lambda: external.send(gps('gpsLocationExternal').to_bytes()))
      assert abs(restarted['candidateSpeedMps'] - 13.4112) < 0.01
      stop(child)
      print(json.dumps({'external': True, 'invalidEvent': True, 'noFix': True, 'oldGps': True, 'internalFallback': True,
                        'stale': True, 'restarted': True, 'ignoredInputs': True}))
    finally:
      cleanup_errors = []
      for child in processes:
        try:
          stop(child)
        except Exception as error:
          cleanup_errors.append(error)
      for action in (source.close, messaging.delete_fake_prefix, lambda: shutil.rmtree(queue_root), provider_log.close):
        try:
          action()
        except Exception as error:
          cleanup_errors.append(error)
      if cleanup_errors and sys.exc_info()[0] is None:
        raise RuntimeError(f'shadow fixture cleanup failed: {cleanup_errors}')


if __name__ == '__main__':
  main()
