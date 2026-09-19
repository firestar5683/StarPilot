import json
from pathlib import Path
import tempfile
import unittest
from event_replay_audit import audit


class AuditTests(unittest.TestCase):
    def test_missing_evidence_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(audit(Path(directory))['instrumented_pass'])

    def test_failed_generation_is_not_fresh_music(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'summary.json').write_text(json.dumps({'generation': [
                {'quality_rejected': True, 'quality_attempts': []}]}))
            result = audit(root)
            self.assertFalse(result['checks']['fresh_generation'])
            self.assertEqual(result['accepted_jobs'], 0)

    def test_future_request_and_single_unmuted_block_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'jobs.jsonl').write_text(json.dumps({'cutoff_ns': 10, 'input_times': {'modelV2': 11}})+'\n')
            (root / 'host_audio.jsonl').write_text('{"muted": true}\n{"muted": false}\n')
            result = audit(root)
            self.assertEqual(result['input_time_violations'], 1)
            self.assertFalse(result['checks']['causal_requests'])
            self.assertFalse(result['checks']['muted_blocks'])


if __name__ == '__main__':
    unittest.main()
