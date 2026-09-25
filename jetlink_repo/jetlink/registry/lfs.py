"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

Getting a large model's ONNX by its git-lfs oid.

comma overwrites one file per model, so the commit is the only name a big
model's ONNX has. GitHub's raw host serves the LFS pointer for any commit it
holds, merged or not, and that pointer carries the oid and size the comma will
ask a jetlink server for. The bytes themselves are on comma's LFS servers,
which is GitLab and not GitHub: each is asked in turn because which one has an
object varies with the model's age.

Since openpilot #38930 (2026-09-16) a commit can ship a precompiled tinygrad
pkl instead, with no ONNX in the tree at all; Cinque Terre V3 is one. Its
subject names the export ("Use f78ed37d for the precompiled eGPU driving
model") and the ONNX is in comma's HuggingFace model repo, in the folder that
id starts. sunnypilot's model builds find it the same way. That repo speaks
the LFS batch protocol too, so it is one more endpoint to ask.

The zoompilot fork downloads through this module too, asking its own
.lfsconfig endpoint first. No openpilot imports.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from jetlink.registry.catalog import NetworkError, NotFound, RegistryError, VerifyError, http_get, http_json, is_sha256

log = logging.getLogger('jetlink.registry')

BIG_ONNX = 'big_driving_supercombo.onnx'
POINTER_URL = 'https://raw.githubusercontent.com/commaai/openpilot/{ref}/openpilot/selfdrive/modeld/models/' + BIG_ONNX
# a commit's subject without the API, whose anonymous limit a car behind CGNAT shares
COMMIT_PATCH_URL = 'https://github.com/commaai/openpilot/commit/{ref}.patch'
DRIVING_MODELS_REPO = 'commaai/openpilot_driving_models'
DRIVING_MODELS_TREE_URL = f'https://huggingface.co/api/models/{DRIVING_MODELS_REPO}/tree/main'
LFS_ENDPOINTS = (
  'https://gitlab.com/commaai/openpilot-lfs.git/info/lfs',      # every object, older and PR-branch models included
  'https://huggingface.co/commaai/openpilot-lfs.git/info/lfs',  # where comma is moving them; the current ones
  f'https://huggingface.co/{DRIVING_MODELS_REPO}.git/info/lfs',  # the exports behind a precompiled pkl
)
# an export folder is a uuid; the subject names its first eight
_EXPORT_ID = re.compile(r'\b[0-9a-f]{8}\b')
LFS_MEDIA_TYPE = 'application/vnd.git-lfs+json'
POINTER_TIMEOUT = 10.0
CONNECT_TIMEOUT = 30.0
# A pointer is 134 bytes. Anything larger is the ONNX itself, served by a host
# that resolved the LFS filter for us, and reading a gigabyte to find that out
# is not on.
POINTER_MAX = 4096
CHUNK = 4 << 20
FREE_SLACK = 64 << 20

ProgressFn = Callable[[float], None]
StopFn = Callable[[], bool]


@dataclass(frozen=True)
class Pointer:
  oid: str    # the ONNX SHA-256
  size: int


def parse_pointer_text(text: str) -> Pointer | None:
  """The oid and size in a git-lfs pointer's text, or None if it is not one."""
  if not isinstance(text, str) or len(text.encode('utf-8', 'replace')) > POINTER_MAX:
    return None
  oid = None
  size = None
  for line in text.splitlines():
    key, _, value = line.partition(' ')
    if key == 'oid':
      oid = value.removeprefix('sha256:').strip()
    elif key == 'size':
      try:
        size = int(value)
      except ValueError:
        return None
  if not is_sha256(oid) or size is None or size <= 0:
    return None
  return Pointer(oid, size)


def fetch_pointer(ref: str, timeout: float = POINTER_TIMEOUT, opener=None) -> Pointer:
  """The oid and size of the ONNX at a comma commit: in its tree, or for a
  commit that ships a precompiled pkl instead, the export its subject names."""
  try:
    text = http_get(POINTER_URL.format(ref=ref), timeout, opener, POINTER_MAX).decode('utf-8', 'replace')
  except NotFound:
    return fetch_export_pointer(ref, timeout=timeout, opener=opener)
  pointer = parse_pointer_text(text)
  if pointer is None:
    raise RegistryError(f"{ref[:10]} did not serve an lfs pointer")
  return pointer


def commit_subject(ref: str, timeout: float = POINTER_TIMEOUT, opener=None) -> str:
  """A comma commit's subject line, from the head of its patch."""
  url = COMMIT_PATCH_URL.format(ref=ref)
  lines = http_get(url, timeout, opener, POINTER_MAX).decode('utf-8', 'replace').splitlines()
  for i, line in enumerate(lines):
    if line.startswith('Subject:'):
      subject = [line.removeprefix('Subject:').strip()]
      # a long subject is folded onto indented lines; the headers end at a blank one
      for cont in lines[i + 1:]:
        if not cont[:1].isspace() or not cont.strip():
          break
        subject.append(cont.strip())
      return re.sub(r'^\[PATCH[^\]]*\]\s*', '', ' '.join(subject))
  raise RegistryError(f"{url} has no subject line")


def _tree(path: str, timeout: float, opener) -> list[dict]:
  url = DRIVING_MODELS_TREE_URL + (f"/{urllib.parse.quote(path)}?recursive=true" if path else '')
  return [e for e in http_json(url, timeout, opener, list) if isinstance(e, dict) and isinstance(e.get('path'), str)]


def fetch_export_pointer(ref: str, timeout: float = POINTER_TIMEOUT, opener=None) -> Pointer:
  """The big ONNX a precompiled-pkl commit was built from, in comma's model repo."""
  subject = commit_subject(ref, timeout=timeout, opener=opener)
  ids = list(dict.fromkeys(_EXPORT_ID.findall(subject)))
  if not ids:
    raise RegistryError(f"{ref[:10]} has no {BIG_ONNX} and its subject names no export: {subject!r}")
  folders = [e['path'] for e in _tree('', timeout, opener) if e.get('type') == 'directory']
  for export in ids:
    matches = [f for f in folders if f.startswith(export)]
    if not matches:
      continue
    if len(matches) > 1:
      raise RegistryError(f"{ref[:10]}: {export} starts {len(matches)} folders in {DRIVING_MODELS_REPO}")
    files = [e for e in _tree(matches[0], timeout, opener)
             if e.get('type') == 'file' and e['path'].rsplit('/', 1)[-1] == BIG_ONNX]
    if len(files) > 1:
      # a subject that names the checkpoint, as '1a421175-.../12864' does, picks one
      files = [f for f in files if f['path'].rsplit('/', 1)[0] in subject] or files
    if len(files) != 1:
      raise RegistryError(f"{ref[:10]}: {len(files)} copies of {BIG_ONNX} under {matches[0]}")
    lfs = files[0].get('lfs') or {}
    oid, size = lfs.get('oid'), lfs.get('size')
    if not is_sha256(oid) or not isinstance(size, int) or size <= 0:
      raise RegistryError(f"{files[0]['path']} is not an lfs object")
    log.info("%s names export %s: %s", ref[:10], export, files[0]['path'])
    return Pointer(oid, size)
  raise RegistryError(f"{ref[:10]}: no folder in {DRIVING_MODELS_REPO} for {', '.join(ids)}")


def lfs_resolve(endpoint: str, pointer: Pointer, timeout: float = CONNECT_TIMEOUT, opener=None) -> str | None:
  """Ask one LFS server for a download href, or None if it does not have it.

  A server that is down is not different from a server that lacks the object:
  either way the caller moves to the next one, so nothing raises here.
  """
  opener = opener or urllib.request.urlopen
  body = json.dumps({
    'operation': 'download',
    'transfers': ['basic'],
    'objects': [{'oid': pointer.oid, 'size': pointer.size}],
  }).encode()
  request = urllib.request.Request(f"{endpoint}/objects/batch", data=body, method='POST',
                                   headers={'Accept': LFS_MEDIA_TYPE, 'Content-Type': LFS_MEDIA_TYPE})
  try:
    with opener(request, timeout=timeout) as response:
      payload = json.loads(response.read().decode())
  except (OSError, ValueError) as e:
    log.warning("lfs batch failed at %s: %s", endpoint, e)
    return None

  for obj in (payload.get('objects') or []) if isinstance(payload, dict) else []:
    if not isinstance(obj, dict) or obj.get('oid') != pointer.oid:
      continue
    if 'error' in obj:
      log.warning("%s has no %s (%s)", endpoint, pointer.oid[:16], (obj['error'] or {}).get('message'))
      return None
    href = ((obj.get('actions') or {}).get('download') or {}).get('href')
    if href:
      return str(href)
  return None


def lfs_download(href: str, pointer: Pointer, dest: Path, progress: ProgressFn | None = None,
                 should_stop: StopFn | None = None, opener=None) -> Path:
  """Stream to a .part file, hashing as we go, and only then take the name.

  A half-written model must never sit where the next start would hand it to a
  backend to build from.
  """
  opener = opener or urllib.request.urlopen
  dest = Path(dest)
  dest.parent.mkdir(parents=True, exist_ok=True)
  free = shutil.disk_usage(dest.parent).free
  if free < pointer.size + FREE_SLACK:
    raise RegistryError(f"need {pointer.size >> 20} MB for the model, {free >> 20} MB free")

  part = dest.with_name(dest.name + '.part')
  digest = hashlib.sha256()
  written = 0
  # Whole percent only: a gigabyte at 4 MB a chunk would call this a few
  # hundred times and the callback may write a param or a socket line.
  reported = -1
  try:
    with opener(href, timeout=CONNECT_TIMEOUT) as response, open(part, 'wb') as out:
      while True:
        if should_stop is not None and should_stop():
          raise RegistryError('download cancelled')
        chunk = response.read(CHUNK)
        if not chunk:
          break
        out.write(chunk)
        digest.update(chunk)
        written += len(chunk)
        if progress is not None and pointer.size:
          percent = int(100 * written / pointer.size)
          if percent != reported:
            reported = percent
            progress(min(1.0, written / pointer.size))
  except RegistryError:
    part.unlink(missing_ok=True)
    raise
  except Exception as e:
    part.unlink(missing_ok=True)
    raise NetworkError(f"could not download {pointer.oid[:16]}: {e}") from e

  if written != pointer.size:
    part.unlink(missing_ok=True)
    raise VerifyError(f"{pointer.oid[:16]} is {written} bytes, expected {pointer.size}")
  if digest.hexdigest() != pointer.oid:
    part.unlink(missing_ok=True)
    raise VerifyError(f"downloaded bytes hash to {digest.hexdigest()[:16]}, expected {pointer.oid[:16]}")

  part.replace(dest)
  if progress is not None:
    progress(1.0)
  return dest
