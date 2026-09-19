"""Offline Mac audition of fresh session plans; never opens an audio device."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'prototype'))
from generation_seed import sample_seed
from hook_planning import PlanCache, digest, next_section, request_plan
from host_hook_adapter import HostHookAdapter
from quality_gate import inspect
from session_seed import select_session
from window_policy import retained_end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sessions', type=int, default=3)
    parser.add_argument('--windows', type=int, default=4)
    parser.add_argument('--session-manifest', type=Path, help='Retry preparation with the already recorded fresh sessions')
    parser.add_argument('--resume', action='store_true', help='Continue a paused batch without rerunning accepted windows')
    parser.add_argument('--max-new-windows', type=int, default=0, help='Bound Mac model residency per process; zero runs the entire batch')
    args = parser.parse_args()
    if args.sessions < 2 or args.windows < 1:
        parser.error('Use multiple fresh sessions and at least one window')
    args.output.mkdir(parents=True, exist_ok=args.resume)
    sessions = (json.loads(args.session_manifest.read_text())['sessions'] if args.session_manifest
                else [select_session() for _ in range(args.sessions)])
    if len(sessions) != args.sessions or any(s.get('seed_origin') != 'fresh-session' for s in sessions):
        raise ValueError('Expected the complete original fresh-session batch')
    for session in sessions:
        select_session(session['generation_seed'])
    report = {'sessions': sessions, 'backend': 'Mac MLX offline; not native runtime equivalence',
              'seed_selection': 'normal fresh-session selector; no rerolls or seed shopping',
              'musical_acceptance': 'pending listening; energy checks cannot establish hook quality',
              'retry_of': str(args.session_manifest) if args.session_manifest else None,
              'runs': [], 'status': 'starting'}
    if args.resume:
        report = json.loads((args.output / 'validation.json').read_text())
        sessions = report['sessions']
        report['status'] = 'resuming'

    def save():
        (args.output / 'validation.json').write_text(json.dumps(report, indent=2))

    save()
    adapter = HostHookAdapter(args.assets_root)
    identities = adapter.fingerprints()
    cache = PlanCache(args.output / 'plans')
    import torch
    import soundfile as sf
    generated_windows = 0
    for session_index, session in enumerate(sessions):
        seed = session['generation_seed']
        run = args.output / f'session_{session_index + 1}'
        run.mkdir(exist_ok=args.resume)
        if session_index < len(report['runs']):
            entry = report['runs'][session_index]
        else:
            entry = dict(session, windows=[], status='preparing')
            report['runs'].append(entry)
        if entry['status'] in ('quality_failed', 'technical_pass_listening_pending'):
            continue
        sources, previous_plan, pieces = {}, None, []
        completed = len(entry['windows'])
        if completed:
            sources = {'hook_reference': run / 'hook_reference.wav', 'committed_prefix': run / 'prefix.npy'}
            previous_plan = entry['windows'][-1]['plan_key']
            audio, rate = sf.read(run / 'core.wav', dtype='float32', always_2d=True)
            if rate != 48000:
                raise ValueError('Unexpected resumed sample rate')
            pieces = [audio / np.float32(.65)]
        for index in range(completed, args.windows):
            if shutil.disk_usage(args.output).free < 1024**3:
                raise RuntimeError('Less than 1 GiB free; refusing another model window')
            role = 'initial' if index == 0 else next_section(index - 1)
            window = 30 if index == 0 else 45
            request = request_plan(session_seed=seed, plan_index=index, profile='prism',
                section=role, window_seconds=window, **identities,
                hook_reference_sha256=digest(sources['hook_reference']) if sources else None,
                committed_prefix_sha256=digest(sources['committed_prefix']) if sources else None,
                previous_plan_sha256=previous_plan)
            tick = time.monotonic()
            plan, hit = cache.resolve(request, adapter, sources=sources)
            plan_seconds = time.monotonic() - tick
            h = adapter.handler
            def tensor(name):
                return torch.from_numpy(np.load(plan / (name + '.npy'), allow_pickle=False)).to(h.device)
            noise_seed = sample_seed(seed, 'prepare', index)
            kwargs = dict(encoder_hidden_states=tensor('encoder_hidden_states'),
                encoder_attention_mask=tensor('encoder_attention_mask'), context_latents=tensor('context_latents'),
                src_latents=torch.zeros((1, window * 25, 64), device=h.device), seed=noise_seed,
                shift=1., infer_steps=8, dcw_enabled=False, disable_tqdm=True)
            if index:
                kwargs.update(repaint_mask=tensor('sampler_repaint_mask'),
                    clean_src_latents=tensor('sampler_clean_src_latents'),
                    repaint_crossfade_frames=12, repaint_injection_ratio=.5)
            tick = time.monotonic()
            generated = h._mlx_run_diffusion(**kwargs)
            latent = generated['target_latents']
            diffusion_seconds = time.monotonic() - tick
            tick = time.monotonic()
            wave = h._mlx_vae_decode(latent.transpose(1, 2)).float().cpu().numpy()[0].T
            decode_seconds = time.monotonic() - tick
            frames, endpoint = retained_end(wave, 48000, request.prefix_seconds, 28 if index == 0 else 36)
            committed = wave[:frames * 1920]
            quality = inspect(committed, 48000, request.prefix_seconds, role=role)
            new = committed[request.prefix_seconds * 48000:]
            sf.write(run / f'{index:02d}_{role}.wav', new * np.float32(.65), 48000, subtype='FLOAT')
            np.save(run / 'prefix.npy', latent.detach().float().cpu().numpy()[:, frames-200:frames])
            if index == 0:
                sf.write(run / 'hook_reference.wav', committed, 48000, subtype='FLOAT')
            sources = {'hook_reference': run / 'hook_reference.wav', 'committed_prefix': run / 'prefix.npy'}
            previous_plan = request.cache_key
            if pieces:
                overlap = 2 * 48000
                prefix = request.prefix_seconds * 48000
                alpha = np.linspace(0, 1, overlap)[:, None]
                pieces[-1][-overlap:] = pieces[-1][-overlap:] * (1-alpha) + committed[prefix-overlap:prefix] * alpha
            pieces.append(new)
            sf.write(run / 'core.wav', np.concatenate(pieces) * np.float32(.65), 48000, subtype='FLOAT')
            entry['windows'].append(dict(index=index, role=role, sample_seed=noise_seed,
                semantic_seed=request.semantic_seed, plan_key=request.cache_key, cache_hit=hit,
                plan_seconds=plan_seconds, generation_seconds=diffusion_seconds, decode_seconds=decode_seconds,
                endpoint=endpoint, quality=quality, raw_pcm_sha256=hashlib.sha256(new.tobytes()).hexdigest()))
            save()
            print(json.dumps({'session': session_index + 1, 'window': index, 'role': role,
                              'quality_pass': quality['accepted'], 'generation_seconds': diffusion_seconds}), flush=True)
            if not quality['accepted']:
                entry['status'] = 'quality_failed'
                break
            import gc
            import mlx.core as mx
            del generated, latent, wave, committed, kwargs
            gc.collect()
            torch.mps.empty_cache()
            mx.clear_cache()
            generated_windows += 1
            if args.max_new_windows and generated_windows >= args.max_new_windows:
                if len(entry['windows']) == args.windows:
                    entry['status'] = 'technical_pass_listening_pending'
                report['status'] = 'paused_after_bounded_host_batch'
                save()
                return
        sf.write(run / 'core.wav', np.concatenate(pieces) * np.float32(.65), 48000, subtype='FLOAT')
        if entry['status'] != 'quality_failed':
            entry['status'] = 'technical_pass_listening_pending'
        save()
    report['status'] = 'complete'
    save()


if __name__ == '__main__':
    main()
