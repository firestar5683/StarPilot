"""Compatibility regressions the reserved-event policy must catch in CI."""

import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.ci.schema_policy import read_inputs, validate


class SchemaPolicyTest(unittest.TestCase):
  def setUp(self):
    self.schemas, self.policy, self.sync = read_inputs()

  def test_current_fork_uses_only_reserved_schema_slots(self):
    self.assertEqual(validate(self.schemas, self.policy, self.sync), [])

  def test_adding_a_car_state_field_is_rejected(self):
    name = 'opendbc_repo/opendbc/car/car.capnp'
    self.schemas[name] = self.schemas[name].replace(b'struct CarState {', b'struct CarState {\n  forkValue @62 :Float32;')
    self.assertTrue(any('car.capnp' in error for error in validate(self.schemas, self.policy, self.sync)))

  def test_other_opendbc_schemas_are_pinned(self):
    for name in ('opendbc_repo/opendbc/car/rlog.capnp', 'opendbc_repo/opendbc/car/include/c++.capnp'):
      with self.subTest(name=name):
        schemas = self.schemas.copy()
        schemas[name] += b'\n# unexpected upstream schema edit\n'
        self.assertTrue(any(name in error for error in validate(schemas, self.policy, self.sync)))

  def test_new_schema_under_either_owned_root_requires_policy(self):
    for name in ('openpilot/cereal/new.capnp', 'opendbc_repo/opendbc/car/new.capnp'):
      with self.subTest(name=name):
        schemas = self.schemas.copy()
        schemas[name] = b'@0xdeadbeefdeadbeef;\n'
        self.assertTrue(any(name in error for error in validate(schemas, self.policy, self.sync)))

  def test_input_discovery_includes_new_schema(self):
    with TemporaryDirectory() as directory:
      root = Path(directory)
      for name, data in self.schemas.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
      (root / 'upstream-sync.json').write_text('{"dependencies": []}')
      new_schema = root / 'opendbc_repo/opendbc/car/new.capnp'
      new_schema.write_bytes(b'@0xdeadbeefdeadbeef;\n')
      discovered, _, _ = read_inputs(root)
      self.assertIn('opendbc_repo/opendbc/car/new.capnp', discovered)

  def test_reserved_custom_extension_and_alias_are_allowed(self):
    # This source-policy test permits extension/aliasing; the separate compiled
    # contract protects the existing message's API and field layout.
    original = b'struct AolAxisState @0xfc6241ed8877b611 {'
    self.assertIn(original, self.schemas['openpilot/cereal/custom.capnp'])
    self.assertIn(b'aolAxisState @142 :Custom.AolAxisState;', self.schemas['openpilot/cereal/log.capnp'])
    self.schemas['openpilot/cereal/custom.capnp'] = self.schemas['openpilot/cereal/custom.capnp'].replace(
      original, b'struct FixtureState @0xfc6241ed8877b611 {\n  note @12 :Text = "{fixture}";')
    self.schemas['openpilot/cereal/log.capnp'] = self.schemas['openpilot/cereal/log.capnp'].replace(
      b'aolAxisState @142 :Custom.AolAxisState;', b'fixtureState @142 :Custom.FixtureState;')
    self.assertEqual(validate(self.schemas, self.policy, self.sync), [])

  def test_restored_map_event_cannot_be_retargeted(self):
    self.assertFalse({17, 18, 19}.intersection(self.policy['historical_empty_slots']))
    schemas = self.schemas.copy()
    schemas['openpilot/cereal/log.capnp'] = schemas['openpilot/cereal/log.capnp'].replace(
      b'mapdExtendedOut @143 :Custom.MapdExtendedOut;', b'mapdExtendedOut @143 :Custom.MapdIn;')
    self.assertTrue(any('event @143' in error for error in validate(schemas, self.policy, self.sync)))

  def test_aol_raw_slots_remain_data_with_original_ordinals(self):
    for old, new in ((b'aolSafetyWire @124 :Data;', b'aolSafetyWire @124 :Custom.AolAxisState;'),
                     (b'aolIntentWire @125 :Data;', b'aolIntentWire @126 :Data;')):
      with self.subTest(old=old):
        schemas = self.schemas.copy()
        self.assertIn(old, schemas['openpilot/cereal/log.capnp'])
        schemas['openpilot/cereal/log.capnp'] = schemas['openpilot/cereal/log.capnp'].replace(old, new)
        self.assertTrue(validate(schemas, self.policy, self.sync))

  def test_historical_slot_rename_and_field_are_rejected(self):
    path = 'openpilot/cereal/custom.capnp'
    reserved_by_name = {slot['struct']: slot for slot in self.policy['reserved']}
    for index in self.policy['historical_empty_slots']:
      name = f'CustomReserved{index}'
      type_id = reserved_by_name[name]['type_id']
      original = f'struct {name} @{type_id} {{'.encode()
      self.assertIn(original, self.schemas[path])
      for replacement in (f'struct DifferentEvent @{type_id} {{'.encode(), original + b'\n  newValue @0 :UInt32;'):
        with self.subTest(index=index, replacement=replacement):
          schemas = self.schemas.copy()
          schemas[path] = schemas[path].replace(original, replacement)
          self.assertTrue(any(f'historical slot {index}' in error for error in validate(schemas, self.policy, self.sync)))

  def test_upstream_plan_and_event_enums_cannot_be_extended_or_remapped(self):
    path = 'openpilot/cereal/log.capnp'
    self.assertIn(b'accelBoost @40 :Float32;', self.schemas[path])
    self.assertNotIn(b'forceStopHolding', self.schemas[path])
    self.assertNotIn(b'teslaCCEngaged', self.schemas[path])
    mutations = (
      (b'accelBoost @40 :Float32;', b'accelBoost @41 :Float32;'),
      (b'accelBoost @40 :Float32;', b'accelBoost @40 :Float32;\n  forceStopHolding @41 :Bool;'),
      (b'enum EventName @0x91f1992a1f77fb03 {', b'enum EventName @0x91f1992a1f77fb03 {\n    teslaCCEngaged @105;'),
    )
    for original, replacement in mutations:
      with self.subTest(replacement=replacement):
        schemas = self.schemas.copy()
        self.assertIn(original, schemas[path])
        schemas[path] = schemas[path].replace(original, replacement)
        self.assertTrue(validate(schemas, self.policy, self.sync))
        policy = copy.deepcopy(self.policy)
        policy['reviewed_log_additions'] = [{'scope': 'struct LongitudinalPlan', 'fields': ['forceStopHolding @41 :Bool;']}]
        self.assertTrue(validate(schemas, policy, self.sync))

  def test_historical_slot_comments_do_not_count_as_fields(self):
    path = 'openpilot/cereal/custom.capnp'
    schemas = self.schemas.copy()
    original = b'struct CustomReserved1 @0xaedffd8f31e7b55d {'
    self.assertIn(original, schemas[path])
    schemas[path] = schemas[path].replace(
      original, original + b'\n  # Past wire use is reserved.\n')
    self.assertEqual(validate(schemas, self.policy, self.sync), [])

  def test_restored_lateral_field_keeps_original_wire_meaning(self):
    self.assertNotIn(10, self.policy['historical_empty_slots'])
    path = 'openpilot/cereal/custom.capnp'
    original = b'desiredCurvature @0 :Float32;'
    self.assertIn(original, self.schemas[path])
    for changed in (b'desiredCurvature @0 :UInt32;', b'desiredCurvature @2 :Float32;'):
      with self.subTest(changed=changed):
        schemas = self.schemas.copy()
        schemas[path] = schemas[path].replace(original, changed)
        self.assertTrue(any('historical slot 10' in error for error in validate(schemas, self.policy, self.sync)))

  def test_custom_id_reuse_event_retargeting_and_core_edits_are_rejected(self):
    cases = (
      ('openpilot/cereal/custom.capnp', b'0xa4f1eb3323f5f582', b'0xc86a3d38d13eb3ef'),
      ('openpilot/cereal/log.capnp', b'@145 :Custom.MapdOut', b'@145 :Custom.MapdIn'),
      ('openpilot/cereal/log.capnp', b'@145 :Custom.MapdOut', b'@146 :Custom.MapdOut'),
      ('openpilot/cereal/log.capnp', b'struct Event {', b'struct Event {\n  forkValue @200 :UInt32;'),
    )
    for path, before, after in cases:
      with self.subTest(after=after):
        source = copy.copy(self.schemas)
        self.assertIn(before, source[path])
        source[path] = source[path].replace(before, after)
        self.assertTrue(validate(source, self.policy, self.sync))

  def test_new_upstream_pin_requires_schema_contract_review(self):
    self.sync['upstream']['commit'] = '0' * 40
    self.assertTrue(validate(self.schemas, self.policy, self.sync))

  def test_reviewed_native_enum_is_only_permitted_core_extension(self):
    path = 'opendbc_repo/opendbc/car/car.capnp'
    self.assertEqual(self.policy['reviewed_enum_additions'], {path: {'enum': 'SafetyModel', 'field': 'teslaPreap @39;'}})
    for before, after in ((b'teslaPreap @39;', b'teslaPreap @40;'),
                          (b'teslaPreap @39;', b'teslaPreap @39;\n    extraFork @40;'),
                          (b'teslaPreap @39;', b'teslaPreap @39;\n    extraBool @62 :Bool;')):
      changed = copy.copy(self.schemas)
      self.assertIn(before, changed[path])
      changed[path] = changed[path].replace(before, after)
      self.assertTrue(validate(changed, self.policy, self.sync))

  def test_navigation_keeps_full_historical_control_prefix(self):
    path = 'openpilot/cereal/custom.capnp'
    for before, after in ((b'hudControl @0 :HUDControl;', b'hudControl @0 :Text;'),
                          (b'cooperativeOffsetDeg @4 :Float32;', b'cooperativeOffsetDeg @4 :Bool;'),
                          (b'uwu @22;', b'uwu @23;')):
      changed = copy.copy(self.schemas)
      self.assertIn(before, changed[path])
      changed[path] = changed[path].replace(before, after)
      self.assertTrue(validate(changed, self.policy, self.sync))
