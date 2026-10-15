#!/usr/bin/env python3
import hashlib
import os
import requests
import tempfile
import urllib.parse

from datetime import datetime
from pathlib import Path

from openpilot.common.file_chunker import get_chunk_name, get_manifest_path
from openpilot.starpilot.common.starpilot_download_utilities import HF_BUCKET_URL, GITHUB_URL
from openpilot.starpilot.common.starpilot_utilities import delete_file, is_url_pingable

RESOURCES_REPO = os.getenv("STARPILOT_RESOURCES_REPO", "firestar5683/StarPilot-Resources")
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1\n"
MAX_MULTIPART_FILES = 100


def normalize_download_url(url: str) -> str:
  parsed = urllib.parse.urlsplit(str(url or "").strip())
  if parsed.netloc.lower() not in {"dropbox.com", "www.dropbox.com"}:
    return url
  query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
  query = [(key, value) for key, value in query if key != "dl"]
  query.append(("dl", "1"))
  return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query)))


def append_url_suffix(url: str, suffix: str) -> str:
  parsed = urllib.parse.urlsplit(str(url or "").strip())
  return urllib.parse.urlunsplit(parsed._replace(path=f"{parsed.path}{suffix}"))


def is_git_lfs_pointer(path: Path) -> bool:
  if not path.is_file() or path.stat().st_size > 1024:
    return False
  with open(path, "rb") as artifact_file:
    return artifact_file.read(len(LFS_POINTER_PREFIX)) == LFS_POINTER_PREFIX


def sha256_file(path: Path) -> str:
  digest = hashlib.sha256()
  with open(path, "rb") as artifact_file:
    for chunk in iter(lambda: artifact_file.read(1024 * 1024), b""):
      digest.update(chunk)
  return digest.hexdigest()


def get_remote_text(url: str, suppress_errors=False) -> str:
  try:
    response = requests.get(normalize_download_url(url), timeout=10)
    response.raise_for_status()
    return response.text.strip()
  except Exception as error:
    if not suppress_errors:
      handle_request_error(error, None, None, None, None)
    return ""


def check_github_rate_limit():
  try:
    response = requests.get("https://api.github.com/rate_limit")
    response.raise_for_status()
    rate_limit_info = response.json()

    remaining = rate_limit_info["rate"]["remaining"]
    print(f"GitHub API Requests Remaining: {remaining}")
    if remaining > 0:
      return True

    reset_time = datetime.utcfromtimestamp(rate_limit_info["rate"]["reset"]).strftime("%Y-%m-%d %H:%M:%S")
    print("GitHub rate limit reached")
    print(f"GitHub Rate Limit Resets At (UTC): {reset_time}")
    return False
  except requests.exceptions.RequestException as error:
    print(f"Error checking GitHub rate limit: {error}")
    return False

def download_file(cancel_param, destination, progress_param, url, download_param, params_memory, allow_unknown_size=False, suppress_errors=False):
  try:
    url = normalize_download_url(url)
    destination.parent.mkdir(parents=True, exist_ok=True)

    total_size = get_remote_file_size(url, suppress_errors=suppress_errors or allow_unknown_size)
    if total_size == 0 and not allow_unknown_size:
      if not url.endswith(".gif"):
        if suppress_errors:
          return
        print(f"Download invalid for {url} (size 0)")
        handle_error(None, "Download invalid...", "Download invalid...", download_param, progress_param, params_memory)
      return

    print(f"Starting download: {url} ({total_size} bytes)")

    with requests.get(url, stream=True, timeout=10) as response:
      response.raise_for_status()

      with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temp_file:
        temp_file_path = Path(temp_file.name)

        downloaded_size = 0
        for chunk in response.iter_content(chunk_size=16384):
          if params_memory.get_bool(cancel_param):
            temp_file_path.unlink(missing_ok=True)
            handle_error(None, "Download cancelled...", "Download cancelled...", download_param, progress_param, params_memory)
            return

          if chunk:
            temp_file.write(chunk)
            downloaded_size += len(chunk)

            if total_size > 0:
              progress = (downloaded_size / total_size) * 100
              if progress != 100:
                params_memory.put(progress_param, f"{progress:.0f}%")
              else:
                params_memory.put(progress_param, "Verifying authenticity...")
            elif downloaded_size > 0:
              params_memory.put(progress_param, "Verifying authenticity...")

        temp_file_path.rename(destination)
        print(f"Download complete: {destination.name}")
        return True

  except Exception as error:
    if suppress_errors:
      return False
    print(f"Download request error: {error}")
    handle_request_error(error, destination, download_param, progress_param, params_memory)
  return False


def download_multipart_file(cancel_param, destination, progress_param, url, download_param, params_memory):
  del download_param
  checksum_text = get_remote_text(append_url_suffix(url, ".sha256"), suppress_errors=True)
  expected_sha256 = checksum_text.split(maxsplit=1)[0].lower() if checksum_text else ""
  if len(expected_sha256) != 64 or any(char not in "0123456789abcdef" for char in expected_sha256):
    return False

  parts: list[tuple[str, int]] = []
  for index in range(MAX_MULTIPART_FILES):
    part_url = append_url_suffix(url, f".p{index:02d}")
    part_size = get_remote_file_size(part_url, suppress_errors=True)
    if part_size <= 0:
      break
    parts.append((part_url, part_size))
  if not parts:
    return False

  destination.parent.mkdir(parents=True, exist_ok=True)
  total_size = sum(part_size for _, part_size in parts)
  downloaded_size = 0
  digest = hashlib.sha256()
  temp_path = None

  try:
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output_file:
      temp_path = Path(output_file.name)
      for part_number, (part_url, expected_part_size) in enumerate(parts, start=1):
        print(f"Downloading {destination.name} part {part_number}/{len(parts)} ({expected_part_size} bytes)")
        part_size = 0
        with requests.get(normalize_download_url(part_url), stream=True, timeout=(10, 60)) as response:
          response.raise_for_status()
          for chunk in response.iter_content(chunk_size=1024 * 1024):
            if params_memory.get_bool(cancel_param):
              return False
            if not chunk:
              continue
            output_file.write(chunk)
            digest.update(chunk)
            part_size += len(chunk)
            downloaded_size += len(chunk)
            params_memory.put(progress_param, f"{(downloaded_size / total_size) * 100:.0f}%")
        if part_size != expected_part_size:
          print(f"Part size mismatch for {part_url}: {part_size} != {expected_part_size}")
          return False

    params_memory.put(progress_param, "Verifying authenticity...")
    if digest.hexdigest() != expected_sha256:
      print(f"SHA-256 mismatch for reassembled {destination.name}")
      return False

    temp_path.replace(destination)
    temp_path = None
    print(f"Reassembled and verified {destination.name}")
    return True
  except Exception as error:
    print(f"Multipart download failed for {destination.name}: {error}")
    return False
  finally:
    if temp_path is not None:
      temp_path.unlink(missing_ok=True)


def delete_chunked_artifact(destination: Path) -> None:
  """Remove a logical artifact and every native chunk belonging to it."""
  destination.unlink(missing_ok=True)
  Path(get_manifest_path(destination)).unlink(missing_ok=True)
  for chunk_path in destination.parent.glob(f"{destination.name}.chunk*of*"):
    chunk_path.unlink(missing_ok=True)


def download_chunked_file(cancel_param, destination, progress_param, url, params_memory,
                          expected_size=None, expected_sha256=None, expected_chunk_count=None):
  """Download a file_chunker artifact without reassembling it on disk."""
  manifest_text = get_remote_text(append_url_suffix(url, ".chunkmanifest"), suppress_errors=True)
  try:
    chunk_count = int(manifest_text)
  except (TypeError, ValueError):
    return False

  expected_chunk_count = int(expected_chunk_count or 0)
  if chunk_count <= 0 or chunk_count > MAX_MULTIPART_FILES:
    return False
  if expected_chunk_count and chunk_count != expected_chunk_count:
    print(f"Chunk count mismatch for {destination.name}: {chunk_count} != {expected_chunk_count}")
    return False

  expected_size = int(expected_size or 0)
  expected_sha256 = str(expected_sha256 or "").strip().lower()
  destination.parent.mkdir(parents=True, exist_ok=True)
  temporary_paths: list[Path] = []
  downloaded_size = 0
  digest = hashlib.sha256()

  try:
    chunk_urls = [append_url_suffix(url, f".chunk{index + 1:02d}of{chunk_count:02d}") for index in range(chunk_count)]
    chunk_sizes = [get_remote_file_size(chunk_url, suppress_errors=True) for chunk_url in chunk_urls]
    if any(size <= 0 for size in chunk_sizes):
      return False
    remote_size = sum(chunk_sizes)
    if expected_size and remote_size != expected_size:
      print(f"Artifact size mismatch for {destination.name}: {remote_size} != {expected_size}")
      return False

    for index, (chunk_url, chunk_size) in enumerate(zip(chunk_urls, chunk_sizes, strict=True)):
      print(f"Downloading {destination.name} chunk {index + 1}/{chunk_count} ({chunk_size} bytes)")
      with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output_file:
        temporary_path = Path(output_file.name)
        temporary_paths.append(temporary_path)
        actual_chunk_size = 0
        with requests.get(normalize_download_url(chunk_url), stream=True, timeout=(10, 60)) as response:
          response.raise_for_status()
          for chunk in response.iter_content(chunk_size=1024 * 1024):
            if params_memory.get_bool(cancel_param):
              return False
            if not chunk:
              continue
            output_file.write(chunk)
            digest.update(chunk)
            actual_chunk_size += len(chunk)
            downloaded_size += len(chunk)
            params_memory.put(progress_param, f"{(downloaded_size / remote_size) * 100:.0f}%")
      if actual_chunk_size != chunk_size:
        print(f"Chunk size mismatch for {chunk_url}: {actual_chunk_size} != {chunk_size}")
        return False

    params_memory.put(progress_param, "Verifying authenticity...")
    if expected_size and downloaded_size != expected_size:
      return False
    if expected_sha256 and digest.hexdigest() != expected_sha256:
      print(f"SHA-256 mismatch for chunked {destination.name}")
      return False

    delete_chunked_artifact(destination)
    for index, temporary_path in enumerate(temporary_paths):
      temporary_path.replace(Path(get_chunk_name(destination, index, chunk_count)))
    temporary_paths.clear()
    Path(get_manifest_path(destination)).write_text(str(chunk_count))
    print(f"Downloaded and verified {destination.name} in {chunk_count} chunks")
    return True
  except Exception as error:
    print(f"Chunked download failed for {destination.name}: {error}")
    return False
  finally:
    for temporary_path in temporary_paths:
      temporary_path.unlink(missing_ok=True)

def get_remote_file_size(url, suppress_errors=False):
  try:
    url = normalize_download_url(url)
    response = requests.head(url, headers={"Accept-Encoding": "identity"}, timeout=10, allow_redirects=True)
    response.raise_for_status()
    return int(response.headers.get("Content-Length", 0))
  except Exception as error:
    if not suppress_errors:
      handle_request_error(error, None, None, None, None)
    return 0

def get_resource_urls():
  """Return resource origins in priority order; GitHub is the only fallback."""
  urls = []
  if is_url_pingable("https://huggingface.co"):
    urls.append(HF_BUCKET_URL)
  if is_url_pingable("https://github.com") or is_url_pingable("https://api.github.com"):
    urls.append(GITHUB_URL)
  return urls


def get_repository_url():
  for url in get_resource_urls():
    return url
  return None

def handle_error(destination, error_message, error, download_param, progress_param, params_memory):
  if destination:
    delete_file(destination)

  if params_memory and progress_param:
    print(f"Error occurred: {error}")
    params_memory.put(progress_param, error_message)
    if download_param:
      # Always release the download gate: a stuck param blocks every later request.
      params_memory.remove(download_param)

def handle_request_error(error, destination, download_param, progress_param, params_memory):
  error_map = {
    requests.ConnectionError: "Connection dropped",
    requests.HTTPError: lambda error: f"Server error ({error.response.status_code})" if error.response else "Server error",
    requests.RequestException: "Network request error. Check connection",
    requests.Timeout: "Download timed out"
  }

  error_message = error_map.get(type(error), "Unexpected error")
  handle_error(destination, f"Failed: {error_message}", error, download_param, progress_param, params_memory)

def verify_download(file_path, url, allow_unknown_size=False, expected_size=None, expected_sha256=None):
  url = normalize_download_url(url)
  expected_size = int(expected_size or 0)
  expected_sha256 = str(expected_sha256 or "").strip().lower()
  remote_file_size = get_remote_file_size(url, suppress_errors=allow_unknown_size or expected_size > 0)

  if not file_path.is_file():
    print(f"File not found: {file_path}")
    return False
  if is_git_lfs_pointer(file_path):
    print(f"Git LFS pointer received instead of artifact: {file_path}")
    return False

  actual_size = file_path.stat().st_size
  if expected_size and actual_size != expected_size:
    print(f"Expected size mismatch for {file_path}: {actual_size} != {expected_size}")
    return False

  if expected_sha256:
    if sha256_file(file_path).lower() != expected_sha256:
      print(f"SHA-256 mismatch for {file_path}")
      return False

  if remote_file_size == 0 and allow_unknown_size:
    if actual_size == 0:
      print(f"File is empty: {file_path}")
      return False
    return True

  if remote_file_size == 0 and expected_size:
    return actual_size == expected_size

  if remote_file_size == 0:
    print(f"Error fetching remote size for {file_path}")
    return False

  if remote_file_size != actual_size:
    print(f"File size mismatch for {file_path}")
    return False

  return True
