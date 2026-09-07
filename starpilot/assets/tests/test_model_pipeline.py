import hashlib
import io
import json
import sys
from pathlib import Path

from scripts import model_compiler
from scripts import reconcile_v23_artifacts
from scripts.model_compiler import split_oversized_artifact
from openpilot.common import file_chunker
from openpilot.selfdrive.modeld import compile_modeld
from openpilot.starpilot.assets import download_functions
from openpilot.starpilot.assets import model_manager
from openpilot.starpilot.assets.model_manager import MANIFEST_CANDIDATES, ModelManager
from openpilot.starpilot.common.model_versions import UNIFIED_ARTIFACT_FORMAT


def test_v25_is_the_only_manifest_candidate():
  assert MANIFEST_CANDIDATES == ("v25",)


def test_v25_manifest_is_loaded_from_models_checkout():
  assert ModelManager._manifest_paths("v25") == ("Models/model_names_v25.json",)


def test_resource_sources_prefer_huggingface_then_github(monkeypatch):
  monkeypatch.setattr(download_functions, "is_url_pingable", lambda url: True)
  assert download_functions.get_resource_urls() == [
    download_functions.HF_BUCKET_URL,
    download_functions.GITHUB_URL,
  ]
  assert all("gitlab" not in url for url in download_functions.get_resource_urls())


def test_huggingface_manifest_lives_under_manifests():
  assert ModelManager._hf_manifest_paths("v25") == ("manifests/model_names_v25.json",)


def test_v25_artifacts_only_use_versioned_paths():
  hf_url = "https://huggingface.co/buckets/StarPilot-Driving/StarPilot-Resources"
  github_url = "https://raw.githubusercontent.com/firestar5683/StarPilot-Resources"
  filename = "pop223_driving_tinygrad.pkl"

  assert ModelManager._artifact_source_urls(hf_url, "v25", "pop223", filename) == (
    f"{hf_url}/models/v25/pop223/{filename}",
  )
  assert ModelManager._artifact_source_urls(github_url, "v25", "pop223", filename) == (
    f"{github_url}/Models/v25/pop223/{filename}",
  )


def test_old_manifest_ids_resolve_to_v23_namespace():
  manager = object.__new__(ModelManager)
  manager.available_models = ["pop223", "tr14223"]
  assert manager._resolve_manifest_model_key("pop22") == "pop223"
  assert manager._resolve_manifest_model_key("tr1422") == "tr14223"
  assert manager._resolve_manifest_model_key("missing") == "missing"


def test_old_remove_avgpool_ids_resolve_to_artifact_ids():
  manager = object.__new__(ModelManager)
  manager.available_models = ["remove-avgpoolv4"]
  assert manager._resolve_manifest_model_key("napv4") == "remove-avgpoolv4"
  assert model_manager.canonical_model_key("napv4") == "remove-avgpoolv4"


def test_model_cleanup_matches_legacy_split_artifacts():
  assert model_manager.is_driving_artifact_file("pop223_driving_tinygrad.pkl")
  assert model_manager.is_driving_artifact_file("driving_vision_tinygrad.pkl")
  assert model_manager.is_driving_artifact_file("driving_off_policy_tinygrad.pkl.p00")
  assert not model_manager.is_driving_artifact_file("dmonitoring_model_tinygrad.pkl")
  assert model_manager.is_driving_artifact_file("local-test_driving_tinygrad.pkl")


def test_manifest_migration_purges_old_artifacts_and_redownloads_selected(tmp_path, monkeypatch):
  monkeypatch.setattr(model_manager, "MODELS_PATH", tmp_path)
  for filename in (
    "pop223_driving_tinygrad.pkl",
    "pop223_driving_tinygrad.pkl.p00",
    "other_driving_tinygrad.pkl.chunk01of02",
    "other_driving_tinygrad.pkl.chunk02of02",
    "other_driving_tinygrad.pkl.chunkmanifest",
    "local-test_driving_tinygrad.pkl",
    "dmonitoring_model_tinygrad.pkl",
  ):
    (tmp_path / filename).write_bytes(b"old")

  class FakeParamsMemory:
    def put(self, key, value):
      del key, value

  manager = object.__new__(ModelManager)
  manager.params_memory = FakeParamsMemory()
  manager.available_models = ["rdf43", "pop223"]
  manager.available_model_names = ["Regret Driven Framework V4", "Pop V2"]
  manager.model_versions = ["v15", "v15"]
  manager.artifact_formats = [UNIFIED_ARTIFACT_FORMAT, UNIFIED_ARTIFACT_FORMAT]

  def fake_download(model_key):
    assert model_key == "pop223"
    (tmp_path / "pop223_driving_tinygrad.pkl").write_bytes(b"v25")

  monkeypatch.setattr(manager, "download_model", fake_download)
  manager._migrate_model_artifacts("pop223")

  assert (tmp_path / "pop223_driving_tinygrad.pkl").read_bytes() == b"v25"
  assert (tmp_path / "local-test_driving_tinygrad.pkl").read_bytes() == b"old"
  assert (tmp_path / "dmonitoring_model_tinygrad.pkl").read_bytes() == b"old"
  assert not (tmp_path / "pop223_driving_tinygrad.pkl.p00").exists()
  assert not (tmp_path / "other_driving_tinygrad.pkl.chunkmanifest").exists()


def test_behavior_version_does_not_control_artifact_layout():
  manager = object.__new__(ModelManager)
  assert manager._required_files("example", UNIFIED_ARTIFACT_FORMAT) == [
    "example_driving_tinygrad.pkl",
  ]
  assert manager._required_files("example", "") == [
    "example_driving_tinygrad.pkl",
  ]
  assert manager._required_files("example", "split") == []


def test_supercombo_defaults_to_v16_without_changing_split_defaults():
  assert model_compiler.resolve_behavior_version("new-model", None, "supercombo") == "v16"
  assert model_compiler.resolve_behavior_version("legacy-model", None, "split") == ""
  assert model_compiler.resolve_behavior_version("new-model", "v15", "supercombo") == "v15"


def test_external_gpu_requirement_is_cached_from_manifest(tmp_path, monkeypatch):
  monkeypatch.setattr(model_manager, "MODELS_PATH", tmp_path)
  manager = object.__new__(ModelManager)
  metadata = manager._build_artifact_metadata_map([
    {"id": "large", "artifact_format": UNIFIED_ARTIFACT_FORMAT, "uses_external_gpu": True},
    {"id": "normal", "artifact_format": UNIFIED_ARTIFACT_FORMAT},
  ])
  (tmp_path / model_manager.ARTIFACT_METADATA_CACHE).write_text(json.dumps(metadata))

  assert model_manager.model_uses_external_gpu("large")
  assert not model_manager.model_uses_external_gpu("normal")
  assert not model_manager.model_uses_external_gpu("missing")


def test_active_small_and_big_profiles_migrate_from_legacy_selection(tmp_path, monkeypatch):
  monkeypatch.setattr(model_manager, "MODELS_PATH", tmp_path)
  (tmp_path / model_manager.ARTIFACT_METADATA_CACHE).write_text(json.dumps({
    "small-one": {"uses_external_gpu": False},
    "big-one": {"uses_external_gpu": True},
  }))

  class FakeParams:
    def __init__(self, selected):
      self.values = {
        "Model": selected,
        "DrivingModel": selected,
        "DrivingModelName": selected.title(),
        "DrivingModelVersion": "v16",
        "AvailableModels": "rdf43,small-one,big-one",
        "AvailableModelNames": "Regret Driven Framework V4,Small One,Big One",
        "ModelVersions": "v15,v16,v16",
      }

    def get(self, key):
      return self.values.get(key)

    def put(self, key, value):
      self.values[key] = value

  small_params = FakeParams("small-one")
  assert model_manager.get_model_profile(small_params, "small") == ("small-one", "Small One", "v16")
  assert model_manager.get_model_profile(small_params, "big") == ("", "", "")

  big_params = FakeParams("big-one")
  assert model_manager.get_model_profile(big_params, "small") == (
    "rdf43", "Regret Driven Framework V4", "v15",
  )
  assert model_manager.get_model_profile(big_params, "big") == ("big-one", "Big One", "v16")


def test_runtime_model_metadata_does_not_overwrite_model_profiles(tmp_path, monkeypatch):
  monkeypatch.setattr(model_manager, "MODELS_PATH", tmp_path)
  (tmp_path / model_manager.ARTIFACT_METADATA_CACHE).write_text(json.dumps({
    "small-one": {"uses_external_gpu": False},
    "big-one": {"uses_external_gpu": True},
  }))

  class FakeParams:
    def __init__(self):
      self.values = {
        "ActiveSmallModel": "small-one",
        "ActiveSmallModelName": "Small One",
        "ActiveSmallModelVersion": "v15",
        "ActiveBigModel": "big-one",
        "ActiveBigModelName": "Big One",
        "ActiveBigModelVersion": "v16",
      }

    def get(self, key):
      return self.values.get(key)

    def put(self, key, value):
      self.values[key] = value

  params = FakeParams()
  model_manager.set_runtime_model_params(params, "big-one", "v16")
  assert params.values["DrivingModel"] == "big-one"
  assert params.values["DrivingModelName"] == "Big One"
  model_manager.set_runtime_model_params(params, "small-one", "v15")
  assert params.values["DrivingModel"] == "small-one"
  assert params.values["DrivingModelName"] == "Small One"
  assert params.values["ActiveBigModel"] == "big-one"
  assert params.values["ActiveSmallModel"] == "small-one"


def test_manifest_metadata_classifies_model_lab_candidates_and_accelerator_artifacts(tmp_path, monkeypatch):
  monkeypatch.setattr(model_manager, "MODELS_PATH", tmp_path)
  manager = object.__new__(ModelManager)
  metadata = manager._build_artifact_metadata_map([
    {"id": "legacy-small", "version": "v15"},
    {
      "id": "declared-small",
      "version": "v15",
      "model_size": "small",
      "model_lab_eligible": True,
      "accelerator_artifacts": {
        "chestnut": {
          "artifact_filename": "declared-small-amd.pkl",
          "artifact_size": 123,
          "artifact_sha256": "a" * 64,
          "artifact_chunk_count": 2,
          "execution_device": "AMD",
        },
      },
    },
    {"id": "chestnut", "version": "v16", "uses_external_gpu": True},
  ])
  (tmp_path / model_manager.ARTIFACT_METADATA_CACHE).write_text(json.dumps(metadata))

  assert metadata["legacy-small"]["model_size"] == "small"
  assert metadata["legacy-small"]["model_size_declared"] is False
  assert metadata["legacy-small"]["model_lab_eligible"] is True
  assert metadata["declared-small"]["model_size_declared"] is True
  assert metadata["declared-small"]["accelerator_artifacts"]["chestnut"] == {
    "artifact_format": UNIFIED_ARTIFACT_FORMAT,
    "artifact_filename": "declared-small-amd.pkl",
    "artifact_size": 123,
    "artifact_sha256": "a" * 64,
    "artifact_chunk_count": 2,
    "artifact_url": "",
    "execution_device": "AMD",
  }
  assert metadata["chestnut"]["model_size"] == "chestnut"
  assert metadata["chestnut"]["model_lab_eligible"] is False
  assert model_manager.model_accelerator_artifact_available("declared-small")
  assert not model_manager.model_accelerator_artifact_available("legacy-small")
  assert model_manager.model_accelerator_artifact_path("declared-small") == (
    tmp_path / "declared-small_driving_chestnut_tinygrad.pkl"
  )


def test_model_manager_downloads_precompiled_accelerator_variant_without_compiling(tmp_path, monkeypatch):
  monkeypatch.setattr(model_manager, "MODELS_PATH", tmp_path)
  manager = object.__new__(ModelManager)

  class FakeParams:
    def __init__(self, values=None):
      self.values = values or {}

    def get(self, key):
      return self.values.get(key)

    def get_bool(self, key):
      return bool(self.values.get(key, False))

    def put(self, key, value):
      self.values[key] = value

    def remove(self, key):
      self.values.pop(key, None)

  manager.params = FakeParams({"ModelManifestVersion": "v25"})
  manager.params_memory = FakeParams({model_manager.MODEL_LAB_DOWNLOAD_PARAM: "lat"})
  manager.downloading_model = False
  metadata = manager._build_artifact_metadata_map([{
    "id": "lat",
    "accelerator_artifacts": {
      "chestnut": {
        "artifact_filename": "lat-amd.pkl",
        "artifact_size": 456,
        "execution_device": "AMD",
      },
    },
  }])
  (tmp_path / model_manager.ARTIFACT_METADATA_CACHE).write_text(json.dumps(metadata))
  monkeypatch.setattr(model_manager, "external_gpu_available", lambda: True)
  monkeypatch.setattr(model_manager, "get_resource_urls", lambda: ["https://models.example"])
  monkeypatch.setattr(manager, "_load_artifact_url_map", lambda: {})
  calls = []

  def fake_download(model_key, path, remote_filename, artifact_metadata, artifact_urls, resource_urls):
    calls.append((model_key, path, remote_filename, artifact_metadata, artifact_urls, resource_urls))
    path.write_bytes(b"precompiled-amd")
    return True

  monkeypatch.setattr(manager, "_download_artifact_to_path", fake_download)

  assert manager.download_model_accelerator("lat")
  assert calls[0][0:3] == (
    "lat",
    tmp_path / "lat_driving_chestnut_tinygrad.pkl",
    "lat-amd.pkl",
  )
  assert calls[0][3]["execution_device"] == "AMD"
  assert calls[0][5] == ["https://models.example"]
  assert manager.params_memory.values[model_manager.DOWNLOAD_PROGRESS_PARAM] == "Chestnut artifact downloaded!"
  assert model_manager.MODEL_LAB_DOWNLOAD_PARAM not in manager.params_memory.values


def test_local_gpu_compile_persists_runtime_metadata(tmp_path, monkeypatch):
  models_path = tmp_path / "models"
  compiled_path = tmp_path / "compiled" / "local-large_driving_tinygrad.pkl"
  models_path.mkdir()
  compiled_path.parent.mkdir()
  compiled_path.write_bytes(b"artifact")
  monkeypatch.setattr(model_compiler, "MODELS_PATH", models_path)

  model_compiler.install_local_artifact(compiled_path, "local-large", "v16", external_gpu=True)

  sidecar = json.loads((models_path / "local-large.json").read_text())
  metadata = json.loads((models_path / model_manager.ARTIFACT_METADATA_CACHE).read_text())
  assert sidecar["uses_external_gpu"] is True
  assert metadata["local-large"]["uses_external_gpu"] is True

  monkeypatch.setattr(model_manager, "MODELS_PATH", models_path)
  manager = object.__new__(ModelManager)
  assert manager._discover_local_models()[0]["uses_external_gpu"] is True

  model_compiler.install_local_artifact(compiled_path, "local-large", "v16", external_gpu=False)
  sidecar = json.loads((models_path / "local-large.json").read_text())
  metadata = json.loads((models_path / model_manager.ARTIFACT_METADATA_CACHE).read_text())
  assert sidecar["uses_external_gpu"] is False
  assert metadata["local-large"]["uses_external_gpu"] is False


def test_all_compilation_uses_oob_and_external_gpu_is_opt_in(tmp_path, monkeypatch):
  invocations = []
  monkeypatch.setattr(model_compiler, "build_compile_env", lambda **_: {
    "DEV": "QCOM", "IMAGE": "2", "NOLOCALS": "1", "OPENPILOT_HACKS": "1",
  })
  monkeypatch.setattr(model_compiler.subprocess, "run", lambda command, **kwargs: invocations.append((command, kwargs)))
  monkeypatch.setattr(model_compiler, "wait_for_external_gpu", lambda: None)
  files = {"driving_supercombo": tmp_path / "model.onnx"}

  model_compiler.compile_driving("normal", files, "supercombo", "v15", tmp_path, "policy")
  model_compiler.compile_driving("large", files, "supercombo", "v15", tmp_path, "policy", external_gpu=True)

  normal_command, normal_kwargs = invocations[0]
  external_command, external_kwargs = invocations[1]
  assert "--out-of-band" in normal_command
  assert normal_kwargs["env"]["DEV"] == "QCOM"
  assert normal_kwargs["env"]["IMAGE"] == "2"
  assert "--out-of-band" in external_command
  assert external_kwargs["env"]["DEBUG"] == "1"
  assert external_kwargs["env"]["DEV"] == "USB+AMD:LLVM"
  assert external_kwargs["env"]["WARP_DEV"] == "QCOM"
  assert all(flag not in external_kwargs["env"] for flag in ("IMAGE", "NOLOCALS", "OPENPILOT_HACKS"))


def test_external_gpu_compile_uses_agnos_isolated_cpu(monkeypatch):
  command = ["python3", "compile_modeld.py"]
  monkeypatch.setattr(model_compiler.sys, "platform", "linux")
  monkeypatch.setattr(model_compiler.platform, "machine", lambda: "aarch64")

  assert model_compiler.external_gpu_compile_command(command) == ["taskset", "-c", "7", *command]


def test_external_gpu_compile_does_not_pin_other_platforms(monkeypatch):
  command = ["python3", "compile_modeld.py"]
  monkeypatch.setattr(model_compiler.sys, "platform", "darwin")
  monkeypatch.setattr(model_compiler.platform, "machine", lambda: "arm64")

  assert model_compiler.external_gpu_compile_command(command) is command


def test_compile_clears_only_selected_model_outputs(tmp_path, monkeypatch):
  monkeypatch.setattr(model_compiler, "build_compile_env", lambda **_: {})
  monkeypatch.setattr(model_compiler.subprocess, "run", lambda *args, **kwargs: None)
  (tmp_path / "normal_driving_tinygrad.pkl").write_bytes(b"old")
  (tmp_path / "normal_driving_tinygrad.pkl.p00").write_bytes(b"old")
  (tmp_path / "other_driving_tinygrad.pkl").write_bytes(b"keep")

  model_compiler.compile_driving(
    "normal", {"driving_supercombo": tmp_path / "model.onnx"}, "supercombo", "v15", tmp_path, "policy",
  )

  assert not (tmp_path / "normal_driving_tinygrad.pkl").exists()
  assert not (tmp_path / "normal_driving_tinygrad.pkl.p00").exists()
  assert (tmp_path / "other_driving_tinygrad.pkl").read_bytes() == b"keep"


def test_v23_namespace_mapping_does_not_cascade(tmp_path):
  (tmp_path / "deeprl3_driving_tinygrad.pkl.p00").write_bytes(b"base")
  (tmp_path / "deeprl33_driving_tinygrad.pkl.p00").write_bytes(b"v3")

  reconcile_v23_artifacts.normalize_artifact_names(tmp_path)

  assert (tmp_path / "deeprl33_driving_tinygrad.pkl.p00").read_bytes() == b"base"
  assert (tmp_path / "deeprl333_driving_tinygrad.pkl.p00").read_bytes() == b"v3"


def test_gpu_is_external_gpu_cli_alias(monkeypatch):
  monkeypatch.setattr(sys, "argv", ["models", "--model", "large", "--gpu"])
  args = model_compiler.parse_args()
  assert args.external_gpu


def test_requested_model_id_uses_only_staged_source(tmp_path):
  source = tmp_path / "big_driving_supercombo.onnx"
  source.touch()
  assert model_compiler.resolve_model_files(tmp_path, "lebowski") == {
    "driving_supercombo": source,
  }


def test_regular_fat_onnx_is_parsed_in_place(tmp_path, monkeypatch):
  source = tmp_path / "big_driving_supercombo.onnx"
  source.write_bytes(b"model")
  monkeypatch.setattr(file_chunker, "open_file_chunked", lambda _: (_ for _ in ()).throw(AssertionError("must not copy")))

  assert compile_modeld.read_file_chunked_to_disk(source) == str(source)


def test_chunked_fat_onnx_is_streamed_to_disk(tmp_path, monkeypatch):
  payload = b"fat model" * 1024

  class StreamingOnly(io.BytesIO):
    def read(self, size=-1):
      assert size >= 0, "staging must not materialize the whole ONNX"
      return super().read(size)

  monkeypatch.setattr(file_chunker, "open_file_chunked", lambda _: StreamingOnly(payload))
  source = tmp_path / "big_driving_supercombo.onnx"
  staged = compile_modeld.read_file_chunked_to_disk(source)
  try:
    assert staged == f"{source}.unchunked"
    assert Path(staged).read_bytes() == payload
  finally:
    Path(staged).unlink(missing_ok=True)


def test_onnx_preflight_accepts_graph_without_reading_weights(tmp_path):
  source = tmp_path / "model.onnx"
  source.write_bytes(b"\x08\x09\x3a\x02\x12\x00")

  model_compiler.validate_onnx_source(source)


def test_onnx_preflight_rejects_empty_truncated_and_lfs_sources(tmp_path):
  empty = tmp_path / "empty.onnx"
  empty.touch()
  truncated = tmp_path / "truncated.onnx"
  truncated.write_bytes(b"\x3a\x08bad")
  pointer = tmp_path / "pointer.onnx"
  pointer.write_text("version https://git-lfs.github.com/spec/v1\n")

  for source, message in ((empty, "empty"), (truncated, "truncated"), (pointer, "Git LFS pointer")):
    try:
      model_compiler.validate_onnx_source(source)
    except ValueError as error:
      assert message in str(error)
    else:
      raise AssertionError(f"{source} should have failed validation")


def test_dropbox_urls_are_direct_downloads():
  url = "https://www.dropbox.com/scl/fi/id/model.pkl?rlkey=key&st=value&dl=0"
  normalized = download_functions.normalize_download_url(url)
  assert normalized.count("dl=1") == 1
  assert "dl=0" not in normalized
  assert "rlkey=key" in normalized


def test_download_verification_uses_manifest_size_and_sha(tmp_path, monkeypatch):
  artifact = tmp_path / "model.pkl"
  artifact.write_bytes(b"unified model")
  monkeypatch.setattr(download_functions, "get_remote_file_size", lambda *args, **kwargs: 0)

  assert download_functions.verify_download(
    artifact,
    "https://example.com/model.pkl",
    allow_unknown_size=True,
    expected_size=artifact.stat().st_size,
    expected_sha256="02f64c1311bd6392462fa9c7c929b002057f261fdcef2050554c08694e7d2120",
  )
  assert not download_functions.verify_download(
    artifact,
    "https://example.com/model.pkl",
    allow_unknown_size=True,
    expected_size=artifact.stat().st_size + 1,
  )


def test_lfs_pointer_is_not_accepted_as_model(tmp_path, monkeypatch):
  artifact = tmp_path / "model.pkl"
  artifact.write_text(
    "version https://git-lfs.github.com/spec/v1\n"
    f"oid sha256:{'0' * 64}\n"
    "size 123456789\n",
  )
  monkeypatch.setattr(download_functions, "get_remote_file_size", lambda *args, **kwargs: artifact.stat().st_size)
  assert not download_functions.verify_download(artifact, "https://example.com/model.pkl")


def test_multipart_download_is_atomic_and_checksum_verified(tmp_path, monkeypatch):
  payload = b"first part" + b"second part"
  expected_sha = hashlib.sha256(payload).hexdigest()
  part_payloads = {
    "https://example.com/model.pkl.p00": b"first part",
    "https://example.com/model.pkl.p01": b"second part",
  }

  class FakeResponse:
    def __init__(self, data):
      self.data = data
      self.text = data.decode()

    def __enter__(self):
      return self

    def __exit__(self, *args):
      pass

    def raise_for_status(self):
      pass

    def iter_content(self, chunk_size):
      del chunk_size
      yield self.data

  def fake_get(url, **kwargs):
    del kwargs
    if url.endswith(".sha256"):
      return FakeResponse(f"{expected_sha}  model.pkl\n".encode())
    return FakeResponse(part_payloads[url])

  def fake_size(url, **kwargs):
    del kwargs
    return len(part_payloads.get(url, b""))

  class FakeParams:
    def get_bool(self, key):
      del key
      return False

    def put(self, key, value):
      del key, value

  monkeypatch.setattr(download_functions.requests, "get", fake_get)
  monkeypatch.setattr(download_functions, "get_remote_file_size", fake_size)
  destination = tmp_path / "model.pkl"

  assert download_functions.download_multipart_file(
    "cancel", destination, "progress", "https://example.com/model.pkl", "download", FakeParams(),
  )
  assert destination.read_bytes() == payload


def test_multipart_checksum_failure_leaves_no_model(tmp_path, monkeypatch):
  class FakeResponse:
    text = f"{'0' * 64}  model.pkl"

    def __enter__(self):
      return self

    def __exit__(self, *args):
      pass

    def raise_for_status(self):
      pass

    def iter_content(self, chunk_size):
      del chunk_size
      yield b"corrupt"

  monkeypatch.setattr(download_functions.requests, "get", lambda *args, **kwargs: FakeResponse())
  monkeypatch.setattr(
    download_functions,
    "get_remote_file_size",
    lambda url, **kwargs: len(b"corrupt") if url.endswith(".p00") else 0,
  )

  class FakeParams:
    def get_bool(self, key):
      del key
      return False

    def put(self, key, value):
      del key, value

  destination = tmp_path / "model.pkl"
  assert not download_functions.download_multipart_file(
    "cancel", destination, "progress", "https://example.com/model.pkl", "download", FakeParams(),
  )
  assert not destination.exists()


def test_native_chunk_download_is_atomic_and_checksum_verified(tmp_path, monkeypatch):
  chunks = [b"first native chunk", b"second native chunk"]
  payload = b"".join(chunks)
  expected_sha = hashlib.sha256(payload).hexdigest()

  class FakeResponse:
    def __init__(self, data):
      self.data = data

    def __enter__(self):
      return self

    def __exit__(self, *args):
      pass

    def raise_for_status(self):
      pass

    def iter_content(self, chunk_size):
      del chunk_size
      yield self.data

  def fake_get(url, **kwargs):
    del kwargs
    index = 0 if ".chunk01of02" in url else 1
    return FakeResponse(chunks[index])

  def fake_size(url, **kwargs):
    del kwargs
    return len(chunks[0 if ".chunk01of02" in url else 1])

  class FakeParams:
    def get_bool(self, key):
      del key
      return False

    def put(self, key, value):
      del key, value

  monkeypatch.setattr(download_functions, "get_remote_text", lambda *args, **kwargs: "2")
  monkeypatch.setattr(download_functions.requests, "get", fake_get)
  monkeypatch.setattr(download_functions, "get_remote_file_size", fake_size)
  destination = tmp_path / "model.pkl"
  destination.write_bytes(b"old model remains until validation succeeds")

  assert download_functions.download_chunked_file(
    "cancel", destination, "progress", "https://example.com/model.pkl", FakeParams(),
    expected_size=len(payload), expected_sha256=expected_sha, expected_chunk_count=2,
  )
  assert not destination.exists()
  assert (tmp_path / "model.pkl.chunkmanifest").read_text() == "2"
  assert b"".join((tmp_path / f"model.pkl.chunk{i:02d}of02").read_bytes() for i in (1, 2)) == payload


def test_oversized_artifact_split_round_trip(tmp_path):
  artifact = tmp_path / "model.pkl"
  artifact.write_bytes(b"multipart artifact")

  outputs = split_oversized_artifact(artifact, chunk_size=10, force=True)
  chunk_paths = [path for path in outputs if ".chunk" in path.name and not path.name.endswith(".chunkmanifest")]
  assert len(chunk_paths) == 2
  assert b"".join(path.read_bytes() for path in chunk_paths) == artifact.read_bytes()
  assert (tmp_path / "model.pkl.chunkmanifest").read_text() == "2"
