"""Read-only post-run acceptance checks. Never used to drive the score."""
import argparse
import json
from pathlib import Path


def audit(run):
    def read(name):
        p = run / name
        return json.loads(p.read_text()) if p.exists() else {}

    def rows(name):
        p = run / name
        return [json.loads(line) for line in p.read_text().splitlines() if line] if p.exists() else []

    launch, summary, bridge = (read(n) for n in ('launch.json', 'summary.json', 'bridge.json'))
    trace, jobs, blocks, ui = (rows(n) for n in ('trace.jsonl', 'jobs.jsonl', 'host_audio.jsonl', 'ui_audit.jsonl'))
    accepted = [g for g in summary.get('generation', []) if g.get('quality_accepted') is True]
    violations = [j for j in jobs if any(t > j.get('cutoff_ns', -1) for t in j.get('input_times', {}).values())]
    last_ui = ui[-1] if ui else {}
    checks = {
        'native_eof': launch.get('end_reason') == 'native final segment exhausted',
        'bridge_clean': bool(bridge) and bridge.get('failure') is None,
        'fresh_generation': bool(accepted),
        'captured_audio': summary.get('audio_seconds', 0) > 0,
        'no_underflow': summary.get('underflows') == 0,
        'no_emergency_fallback': summary.get('emergency_fallbacks') == 0,
        'worker_healthy_throughout': bool(trace) and not any(t.get('worker_failed') for t in trace),
        'causal_requests': bool(jobs) and not violations,
        'muted_launch': launch.get('muted') is True,
        'muted_blocks': bool(blocks) and all(b.get('muted') is True for b in blocks),
        'no_output_flags': bool(blocks) and all(not b.get('portaudio_status') for b in blocks),
        'camera': last_ui.get('accepted_camera_frames', 0) > 0,
        'path': last_ui.get('nonempty_path_draws', 0) > 0,
        'lanes': last_ui.get('nonempty_lane_draws', 0) > 0,
    }
    return {
        'checks': checks, 'instrumented_pass': all(checks.values()),
        'audio_seconds': summary.get('audio_seconds'), 'accepted_jobs': len(accepted),
        'accepted_music_holds': summary.get('accepted_music_holds'),
        'navigation_present': any(t.get('nav', {}).get('valid') for t in trace),
        'curve_activations': len({t['activation'] for t in trace if t.get('activation') is not None and t.get('kind') == 'curve'}),
        'input_time_violations': len(violations), 'ui_last': last_ui,
        'bridge': bridge,
        'limitations': 'Instrumented evidence only; musical quality, speakers, Bluetooth and live driving are not verified.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    result = audit(args.run)
    (args.run / 'event_replay_audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
