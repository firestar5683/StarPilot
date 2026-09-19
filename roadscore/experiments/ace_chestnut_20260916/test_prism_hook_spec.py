import unittest
from prism_hook_spec import spec, IDENTITY, HOOK, ROLES


class HookSpecTests(unittest.TestCase):
    def test_identity_and_hook_survive_every_role(self):
        candidate = spec()
        self.assertEqual(set(candidate['role_captions']), set(ROLES))
        for caption in candidate['role_captions'].values():
            self.assertTrue(caption.startswith(IDENTITY + HOOK))
            self.assertIn('128 BPM, D minor', caption)
        self.assertEqual(len(set(candidate['role_captions'].values())), 6)
        self.assertIn('complete established hook', candidate['role_captions']['chorus'])
        self.assertIn('transforming the same hook', candidate['role_captions']['bridge'])
        self.assertIn('resolve', candidate['role_captions']['outro'])

    def test_real_arc_not_repeated_verse(self):
        candidate = spec()
        self.assertTrue(candidate['thinking'])
        self.assertEqual(candidate['lyrics'].count('[Chorus]'), 2)
        self.assertIn('[Bridge]', candidate['lyrics'])
        self.assertIn('[Pre-Chorus]', candidate['lyrics'])
        self.assertIn('no prepared continuation tensors', candidate['continuation_policy'])
        self.assertEqual(sum(x['bars'] for x in candidate['desired_timeline']), 32)
        self.assertEqual(candidate['desired_timeline'][-1]['end_seconds'], 60)
        self.assertIn('not verified', candidate['timeline_status'])

    def test_seed_policy_reproducible_and_not_seed_shopping(self):
        self.assertEqual(spec()['seed'], 33602)
        self.assertEqual(spec(123), spec(123))
        self.assertNotEqual(spec(123)['seed'], spec(124)['seed'])
        self.assertEqual(spec(123)['caption'], spec(124)['caption'])
        for bad in (-1, 2**32, True, 1.5):
            with self.assertRaises(ValueError):
                spec(bad)


if __name__ == '__main__':
    unittest.main()
