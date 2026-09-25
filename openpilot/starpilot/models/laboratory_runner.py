from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from openpilot.cereal import log
from openpilot.starpilot.models.laboratory import validate_configuration
from openpilot.starpilot.models.laboratory_outputs import compose_model_outputs, hybrid_action_values
from openpilot.starpilot.models.manager import ROOT, artifact_entry, artifact_path, catalog
from openpilot.starpilot.models.receipt import PreparedArtifact
from openpilot.starpilot.models.runner import CatalogModelState, action_from_outputs, load_verified_model


@dataclass(frozen=True)
class LaboratoryRole:
  model_id: str
  behavior_version: str
  artifact: PreparedArtifact


@dataclass(frozen=True)
class LaboratoryFrame:
  outputs: dict[str, np.ndarray]
  action: log.ModelDataV2.Action


class LaboratoryPair:
  def __init__(self, lateral: CatalogModelState, longitudinal: CatalogModelState,
               lateral_artifact: PreparedArtifact, longitudinal_artifact: PreparedArtifact):
    if lateral is longitudinal or lateral.model_id == longitudinal.model_id:
      raise ValueError("Model Laboratory requires two distinct models")
    if not lateral.chestnut or not longitudinal.chestnut:
      raise ValueError("Model Laboratory requires two AMD variants")
    if lateral.camera_warp_descriptor is None or lateral.camera_warp_descriptor != longitudinal.camera_warp_descriptor:
      raise ValueError("Model Laboratory requires compatible policy-history camera warps")
    self.lateral = lateral
    self.longitudinal = longitudinal
    self.lateral_role = LaboratoryRole(lateral.model_id, lateral.behavior_version, lateral_artifact)
    self.longitudinal_role = LaboratoryRole(longitudinal.model_id, longitudinal.behavior_version, longitudinal_artifact)
    self.failed = False

  def run_frame(self, bufs: dict, transforms: dict[str, np.ndarray], inputs: dict[str, np.ndarray],
                previous: log.ModelDataV2.Action, lat_action_t: float, long_action_t: float, v_ego: float,
                lat_smooth_seconds: float = 0.0, long_smooth_seconds: float = 0.3,
                after_enqueue: Callable[[], None] | None = None) -> LaboratoryFrame:
    """Run both roles before releasing the camera frame; any failure requires fallback."""
    if self.failed:
      raise RuntimeError("Model Laboratory pair failed; load a fallback before continuing")
    try:
      lateral_output = self.lateral.run(bufs, transforms, inputs)
      shared_warp = self.lateral.last_warp
      if shared_warp is None:
        raise ValueError("Model Laboratory camera warp unavailable")
      longitudinal_output = self.longitudinal.run(bufs, transforms, inputs, after_enqueue, shared_warp=shared_warp)
      actions = [action_from_outputs(output, model.behavior_version, previous, lat_action_t, long_action_t, v_ego,
                                     lat_smooth_seconds, long_smooth_seconds)
                 for model, output in ((self.lateral, lateral_output), (self.longitudinal, longitudinal_output))]
      action = log.ModelDataV2.Action(**hybrid_action_values(*actions))
      return LaboratoryFrame(compose_model_outputs(lateral_output, longitudinal_output), action)
    except Exception:
      self.failed = True
      self.lateral.last_warp = self.longitudinal.last_warp = None
      raise


def load_laboratory_pair(cam_w: int, cam_h: int, config: dict, *, root: Path = ROOT) -> LaboratoryPair:
  validate_configuration(config)
  if not config["enabled"]:
    raise ValueError("Model Laboratory is disabled")
  entries = catalog(root)
  requests = []
  for role in ("lateralModel", "longitudinalModel"):
    mid = config[role]
    artifact = artifact_entry(mid, entries, "amd")
    if "artifact_sha256" not in artifact:
      raise ValueError("Model Laboratory requires published AMD variants for both models")
    requests.append((mid, entries[mid]["version"], artifact["artifact_sha256"]))
  loaded = [load_verified_model(cam_w, cam_h, artifact_path(mid, root, "amd"), version, True, mid, digest, root=root)
            for mid, version, digest in requests]
  return LaboratoryPair(loaded[0][0], loaded[1][0], loaded[0][1], loaded[1][1])
