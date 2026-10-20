import hashlib
import io
import os
import struct
import tarfile
from typing import Any
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openpilot.starpilot.soloist import package
from openpilot.starpilot.soloist.paths import Layout

BUILD = 1792173722  # 2026-10-16, from a real `soloist --version`
NOW = datetime.fromtimestamp(BUILD, UTC) + timedelta(days=1)
VERSION_LINE = f'soloist 1.3.9.32 build {BUILD} (20261016) (g440165f200) (linux/aarch64)'


def elf(machine=183, elf_class=2, interpreter=b'/lib/ld-linux-aarch64.so.1', extra=b'GLIBC_2.38\x00') -> bytes:
  header = bytearray(64)
  header[:4] = b'\x7fELF'
  header[4], header[5] = elf_class, 1
  phoff, phentsize = 64, 56
  struct.pack_into('<HH', header, 16, 3, machine)
  struct.pack_into('<Q', header, 32, phoff)
  struct.pack_into('<HH', header, 54, phentsize, 1)
  interp_offset = phoff + phentsize
  program = struct.pack('<IIQQQQQQ', 3, 4, interp_offset, 0, 0, len(interpreter) + 1, len(interpreter) + 1, 1)
  return bytes(header) + program + interpreter + b'\x00' + extra + b'\x00' * 4096


def archive(members: dict[str, bytes] | None = None, *, links: bool = False, prefix: str = '') -> bytes:
  members = members if members is not None else {'soloist': elf(), 'CHANGELOG.md': b'# Soloist', 'THIRD_PARTY_LICENSES.txt': b'MIT'}
  buffer = io.BytesIO()
  with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
    for name, data in members.items():
      info = tarfile.TarInfo(prefix + name)
      info.size = len(data)
      info.mode = 0o555
      tar.addfile(info, io.BytesIO(data))
    if links:
      info = tarfile.TarInfo('evil')
      info.type = tarfile.SYMTYPE
      info.linkname = '/etc/passwd'
      tar.addfile(info)
  return buffer.getvalue()


def write(tmp_path: Path, data: bytes) -> Path:
  path = tmp_path / 'upload.tar.gz'
  path.write_bytes(data)
  return path


def official(data: bytes):
  return lambda: (hashlib.md5(data).hexdigest(), len(data))


def run_import(layout, path, data=None, **kwargs):
  data = path.read_bytes() if data is None else data
  options: dict[str, Any] = {'digest': official(data), 'probe': lambda _exe: VERSION_LINE, 'now': NOW, **kwargs}
  return package.import_archive(layout, path, **options)


def test_read_archive_keeps_known_files_and_accepts_one_folder(tmp_path):
  files = package.read_archive(write(tmp_path, archive(prefix='soloist_release_arm64/')))
  assert set(files) == {'soloist', 'CHANGELOG.md', 'THIRD_PARTY_LICENSES.txt'}


@pytest.mark.parametrize('data,code', [
  (b'PK\x03\x04 not gzip', 'NOT_ARCHIVE'),
  (archive({'README': b'x'}), 'NO_PLAYER'),
  (archive(links=True), 'UNSAFE'),
  (archive({'../soloist': elf()}), 'UNSAFE'),
  (archive({'a/b/c/soloist': elf()}), 'NO_PLAYER'),
  (archive()[:200], 'CORRUPT'),
], ids=['not_gzip', 'no_player', 'links', 'parent_path', 'nested', 'truncated'])
def test_read_archive_rejects_unsafe_or_wrong_archives(tmp_path, data, code):
  with pytest.raises(package.ImportFailed) as error:
    package.read_archive(write(tmp_path, data))
  assert error.value.code == code


def test_read_archive_bounds_decompressed_bytes(tmp_path):
  with pytest.raises(package.ImportFailed) as error:
    package.read_archive(write(tmp_path, archive({'filler.bin': b'\x00' * (3 * 1024 * 1024), 'soloist': elf()})), max_unpacked=1024 * 1024)
  assert error.value.code == 'TOO_LARGE'


@pytest.mark.parametrize('binary,code', [
  (elf(machine=62), 'WRONG_ARCH'),
  (elf(elf_class=1), 'WRONG_ARCH'),
  (elf(interpreter=b'/lib/ld-linux-armhf.so.3'), 'INCOMPATIBLE'),
  (b'#!/bin/sh\necho hi\n' + b'\x00' * 64, 'NO_PLAYER'),
], ids=['x86_64', 'elf32', 'armhf', 'script'])
def test_check_executable(binary, code):
  with pytest.raises(package.ImportFailed) as error:
    package.check_executable(binary)
  assert error.value.code == code


def test_check_executable_glibc_requirement():
  package.check_executable(elf(), max_glibc_minor=39)
  with pytest.raises(package.ImportFailed) as error:
    package.check_executable(elf(), max_glibc_minor=35)
  assert error.value.code == 'INCOMPATIBLE'


def test_parse_version_reads_build_timestamp():
  parsed = package.parse_version(VERSION_LINE)
  assert parsed['version'] == '1.3.9.32'
  assert parsed['built'].startswith('2026-10-16')
  assert parsed['expires'].startswith('2027-01-14')
  with pytest.raises(package.ImportFailed):
    package.parse_version('soloist dev build')


def test_import_installs_and_reports_status(tmp_path):
  layout = Layout(tmp_path / 'root')
  data = archive()
  stages = []
  metadata = run_import(layout, write(tmp_path, data), progress=lambda **v: stages.append(v.get('stage')))
  assert stages == ['reading', 'unpacking', 'verifying', 'testing', 'installing']
  assert os.access(layout.current / 'soloist', os.X_OK)
  status = package.release_status(layout, now=NOW)
  assert status['installed'] and status['version'] == '1.3.9.32' and status['level'] == 'ok' and status['daysLeft'] == 89
  assert package.release_status(layout, now=NOW + timedelta(days=80))['level'] == 'soon'
  assert package.release_status(layout, now=NOW + timedelta(days=95))['expired'] is True
  assert metadata['sha256'] == hashlib.sha256(data).hexdigest()


def test_import_refuses_files_that_do_not_match_spotify(tmp_path):
  layout = Layout(tmp_path / 'root')
  path = write(tmp_path, archive())
  with pytest.raises(package.ImportFailed) as error:
    run_import(layout, path, digest=lambda: ('0' * 32, path.stat().st_size))
  assert error.value.code == 'NOT_OFFICIAL'
  assert not package.release_status(layout)['installed']
  assert not any(layout.releases.iterdir()) if layout.releases.exists() else True


def test_import_without_internet_needs_a_previously_verified_build(tmp_path):
  layout = Layout(tmp_path / 'root')
  data = archive()
  def offline():
    raise package.ImportFailed('offline', 'OFFLINE')
  with pytest.raises(package.ImportFailed) as error:
    run_import(layout, write(tmp_path, data), digest=offline)
  assert error.value.code == 'OFFLINE'
  run_import(layout, write(tmp_path, data))
  run_import(layout, write(tmp_path, data), digest=offline)  # reinstalling the same verified build works offline


def test_probe_is_only_run_after_verification_and_expiry_is_enforced(tmp_path):
  layout = Layout(tmp_path / 'root')
  probed = []
  path = write(tmp_path, archive())
  with pytest.raises(package.ImportFailed):
    run_import(layout, path, digest=lambda: ('0' * 32, 1), probe=lambda exe: probed.append(exe) or VERSION_LINE)
  assert probed == []
  with pytest.raises(package.ImportFailed) as error:
    run_import(layout, write(tmp_path, archive()), now=NOW + timedelta(days=100))
  assert error.value.code == 'EXPIRED'
  assert not package.release_status(layout)['installed']


def test_update_keeps_previous_and_rollback_restores_it(tmp_path):
  layout = Layout(tmp_path / 'root')
  run_import(layout, write(tmp_path, archive()))
  first = os.path.realpath(layout.current)
  run_import(layout, write(tmp_path, archive({'soloist': elf(extra=b'GLIBC_2.38\x00new build')})))
  assert os.path.realpath(layout.current) != first
  assert os.path.realpath(layout.previous) == first
  assert len(list(layout.releases.iterdir())) == 2
  assert package.rollback(layout)
  assert os.path.realpath(layout.current) == first
  assert not layout.previous.exists()


def test_activation_requires_park(tmp_path):
  layout = Layout(tmp_path / 'root')
  with pytest.raises(package.ImportFailed) as error:
    run_import(layout, write(tmp_path, archive()), may_activate=lambda: False)
  assert error.value.code == 'DRIVING'
  assert not package.release_status(layout)['installed']


def test_import_job_reports_failure_and_removes_upload(tmp_path):
  layout = Layout(tmp_path / 'root')
  job = package.ImportJob(layout, digest=lambda: ('0' * 32, 1), probe=lambda _exe: VERSION_LINE, now=NOW)
  path = write(tmp_path, archive())
  job.start(path=path, enabled=lambda: True)
  job.thread.join(timeout=5)
  assert job.status()['state'] == 'failed' and job.status()['code'] == 'NOT_OFFICIAL'
  assert not path.exists()
