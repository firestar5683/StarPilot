from pathlib import Path

from openpilot.starpilot.models.catalog import BY_ID, BUNDLED_CURRENT, GENERATION
from openpilot.starpilot.models.manager import (
  ModelError, ModelManager, artifact_entry, artifact_path, atomic_json, catalog, read_json, state_lock, verified_artifact,
)


def configuration(root: Path) -> dict:
  default = {"enabled": False, "lateralModel": "", "longitudinalModel": ""}
  try:
    saved = read_json(root / "laboratory.json", 4096)
    validate_configuration(saved)
    return saved
  except (OSError, ValueError, TypeError):
    return default


def validate_configuration(value: dict) -> None:
  if (not isinstance(value, dict) or set(value) != {"enabled", "lateralModel", "longitudinalModel"} or
      type(value["enabled"]) is not bool):
    raise ModelError("Invalid laboratory configuration")
  for key in ("lateralModel", "longitudinalModel"):
    mid = value[key]
    if not isinstance(mid, str) or (mid and (mid not in BY_ID or mid == BUNDLED_CURRENT or BY_ID[mid].uses_external_gpu)):
      raise ModelError("Choose small models for the laboratory pair")
  if value["enabled"] and (not value["lateralModel"] or not value["longitudinalModel"] or
                           value["lateralModel"] == value["longitudinalModel"]):
    raise ModelError("Choose two different small models")


class ModelLaboratory:
  def __init__(self, manager: ModelManager, *, runtime_supported: bool = False):
    self.manager = manager
    self.runtime_supported = runtime_supported

  @property
  def runtime_unavailable_reason(self) -> str:
    return "" if self.runtime_supported else "Pair inference is not available in this build yet."

  def snapshot(self) -> dict:
    owner = self.manager
    with owner.lock:
      entries = catalog(owner.root)
      config = configuration(owner.root)
      parked, gpu = owner.parked(), owner.gpu_present()
      job = owner._job_status()
      models = []
      for mid, row in entries.items():
        small = not BY_ID[mid].uses_external_gpu
        eligible = small and row.get("model_lab_eligible") is True
        artifact = artifact_entry(mid, entries, "amd") if eligible else {}
        published = "artifact_sha256" in artifact
        installed, checking = owner._snapshot_installed(mid, row, "amd") if published else (False, False)
        if not small:
          state, reason = "unsupported", "Big models cannot be combined in this build."
        elif not eligible:
          state, reason = "unsupported", "This model is not available for combining."
        elif not published:
          state, reason = "unpublished", "A Chestnut version for combining has not been published for this model."
        elif checking:
          state, reason = "checking", "Checking the downloaded Chestnut version."
        elif not installed:
          state, reason = "missing", "Download the Chestnut version to prepare this model for combining."
        elif not self.runtime_supported:
          state, reason = "runtime-unavailable", "Download verified. Running two models together is unavailable in this build."
        elif not gpu:
          state, reason = "gpu-unavailable", "Download verified. Connect a ready Chestnut to use it."
        else:
          state, reason = "installed", "Download verified. Choose another compatible model to form a pair."
        models.append({"value": mid, "label": row["name"], "version": row["version"], "series": row.get("series", ""),
                       "small": small, "modelSize": "small" if small else "big", "modelLabEligible": eligible,
                       "modelLabArtifactAvailable": published, "modelLabArtifactInstalled": installed, "checking": checking,
                       "modelLabStatus": state, "modelLabReason": reason,
                       "artifactSize": artifact.get("artifact_size", 0)})
      return {"schemaVersion": 1, "chestnutReady": gpu, "isOnroad": not parked, "configuration": config,
              "configurationError": self.runtime_unavailable_reason if config["enabled"] else "",
              "runtimeSupported": self.runtime_supported, "runtimeUnavailableReason": self.runtime_unavailable_reason,
              "runtime": {"requested": config["enabled"], "active": False, "lateralModel": "", "longitudinalModel": "",
                          "error": "", "health": "unavailable"},
              "download": {"model": job.get("model", ""), "progress": job.get("progress", ""),
                           "downloading": job["downloading"], "jobId": job.get("jobId", ""),
                           "variant": job.get("variant", "standard")},
              "summary": {"catalog": len(models), "eligible": sum(row["modelLabEligible"] is True for row in models),
                          "ready": sum(row["modelLabArtifactInstalled"] is True for row in models),
                          "published": sum(row["modelLabArtifactAvailable"] is True for row in models),
                          "declaredSize": sum(int(row["artifactSize"]) for row in models)},
              "models": models, "manifest": {"version": GENERATION},
              "capabilities": {"configure": parked, "download": parked,
                               "delete": parked, "cancel": True, "refresh": parked}}

  def action(self, action: str, payload: dict) -> dict:
    owner = self.manager
    if not isinstance(payload, dict):
      raise ModelError("Invalid laboratory request")
    with owner.lock:
      owner._require_parked()
      if action == "download":
        if set(payload) != {"model"} or not isinstance(payload["model"], str):
          raise ModelError("Unknown laboratory model")
        return owner.action("download", {"model": payload["model"], "variant": "amd", "allowGpuWithoutGpu": True})
      if action not in ("configure", "delete"):
        raise ModelError("Unknown laboratory action")
      with state_lock(owner.root):
        owner._require_parked()
        if owner._job_busy():
          raise ModelError("Wait for the model download to finish")
        if action == "configure":
          validate_configuration(payload)
          if payload["enabled"]:
            if not self.runtime_supported:
              raise ModelError(self.runtime_unavailable_reason)
            if not owner.gpu_present():
              raise ModelError("Connect a firmware-ready Chestnut to enable this pair")
            entries = catalog(owner.root)
            for role in ("lateralModel", "longitudinalModel"):
              if verified_artifact(payload[role], entries, owner.root, "amd") is None:
                raise ModelError("Download and verify both eGPU variants first")
            owner._require_parked()
          atomic_json(owner.root / "laboratory.json", payload)
          message = "Model Laboratory configuration saved"
        else:
          if set(payload) != {"model"} or not isinstance(payload["model"], str):
            raise ModelError("Unknown laboratory model")
          mid = payload["model"]
          destination = artifact_path(mid, owner.root, "amd")
          config = configuration(owner.root)
          if config["enabled"] and mid in (config["lateralModel"], config["longitudinalModel"]):
            raise ModelError("Disable the laboratory pair before deleting either eGPU variant")
          destination.unlink(missing_ok=True)
          owner.checked.pop(f"{mid}:amd", None)
          message = "eGPU variant deleted"
      return {**self.snapshot(), "message": message}
