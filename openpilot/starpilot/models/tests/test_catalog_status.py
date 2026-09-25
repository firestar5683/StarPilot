import hashlib
from pathlib import Path
import unittest

from openpilot.starpilot.models.catalog import BUNDLED_CURRENT, CATALOG, resolve_selection
from openpilot.starpilot.models.status import (ModelHealth, ModelLoad, ModelOutput, ModelProcess,
                                              ModelVariant, project_status)


class TestModelCatalogStatus(unittest.TestCase):
  def test_catalog_pins_current_source_and_lists_model_metadata(self):
    self.assertEqual(len(CATALOG), 100)
    entry = resolve_selection(None)
    self.assertEqual(entry.model_id, BUNDLED_CURRENT)
    source = Path(__file__).resolve().parents[4] / entry.source_path
    self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), entry.source_sha256)
    self.assertEqual(resolve_selection("rdf43").version, "v15")
    with self.assertRaises(ValueError):
      resolve_selection("unknown-model")
    with self.assertRaises(ValueError):
      resolve_selection("")

  def test_loaded_identity_requires_same_process_and_fresh_both_outputs(self):
    process = ModelProcess(421, 5000, True)
    load = ModelLoad(421, 5000, 1_100_000_000, BUNDLED_CURRENT, ModelVariant.SMALL, "a" * 64)
    output = ModelOutput(1_180_000_000, True, 1_185_000_000, True, False, False)
    self.assertEqual(project_status(None, process, load, output, 1_200_000_000).health, ModelHealth.ACTIVE)
    self.assertEqual(project_status(None, ModelProcess(422, 5001, True), load, output,
                                    1_200_000_000).health, ModelHealth.IDENTITY_UNAVAILABLE)
    self.assertEqual(project_status(None, process, load, output, 1_500_000_001).health, ModelHealth.STALE)
    self.assertEqual(project_status(None, process, load, ModelOutput(1_050_000_000, True, 1_185_000_000,
                                                                     True, False, False), 1_200_000_000).health,
                     ModelHealth.STALE)
    self.assertEqual(project_status(None, process, load, ModelOutput(1_180_000_000, True, 1_185_000_000,
                                                                     True, True, True), 1_200_000_000).health,
                     ModelHealth.FAILED)

  def test_runtime_stall_preserves_requested_big_and_active_small_identity(self):
    process = ModelProcess(421, 5000, True)
    load = ModelLoad(421, 5000, 1_100_000_000, 'sc23', ModelVariant.SMALL, 'a' * 64, 'chestnut-run-stalled')
    output = ModelOutput(1_180_000_000, True, 1_185_000_000, True, False, False)
    status = project_status('cinquev3', process, load, output, 1_200_000_000)
    self.assertEqual((status.requested_id, status.loaded_id, status.health), ('cinquev3', 'sc23', ModelHealth.ACTIVE))
    self.assertTrue(status.pending_next_start)
    self.assertEqual(status.fallback_reason, 'chestnut-run-stalled')

  def test_catalog_selection_preserves_actual_fallback_identity(self):
    process = ModelProcess(421, 5000, True)
    load = ModelLoad(421, 5000, 1_100_000_000, "sc23", ModelVariant.SMALL, "a" * 64, "chestnut-load-failed")
    output = ModelOutput(1_180_000_000, True, 1_185_000_000, True, False, False)
    status = project_status("cinquev3", process, load, output, 1_200_000_000)
    self.assertEqual((status.requested_id, status.loaded_id, status.health), ("cinquev3", "sc23", ModelHealth.ACTIVE))
    self.assertTrue(status.pending_next_start)
    self.assertEqual(status.fallback_reason, "chestnut-load-failed")
    impossible = ModelLoad(421, 5000, 1_100_000_000, "cinquev3", ModelVariant.SMALL, "a" * 64)
    self.assertEqual(project_status("cinquev3", process, impossible, output, 1_200_000_000).health, ModelHealth.IDENTITY_UNAVAILABLE)

  def test_no_saved_choice_or_stale_receipt_claims_active(self):
    process = ModelProcess(421, 5000, True)
    self.assertEqual(project_status(None, None, None, None, 1_200_000_000).health, ModelHealth.UNAVAILABLE)
    self.assertEqual(project_status(None, process, None, None, 1_200_000_000).health, ModelHealth.LOADING)
    stale_load = ModelLoad(421, 4999, 1_100_000_000, BUNDLED_CURRENT, ModelVariant.SMALL, "a" * 64)
    self.assertEqual(project_status(None, process, stale_load, None, 1_200_000_000).health, ModelHealth.LOADING)


if __name__ == "__main__":
  unittest.main()
