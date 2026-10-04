import ast
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.laptop_device_build import qcom_artifact_contract as contract


ROOT = Path(__file__).resolve().parents[3]


class TestQcomArtifactContract(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.package = Path(temporary.name)
    self.artifacts = self.package / "artifacts"
    self.artifacts.mkdir()
    self.commands = contract.commands(ROOT)
    for name in self.commands:
      (self.artifacts / name).write_bytes(f"artifact:{name}".encode())
    with patch("tools.laptop_device_build.validate_artifacts.require_qcom_pickle"):
      manifest = contract.record(ROOT, self.artifacts)
    (self.package / "manifest.json").write_text(json.dumps(manifest))

  def verify(self, name):
    with patch("tools.laptop_device_build.validate_artifacts.require_qcom_pickle"):
      return contract.verify(self.package, ROOT, name, self.commands[name])

  def compatible_package(self):
    manifest = json.loads((self.package / "manifest.json").read_text())
    current = contract.source_inventory(ROOT)
    old_hash = "0" * 64
    manifest["source"]["sources"][contract.COMPATIBILITY_SOURCE] = old_hash
    manifest["source_sha256"] = contract._inventory_signature(manifest["source"])
    (self.package / "manifest.json").write_text(json.dumps(manifest))
    evidence_dir = self.package / "compatibility"
    evidence_dir.mkdir()
    (evidence_dir / "qualification.txt").write_text("reviewed paired output evidence\n")
    observations = {name: [{"input": label, "shape": contract.COMPATIBILITY_OUTPUTS[name][0],
                            "dtype": contract.COMPATIBILITY_OUTPUTS[name][1],
                            "build_sha256": str(index + 4) * 64,
                            "runtime_sha256": str(index + 4) * 64}
                           for index, label in enumerate(("A", "B", "A"))]
                    for name in self.commands}
    evidence = {"version": 1, "method": "paired-qcom-output-sha256",
                "build_manifest_sha256": contract._sha(self.package / "manifest.json"),
                "compatible_source_sha256": contract._inventory_signature(current),
                "changed_source": {"path": contract.COMPATIBILITY_SOURCE, "build_sha256": old_hash,
                                   "runtime_sha256": current["sources"][contract.COMPATIBILITY_SOURCE]},
                "artifact_sha256": {name: entry["sha256"] for name, entry in manifest["artifacts"].items()},
                "paired_outputs": observations,
                "evidence_files": {"qualification.txt": contract._sha(evidence_dir / "qualification.txt")}}
    (self.package / "compatibility.json").write_text(json.dumps(evidence))
    return evidence, current

  def test_exact_source_and_artifacts_select_expected_target(self):
    name = "dmonitoring_model_tinygrad.pkl"
    self.assertEqual(self.verify(name)[0], self.artifacts / name)
    self.assertEqual(set(json.loads((self.package / "manifest.json").read_text())["artifacts"]), set(self.commands))

  def historical_package(self, compatible=False):
    if compatible:
      evidence, current = self.compatible_package()
    manifest = json.loads((self.package / "manifest.json").read_text())
    command = " ".join((f'{contract.FLAGS} taskset -c 0-7 python3 "{ROOT}/tinygrad_repo/examples/openpilot/compile_onnx.py"',
                        f'"{ROOT / contract.RETIRED_SOURCE}" "{ROOT / contract.MODEL_DIR / contract.RETIRED_TARGET}"',
                        '--out-of-band --benchmark-runs 1'))
    manifest['source']['sources'][contract.RETIRED_SOURCE] = contract.RETIRED_SOURCE_SHA256
    manifest['source']['commands'][contract.RETIRED_TARGET] = contract._tokens(command, ROOT)
    manifest['artifacts'][contract.RETIRED_TARGET] = {'sha256': contract.RETIRED_ARTIFACT_SHA256, 'size': 70473368}
    manifest['source_sha256'] = contract._inventory_signature(manifest['source'])
    (self.package / 'manifest.json').write_text(json.dumps(manifest))
    if compatible:
      current, _ = contract._historical_inventory(manifest, current, self.commands, ROOT)
      evidence['compatible_source_sha256'] = contract._inventory_signature(current)
      evidence['build_manifest_sha256'] = contract._sha(self.package / 'manifest.json')
      evidence['artifact_sha256'][contract.RETIRED_TARGET] = contract.RETIRED_ARTIFACT_SHA256
      shape, dtype = contract.COMPATIBILITY_OUTPUTS[contract.RETIRED_TARGET]
      evidence['paired_outputs'][contract.RETIRED_TARGET] = [
        {'input': label, 'shape': shape, 'dtype': dtype, 'build_sha256': 'a' * 64, 'runtime_sha256': 'a' * 64}
        for label in ('A', 'B', 'A')]
      (self.package / 'compatibility.json').write_text(json.dumps(evidence))

  def test_only_dm_and_warps_are_current_build_inputs(self):
    self.assertEqual(len(self.commands), 5)
    self.assertNotIn(contract.RETIRED_TARGET, self.commands)
    self.assertNotIn(contract.RETIRED_SOURCE, contract.STATIC_SOURCES)
    tree = ast.parse((ROOT / 'openpilot/selfdrive/modeld/SConscript').read_text())
    models = [tuple(arg.value for arg in node.args) for node in ast.walk(tree)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'compile_model']
    self.assertEqual(models, [('models/dmonitoring_model.onnx', 'models/dmonitoring_model_tinygrad.pkl')])
    with self.assertRaisesRegex(ValueError, 'command recipe changed'):
      contract.verify(self.package, ROOT, contract.RETIRED_TARGET, 'ignored')

  def test_historical_package_uses_verified_five_subset_without_retired_bytes(self):
    for compatible in (False, True):
      with self.subTest(compatible=compatible):
        self.historical_package(compatible)
        before = (self.package / 'manifest.json').read_bytes()
        for name in self.commands:
          self.assertEqual(self.verify(name)[0], self.artifacts / name)
        self.assertEqual((self.package / 'manifest.json').read_bytes(), before)
        self.assertFalse((self.artifacts / contract.RETIRED_TARGET).exists())

  def test_historical_subset_does_not_hide_unreviewed_source_or_artifact(self):
    self.historical_package(True)
    current = contract.source_inventory(ROOT)
    current['sources']['unreviewed.py'] = 'f' * 64
    with patch.object(contract, 'source_inventory', return_value=current), self.assertRaisesRegex(ValueError, 'outside reviewed'):
      self.verify('dmonitoring_model_tinygrad.pkl')
    (self.artifacts / 'dm_warp_1344x760_tinygrad.pkl').write_bytes(b'changed')
    with self.assertRaisesRegex(ValueError, 'artifact mismatch'):
      self.verify('dmonitoring_model_tinygrad.pkl')

  def test_historical_retirement_requires_exact_reviewed_provenance(self):
    self.historical_package()
    manifest = json.loads((self.package / 'manifest.json').read_text())
    manifest['source']['sources'][contract.RETIRED_SOURCE] = 'f' * 64
    manifest['source_sha256'] = contract._inventory_signature(manifest['source'])
    (self.package / 'manifest.json').write_text(json.dumps(manifest))
    with self.assertRaisesRegex(ValueError, 'Unreviewed retired'):
      self.verify('dmonitoring_model_tinygrad.pkl')

  def test_source_and_command_changes_reject(self):
    name = "dmonitoring_model_tinygrad.pkl"
    with patch.object(contract, "_sources", return_value={"changed.py": "0" * 64}), \
         self.assertRaisesRegex(ValueError, "sources changed"):
      self.verify(name)
    with self.assertRaisesRegex(ValueError, "command recipe changed"):
      contract.verify(self.package, ROOT, name, self.commands[name] + " --different")

  def test_one_artifact_change_or_missing_member_rejects_whole_package(self):
    (self.artifacts / "dm_warp_1344x760_tinygrad.pkl").write_bytes(b"changed")
    with self.assertRaisesRegex(ValueError, "artifact mismatch"):
      self.verify("dmonitoring_model_tinygrad.pkl")
    manifest = json.loads((self.package / "manifest.json").read_text())
    del manifest["artifacts"]["dm_warp_1344x760_tinygrad.pkl"]
    (self.package / "manifest.json").write_text(json.dumps(manifest))
    with self.assertRaisesRegex(ValueError, "source or artifact set"):
      self.verify("dmonitoring_model_tinygrad.pkl")

  def test_wrong_backend_pickle_rejects_even_with_matching_hash(self):
    with self.assertRaises(ValueError):
      contract.verify(self.package, ROOT, "dmonitoring_model_tinygrad.pkl", self.commands["dmonitoring_model_tinygrad.pkl"])

  def test_malformed_manifest_artifacts_reject_cleanly(self):
    manifest = json.loads((self.package / "manifest.json").read_text())
    for malformed in (None, [], "not-a-map"):
      manifest["artifacts"] = malformed
      (self.package / "manifest.json").write_text(json.dumps(manifest))
      with self.subTest(malformed=malformed), self.assertRaisesRegex(ValueError, "artifact set"):
        self.verify("dmonitoring_model_tinygrad.pkl")

  def test_changed_bytes_during_copy_leave_existing_target(self):
    name = "dmonitoring_model_tinygrad.pkl"
    target = self.package / name
    target.write_bytes(b"previous")
    with patch("tools.laptop_device_build.validate_artifacts.require_qcom_pickle"), \
         patch.object(contract.shutil, "copyfileobj", side_effect=lambda source, output: output.write(b"changed")), \
         self.assertRaisesRegex(ValueError, "changed during copy"):
      contract.import_artifact(self.package, ROOT, target, self.commands[name])
    self.assertEqual(target.read_bytes(), b"previous")
    self.assertFalse(list(self.package.glob(".qcom-import-*")))

  def test_exact_compatible_source_and_all_five_artifacts_verify(self):
    self.compatible_package()
    for name in self.commands:
      with self.subTest(name=name):
        self.assertEqual(self.verify(name)[0], self.artifacts / name)

  def test_compatible_source_rejects_unrelated_source_or_recipe_change(self):
    _, current = self.compatible_package()
    changed = copy.deepcopy(current)
    changed["sources"]["unrelated.py"] = "1" * 64
    with patch.object(contract, "source_inventory", return_value=changed), \
         self.assertRaisesRegex(ValueError, "outside reviewed"):
      self.verify("dmonitoring_model_tinygrad.pkl")
    changed = copy.deepcopy(current)
    changed["commands"]["dmonitoring_model_tinygrad.pkl"].append("--new-option")
    with patch.object(contract, "source_inventory", return_value=changed), \
         self.assertRaisesRegex(ValueError, "outside reviewed"):
      self.verify("dmonitoring_model_tinygrad.pkl")

  def test_compatible_source_rejects_artifact_or_paired_output_change(self):
    evidence, _ = self.compatible_package()
    del evidence["paired_outputs"]["dmonitoring_model_tinygrad.pkl"]
    (self.package / "compatibility.json").write_text(json.dumps(evidence))
    with self.assertRaisesRegex(ValueError, "lacks a stock target"):
      self.verify("dmonitoring_model_tinygrad.pkl")
    evidence["paired_outputs"]["dmonitoring_model_tinygrad.pkl"] = [
      {"input": label, "shape": contract.COMPATIBILITY_OUTPUTS["dmonitoring_model_tinygrad.pkl"][0],
       "dtype": "float32", "build_sha256": str(index + 4) * 64,
       "runtime_sha256": str(index + 4) * 64}
      for index, label in enumerate(("A", "B", "A"))]
    (self.package / "compatibility.json").write_text(json.dumps(evidence))
    (self.artifacts / "dmonitoring_model_tinygrad.pkl").write_bytes(b"changed")
    with self.assertRaisesRegex(ValueError, "artifact mismatch"):
      self.verify("dmonitoring_model_tinygrad.pkl")

  def test_compatible_source_rejects_changed_or_unsafe_evidence(self):
    evidence, _ = self.compatible_package()
    evidence_file = self.package / "compatibility" / "qualification.txt"
    evidence_file.write_text("changed evidence\n")
    with self.assertRaisesRegex(ValueError, "evidence file mismatch"):
      self.verify("dmonitoring_model_tinygrad.pkl")
    evidence_file.write_text("reviewed paired output evidence\n")
    evidence["evidence_files"] = {"../qualification.txt": contract._sha(evidence_file)}
    (self.package / "compatibility.json").write_text(json.dumps(evidence))
    with self.assertRaisesRegex(ValueError, "evidence filename"):
      self.verify("dmonitoring_model_tinygrad.pkl")
    evidence["evidence_files"] = {"qualification.txt": contract._sha(evidence_file)}
    (self.package / "compatibility.json").write_text(json.dumps(evidence))
    outside = self.package / "outside.txt"
    outside.write_text("reviewed paired output evidence\n")
    evidence_file.unlink()
    evidence_file.symlink_to(outside)
    with self.assertRaisesRegex(ValueError, "evidence file mismatch"):
      self.verify("dmonitoring_model_tinygrad.pkl")
    evidence_file.unlink()
    evidence_file.write_text("reviewed paired output evidence\n")
    evidence_dir = self.package / "compatibility"
    evidence_dir.rename(self.package / "actual_evidence")
    evidence_dir.symlink_to(self.package / "actual_evidence", target_is_directory=True)
    with self.assertRaisesRegex(ValueError, "evidence directory"):
      self.verify("dmonitoring_model_tinygrad.pkl")

  def test_compatible_source_rejects_unequal_outputs_and_stale_source_binding(self):
    evidence, _ = self.compatible_package()
    original = copy.deepcopy(evidence)
    evidence["paired_outputs"]["dmonitoring_model_tinygrad.pkl"][1]["runtime_sha256"] = "a" * 64
    (self.package / "compatibility.json").write_text(json.dumps(evidence))
    with self.assertRaisesRegex(ValueError, "Invalid QCOM paired outputs"):
      self.verify("dmonitoring_model_tinygrad.pkl")
    original["compatible_source_sha256"] = "b" * 64
    (self.package / "compatibility.json").write_text(json.dumps(original))
    with self.assertRaisesRegex(ValueError, "not bound"):
      self.verify("dmonitoring_model_tinygrad.pkl")

  def test_compatible_source_rejects_bool_versions_and_duplicate_json_fields(self):
    evidence, _ = self.compatible_package()
    evidence["version"] = True
    (self.package / "compatibility.json").write_text(json.dumps(evidence))
    with self.assertRaisesRegex(ValueError, "not bound"):
      self.verify("dmonitoring_model_tinygrad.pkl")
    (self.package / "compatibility.json").write_text('{"version":1,"version":1}')
    with self.assertRaisesRegex(ValueError, "Duplicate QCOM manifest field"):
      self.verify("dmonitoring_model_tinygrad.pkl")
    manifest = json.loads((self.package / "manifest.json").read_text())
    manifest["version"] = True
    (self.package / "manifest.json").write_text(json.dumps(manifest))
    with self.assertRaisesRegex(ValueError, "source or artifact set"):
      self.verify("dmonitoring_model_tinygrad.pkl")


class TestQcomSupplementalRuntimeCompatibility(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.package = Path(temporary.name)
    self.current = {"sources": {name: hashes[1] for name, hashes in contract.RUNTIME_EXTENSION_CHANGES.items()},
                    "commands": {"driving_tinygrad.pkl": ["DEV=QCOM", "IMAGE=1", "compile"]}}
    self.current["sources"].update(contract.RUNTIME_EXTENSION_ADDITIONS)
    self.current["sources"].update({contract.COMPATIBILITY_SOURCE: "a" * 64, "model.onnx": "b" * 64})
    parent = copy.deepcopy(self.current)
    for name, hashes in contract.RUNTIME_EXTENSION_CHANGES.items():
      parent["sources"][name] = hashes[0]
    for name in contract.RUNTIME_EXTENSION_ADDITIONS:
      del parent["sources"][name]
    saved = copy.deepcopy(parent)
    saved["sources"][contract.COMPATIBILITY_SOURCE] = "c" * 64
    self.manifest = {"source": saved, "source_sha256": contract._inventory_signature(saved),
                     "artifacts": {name: {"sha256": "d" * 64} for name in contract.COMPATIBILITY_OUTPUTS}}
    self.manifest_path = self.package / "manifest.json"
    self.manifest_path.write_text(json.dumps(self.manifest))
    evidence_dir = self.package / "compatibility"
    evidence_dir.mkdir()
    (evidence_dir / "outputs.txt").write_text("A/B/A output hashes\n")
    self.evidence = {"version": 1, "method": "paired-qcom-output-sha256",
                     "build_manifest_sha256": contract._sha(self.manifest_path),
                     "compatible_source_sha256": contract._inventory_signature(parent),
                     "changed_source": {"path": contract.COMPATIBILITY_SOURCE, "build_sha256": "c" * 64, "runtime_sha256": "a" * 64},
                     "artifact_sha256": dict.fromkeys(contract.COMPATIBILITY_OUTPUTS, "d" * 64),
                     "paired_outputs": {name: [{"input": label, "shape": shape, "dtype": dtype,
                                                "build_sha256": "e" * 64, "runtime_sha256": "e" * 64}
                                               for label in ("A", "B", "A")]
                                        for name, (shape, dtype) in contract.COMPATIBILITY_OUTPUTS.items()},
                     "evidence_files": {"outputs.txt": contract._sha(evidence_dir / "outputs.txt")}}
    self.parent_path = self.package / "compatibility.json"
    self.parent_path.write_text(json.dumps(self.evidence))
    self.bind_extension()

  def bind_extension(self):
    extension = {"version": 1, "profile": contract.RUNTIME_EXTENSION_PROFILE,
                 "parent_evidence_sha256": contract._sha(self.parent_path),
                 "compatible_source_sha256": contract._inventory_signature(self.current)}
    (self.package / "runtime-compatibility.json").write_text(json.dumps(extension))

  def verify(self):
    contract._verify_runtime_compatibility(self.package, self.manifest_path, self.manifest,
                                         self.current, dict.fromkeys(contract.COMPATIBILITY_OUTPUTS))

  def test_reviewed_extension_preserves_original_manifest_and_parent_attestation(self):
    before = self.manifest_path.read_bytes(), self.parent_path.read_bytes()
    self.verify()
    self.assertEqual(before, (self.manifest_path.read_bytes(), self.parent_path.read_bytes()))

  def test_each_reviewed_source_and_added_helper_requires_exact_bytes(self):
    original = copy.deepcopy(self.current)
    for name in (*contract.RUNTIME_EXTENSION_CHANGES, *contract.RUNTIME_EXTENSION_ADDITIONS):
      with self.subTest(name=name):
        self.current = copy.deepcopy(original)
        self.current["sources"][name] = "f" * 64
        self.bind_extension()
        with self.assertRaisesRegex(ValueError, "Unreviewed QCOM runtime"):
          self.verify()

  def test_extra_missing_or_model_changed_source_is_not_normalized_away(self):
    original = copy.deepcopy(self.current)
    for kind in ("extra", "missing", "model"):
      with self.subTest(kind=kind):
        self.current = copy.deepcopy(original)
        if kind == "extra":
          self.current["sources"]["unexpected.py"] = "f" * 64
        elif kind == "missing":
          del self.current["sources"]["model.onnx"]
        else:
          self.current["sources"]["model.onnx"] = "f" * 64
        self.bind_extension()
        with self.assertRaisesRegex(ValueError, "outside reviewed"):
          self.verify()

  def test_compile_command_change_remains_rejected(self):
    self.current["commands"]["driving_tinygrad.pkl"].append("FLOAT16=0")
    self.bind_extension()
    with self.assertRaisesRegex(ValueError, "outside reviewed"):
      self.verify()

  def test_parent_evidence_mutation_and_missing_supplement_reject(self):
    original = self.parent_path.read_bytes()
    self.parent_path.write_bytes(original + b"\n")
    with self.assertRaisesRegex(ValueError, "parent evidence"):
      self.verify()
    self.parent_path.write_bytes(original)
    (self.package / "runtime-compatibility.json").unlink()
    with self.assertRaisesRegex(ValueError, "outside reviewed"):
      self.verify()

  def test_artifact_substitution_and_unequal_paired_output_reject_after_rebinding(self):
    original = copy.deepcopy(self.evidence)
    for kind in ("artifact", "output"):
      with self.subTest(kind=kind):
        self.evidence = copy.deepcopy(original)
        if kind == "artifact":
          self.evidence["artifact_sha256"]["driving_tinygrad.pkl"] = "f" * 64
        else:
          self.evidence["paired_outputs"]["driving_tinygrad.pkl"][0]["runtime_sha256"] = "f" * 64
        self.parent_path.write_text(json.dumps(self.evidence))
        self.bind_extension()
        with self.assertRaises(ValueError):
          self.verify()

  def test_supplement_symlink_unknown_profile_and_extra_fields_reject(self):
    path = self.package / "runtime-compatibility.json"
    good = json.loads(path.read_text())
    for mutation in ({"profile": "unreviewed"}, {"extra": True}, {"version": True}):
      path.write_text(json.dumps(good | mutation))
      with self.subTest(mutation=mutation), self.assertRaises(ValueError):
        self.verify()
    path.unlink()
    path.symlink_to(self.parent_path)
    with self.assertRaisesRegex(ValueError, "Invalid QCOM runtime extension"):
      self.verify()
