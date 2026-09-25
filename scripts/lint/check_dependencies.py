#!/usr/bin/env python3
import sys
import tomllib
import importlib.metadata
from pathlib import Path


DIRECT_LIMITS = {"baseline": 37, "dev": 3, "safety": 5}
TOOLING_PACKAGES = frozenset({
  "colorlog", "cppcheck", "execnet", "gcovr", "iniconfig", "jinja2", "lxml", "markupsafe",
  "pluggy", "pygments", "pytest", "pytest-mock", "pytest-xdist", "tree-sitter", "tree-sitter-c",
})
BASELINE_INSTALLED_LIMIT = 65
TOOLING_INSTALLED_LIMIT = 15


def direct_dependency_counts(project: dict) -> dict[str, int]:
  extras = project["optional-dependencies"]
  return {
    "baseline": len(project["dependencies"]) + sum(len(deps) for name, deps in extras.items() if name not in ("dev", "safety")),
    "dev": len(extras.get("dev", ())),
    "safety": len(extras.get("safety", ())),
  }


def direct_dependencies_within_limits(project: dict) -> bool:
  counts = direct_dependency_counts(project)
  return all(counts[name] <= limit for name, limit in DIRECT_LIMITS.items())


def installed_dependency_counts(packages: set[str], tooling_names: frozenset[str] = TOOLING_PACKAGES) -> tuple[int, int]:
  tooling = len(packages & tooling_names)
  return len(packages) - tooling, tooling


def installed_dependencies_within_limits(packages: set[str], tooling_names: frozenset[str] = TOOLING_PACKAGES) -> bool:
  baseline, tooling = installed_dependency_counts(packages, tooling_names)
  return baseline <= BASELINE_INSTALLED_LIMIT and tooling <= TOOLING_INSTALLED_LIMIT


def main() -> int:
  if sys.prefix == sys.base_prefix:
    print("Dependency checks require a virtual environment. Run tools/op.sh setup first.")
    return 1

  project = tomllib.loads((Path(__file__).resolve().parents[2] / "pyproject.toml").read_text())["project"]
  direct = direct_dependency_counts(project)
  # Count each installed package once, including transitive dependencies and all extras.
  packages = {dist.metadata["Name"].lower().replace("_", "-") for dist in importlib.metadata.distributions()}
  installed_baseline, installed_tooling = installed_dependency_counts(packages)
  # Logical file sizes avoid filesystem block-size differences. Don't follow links to the interpreter or source tree.
  size = sum(path.stat().st_size for path in Path(sys.prefix).rglob("*") if not path.is_symlink() and path.is_file())

  """
    This test prevents our depency footprint from growing.
    These values are *not* intended to be increased, and we
    expect to strictly drive these down over time.
  """
  failed = not direct_dependencies_within_limits(project) or not installed_dependencies_within_limits(packages)
  for name, limit in DIRECT_LIMITS.items():
    print(f"Direct dependencies ({name}): {direct[name]} (limit: {limit})")
  print(f"Installed dependencies (baseline): {installed_baseline} (limit: {BASELINE_INSTALLED_LIMIT})")
  print(f"Installed dependencies (CI tooling): {installed_tooling} (limit: {TOOLING_INSTALLED_LIMIT})")
  for name, value, limit in (
    ("Venv size (MiB)", size / 1024**2, 550),
  ):
    print(f"{name}: {value:g} (limit: {limit})")
    failed |= value > limit
  return int(failed)


if __name__ == "__main__":
  raise SystemExit(main())
