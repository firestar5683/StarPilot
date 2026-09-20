"""Bounded offline Mac initials from the exact current native conditioning bank.

Uses the official Torch DiT layers with native exported FP16 weights and explicit
native masks/time/rotary inputs. MPS arithmetic and FP32 VAE decoding differ from
Chestnut: this is a listening shortlist, never an exact cross-backend replay.
No planner, download, route reader, audio device, or hardware connection is used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                  TOKENIZERS_PARALLELISM='false', PYTORCH_ENABLE_MPS_FALLBACK='1')
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'prototype'))
from cached_composition import validate_bank
from generation_seed import sample_seed
from host_hook_adapter import HostHookAdapter
from quality_gate import HOOK_POLICY, inspect
from window_policy import retained_end

BANK_SHA256 = 'd8570881b873a093ea509cafd8592e6b78ced880e9cc00d8f5fbfc8e67e39daf'
BASELINE = 1496885951


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def array_digest(value):
    return hashlib.sha256(value.tobytes()).hexdigest()


def time_features(value):
    # Same NumPy FP16 feature construction as native_ace.time_features.
    f = np.exp(-np.log(10000) * np.arange(128, dtype=np.float32) / 128)
    v = np.asarray(value, dtype=np.float32).reshape(-1, 1) * 1000 * f[None, :]
    return np.concatenate((np.cos(v), np.sin(v)), -1).astype(np.float16)


class Reference:
    def __init__(self, assets, cond, context, valid):
        import torch
        from diffusers import AutoencoderOobleck
        from safetensors import safe_open
        model_root = assets / 'experiments/composition_20260916/models/ace/checkpoints'
        exports = assets / 'experiments/ace_chestnut_20260916'
        sys.path.insert(0, str(model_root / 'acestep-v15-turbo'))
        from configuration_acestep_v15 import AceStepConfig
        from modeling_acestep_v15_turbo import AceStepDiTModel
        self.torch = torch
        config = AceStepConfig.from_pretrained(model_root / 'acestep-v15-turbo', local_files_only=True)
        config._attn_implementation = 'sdpa'
        with torch.device('meta'):
            self.model = AceStepDiTModel(config)
        weights = {p.stem: torch.from_numpy(np.load(p, allow_pickle=False))
                   for p in sorted((exports / 'weights').glob('*.npy'))}
        # Prove that the exported native DiT tensors are this bank's checkpoint.
        with safe_open(str(model_root / 'acestep-v15-turbo/model.safetensors'), framework='pt', device='cpu') as source:
            expected = {key.removeprefix('decoder.') for key in source.keys() if key.startswith('decoder.')}
            if set(weights) != expected:
                raise ValueError('Incomplete or unexpected native DiT export')
            for name, value in weights.items():
                if value.dtype != torch.float16 or not torch.equal(value, source.get_tensor('decoder.' + name).half()):
                    raise ValueError('Native DiT export differs from matching checkpoint: ' + name)
        self.model.load_state_dict(weights, assign=True)
        # Rotary values are supplied explicitly below, so discard the meta buffer.
        self.model.rotary_emb = torch.nn.Identity()
        self.model = self.model.to('mps').eval()
        del weights
        vae = AutoencoderOobleck.from_pretrained(model_root / 'vae', local_files_only=True).eval()
        for module in vae.decoder.modules():
            if hasattr(module, 'weight_g'):
                torch.nn.utils.remove_weight_norm(module)
        decoder_weights = {p.stem: torch.from_numpy(np.load(p, allow_pickle=False))
                           for p in sorted((exports / 'vae_weights').glob('*.npy'))}
        reference_weights = vae.decoder.state_dict()
        if set(decoder_weights) != set(reference_weights):
            raise ValueError('Incomplete or unexpected native VAE export')
        for name, value in decoder_weights.items():
            if value.dtype != torch.float16 or not torch.equal(value, reference_weights[name].half()):
                raise ValueError('Native VAE export differs from matching checkpoint: ' + name)
        vae.decoder.load_state_dict(decoder_weights, assign=True)
        self.decoder = vae.decoder.float().to('mps').eval()
        del vae, decoder_weights, reference_weights
        self.cond = self.tensor(cond)
        self.context = self.tensor(context)
        self.cross_mask = self.tensor(np.where(valid[:, None, None, :], 0, -np.inf).astype(np.float16))
        n = context.shape[1] // 2
        positions = np.arange(n, dtype=np.float32)[:, None]
        freq = positions / (1000000 ** (np.arange(0, 128, 2, dtype=np.float32) / 128))[None, :]
        freq = np.concatenate((freq, freq), -1)[None]
        self.rotary = (self.tensor(np.cos(freq).astype(np.float16)), self.tensor(np.sin(freq).astype(np.float16)))
        index = np.arange(n)
        self.local_mask = self.tensor(np.where(abs(index[:, None] - index[None, :]) <= 128, 0, -np.inf).astype(np.float16)[None, None])

    def tensor(self, value):
        return self.torch.from_numpy(value).to('mps')

    def velocity(self, latent, timestep):
        """Official layers with the exact masks/features used by native_ace.DiT.

        The vendor model.forward resets caller masks, so use its layers directly
        to retain the native padded-conditioning mask without changing vendor code.
        """
        m = self.model
        torch = self.torch
        def embedding(block, value):
            z = block.linear_2(block.act1(block.linear_1(self.tensor(time_features([value])))))
            return z, block.time_proj(block.act2(z)).reshape(1, 6, 2048)
        t, projection = embedding(m.time_embed, timestep)
        r, projection_r = embedding(m.time_embed_r, 0)
        hidden = m.proj_in(torch.cat((self.context, latent), dim=-1))
        condition = m.condition_embedder(self.cond)
        for index, layer in enumerate(m.layers):
            hidden = layer(hidden, self.rotary, projection + projection_r,
                           attention_mask=self.local_mask if index % 2 == 0 else None,
                           encoder_hidden_states=condition, encoder_attention_mask=self.cross_mask,
                           use_cache=False)[0]
        shift, scale = (m.scale_shift_table + (t + r).unsqueeze(1)).chunk(2, dim=1)
        return m.proj_out((m.norm_out(hidden) * (1 + scale) + shift).type_as(hidden))

    def generate(self, noise, progress):
        torch = self.torch
        started = time.monotonic()
        with torch.inference_mode():
            x = self.tensor(noise)
            for i, timestep in enumerate(np.linspace(1, 0, 9)[:-1]):
                step = time.monotonic()
                x = x - self.velocity(x, float(timestep)) * .125
                torch.mps.synchronize()
                if not torch.isfinite(x).all().item():
                    raise ValueError('Nonfinite diffusion latent')
                progress(dict(step=i, seconds=time.monotonic() - step))
            latent = x.cpu().numpy()
            diffusion = time.monotonic() - started
            started = time.monotonic()
            # Native ChunkDecoder layout: 375-frame windows, 250-frame core.
            n, window, core = latent.shape[1], 375, 250
            halo = (window - core) // 2
            parts = []
            for start in range(0, n, core):
                left = max(0, min(start - halo, n - window))
                end = min(start + core, n)
                chunk = self.tensor(latent[:, left:left + window].transpose(0, 2, 1).copy()).float()
                decoded = self.decoder(chunk).cpu().numpy()[0].T
                parts.append(decoded[(start - left) * 1920:(end - left) * 1920])
            wave = np.concatenate(parts)
            decode = time.monotonic() - started
        return wave, latent, diffusion, decode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets-root', type=Path, required=True)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', type=int, nargs='+', default=[BASELINE, 3277374468])
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if not 1 <= len(args.seeds) <= 2 or args.seeds[0] != BASELINE or any(not 0 <= n < 2**32 for n in args.seeds):
        parser.error('One or two uint32 seeds, beginning with native baseline1496885951, are required')
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'verifying_inputs', 'backend': 'Mac PyTorch MPS; exported FP16 DiT; exported-weight FP32 VAE',
              'cross_backend_guarantee': False, 'musical_acceptance': 'pending user listening; no best seed selected',
              'composition_policy': 'hook-cache-v1', 'profile': 'prism', 'presentation_policy': 'conservative-v3',
              'presentation_scope': 'isolated core audio, gain0.65; route DSP/UI/synchronization require native verification',
              'sampler': {'steps': 8, 'method': 'Euler', 'schedule': np.linspace(1, 0, 9).tolist(), 'shift': 1.,
                          'dcw_enabled': False, 'time_embed_r_value': 0., 'noise': 'NumPy default_rng PCG64 standard_normal cast FP16',
                          'model_seconds': 30, 'target_commit_seconds': 28, 'prefix_seconds': 0, 'rerolls_in_this_audition': 0},
              'runs': [], 'source_sha256': {p.name: digest(p) for p in [Path(__file__), HERE / 'native_ace.py', HERE / 'ace_runtime.py',
                  HERE / 'chunk_decode.py', HERE / 'quality_gate.py', HERE / 'window_policy.py', HERE.parents[1] / 'prototype/generation_seed.py']}}
    def save():
        (args.output / 'audition.json').write_text(json.dumps(report, indent=2))
    save()
    try:
        if digest(args.bank / 'bank.json') != BANK_SHA256:
            raise ValueError('Exact current-native bank missing: expected ' + BANK_SHA256)
        manifest = validate_bank(args.bank, 'prism')
        identities = HostHookAdapter(args.assets_root, preparation_only=True).fingerprints()
        if any(identities[key] != manifest['roles']['initial']['request'][key] for key in identities):
            raise ValueError('Local checkpoint/preparation fingerprints differ from exact bank')
        initial = args.bank / 'initial'
        cond = np.load(initial / 'encoder_hidden_states.npy', allow_pickle=False).astype(np.float16)
        context = np.load(initial / 'context_latents.npy', allow_pickle=False).astype(np.float16)
        valid = np.load(initial / 'encoder_attention_mask.npy', allow_pickle=False).astype(bool)
        if context.shape != (1, 750, 128) or (initial / 'sampler_repaint_mask.npy').exists():
            raise ValueError('Expected unpainted30s native initial')
        width = max(256, ((cond.shape[1] + 31) // 32) * 32)
        pad = width - cond.shape[1]
        cond = np.pad(cond, ((0, 0), (0, pad), (0, 0)))
        valid = np.pad(valid, ((0, 0), (0, pad)))
        import torch
        import mlx.core as mx
        import soundfile as sf
        import acestep
        if not torch.backends.mps.is_available():
            raise RuntimeError('MPS is unavailable')
        expected_package = args.assets_root / 'experiments/composition_20260916/vendor/ACE-Step-1.5/acestep'
        if Path(acestep.__file__).resolve().parent != expected_package.resolve():
            raise ValueError('ACE import differs from fingerprinted package')
        report.update(status='inputs_verified', conditioning_bank=str(args.bank), conditioning_bank_sha256=BANK_SHA256,
                      model_fingerprints=identities, conditioning_tensor_sha256=manifest['roles']['initial']['sha256'],
                      versions={'numpy': np.__version__, 'torch': torch.__version__, 'mlx': str(mx.__file__), 'soundfile': sf.__version__},
                      prepared_inputs={name: {'shape': list(a.shape), 'dtype': str(a.dtype), 'sha256': array_digest(a)}
                                       for name, a in [('encoder_hidden_states', cond), ('context_latents', context), ('encoder_attention_mask', valid)]})
        save()
        if args.check_only:
            return
        started = time.monotonic()
        reference = Reference(args.assets_root, cond, context, valid)
        report.update(status='generating', exported_weights_match_checkpoint=True, model_load_seconds=time.monotonic() - started)
        save()
        for session_seed in args.seeds:
            directory = args.output / str(session_seed)
            directory.mkdir()
            noise_seed = sample_seed(session_seed, 'prepare', 0)
            noise = np.random.default_rng(noise_seed).standard_normal((1, 750, 64)).astype(np.float16)
            np.save(directory / 'noise.npy', noise)
            row = {'session_seed': session_seed, 'sample_seed': noise_seed, 'phase': 'prepare', 'index': 0,
                   'noise_sha256': array_digest(noise), 'attempt': 0, 'steps': [], 'status': 'generating'}
            report['runs'].append(row)
            save()
            def progress(value):
                row['steps'].append(value)
                save()
                print(json.dumps({'session_seed': session_seed, **value}), flush=True)
            wave, latent, generation, decode = reference.generate(noise, progress)
            endpoint_error = None
            try:
                frames, endpoint = retained_end(wave, 48000, 0, 28)
            except ValueError as error:
                frames, endpoint_error = 700, str(error)
                endpoint = {'rejected': endpoint_error}
            committed = wave[:frames * 1920]
            quality = inspect(committed, 48000, 0, role='initial', policy=HOOK_POLICY, endpoint_error=endpoint_error)
            sf.write(directory / 'initial_raw.wav', committed, 48000, subtype='FLOAT')
            sf.write(directory / 'initial_listen.wav', committed * np.float32(.65), 48000, subtype='FLOAT')
            np.save(directory / 'committed_latents.npy', latent[:, :frames])
            row.update(status='technical_pass_listening_pending' if quality['accepted'] else 'quality_rejected_no_reroll',
                       generation_seconds=generation, decode_seconds=decode, endpoint=endpoint, quality=quality,
                       committed_seconds=len(committed) / 48000, raw_pcm_sha256=array_digest(committed),
                       raw_peak=float(np.abs(committed).max()), listen_file=str(directory / 'initial_listen.wav'))
            save()
            print(json.dumps({'session_seed': session_seed, 'status': row['status'], 'seconds': generation + decode}), flush=True)
        report['status'] = 'complete_listening_pending'
        save()
    except Exception as error:
        report.update(status='stopped', error=str(error))
        save()
        raise


if __name__ == '__main__':
    main()
