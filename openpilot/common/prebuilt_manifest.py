import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


RECEIPT = 'prebuilt.json'
RUNTIME_ROOTS = ('openpilot/system/ui/', 'openpilot/selfdrive/ui/', 'openpilot/starpilot/ui/',
                 'openpilot/starpilot/software/', 'openpilot/starpilot/galaxy/')


def protected(path):
  if path in ('prebuilt', RECEIPT):
    return False
  if path.endswith('.py') and path.startswith(RUNTIME_ROOTS):
    return False
  if path.startswith('openpilot/starpilot/galaxy/') and path.endswith(('.html', '.css', '.js', '.svg', '.png', '.jpg', '.woff2')):
    return False
  return True


def inventory_digest(entries):
  inventory = sorted((path, mode, blob) for path, mode, blob in entries if protected(path))
  return hashlib.sha256(json.dumps(inventory, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def revision_digest(git, revision):
  entries = []
  for record in git('ls-tree', '-rz', '--full-tree', revision).split('\0'):
    if record:
      metadata, path = record.split('\t', 1)
      mode, kind, blob = metadata.split()
      if kind != 'blob':
        raise ValueError('Prebuilt inventory contains non-file source')
      entries.append((path, mode, blob))
  return inventory_digest(entries)


def valid_receipt(git, revision):
  if git('ls-tree', revision, '--', RECEIPT).strip().split()[:1] != ['100644']:
    return False
  try:
    receipt = json.loads(git('show', f'{revision}:{RECEIPT}'))
    return (type(receipt) is dict and type(receipt.get('schema_version')) is int and receipt['schema_version'] == 1 and
            receipt.get('protected_inventory_sha256') == revision_digest(git, revision))
  except (ValueError, TypeError, KeyError):
    return False


def write_receipt(repo):
  repo = Path(repo).resolve()
  def git(*args, input=None):
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(repo), *args],
                                   input=input, timeout=30).decode()
  entries = []
  regular = []
  for record in git('ls-files', '--stage', '-z').split('\0'):
    if not record:
      continue
    metadata, path = record.split('\t', 1)
    indexed_mode, _, stage = metadata.split()
    if stage != '0' or indexed_mode == '160000':
      raise ValueError('Prebuilt source has unresolved or nested Git entries')
    if not protected(path):
      continue
    file = repo / path
    info = file.lstat()
    if stat.S_ISLNK(info.st_mode):
      mode = '120000'
      blob = git('hash-object', '--stdin', input=os.fsencode(os.readlink(file))).strip()
    elif stat.S_ISREG(info.st_mode):
      mode = '100755' if info.st_mode & 0o111 else '100644'
      regular.append((path, mode))
      continue
    else:
      raise ValueError('Prebuilt source contains a non-regular file')
    entries.append((path, mode, blob))
  for offset in range(0, len(regular), 256):
    batch = regular[offset:offset + 256]
    blobs = git('hash-object', '--no-filters', '--', *(path for path, _ in batch)).splitlines()
    if len(blobs) != len(batch):
      raise ValueError('Prebuilt source hashing was incomplete')
    entries.extend((path, mode, blob) for (path, mode), blob in zip(batch, blobs, strict=True))
  receipt = dict(schema_version=1, protected_inventory_sha256=inventory_digest(entries))
  temporary = repo / (RECEIPT + '.tmp')
  try:
    temporary.write_text(json.dumps(receipt, sort_keys=True) + '\n')
    os.replace(temporary, repo / RECEIPT)
  finally:
    temporary.unlink(missing_ok=True)
  return receipt


if __name__ == '__main__':
  write_receipt(sys.argv[1])
