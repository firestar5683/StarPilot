import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch
from characterize_routes import characterize


class CharacterizationTests(unittest.TestCase):
    def test_parser_warning_prevents_clean_log_claim(self):
        def warned_reader(_):
            warnings.warn('Corrupted events detected', RuntimeWarning)
            return iter(())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            segment = root / 'fixture--0'
            segment.mkdir()
            (segment / 'rlog').touch()
            with patch('characterize_routes.LogReader', side_effect=warned_reader):
                result = characterize(root)
            self.assertFalse(result['all_available_logs_readable'])
            self.assertEqual(result['segments'][0]['warnings'], ['Corrupted events detected'])


if __name__ == '__main__':
    unittest.main()
