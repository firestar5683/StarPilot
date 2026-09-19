"""Offline route richness only. Never imported by generation or playback."""
import argparse
from collections import Counter
import json
import warnings
from pathlib import Path
import numpy as np
from openpilot.tools.lib.logreader import LogReader


def characterize(folder):
    services = Counter()
    segments = []
    speeds, curvatures = [], []
    moving_seconds = 0
    first = last = previous_car = None
    previous_signals = (False, False)
    previous_standstill = None
    nav_key = previous_nav_distance = previous_lane = None
    speed = 0
    counts = Counter()
    active_curve = False
    strongest = []
    for segment in sorted(folder.glob('*--*'), key=lambda p: int(p.name.rsplit('--', 1)[1])):
        files = sorted(segment.glob('rlog*')) or sorted(segment.glob('qlog*'))
        if not files:
            continue
        row = {'segment': int(segment.name.rsplit('--', 1)[1]), 'readable': False}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                for event in LogReader(str(files[0])):
                    kind = event.which()
                    services[kind] += 1
                    t = event.logMonoTime / 1e9
                    first = t if first is None else min(first, t)
                    last = t if last is None else max(last, t)
                    if kind == 'carState':
                        car = event.carState
                        speed = float(car.vEgo)
                        speeds.append(speed)
                        if previous_car is not None and speed > .5:
                            moving_seconds += max(0, min(.2, t-previous_car))
                        previous_car = t
                        signals = (bool(car.leftBlinker), bool(car.rightBlinker))
                        counts['turn_signal_activations'] += sum(now and not before for now, before in zip(signals, previous_signals))
                        previous_signals = signals
                        stopped = bool(car.standstill)
                        if previous_standstill is not None and stopped != previous_standstill:
                            counts['stop_events' if stopped else 'resume_events'] += 1
                        previous_standstill = stopped
                    elif kind == 'modelV2':
                        model = event.modelV2
                        samples = [abs(float(y))/max(speed, 3) for dt, y in zip(model.orientationRate.t, model.orientationRate.z) if 1 <= dt <= 5]
                        if samples and speed > 3:
                            curvature = max(samples)
                            curvatures.append(curvature)
                            if curvature > 1/150 and not active_curve:
                                counts['curve_proxy_events'] += 1
                                strongest.append({'log_monotonic_seconds': t, 'max_curvature_per_meter': curvature})
                                active_curve = True
                            elif curvature < 1/300:
                                active_curve = False
                        lane = str(model.meta.laneChangeState)
                        if lane != previous_lane and lane not in ('off', '0'):
                            counts['lane_change_state_transitions'] += 1
                        previous_lane = lane
                    elif kind == 'navInstruction' and event.valid:
                        nav = event.navInstruction
                        key = (str(nav.maneuverType), str(nav.maneuverModifier))
                        distance = float(nav.maneuverDistance)
                        if key != nav_key or (previous_nav_distance is not None and distance > previous_nav_distance+100):
                            counts['navigation_maneuvers'] += 1
                        counts['arrival_messages'] += nav.maneuverType == 'arrive'
                        nav_key, previous_nav_distance = key, distance
                row['readable'] = True
            except Exception as error:
                row.update(error_type=type(error).__name__, error=str(error))
        row["warnings"] = [str(w.message) for w in caught]
        segments.append(row)
    def distribution(values):
        return dict(zip(['min', 'p50', 'p90', 'p99', 'max'], map(float, np.percentile(values, [0, 50, 90, 99, 100])))) if values else None
    return {'purpose': 'Offline route richness; never influences runtime generation or human musical ranking',
            'duration_seconds': None if first is None else last-first,
            'moving_seconds': moving_seconds, 'speed_meters_per_second': distribution(speeds),
            'curvature_proxy_per_meter': distribution(curvatures),
            'curve_proxy_policy': 'Model predicted max abs yaw-rate / current speed over 1–5 s; speed >3 m/s; enter radius<150m, release radius>300m. Proxy, not annotated road truth.',
            'events': dict(counts), 'strongest_curve_proxy_onsets': sorted(strongest, key=lambda x: -x['max_curvature_per_meter'])[:5],
            'services': dict(services), 'segments': segments,
            'required_messages_present': all(services[x] > 0 for x in ['modelV2', 'carState', 'roadEncodeIdx']),
            'navigation_present': services['navInstruction'] > 0,
            'all_available_logs_readable': bool(segments) and all(s['readable'] and not s.get('warnings') for s in segments)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    for folder in sorted(args.root.iterdir()):
        if folder.is_dir():
            result = characterize(folder)
            (folder / 'characterization.json').write_text(json.dumps(result, indent=2))
            print(folder.name, result['duration_seconds'], result['all_available_logs_readable'], flush=True)
