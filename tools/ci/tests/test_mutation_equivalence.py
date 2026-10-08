from copy import deepcopy
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from opendbc.safety.tests import mutation
from tools.ci import run_safety_qualification as qualification


class TestMutationEquivalence(TestCase):
  @staticmethod
  def fixture(expression, original="250000U", mutated="250001U"):
    source = f"int compare(unsigned int elapsed) {{ return elapsed < ({expression}); }}\n"
    start = source.index(original)
    site = mutation.MutationSite(0, start, start + len(original), start, start + len(original),
                                 1, original, mutated, "boundary", mutation.SAFETY_DIR / "lateral.h", 1)
    return source, [site]

  def test_actual_compiler_proves_same_unsigned_quotient_type_and_value(self):
    source, sites = self.fixture("250000U / 2U")
    proof, = mutation.prove_equivalent_divisions(source, sites, set())
    self.assertEqual((proof["original_expression"], proof["mutated_expression"], proof["c_type"], proof["value"]),
                     ("250000U / 2U", "250001U / 2U", "unsigned int", 125000))
    self.assertEqual(proof["site_id"], 0)
    self.assertEqual(len(proof["compiler_sha256"]), 64)
    self.assertEqual(len(proof["proof_source_sha256"]), 64)
    # Reject a mathematically false claimed quotient using the real compiler.
    false_proof = [{**proof, "value": 125001}]
    result = subprocess.run(["cc", *proof["compiler_flags"]], input=mutation.division_proof_source(false_proof),
                            capture_output=True, text=True, timeout=30)
    self.assertNotEqual(result.returncode, 0)

  def test_narrow_closed_operand_scope_rejects_every_unproved_context(self):
    for expression, original, mutated in (
      ("250000U / 3U", "3U", "4U"),
      ("250000 / 2U", "250000", "250001"),
      ("250000UL / 2U", "250000UL", "250001UL"),
      ("250000U / 0U", "250000U", "250001U"),
      ("250000.0 / 2U", "250000.0", "250001.0"),
      ("(unsigned int)250000U / 2U", "250000U", "250001U"),
      ("250000U / elapsed", "250000U", "250001U"),
      ("250000U / fn()", "250000U", "250001U"),
      ("(250000U / 2U) + elapsed", "250000U", "250001U"),
      ("(250000U / 2U) + 1U", "250000U", "250001U"),
      ("4294967295U / 2U", "4294967295U", "4294967296U"),
    ):
      with self.subTest(expression=expression):
        source, sites = self.fixture(expression, original, mutated)
        self.assertEqual(mutation.equivalent_division_candidates(source, sites, set()), [])
    source, sites = self.fixture("250000U / 2U")
    self.assertEqual(mutation.equivalent_division_candidates(source, sites, {0}), [])

  def test_failed_compiler_proof_is_fatal_not_an_equivalence_allowance(self):
    source, sites = self.fixture("250000U / 2U")
    with patch.object(mutation.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "type mismatch")):
      with self.assertRaisesRegex(RuntimeError, "compiler proof failed"):
        mutation.prove_equivalent_divisions(source, sites, set())

  @staticmethod
  def full_artifact(directory):
    sites, _, excluded, source = mutation.enumerate_sites(mutation.ROOT / mutation.SAFETY_C_REL, directory / "source.i")
    proofs = mutation.prove_equivalent_divisions(source, sites, excluded)
    equivalent_ids = {proof["site_id"] for proof in proofs}
    executed = [site for site in sites if site.site_id not in excluded | equivalent_ids]
    results = [mutation.MutantResult(site, "killed", 0.0, "artifact shape fixture, not a mutation qualification") for site in executed]
    path = directory / "results.json"
    mutation.write_results_json(path, discovered_sites=sites, pruned_ids=excluded, results=results,
                                site_targets={site.site_id: ["fixture.TestShape.test_one"] for site in executed},
                                preprocessed_source=source, baseline_sec=0.0, proven_equivalent=proofs)
    summary = {"candidates": len(sites), "pruned_build_incompatible": len(excluded), "proven_equivalent": len(proofs),
               "total": len(executed), "killed": len(executed), "survived": 0, "infra_error": 0}
    return path, json.loads(path.read_text()), summary

  def test_full_partition_rechecks_actual_context_type_compiler_and_exact_ids(self):
    with TemporaryDirectory() as directory:
      path, original, summary = self.full_artifact(Path(directory))
      self.assertTrue(original["proven_equivalent"])
      self.assertTrue(qualification.complete_mutation_artifact(path, summary))
      for name, change in (
        ("value", lambda artifact: artifact["proven_equivalent"][0].update(value=125001)),
        ("expression", lambda artifact: artifact["proven_equivalent"][0].update(mutated_expression="0U / 2U")),
        ("context", lambda artifact: artifact["proven_equivalent"][0].update(comparison_operator="==")),
        ("compiler", lambda artifact: artifact["proven_equivalent"][0].update(compiler_sha256="f" * 64)),
        ("proof hash", lambda artifact: artifact["proven_equivalent"][0].update(proof_source_sha256="f" * 64)),
        ("preprocessed hash", lambda artifact: artifact.update(preprocessed_source_sha256="f" * 64)),
        ("missing", lambda artifact: artifact["proven_equivalent"].pop()),
        ("duplicate", lambda artifact: artifact["proven_equivalent"].append(artifact["proven_equivalent"][0])),
        ("overlap", lambda artifact: artifact["proven_equivalent"][0].update(site_id=artifact["results"][0]["site_id"])),
        ("out of range", lambda artifact: artifact["proven_equivalent"][0].update(site_id=artifact["discovered"])),
      ):
        with self.subTest(forgery=name):
          artifact = deepcopy(original)
          change(artifact)
          path.write_text(json.dumps(artifact))
          self.assertFalse(qualification.complete_mutation_artifact(path, summary))
      path.write_text(json.dumps(original))
      with patch.object(qualification.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "proof failure")):
        self.assertFalse(qualification.complete_mutation_artifact(path, summary))
      # Even a internally reconciled empty partition cannot conceal a known
      # equivalent candidate by merely relabelling its absence as build pruning.
      artifact = deepcopy(original)
      removed = artifact["proven_equivalent"].pop()
      artifact["pruned_build_incompatible"].append(removed)
      path.write_text(json.dumps(artifact))
      forged_summary = {**summary, "proven_equivalent": summary["proven_equivalent"] - 1,
                        "pruned_build_incompatible": summary["pruned_build_incompatible"] + 1}
      self.assertFalse(qualification.complete_mutation_artifact(path, forged_summary))

  def test_empty_mutated_operator_is_permitted_only_for_negation_removal(self):
    from tools.ci.tests.test_safety_qualification import TestSafetyQualificationRunner
    original = TestSafetyQualificationRunner.mutation_artifact()
    summary = {"candidates": 1, "pruned_build_incompatible": 0, "proven_equivalent": 0,
               "total": 1, "killed": 1, "survived": 0, "infra_error": 0}
    with TemporaryDirectory() as directory:
      path = Path(directory) / "results.json"
      for family, operator, expected in (("remove_negation", "!", True), ("boundary", "!", False),
                                         ("remove_negation", "0", False), ("comparison", "!", False)):
        with self.subTest(family=family, operator=operator):
          artifact = deepcopy(original)
          artifact["results"][0].update(mutator=family, original_op=operator, mutated_op="")
          path.write_text(json.dumps(artifact))
          self.assertEqual(qualification.complete_mutation_artifact(path, summary), expected)

  def test_v1_never_reinterprets_old_survivors_as_equivalent(self):
    from tools.ci.tests.test_safety_qualification import TestSafetyQualificationRunner
    artifact = TestSafetyQualificationRunner.mutation_artifact()
    artifact["results"][0]["outcome"] = "survived"
    summary = {"candidates": 1, "pruned_build_incompatible": 0, "proven_equivalent": 0,
               "total": 1, "killed": 0, "survived": 1, "infra_error": 0}
    with TemporaryDirectory() as directory:
      path = Path(directory) / "results.json"
      path.write_text(json.dumps(artifact))
      self.assertTrue(qualification.complete_mutation_artifact(path, summary))
      artifact["proven_equivalent"] = [{"site_id": 0}]
      path.write_text(json.dumps(artifact))
      self.assertFalse(qualification.complete_mutation_artifact(path, summary))
      log = "\n".join(("Found 1 unique candidates", "  pruned_build_incompatible: 0", "  total: 1",
                       "  killed: 0", "  survived: 1", "  infra_error: 0", ""))
      artifact.pop("proven_equivalent")
      path.write_text(json.dumps(artifact))
      gate = qualification.Gate("mutation-full", Path(directory), qualification.sys.executable)
      consumed_path = Path(directory) / "mutation-results.json"
      path.unlink()
      def fake_run(*args, **kwargs):
        consumed_path.write_text(json.dumps(artifact))
        return 0, log
      with patch.object(gate, "run", side_effect=fake_run):
        # A v1 survived result remains fatal despite a successful subprocess.
        self.assertFalse(gate.execute())
      self.assertTrue(gate.summary["artifact_valid"])
