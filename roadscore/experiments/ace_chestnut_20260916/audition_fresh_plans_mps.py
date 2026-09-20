"""Three bounded Mac song auditions with fresh semantic plans, preserving every attempt.

Prepare and render are separate processes so the musical planner is unloaded before
the verified native-weight MPS decoder loads. No route input, audio output, network,
hardware access, automatic rerolls, or changes to the runtime conditioning bank.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import secrets
import sys
import time

os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                  HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false',
                  PYTORCH_ENABLE_MPS_FALLBACK='1')
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'prototype'))
from hook_planning import PlanCache, PlanRequest, digest, request_plan, validate_prepared
from host_hook_adapter import HostHookAdapter
from generation_seed import sample_seed
from quality_gate import HOOK_POLICY, inspect
from window_policy import retained_end


def save(root, report):
    report['peak_process_rss_bytes'] = max(report.get('peak_process_rss_bytes', 0),
                                         resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    (root / 'audition.json').write_text(json.dumps(report, indent=2))


def prepare(args):
    args.output.mkdir(parents=True, exist_ok=False)
    seeds = [secrets.randbits(32) for _ in range(3)]
    if len(set(seeds)) != 3:
        raise RuntimeError('Fresh-seed collision; do not silently substitute candidates')
    report = dict(status='preparing', profile='prism', attempts_per_song=1,
                  preparation='Fresh actual semantic plan for each song; same current v4 groove prompt',
                  backend='Mac preparation-only MLX planner, then official Torch MPS DiT with native exported weights',
                  listening_scope='Opening excerpts only; no route, continuations, gestures or presentation DSP',
                  gain=.65, musical_acceptance='User listening required; no winner selected',
                  source_sha256={p.name: digest(p) for p in (Path(__file__), HERE/'host_hook_adapter.py',
                      HERE/'audition_cached_initial_mps.py', HERE.parents[1]/'prototype/hook_planning.py')},
                  songs=[dict(label=f'Song {i+1}', session_seed=seed, attempt=0, status='registered')
                         for i, seed in enumerate(seeds)])
    save(args.output, report)
    started = time.monotonic()
    try:
        adapter = HostHookAdapter(args.assets_root, preparation_only=True)
        identities = adapter.fingerprints()
        report['model_fingerprints'] = identities
        cache = PlanCache(args.output/'plans')
        for row in report['songs']:
            request = request_plan(session_seed=row['session_seed'], plan_index=0,
                profile='prism', section='initial', window_seconds=30, **identities)
            row.update(status='preparing', semantic_seed=request.semantic_seed, request=request.identity())
            save(args.output, report)
            tick = time.monotonic()
            directory, hit = cache.resolve(request, adapter)
            plan = json.loads((directory/'semantic_plan.json').read_text())
            row.update(status='prepared', plan_key=request.cache_key, plan_seconds=time.monotonic()-tick,
                       plan_cache_hit=hit, plan_sha256=digest(directory/'semantic_plan.json'),
                       audio_codes_sha256=hashlib.sha256(plan['audio_codes'].encode()).hexdigest())
            save(args.output, report)
            print(json.dumps({k: row[k] for k in ('label','session_seed','semantic_seed','status','plan_seconds')}), flush=True)
        report.update(status='prepared', preparation_seconds=time.monotonic()-started,
                      preparation_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if len({row['audio_codes_sha256'] for row in report['songs']}) != 3:
            raise ValueError('Planner produced duplicate semantic code sequences; do not claim distinct plans')
        save(args.output, report)
    except BaseException as error:
        report.update(status='preparation_failed', error=repr(error))
        save(args.output, report)
        raise


def render(args):
    from audition_cached_initial_mps import Reference, array_digest
    import soundfile as sf
    report = json.loads((args.output/'audition.json').read_text())
    if report['status'] != 'prepared':
        raise ValueError('Render requires an untouched complete preparation batch')
    started = time.monotonic()
    reference = None
    try:
        report['status'] = 'rendering'
        save(args.output, report)
        for i, row in enumerate(report['songs']):
            directory = args.output / f'song_{i+1}'
            directory.mkdir(exist_ok=False)
            plan = args.output / 'plans' / row['plan_key']
            row['conditioning_sha256'] = validate_prepared(PlanRequest(**row['request']), plan)
            cond = np.load(plan/'encoder_hidden_states.npy', allow_pickle=False).astype(np.float16)
            context = np.load(plan/'context_latents.npy', allow_pickle=False).astype(np.float16)
            valid = np.load(plan/'encoder_attention_mask.npy', allow_pickle=False).astype(bool)
            width = max(256, ((cond.shape[1]+31)//32)*32)
            cond = np.pad(cond, ((0,0),(0,width-cond.shape[1]),(0,0)))
            valid = np.pad(valid, ((0,0),(0,width-valid.shape[1])))
            if context.shape != (1,750,128):
                raise ValueError('Unexpected initial shape')
            if reference is None:
                tick = time.monotonic()
                reference = Reference(args.assets_root, cond, context, valid)
                report['render_model_load_seconds'] = time.monotonic()-tick
            else:
                reference.cond = reference.tensor(cond)
                reference.context = reference.tensor(context)
                reference.cross_mask = reference.tensor(np.where(valid[:,None,None,:],0,-np.inf).astype(np.float16))
            noise_seed = sample_seed(row['session_seed'], 'prepare', 0)
            noise = np.random.default_rng(noise_seed).standard_normal((1,750,64)).astype(np.float16)
            np.save(directory/'noise.npy', noise)
            row.update(status='generating', sample_seed=noise_seed, noise_sha256=array_digest(noise), steps=[])
            save(args.output, report)
            def progress(value):
                row['steps'].append(value)
                save(args.output, report)
                print(json.dumps(dict(label=row['label'], **value)), flush=True)
            wave, latent, generation, decode = reference.generate(noise, progress)
            endpoint_error = None
            try:
                frames, endpoint = retained_end(wave, 48000, 0, 28)
            except ValueError as error:
                frames, endpoint_error = 700, str(error)
                endpoint = {'rejected': endpoint_error}
            committed = wave[:frames*1920]
            quality = inspect(committed, 48000, 0, role='initial', policy=HOOK_POLICY, endpoint_error=endpoint_error)
            sf.write(directory/'raw.wav', committed, 48000, subtype='FLOAT')
            sf.write(directory/'listen.wav', committed*np.float32(.65), 48000, subtype='FLOAT')
            np.save(directory/'committed_latents.npy', latent[:,:frames])
            row.update(status='technical_pass_listening_pending' if quality['accepted'] else 'technical_reject_no_reroll',
                       generation_seconds=generation, decode_seconds=decode, quality=quality,
                       endpoint=endpoint, seconds=len(committed)/48000, raw_pcm_sha256=array_digest(committed),
                       listen_file=str(directory/'listen.wav'), raw_peak=float(np.abs(committed).max()))
            save(args.output, report)
            print(json.dumps({k:row[k] for k in ('label','status','seconds','generation_seconds','decode_seconds')}), flush=True)
        report.update(status='complete_listening_pending', render_seconds=time.monotonic()-started,
                      render_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        save(args.output, report)
        finalize_auditions(args.output, report)
        write_page(args.output, report)
    except BaseException as error:
        report.update(status='render_failed', error=repr(error))
        save(args.output, report)
        raise


def finalize_auditions(root, report):
    """One common gain for every candidate and the reference, with raw PCM retained."""
    import soundfile as sf
    for row in report['songs']:
        path = Path(row['listen_file'])
        original = path.with_name('listen_original_gain_065.wav')
        if original.exists():
            raise FileExistsError('Audition leveling already finalized; preserve it')
        path.rename(original)
        wave, rate = sf.read(path.with_name('raw.wav'), dtype='float32', always_2d=True)
        listen = wave*np.float32(.60)
        if not np.isfinite(listen).all() or np.abs(listen).max() >= 1:
            raise ValueError('Unsafe listening peak; no automatic per-song normalization')
        sf.write(path, listen, rate, subtype='FLOAT')
        row.update(listening_peak=float(np.abs(listen).max()), original_gain_065_file=str(original))
    reference = root.parent/'mac-seeds/mps-initials/1496885951/initial_listen.wav'
    wave, rate = sf.read(reference, dtype='float32', always_2d=True)
    sf.write(root/'reference_A.wav', wave*np.float32(.60/.65), rate, subtype='FLOAT')
    report.update(gain=.60, gain_note='Common0.60 audition gain for all songs and A; original0.65 files and raw generation retained',
                  reference=dict(source=str(reference), sha256=digest(reference), source_gain=.65),
                  finalization_source_sha256=digest(Path(__file__)))
    save(root, report)


def write_page(root, report):
    cards = ''.join(f'''<article><span class="tag">New semantic plan · {r['seconds']:.1f}s</span>
<h2>{r['label']}</h2><audio controls preload="metadata" src="song_{i+1}/listen.wav"></audio>
<p>Seed {r['session_seed']} · {'Technical checks passed' if r['quality']['accepted'] else 'Technical check failed; preserved for review'}</p></article>'''
                    for i,r in enumerate(report['songs']))
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>RoadScore · new songs</title><style>body{margin:0;background:#101317;color:#edf2f7;font:18px system-ui,sans-serif}main{max-width:900px;margin:60px auto;padding:0 24px}h1{font-size:44px;letter-spacing:-1.5px;margin-bottom:12px}p{color:#afbbc8;line-height:1.6}article{border:1px solid #37414b;border-radius:18px;padding:24px;margin:22px 0;background:#191f27}audio{width:100%}.tag{font-size:13px;color:#75e2dc}h2{margin:10px 0 20px}a{color:#75e2dc}</style>
<main><span class="tag">ROADSCORE · PRISM</span><h1>Three new song ideas</h1><p>Each opening has a new musical plan and seed, using the same groove-focused Prism strategy. These are core music only, with the same gain and no added cues. Pick the hook and groove you like; none is selected automatically.</p>''' + cards + '''
<article><span class="tag">Current reference</span><h2>A · current showcase</h2><audio controls preload="metadata" src="reference_A.wav"></audio><p>The earlier A–H set varied the backing under one fixed musical plan. The three above generate new plans.</p></article>
<p>Opening auditions, not complete route scores. A selected new song needs its own matching continuation bank and full-route verification before replacing the preserved demo. Mac arithmetic is not bit-identical to Chestnut.</p></main>
<script>const players=[...document.querySelectorAll('audio')];players.forEach(p=>p.addEventListener('play',()=>players.forEach(q=>{if(q!==p)q.pause()})));</script></html>'''
    (root/'index.html').write_text(page)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('prepare','render'))
    p.add_argument('--assets-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    {'prepare':prepare,'render':render}[args.phase](args)


if __name__ == '__main__':
    main()
