import importlib.util
import json
import os
import zipfile
from pathlib import Path

import pytest


def _load_patch_module():
  path = Path(__file__).resolve().parent / "patch_system_reset_image.py"
  spec = importlib.util.spec_from_file_location("patch_system_reset_image_under_test", path)
  assert spec is not None and spec.loader is not None
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


patch_image = _load_patch_module()


def test_only_version_runtime_packages_and_factory_install_payloads_are_mutable():
  assert patch_image.ALLOWED_IMAGE_MUTATIONS == {
    patch_image.VERSION_PATH_IN_IMAGE,
    *patch_image.STAR_PILOT_DEPENDENCY_PATHS,
    *patch_image.LEGACY_RUNTIME_LIBRARY_PATHS,
    patch_image.SETUP_PATH_IN_IMAGE,
    patch_image.INSTALLER_PATH_IN_IMAGE,
  }
  assert set(patch_image.C3_DEPENDENCY_PATHS) < set(patch_image.STAR_PILOT_DEPENDENCY_PATHS)
  assert len(patch_image.LEGACY_RUNTIME_LIBRARY_PATHS) == 10
  assert len(patch_image.LEGACY_RUNTIME_LIBRARY_PATHS) == len(set(patch_image.LEGACY_RUNTIME_LIBRARY_PATHS))


def test_upstream_profile_covers_factory_reset_and_runtime_paths():
  assert patch_image.UPSTREAM_VERSION == "19.6"
  assert patch_image.UPSTREAM_RAW_SHA256 == "5b6ce7965904a157fd3a134ccfcb854f9ca5c1cc2a26b7cb80a4fa4e1cc4aaa3"
  assert set(patch_image.UPSTREAM_REQUIRED_VENV_PATHS) == {"capnp", "numpy", "Crypto", "tqdm", "raylib"}
  assert set(patch_image.REQUIRED_VENV_PATHS) == {
    "crcmod", "serial", "kaitaistruct", "cv2", "mapbox_earcut", "jsonrpc", "xattr", "onnx",
    "aiohttp", "pyaudio", "capnp", "numpy", "Crypto", "tqdm", "raylib",
  }
  assert patch_image.CANDIDATE_SITE_PACKAGES_COUNT == (
    patch_image.UPSTREAM_SITE_PACKAGES_COUNT + len(patch_image.STAR_PILOT_DEPENDENCY_PATHS)
  )
  assert len(patch_image.STAR_PILOT_DEPENDENCY_PATHS) == len(set(patch_image.STAR_PILOT_DEPENDENCY_PATHS))
  assert set(patch_image.PROTECTED_PAYLOAD_HASHES) >= {
    "/etc/NetworkManager/NetworkManager.conf",
    "/lib/systemd/system/NetworkManager.service",
    "/usr/comma/updater",
    "/usr/comma/reset",
    "/usr/comma/comma.sh",
    "/usr/comma/magic.py",
  }
  assert set(patch_image.UPSTREAM_FACTORY_INSTALL_HASHES) == {"/usr/comma/installer", "/usr/comma/setup"}
  assert set(patch_image.PROTECTED_PAYLOAD_HASHES).isdisjoint(patch_image.UPSTREAM_FACTORY_INSTALL_HASHES)


@pytest.mark.parametrize("version", ["19.6.1", "19.6.5", "19.6.99"])
def test_target_version_accepts_starpilot_revision(version):
  assert patch_image.validate_target_version(version) == version


@pytest.mark.parametrize("version", ["19.6", "19.6.0", "19.7.1", "20.6.1", "latest"])
def test_target_version_rejects_non_revision(version):
  with pytest.raises(RuntimeError):
    patch_image.validate_target_version(version)


def test_write_version_fails_closed_if_allowlist_changes(tmp_path, monkeypatch):
  monkeypatch.setattr(patch_image, "ALLOWED_IMAGE_MUTATIONS", frozenset({"/VERSION", "/usr/comma/setup"}))
  with pytest.raises(RuntimeError, match="allowlist"):
    patch_image.write_version("debugfs", tmp_path / "system.img", tmp_path / "VERSION")


def test_add_path_to_image_preserves_runtime_library_symlink(tmp_path, monkeypatch):
  target = tmp_path / "libavformat.so.58.29.100"
  target.write_bytes(b"ELF")
  source = tmp_path / "libavformat.so.58"
  source.symlink_to(target.name)
  calls = []

  monkeypatch.setattr(patch_image, "image_path_exists", lambda *_args: False)
  monkeypatch.setattr(patch_image, "ensure_image_directory", lambda *_args: None)

  def fake_run_debugfs(_debugfs, _image, request, *, write=False):
    calls.append((request, write))
    if request.startswith("stat "):
      return 'Inode: 1 Type: symlink\nFast link dest: "libavformat.so.58.29.100"'
    return ""

  monkeypatch.setattr(patch_image, "run_debugfs", fake_run_debugfs)
  patch_image.add_path_to_image("debugfs", tmp_path / "system.img", source, "/usr/local/lib/libavformat.so.58")

  assert ("symlink /usr/local/lib/libavformat.so.58 libavformat.so.58.29.100", True) in calls
  assert not any(request.startswith("write ") for request, _write in calls)


def _setup_source(member: str) -> str:
  connectivity = (
    'request = urllib.request.Request(OPENPILOT_URL, method="HEAD")'
    if member.endswith("mici_setup.py")
    else "urllib.request.urlopen(OPENPILOT_URL, timeout=2.0)"
  )
  labels = (
    'LargerSlider("slide to install\\nopenpilot", use_openpilot_callback)\n'
    'BigPillButton("install openpilot", green=True)\n'
    'set_text("install openpilot" if not custom_software else "choose software")'
    if member.endswith("mici_setup.py")
    else 'ButtonRadio("openpilot", self.checkmark)'
  )
  if member.endswith("mici_setup.py"):
    not_elf = 'self._download_failed_reason = "No custom software found at this URL: " + self.download_url.replace("https://", "", 1)'
    http_error = 'self._download_failed_reason = "http"'
    generic_error = 'self._download_failed_reason = "Invalid URL: " + self.download_url.replace("https://", "", 1)'
  else:
    not_elf = 'self.download_failed(self.download_url, "No custom software found at this URL.")'
    http_error = 'self.download_failed(self.download_url, "http")'
    generic_error = (
      'error_msg = "Ensure the entered URL is valid, and the device\'s internet connection is good."\n'
      '      self.download_failed(self.download_url, error_msg)'
    )
  return f'''OPENPILOT_URL = "https://openpilot.comma.ai"
{connectivity}
{labels}
  def download(self, url: str):
    # autocomplete incomplete URLs
    if re.match("^([^/.]+)/([^/]+)$", url):
      url = f"https://installer.comma.ai/{{url}}"

    parsed = urlparse(url, scheme='https')
    self.download_url = (urlparse(f"https://{{url}}") if not parsed.netloc else parsed).geturl()

    try:
      import tempfile

      headers = {{"User-Agent": "test"}}
      req = urllib.request.Request(self.download_url, headers=headers)

      with open(tmpfile, 'wb') as f, urllib.request.urlopen(req, timeout=30) as response:
        total_size = int(response.headers.get('content-length', 0))
      is_elf = True
      if not is_elf:
        {not_elf}
      with open(INSTALLER_URL_PATH, "w") as f:
        f.write(self.download_url)
    except urllib.error.HTTPError as e:
      {http_error}
    except Exception:
      {generic_error}
'''


def test_patch_setup_zipapp_preserves_prefix_and_custom_flow(tmp_path):
  source = tmp_path / "setup"
  source.write_bytes(b"#!/usr/bin/env python3\n")
  with zipfile.ZipFile(source, "a") as setup_zip:
    for member in patch_image.SETUP_SOURCE_MEMBERS:
      setup_zip.writestr(member, _setup_source(member))
      cache_member = str(Path(member).parent / "__pycache__" / f"{Path(member).stem}.cpython-312.pyc")
      setup_zip.writestr(cache_member, b"stale")
    setup_zip.writestr("unchanged.txt", b"upstream")
  os.chmod(source, 0o755)

  destination = tmp_path / "setup.patched"
  patch_image.patch_setup_zipapp(source, destination)

  assert destination.read_bytes().startswith(b"#!/usr/bin/env python3\n")
  assert destination.stat().st_mode & 0o777 == 0o755
  with zipfile.ZipFile(destination) as setup_zip:
    assert setup_zip.read("unchanged.txt") == b"upstream"
    assert not any(patch_image.is_setup_cache_member(name) for name in setup_zip.namelist())
    mici = setup_zip.read(patch_image.SETUP_SOURCE_MEMBERS[0]).decode()
    tici = setup_zip.read(patch_image.SETUP_SOURCE_MEMBERS[1]).decode()
  assert 'OPENPILOT_URL = "file:///usr/comma/installer"' in mici
  assert 'LargerSlider("slide to install\\nStarPilot"' in mici
  assert "urllib.request.Request(CONNECTIVITY_URL" in mici
  assert 'ButtonRadio("StarPilot"' in tici
  assert "urllib.request.urlopen(CONNECTIVITY_URL" in tici
  for setup_source in (mici, tici):
    assert "patch_bundled_installer(tmpfile, *self.bundled_installer_target)" in setup_source
    assert "install_bundled_installer(*bundled_target, self.installer_url)" in setup_source
    assert 'self.bundled_installer_target = (("firestar5683", "StarPilot") if url == OPENPILOT_URL else None)' in setup_source
    assert "self.installer_url = (" in setup_source
    assert "url = OPENPILOT_URL" in setup_source
    assert "f.write(self.installer_url)" in setup_source
    assert 'open("/usr/comma/installer", "rb")' in setup_source
    assert "self.download_url == OPENPILOT_URL" in setup_source
    assert 'url = f"https://installer.comma.ai/{url}"' not in setup_source


def test_patch_installer_binary_keeps_elf_layout_and_targets_starpilot(tmp_path):
  source = tmp_path / "installer"
  source.write_bytes(
    b"\x7fELF" +
    b"https://github.com/commaai/openpilot.git?" + b" " * 64 + b"\0" +
    b"release3?" + b" " * 64 + b"\0tail"
  )
  os.chmod(source, 0o755)
  destination = tmp_path / "installer.patched"

  patch_image.patch_installer_binary(source, destination)

  assert destination.stat().st_size == source.stat().st_size
  assert destination.stat().st_mode & 0o777 == 0o755
  data = destination.read_bytes()
  assert data.count(b"https://github.com/firestar5683/openpilot.git?") == 1
  assert data.count(b"StarPilot?") == 1
  assert b"commaai/openpilot" not in data


def test_update_manifest_changes_only_system_entry():
  original = [
    {"name": "boot", "url": "custom-boot", "hash": "boot-hash"},
    {"name": "system", "url": "old", "hash": "old", "alt": {"url": "old-alt"}},
  ]
  updated = patch_image.update_manifest_system_entry(original, "hosted", "new-hash", 123)
  assert updated[0] == original[0]
  assert updated[1] == {
    "name": "system",
    "url": "hosted",
    "hash": "new-hash",
    "hash_raw": "new-hash",
    "size": 123,
    "sparse": False,
    "full_check": False,
    "has_ab": True,
    "ondevice_hash": "new-hash",
  }
  assert json.dumps(original)


def test_protected_payload_validation_reports_any_drift():
  patch_image.validate_protected_payloads(dict(patch_image.PROTECTED_PAYLOAD_HASHES))
  changed = dict(patch_image.PROTECTED_PAYLOAD_HASHES)
  changed["/usr/comma/reset"] = "0" * 64
  with pytest.raises(RuntimeError, match="/usr/comma/reset"):
    patch_image.validate_protected_payloads(changed)
