"""Causal whole-maneuver regression; no native runtime or substituted clocks."""

import unittest
from openpilot.starpilot.flm.evidence_phases import stage_blocks


def block(name, first):
  return {
    'block_id': name,
    'samples': tuple({'control_ns': first + index * 10, 'apply_ns': first + index * 10 + 1, 'mono_ns': first + index * 10 + 101} for index in range(80)),
  }


class CausalPhaseTests(unittest.TestCase):
  def test_whole_boundary_block_quarantined_without_row_mutation(self):
    raw = (block('calibration', 100), block('boundary', 900), block('fresh', 2000))
    accepted, boundary = stage_blocks(raw, 1, 1000)
    self.assertEqual(boundary, ('boundary',))
    self.assertEqual(accepted, (raw[2],))
    self.assertIs(accepted[0], raw[2])
    self.assertEqual(len(raw[1]['samples']), 80)
    self.assertEqual(raw[1]['samples'][0]['control_ns'], 900)

  def test_equal_cutoff_never_becomes_stage_evidence(self):
    accepted, boundary = stage_blocks((block('equal', 1000),), 0, 1000)
    self.assertEqual(accepted, ())
    self.assertEqual(boundary, ('equal',))

  def test_all_three_original_support_clocks_must_be_ordered(self):
    bad = block('bad', 2000)
    bad['samples'] = ({'control_ns': 2000, 'apply_ns': 1999, 'mono_ns': 2100},)
    with self.assertRaises(ValueError):
      stage_blocks((bad,), 0, 1000)

  def test_empty_block_cannot_manufacture_maturity(self):
    with self.assertRaises(ValueError):
      stage_blocks(({'block_id': 'empty', 'samples': ()},), 0, 1)


if __name__ == '__main__':
  unittest.main()
