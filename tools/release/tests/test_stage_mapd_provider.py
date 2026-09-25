import hashlib
import json
from pathlib import Path
import stat
import shutil
import struct
import subprocess
import tempfile
import unittest

from openpilot.starpilot.maps.artifact import source_digest
from tools.release.release_files import release_files
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

  def test_stripped_selection_preserves_complete_mapd_source_digest(self):
    inputs = {
      'mapd_repo/.github/workflows/build.yml': 'name: build\n',
      'mapd_repo/.github/workflows/release.yml': 'name: release\n',
      'mapd_repo/go.mod': 'module fixture\nreplace example/module => ./third_party/module\n',
      'mapd_repo/third_party/module/go.mod': 'module example/module\n',
      'mapd_repo/third_party/module/header.go': 'package module\nconst Readers = 64\n',
      'mapd_repo/third_party/module/LICENSE': 'fixture license\n',
      '.github/workflows/tests.yaml': 'name: root CI\n',
    }
    for name, content in inputs.items():
      path = self.source / name
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text(content)
    self.git('add', *inputs)
    self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
             'commit', '--quiet', '-m', 'dependency fixture')
    self.revision = self.git('rev-parse', 'HEAD').strip()
    manifest = self.make_package()
    selected = release_files(str(self.source))
    self.assertNotIn(b'.github/workflows/tests.yaml', selected)
    for name in inputs:
      if name.startswith('mapd_repo/'):
        self.assertIn(name.encode(), selected)
    for raw in selected:
      name = raw.decode()
      target = self.destination / name
      target.parent.mkdir(parents=True, exist_ok=True)
      shutil.copy2(self.source / name, target)
    self.assertEqual(source_digest(self.destination / 'mapd_repo'), manifest['sourceDigest'])
    self.assertEqual(stage_provider(self.source, self.destination), manifest)
    (self.destination / 'mapd_repo/third_party/module/header.go').write_text('package changed\n')
    with self.assertRaisesRegex(ValueError, 'release Mapd source differs'):
      stage_provider(self.source, self.destination)

  def test_tracked_archive_and_release_copy_include_valid_provider(self):
    lifecycle = self.source / 'openpilot/starpilot/maps/shadow_lifecycle.py'
    lifecycle.write_text('# fixture lifecycle\n')
    self.git('add', 'openpilot/starpilot/maps')
    self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
             'commit', '--quiet', '-m', 'tracked provider')
    archive = self.base / 'source.tar'
    self.git('archive', '--format=tar', '--output', str(archive), 'HEAD')
    extracted = self.base / 'archive'
    extracted.mkdir()
    shutil.unpack_archive(archive, extracted)
    self.assertEqual(validate_provider(extracted), validate_provider(self.source))
    for raw in release_files(str(self.source)):
      target = self.destination / raw.decode()
      target.parent.mkdir(parents=True, exist_ok=True)
      shutil.copy2(self.source / raw.decode(), target)
    binary = self.destination / PROVIDER / 'mapd'
    before = binary.stat()
    self.assertEqual(stage_provider(self.source, self.destination), validate_provider(self.source))
    self.assertEqual(binary.stat().st_ino, before.st_ino)
    self.assertEqual(binary.stat().st_mode, before.st_mode)

  def test_ignored_local_provider_cannot_mask_missing_git_package(self):
    self.assertIsInstance(validate_provider(self.source), dict)
    with self.assertRaisesRegex(ValueError, 'Mapd Git package missing'):
      release_files(str(self.source), require_provider=True)

  def test_existing_partial_tampered_or_symlink_package_denied(self):
    stage_provider(self.source, self.destination)
    binary = self.destination / PROVIDER / 'mapd'
    binary.write_bytes(binary.read_bytes() + b'tampered')
    with self.assertRaisesRegex(ValueError, 'hash or embedded'):
      stage_provider(self.source, self.destination)
    binary.unlink()
    with self.assertRaises(OSError):
      stage_provider(self.source, self.destination)
    binary.symlink_to(self.source / PROVIDER / 'mapd')
    with self.assertRaises(ValueError):
      stage_provider(self.source, self.destination)

  def test_finder_metadata_does_not_change_source_attestation(self):
    manifest = self.make_package()
    metadata = self.source / 'mapd_repo/.DS_Store'
    metadata.write_bytes(b'finder metadata')
    self.assertEqual(source_digest(self.source / 'mapd_repo'), manifest['sourceDigest'])
    metadata.write_bytes(b'updated finder metadata')
    self.assertEqual(validate_provider(self.source), manifest)
    (self.source / 'mapd_repo/main.go').write_text('package changed\n')
    with self.assertRaisesRegex(ValueError, 'source'):
      validate_provider(self.source)

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
