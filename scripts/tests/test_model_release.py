from __future__ import annotations

import json
from pathlib import Path

from scripts import model_release
from scripts.model_release import parse_lfs_pointer, parse_pasted_release, runtime_file, update_manifest


RELEASE_TEXT = """
**BRANCH UPDATED — BIG**
[remove-avgpool](https://github.com/commaai/openpilot/pull/38681) #38681 [big] (Branch v5)
**Changed Files**
[big_driving_supercombo](https://github.com/commaai/openpilot/blob/remove-avgpool/openpilot/selfdrive/modeld/models/big_driving_supercombo.onnx)
**Recent Commits [f877]**
[f877d7a0ccc3cce943c76e285214c020cd65c899](https://github.com/commaai/openpilot/commit/f877d7a0ccc3cce943c76e285214c020cd65c899)
[faster compile](https://github.com/commaai/openpilot/commit/83a461eb4f0cb5737132c24b7a5ad5de46fc0fbb)
**Next Model Version [big]**
Model v4

Bmrlnap v4 (August 30, 2026) f877
"""


def test_parse_release_block():
  info = parse_pasted_release(RELEASE_TEXT, None, "v16")
  assert info.model_id == "bmrlnapv4"
  assert info.display_name == "Bmrlnap v4"
  assert info.release_date == "2026-08-30"
  assert info.branch == "remove-avgpool"
  assert info.source_ref == "f877d7a0ccc3cce943c76e285214c020cd65c899"
  assert info.source_path.endswith("big_driving_supercombo.onnx")
  assert info.input_format == "supercombo"
  assert info.uses_external_gpu
  assert info.commits == [
    "f877d7a0ccc3cce943c76e285214c020cd65c899",
    "83a461eb4f0cb5737132c24b7a5ad5de46fc0fbb",
  ]


def test_lfs_pointer_parser():
  pointer = (
    b"version https://git-lfs.github.com/spec/v1\n"
    b"oid sha256:" + b"a" * 64 + b"\n"
    b"size 123\n"
  )
  assert parse_lfs_pointer(pointer) == ("a" * 64, 123)


def test_sha_only_resolves_commit_metadata(monkeypatch):
  commit = "f877d7a0ccc3cce943c76e285214c020cd65c899"
  payloads = {
    f"https://api.github.com/repos/commaai/openpilot/commits/{commit}": {
      "commit": {"committer": {"date": "2026-08-31T00:41:06Z"}},
      "files": [{"filename": "openpilot/selfdrive/modeld/models/big_driving_supercombo.onnx"}],
    },
    f"https://api.github.com/repos/commaai/openpilot/commits/{commit}/pulls": [
      {"title": "BMRLNAP", "head": {"sha": commit, "ref": "remove-avgpool"}},
    ],
  }

  monkeypatch.setattr(model_release, "get_json_value", lambda url: payloads[url])
  info = parse_pasted_release(commit, None, "v16")

  assert info.model_id == "bmrlnap"
  assert info.display_name == "BMRLNAP"
  assert info.release_date == "2026-08-30"
  assert info.branch == "remove-avgpool"
  assert info.source_ref == commit
  assert info.source_path.endswith("big_driving_supercombo.onnx")
  assert info.uses_external_gpu


def test_runtime_scan_excludes_model_weights_but_flags_runtime_code():
  assert not runtime_file("openpilot/selfdrive/modeld/models/big_driving_supercombo.onnx")
  assert runtime_file("openpilot/selfdrive/modeld/compile_modeld.py")
  assert runtime_file("tinygrad/engine/jit.py")
  assert not runtime_file("README.md")


def test_update_manifest_replaces_one_entry(tmp_path: Path):
  manifest = tmp_path / "model_names_v25.json"
  manifest.write_text(json.dumps({"models": [{"id": "old"}]}) + "\n")
  info = parse_pasted_release(RELEASE_TEXT, "bmrlnapv4", "v16")
  path = update_manifest(
    tmp_path,
    info,
    {"size": 123, "sha256": "a" * 64},
    "v25",
  )
  payload = json.loads(path.read_text())
  assert len(payload["models"]) == 2
  entry = payload["models"][1]
  assert entry["id"] == "bmrlnapv4"
  assert entry["artifact_size"] == 123
  assert entry["uses_external_gpu"]
