import subprocess
import tempfile
import unittest
from pathlib import Path


CHECKER = Path(__file__).resolve().parents[3] / 'scripts/lint/check_shebang_format.sh'


class ShebangFormatTest(unittest.TestCase):
  def check(self, content: bytes) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as directory:
      script = Path(directory) / 'script with spaces'
      script.write_bytes(content)
      return subprocess.run(['bash', str(CHECKER), str(script)], capture_output=True, text=True)

  def test_binary_payload_with_embedded_shebang_is_not_a_script(self):
    result = self.check(b'\x7fELF\x00\n#!/usr/bin/python\n')
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

  def test_text_script_format_is_still_enforced(self):
    for language in ('python3', 'bash'):
      with self.subTest(language=language):
        self.assertEqual(self.check(f'#!/usr/bin/env {language}\n'.encode()).returncode, 0)
        self.assertNotEqual(self.check(f'#!/usr/bin/{language}\n'.encode()).returncode, 0)


if __name__ == '__main__':
  unittest.main()
