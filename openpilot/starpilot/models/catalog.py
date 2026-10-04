"""Reviewed local driving-model catalog. This module never loads model artifacts."""

from dataclasses import dataclass
import json
from pathlib import Path


BUNDLED_CURRENT = "bundled-current"
DEFAULT_SMALL = "rdf43"
DEFAULT_SMALL_SHA256 = "e23f65b3790a2092348024603966717506c2ad1fae10b4312bdfe1f2b932df61"
DEFAULT_SMALL_SIZE = 125895084
GENERATION = "v26"
COMPILER_REVISION = "9d0446a4ba8a532c8b674fb6ad795af015cd9dcf"
ARTIFACT_ABI = "tinygrad_single_v1_arena"
CATALOG_PATH = Path(__file__).with_name("catalog-v26.json")


@dataclass(frozen=True)
class ModelEntry:
  model_id: str
  name: str
  source_sha256: str
  source_path: str
  compiler_revision: str
  artifact_abi: str
  selectable: bool
  version: str = "current"
  uses_external_gpu: bool = False


BUNDLED = (
  ModelEntry(
    model_id=BUNDLED_CURRENT,
    name="Regret Driven Framework V4",
    source_sha256=DEFAULT_SMALL_SHA256,
    source_path="openpilot/selfdrive/modeld/models/rdf43_driving_tinygrad.pkl",
    compiler_revision="9d0446a4ba8a532c8b674fb6ad795af015cd9dcf",
    artifact_abi=ARTIFACT_ABI,
    selectable=True,
    version="v15",
  ),
)

CATALOG = BUNDLED + tuple(ModelEntry(
  model_id=m["id"], name=m["name"],
  source_sha256=DEFAULT_SMALL_SHA256 if m["id"] == DEFAULT_SMALL else "",
  source_path="openpilot/selfdrive/modeld/models/rdf43_driving_tinygrad.pkl" if m["id"] == DEFAULT_SMALL else "",
  compiler_revision=COMPILER_REVISION, artifact_abi=ARTIFACT_ABI, selectable=True,
  version=m["version"], uses_external_gpu=bool(m.get("uses_external_gpu", False)),
) for m in json.loads(CATALOG_PATH.read_text())["models"])

BY_ID = {entry.model_id: entry for entry in CATALOG}


def resolve_selection(requested_id: str | None) -> ModelEntry:
  """Resolve a saved request; absence means the bundled model, never an unknown ID."""
  model_id = DEFAULT_SMALL if requested_id in (None, BUNDLED_CURRENT) else requested_id
  if not isinstance(model_id, str) or model_id not in BY_ID or not BY_ID[model_id].selectable:
    raise ValueError("unqualified driving-model selection")
  return BY_ID[model_id]
