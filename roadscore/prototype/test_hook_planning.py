import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace

import numpy as np
from hook_planning import PlanCache, digest, next_section, request_plan, validate_prepared


def request(seed=101, **extra):
    values = dict(session_seed=seed, plan_index=0, profile='prism', section='initial', window_seconds=30,
                  model_fingerprint='a' * 64, preparation_fingerprint='b' * 64)
    values.update(extra)
    return request_plan(**values)


def fake_prepare(req, sources, out):
    np.save(out / 'encoder_hidden_states.npy', np.zeros((1, 4, 2048), np.float32))
    np.save(out / 'encoder_attention_mask.npy', np.ones((1, 4), bool))
    np.save(out / 'context_latents.npy', np.zeros((1, req.window_seconds * 25, 128), np.float32))
    (out / 'semantic_plan.json').write_text(json.dumps({'audio_codes': 'test-only-code', 'semantic_seed': req.semantic_seed}))
    (out / 'prepared.json').write_text(json.dumps({'request_key': req.cache_key,
        'semantic_seed': req.semantic_seed, 'semantic_plan_present': True, 'audio_diffusion_called': False}))


class PlanningTests(unittest.TestCase):
    def test_gold_groove_reaches_every_prepared_role_and_invalidates_old_plans(self):
        initial = request()
        gold = ('Instrumental polished K-pop and modern electronic game score. No vocals, no singing, no speech. '
                'Continuous tight drum groove, punchy bass, memorable recurring hook, polished dynamic arrangement. '
                '128 BPM, D minor. Crystal pluck arpeggios and a playful four-note rising synth motif; '
                'crisp electronic snare, rubbery syncopated bass and bright glass leads.')
        self.assertTrue(initial.caption.startswith(gold))
        self.assertIn('Enter immediately', initial.caption)
        self.assertEqual(initial.lyrics, '[Instrumental]\n[Verse]')
        self.assertNotEqual(initial.cache_key, replace(initial, version='roadscore-hook-plan-v2').cache_key)
        for role in ('verse', 'prechorus', 'chorus', 'bridge', 'outro'):
            current = request(plan_index=1, section=role, window_seconds=45,
                              hook_reference_sha256='c'*64, committed_prefix_sha256='d'*64,
                              previous_plan_sha256='e'*64)
            self.assertTrue(current.caption.startswith(gold))
            self.assertNotIn('breathing space', current.caption)
            self.assertNotIn('lighter', current.caption)
            self.assertEqual(current.prefix_seconds, 8)
            self.assertEqual(current.window_seconds, 45)
        self.assertEqual(initial.window_seconds, 30)

    def test_fresh_composition_not_same_plan(self):
        first, second = request(101), request(102)
        self.assertEqual(first, request(101))
        self.assertNotEqual(first.semantic_seed, second.semantic_seed)
        self.assertNotEqual(first.cache_key, second.cache_key)
        self.assertEqual(first.caption, second.caption)
        self.assertNotEqual(first.semantic_seed, first.session_seed)

    def test_no_fixedseed_or_lost_context_fallback(self):
        for seed in (None, -1, 2**32, True):
            with self.assertRaises(ValueError):
                request(seed)
        with self.assertRaises(ValueError):
            request(plan_index=1, section='verse')
        with self.assertRaises(ValueError):
            request(section='verse')
        with self.assertRaises(ValueError):
            request(window_seconds=120)

    def test_sections_develop_and_fresh_inputs_invalidate_cache(self):
        roles = [next_section(i) for i in range(6)]
        self.assertEqual(roles, ['verse', 'prechorus', 'chorus', 'verse', 'bridge', 'chorus'])
        self.assertEqual(next_section(999, arrival_intent=True), 'outro')
        req = request(plan_index=1, section='verse', hook_reference_sha256='c' * 64,
                      committed_prefix_sha256='d' * 64, previous_plan_sha256='e' * 64)
        for change in ({'section': 'chorus'}, {'window_seconds': 45}, {'committed_prefix_sha256': 'f' * 64},
                       {'model_fingerprint': 'f' * 64}, {'previous_plan_sha256': 'f' * 64}):
            self.assertNotEqual(req.cache_key, replace(req, **change).cache_key)

    def test_automatic_exactcache_and_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = PlanCache(directory)
            calls = []
            def prepare(*args):
                calls.append(args[0].semantic_seed)
                fake_prepare(*args)
            path, hit = cache.resolve(request(), prepare)
            self.assertFalse(hit)
            self.assertEqual(cache.resolve(request(), prepare), (path, True))
            self.assertEqual(len(calls), 1)
            cache.resolve(request(102), prepare)
            self.assertEqual(len(calls), 2)
            with (path / 'context_latents.npy').open('ab') as stream:
                stream.write(b'changed')
            with self.assertRaises(ValueError):
                cache.resolve(request(), prepare)

    def test_strings_only_and_pcmcache_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = PlanCache(directory)
            def bad(req, sources, out):
                fake_prepare(req, sources, out)
                (out / 'score.wav').write_bytes(b'cached old song')
            with self.assertRaises(ValueError):
                cache.resolve(request(), bad)
            def no_codes(req, sources, out):
                fake_prepare(req, sources, out)
                (out / 'semantic_plan.json').write_text(json.dumps({'caption': req.caption}))
            with self.assertRaises(ValueError):
                cache.resolve(request(), no_codes)

    def test_wrong_source_stops_before_prepare(self):
        with tempfile.TemporaryDirectory() as directory:
            hook = Path(directory) / 'hook.wav'
            prefix = Path(directory) / 'prefix.npy'
            hook.write_bytes(b'current-hook')
            np.save(prefix, np.zeros((1, 200, 64), np.float16))
            req = request(plan_index=1, section='verse', hook_reference_sha256=digest(hook),
                          committed_prefix_sha256=digest(prefix), previous_plan_sha256='e' * 64)
            hook.write_bytes(b'other-session-hook')
            with self.assertRaises(ValueError):
                PlanCache(Path(directory) / 'cache').resolve(req, lambda *_: self.fail('must not prepare'),
                    sources={'hook_reference': hook, 'committed_prefix': prefix})

    def test_continuation_cache_checks_actual_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hook, prefix = root / 'hook.wav', root / 'prefix.npy'
            hook.write_bytes(b'accepted hook')
            actual = np.ones((1, 200, 64), np.float16) * 3
            np.save(prefix, actual)
            req = request(plan_index=1, section='chorus', hook_reference_sha256=digest(hook),
                          committed_prefix_sha256=digest(prefix), previous_plan_sha256='e' * 64)
            def prepare(req, sources, out):
                fake_prepare(req, sources, out)
                n = req.window_seconds * 25
                context = np.zeros((1, n, 128), np.float32)
                context[:, :200, :64] = actual
                source = np.zeros((1, n, 64), np.float32)
                source[:, :200] = actual
                np.save(out / 'context_latents.npy', context)
                np.save(out / 'sampler_clean_src_latents.npy', source)
                np.save(out / 'sampler_repaint_mask.npy', np.arange(n)[None, :] >= 200)
                (out / 'sampler.json').write_text(json.dumps({'repaint_crossfade_frames': 12, 'repaint_injection_ratio': .5}))
            sources = {'hook_reference': hook, 'committed_prefix': prefix}
            path, hit = PlanCache(root / 'cache').resolve(req, prepare, sources=sources)
            self.assertFalse(hit)
            validate_prepared(req, path, sources)
            np.save(path / 'sampler_clean_src_latents.npy', np.zeros((1, 750, 64), np.float32))
            with self.assertRaises(ValueError):
                validate_prepared(req, path, sources)


if __name__ == '__main__':
    unittest.main()
