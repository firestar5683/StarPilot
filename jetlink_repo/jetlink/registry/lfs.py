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

Since openpilot #38930 a commit can ship a precompiled tinygrad
pkl instead, with no ONNX in the tree at all; Cinque Terre V3 is one. Its
subject names the export ("Use f78ed37d for the precompiled eGPU driving
model") and the ONNX is in comma's HuggingFace model repo, in the folder that
id starts. sunnypilot's model builds find it the same way. That repo speaks
the LFS batch protocol too, so it is one more endpoint to ask.

Not every such commit names its export. ResAction's pull request (#39037)
adds the ONNX in one commit and replaces it with the pkl in the
next, subject "compiled", and a squash merge's subject only names the pull
request. The pointer is still in a diff: the one the commit's own patch
deletes, or the last one its pull request's patch carries.

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
# every commit of a pull request, one patch after another, for a squash merge's subject
PULL_PATCH_URL = 'https://github.com/commaai/openpilot/pull/{number}.patch'
# how much of a patch is read for the pointers in its diffs; a model commit's is 3 KB
PATCH_MAX = 256 << 10
# the diff header of the big ONNX, wherever the tree keeps selfdrive
_ONNX_DIFF = re.compile(r'^diff --git a/\S*selfdrive/modeld/models/' + re.escape(BIG_ONNX) + r' ')
# a squash merge's subject ends with its pull request
_PULL = re.compile(r'\(#([0-9]+)\)$')
DRIVING_MODELS_REPO = 'commaai/openpilot_driving_models'
DRIVING_MODELS_TREE_URL = f'https://huggingface.co/api/models/{DRIVING_MODELS_REPO}/tree/main'
LFS_ENDPOINTS = (
  'https://gitlab.com/commaai/openpilot-lfs.git/info/lfs',      # every object, older and PR-branch models included
  'https://huggingface.co/commaai/openpilot-lfs.git/info/lfs',  # where comma is moving them; the current ones
  f'https://huggingface.co/{DRIVING_MODELS_REPO}.git/info/lfs',  # the exports behind a precompiled pkl
)
# an export folder is a uuid; the subject names its first eight
_EXPORT_ID = re.compile(r'\b[0-9a-f]{8}\b')
# how comma's model commits name an export: the whole uuid, or its first eight
# and the checkpoint ('8d736683/12864'). A bare eight could be any hex word
_NAMED_EXPORT = r'\b{}[-/]'
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
  commit that ships a precompiled pkl instead, the ONNX it was built from."""
  try:
    text = http_get(POINTER_URL.format(ref=ref), timeout, opener, POINTER_MAX).decode('utf-8', 'replace')
  except NotFound:
    return fetch_export_pointer(ref, timeout=timeout, opener=opener)
  pointer = parse_pointer_text(text)
  if pointer is None:
    raise RegistryError(f"{ref[:10]} did not serve an lfs pointer")
  return pointer


def patch_subjects(text: str) -> list[str]:
  """Every commit's subject in a patch, in order: one for a commit's, one per
  commit for a pull request's."""
  lines = text.splitlines()
  subjects = []
  for i, line in enumerate(lines):
    if line.startswith('Subject:'):
      subject = [line.removeprefix('Subject:').strip()]
      # a long subject is folded onto indented lines; the headers end at a blank one
      for cont in lines[i + 1:]:
        if not cont[:1].isspace() or not cont.strip():
          break
        subject.append(cont.strip())
      subjects.append(re.sub(r'^\[PATCH[^\]]*\]\s*', '', ' '.join(subject)))
  return subjects


def diff_pointer(text: str) -> Pointer | None:
  """The big ONNX's pointer in a patch's diffs, the last one wins: the pointer a
  diff gives the file, or for a diff that deletes it, the pointer it had. A
  commit that swaps the ONNX for a pkl deletes the ONNX the pkl was built from."""
  found = None
  section: list[str] | None = None

  def close():
    nonlocal found
    if section is not None:
      added = parse_pointer_text('\n'.join(x[1:] for x in section if x.startswith('+') and not x.startswith('+++')))
      removed = parse_pointer_text('\n'.join(x[1:] for x in section if x.startswith('-') and not x.startswith('---')))
      found = added or removed or found

  for line in text.splitlines():
    # each diff, and each commit of a pull request's patch, ends the one before
    if line.startswith(('diff --git ', 'From ')):
      close()
      section = [] if _ONNX_DIFF.match(line) else None
    elif section is not None:
      section.append(line)
  close()
  return found


def commit_subject(ref: str, timeout: float = POINTER_TIMEOUT, opener=None) -> str:
  """A comma commit's subject line, from the head of its patch."""
  url = COMMIT_PATCH_URL.format(ref=ref)
  subjects = patch_subjects(http_get(url, timeout, opener, POINTER_MAX).decode('utf-8', 'replace'))
  if not subjects:
    raise RegistryError(f"{url} has no subject line")
  return subjects[0]


def _tree(path: str, timeout: float, opener) -> list[dict]:
  url = DRIVING_MODELS_TREE_URL + (f"/{urllib.parse.quote(path)}?recursive=true" if path else '')
  return [e for e in http_json(url, timeout, opener, list) if isinstance(e, dict) and isinstance(e.get('path'), str)]


def fetch_export_pointer(ref: str, timeout: float = POINTER_TIMEOUT, opener=None) -> Pointer:
  """The big ONNX a precompiled-pkl commit was built from. In turn: the export
  its subject names, in comma's model repo; the pointer its own diff deletes;
  and for a squash merge, the last pointer its pull request carried, or the
  export one of that pull request's commits names.

  The newest export named wins: a pull request's commits are in order, and
  Mountain Dew's (#39047) named three before the one it shipped. One that is
  not in the model repo yet stops the search rather than falling back to an
  older one, a different model."""
  url = COMMIT_PATCH_URL.format(ref=ref)
  patch = http_get(url, timeout, opener, PATCH_MAX).decode('utf-8', 'replace')
  subjects = patch_subjects(patch)
  if not subjects:
    raise RegistryError(f"{url} has no subject line")
  subject = subjects[0]
  ids = _newest_first(subject)
  pointer, missing = _export_pointer(ref, ids, subject, timeout, opener)
  if pointer is not None:
    return pointer
  tried = [f"its subject {_not_uploaded(missing)}" if missing else f"no folder in {DRIVING_MODELS_REPO} for {', '.join(ids)}" if ids
           else 'its subject names no export']
  if (pointer := diff_pointer(patch)) is not None:
    log.info("%s deletes %s %s", ref[:10], BIG_ONNX, pointer.oid[:16])
    return pointer
  tried.append(f"its diff has no {BIG_ONNX}")
  if (pull := _PULL.search(subject)) is not None:
    number = pull.group(1)
    pull_patch = http_get(PULL_PATCH_URL.format(number=number), timeout, opener, PATCH_MAX).decode('utf-8', 'replace')
    if (pointer := diff_pointer(pull_patch)) is not None:
      log.info("%s merged #%s, whose last %s is %s", ref[:10], number, BIG_ONNX, pointer.oid[:16])
      return pointer
    if missing is None:  # an export the subject names and the repo lacks stops the search here too
      pull_subjects = ' '.join(patch_subjects(pull_patch))
      pull_ids = [i for i in _newest_first(pull_subjects) if i not in ids]
      pointer, pull_missing = _export_pointer(ref, pull_ids, pull_subjects, timeout, opener)
      if pointer is not None:
        return pointer
      tried.append(f"pull request #{number} {_not_uploaded(pull_missing)}" if pull_missing else f"nor does pull request #{number}")
  raise RegistryError(f"{ref[:10]} has no {BIG_ONNX}: {'; '.join(tried)} ({subject!r})")


def _newest_first(text: str) -> list[str]:
  """The eight-hex ids `text` names, the last mention first."""
  return list(dict.fromkeys(reversed(_EXPORT_ID.findall(text))))


def _not_uploaded(export: str) -> str:
  return f"names export {export}, which is not in {DRIVING_MODELS_REPO} yet"


def _export_pointer(ref: str, ids: list[str], subject: str, timeout: float, opener) -> tuple[Pointer | None, str | None]:
  """The ONNX in the first export folder one of `ids` starts, and None; or
  None and the first id `subject` names as an export that has no folder, where
  the search stops; or None and None when no id has a folder."""
  if not ids:
    return None, None
  folders = [e['path'] for e in _tree('', timeout, opener) if e.get('type') == 'directory']
  for export in ids:
    matches = [f for f in folders if f.startswith(export)]
    if not matches:
      if re.search(_NAMED_EXPORT.format(export), subject):
        return None, export
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
    return Pointer(oid, size), None
  return None, None


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
  backend to build from. A transfer that stalls or is stopped keeps its .part,
  and the next call carries on from it with a Range request: 755 MB over a
  car's connection need not arrive in one go. Only bytes that prove wrong are dropped.
  """
  opener = opener or urllib.request.urlopen
  dest = Path(dest)
  dest.parent.mkdir(parents=True, exist_ok=True)
  part = dest.with_name(dest.name + '.part')
  digest = hashlib.sha256()
  written = _resume_from(part, pointer.size, digest)
  free = shutil.disk_usage(dest.parent).free
  if free < pointer.size - written + FREE_SLACK:
    raise RegistryError(f"need {(pointer.size - written) >> 20} MB more for the model, {free >> 20} MB free")

  # Whole percent only: a gigabyte at 4 MB a chunk would call this a few
  # hundred times and the callback may write a param or a socket line.
  reported = -1
  if written < pointer.size:
    request = urllib.request.Request(href, headers={'Range': f'bytes={written}-'}) if written else href
    try:
      with opener(request, timeout=CONNECT_TIMEOUT) as response:
        if written and response.status != 206:
          # the server ignored the Range and sends the whole object
          log.warning("%s: no partial content, downloading from the start", pointer.oid[:16])
          digest, written = hashlib.sha256(), 0
        with open(part, 'ab' if written else 'wb') as out:
          while True:
            if should_stop is not None and should_stop():
              raise RegistryError('download stopped')
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
      raise
    except Exception as e:
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


def _resume_from(part: Path, size: int, digest) -> int:
  """How much of the model an earlier attempt left in `part`, hashed into
  `digest`; 0, with the file gone, for anything that cannot be a prefix."""
  try:
    have = part.stat().st_size
  except OSError:
    return 0
  if have > size:
    part.unlink(missing_ok=True)
    return 0
  buf = bytearray(CHUNK)
  view = memoryview(buf)
  with open(part, 'rb') as f:
    while n := f.readinto(buf):
      digest.update(view[:n])
  return have
