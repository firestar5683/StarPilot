#!/usr/bin/env python3
import json
import re
import requests
import shutil
import time
import urllib.parse
import urllib.request

from pathlib import Path

from openpilot.frogpilot.assets.download_functions import GITLAB_URL, download_file, get_repository_url, handle_error, handle_request_error, verify_download
from openpilot.frogpilot.common.frogpilot_utilities import delete_file
from openpilot.frogpilot.common.frogpilot_variables import DEFAULT_MODEL, MODELS_PATH, params, params_default, params_memory

VERSION = "v20"

CANCEL_DOWNLOAD_PARAM = "CancelModelDownload"
DOWNLOAD_PROGRESS_PARAM = "ModelDownloadProgress"
MODEL_DOWNLOAD_PARAM = "ModelToDownload"
MODEL_DOWNLOAD_ALL_PARAM = "DownloadAllModels"

class ModelManager:
  def __init__(self):
    self.available_models = (params.get("AvailableModels", encoding="utf-8") or "").split(",")
    self.model_versions = (params.get("ModelVersions", encoding="utf-8") or "").split(",")
    self.model_series = (params.get("AvailableModelSeries", encoding="utf-8") or "").split(",")


    self.downloading_model = False

  @staticmethod
  def fetch_models(url):
    try:
      with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))["models"]
    except Exception as error:
      handle_request_error(error, None, None, None, None)
      return []

  @staticmethod
  def fetch_all_model_sizes(repo_url):
    project_path = "firestar5683/StarPilot-Resources"
    branch = "Models"

    if "github" in repo_url:
      api_url = f"https://api.github.com/repos/{project_path}/contents?ref={branch}"
    elif "gitlab" in repo_url:
      api_url = f"https://gitlab.com/api/v4/projects/{urllib.parse.quote_plus(project_path)}/repository/tree?ref={branch}"
    else:
      return {}

    try:
      response = requests.get(api_url)
      response.raise_for_status()
      model_files = [file for file in response.json() if "." in file["name"]]

      if "gitlab" in repo_url:
        model_sizes = {}
        for file in model_files:
          file_path = file["path"]
          metadata_url = f"https://gitlab.com/api/v4/projects/{urllib.parse.quote_plus(project_path)}/repository/files/{urllib.parse.quote_plus(file_path)}/raw?ref={branch}"
          metadata_response = requests.head(metadata_url)
          metadata_response.raise_for_status()
          model_sizes[file["name"].rsplit(".", 1)[0]] = int(metadata_response.headers.get("content-length", 0))
        return model_sizes
      else:
        return {file["name"].rsplit(".", 1)[0]: file["size"] for file in model_files if "size" in file}

    except Exception as error:
      handle_request_error(f"Failed to fetch model sizes from {'GitHub' if 'github' in repo_url else 'GitLab'}: {error}", None, None, None, None)
      return {}

  def handle_verification_failure(self, model, model_path, file_extension):
    print(f"Verification failed for model {model}. Retrying from GitLab...")
    model_url = f"{GITLAB_URL}/Models/{model}.{file_extension}"
    download_file(CANCEL_DOWNLOAD_PARAM, model_path, DOWNLOAD_PROGRESS_PARAM, model_url, MODEL_DOWNLOAD_PARAM, params_memory)

    if params_memory.get_bool(CANCEL_DOWNLOAD_PARAM):
      handle_error(None, "Download cancelled...", "Download cancelled...", MODEL_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, params_memory)
      self.downloading_model = False
      return

    if verify_download(model_path, model_url):
      print(f"Model {model} downloaded and verified successfully!")
      params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Downloaded!")
      params_memory.remove(MODEL_DOWNLOAD_PARAM)
      self.downloading_model = False
    else:
      handle_error(model_path, "Verification failed...", "GitLab verification failed", MODEL_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, params_memory)
      self.downloading_model = False

  def download_model(self, model_to_download):
    self.downloading_model = True

    repo_url = get_repository_url()
    if not repo_url:
      handle_error(None, "GitHub and GitLab are offline...", "Repository unavailable", MODEL_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, params_memory)
      self.downloading_model = False
      return

    try:
      model_index = self.available_models.index(model_to_download)
      model_version = self.model_versions[model_index]
    except Exception:
      handle_error(None, f"Unknown model version for {model_to_download}! Download aborted.", "Model download failed", MODEL_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, params_memory)
      self.downloading_model = False
      return

    if model_version in ("v8", "v9", "v10", "v11"):
      # Download all PKL and metadata files for multi-file tinygrad models (v8 and v9)
      filenames = [
          f"{model_to_download}_driving_policy_tinygrad.pkl",
          f"{model_to_download}_driving_vision_tinygrad.pkl",
          f"{model_to_download}_driving_policy_metadata.pkl",
          f"{model_to_download}_driving_vision_metadata.pkl",
      ]
      for filename in filenames:
        model_path = MODELS_PATH / filename
        model_url = f"{repo_url}/Models/{filename}"
        print(f"Downloading model file: {filename}")
        download_file(CANCEL_DOWNLOAD_PARAM, model_path, DOWNLOAD_PROGRESS_PARAM, model_url, MODEL_DOWNLOAD_PARAM, params_memory)

        if params_memory.get_bool(CANCEL_DOWNLOAD_PARAM):
          handle_error(None, "Download cancelled...", "Download cancelled...", MODEL_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, params_memory)
          self.downloading_model = False
          return

        if verify_download(model_path, model_url):
          print(f"File {filename} downloaded and verified successfully!")
          params_memory.put(DOWNLOAD_PROGRESS_PARAM, f"Downloaded {filename}!")
        else:
          self.handle_verification_failure(filename[:-4], model_path, "pkl")
          self.downloading_model = False
          return
      # After all files are downloaded and verified
      params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Downloaded!")
      params_memory.remove(MODEL_DOWNLOAD_PARAM)

    elif model_version == "v7":
      # Download both PKL and metadata for OG tinygrad models
      v7_filenames = [
        f"{model_to_download}.pkl",
        f"{model_to_download}_metadata.pkl"
      ]
      for filename in v7_filenames:
        model_path = MODELS_PATH / filename
        model_url = f"{repo_url}/Models/{filename}"
        print(f"Downloading v7 model file: {filename}")
        download_file(CANCEL_DOWNLOAD_PARAM, model_path, DOWNLOAD_PROGRESS_PARAM, model_url, MODEL_DOWNLOAD_PARAM, params_memory)

        if params_memory.get_bool(CANCEL_DOWNLOAD_PARAM):
          handle_error(None, "Download cancelled...", "Download cancelled...", MODEL_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, params_memory)
          self.downloading_model = False
          return

        if verify_download(model_path, model_url):
          print(f"File {filename} downloaded and verified successfully!")
          params_memory.put(DOWNLOAD_PROGRESS_PARAM, f"Downloaded {filename}!")
        else:
          self.handle_verification_failure(filename.rsplit('.',1)[0], model_path, "pkl")
          self.downloading_model = False
          return

      # Once both files are fetched
      params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Downloaded!")
      params_memory.remove(MODEL_DOWNLOAD_PARAM)

    else:
      # Classic model: download only the .thneed file
      file_extension = "thneed"
      model_path = MODELS_PATH / f"{model_to_download}.{file_extension}"
      model_url = f"{repo_url}/Models/{model_to_download}.{file_extension}"
      print(f"Downloading classic model: {model_to_download}")
      download_file(CANCEL_DOWNLOAD_PARAM, model_path, DOWNLOAD_PROGRESS_PARAM, model_url, MODEL_DOWNLOAD_PARAM, params_memory)

      if params_memory.get_bool(CANCEL_DOWNLOAD_PARAM):
        handle_error(None, "Download cancelled...", "Download cancelled...", MODEL_DOWNLOAD_PARAM, DOWNLOAD_PROGRESS_PARAM, params_memory)
        self.downloading_model = False
        return

      if verify_download(model_path, model_url):
        print(f"Model {model_to_download} downloaded and verified successfully!")
        params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Downloaded!")
        params_memory.remove(MODEL_DOWNLOAD_PARAM)
      else:
        self.handle_verification_failure(model_to_download, model_path, file_extension)
        self.downloading_model = False
        return

    self.downloading_model = False

  @staticmethod
  def copy_default_model():
    default_model_path = MODELS_PATH / f"{DEFAULT_MODEL}.thneed"
    source_path = Path(__file__).parents[2] / "selfdrive/modeld/models/supercombo.thneed"
    if source_path.is_file() and not default_model_path.is_file():
      shutil.copyfile(source_path, default_model_path)
      print(f"Copied the default model from {source_path} to {default_model_path}")

  def check_models(self, boot_run, repo_url):
    available_models = set(self.available_models) - {DEFAULT_MODEL}
    downloaded_models = set()
    for model in available_models:
      try:
        model_index = self.available_models.index(model)
        model_version = self.model_versions[model_index]
      except Exception:
        model_version = None

      if model_version in ("v8", "v9", "v10", "v11"):
        v8_v9_files = [
          f"{model}_driving_policy_tinygrad.pkl",
          f"{model}_driving_vision_tinygrad.pkl",
          f"{model}_driving_policy_metadata.pkl",
          f"{model}_driving_vision_metadata.pkl",
        ]
        if all((MODELS_PATH / f).is_file() for f in v8_v9_files):
          downloaded_models.add(model)
      elif model_version == "v7":
        filename = f"{model}.pkl"
        if (MODELS_PATH / filename).is_file():
          downloaded_models.add(model)
      else:
        filename = f"{model}.thneed"
        if (MODELS_PATH / filename).is_file():
          downloaded_models.add(model)

    outdated_models = downloaded_models - available_models
    for model in outdated_models:
      for model_file in MODELS_PATH.glob(f"{model}*"):
        print(f"Removing outdated model: {model_file}")
        delete_file(model_file)

    for tmp_file in MODELS_PATH.glob("tmp*"):
      if tmp_file.is_file():
        delete_file(tmp_file)

    if params.get("Model", encoding="utf-8") not in self.available_models:
      params.put("Model", params_default.get("Model", encoding="utf-8"))

    automatically_download_models = params.get_bool("AutomaticallyDownloadModels")
    if not automatically_download_models:
      return

    model_sizes = self.fetch_all_model_sizes(repo_url)
    if not model_sizes:
      print("No model size data available. Continuing downloads based on file existence")
      # do not return; proceed to download missing files

    needs_download = False

    # Enhanced model file validation per model version
    for model in available_models:
      model_version = None
      try:
        model_index = self.available_models.index(model)
        model_version = self.model_versions[model_index]
      except Exception:
        model_version = None

      if model_version in ("v8", "v9", "v10", "v11"):
        v8_v9_files = [
          f"{model}_driving_policy_tinygrad.pkl",
          f"{model}_driving_vision_tinygrad.pkl",
          f"{model}_driving_policy_metadata.pkl",
          f"{model}_driving_vision_metadata.pkl",
        ]
        for filename in v8_v9_files:
          path = MODELS_PATH / filename
          expected_size = model_sizes.get(filename.rsplit(".", 1)[0])
          if not path.is_file() or expected_size is None or path.stat().st_size != expected_size:
            needs_download = True
            break
      elif model_version == "v7":
        filename = f"{model}.pkl"
        path = MODELS_PATH / filename
        expected_size = model_sizes.get(model)
        if not path.is_file() or expected_size is None or path.stat().st_size != expected_size:
          needs_download = True
      else:
        filename = f"{model}.thneed"
        path = MODELS_PATH / filename
        expected_size = model_sizes.get(model)
        if not path.is_file() or expected_size is None or path.stat().st_size != expected_size:
          needs_download = True

    if needs_download:
      self.download_all_models()

  def update_model_params(self, model_info, repo_url):
      self.available_models = [model["id"] for model in model_info]
      self.model_versions = [model["version"] for model in model_info]
      self.model_series = [model.get("series", "Dom Forgot To Label Me") for model in model_info]

      params.put("AvailableModels", ",".join(self.available_models))
      params.put("AvailableModelNames", ",".join([model["name"] for model in model_info]))
      params.put("AvailableModelSeries", ",".join(self.model_series))
      params.put("ModelVersions", ",".join(self.model_versions))
      params.put("AvailableModelSeries", ",".join(self.model_series))
      print("Models list updated successfully")

      # --- Generate per-model version JSON for offline UI ---
      try:
          versions_file = MODELS_PATH / ".model_versions.json"
          version_map = {model_id: version for model_id, version in zip(self.available_models, self.model_versions)}
          with open(versions_file, "w") as vf:
              json.dump(version_map, vf)
      except Exception as e:
          print(f"Failed to write .model_versions.json: {e}")
      # --- end JSON generation ---

      # Immediately sync the active ModelVersion param
      try:
          current = params.get("Model", encoding="utf-8")
          if current in version_map:
              params.put("ModelVersion", version_map[current])
              print(f"Successfully synced ModelVersion to {version_map[current]} for model {current}")
          else:
              print(f"Warning: Model {current} not found in version map")
      except Exception as e:
          print(f"Failed to sync ModelVersion for {current}: {e}")

      # Also ensure ModelVersion is set for the default model if not already set
      try:
          if not params.get("ModelVersion", encoding="utf-8"):
              default_model = params.get("Model", encoding="utf-8") or DEFAULT_MODEL
              if default_model in version_map:
                  params.put("ModelVersion", version_map[default_model])
                  print(f"Set default ModelVersion to {version_map[default_model]} for model {default_model}")
      except Exception as e:
          print(f"Failed to set default ModelVersion: {e}")

  def update_models(self, boot_run=False):
    if self.downloading_model:
      return

    repo_url = get_repository_url()
    if repo_url is None:
      print("GitHub and GitLab are offline...")
      return

    model_info = self.fetch_models(f"{repo_url}/Versions/model_names_{VERSION}.json")
    if model_info:
      self.update_model_params(model_info, repo_url)
      self.check_models(boot_run, repo_url)

      # Ensure ModelVersion is set immediately after updating model params
      if boot_run:
        try:
          current = params.get("Model", encoding="utf-8")
          if current and current in [model["id"] for model in model_info]:
            model_index = [model["id"] for model in model_info].index(current)
            version = model_info[model_index]["version"]
            params.put("ModelVersion", version)
            print(f"Boot sync: Set ModelVersion to {version} for model {current}")
        except Exception as e:
          print(f"Boot sync failed: {e}")

  def download_all_models(self):
    repo_url = get_repository_url()
    if not repo_url:
      handle_error(None, "GitHub and GitLab are offline...", "Repository unavailable", MODEL_DOWNLOAD_ALL_PARAM, DOWNLOAD_PROGRESS_PARAM, params_memory)
      return

    model_info = self.fetch_models(f"{repo_url}/Versions/model_names_{VERSION}.json")
    if model_info:
      available_models = [model["id"] for model in model_info]
      available_model_names = [re.sub(r"[🗺️👀📡]", "", model["name"]).strip() for model in model_info]
      model_versions = [model["version"] for model in model_info]
      model_series = [model.get("series", "Dom Forgot To Label Me") for model in model_info]

      for model, model_name, model_version in zip(available_models, available_model_names, model_versions):
        if params_memory.get_bool(CANCEL_DOWNLOAD_PARAM):
          handle_error(None, "Download cancelled...", "Download cancelled...", MODEL_DOWNLOAD_ALL_PARAM, DOWNLOAD_PROGRESS_PARAM, params_memory)
          return

        if model_version in ("v8", "v9", "v10", "v11"):
          required_files = [
              f"{model}_driving_policy_tinygrad.pkl",
              f"{model}_driving_vision_tinygrad.pkl",
              f"{model}_driving_policy_metadata.pkl",
              f"{model}_driving_vision_metadata.pkl",
          ]
          missing = [f for f in required_files if not (MODELS_PATH / f).is_file()]
          if missing:
            print(f"Tinygrad model {model} is missing files. Preparing to download...")
            params_memory.put(DOWNLOAD_PROGRESS_PARAM, f"Downloading \"{model_name}\"...")
            self.download_model(model)
        elif model_version == "v7":
          # OG tinygrad: only need PKL file
          model_file = MODELS_PATH / f"{model}.pkl"
          if not model_file.is_file():
            print(f"PKL model {model} is missing. Preparing to download...")
            params_memory.put(DOWNLOAD_PROGRESS_PARAM, f"Downloading \"{model_name}\"...")
            self.download_model(model)
        else:
          # Classic: only need .thneed
          model_file = MODELS_PATH / f"{model}.thneed"
          if not model_file.is_file():
            print(f"Classic model {model} is missing. Preparing to download...")
            params_memory.put(DOWNLOAD_PROGRESS_PARAM, f"Downloading \"{model_name}\"...")
            self.download_model(model)

      params_memory.put(DOWNLOAD_PROGRESS_PARAM, "All models downloaded!")
    else:
      handle_error(None, "Unable to fetch models...", "Model list unavailable", MODEL_DOWNLOAD_ALL_PARAM, DOWNLOAD_PROGRESS_PARAM, params_memory)
