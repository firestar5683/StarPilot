"""Frozen StarPilot radar wire remains readable in both directions."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from openpilot.cereal import custom
from tools.ci.custom_schema_contract import CONTRACT, describe, validate
from tools.ci.schema_policy import read_inputs, validate as validate_source


# Serialized by frozen 678af783 StarPilotRadarState with populated original
# leadLeft, leadRight and adjacentStopped. No Domathon extension is present.
FROZEN_BYTES = bytes.fromhex(
  '000000001400000000000000000003000800000007000000200000000700000038000000020000000000c841000040400000000000000000000040410000000000000000000000000000000000000000020000000000000000000000eeffffff0000e041000040c00000000000000000000030410000000000000000000000000000000000000000020000000000000000000000edffffff010000000000f04100002040ecffffff'
)
FROZEN_SCHEMA = Path(__file__).with_name('testdata') / 'frozen_starpilot_radar.capnp'


def _frozen_read(raw: bytes) -> dict:
  # Pycapnp will abort on duplicate schema IDs if old and current modules are
  # loaded in the same interpreter. A separate reader is the real old-client
  # compatibility check, not a schema-text equality assertion.
  program = """
import capnp, json, sys
module = capnp.load(sys.argv[1])
with module.StarPilotRadarState.from_bytes(bytes.fromhex(sys.argv[2])) as wire:
  print(json.dumps({'left': [wire.leadLeft.status, wire.leadLeft.dRel, wire.leadLeft.yRel, wire.leadLeft.radarTrackId],
                    'right': [wire.leadRight.status, wire.leadRight.dRel, wire.leadRight.yRel, wire.leadRight.radarTrackId],
                    'stopped': [wire.adjacentStopped.status, wire.adjacentStopped.dRel, wire.adjacentStopped.yRel,
                                wire.adjacentStopped.radarTrackId]}))
"""
  result = subprocess.run([sys.executable, '-c', program, str(FROZEN_SCHEMA), raw.hex()], capture_output=True, text=True, check=True, timeout=10)
  return json.loads(result.stdout)


class AdjacentRadarSchemaTest(unittest.TestCase):
  def test_current_reader_accepts_original_frozen_wire(self):
    with custom.StarPilotRadarState.from_bytes(FROZEN_BYTES) as wire:
      self.assertEqual((wire.leadLeft.status, wire.leadLeft.dRel, wire.leadLeft.yRel, wire.leadLeft.radarTrackId), (True, 25.0, 3.0, 17))
      self.assertEqual((wire.leadRight.status, wire.leadRight.dRel, wire.leadRight.yRel, wire.leadRight.radarTrackId), (True, 28.0, -3.0, 18))
      self.assertEqual(
        (wire.adjacentStopped.status, wire.adjacentStopped.dRel, wire.adjacentStopped.yRel, wire.adjacentStopped.radarTrackId), (True, 30.0, 2.5, 19)
      )
      self.assertEqual(wire.qualifiedAdjacent.status, 'unknown')

  def test_frozen_reader_ignores_appended_qualified_observation(self):
    wire = custom.StarPilotRadarState.new_message()
    wire.leadLeft.status = True
    wire.leadLeft.dRel = 25.0
    wire.leadLeft.yRel = 3.0
    wire.leadLeft.radarTrackId = 17
    wire.leadRight.status = True
    wire.leadRight.dRel = 28.0
    wire.leadRight.yRel = -3.0
    wire.leadRight.radarTrackId = 18
    wire.adjacentStopped.status = True
    wire.adjacentStopped.dRel = 30.0
    wire.adjacentStopped.yRel = 2.5
    wire.adjacentStopped.radarTrackId = 19
    wire.qualifiedAdjacent.version = 1
    wire.qualifiedAdjacent.status = 'ambiguous'
    wire.qualifiedAdjacent.left.present = True
    self.assertEqual(
      _frozen_read(wire.to_bytes()),
      {
        'left': [True, 25.0, 3.0, 17],
        'right': [True, 28.0, -3.0, 18],
        'stopped': [True, 30.0, 2.5, 19],
      },
    )

  def test_frozen_compiled_root_and_nested_contracts_remain_additive(self):
    baseline = json.loads(CONTRACT.read_text())
    self.assertEqual(baseline['roots']['StarPilotRadarState'], '13289668853598257608')
    current = describe(custom, baseline['roots'])
    self.assertEqual(validate(current, baseline), [])
    self.assertEqual(set(baseline['nodes']['13289668853598257608']['fields']), {'0', '1', '2', '3'})
    mutated = copy.deepcopy(current)
    mutated['nodes']['13289668853598257608']['fields']['0']['name'] = 'falseLead'
    self.assertTrue(validate(mutated, baseline))

  def test_event_pointer_still_uses_original_id_at_114(self):
    schemas, policy, sync = read_inputs()
    self.assertEqual(validate_source(schemas, policy, sync), [])
    changed = schemas.copy()
    changed['openpilot/cereal/log.capnp'] = changed['openpilot/cereal/log.capnp'].replace(
      b'starpilotRadarState @114 :Custom.StarPilotRadarState;',
      b'starpilotRadarState @114 :Custom.CustomReserved6;',
    )
    self.assertTrue(any('event @114' in error for error in validate_source(changed, policy, sync)))


if __name__ == '__main__':
  unittest.main()
