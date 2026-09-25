import hashlib
import json
from pathlib import Path
import stat
import struct
import subprocess
import tempfile
import unittest

from openpilot.starpilot.maps.artifact import source_digest
from tools.release.stage_mapd_provider import PROVIDER, stage_provider, validate_provider


class TestStageMapdProvider(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.base = Path(temporary.name)
    self.source = self.base / 'source'
    self.source.mkdir()
    self.destination = self.base / 'release'
    self.destination.mkdir()
    self.git('init', '--quiet')
    (self.source / 'mapd_repo').mkdir()
    (self.source / 'mapd_repo/main.go').write_text('package main\n')
    (self.source / 'upstream-sync.json').write_text(json.dumps({'dependencies': [
      {'path': 'mapd_repo', 'commit': 'a' * 40},
    ]}))
    self.git('add', 'mapd_repo/main.go', 'upstream-sync.json')
    self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
             'commit', '--quiet', '-m', 'fixture')
    self.revision = self.git('rev-parse', 'HEAD').strip()
    (self.source / PROVIDER).mkdir(parents=True)
    (self.destination / 'openpilot/starpilot/maps').mkdir(parents=True)
    (self.destination / 'mapd_repo').mkdir()
    (self.destination / 'mapd_repo/main.go').write_text('package main\n')
    (self.destination / 'upstream-sync.json').write_bytes((self.source / 'upstream-sync.json').read_bytes())
    self.make_package()

  def git(self, *args):
    return subprocess.check_output(['git', '-C', str(self.source), *args], text=True)

  def make_package(self):
    digest = source_digest(self.source / 'mapd_repo')
    header = bytearray(64)
    header[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<H', header, 18, 183)
    struct.pack_into('<Q', header, 32, 64)
    struct.pack_into('<H', header, 54, 56)
    struct.pack_into('<H', header, 56, 1)
    program = bytearray(56)
    struct.pack_into('<I', program, 0, 1)
    binary = bytes(header + program) + self.revision.encode() + b'\n' + b'a' * 40 + b'\n' + digest.encode()
    path = self.source / PROVIDER / 'mapd'
    path.write_bytes(binary)
    path.chmod(0o755)
    manifest = {'schemaVersion': 1, 'goVersion': 'go1.25.1', 'target': 'linux-arm64-static',
                'sourceRevision': self.revision, 'upstreamRevision': 'a' * 40,
                'sourceDigest': digest, 'binarySha256': hashlib.sha256(binary).hexdigest()}
    (self.source / PROVIDER / 'manifest.json').write_text(json.dumps(manifest))
    return manifest

  def test_validated_package_stages_both_files(self):
    manifest = self.make_package()
    (self.source / 'README.md').write_text('unrelated release note\n')
    self.git('add', 'README.md')
    self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
             'commit', '--quiet', '-m', 'unrelated change')
    self.assertNotEqual(self.git('rev-parse', 'HEAD').strip(), manifest['sourceRevision'])
    self.assertEqual(validate_provider(self.source), manifest)
    self.assertEqual(stage_provider(self.source, self.destination), manifest)
    self.assertEqual((self.destination / PROVIDER / 'mapd').read_bytes(), (self.source / PROVIDER / 'mapd').read_bytes())
    self.assertEqual(json.loads((self.destination / PROVIDER / 'manifest.json').read_text()), manifest)
    self.assertTrue((self.destination / PROVIDER / 'mapd').stat().st_mode & stat.S_IXUSR)

  def test_missing_stale_or_tampered_package_cannot_stage(self):
    binary = self.source / PROVIDER / 'mapd'
    manifest = self.source / PROVIDER / 'manifest.json'
    binary.unlink()
    with self.assertRaises(OSError):
      stage_provider(self.source, self.destination)
    self.assertFalse((self.destination / PROVIDER / 'mapd').exists())
    self.make_package()
    (self.source / 'mapd_repo/main.go').write_text('package changed\n')
    with self.assertRaisesRegex(ValueError, 'source changed'):
      stage_provider(self.source, self.destination)
    (self.source / 'mapd_repo/main.go').write_text('package main\n')
    binary.write_bytes(binary.read_bytes() + b'tampered')
    with self.assertRaisesRegex(ValueError, 'hash or embedded'):
      stage_provider(self.source, self.destination)
    self.make_package()
    manifest.unlink()
    manifest.symlink_to(self.source / 'upstream-sync.json')
    with self.assertRaises(ValueError):
      stage_provider(self.source, self.destination)
    self.assertFalse((self.destination / PROVIDER / 'mapd').exists())

  def test_release_source_mismatch_rejected_before_copy(self):
    (self.destination / 'mapd_repo/main.go').write_text('package different\n')
    with self.assertRaisesRegex(ValueError, 'release Mapd source differs'):
      stage_provider(self.source, self.destination)
    self.assertFalse((self.destination / PROVIDER / 'mapd').exists())


if __name__ == '__main__':
  unittest.main()
