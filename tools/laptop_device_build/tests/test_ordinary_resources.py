import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]


def owner(path):
  spec = importlib.util.spec_from_file_location(path.stem, path)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


class TestOrdinaryResources(unittest.TestCase):
  def test_release_revision_pointer_rejected_without_checkout_dependence(self):
    check = owner(ROOT / 'tools/resources/check.py')
    responses = ['100644 blob abc 127\tasset.onnx\n', check.POINTER + b'\noid sha256:bad\n']
    with patch.object(check.subprocess, 'check_output', side_effect=responses), patch.object(sys, 'argv', ['check', '--revision', 'HEAD']):
      with self.assertRaisesRegex(ValueError, 'placeholder pointer'):
        check.main()

  def test_release_ordinary_blob_and_binary_attributes_accepted(self):
    check = owner(ROOT / 'tools/resources/check.py')
    check.validate_blob('asset.wav', 2048)
    check.validate_blob('.gitattributes', 12, b'*.wav -text\n')

  def test_active_filter_and_oversized_blob_rejected(self):
    check = owner(ROOT / 'tools/resources/check.py')
    with self.assertRaisesRegex(ValueError, 'active checkout filter'):
      check.validate_blob('.gitattributes', 22, b'*.wav filter=lfs -text\n')
    check.validate_blob('exact-limit.pkl', 100 * 1024 * 1024)
    with self.assertRaisesRegex(ValueError, 'exceeds 100 MiB'):
      check.validate_blob('too-large.pkl', check.MAX_BLOB_BYTES + 1)

  def test_binary_lint_uses_byte_attributes_but_never_waives_pointer(self):
    lint = owner(ROOT / 'scripts/lint/check_added_large_files.py')
    with tempfile.TemporaryDirectory() as directory:
      file = Path(directory) / 'asset.wav'
      file.write_bytes(b'W' * 2048)
      attr = f'{file}\0text\0unset\0'
      with patch.object(lint.subprocess, 'run') as run:
        run.return_value.stdout = attr
        self.assertEqual(lint.check_added_large_files([str(file)], 1), 0)
        file.write_bytes(b'version https://git-lfs.github.com/spec/v1\noid sha256:bad\n')
        self.assertEqual(lint.check_added_large_files([str(file)], 1), 1)


if __name__ == '__main__':
  unittest.main()
