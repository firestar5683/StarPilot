import subprocess

import pytest

from tools.release.build_manifest import capture, verify


@pytest.fixture
def checkout(tmp_path):
  root = tmp_path / 'repo'
  root.mkdir()
  subprocess.run(['git', 'init', '-q', str(root)], check=True)
  for name in ('source.py', 'output.bin', 'undeclared.bin'):
    (root / name).write_text('original\n')
  subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
  subprocess.run(['git', '-C', str(root), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                  'commit', '-qm', 'fixture'], check=True)
  return root, tmp_path / 'manifest.json'


def test_declared_output_rebuilt(checkout):
  root, manifest = checkout
  capture(root, manifest, ['output.bin'], {'arch': 'test'})
  (root / 'output.bin').write_bytes(b'host output')
  capture(root, manifest, ['output.bin'], {'arch': 'test'})
  verify(root, manifest)


@pytest.mark.parametrize('change', ['source', 'undeclared', 'missing', 'empty', 'mode', 'symlink', 'untracked', 'index'])
def test_build_mutations_rejected(checkout, change):
  root, manifest = checkout
  capture(root, manifest, ['output.bin'], {'arch': 'test'})
  target = root / 'output.bin'
  if change in ('source', 'undeclared'):
    (root / ('source.py' if change == 'source' else 'undeclared.bin')).write_text('changed')
  elif change == 'missing':
    target.unlink()
  elif change == 'empty':
    target.write_bytes(b'')
  elif change == 'mode':
    target.chmod(0o755)
  elif change == 'symlink':
    target.unlink()
    target.symlink_to('source.py')
  elif change == 'untracked':
    (root / 'unexpected.py').write_text('created')
  else:
    target.write_text('changed')
    subprocess.run(['git', '-C', str(root), 'add', 'output.bin'], check=True)
  with pytest.raises((ValueError, FileNotFoundError)):
    verify(root, manifest)


def test_dirty_capture_rejected(checkout):
  root, manifest = checkout
  (root / 'source.py').write_text('changed')
  with pytest.raises(ValueError, match='clean'):
    capture(root, manifest, ['output.bin'], {})


def test_stale_config_and_root_rejected(checkout, tmp_path):
  root, manifest = checkout
  capture(root, manifest, ['output.bin'], {'arch': 'one'})
  with pytest.raises(ValueError, match='Stale'):
    capture(root, manifest, ['output.bin'], {'arch': 'two'})
  other = tmp_path / 'other'
  subprocess.run(['git', 'clone', '-q', str(root), str(other)], check=True)
  with pytest.raises(ValueError, match='different checkout'):
    verify(other, manifest)


def test_unsafe_manifest_rejected(checkout):
  root, manifest = checkout
  capture(root, manifest, ['output.bin'], {})
  manifest.chmod(0o644)
  with pytest.raises(ValueError, match='Unsafe'):
    verify(root, manifest)


def test_manifest_inside_checkout_rejected(checkout):
  root, _ = checkout
  with pytest.raises(ValueError, match='outside'):
    capture(root, root / 'manifest.json', ['output.bin'], {})


def test_manifest_parent_symlink_inside_checkout_rejected(checkout, tmp_path):
  root, _ = checkout
  alias = tmp_path / 'alias'
  alias.symlink_to(root, target_is_directory=True)
  with pytest.raises(ValueError, match='outside'):
    capture(root, alias / 'manifest.json', ['output.bin'], {})
