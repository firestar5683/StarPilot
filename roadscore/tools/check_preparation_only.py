"""Exactly two real semantic preparations; no diffusion, cache hits, or device access."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'prototype'), str(ROOT / 'experiments/ace_chestnut_20260916')]
from hook_planning import PlanRequest
from host_hook_adapter import HostHookAdapter, PreparationOnlyDecoder


def compare(reference, actual):
    result = {}
    for name in ('encoder_hidden_states', 'encoder_attention_mask', 'context_latents'):
        before = np.load(reference / (name + '.npy'), allow_pickle=False)
        after = np.load(actual / (name + '.npy'), allow_pickle=False)
        if before.shape != after.shape:
            raise ValueError('Conditioning shape changed: ' + name)
        delta = before.astype(np.float64) - after.astype(np.float64)
        result[name] = {'shape': list(after.shape), 'exact': bool(np.array_equal(before, after)),
                        'max_absolute_error': float(np.max(np.abs(delta))),
                        'rms_error': float(np.sqrt(np.mean(delta * delta)))}
    old = json.loads((reference / 'semantic_plan.json').read_text())
    new = json.loads((actual / 'semantic_plan.json').read_text())
    result['semantic_codes_equal'] = old['audio_codes'] == new['audio_codes']
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--assets-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    original = PlanRequest(**json.loads((args.reference / 'prepared.json').read_text())['request'])
    if original.plan_index != 0 or original.prefix_seconds or original.hook_reference_sha256:
        raise ValueError('This bounded check only accepts the saved initial request')
    args.out.mkdir(parents=True, exist_ok=False)
    report = {'reference': str(args.reference), 'runs': [], 'audio_diffusion_permitted': False}
    try:
        adapter = HostHookAdapter(args.assets_root, preparation_only=True)
        identity = adapter.fingerprints()
        if identity['model_fingerprint'] != original.model_fingerprint:
            raise ValueError('Model assets differ from the original request')
        request = replace(original, **identity)
        report.update(original_request=original.identity(), request=request.identity())
        for label in ('cold', 'warm'):
            output = args.out / label
            output.mkdir()
            started = time.monotonic()
            adapter(request, {}, output)  # Bypass PlanCache: both calls perform real preparation.
            elapsed = time.monotonic() - started
            if not isinstance(adapter.handler.mlx_decoder, PreparationOnlyDecoder):
                raise RuntimeError('Preparation-only decoder was not retained')
            prepared = json.loads((output / 'prepared.json').read_text())
            if prepared['audio_diffusion_called'] or not prepared['host_preparation_only']:
                raise RuntimeError('Unexpected preparation provenance')
            import mlx.core as mx
            result = {'phase': label, 'seconds': elapsed,
                      'process_peak_rss_bytes_macos': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      'mlx_active_bytes_after': mx.get_active_memory(),
                      'comparison_to_original': compare(args.reference, output)}
            if label == 'warm': result['comparison_to_cold'] = compare(args.out / 'cold', output)
            report['runs'].append(result)
            (args.out / 'comparison.json').write_text(json.dumps(report, indent=2))
            print(label, elapsed, 'seconds; comparisons saved', flush=True)
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        (args.out / 'comparison.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
