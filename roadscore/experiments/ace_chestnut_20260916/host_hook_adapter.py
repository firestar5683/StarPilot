"""Lazy official Mac semantic planner adapter for hook_planning.PlanCache.

No audio diffusion. Not deployed/validated on native until a combined plan is
approved. Continuation hint+prefix composition is an explicit candidate algorithm.
"""
import json
import hashlib
import os
from pathlib import Path
import random
import sys
import threading

import numpy as np


class Captured(BaseException):
    pass


def finish_capture(completed, result, request, sources, output):
    from hook_planning import validate_prepared
    if not completed:
        raise RuntimeError('Semantic preparation did not reach the completed capture boundary')
    if result is not None and (result.success or str(result.error) != "'outputs'"):
        raise RuntimeError(f'Unexpected result after capture: {result.success}: {result.error}')
    validate_prepared(request, output, sources)


def continuation_inputs(context, prefix):
    """Keep planned future hints; overwrite only exact already-committed8s prefix."""
    if context.ndim != 3 or context.shape[0] != 1 or context.shape[2] != 128:
        raise ValueError('Expected native context shape')
    if prefix.shape != (1, 200, 64) or not np.isfinite(prefix).all() or context.shape[1] <= 200:
        raise ValueError('Expected exactly8s committed latent prefix, never whole previous song')
    result = context.copy()
    mask = np.arange(context.shape[1])[None, :] >= 200
    source = np.zeros((1, context.shape[1], 64), dtype=context.dtype)
    source[:, :200] = prefix
    result[:, :200, :64] = prefix
    result[:, :, 64:] = mask[:, :, None]
    return result, source, mask


class PreparationOnlyDecoder:
    """Dispatch marker, never a model: accidental diffusion must fail closed."""
    def __call__(self, *args, **kwargs):
        raise RuntimeError('Host diffusion disabled in preparation-only service')


def release_preparation_decoder(handler):
    # Official code selects the capture boundary only when mlx_decoder is not None.
    # Require real initialization first; do not fake a successful model conversion.
    if not handler.use_mlx_dit or handler.mlx_decoder is None or handler.model.decoder is not None:
        raise RuntimeError('Release requires verified MLX conversion and disabled Torch decoder')
    handler.mlx_decoder = PreparationOnlyDecoder()


class HostHookAdapter:
    """One serialized host model instance; initialize only on actual cache miss."""
    def __init__(self, assets_root, *, preparation_only=False):
        self.preparation_only = preparation_only
        self.base = Path(assets_root).resolve() / 'experiments/composition_20260916'
        self.handler = self.lm = None
        self.lock = threading.Lock()
        self._fingerprints = None

    def fingerprints(self):
        """Call once before constructing requests; does not load models or generate."""
        if self._fingerprints is None:
            def tree_hash(root):
                paths = sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
                if not paths:
                    raise FileNotFoundError(f'No identity files at {root}')
                state = hashlib.sha256()
                for path in paths:
                    with path.open('rb') as stream:
                        value = hashlib.file_digest(stream, 'sha256').hexdigest()
                    state.update(str(path.relative_to(root)).encode() + b'\0' + value.encode() + b'\n')
                return state.hexdigest()
            model = tree_hash(self.base / 'models/ace/checkpoints')
            official = tree_hash(self.base / 'vendor/ACE-Step-1.5/acestep')
            local = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            preparation = hashlib.sha256((official + local + ('preparation-only-v1' if self.preparation_only else 'full-host-v1')).encode()).hexdigest()
            self._fingerprints = {'model_fingerprint': model, 'preparation_fingerprint': preparation}
        return dict(self._fingerprints)

    def _load(self):
        if self.handler is not None:
            return
        if sys.platform != 'darwin':
            raise RuntimeError('Official host semantic preparation currently requires Mac')
        if not (self.base / 'models/ace/checkpoints').is_dir():
            raise FileNotFoundError('Existing local model assets required; no downloads')
        os.environ.update(HF_HOME=str(self.base / 'cache/hf'), HF_HUB_OFFLINE='1',
                          HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false')
        import acestep
        if Path(acestep.__file__).resolve().parent != (self.base / 'vendor/ACE-Step-1.5/acestep').resolve():
            raise RuntimeError('Imported ACE package differs from fingerprinted preparation source')
        from acestep.handler import AceStepHandler
        from acestep.llm_inference import LLMHandler
        handler, lm = AceStepHandler(), LLMHandler()
        status, ok = lm.initialize(str(self.base / 'models/ace/checkpoints'), 'acestep-5Hz-lm-1.7B', backend='mlx', device='mps')
        if not ok:
            raise RuntimeError(status)
        original_init = handler._init_mlx_dit
        def initialize_without_duplicate(*args, **kwargs):
            ok = original_init(*args, **kwargs)
            if not ok or handler.mlx_decoder is None:
                raise RuntimeError('MLX conversion failed; refusing Torch diffusion fallback')
            import gc
            import torch
            handler.model.decoder = None
            def no_torch_diffusion(*args, **kwargs):
                raise RuntimeError('Torch diffusion disabled after verified MLX conversion')
            handler.model.generate_audio = no_torch_diffusion
            gc.collect()
            torch.mps.empty_cache()
            return ok
        handler._init_mlx_dit = initialize_without_duplicate
        status, ok = handler.initialize_service(str(self.base / 'models/ace'), config_path='acestep-v15-turbo',
            device='mps', use_mlx_dit=True, offload_to_cpu=True, offload_dit_to_cpu=True)
        if not ok or not handler.use_mlx_dit or handler.mlx_decoder is None:
            raise RuntimeError(f'No safe MLX preparation boundary: {status}')
        if self.preparation_only:
            release_preparation_decoder(handler)
            import gc
            import mlx.core as mx
            import torch
            gc.collect()
            mx.clear_cache()
            torch.mps.empty_cache()
        self.handler, self.lm = handler, lm

    def __call__(self, request, sources, output):
        with self.lock:
            identities = self.fingerprints()
            if (request.model_fingerprint != identities['model_fingerprint'] or
                    request.preparation_fingerprint != identities['preparation_fingerprint']):
                raise ValueError('Request fingerprint does not match this host preparation implementation/models')
            self._load()
            import torch
            import mlx.core as mx
            from acestep.inference import GenerationParams, GenerationConfig, generate_music
            random.seed(request.semantic_seed)
            np.random.seed(request.semantic_seed)
            torch.manual_seed(request.semantic_seed)
            mx.random.seed(request.semantic_seed)
            output = Path(output)
            original_diffusion = self.handler._mlx_run_diffusion
            original_plan = self.lm.generate_with_stop_condition
            captured_plan = {}
            completed = threading.Event()

            def plan(*args, **kwargs):
                result = original_plan(*args, **kwargs)
                if not result.get('success') or not result.get('audio_codes'):
                    raise RuntimeError('Planner failed; no generic/static conditioning fallback')
                captured_plan.update(semantic_seed=request.semantic_seed, audio_codes=result['audio_codes'],
                    actual_seeds=kwargs.get('seeds'), caption=kwargs.get('caption'), lyrics=kwargs.get('lyrics'),
                    time_costs=result.get('extra_outputs', {}).get('time_costs'))
                if captured_plan['actual_seeds'] != [request.semantic_seed]:
                    raise ValueError('Host planner ignored requested reproducibility seed')
                return result

            def capture(*unused, **kwargs):
                if not captured_plan:
                    raise ValueError('No actual semantic plan was generated')
                if kwargs.get('repaint_mask') is not None:
                    raise ValueError('Unexpected upstream repaint; refuse ambiguous semantic prefix')
                arrays = {name: kwargs[name].detach().float().cpu().numpy()
                          for name in ('encoder_hidden_states', 'encoder_attention_mask', 'context_latents')}
                if arrays['context_latents'].shape != (1, request.window_seconds * 25, 128):
                    raise ValueError('Unexpected planned duration')
                if request.prefix_seconds:
                    prefix = np.load(sources['committed_prefix'], allow_pickle=False)
                    context, source, mask = continuation_inputs(arrays['context_latents'], prefix)
                    arrays.update(context_latents=context, sampler_clean_src_latents=source, sampler_repaint_mask=mask)
                    (output / 'sampler.json').write_text(json.dumps({
                        'repaint_crossfade_frames': 12, 'repaint_injection_ratio': .5,
                        'semantic_prefix_policy': 'generated plan hints with exact committed8s prefix; candidate unvalidated native'}))
                for name, array in arrays.items():
                    np.save(output / (name + '.npy'), array)
                (output / 'semantic_plan.json').write_text(json.dumps(captured_plan, indent=2))
                (output / 'prepared.json').write_text(json.dumps({
                    'request_key': request.cache_key, 'semantic_seed': request.semantic_seed,
                    'semantic_plan_present': True, 'audio_diffusion_called': False,
                    'host_preparation_only': self.preparation_only,
                    'conditioning_strategy': 'full semantic planning per bounded window; actual hook audio reference; committed latent prefix',
                    'native_validated': False, 'request': request.identity()}, indent=2))
                from hook_planning import validate_prepared
                validate_prepared(request, output, sources)
                completed.set()
                raise Captured()

            self.handler._mlx_run_diffusion = capture
            self.lm.generate_with_stop_condition = plan
            try:
                params = GenerationParams(caption=request.caption, lyrics=request.lyrics,
                    instrumental=True, bpm=request.bpm, keyscale=request.keyscale, timesignature='4',
                    duration=request.window_seconds, inference_steps=8, seed=request.semantic_seed,
                    thinking=True, dcw_enabled=False, use_cot_caption=False, use_cot_metas=False,
                    use_cot_language=False, reference_audio=str(sources['hook_reference']) if sources else None)
                try:
                    result = generate_music(self.handler, self.lm, params,
                        GenerationConfig(batch_size=1, allow_lm_batch=False, use_random_seed=False,
                                         seeds=[request.semantic_seed], audio_format='wav'), save_dir=None)
                except Captured:
                    finish_capture(completed.is_set(), None, request, sources, output)
                    return
                finish_capture(completed.is_set(), result, request, sources, output)
            finally:
                self.handler._mlx_run_diffusion = original_diffusion
                self.lm.generate_with_stop_condition = original_plan
