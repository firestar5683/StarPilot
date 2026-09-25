import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import capnp

from opendbc.car import structs as car
from openpilot.common.params import Params
from openpilot.starpilot import schema_cache as cache


class TestSchemaCache(unittest.TestCase):
  def setUp(self):
    self.temporary = tempfile.TemporaryDirectory()
    self.addCleanup(self.temporary.cleanup)
    self.root = Path(self.temporary.name)
    self.params = Params(str(self.root / "params"))
    self.event_parsers = []
    cache.prewarm_cache_contracts()

  def message(self, key):
    contract = cache.CONTRACTS[key]
    message = contract.root.new_message()
    if contract.service:
      message.init(contract.service)
    else:
      message.carFingerprint = "CACHE_TEST_FIXTURE"
    return message

  def encoded(self, key="CarParamsPersistent"):
    cache.put_cache(self.params, key, self.message(key), block=True)
    return self.params.get(key)

  @staticmethod
  def header_and_payload(raw):
    start = len(cache.MAGIC) + 4
    size = struct.unpack_from(">I", raw, len(cache.MAGIC))[0]
    return json.loads(raw[start:start + size]), raw[start + size:]

  @staticmethod
  def repack(header, payload):
    raw = json.dumps(header, separators=(",", ":")).encode()
    return cache.MAGIC + struct.pack(">I", len(raw)) + raw + payload

  def test_all_key_service_contracts_roundtrip_native_params(self):
    for key in cache.CACHE_KEYS:
      with self.subTest(key=key):
        raw = self.encoded(key)
        inspected = cache.inspect_cache(key, raw)
        self.assertEqual(inspected.status, "valid")
        self.assertEqual(cache.get_cache(self.params, key), inspected.payload)
        with cache.CONTRACTS[key].root.from_bytes(inspected.payload) as message:
          if cache.CONTRACTS[key].service:
            self.assertEqual(message.which(), cache.CONTRACTS[key].service)
          else:
            self.assertEqual(message.carFingerprint, "CACHE_TEST_FIXTURE")

  def test_single_queued_write_preserves_block_argument(self):
    params = Mock()
    for block in (False, True):
      params.reset_mock()
      cache.put_cache(params, "CarParamsCache", self.message("CarParamsCache"), block=block)
      self.assertEqual(params.put.call_count, 1)
      self.assertEqual(params.put.call_args.kwargs, {"block": block})
      key, value = params.put.call_args.args
      self.assertEqual(cache.inspect_cache(key, value).status, "valid")

  def test_native_async_write_and_capture_before_builder_mutation(self):
    message = self.message("CarParamsCache")
    cache.put_cache(self.params, "CarParamsCache", message, block=False)
    message.carFingerprint = "CHANGED_AFTER_QUEUE"
    raw = self.params.get("CarParamsCache", block=True)
    result = cache.inspect_cache("CarParamsCache", raw)
    with car.CarParams.from_bytes(result.payload) as restored:
      self.assertEqual(restored.carFingerprint, "CACHE_TEST_FIXTURE")

  def test_already_serialized_builder_and_reader_can_be_used(self):
    message = self.message("CarParamsCache")
    original = message.to_bytes()
    cache.put_cache(self.params, "CarParamsCache", message, block=True)
    cache.put_cache(self.params, "CarParamsPersistent", message, block=True)
    with car.CarParams.from_bytes(original) as reader:
      cache.put_cache(self.params, "CarParamsPrevRoute", reader, block=True)
    self.assertEqual(cache.get_cache(self.params, "CarParamsCache"), original)
    self.assertEqual(cache.get_cache(self.params, "CarParamsPrevRoute"), original)

  def test_raw_bytes_cannot_be_blessed_by_typed_writer(self):
    raw = self.message("CarParamsCache").to_bytes()
    for invalid in (raw, bytearray(raw), memoryview(raw), {}, None):
      with self.subTest(type=type(invalid)), self.assertRaises(TypeError):
        cache.put_cache(self.params, "CarParamsCache", invalid)
    self.assertIsNone(self.params.get("CarParamsCache"))

  def test_wrong_root_and_service_rejected(self):
    with self.assertRaises(ValueError):
      cache.put_cache(self.params, "CalibrationParams", self.message("CarParamsCache"))
    with self.assertRaises(ValueError):
      cache.put_cache(self.params, "CalibrationParams", self.message("LiveDelay"))

  def test_missing_and_unversioned_are_distinct_and_preserved(self):
    self.assertEqual(cache.inspect_cache("CarParamsCache", None).status, "missing")
    for raw in (b"", b"old bytes", self.message("CarParamsCache").to_bytes()):
      self.params.put("CarParamsCache", raw, block=True)
      self.assertEqual(cache.inspect_cache("CarParamsCache", raw).status, "incompatible")
      self.assertIsNone(cache.get_cache(self.params, "CarParamsCache"))
      # Native Params maps an empty value to None; inspect raw storage to prove
      # that a cache miss did not remove or replace even an empty file.
      self.assertEqual((Path(self.params.get_param_path()) / "CarParamsCache").read_bytes(), raw)

  def test_cache_key_cannot_be_relabelled(self):
    raw = self.encoded()
    self.assertEqual(cache.inspect_cache("CarParamsPrevRoute", raw).status, "incompatible")
    with self.assertRaises(ValueError):
      cache.put_cache(self.params, "CarParams", self.message("CarParamsCache"))

  def test_metadata_epoch_schema_and_digest_tampering_rejected(self):
    header, payload = self.header_and_payload(self.encoded())
    for key, value in (("version", 2), ("version", True), ("schema_sha256", "0" * 64),
                       ("root_id", "0x1"), ("producer_contract", "other"), ("payload_bytes", False),
                       ("fingerprint_format", "other"), ("extra", "field")):
      changed = copy.deepcopy(header)
      changed[key] = value
      self.assertEqual(cache.inspect_cache("CarParamsPersistent", self.repack(changed, payload)).status, "incompatible")
    damaged = payload[:-1] + bytes([payload[-1] ^ 1])
    self.assertEqual(cache.inspect_cache("CarParamsPersistent", self.repack(header, damaged)).status, "incompatible")

  def test_duplicate_json_member_rejected(self):
    header, payload = self.header_and_payload(self.encoded())
    text = json.dumps(header)[:-1] + ', "version":1}'
    encoded = text.encode()
    raw = cache.MAGIC + struct.pack(">I", len(encoded)) + encoded + payload
    self.assertEqual(cache.inspect_cache("CarParamsPersistent", raw).status, "incompatible")

  def test_wrong_event_service_rejected_even_with_consistent_digest(self):
    header, _ = self.header_and_payload(self.encoded("CalibrationParams"))
    payload = self.message("LiveDelay").to_bytes()
    header.update(payload_bytes=len(payload), payload_sha256=hashlib.sha256(payload).hexdigest())
    self.assertEqual(cache.inspect_cache("CalibrationParams", self.repack(header, payload)).status, "incompatible")

  def test_malformed_capnp_rejected_even_with_consistent_digest(self):
    header, _ = self.header_and_payload(self.encoded())
    payload = b"not capnp"
    header.update(payload_bytes=len(payload), payload_sha256=hashlib.sha256(payload).hexdigest())
    self.assertEqual(cache.inspect_cache("CarParamsPersistent", self.repack(header, payload)).status, "incompatible")

  def test_total_envelope_limit_includes_metadata(self):
    raw = self.encoded()
    params = Mock()
    with patch.object(cache, "MAX_ENVELOPE_BYTES", len(raw) - 1):
      self.assertEqual(cache.inspect_cache("CarParamsPersistent", raw).status, "incompatible")
      with self.assertRaises(ValueError):
        cache.put_cache(params, "CarParamsPersistent", self.message("CarParamsPersistent"))
    params.put.assert_not_called()
    self.assertLess(cache.MAX_PAYLOAD_BYTES + cache.MAX_HEADER_BYTES + len(cache.MAGIC) + 4, cache.MAX_ENVELOPE_BYTES + 1)

  def test_invalid_or_truncated_header_length_rejected(self):
    for size, body in ((0, b""), (cache.MAX_HEADER_BYTES + 1, b"x"), (200, b"x")):
      raw = cache.MAGIC + struct.pack(">I", size) + body
      self.assertEqual(cache.inspect_cache("CarParamsCache", raw).status, "incompatible")

  def schemas(self, members):
    parsers, modules = [], []
    for index, member in enumerate(members):
      directory = self.root / f"schema-{index}"
      directory.mkdir()
      path = directory / "fixture.capnp"
      path.write_text('@0xabcdefabcdefabcd; struct Root @0xabcdefabcdefabce { child @0 :Choice; ' +
                      'enum Choice @0xabcdefabcdefabcf { ' + member + ' @0; } }')
      parser = capnp.SchemaParser()
      parsers.append(parser)
      modules.append(parser.load(str(path)))
    return parsers, modules

  def test_same_root_id_and_bytes_different_nested_enum_differ(self):
    parsers, modules = self.schemas(("firstMeaning", "otherMeaning"))
    a, b = (module.Root.schema for module in modules)
    self.assertEqual(a.node.id, b.node.id)
    self.assertEqual(a.node.as_builder().to_bytes(), b.node.as_builder().to_bytes())
    self.assertNotEqual(a, b)
    self.assertNotEqual(cache.schema_fingerprint(a), cache.schema_fingerprint(b))
    self.assertEqual(len(parsers), 2)  # keep parser ownership alive through assertions

  def test_fingerprint_stable_across_schema_locations(self):
    parsers, modules = self.schemas(("sameMeaning", "sameMeaning"))
    self.assertEqual(cache.schema_fingerprint(modules[0].Root.schema), cache.schema_fingerprint(modules[1].Root.schema))
    self.assertEqual(len(parsers), 2)

  def test_independent_copy_of_current_schema_is_not_current_producer(self):
    source = Path(__file__).resolve().parents[3] / "opendbc_repo/opendbc/car"
    destination = self.root / "separate-checkout"
    destination.mkdir()
    shutil.copy(source / "car.capnp", destination / "car.capnp")
    shutil.copytree(source / "include", destination / "include")
    parser = capnp.SchemaParser()
    module = parser.load(str(destination / "car.capnp"), imports=[str(destination)])
    self.assertEqual(cache.schema_fingerprint(module.CarParams.schema), cache.schema_fingerprint(car.CarParams.schema))
    self.assertEqual(module.CarParams.schema.node.id, car.CarParams.schema.node.id)
    with self.assertRaises(ValueError):
      cache.put_cache(self.params, "CarParamsCache", module.CarParams.new_message())

  def test_compiled_fingerprints_stable_across_fresh_processes(self):
    code = 'import json; from openpilot.starpilot.schema_cache import prewarm_cache_contracts; print(json.dumps(prewarm_cache_contracts(), sort_keys=True))'
    root = Path(__file__).resolve().parents[3]
    outputs = [subprocess.check_output([sys.executable, "-c", code], cwd=root, text=True) for _ in range(2)]
    self.assertEqual(outputs[0], outputs[1])
    self.assertEqual(json.loads(outputs[0]), cache.prewarm_cache_contracts())

  def test_prewarm_optional_keys_and_no_recomputation(self):
    result = cache.prewarm_cache_contracts(("LiveDelay",))
    self.assertEqual(set(result), {"LiveDelay"})
    with patch.object(cache, "schema_fingerprint", side_effect=AssertionError("unexpected cold computation")):
      self.encoded("LiveDelay")
      self.assertIsNotNone(cache.get_cache(self.params, "LiveDelay"))

  def event_schema(self, *, extra_arm="", extra_field="", unrelated="Text", selected="Float64", enum_name="first",
                   valid_default="true", swap_tags=False):
    directory = Path(tempfile.mkdtemp(dir=self.root))
    path = directory / "event.capnp"
    first, second = (2, 1) if swap_tags else (1, 2)
    path.write_text(f'''@0xabcdefabcdefabd0;
      struct Event @0xabcdefabcdefabd1 {{
        logMonoTime @0 :UInt64;
        union {{ selected @{first} :Payload; unrelated @{second} :{unrelated}; {extra_arm} }}
        valid @3 :Bool = {valid_default}; {extra_field}
      }}
      struct Payload @0xabcdefabcdefabd2 {{ value @0 :{selected}; nested @1 :Nested; }}
      struct Nested @0xabcdefabcdefabd3 {{ values @0 :List(Float64); kind @1 :Kind; }}
      enum Kind @0xabcdefabcdefabd4 {{ {enum_name} @0; }}
    ''')
    parser = capnp.SchemaParser()
    module = parser.load(str(path))
    self.event_parsers.append(parser)
    return module.Event

  def event_contract(self, root):
    return patch.dict(cache.CONTRACTS, CalibrationParams=cache.CacheContract(root, "selected", "calibration-state-v1"))

  def test_service_fingerprint_ignores_unrelated_union_changes(self):
    original = self.event_schema()
    for changed in (self.event_schema(unrelated="Data"), self.event_schema(extra_arm="added @4 :Text;")):
      self.assertNotEqual(cache.schema_fingerprint(original.schema), cache.schema_fingerprint(changed.schema))
      self.assertEqual(cache.event_service_fingerprint(original.schema, "selected"),
                       cache.event_service_fingerprint(changed.schema, "selected"))

  def test_service_fingerprint_rejects_selected_or_wrapper_changes(self):
    original = self.event_schema()
    for options in ({"selected": "Int64"}, {"enum_name": "otherMeaning"}, {"valid_default": "false"},
                    {"swap_tags": True}, {"extra_field": "extra @4 :UInt64;"}):
      with self.subTest(options=options):
        changed = self.event_schema(**options)
        self.assertNotEqual(cache.event_service_fingerprint(original.schema, "selected"),
                            cache.event_service_fingerprint(changed.schema, "selected"))

  def test_unrelated_upgrade_restores_nondefault_typed_event_values(self):
    original, changed = self.event_schema(), self.event_schema(extra_arm="added @4 :Text;")
    message = original.new_message(logMonoTime=12345, valid=False,
                                   selected={"value": 1.25, "nested": {"values": [2.5, -3.0], "kind": "first"}})
    with self.event_contract(original), patch.dict(cache._FINGERPRINTS, clear=True):
      cache.put_cache(self.params, "CalibrationParams", message, block=True)
    raw = self.params.get("CalibrationParams")
    header, _ = self.header_and_payload(raw)
    self.assertEqual((header["version"], header["fingerprint_format"]), (2, cache.EVENT_FINGERPRINT_FORMAT))
    with self.event_contract(changed), patch.dict(cache._FINGERPRINTS, clear=True):
      payload = cache.get_cache(self.params, "CalibrationParams")
      self.assertIsNotNone(payload)
      with changed.from_bytes(payload) as restored:
        self.assertEqual(restored.to_dict(), message.to_dict())
    self.assertEqual(self.params.get("CalibrationParams"), raw)

  def test_legacy_event_requires_full_current_schema_match(self):
    original, changed = self.event_schema(), self.event_schema(extra_arm="added @4 :Text;")
    message = original.new_message(selected={"value": 1.25})
    payload = message.to_bytes()
    with self.event_contract(original), patch.dict(cache._FINGERPRINTS, clear=True):
      header = cache._header(cache.CONTRACTS["CalibrationParams"], "CalibrationParams", payload, version=1)
      raw = self.repack(header, payload)
      self.assertEqual(cache.inspect_cache("CalibrationParams", raw).status, "valid")
    with self.event_contract(changed), patch.dict(cache._FINGERPRINTS, clear=True):
      self.assertEqual(cache.inspect_cache("CalibrationParams", raw).status, "incompatible")

  def test_current_event_legacy_values_remain_readable_without_rewrite(self):
    for key in (key for key, contract in cache.CONTRACTS.items() if contract.service is not None):
      with self.subTest(key=key):
        payload = self.message(key).to_bytes()
        header = cache._header(cache.CONTRACTS[key], key, payload, version=1)
        raw = self.repack(header, payload)
        self.params.put(key, raw, block=True)
        self.assertEqual(cache.get_cache(self.params, key), payload)
        self.assertEqual(self.params.get(key), raw)

  def test_service_cache_version_and_producer_cannot_be_relabelled(self):
    header, payload = self.header_and_payload(self.encoded("LiveDelay"))
    for key, value in (("version", 1), ("version", 3), ("version", True), ("producer_contract", "other"),
                       ("fingerprint_format", cache.FINGERPRINT_FORMAT), ("service", "vehicleParameters")):
      changed = {**header, key: value}
      with self.subTest(key=key, value=value):
        self.assertEqual(cache.inspect_cache("LiveDelay", self.repack(changed, payload)).status, "incompatible")


if __name__ == "__main__":
  unittest.main()
