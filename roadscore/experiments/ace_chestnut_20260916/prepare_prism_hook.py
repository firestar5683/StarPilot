"""Mac-only semantic planning/tensor capture. Stops BEFORE audio diffusion or decoding."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time
import traceback

from prism_hook_spec import spec


class BoundaryCaptured(BaseException):
    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets-root', type=Path, required=True, help='Existing RoadScore assets; read only')
    parser.add_argument('--output-root', type=Path, required=True, help='New private demo artifacts only')
    parser.add_argument('--route-seed', type=int)
    parser.add_argument('--prepare', action='store_true', help='Run one host semantic plan; no audio diffusion')
    args = parser.parse_args()
    recipe = spec(args.route_seed)
    out = args.output_root.resolve() / f'prism_hook_v1_{time.time_ns()}'
    out.mkdir(parents=True, exist_ok=False)
    (out / 'hook_spec.json').write_text(json.dumps(recipe, indent=2))
    state = {'phase': 'spec_only', 'output': str(out), 'spec_sha256': recipe['spec_sha256'],
             'audio_generated': False, 'native_deployed': False, 'continuation_tensors_prepared': False}

    def record():
        (out / 'preparation.json').write_text(json.dumps(state, indent=2))

    record()
    if not args.prepare:
        print(json.dumps(state))
        return
    if sys.platform != 'darwin':
        raise RuntimeError('This host-preparation entry point is Mac-only; no device execution')
    base = args.assets_root.resolve() / 'experiments/composition_20260916'
    if not (base / 'models/ace/checkpoints').is_dir():
        raise FileNotFoundError('Existing local ACE checkpoints missing; no download attempted')
    os.environ.update(HF_HOME=str(base / 'cache/hf'), HF_HUB_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                      TOKENIZERS_PARALLELISM='false', PYTORCH_ENABLE_MPS_FALLBACK='1')
    started = time.monotonic()
    state.update(phase='loading', started_wall=time.time())
    record()
    try:
        import numpy as np
        import torch
        import mlx.core as mx
        from acestep.handler import AceStepHandler
        from acestep.llm_inference import LLMHandler
        from acestep.inference import GenerationParams, GenerationConfig, generate_music
        seed = recipe['seed']
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        mx.random.seed(seed)
        handler, lm = AceStepHandler(), LLMHandler()
        status, ok = handler.initialize_service(str(base / 'models/ace'), config_path='acestep-v15-turbo',
            device='mps', use_mlx_dit=True, offload_to_cpu=True, offload_dit_to_cpu=False)
        if not ok:
            raise RuntimeError(status)
        if not handler.use_mlx_dit or handler.mlx_decoder is None:
            raise RuntimeError('MLX boundary unavailable; refuse fallback audio generation')
        status, ok = lm.initialize(str(base / 'models/ace/checkpoints'), 'acestep-5Hz-lm-1.7B', backend='mlx', device='mps')
        if not ok:
            raise RuntimeError(status)
        original_plan = lm.generate_with_stop_condition

        def record_plan(*values, **kwargs):
            result = original_plan(*values, **kwargs)
            codes = result.get('audio_codes', '')
            if not result.get('success') or not codes:
                raise RuntimeError('Semantic planner did not return audio codes')
            (out / 'semantic_plan.json').write_text(json.dumps({
                'caption': kwargs.get('caption'), 'lyrics': kwargs.get('lyrics'),
                'seeds': kwargs.get('seeds'), 'infer_type': kwargs.get('infer_type'),
                'temperature': kwargs.get('temperature'), 'cfg_scale': kwargs.get('cfg_scale'),
                'audio_codes': codes, 'metadata': result.get('metadata'),
                'time_costs': result.get('extra_outputs', {}).get('time_costs'),
            }, indent=2))
            state['semantic_plan_present'] = True
            return result

        lm.generate_with_stop_condition = record_plan
        state.update(phase='planning', load_seconds=time.monotonic() - started)
        record()

        def capture(*unused, **kwargs):
            required = ('encoder_hidden_states', 'encoder_attention_mask', 'context_latents')
            arrays = {}
            for key in required:
                tensor = kwargs.get(key)
                if not isinstance(tensor, torch.Tensor):
                    raise ValueError(f'Missing prepared boundary tensor: {key}')
                array = tensor.detach().float().cpu().numpy()
                if not np.isfinite(array).all():
                    raise ValueError(f'Non-finite {key}')
                arrays[key] = array
            if arrays['context_latents'].shape != (1, 1500, 128):
                raise ValueError('Preparation did not produce a full60s context')
            if kwargs.get('repaint_mask') is not None:
                raise ValueError('Full planned composition must not silently become repaint')
            if not state.get('semantic_plan_present'):
                raise ValueError('Refuse unplanned conditioning')
            case = dict(recipe, name='prism_hook_v1_60', reference_audio=None,
                        sampler={k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool)) or v is None},
                        tensor_shapes={k: list(v.shape) for k, v in arrays.items()})
            for key, array in arrays.items():
                np.save(out / (key + '.npy'), array)
            (out / 'case.json').write_text(json.dumps(case, indent=2))
            state.update(phase='prepared_boundary', audio_diffusion_called=False,
                         boundary_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                          for p in out.glob('*.npy')},
                         tensor_shapes=case['tensor_shapes'], elapsed_seconds=time.monotonic() - started)
            record()
            raise BoundaryCaptured()

        handler._mlx_run_diffusion = capture
        params = GenerationParams(caption=recipe['caption'], lyrics=recipe['lyrics'], instrumental=True,
            bpm=128, keyscale='D minor', timesignature='4', duration=60, inference_steps=8, seed=seed,
            thinking=True, dcw_enabled=False, use_cot_caption=False, use_cot_metas=False, use_cot_language=False)
        try:
            result = generate_music(handler, lm, params,
                GenerationConfig(batch_size=1, allow_lm_batch=False, use_random_seed=False, seeds=[seed], audio_format='wav'),
                save_dir=str(out / 'unused_audio'))
        except BoundaryCaptured:
            pass
        else:
            raise RuntimeError(f'Expected boundary capture, got success={result.success}: {result.error}')
        if state['phase'] != 'prepared_boundary':
            raise RuntimeError('No native-compatible tensor capture')
        print(json.dumps(state))
    except BaseException as error:
        state.update(phase='failed', error=repr(error), traceback=traceback.format_exc(), elapsed_seconds=time.monotonic() - started)
        record()
        raise


if __name__ == '__main__':
    main()
