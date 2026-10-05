"""Select reviewed fork expectations without changing replay comparisons."""
from dataclasses import fields
import hashlib
import inspect
import json
from pathlib import Path

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "openpilot/selfdrive/test/process_replay/refs/starpilot"


def _canonical(value):
  if value is None or isinstance(value, (str, bool, int, float)):
    return value
  if isinstance(value, (list, tuple)):
    return [_canonical(v) for v in value]
  if isinstance(value, dict):
    return {k: _canonical(v) for k, v in sorted(value.items())}
  if callable(value):
    if inspect.isfunction(value):
      return {"callable": value.__module__ + "." + value.__qualname__}
    return {"callable": type(value).__module__ + "." + type(value).__qualname__, "parameters": _canonical(vars(value))}
  raise TypeError(f"Unsupported replay configuration value: {type(value).__name__}")


def config_signature(cfg):
  normalized = {field.name: _canonical(getattr(cfg, field.name)) for field in fields(cfg)}
  return hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def reviewed_reference(segment, cfg, raw_input, *, official_commit, artifact_commit, reference_dir=REFERENCE_DIR):
  manifest = json.loads((reference_dir / "manifest.json").read_text())
  if (manifest.get("version") != 1 or manifest.get("official_baseline_commit") != official_commit
      or manifest.get("official_artifact_commit") != artifact_commit):
    raise ValueError("Reviewed replay manifest baseline changed")
  records = [record for record in manifest["references"] if record["segment"] == segment and record["process"] == cfg.proc_name]
  if not records:
    return None
  if len(records) != 1:
    raise ValueError("Duplicate reviewed replay reference")
  record = records[0]
  if record["official_baseline_commit"] != official_commit or record["official_artifact_commit"] != artifact_commit:
    raise ValueError("Reviewed replay reference baseline changed")
  if hashlib.sha256(raw_input).hexdigest() != record["input_sha256"] or len(raw_input) != record["input_bytes"]:
    raise ValueError("Reviewed replay input changed")
  if config_signature(cfg) != record["config_sha256"]:
    raise ValueError("Reviewed replay process configuration changed")
  filename = record["file"]
  if Path(filename).name != filename:
    raise ValueError("Reviewed reference must be a local filename")
  path = reference_dir / filename
  raw = path.read_bytes()
  if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
    raise ValueError("Reviewed replay reference changed")
  return str(path)
