#!/usr/bin/env python3
import argparse
import codecs
import os
import pickle
import re
import shutil
import subprocess
import sys

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_ROOT = Path("/data/openpilot/uncompiledmodels")
DEFAULT_OUTPUT_ROOT = Path("/data/openpilot/compiledmodels")
COMPILE_SCRIPT = REPO_ROOT / "tinygrad_repo/examples/openpilot/compile3.py"

COMPONENT_ALIASES = {
  "driving_off_policy": ("driving_off_policy", "off_policy", "offpolicy"),
  "driving_policy": ("driving_policy", "policy"),
  "driving_vision": ("driving_vision", "vision"),
}
REQUIRED_COMPONENTS = {"driving_policy", "driving_vision"}


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Compile staged ONNX driving models into tinygrad pkls without touching selfdrive/modeld/models.",
  )
  parser.add_argument("--model", help="Output model key, for example sc2.")
  parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_ROOT, help="Directory containing staged ONNX files. Flat root files like driving_policy.onnx are preferred.")
  parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT, help="Directory for compiled tinygrad pkls and metadata.")
  parser.add_argument("--list", action="store_true", help="List detected staged models and exit.")
  parser.add_argument("--force", action="store_true", help="Legacy no-op. Compiled outputs are always cleared before a build.")

  args, unknown = parser.parse_known_args()
  dynamic_model_flags = [arg[2:] for arg in unknown if arg.startswith("--")]
  invalid = [arg for arg in unknown if not arg.startswith("--")]
  if invalid:
    parser.error(f"Unexpected arguments: {' '.join(invalid)}")
  if len(dynamic_model_flags) > 1:
    parser.error("Pass only one dynamic model flag, for example ./models --sc2")
  if args.model and dynamic_model_flags and args.model != dynamic_model_flags[0]:
    parser.error("Use either --model sc2 or --sc2, not both with different values.")
  args.model = args.model or (dynamic_model_flags[0] if dynamic_model_flags else None)
  return args


def detect_component(path: Path) -> str | None:
  stem = path.stem.lower()
  for component, aliases in COMPONENT_ALIASES.items():
    if any(alias in stem for alias in aliases):
      return component
  return None


def find_staged_models(input_root: Path) -> dict[str, dict[str, Path]]:
  found: dict[str, dict[str, Path]] = {}
  if not input_root.is_dir():
    return found

  for child in sorted(input_root.iterdir()):
    if not child.is_dir():
      continue
    model_files = {}
    for onnx_file in sorted(child.glob("*.onnx")):
      component = detect_component(onnx_file)
      if component:
        model_files[component] = onnx_file
    if model_files:
      found[child.name] = model_files

  flat_root_files = {}
  for onnx_file in sorted(input_root.glob("*.onnx")):
    component = detect_component(onnx_file)
    if component is None:
      continue

    model_key = None
    lowered = onnx_file.stem.lower()
    for alias in COMPONENT_ALIASES[component]:
      if lowered == alias:
        model_key = None
        break
      suffix = f"_{alias}"
      if lowered.endswith(suffix):
        model_key = onnx_file.stem[:-len(suffix)]
        break

    if model_key in ("", "driving"):
      model_key = None

    if model_key:
      found.setdefault(model_key, {})[component] = onnx_file
    else:
      flat_root_files[component] = onnx_file

  if flat_root_files:
    found["_root"] = flat_root_files

  return found


def resolve_model_files(input_root: Path, model_key: str) -> dict[str, Path]:
  staged = find_staged_models(input_root)
  if model_key in staged:
    return staged[model_key]

  root_files = staged.get("_root")
  if root_files and len(staged) == 1:
    return root_files

  prefixed_files = {}
  for onnx_file in sorted(input_root.glob(f"{model_key}_*.onnx")):
    component = detect_component(onnx_file)
    if component:
      prefixed_files[component] = onnx_file
  return prefixed_files


def get_metadata_value_by_name(model, name: str):
  for prop in model.metadata_props:
    if prop.key == name:
      return prop.value
  return None


def write_metadata(onnx_path: Path, output_path: Path) -> None:
  import onnx

  model = onnx.load(str(onnx_path))
  output_slices = get_metadata_value_by_name(model, "output_slices")
  if output_slices is None:
    raise ValueError(f"output_slices not found in metadata for {onnx_path.name}")

  def get_name_and_shape(value_info) -> tuple[str, tuple[int, ...]]:
    shape = tuple(int(dim.dim_value) for dim in value_info.type.tensor_type.shape.dim)
    return value_info.name, shape

  metadata = {
    "model_checkpoint": get_metadata_value_by_name(model, "model_checkpoint"),
    "output_slices": pickle.loads(codecs.decode(output_slices.encode(), "base64")),
    "input_shapes": dict(get_name_and_shape(x) for x in model.graph.input),
    "output_shapes": dict(get_name_and_shape(x) for x in model.graph.output),
  }

  with open(output_path, "wb") as f:
    pickle.dump(metadata, f)


def compile_component(onnx_path: Path, output_path: Path) -> None:
  env = os.environ.copy()
  existing_pythonpath = env.get("PYTHONPATH", "")
  env["PYTHONPATH"] = f"{REPO_ROOT}:{existing_pythonpath}" if existing_pythonpath else str(REPO_ROOT)
  subprocess.run(
    [sys.executable, str(COMPILE_SCRIPT), str(onnx_path), str(output_path)],
    cwd=REPO_ROOT,
    env=env,
    check=True,
  )


def clear_existing_outputs(output_dir: Path) -> list[Path]:
  removed = []
  for existing in sorted(output_dir.iterdir()):
    if existing.is_file() or existing.is_symlink():
      existing.unlink()
    elif existing.is_dir():
      shutil.rmtree(existing)
    removed.append(existing)
  return removed


def list_models(staged: dict[str, dict[str, Path]], input_root: Path) -> int:
  if not staged:
    print(f"No staged models found in {input_root}")
    return 0

  for model_key, files in sorted(staged.items()):
    print(model_key)
    for component, path in sorted(files.items()):
      print(f"  {component}: {path}")
  return 0


def main() -> int:
  args = parse_args()
  staged = find_staged_models(args.input_dir)

  if args.list:
    return list_models(staged, args.input_dir)

  if not args.model:
    available = ", ".join(sorted(k for k in staged if k != "_root"))
    raise SystemExit(f"Choose a model key, for example ./models --sc2. Available staged models: {available or 'none'}")

  model_key = args.model.strip()
  files = resolve_model_files(args.input_dir, model_key)
  if not files:
    raise SystemExit(
      f"No staged ONNX files found for {model_key} in {args.input_dir}. "
      f"Use {args.input_dir}/driving_policy.onnx and {args.input_dir}/driving_vision.onnx, "
      f"or optionally {args.input_dir / model_key}/*.onnx"
    )

  missing = sorted(REQUIRED_COMPONENTS - set(files))
  if missing:
    raise SystemExit(f"Missing required ONNX files for {model_key}: {', '.join(missing)}")

  args.output_dir.mkdir(parents=True, exist_ok=True)
  print(f"Compiling {model_key} from {args.input_dir} -> {args.output_dir}")

  removed = clear_existing_outputs(args.output_dir)
  if removed:
    print(f"  cleared {len(removed)} existing output entries")

  for component, onnx_path in sorted(files.items()):
    output_pkl = args.output_dir / f"{model_key}_{component}_tinygrad.pkl"
    output_metadata = args.output_dir / f"{model_key}_{component}_metadata.pkl"

    print(f"  compiling {component}: {onnx_path.name}")
    compile_component(onnx_path, output_pkl)
    write_metadata(onnx_path, output_metadata)
    print(f"  saved {output_pkl.name}")
    print(f"  saved {output_metadata.name}")

  print("Done.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
