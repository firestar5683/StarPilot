"""Exercise source methods with fake HTTP/Params; no native imports or live requests."""
import ast
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest
import requests


def load_source(path, names, namespace):
  nodes = [node for node in ast.parse(path.read_text()).body if
           isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names or
           isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in names for target in node.targets)]
  exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)


class Params:
  def __init__(self):
    self.values = {}
  def get_bool(self, key):
    return bool(self.values.get(key))
  def put(self, key, value):
    self.values[key] = value
  def remove(self, key):
    self.values.pop(key, None)


class Response:
  def __init__(self, data=None, payload=b"", status=200):
    self.data, self.payload, self.status_code = data, payload, status
    self.headers = {"Content-Length": str(len(payload))}
  def json(self):
    return self.data
  def raise_for_status(self):
    if self.status_code >= 400:
      raise requests.exceptions.HTTPError(str(self.status_code), response=self)
  def __enter__(self):
    return self
  def __exit__(self, *args):
    pass
  def iter_content(self, chunk_size):
    yield self.payload


@pytest.fixture
def theme(tmp_path):
  root = Path(__file__).resolve().parents[3]
  archive = io.BytesIO()
  with zipfile.ZipFile(archive, "w") as output:
    output.writestr("asset.bin", b"downloaded asset")
  payloads = {"Distance-Icons/frog-animated.zip": archive.getvalue(),
              "Themes/frog/colors.zip": archive.getvalue(), "Steering-Wheels/frog.png": b"new wheel"}
  trees = {branch: [dict(path="theme/" + path, type="file", size=len(payload))
                    for path, payload in payloads.items() if path.startswith(branch + "/")]
           for branch in ("Distance-Icons", "Steering-Wheels", "Themes")}
  trees["Themes"].append(dict(path="theme/Themes/bootlogo/Preview.png", type="file", size=20))
  catalogs, transfers = [], []
  def get(url, **kwargs):
    if "/tree/theme/" in url:
      branch = url.split("/tree/theme/", 1)[1].split("?", 1)[0]
      catalogs.append(branch)
      return Response(data=trees[branch])
    path = url.split("/theme/", 1)[1] if "/theme/" in url else url.split("example.invalid/", 1)[1]
    transfers.append(path)
    return Response(payload=payloads.get(path, b""), status=200 if path in payloads else 404)
  def head(url, **kwargs):
    path = url.split("/theme/", 1)[1] if "/theme/" in url else url.split("example.invalid/", 1)[1]
    return Response(payload=payloads.get(path, b""), status=200 if path in payloads else 404)
  errors = []
  namespace = dict(Path=Path, requests=requests, json=json, os=os, zipfile=zipfile,
                   HF_BUCKET="fixture/resources", GITHUB_URL="https://example.invalid", THEME_SAVE_PATH=tmp_path,
                   get_resource_urls=lambda _: ["https://huggingface.co/buckets/fixture/resources/resolve", "https://example.invalid"],
                   handle_error=lambda *args: errors.append(args), handle_request_error=lambda *args: errors.append(args))
  load_source(root / "starpilot/common/starpilot_utilities.py", {"delete_file", "extract_zip", "update_json_file"}, namespace)
  load_source(root / "starpilot/common/starpilot_download_utilities.py",
              {"download_file", "get_remote_file_size", "verify_download"}, namespace)
  load_source(root / "starpilot/assets/theme_manager.py",
              {"ThemeManager", "THEME_COMPONENT_PARAMS", "CANCEL_DOWNLOAD_PARAM", "DOWNLOAD_PROGRESS_PARAM"}, namespace)
  for path in ("bootlogos", "steering_wheels", "theme_packs/frog/colors", "theme_packs/frog-animated/distance_icons"):
    (tmp_path / path).mkdir(parents=True)
  (tmp_path / "steering_wheels/frog.png").write_bytes(b"old wheel")
  manager = namespace["ThemeManager"].__new__(namespace["ThemeManager"])
  manager.params, manager.params_memory = Params(), Params()
  manager.downloading_theme = False
  manager.theme_sizes, manager.theme_sizes_path = {}, tmp_path / "theme_sizes.json"
  manager.session = SimpleNamespace(get=get, head=head)
  manager.sync_local_resources = lambda: None
  return SimpleNamespace(manager=manager, catalogs=catalogs, transfers=transfers, payloads=payloads, errors=errors, path=tmp_path)


@pytest.mark.parametrize("recorded_size", [None, 1])
def test_menu_refresh_lists_choices_without_downloading_existing_assets(theme, recorded_size):
  if recorded_size is not None:
    theme.manager.theme_sizes = {"wheels": {"frog": recorded_size}, "themes": {"frog": {"colors": recorded_size}}}
  theme.manager.update_themes(object(), update_assets=False)
  assert theme.catalogs == ["Distance-Icons", "Steering-Wheels", "Themes"]
  assert not theme.transfers
  assert theme.manager.params.values["DownloadableBootLogos"] == "Preview"
  assert theme.manager.params.values["ThemesDownloaded"]["themes"]["Frog"] == ["colors"]
  assert (theme.path / "steering_wheels/frog.png").read_bytes() == b"old wheel"


def test_default_maintenance_updates_assets_without_nested_downloads(theme):
  depth, maximum = 0, 0
  original = theme.manager.download_theme
  def download(*args):
    nonlocal depth, maximum
    depth += 1
    maximum = max(maximum, depth)
    try:
      return original(*args)
    finally:
      depth -= 1
  theme.manager.download_theme = download
  theme.manager.update_themes(object())
  assert maximum == 1
  assert theme.transfers.count("Steering-Wheels/frog.png") == 1
  assert (theme.path / "theme_packs/frog/colors/asset.bin").read_bytes() == b"downloaded asset"
  assert theme.manager.theme_sizes["themes"]["frog"]["colors"] == len(theme.payloads["Themes/frog/colors.zip"])


def test_selected_wheel_accepts_png_fallback_without_updating_other_assets(theme):
  theme.manager.params_memory.put("WheelToDownload", "frog")
  theme.manager.download_theme("steering_wheels", "frog", "WheelToDownload", object())
  assert theme.transfers == ["Steering-Wheels/frog.gif", "Steering-Wheels/frog.png"]
  assert len(theme.catalogs) == 3
  assert (theme.path / "steering_wheels/frog.png").read_bytes() == b"new wheel"
  assert theme.manager.theme_sizes["wheels"]["frog"] == len(b"new wheel")
  assert theme.manager.params_memory.values["ThemeDownloadProgress"] == "Downloaded!"
  assert "WheelToDownload" not in theme.manager.params_memory.values
  assert not theme.manager.downloading_theme


def test_failed_fallback_does_not_confirm_existing_png(theme):
  theme.payloads.pop("Steering-Wheels/frog.png")
  theme.manager.download_theme("steering_wheels", "frog", "WheelToDownload", object())
  assert theme.errors
  assert "ThemeDownloadProgress" not in theme.manager.params_memory.values
  assert not theme.manager.theme_sizes
  assert not theme.catalogs
  assert not theme.manager.downloading_theme


def test_rejected_png_fallback_can_retry_original_gif_from_next_origin(theme):
  theme.payloads["Steering-Wheels/frog.gif"] = b"valid gif"
  original_get, original_head = theme.manager.session.get, theme.manager.session.head
  def get(url, **kwargs):
    if "huggingface.co" in url and url.endswith(".gif"):
      theme.transfers.append("Steering-Wheels/frog.gif")
      return Response(status=404)
    return original_get(url, **kwargs)
  def head(url, **kwargs):
    if "huggingface.co" in url and url.endswith(".png"):
      return Response(payload=b"wrong remote size")
    return original_head(url, **kwargs)
  theme.manager.session.get, theme.manager.session.head = get, head
  theme.manager.download_theme("steering_wheels", "frog", "WheelToDownload", object())
  assert theme.transfers == ["Steering-Wheels/frog.gif", "Steering-Wheels/frog.png", "Steering-Wheels/frog.gif"]
  assert (theme.path / "steering_wheels/frog.gif").read_bytes() == b"valid gif"
  assert theme.manager.theme_sizes["wheels"]["frog"] == len(b"valid gif")
  assert theme.manager.params_memory.values["ThemeDownloadProgress"] == "Downloaded!"


def test_cancelled_download_does_not_publish_success_or_refresh_catalog(theme):
  theme.manager.params_memory.put("CancelThemeDownload", True)
  theme.manager.download_theme("steering_wheels", "frog", "WheelToDownload", object())
  assert theme.errors
  assert "ThemeDownloadProgress" not in theme.manager.params_memory.values
  assert not theme.manager.theme_sizes
  assert not theme.catalogs
  assert not list(theme.path.rglob("*.tmp"))
  assert not theme.manager.downloading_theme
