import tempfile
import json
import struct
import unittest
from pathlib import Path

from opendbc.car import structs
from openpilot.common.params import Params
from openpilot.starpilot import schema_cache as cache
from openpilot.starpilot.state_migration import MigrationRequired, load_snapshot, prepare_manager_start
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

  def stale_cache(self, key):
    contract = cache.CONTRACTS[key]
    message = contract.root.new_message() if contract.service is None else messaging.new_message(contract.service)
    payload = message.to_bytes()
    header = cache._header(contract, key, payload)
    header.update(producer_contract="prior-runtime-contract", schema_sha256="0" * 64)
    encoded = json.dumps(header, separators=(",", ":")).encode()
    raw = cache.MAGIC + struct.pack(">I", len(encoded)) + encoded + payload
    self.assertEqual(cache.inspect_cache(key, raw).status, "incompatible")
    self.params.put(key, raw, block=True)
    return raw

  def test_initialized_actual_registry_archives_all_vehicle_contracts_only(self):
    prepare_manager_start(self.params, self.storage, auto_migrate=True)
    vehicle_keys = {key for key, contract in cache.CONTRACTS.items() if contract.root is structs.CarParams}
    self.assertTrue(vehicle_keys)
    stale = {key: self.stale_cache(key) for key in vehicle_keys}
    cache.put_cache(self.params, "CalibrationParams", messaging.new_message("extrinsicsCalibration"), block=True)
    cache.put_cache(self.params, "LiveDelay", messaging.new_message("lateralDelay"), block=True)
    self.params.put_bool("IsMetric", True, block=True)
    self.params.put_bool("AlwaysOnLateral", True, block=True)
    self.params.put("DongleId", "preserved-operational-identity", block=True)
    namespace = Path(self.params.get_param_path())
    original = {path.name: path.read_bytes() for path in namespace.iterdir()}
    before = self.tree()
    with self.assertRaisesRegex(MigrationRequired, "incompatible retained cache"):
      check_startup(namespace, self.storage)
    self.assertEqual(self.tree(), before)
    prepare_manager_start(self.params, self.storage, auto_migrate=True)
    expected = {key: raw for key, raw in original.items() if key not in vehicle_keys}
    self.assertEqual({path.name: path.read_bytes() for path in namespace.iterdir()}, expected)
    snapshot, = (self.storage / "snapshots").iterdir()
    self.assertEqual(load_snapshot(snapshot), original)
    receipt = json.loads((snapshot / "migration.json").read_bytes())
    self.assertEqual(set(receipt["actions"]), set(stale))
    self.assertEqual(receipt["status"], "migrated")
    after = self.tree()
    prepare_manager_start(self.params, self.storage, auto_migrate=True)
    check_startup(namespace, self.storage)
    self.assertEqual(self.tree(), after)

  def test_initialized_vehicle_upgrade_does_not_admit_invalid_other_cache(self):
    prepare_manager_start(self.params, self.storage, auto_migrate=True)
    vehicle_keys = {key for key, contract in cache.CONTRACTS.items() if contract.root is structs.CarParams}
    for key in vehicle_keys:
      self.stale_cache(key)
    self.stale_cache("LiveDelay")
    namespace = Path(self.params.get_param_path())
    original = {path.name: path.read_bytes() for path in namespace.iterdir()}
    with self.assertRaises(MigrationRequired):
      prepare_manager_start(self.params, self.storage, auto_migrate=True)
    self.assertEqual({path.name: path.read_bytes() for path in namespace.iterdir()}, original)
    snapshot, = (self.storage / "snapshots").iterdir()
    self.assertEqual(load_snapshot(snapshot), original)

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
