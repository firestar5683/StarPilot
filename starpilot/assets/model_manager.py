#!/usr/bin/env python3
import json
import random
import re
import urllib.request

from pathlib import Path
from urllib.parse import quote

from openpilot.starpilot.assets.download_functions import (
  delete_chunked_artifact,
  download_chunked_file,
  download_file,
  download_multipart_file,
  get_resource_urls,
  handle_error,
  handle_request_error,
  verify_download,
)
from openpilot.starpilot.common.model_versions import (
  UNIFIED_ARTIFACT_FORMAT,
  driving_artifact_filename,
  is_supported_artifact_format,
)
from openpilot.starpilot.common.model_lab import load_model_lab_config
from openpilot.starpilot.common.starpilot_utilities import delete_file
from openpilot.starpilot.common.starpilot_variables import MODELS_PATH
from openpilot.common.file_chunker import file_chunked_exists, get_existing_chunks, get_manifest_path
from openpilot.system.hardware.usb import chestnut_firmware_ready

MANIFEST_CANDIDATES = ("v25",)
MODEL_NAMESPACE_SUFFIX = "3"
DEFAULT_MODEL_KEY = "rdf43"
ACTIVE_BIG_MODEL_PARAM = "ActiveBigModel"
ACTIVE_BIG_MODEL_NAME_PARAM = "ActiveBigModelName"
ACTIVE_BIG_MODEL_VERSION_PARAM = "ActiveBigModelVersion"
ACTIVE_SMALL_MODEL_PARAM = "ActiveSmallModel"
ACTIVE_SMALL_MODEL_NAME_PARAM = "ActiveSmallModelName"
ACTIVE_SMALL_MODEL_VERSION_PARAM = "ActiveSmallModelVersion"
MODEL_PROFILE_PARAMS = {
  "big": (ACTIVE_BIG_MODEL_PARAM, ACTIVE_BIG_MODEL_NAME_PARAM, ACTIVE_BIG_MODEL_VERSION_PARAM),
  "small": (ACTIVE_SMALL_MODEL_PARAM, ACTIVE_SMALL_MODEL_NAME_PARAM, ACTIVE_SMALL_MODEL_VERSION_PARAM),
}
LOCAL_MODEL_PREFIX = "local-"
LOCAL_MODEL_SERIES = "Local Series"
ARTIFACT_URLS_CACHE = ".model_artifact_urls.json"
ARTIFACT_METADATA_CACHE = ".model_artifacts.json"
MODEL_KEY_CANONICAL_MAP = {
  "sc": "sc2",
  "napv1": "remove-avgpoolv1",
  "napv2": "remove-avgpoolv2",
  "napv3": "remove-avgpoolv3",
  "napv4": "remove-avgpoolv4",
  # The original bundled RDF key remains valid after the bundled default moves
  # to the v23 RDF V4 artifact.
  "rdf": DEFAULT_MODEL_KEY,
}
LEGACY_DRIVING_PREFIXES = (
  "driving_",
)

CANCEL_DOWNLOAD_PARAM = "CancelModelDownload"
DOWNLOAD_PROGRESS_PARAM = "ModelDownloadProgress"
MODEL_DOWNLOAD_PARAM = "ModelToDownload"
MODEL_DOWNLOAD_ALL_PARAM = "DownloadAllModels"
MODEL_LAB_DOWNLOAD_PARAM = "ModelLabModelToDownload"
ALLOW_GPU_DOWNLOAD_WITHOUT_GPU_PARAM = "AllowGpuModelDownloadWithoutGpu"
UPDATE_TINYGRAD_PARAM = "UpdateTinygrad"
MODEL_LAB_ACCELERATOR = "chestnut"
MODEL_LAB_EXECUTION_DEVICE = "AMD"


def _clean_model_name(name: str) -> str:
  return re.sub(r"[🗺️👀📡]", "", str(name or "")).strip()


def canonical_model_key(model_key: str) -> str:
  key = (model_key or "").strip()
  return MODEL_KEY_CANONICAL_MAP.get(key, key)


def is_builtin_model_key(model_key: str) -> bool:
  return canonical_model_key(model_key) == DEFAULT_MODEL_KEY


def is_local_model_key(model_key: str) -> bool:
  """Hand-installed models live outside the manifest and are never downloaded or pruned."""
  return canonical_model_key(model_key).startswith(LOCAL_MODEL_PREFIX)


def is_driving_artifact_file(filename: str) -> bool:
  """Match both namespaced unified artifacts and pre-v23 split driving files."""
  return "_driving_" in filename or filename.startswith(LEGACY_DRIVING_PREFIXES)


def model_key_aliases(model_key: str) -> list[str]:
  canonical_key = canonical_model_key(model_key)
  aliases = [canonical_key]

  for alias, canonical in MODEL_KEY_CANONICAL_MAP.items():
    if canonical == canonical_key:
      aliases.append(alias)

  if model_key.endswith("_default"):
    aliases.append(model_key[:-8])

  if model_key and not model_key.endswith("2"):
    aliases.append(f"{model_key}2")

  return [alias for alias in dict.fromkeys(alias for alias in aliases if alias)]


def load_model_artifact_metadata(model_key: str) -> dict:
  try:
    payload = json.loads((MODELS_PATH / ARTIFACT_METADATA_CACHE).read_text())
    metadata = payload.get(canonical_model_key(model_key), {}) if isinstance(payload, dict) else {}
    return metadata if isinstance(metadata, dict) else {}
  except (OSError, ValueError, TypeError):
    return {}


def model_uses_external_gpu(model_key: str) -> bool:
  return bool(load_model_artifact_metadata(model_key).get("uses_external_gpu", False))


def _params_text(params, key: str) -> str:
  try:
    value = params.get(key)
  except Exception:
    return ""
  if value is None:
    return ""
  if isinstance(value, bytes):
    return value.decode("utf-8", errors="ignore").strip()
  return str(value).strip()


def _catalog_model_details(params, model_key: str) -> tuple[str, str]:
  canonical_key = canonical_model_key(model_key)
  models = [canonical_model_key(entry) for entry in _params_text(params, "AvailableModels").split(",")]
  names = [entry.strip() for entry in _params_text(params, "AvailableModelNames").split(",")]
  versions = [entry.strip() for entry in _params_text(params, "ModelVersions").split(",")]
  try:
    index = models.index(canonical_key)
  except ValueError:
    return "", ""
  name = names[index] if index < len(names) else ""
  version = versions[index] if index < len(versions) else ""
  return name, version


def get_model_profile(params, profile: str) -> tuple[str, str, str]:
  if profile not in MODEL_PROFILE_PARAMS:
    raise ValueError(f"Unknown model profile: {profile}")

  key_param, name_param, version_param = MODEL_PROFILE_PARAMS[profile]
  model_key = canonical_model_key(_params_text(params, key_param))
  requires_gpu = profile == "big"
  if model_key and model_uses_external_gpu(model_key) != requires_gpu:
    model_key = ""

  if not model_key:
    legacy_key = canonical_model_key(_params_text(params, "DrivingModel") or _params_text(params, "Model"))
    if legacy_key and model_uses_external_gpu(legacy_key) == requires_gpu:
      model_key = legacy_key

  if not model_key and profile == "small":
    model_key = DEFAULT_MODEL_KEY
  if not model_key:
    return "", "", ""

  stored_key = canonical_model_key(_params_text(params, key_param))
  model_name = _params_text(params, name_param) if stored_key == model_key else ""
  model_version = _params_text(params, version_param) if stored_key == model_key else ""
  if not model_name and canonical_model_key(_params_text(params, "DrivingModel") or _params_text(params, "Model")) == model_key:
    model_name = _params_text(params, "DrivingModelName")
  if not model_version and canonical_model_key(_params_text(params, "DrivingModel") or _params_text(params, "Model")) == model_key:
    model_version = _params_text(params, "DrivingModelVersion") or _params_text(params, "ModelVersion")

  catalog_name, catalog_version = _catalog_model_details(params, model_key)
  model_name = catalog_name or model_name
  model_version = catalog_version or model_version
  if is_builtin_model_key(model_key):
    model_name = model_name or "Regret Driven Framework V4"
    model_version = model_version or "v15"
  return model_key, model_name, model_version


def set_model_profile(params, profile: str, model_key: str, model_name: str = "", model_version: str = "") -> None:
  if profile not in MODEL_PROFILE_PARAMS:
    raise ValueError(f"Unknown model profile: {profile}")

  canonical_key = canonical_model_key(model_key)
  if not canonical_key:
    raise ValueError("Model profile cannot be empty")
  if model_uses_external_gpu(canonical_key) != (profile == "big"):
    raise ValueError(f"Model {canonical_key} is not a {profile} model")

  catalog_name, catalog_version = _catalog_model_details(params, canonical_key)
  key_param, name_param, version_param = MODEL_PROFILE_PARAMS[profile]
  params.put(key_param, canonical_key)
  params.put(name_param, model_name or catalog_name or canonical_key)
  params.put(version_param, model_version or catalog_version or ("v15" if is_builtin_model_key(canonical_key) else ""))


def set_runtime_model_params(params, model_key: str, model_version: str = "") -> None:
  canonical_key = canonical_model_key(model_key) or DEFAULT_MODEL_KEY
  profile = "big" if model_uses_external_gpu(canonical_key) else "small"
  profile_key, profile_name, profile_version = get_model_profile(params, profile)
  catalog_name, catalog_version = _catalog_model_details(params, canonical_key)
  model_name = profile_name if profile_key == canonical_key else catalog_name
  resolved_version = model_version or (profile_version if profile_key == canonical_key else catalog_version)
  if is_builtin_model_key(canonical_key):
    model_name = model_name or "Regret Driven Framework V4"
    resolved_version = resolved_version or "v15"

  params.put("Model", canonical_key)
  params.put("DrivingModel", canonical_key)
  params.put("DrivingModelName", model_name or canonical_key)
  if resolved_version:
    params.put("ModelVersion", resolved_version)
    params.put("DrivingModelVersion", resolved_version)


def model_accelerator_artifact_metadata(model_key: str, accelerator: str = MODEL_LAB_ACCELERATOR) -> dict:
  metadata = load_model_artifact_metadata(model_key)
  artifacts = metadata.get("accelerator_artifacts", {})
  if not isinstance(artifacts, dict):
    return {}
  artifact = artifacts.get(str(accelerator or "").strip().lower(), {})
  return artifact if isinstance(artifact, dict) else {}


def model_accelerator_artifact_filename(model_key: str, accelerator: str = MODEL_LAB_ACCELERATOR) -> str:
  model_key = canonical_model_key(model_key)
  accelerator = str(accelerator or "").strip().lower()
  return f"{model_key}_driving_{accelerator}_tinygrad.pkl"


def model_accelerator_artifact_path(model_key: str, accelerator: str = MODEL_LAB_ACCELERATOR) -> Path:
  return MODELS_PATH / model_accelerator_artifact_filename(model_key, accelerator)


def model_accelerator_artifact_available(model_key: str, accelerator: str = MODEL_LAB_ACCELERATOR) -> bool:
  artifact = model_accelerator_artifact_metadata(model_key, accelerator)
  execution_device = str(artifact.get("execution_device") or artifact.get("device") or "").strip().upper()
  artifact_format = str(artifact.get("artifact_format") or UNIFIED_ARTIFACT_FORMAT).strip()
  return bool(artifact) and execution_device == MODEL_LAB_EXECUTION_DEVICE and is_supported_artifact_format(artifact_format)


def model_accelerator_artifact_installed(model_key: str, accelerator: str = MODEL_LAB_ACCELERATOR) -> bool:
  return model_accelerator_artifact_available(model_key, accelerator) and file_chunked_exists(
    model_accelerator_artifact_path(model_key, accelerator)
  )


def external_gpu_available() -> bool:
  """Return whether the supported external GPU link is ready for modeld."""
  try:
    return bool(chestnut_firmware_ready())
  except Exception:
    return False


class ModelManager:
  def __init__(self, params, params_memory, boot_run=False):
    self.params = params
    self.params_memory = params_memory
    self.downloading_model = False

    self.available_models: list[str] = []
    self.model_versions: list[str] = []
    self.model_series: list[str] = []
    self.available_model_names: list[str] = []
    self.artifact_formats: list[str] = []

    self._load_catalog_from_params()

    self._ensure_model_params()
    self._ensure_model_profiles()
    if boot_run:
      self._sync_selected_model_version()

  @staticmethod
  def _canonical_model_key(model_key: str) -> str:
    return canonical_model_key(model_key)

  def _param_text(self, key: str) -> str:
    raw = self.params.get(key)
    if raw is None:
      return ""
    if isinstance(raw, bytes):
      return raw.decode("utf-8", errors="ignore").strip()
    return str(raw).strip()

  def _param_bool(self, key: str) -> bool:
    try:
      return bool(self.params.get_bool(key))
    except Exception:
      return self._param_text(key).lower() in {"1", "true", "yes", "on"}

  def _default_param_text(self, key: str) -> str:
    try:
      default_value = self.params.get_default_value(key)
    except Exception:
      return ""
    if default_value is None:
      return ""
    if isinstance(default_value, bytes):
      return default_value.decode("utf-8", errors="ignore").strip()
    return str(default_value).strip()

  def _resolve_mirrored_param(self, primary_key: str, secondary_key: str) -> str:
    primary_val = self._param_text(primary_key)
    secondary_val = self._param_text(secondary_key)
    if primary_val == secondary_val:
      return secondary_val or primary_val

    primary_default = self._default_param_text(primary_key)
    secondary_default = self._default_param_text(secondary_key)
    primary_non_default = bool(primary_val) and primary_val != primary_default
    secondary_non_default = bool(secondary_val) and secondary_val != secondary_default

    if secondary_non_default:
      return secondary_val
    if primary_non_default:
      return primary_val
    return secondary_val or primary_val

  def _load_catalog_from_params(self):
    self.available_models = [entry for entry in self._param_text("AvailableModels").split(",") if entry]
    self.model_versions = [entry for entry in self._param_text("ModelVersions").split(",") if entry]
    self.model_series = [entry for entry in self._param_text("AvailableModelSeries").split(",") if entry]
    self.available_model_names = [entry for entry in self._param_text("AvailableModelNames").split(",") if entry]
    self.artifact_formats = [entry for entry in self._param_text("AvailableModelArtifactFormats").split(",") if entry]

  @staticmethod
  def _manifest_paths(manifest_version: str) -> tuple[str, ...]:
    return (f"Models/model_names_{manifest_version}.json",)

  def _set_model_param_keys(self, model_key: str | None = None, model_name: str | None = None, model_version: str | None = None):
    if model_key is not None and model_key != "":
      canonical_key = self._canonical_model_key(model_key)
      self.params.put("Model", canonical_key)
      self.params.put("DrivingModel", canonical_key)
    if model_name is not None and model_name != "":
      self.params.put("DrivingModelName", model_name)
    if model_version is not None and model_version != "":
      self.params.put("ModelVersion", model_version)
      self.params.put("DrivingModelVersion", model_version)

  def _ensure_model_params(self):
    selected_model = self._selected_model()
    current_version = self._resolve_mirrored_param("ModelVersion", "DrivingModelVersion")
    if not current_version:
      current_version = self._default_param_text("ModelVersion") or self._default_param_text("DrivingModelVersion") or ("v15" if is_builtin_model_key(selected_model) else "v11")

    selected_name = self._param_text("DrivingModelName")
    if not selected_name and selected_model in self.available_models:
      selected_index = self.available_models.index(selected_model)
      if selected_index < len(self.available_model_names):
        selected_name = self.available_model_names[selected_index]

    self._set_model_param_keys(selected_model, selected_name, current_version)

  def _ensure_model_profiles(self):
    for profile in MODEL_PROFILE_PARAMS:
      model_key, model_name, model_version = get_model_profile(self.params, profile)
      if model_key:
        set_model_profile(self.params, profile, model_key, model_name, model_version)

  def _model_key_aliases(self, model_key: str) -> list[str]:
    return model_key_aliases(model_key)

  def _model_version_map(self) -> dict[str, str]:
    return {
      model_key: self.model_versions[index]
      for index, model_key in enumerate(self.available_models)
      if index < len(self.model_versions) and model_key
    }

  def _model_artifact_format_map(self) -> dict[str, str]:
    return {
      model_key: self.artifact_formats[index]
      for index, model_key in enumerate(self.available_models)
      if index < len(self.artifact_formats) and model_key
    }

  def _resolve_manifest_model_key(self, model_key: str) -> str:
    """Resolve an old manifest ID to its namespaced v23 replacement."""
    canonical_key = self._canonical_model_key(model_key)
    if canonical_key in self.available_models or is_builtin_model_key(canonical_key):
      return canonical_key

    for alias in self._model_key_aliases(canonical_key):
      candidate = f"{alias}{MODEL_NAMESPACE_SUFFIX}"
      if candidate in self.available_models:
        return candidate
    return canonical_key

  def _blacklisted_model_keys(self) -> set[str]:
    return {
      self._canonical_model_key(entry)
      for entry in self._param_text("BlacklistedModels").split(",")
      if entry.strip()
    }

  def _selected_model(self) -> str:
    selected = self._resolve_mirrored_param("Model", "DrivingModel")
    if selected:
      return self._canonical_model_key(selected)
    default_value = self._default_param_text("Model") or self._default_param_text("DrivingModel")
    if default_value:
      return self._canonical_model_key(default_value)
    return DEFAULT_MODEL_KEY

  def _required_files(self, model_key: str, artifact_format: str) -> list[str]:
    if not is_supported_artifact_format(artifact_format):
      return []
    return [driving_artifact_filename(model_key, artifact_format)]

  @staticmethod
  def _artifact_urls_cache_path() -> Path:
    return MODELS_PATH / ARTIFACT_URLS_CACHE

  @staticmethod
  def _artifact_metadata_cache_path() -> Path:
    return MODELS_PATH / ARTIFACT_METADATA_CACHE

  def _load_artifact_url_map(self) -> dict[str, dict[str, str]]:
    try:
      cache_path = self._artifact_urls_cache_path()
      if not cache_path.is_file():
        return {}

      payload = json.loads(cache_path.read_text())
      if not isinstance(payload, dict):
        return {}

      normalized: dict[str, dict[str, str]] = {}
      for model_key, urls in payload.items():
        if not isinstance(urls, dict):
          continue
        normalized[str(model_key)] = {
          str(filename): str(url)
          for filename, url in urls.items()
          if filename and url
        }
      return normalized
    except Exception as error:
      print(f"Failed to load artifact URL cache: {error}")
      return {}

  def _build_artifact_url_map(self, model_info: list[dict]) -> dict[str, dict[str, str]]:
    artifact_url_map: dict[str, dict[str, str]] = {}

    for model in model_info:
      model_key = self._canonical_model_key(str(model.get("id") or "").strip())
      artifact_format = str(model.get("artifact_format") or "").strip()
      required_files = self._required_files(model_key, artifact_format)
      if not model_key or not required_files:
        continue

      urls: dict[str, str] = {}

      explicit_urls = model.get("artifact_urls") or model.get("download_urls")
      if isinstance(explicit_urls, dict):
        for filename, url in explicit_urls.items():
          if filename and url:
            urls[str(filename).strip()] = str(url).strip()

      base_url = str(model.get("artifact_base_url") or model.get("download_base_url") or "").strip()
      if base_url:
        base_url = base_url.rstrip("/")
        for filename in required_files:
          urls.setdefault(filename, f"{base_url}/{filename}")

      direct_url = str(model.get("artifact_url") or model.get("download_url") or "").strip()
      if direct_url:
        if len(required_files) == 1:
          urls.setdefault(required_files[0], direct_url)
        else:
          matched_filename = next((filename for filename in required_files if Path(filename).name == Path(direct_url).name), None)
          if matched_filename is not None:
            urls.setdefault(matched_filename, direct_url)

      if urls:
        artifact_url_map[model_key] = urls

    return artifact_url_map

  @staticmethod
  def _normalize_accelerator_artifacts(model: dict) -> dict[str, dict]:
    raw_artifacts = model.get("accelerator_artifacts")
    if not isinstance(raw_artifacts, dict):
      return {}

    artifacts: dict[str, dict] = {}
    for accelerator, raw_artifact in raw_artifacts.items():
      accelerator = str(accelerator or "").strip().lower()
      if not accelerator or not isinstance(raw_artifact, dict):
        continue
      artifact_format = str(raw_artifact.get("artifact_format") or UNIFIED_ARTIFACT_FORMAT).strip()
      if not is_supported_artifact_format(artifact_format):
        continue
      artifacts[accelerator] = {
        "artifact_format": artifact_format,
        "artifact_filename": str(raw_artifact.get("artifact_filename") or "").strip(),
        "artifact_size": int(raw_artifact.get("artifact_size") or 0),
        "artifact_sha256": str(raw_artifact.get("artifact_sha256") or "").strip().lower(),
        "artifact_chunk_count": int(raw_artifact.get("artifact_chunk_count") or 0),
        "artifact_url": str(raw_artifact.get("artifact_url") or raw_artifact.get("download_url") or "").strip(),
        "execution_device": str(raw_artifact.get("execution_device") or raw_artifact.get("device") or "").strip().upper(),
      }
    return artifacts

  def _build_artifact_metadata_map(self, model_info: list[dict]) -> dict[str, dict]:
    metadata: dict[str, dict] = {}
    for model in model_info:
      model_key = self._canonical_model_key(str(model.get("id") or "").strip())
      artifact_format = str(model.get("artifact_format") or UNIFIED_ARTIFACT_FORMAT).strip()
      if not model_key or not is_supported_artifact_format(artifact_format):
        continue
      uses_external_gpu = bool(model.get("uses_external_gpu", False))
      model_size_declared = bool(model.get("model_size") or model.get("size_class"))
      model_size = str(model.get("model_size") or model.get("size_class") or ("chestnut" if uses_external_gpu else "small")).strip()
      metadata[model_key] = {
        "artifact_format": artifact_format,
        "artifact_filename": str(model.get("artifact_filename") or "").strip(),
        "artifact_size": int(model.get("artifact_size") or 0),
        "artifact_sha256": str(model.get("artifact_sha256") or "").strip().lower(),
        "artifact_chunk_count": int(model.get("artifact_chunk_count") or 0),
        "artifact_url": str(model.get("artifact_url") or model.get("download_url") or "").strip(),
        "uses_external_gpu": uses_external_gpu,
        "model_size": model_size,
        "model_size_declared": model_size_declared,
        "model_lab_eligible": bool(model.get("model_lab_eligible", not uses_external_gpu)),
        "accelerator_artifacts": self._normalize_accelerator_artifacts(model),
      }
    return metadata

  def _load_artifact_metadata_map(self) -> dict[str, dict]:
    try:
      path = self._artifact_metadata_cache_path()
      payload = json.loads(path.read_text()) if path.is_file() else {}
      return payload if isinstance(payload, dict) else {}
    except Exception as error:
      print(f"Failed to load artifact metadata cache: {error}")
      return {}

  def _is_model_downloaded(self, model_key: str, artifact_format: str) -> bool:
    if is_builtin_model_key(model_key):
      return True

    required_files = self._required_files(model_key, artifact_format)
    if not required_files:
      return False
    metadata = self._load_artifact_metadata_map().get(self._canonical_model_key(model_key), {})
    for filename in required_files:
      path = MODELS_PATH / filename
      if not file_chunked_exists(path):
        return False
      expected_size = int(metadata.get("artifact_size") or 0)
      try:
        paths = get_existing_chunks(path)
      except (OSError, ValueError):
        return False
      if paths and paths[0] == get_manifest_path(path):
        paths = paths[1:]
      if not paths or any(not Path(part).is_file() for part in paths):
        return False
      if expected_size and sum(Path(part).stat().st_size for part in paths) != expected_size:
        return False
    return True

  def _installed_model_choices(self, profile: str = "") -> list[tuple[str, str, str]]:
    self._load_catalog_from_params()
    version_map = self._model_version_map()
    artifact_format_map = self._model_artifact_format_map()
    blacklisted_keys = self._blacklisted_model_keys()
    choices: list[tuple[str, str, str]] = []
    seen_keys: set[str] = set()

    for index, model_key in enumerate(self.available_models):
      if not model_key:
        continue

      canonical_key = self._canonical_model_key(model_key)
      if canonical_key in blacklisted_keys or canonical_key in seen_keys:
        continue
      if profile and model_uses_external_gpu(canonical_key) != (profile == "big"):
        continue
      if model_uses_external_gpu(canonical_key) and not external_gpu_available():
        continue

      model_version = version_map.get(model_key) or version_map.get(canonical_key) or ""
      if not model_version and is_builtin_model_key(canonical_key):
        model_version = self._default_param_text("ModelVersion") or self._default_param_text("DrivingModelVersion") or "v15"

      artifact_format = artifact_format_map.get(model_key) or artifact_format_map.get(canonical_key) or ""
      if not self._is_model_downloaded(model_key, artifact_format):
        continue

      model_name = self.available_model_names[index] if index < len(self.available_model_names) else canonical_key
      choices.append((canonical_key, model_name, model_version))
      seen_keys.add(canonical_key)

    return choices

  def randomize_selected_model(self) -> str | None:
    if not self._param_bool("ModelRandomizer"):
      return None
    if load_model_lab_config(self.params)["enabled"]:
      print("Model Randomizer skipped while Model Laboratory is enabled.")
      return None

    active_big_model, _, _ = get_model_profile(self.params, "big")
    profile = "big" if external_gpu_available() and active_big_model else "small"
    choices = self._installed_model_choices(profile)
    if not choices:
      print("Model Randomizer skipped: no installed, non-blacklisted models available.")
      return None

    selected, _, _ = get_model_profile(self.params, profile)
    eligible_choices = [choice for choice in choices if self._canonical_model_key(choice[0]) != selected]
    if not eligible_choices:
      eligible_choices = choices

    model_key, model_name, model_version = random.choice(eligible_choices)
    if not model_version:
      model_version = self._default_param_text("ModelVersion") or self._default_param_text("DrivingModelVersion") or "v11"

    set_model_profile(self.params, profile, model_key, model_name, model_version)
    self._set_model_param_keys(model_key, model_name, model_version)
    try:
      self.params_memory.put_bool("StarPilotTogglesUpdated", True)
    except Exception:
      pass
    print(f"Model Randomizer selected {model_name} ({model_key}, {model_version}).")
    return model_key

  def _sync_selected_model_version(self):
    version_map = self._model_version_map()
    name_map = {model_key: model_name for model_key, model_name in zip(self.available_models, self.available_model_names)}
    selected = self._selected_model()
    version = version_map.get(selected)
    if version:
      self._set_model_param_keys(selected, name_map.get(selected), version)
      return

    for alias in self._model_key_aliases(selected):
      version = version_map.get(alias)
      if version:
        selected_name = name_map.get(selected) or name_map.get(alias) or self._param_text("DrivingModelName")
        self._set_model_param_keys(selected, selected_name, version)
        return

    fallback_version = self._resolve_mirrored_param("ModelVersion", "DrivingModelVersion")
    if not fallback_version:
      fallback_version = self._default_param_text("ModelVersion") or self._default_param_text("DrivingModelVersion") or ("v15" if is_builtin_model_key(selected) else "v11")
    self._set_model_param_keys(selected, name_map.get(selected, ""), fallback_version)

  @staticmethod
  def _fetch_manifest(url: str) -> list[dict]:
    try:
      with urllib.request.urlopen(url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
      return payload.get("models", []) if isinstance(payload, dict) else []
    except Exception as error:
      handle_request_error(error, None, None, None, None)
      return []

  @staticmethod
  def _is_huggingface_url(url: str) -> bool:
    return "huggingface.co/buckets/" in url

  @staticmethod
  def _hf_manifest_paths(manifest_version: str) -> tuple[str, ...]:
    return (f"manifests/model_names_{manifest_version}.json",)

  @classmethod
  def _artifact_source_urls(cls, resource_url: str, manifest_version: str, model_key: str, filename: str) -> tuple[str, ...]:
    model_key = quote(cls._canonical_model_key(model_key), safe="")
    manifest_version = quote(manifest_version, safe="")
    filename = quote(filename, safe="")
    if cls._is_huggingface_url(resource_url):
      return (f"{resource_url}/models/{manifest_version}/{model_key}/{filename}",)
    return (f"{resource_url}/Models/{manifest_version}/{model_key}/{filename}",)

  def _get_manifest(self, resource_urls: str | list[str]) -> tuple[str | None, list[dict]]:
    if isinstance(resource_urls, str):
      resource_urls = [resource_urls]

    for manifest_version in MANIFEST_CANDIDATES:
      for resource_url in resource_urls:
        manifest_paths = (
          self._hf_manifest_paths(manifest_version)
          if self._is_huggingface_url(resource_url)
          else self._manifest_paths(manifest_version)
        )
        for manifest_path in manifest_paths:
          model_info = self._fetch_manifest(f"{resource_url}/{manifest_path}")
          if not model_info:
            continue

          filtered = [
            model for model in model_info
            if is_supported_artifact_format(model.get("artifact_format"))
          ]
          if not filtered:
            continue

          return manifest_version, filtered

    return None, []

  def _remove_stale_model_files(self):
    valid_keys = set(self.available_models)
    for model_file in MODELS_PATH.iterdir():
      if not model_file.is_file() or not is_driving_artifact_file(model_file.name):
        continue
      model_key = model_file.name.split("_driving_", 1)[0] if "_driving_" in model_file.name else ""
      if not model_key or not is_local_model_key(model_key) and model_key not in valid_keys:
        delete_file(model_file, print_error=False)

    for temp_file in MODELS_PATH.glob("tmp*"):
      delete_file(temp_file, print_error=False)

  def _enforce_selected_model(self):
    if not self.available_models:
      return

    selected = self._selected_model()
    if is_builtin_model_key(selected):
      self._sync_selected_model_version()
    else:
      resolved_selected = self._resolve_manifest_model_key(selected)
      if resolved_selected != selected:
        selected_index = self.available_models.index(resolved_selected)
        selected_name = self.available_model_names[selected_index] if selected_index < len(self.available_model_names) else resolved_selected
        self._set_model_param_keys(resolved_selected, selected_name, None)
        selected = resolved_selected

      aliases = self._model_key_aliases(selected)
      if any(alias in self.available_models for alias in aliases):
        self._sync_selected_model_version()
      else:
        try:
          default_model = self._default_param_text("Model") or self._default_param_text("DrivingModel")
        except Exception:
          default_model = DEFAULT_MODEL_KEY

        candidates = self._model_key_aliases(default_model) + self._model_key_aliases(DEFAULT_MODEL_KEY) + self.available_models
        replacement = next((entry for entry in candidates if entry in self.available_models), self.available_models[0])
        replacement_index = self.available_models.index(replacement)
        replacement_name = self.available_model_names[replacement_index] if replacement_index < len(self.available_model_names) else replacement
        self._set_model_param_keys(replacement, replacement_name, None)
        self._sync_selected_model_version()

    self._ensure_model_profiles()

  def _discover_local_models(self) -> list[dict]:
    """Synthesize manifest entries for hand-installed models found in MODELS_PATH.

    A local model is any "<local-*>_driving_*" artifact. An optional "<id>.json"
    sidecar supplies name/version/series; without one the version stays empty so
    modeld falls back to the version embedded in the artifact itself.
    """
    try:
      entries = sorted(MODELS_PATH.glob(f"{LOCAL_MODEL_PREFIX}*_driving_*"))
    except Exception as error:
      print(f"Failed to scan for local models: {error}")
      return []

    discovered: dict[str, dict] = {}
    for model_file in entries:
      model_key = model_file.name.split("_driving_", 1)[0]
      # Keys and names land in comma-joined params, so a comma would corrupt the catalog.
      if not model_key.startswith(LOCAL_MODEL_PREFIX) or "," in model_key or model_key in discovered:
        continue

      info: dict = {}
      sidecar = MODELS_PATH / f"{model_key}.json"
      if sidecar.is_file():
        try:
          loaded = json.loads(sidecar.read_text())
          if isinstance(loaded, dict):
            info = loaded
        except Exception as error:
          print(f"Ignoring malformed local model sidecar {sidecar.name}: {error}")

      fallback_name = model_key[len(LOCAL_MODEL_PREFIX):].replace("_", " ").replace("-", " ").strip()
      discovered[model_key] = {
        "id": model_key,
        "name": _clean_model_name(info.get("name") or fallback_name or model_key).replace(",", " "),
        "version": str(info.get("version") or "").strip(),
        "series": str(info.get("series") or LOCAL_MODEL_SERIES).strip().replace(",", " "),
        "released": str(info.get("released") or "2100-01-01").strip(),
        "community_favorite": False,
        "artifact_format": UNIFIED_ARTIFACT_FORMAT,
        "uses_external_gpu": bool(info.get("uses_external_gpu", False)),
        "model_size": str(info.get("model_size") or "small").strip(),
        "model_lab_eligible": bool(info.get("model_lab_eligible", not info.get("uses_external_gpu", False))),
        "accelerator_artifacts": info.get("accelerator_artifacts", {}),
      }

    return list(discovered.values())

  def update_model_params(self, model_info: list[dict], manifest_version: str):
    model_info = list(model_info) + self._discover_local_models()
    self.available_models = [str(model.get("id") or "").strip() for model in model_info]
    self.available_model_names = [_clean_model_name(model.get("name")) for model in model_info]
    self.model_versions = [str(model.get("version") or "").strip() for model in model_info]
    self.model_series = [str(model.get("series") or "Custom Series").strip() for model in model_info]
    self.artifact_formats = [
      str(model.get("artifact_format") or UNIFIED_ARTIFACT_FORMAT).strip()
      for model in model_info
    ]

    released_dates = [str(model.get("released") or "2023-01-01").strip() for model in model_info]
    community_favorites = [model_key for model_key, model in zip(self.available_models, model_info) if model.get("community_favorite", False)]

    self.params.put("AvailableModels", ",".join(self.available_models))
    self.params.put("AvailableModelNames", ",".join(self.available_model_names))
    self.params.put("AvailableModelSeries", ",".join(self.model_series))
    self.params.put("AvailableModelArtifactFormats", ",".join(self.artifact_formats))
    self.params.put("ModelReleasedDates", ",".join(released_dates))
    self.params.put("ModelVersions", ",".join(self.model_versions))
    self.params.put("CommunityFavorites", ",".join(community_favorites))
    self.params.put("ModelManifestVersion", manifest_version)

    self._sync_selected_model_version()

    try:
      version_map = {model_key: version for model_key, version in zip(self.available_models, self.model_versions)}
      versions_file = MODELS_PATH / ".model_versions.json"
      versions_file.parent.mkdir(parents=True, exist_ok=True)
      versions_file.write_text(json.dumps(version_map))

      artifact_urls_file = self._artifact_urls_cache_path()
      artifact_urls_file.write_text(json.dumps(self._build_artifact_url_map(model_info)))
      self._artifact_metadata_cache_path().write_text(json.dumps(self._build_artifact_metadata_map(model_info)))
    except Exception as error:
      print(f"Failed to write model versions cache: {error}")
    self._ensure_model_profiles()

  def check_models(self, boot_run: bool):
    del boot_run  # Not currently needed, retained for call-site parity.
    self._remove_stale_model_files()
    self._enforce_selected_model()

  def _migrate_model_artifacts(self, selected_model: str):
    """Remove artifacts compiled for the previous tinygrad manifest.

    Model IDs are stable across manifest generations, but tinygrad pickles are
    not. Local models are intentionally retained because StarPilot does not own
    or have a source from which to redownload them.
    """
    removed = 0
    for model_file in MODELS_PATH.iterdir():
      if not model_file.is_file() or not is_driving_artifact_file(model_file.name):
        continue
      model_key = model_file.name.split("_driving_", 1)[0] if "_driving_" in model_file.name else ""
      if model_key and is_local_model_key(model_key):
        continue
      if model_file.is_file() or model_file.is_symlink():
        delete_file(model_file, print_error=False)
        removed += 1
    if removed:
      print(f"Removed {removed} incompatible model artifacts during tinygrad manifest migration.")

    if selected_model and not is_builtin_model_key(selected_model):
      self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, f"Downloading selected model \"{selected_model}\"...")
      self.download_model(selected_model)
      selected_format = self._model_artifact_format_map().get(selected_model, "")
      selected_files = self._required_files(selected_model, selected_format)
      if not selected_files or not all(file_chunked_exists(MODELS_PATH / filename) for filename in selected_files):
        default_index = next(
          (index for index, key in enumerate(self.available_models) if is_builtin_model_key(key)),
          None,
        )
        default_name = (
          self.available_model_names[default_index]
          if default_index is not None and default_index < len(self.available_model_names)
          else "Regret Driven Framework V4"
        )
        default_version = (
          self.model_versions[default_index]
          if default_index is not None and default_index < len(self.model_versions)
          else "v15"
        )
        self._set_model_param_keys(DEFAULT_MODEL_KEY, default_name, default_version)
        self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Selected model unavailable; using built-in model.")

  def update_models(self, boot_run=False):
    if self.downloading_model:
      return

    resource_urls = get_resource_urls()
    if not resource_urls:
      print("Hugging Face and GitHub are offline...")
      return

    manifest_version, model_info = self._get_manifest(resource_urls)
    if not model_info:
      print("No compatible tinygrad manifest found.")
      return

    selected_model = self._selected_model()
    previous_manifest = self._param_text("ModelManifestVersion")
    resolved_manifest = manifest_version or "unknown"
    self.update_model_params(model_info, resolved_manifest)
    migrated_model = self._resolve_manifest_model_key(selected_model)
    if migrated_model != selected_model:
      migrated_index = self.available_models.index(migrated_model)
      migrated_name = self.available_model_names[migrated_index] if migrated_index < len(self.available_model_names) else migrated_model
      migrated_version = self.model_versions[migrated_index] if migrated_index < len(self.model_versions) else ""
      self._set_model_param_keys(migrated_model, migrated_name, migrated_version)
      selected_model = migrated_model
    if previous_manifest != resolved_manifest:
      self._migrate_model_artifacts(selected_model)
    self.check_models(boot_run)

  def download_model(self, model_to_download: str):
    allow_gpu_without_gpu = self.params_memory.get_bool(ALLOW_GPU_DOWNLOAD_WITHOUT_GPU_PARAM)
    try:
      self._download_model(model_to_download, allow_gpu_without_gpu)
    finally:
      self.params_memory.remove(ALLOW_GPU_DOWNLOAD_WITHOUT_GPU_PARAM)

  def _download_artifact_to_path(self, model_key: str, file_path: Path, remote_filename: str,
                                 artifact_metadata: dict, artifact_urls: dict[str, str],
                                 resource_urls: list[str]) -> bool:
    manifest_version = self._param_text("ModelManifestVersion") or MANIFEST_CANDIDATES[0]
    candidate_urls: list[tuple[str, bool, bool]] = []
    custom_url = (
      artifact_urls.get(file_path.name)
      or artifact_urls.get(remote_filename)
      or artifact_metadata.get("artifact_url")
      or ""
    ).strip()
    if custom_url:
      candidate_urls.append((custom_url, True, False))

    for resource_url in resource_urls:
      for artifact_url in self._artifact_source_urls(resource_url, manifest_version, model_key, remote_filename):
        if not any(existing[0] == artifact_url for existing in candidate_urls):
          candidate_urls.append((artifact_url, False, True))

    for candidate_url, allow_unknown_size, allow_multipart in candidate_urls:
      chunk_count = int(artifact_metadata.get("artifact_chunk_count") or 0)
      if chunk_count and download_chunked_file(
        CANCEL_DOWNLOAD_PARAM,
        file_path,
        DOWNLOAD_PROGRESS_PARAM,
        candidate_url,
        self.params_memory,
        expected_size=artifact_metadata.get("artifact_size"),
        expected_sha256=artifact_metadata.get("artifact_sha256"),
        expected_chunk_count=chunk_count,
      ):
        return True

      download_file(
        CANCEL_DOWNLOAD_PARAM,
        file_path,
        DOWNLOAD_PROGRESS_PARAM,
        candidate_url,
        MODEL_DOWNLOAD_PARAM,
        self.params_memory,
        allow_unknown_size=allow_unknown_size,
        suppress_errors=True,
      )
      if self.params_memory.get_bool(CANCEL_DOWNLOAD_PARAM):
        return False

      if verify_download(
        file_path,
        candidate_url,
        allow_unknown_size=allow_unknown_size,
        expected_size=artifact_metadata.get("artifact_size"),
        expected_sha256=artifact_metadata.get("artifact_sha256"),
      ):
        return True
      delete_file(file_path, print_error=False)

      if not chunk_count and download_chunked_file(
        CANCEL_DOWNLOAD_PARAM,
        file_path,
        DOWNLOAD_PROGRESS_PARAM,
        candidate_url,
        self.params_memory,
      ):
        return True

      if allow_multipart and download_multipart_file(
        CANCEL_DOWNLOAD_PARAM,
        file_path,
        DOWNLOAD_PROGRESS_PARAM,
        candidate_url,
        MODEL_DOWNLOAD_PARAM,
        self.params_memory,
      ):
        return True

    delete_chunked_artifact(file_path)
    return False

  def download_model_accelerator(self, model_key: str, accelerator: str = MODEL_LAB_ACCELERATOR) -> bool:
    self.downloading_model = True
    model_key = self._canonical_model_key(model_key)
    accelerator = str(accelerator or "").strip().lower()
    try:
      if accelerator == MODEL_LAB_ACCELERATOR and not external_gpu_available():
        handle_error(None, "External GPU required...", "Chestnut is not connected and firmware-ready.",
                     MODEL_LAB_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
        return False

      artifact_metadata = model_accelerator_artifact_metadata(model_key, accelerator)
      if not model_accelerator_artifact_available(model_key, accelerator):
        handle_error(None, "Accelerator artifact unavailable...",
                     f"The manifest has no precompiled {MODEL_LAB_EXECUTION_DEVICE} artifact for {model_key}.",
                     MODEL_LAB_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
        return False

      resource_urls = get_resource_urls()
      if not resource_urls:
        handle_error(None, "Hugging Face and GitHub are offline...", "Repository unavailable",
                     MODEL_LAB_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
        return False

      artifact_urls = self._load_artifact_url_map().get(model_key, {})
      local_path = model_accelerator_artifact_path(model_key, accelerator)
      remote_filename = str(artifact_metadata.get("artifact_filename") or local_path.name).strip()
      if Path(remote_filename).name != remote_filename:
        handle_error(None, "Invalid accelerator artifact filename...", "Model download failed",
                     MODEL_LAB_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
        return False

      if not self._download_artifact_to_path(
        model_key, local_path, remote_filename, artifact_metadata, artifact_urls, resource_urls,
      ):
        if self.params_memory.get_bool(CANCEL_DOWNLOAD_PARAM):
          handle_error(None, "Download cancelled...", "Download cancelled...",
                       MODEL_LAB_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
        else:
          handle_error(local_path, "Verification failed...", f"Verification failed for {remote_filename}",
                       MODEL_LAB_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
        return False

      self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Chestnut artifact downloaded!")
      return True
    finally:
      self.params_memory.remove(MODEL_LAB_DOWNLOAD_PARAM)
      self.downloading_model = False

  def _download_model(self, model_to_download: str, allow_gpu_without_gpu: bool):
    self.downloading_model = True
    model_to_download = self._canonical_model_key(model_to_download)

    if is_builtin_model_key(model_to_download):
      self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Built-in model already downloaded.")
      self.params_memory.remove(MODEL_DOWNLOAD_PARAM)
      self.downloading_model = False
      return

    if model_uses_external_gpu(model_to_download) and not external_gpu_available() and not allow_gpu_without_gpu:
      handle_error(None, "External GPU required...", "This model requires a detected external GPU.", MODEL_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
      self.downloading_model = False
      return

    # Local models have no upstream URL; a download attempt would 404 and then
    # delete_file() the artifact on verification failure.
    if is_local_model_key(model_to_download):
      self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Local model, nothing to download.")
      self.params_memory.remove(MODEL_DOWNLOAD_PARAM)
      self.downloading_model = False
      return

    resource_urls = get_resource_urls()
    if not resource_urls:
      handle_error(None, "Hugging Face and GitHub are offline...", "Repository unavailable", MODEL_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
      self.downloading_model = False
      return

    # Refresh from params so long-lived workers pick up manifest refreshes done by
    # a separate ModelManager instance before we validate the requested model.
    self._load_catalog_from_params()
    artifact_format_map = self._model_artifact_format_map()
    artifact_format = artifact_format_map.get(model_to_download) or artifact_format_map.get(self._canonical_model_key(model_to_download)) or ""
    model_artifact_urls = self._load_artifact_url_map()
    artifact_urls = model_artifact_urls.get(self._canonical_model_key(model_to_download)) or model_artifact_urls.get(model_to_download) or {}
    artifact_metadata_map = self._load_artifact_metadata_map()
    artifact_metadata = artifact_metadata_map.get(self._canonical_model_key(model_to_download)) or artifact_metadata_map.get(model_to_download) or {}
    required_files = self._required_files(model_to_download, artifact_format)
    if not required_files:
      handle_error(None, f"Unsupported model format for {model_to_download}", "Model download failed", MODEL_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
      self.downloading_model = False
      return

    for filename in required_files:
      file_path = MODELS_PATH / filename
      remote_filename = str(artifact_metadata.get("artifact_filename") or filename).strip()
      download_succeeded = self._download_artifact_to_path(
        model_to_download, file_path, remote_filename, artifact_metadata, artifact_urls, resource_urls,
      )

      if not download_succeeded:
        if self.params_memory.get_bool(CANCEL_DOWNLOAD_PARAM):
          handle_error(None, "Download cancelled...", "Download cancelled...", MODEL_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
          self.downloading_model = False
          return
        handle_error(file_path, "Verification failed...", f"Verification failed for {filename}", MODEL_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
        self.downloading_model = False
        return

    self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Downloaded!")
    self.params_memory.remove(MODEL_DOWNLOAD_PARAM)
    self.downloading_model = False

  def download_all_models(self):
    allow_gpu_without_gpu = self.params_memory.get_bool(ALLOW_GPU_DOWNLOAD_WITHOUT_GPU_PARAM)
    try:
      self._download_all_models(allow_gpu_without_gpu)
    finally:
      self.params_memory.remove(ALLOW_GPU_DOWNLOAD_WITHOUT_GPU_PARAM)

  def _download_all_models(self, allow_gpu_without_gpu: bool):
    resource_urls = get_resource_urls()
    if not resource_urls:
      handle_error(None, "Hugging Face and GitHub are offline...", "Repository unavailable", MODEL_DOWNLOAD_ALL_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
      return

    manifest_version, model_info = self._get_manifest(resource_urls)
    if not model_info:
      handle_error(None, "Unable to fetch models...", "Model list unavailable", MODEL_DOWNLOAD_ALL_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
      return

    self.update_model_params(model_info, manifest_version or "unknown")

    artifact_format_map = self._model_artifact_format_map()
    for model_key, model_name in zip(self.available_models, self.available_model_names):
      if self.params_memory.get_bool(CANCEL_DOWNLOAD_PARAM):
        handle_error(None, "Download cancelled...", "Download cancelled...", MODEL_DOWNLOAD_ALL_PARAM, DOWNLOAD_PROGRESS_PARAM, self.params_memory)
        return

      if is_local_model_key(model_key):
        continue

      if model_uses_external_gpu(model_key) and not external_gpu_available() and not allow_gpu_without_gpu:
        continue

      artifact_format = artifact_format_map.get(model_key, "")
      if self._is_model_downloaded(model_key, artifact_format):
        continue

      self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, f"Downloading \"{model_name}\"...")
      self._download_model(model_key, allow_gpu_without_gpu)
      if self.params_memory.get_bool(CANCEL_DOWNLOAD_PARAM):
        return

    self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "All models downloaded!")
    self.params_memory.remove(MODEL_DOWNLOAD_ALL_PARAM)
    self.randomize_selected_model()

  def update_tinygrad(self):
    # This branch ships tinygrad runtime in-tree. "Update" here refreshes local model files.
    self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Updating...")

    for model_file in MODELS_PATH.iterdir():
      if not model_file.is_file() or not is_driving_artifact_file(model_file.name):
        continue
      model_key = model_file.name.split("_driving_", 1)[0] if "_driving_" in model_file.name else ""
      if model_key and is_local_model_key(model_key):
        continue
      if model_file.is_file():
        delete_file(model_file, print_error=False)

    model_versions_file = MODELS_PATH / ".model_versions.json"
    if model_versions_file.is_file():
      delete_file(model_versions_file, print_error=False)

    artifact_urls_file = self._artifact_urls_cache_path()
    if artifact_urls_file.is_file():
      delete_file(artifact_urls_file, print_error=False)

    artifact_metadata_file = self._artifact_metadata_cache_path()
    if artifact_metadata_file.is_file():
      delete_file(artifact_metadata_file, print_error=False)

    self.params.put_bool("TinygradUpdateAvailable", False)
    self.params_memory.remove(UPDATE_TINYGRAD_PARAM)
    self.params_memory.remove(CANCEL_DOWNLOAD_PARAM)

    if self.params.get_bool("AutomaticallyDownloadModels"):
      self.params_memory.put_bool(MODEL_DOWNLOAD_ALL_PARAM, True)
      self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Downloading...")
    else:
      self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Updated!")
