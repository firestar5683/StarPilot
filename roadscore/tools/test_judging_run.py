import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import judging_run


class OfficialAttemptPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.freeze = self.root / 'generated/judging_configuration.private.json'
        self.freeze.parent.mkdir()
        self.policy = self.root / 'policy.json'
        self.policy.write_text('{"shared_policy": 1}')
        self.manifest = self.root / 'manifest.json'
        self.manifest.write_text(json.dumps({'configuration': {}, 'submissions': [
            {'label': 'A', 'seed': 123, 'route': 'synthetic/route'}]}))

    def write_freeze(self):
        self.freeze.write_text(json.dumps({
            'policy.json': hashlib.sha256(self.policy.read_bytes()).hexdigest()}))

    def assert_preflight_rejected_without_side_effects(self):
        ledger = self.root / 'results/community_judging/official_A.json'
        previous = ledger.read_bytes() if ledger.exists() else None
        with patch.object(judging_run, 'ROOT', self.root), patch.object(judging_run.subprocess, 'run') as run:
            with patch('sys.argv', ['judging_run', str(self.manifest), '--label', 'A']):
                with self.assertRaises(SystemExit):
                    judging_run.main()
            run.assert_not_called()
        self.assertEqual(ledger.read_bytes() if ledger.exists() else None, previous)
        if previous is None:
            self.assertFalse((self.root / 'results').exists())

    def test_missing_empty_or_malformed_freeze_blocks_before_attempt_creation(self):
        self.assert_preflight_rejected_without_side_effects()
        for content in ('{}', '[]', 'null', '{broken', '{"policy.json": "wrong"}'):
            with self.subTest(content=content):
                self.freeze.write_text(content)
                self.assert_preflight_rejected_without_side_effects()

    def test_matching_freeze_passes_but_changed_or_missing_policy_blocks(self):
        self.write_freeze()
        judging_run.validate_frozen_configuration(self.root)
        self.policy.write_text('changed')
        self.assert_preflight_rejected_without_side_effects()
        self.policy.unlink()
        self.assert_preflight_rejected_without_side_effects()

    def test_freeze_cannot_reference_files_outside_project(self):
        for name in ('../policy.json', '/tmp/policy.json'):
            with self.subTest(name=name):
                self.freeze.write_text(json.dumps({name: '0' * 64}))
                self.assert_preflight_rejected_without_side_effects()

    def test_failed_preflight_preserves_existing_official_attempt(self):
        ledger = self.root / 'results/community_judging/official_A.json'
        ledger.parent.mkdir(parents=True)
        ledger.write_text('{"phase":"finished","attempt":1,"seed":123}')
        self.assert_preflight_rejected_without_side_effects()

    def test_handoff_requires_explicit_authorization_and_complete_preparation(self):
        self.write_freeze()
        manifest = json.loads(self.manifest.read_text())
        manifest['schema'] = 'roadscore-judging-handoff-v1'
        row = manifest['submissions'][0]
        row.update(preparation_ready=True, preparation_blockers=[])
        for authorized in (None, False, 'true', 1):
            with self.subTest(authorized=authorized):
                manifest['generation_authorized'] = authorized
                self.manifest.write_text(json.dumps(manifest))
                self.assert_preflight_rejected_without_side_effects()
        manifest['generation_authorized'] = True
        for ready, blockers in ((False, []), (True, ['missing camera']), (True, None)):
            with self.subTest(ready=ready, blockers=blockers):
                row.update(preparation_ready=ready, preparation_blockers=blockers)
                self.manifest.write_text(json.dumps(manifest))
                self.assert_preflight_rejected_without_side_effects()
        row.update(preparation_ready=True, preparation_blockers=[])
        judging_run.validate_handoff_readiness(manifest, row)


if __name__ == '__main__':
    unittest.main()
