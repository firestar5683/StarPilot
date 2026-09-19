"""Audition one deterministic quality retry of an existing offline continuation."""
import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'prototype'))
from hook_planning import PlanRequest, digest, validate_prepared
from host_hook_adapter import HostHookAdapter
from quality_gate import HOOK_POLICY, inspect, reroll_seed
from window_policy import retained_end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=Path, required=True)
    parser.add_argument('--assets-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads((args.batch / 'validation.json').read_text())
    session = report['runs'][0]
    entry = session['windows'][1]
    plan = args.batch / 'plans' / entry['plan_key']
    request = PlanRequest(**json.loads((plan / 'prepared.json').read_text())['request'])
    if request.plan_index != 1 or request.section != 'verse' or request.prefix_seconds != 8:
        raise ValueError('This diagnostic requires the first continuation and its original prefix')
    adapter = HostHookAdapter(args.assets_root)
    identity = adapter.fingerprints()
    if identity != dict(model_fingerprint=request.model_fingerprint,
                        preparation_fingerprint=request.preparation_fingerprint):
        raise ValueError('Model or preparation implementation changed since the source batch')
    args.output.mkdir(parents=True, exist_ok=False)
    prefix = np.load(plan / 'sampler_clean_src_latents.npy')[:, :200]
    prefix_file = args.output / 'original_prefix.npy'
    np.save(prefix_file, prefix)
    if digest(prefix_file) != request.committed_prefix_sha256:
        raise ValueError('Saved plan prefix differs from its original committed prefix hash')
    hashes = validate_prepared(request, plan, {'committed_prefix': prefix_file})
    chosen = reroll_seed(entry['sample_seed'], 1)
    provenance = {'session_seed': session['generation_seed'], 'sample_seed': entry['sample_seed'],
                  'retry_seed': chosen, 'attempt': 1, 'plan_key': request.cache_key,
                  'prepared_hashes': hashes, 'prompt_changed': False,
                  'backend': 'Mac MLX diagnostic; not native bit equivalence',
                  'scope': 'Original initial window plus first bounded deterministic continuation retry only'}
    (args.output / 'retry.json').write_text(json.dumps(provenance, indent=2))
    adapter._load()
    import soundfile as sf
    import torch
    h = adapter.handler
    def tensor(name):
        return torch.from_numpy(np.load(plan / (name + '.npy'), allow_pickle=False)).to(h.device)
    started = time.monotonic()
    generated = h._mlx_run_diffusion(
        encoder_hidden_states=tensor('encoder_hidden_states'),
        encoder_attention_mask=tensor('encoder_attention_mask'),
        context_latents=tensor('context_latents'),
        src_latents=torch.zeros((1, 1125, 64), device=h.device), seed=chosen,
        shift=1., infer_steps=8, dcw_enabled=False, disable_tqdm=True,
        repaint_mask=tensor('sampler_repaint_mask'),
        clean_src_latents=tensor('sampler_clean_src_latents'),
        repaint_crossfade_frames=12, repaint_injection_ratio=.5)
    provenance['generation_seconds'] = time.monotonic() - started
    started = time.monotonic()
    latent = generated['target_latents']
    wave = h._mlx_vae_decode(latent.transpose(1, 2)).float().cpu().numpy()[0].T
    provenance['decoder_seconds'] = time.monotonic() - started
    frames, endpoint = retained_end(wave, 48000, 8, 36)
    committed = wave[:frames * 1920]
    sf.write(args.output / 'committed_raw.wav', committed, 48000, subtype='FLOAT')
    sf.write(args.output / 'continuation.wav', committed[8*48000:] * np.float32(.65), 48000, subtype='FLOAT')
    initial, rate = sf.read(args.batch / 'session_1' / '00_initial.wav', dtype='float32', always_2d=True)
    if rate != 48000:
        raise ValueError('Unexpected initial sample rate')
    overlap = 2 * rate
    alpha = np.linspace(0, 1, overlap)[:, None]
    initial[-overlap:] = initial[-overlap:] * (1-alpha) + committed[6*rate:8*rate] * np.float32(.65) * alpha
    joined = np.concatenate([initial, committed[8*rate:] * np.float32(.65)])
    sf.write(args.output / 'joined_audition.wav', joined, rate, subtype='FLOAT')
    provenance['endpoint'] = endpoint
    provenance['quality'] = inspect(committed, rate, 8, role='verse', policy=HOOK_POLICY)
    (args.output / 'retry.json').write_text(json.dumps(provenance, indent=2))
    print(json.dumps(provenance), flush=True)


if __name__ == '__main__':
    main()
