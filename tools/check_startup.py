"""Read-only local manager admission check for an existing Params namespace."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from openpilot.common.params import Params
from openpilot.starpilot.state_migration import MigrationRequired, prepare_manager_start


class ExistingParams:
  def __init__(self, namespace: Path, key_types):
    self.namespace = namespace
    self.key_types = key_types

  def get_param_path(self):
    return str(self.namespace)

  def all_keys(self):
    return list(self.key_types)

  def get_type(self, key):
    return self.key_types[key.encode() if isinstance(key, str) else key]


def check_startup(params_root: Path, storage: Path) -> None:
  if not params_root.is_dir():
    raise ValueError("Existing Params namespace required")
  standard = params_root / "d"
  if standard.is_symlink() and standard.is_dir():
    namespace = standard
  elif params_root.is_symlink() or (not any(path.is_symlink() for path in params_root.iterdir()) and
                                    any(path.is_file() and path.name != ".lock" for path in params_root.iterdir())):
    namespace = params_root
  else:
    raise ValueError("Supply an existing Params namespace or a root with d; empty or named-link roots are ambiguous")
  if not storage.is_dir():
    raise ValueError("Existing recovery storage directory required")
  with TemporaryDirectory(prefix="startup-preflight-") as temporary:
    registry = Params(temporary)
    key_types = {key: registry.get_type(key) for key in registry.all_keys()}
  prepare_manager_start(ExistingParams(namespace, key_types), storage, dry_run=True)


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("params_root", type=Path)
  parser.add_argument("storage", type=Path)
  args = parser.parse_args()
  try:
    check_startup(args.params_root, args.storage)
  except (MigrationRequired, ValueError, OSError) as error:
    print(f"Startup admission rejected: {error}")
    return 1
  print("Startup admission accepted (read-only point-in-time check)")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
