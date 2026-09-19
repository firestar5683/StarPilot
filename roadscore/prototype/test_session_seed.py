import os
import shlex
import unittest
from unittest.mock import Mock, patch
from generation_seed import configured_seed, sample_seed
from session_seed import seed_argument, select_session, seed_environment, remote_assignments


class SessionSeedTests(unittest.TestCase):
    def test_each_normal_launch_draws_once_and_does_not_inherit_gold(self):
        draw = Mock(side_effect=[18007211, 28899402, 79121330])
        with patch.dict(os.environ, {'ROADSCORE_GENERATION_SEED': '33602'}):
            sessions = [select_session(random_bits=draw) for _ in range(3)]
        self.assertEqual(draw.call_count, 3)
        self.assertEqual(len({s['generation_seed'] for s in sessions}), 3)
        self.assertTrue(all(s['seed_origin'] == 'fresh-session' for s in sessions))
        streams = [tuple(sample_seed(s['generation_seed'], 'prepare', i) for i in range(4)) for s in sessions]
        self.assertEqual(len(set(streams)), 3)

    def test_explicit_session_repeats_initial_and_continuation_streams(self):
        forbidden = Mock(side_effect=AssertionError('Explicit seed must not draw randomness'))
        a = select_session(73921, random_bits=forbidden)
        b = select_session('73921', random_bits=forbidden)
        self.assertEqual(a, b)
        for phase in ('prepare', 'continuation'):
            self.assertEqual([sample_seed(a['generation_seed'], phase, i) for i in range(8)],
                             [sample_seed(b['generation_seed'], phase, i) for i in range(8)])
        self.assertEqual(a['reproduce_cli'], ['--roadscore-seed', '73921'])

    def test_official_seed_is_preserved_and_conflict_refused(self):
        s = select_session(114992, judging_seed='114992')
        self.assertEqual(s['seed_origin'], 'judging-route')
        self.assertEqual(s['generation_seed'], 114992)
        for explicit in (None, 114993):
            with self.assertRaises(ValueError):
                select_session(explicit, judging_seed=114992)

    def test_native_and_remote_receive_identical_seed_environment(self):
        for source in (select_session(0), select_session(2**32-1, judging_seed=2**32-1)):
            native = seed_environment(source)
            remote = dict(part.split('=', 1) for part in shlex.split(remote_assignments(source)))
            self.assertEqual(remote, native)
            with patch.dict(os.environ, remote, clear=True):
                self.assertEqual(configured_seed(required=True), source['generation_seed'])

    def test_worker_cannot_fall_back_to_diagnostic_seed(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(configured_seed())  # read-only legacy callers remain compatible
            with self.assertRaisesRegex(ValueError, 'session seed'):
                configured_seed(required=True)

    def test_reject_invalid_seed_without_random_or_shell_input(self):
        for bad in (-1, 2**32, '1.5', 'nan', '$(anything)', True):
            with self.assertRaises(ValueError):
                seed_argument(bad)


if __name__ == '__main__':
    unittest.main()
