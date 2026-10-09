"""Private first-boot snapshot before the existing StarPilot migrations."""
import os
from pathlib import Path
import tarfile
import tempfile

DATA = Path('/data/galaxy-ble')
ROOTS = ('/data/params', '/cache/starpilot/params', '/cache/params')


def backup_settings(data=DATA, roots=ROOTS):
  data.mkdir(parents=True, exist_ok=True, mode=0o700)
  target = data / 'settings-before-pilot.tar.gz'
  if target.exists():
    return target
  if not any(Path(root).is_dir() for root in roots):
    return None
  fd, temporary = tempfile.mkstemp(dir=data, prefix='.settings-')
  try:
    with os.fdopen(fd, 'wb') as stream:
      with tarfile.open(fileobj=stream, mode='w:gz', dereference=True) as archive:
        for root in roots:
          path = Path(root)
          if path.is_dir():
            archive.add(path, arcname=str(path).lstrip('/'))
        migration_flags = Path('/data/.starpilot_param_migrations')
        if migration_flags.is_dir():
          archive.add(migration_flags, arcname='data/.starpilot_param_migrations')
        for flag in Path('/data').glob('starpilot_*_v*'):
          if flag.is_file():
            archive.add(flag, arcname=f'data/{flag.name}')
      stream.flush()
      os.fsync(stream.fileno())
    os.link(temporary, target)
  except FileExistsError:
    pass
  finally:
    os.unlink(temporary)
  return target


if __name__ == '__main__':
  try:
    backup_settings()
  except Exception:
    print('Galaxy settings backup failed; existing settings were not changed.')
    raise SystemExit(1)
