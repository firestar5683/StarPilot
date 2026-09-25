"""Map virtual-environment library paths to their deployment location."""

from pathlib import PurePosixPath


def runtime_library_path(library_dir: str, build_venv: str, target_venv: str | None = None) -> str:
  if target_venv is None:
    return library_dir
  library, build, target = map(PurePosixPath, (library_dir, build_venv, target_venv))
  if not all(path.is_absolute() and ".." not in path.parts for path in (library, build, target)):
    raise ValueError("Library and virtual-environment paths must be absolute")
  return str(target / library.relative_to(build))
