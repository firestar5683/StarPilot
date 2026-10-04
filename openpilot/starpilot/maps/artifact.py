"""Standard-library checks shared by Mapd packaging and launch preflight."""

import hashlib
import json
from pathlib import Path
import struct
from typing import BinaryIO


def source_digest(source: Path) -> str:
  files = {path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
           for path in source.rglob('*') if path.is_file() and path.name != '.DS_Store' and
           path.relative_to(source).parts[0] not in ('.git', 'build', 'media', 'offline')}
  return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def elf_arm64_static_file(file: BinaryIO) -> bool:
  """Check the actual ELF target and absence of a dynamic interpreter."""
  file.seek(0)
  header = file.read(64)
  if len(header) != 64 or header[:4] != b'\x7fELF' or header[4] != 2 or header[5] != 1:
    return False
  if struct.unpack_from('<H', header, 18)[0] != 183:  # EM_AARCH64
    return False
  program_offset = struct.unpack_from('<Q', header, 32)[0]
  entry_size = struct.unpack_from('<H', header, 54)[0]
  entry_count = struct.unpack_from('<H', header, 56)[0]
  if entry_size < 56 or entry_count == 0 or entry_count > 128:
    return False
  if program_offset > 1 << 32 or entry_size * entry_count > 1 << 20:
    return False
  file.seek(program_offset)
  for _ in range(entry_count):
    entry = file.read(entry_size)
    if len(entry) != entry_size:
      return False
    if struct.unpack_from('<I', entry)[0] in (2, 3):  # PT_DYNAMIC, PT_INTERP
      return False
  return True


def elf_arm64_static(path: Path) -> bool:
  with path.open('rb') as file:
    return elf_arm64_static_file(file)
