import ast
import os
from pathlib import Path
import re
import stat
import tempfile
import unittest


SCONSTRUCT = Path(__file__).resolve().parents[1] / 'SConstruct'


class CacheOS:
  path = os.path

  def __init__(self, *, vanish_on_walk=None, vanish_on_unlink=None, fail_stat=None, fail_unlink=None):
    self.vanish_on_walk = vanish_on_walk
    self.vanish_on_unlink = vanish_on_unlink
    self.fail_stat = fail_stat
    self.fail_unlink = fail_unlink

  def walk(self, root):
    for entry in os.walk(root):
      if self.vanish_on_walk is not None and self.vanish_on_walk.parent == Path(entry[0]):
        self.vanish_on_walk.unlink(missing_ok=True)
      yield entry

  def stat(self, path, *, follow_symlinks=True):
    if self.fail_stat == Path(path):
      raise PermissionError(path)
    return os.stat(path, follow_symlinks=follow_symlinks)

  def unlink(self, path):
    if self.fail_unlink == Path(path):
      raise PermissionError(path)
    if self.vanish_on_unlink == Path(path):
      os.unlink(path)
      raise FileNotFoundError(path)
    os.unlink(path)


def prune(root, limit, os_impl=os):
  tree = ast.parse(SCONSTRUCT.read_text())
  function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'prune_cache_dir')
  scope = {'os': os_impl, 're': re, 'stat': stat, 'cache_dir': str(root), 'cache_size_limit': limit}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), str(SCONSTRUCT), 'exec'), scope)
  scope['prune_cache_dir']()


class TestSconsCachePrune(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)
    self.shard = self.root / '8B'
    self.shard.mkdir()

  def artifact(self, suffix='a', length=32):
    path = self.shard / ('8b' + suffix * (length - 2))
    path.write_bytes(b'finalized-artifact')
    return path

  def test_only_finalized_artifacts_are_pruned(self):
    final32 = self.artifact('a')
    final64 = self.artifact('b', 64)
    temp = self.shard / (final32.name + '.tmpwriter')
    temp.write_bytes(b'active-writer')
    metadata = self.root / 'config'
    metadata.write_bytes(b'cache-metadata')
    tag = self.root / 'CACHEDIR.TAG'
    tag.write_bytes(b'tag')
    outside = self.root / 'outside'
    outside.write_bytes(b'outside')
    link = self.shard / ('8b' + 'c' * 30)
    link.symlink_to(outside)
    prune(str(self.root) + '/', 1)
    self.assertFalse(final32.exists())
    self.assertFalse(final64.exists())
    self.assertTrue(temp.exists())
    self.assertTrue(metadata.exists())
    self.assertTrue(tag.exists())
    self.assertTrue(link.is_symlink())
    self.assertEqual(outside.read_bytes(), b'outside')

  def test_disappearing_temp_and_finalized_stat_are_harmless(self):
    final = self.artifact()
    temp = self.shard / (final.name + '.tmpwriter')
    temp.write_bytes(b'active-writer')
    prune(self.root, 1, CacheOS(vanish_on_walk=temp))
    self.assertFalse(final.exists())
    final = self.artifact()
    prune(self.root, 1, CacheOS(vanish_on_walk=final))
    self.assertFalse(final.exists())

  def test_disappearing_unlink_is_harmless(self):
    final = self.artifact()
    prune(self.root, 1, CacheOS(vanish_on_unlink=final))
    self.assertFalse(final.exists())

  def test_other_io_errors_remain_visible(self):
    final = self.artifact()
    with self.assertRaises(PermissionError):
      prune(self.root, 1, CacheOS(fail_stat=final))
    self.assertTrue(final.exists())
    with self.assertRaises(PermissionError):
      prune(self.root, 1, CacheOS(fail_unlink=final))
    self.assertTrue(final.exists())


if __name__ == '__main__':
  unittest.main()
