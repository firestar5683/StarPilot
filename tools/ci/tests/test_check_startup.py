import tempfile
import json
import struct
import unittest
from pathlib import Path

from openpilot.common.params import Params
from openpilot.starpilot import schema_cache as cache
from openpilot.starpilot.state_migration import MigrationRequired, prepare_manager_start
from openpilot.cereal import messaging
from tools.check_startup import check_startup


class TestCheckStartup(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)
    self.params = Params(str(self.root / "params"))
    self.storage = self.root / "recovery"
    self.storage.mkdir(mode=0o700)

  def tree(self):
    return {str(path.relative_to(self.root)): path.read_bytes() if path.is_file() else None
            for path in self.root.rglob("*")}

  def test_valid_initialized_cache_accepted_without_writes(self):
    prepare_manager_start(self.params, self.storage)
    cache.put_cache(self.params, "LiveDelay", messaging.new_message("lateralDelay"), block=True)
    before = self.tree()
    check_startup(Path(self.params.get_param_path()), self.storage)
    self.assertEqual(self.tree(), before)

  def test_incompatible_retained_cache_rejected_without_writes(self):
    prepare_manager_start(self.params, self.storage)
    payload = messaging.new_message("lateralDelay").to_bytes()
    header = cache._header(cache.CONTRACTS["LiveDelay"], "LiveDelay", payload, version=1)
    header["schema_sha256"] = "0" * 64
    encoded = json.dumps(header, separators=(",", ":")).encode()
    raw = cache.MAGIC + struct.pack(">I", len(encoded)) + encoded + payload
    self.assertEqual(cache.inspect_cache("LiveDelay", raw).status, "incompatible")
    (Path(self.params.get_param_path()) / "LiveDelay").write_bytes(raw)
    before = self.tree()
    with self.assertRaisesRegex(MigrationRequired, "incompatible retained cache"):
      check_startup(Path(self.params.get_param_path()), self.storage)
    self.assertEqual(self.tree(), before)

  def test_missing_input_rejected_without_creating_namespace(self):
    missing = self.root / "missing"
    with self.assertRaisesRegex(ValueError, "Existing Params namespace required"):
      check_startup(missing, self.storage)
    self.assertFalse(missing.exists())

  def test_root_with_named_link_or_empty_directory_is_rejected(self):
    named = self.root / "named"
    named.mkdir()
    (named / "other").symlink_to(Path(self.params.get_param_path()), target_is_directory=True)
    before = self.tree()
    with self.assertRaisesRegex(ValueError, "named-link roots are ambiguous"):
      check_startup(named, self.storage)
    empty = self.root / "empty"
    empty.mkdir()
    with self.assertRaisesRegex(ValueError, "empty or named-link roots are ambiguous"):
      check_startup(empty, self.storage)
    self.assertEqual({key: value for key, value in self.tree().items() if key != "empty"}, before)
