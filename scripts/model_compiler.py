#!/usr/bin/env python3
import argparse
import codecs
import hashlib
import json
import os
import pickle
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

DEFAULT_INPUT_ROOT = Path("/data/openpilot/uncompiledmodels")
DEFAULT_OUTPUT_ROOT = Path("/data/openpilot/compiledmodels")
COMPILE_SCRIPT = REPO_ROOT / "tinygrad_repo/examples/openpilot/compile3.py"
DRIVING_COMPILE_SCRIPT = REPO_ROOT / "selfdrive/modeld/compile_modeld.py"
DM_WARP_COMPILE_SCRIPT = REPO_ROOT / "selfdrive/modeld/compile_dm_warp.py"
MODEL_VERSIONS_CACHE = Path("/data/models/.model_versions.json")
MODELS_PATH = MODEL_VERSIONS_CACHE.parent  # runtime dir modeld loads from: /data/models

DM_MODEL_KEY = "dm"
DM_MODEL_NAME = "dmonitoring_model"
DM_TARGET_ALIASES = {DM_MODEL_KEY, "dmonitoring", DM_MODEL_NAME}
DM_INPUT_CANDIDATES = ("dmonitoring_model.onnx", "dmonitoring.onnx", "dm.onnx")

COMPONENT_ALIASES = {
  "driving_supercombo": ("driving_supercombo", "supercombo"),
  "driving_off_policy": ("driving_off_policy", "off_policy", "offpolicy"),
  "driving_on_policy": ("driving_on_policy", "on_policy", "onpolicy"),
  "driving_policy": ("driving_policy", "policy"),
  "driving_vision": ("driving_vision", "vision"),
}
DEFAULT_CAMERA_RESOLUTIONS = ((1928, 1208), (1344, 760))
MEDMODEL_INPUT_SIZE = (512, 256)
DM_INPUT_SIZE = (1440, 960)
MODEL_RUN_FREQ = 20
MODEL_CONTEXT_FREQ = 5
REPOSITORY_FILE_LIMIT = 100 * 1024 * 1024
DEFAULT_MULTIPART_SIZE = 95 * 1024 * 1024


def build_compile_env() -> dict[str, str]:
  env = os.environ.copy()
  pythonpath = env.get("PYTHONPATH", "")
  env["PYTHONPATH"] = f"{REPO_ROOT}:{pythonpath}" if pythonpath else str(REPO_ROOT)
  for key, default in {
    "DEBUG": "0",
    "FLOAT16": "1",
    "IMAGE": "2",
    "JIT_BATCH_SIZE": "0",
    "NOLOCALS": "1",
    "OPENPILOT_HACKS": "1",
  }.items():
    try:
      int(str(env.get(key)), 0)
    except (TypeError, ValueError):
      env[key] = default
  return env


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Compile staged ONNX models into StarPilot's unified tinygrad artifact format.",
  )
  parser.add_argument("--model", help="Output model ID, for example sc2.")
  parser.add_argument("--dm", action="store_true", help="Build DM model, metadata, and both camera warps.")
  parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_ROOT)
  parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
  parser.add_argument(
    "--input-format",
    choices=("auto", "supercombo", "split"),
    default="auto",
    help="Source ONNX layout. Auto prefers supercombo when present.",
  )
  parser.add_argument(
    "--version",
    help="Behavioral model version stored in the artifact. It does not control artifact layout.",
  )
  parser.add_argument("--list", action="store_true", help="List staged models and exit.")
  parser.add_argument("--force", action="store_true", help="Accepted for compatibility; selected outputs are always replaced.")
  parser.add_argument("--gpu", "--external-gpu", dest="external_gpu", action="store_true",
                      help="Compile the driving artifact for the USB AMD GPU.")
  parser.add_argument("--split-artifact", type=Path, help="Split an existing oversized PKL without compiling.")
  parser.add_argument("--chunk-size-mib", type=int, default=95, help="Multipart size in MiB; must be below 100.")
  parser.add_argument("--no-split", action="store_true",
                      help="Keep a single .pkl even if >100 MiB (for local installs, which need one "
                           "file). Auto-enabled for local- model IDs.")
  parser.add_argument("--no-install", action="store_true",
                      help="Do not auto-copy a local- model into /data/models after compiling.")
  parser.add_argument(
    "--image-history-pipeline",
    choices=("policy", "warp"),
    default="policy",
    help="Driving artifact ABI. 'policy' is the newer faster path; 'warp' reproduces legacy v22 artifacts.",
  )

  args, unknown = parser.parse_known_args()
  dynamic_flags = [value[2:] for value in unknown if value.startswith("--")]
  invalid = [value for value in unknown if not value.startswith("--")]
  if invalid:
    parser.error(f"Unexpected arguments: {' '.join(invalid)}")
  if len(dynamic_flags) > 1:
    parser.error("Pass only one dynamic model flag, for example ./models --sc2")
  if args.model and dynamic_flags and args.model != dynamic_flags[0]:
    parser.error("Use either --model sc2 or --sc2, not both.")
  args.model = args.model or (dynamic_flags[0] if dynamic_flags else None)
  if args.model and args.model.strip().lower() in DM_TARGET_ALIASES:
    args.dm = True
    args.model = None
  if args.dm and args.model:
    parser.error("Use either --dm or a driving model ID.")
  if args.split_artifact and (args.dm or args.model):
    parser.error("--split-artifact cannot be combined with --dm or a model ID.")
  if not 1 <= args.chunk_size_mib < 100:
    parser.error("--chunk-size-mib must be between 1 and 99.")
  return args


def detect_component(path: Path) -> str | None:
  stem = path.stem.lower()
  for component, aliases in COMPONENT_ALIASES.items():
    if any(alias in stem for alias in aliases):
      return component
  return None


def _model_key_from_flat_file(path: Path, component: str) -> str | None:
  lowered = path.stem.lower()
  for alias in COMPONENT_ALIASES[component]:
    if lowered == alias:
      return None
    suffix = f"_{alias}"
    if lowered.endswith(suffix):
      key = path.stem[:-len(suffix)]
      return None if key in ("", "driving") else key
  return None


def find_staged_models(input_root: Path) -> dict[str, dict[str, Path]]:
  found: dict[str, dict[str, Path]] = {}
  if not input_root.is_dir():
    return found

  for child in sorted(input_root.iterdir()):
    if not child.is_dir():
      continue
    files = {
      component: path
      for path in sorted(child.glob("*.onnx"))
      if (component := detect_component(path)) is not None
    }
    if files:
      found[child.name] = files

  root_files: dict[str, Path] = {}
  for path in sorted(input_root.glob("*.onnx")):
    component = detect_component(path)
    if component is None:
      continue
    model_key = _model_key_from_flat_file(path, component)
    if model_key:
      found.setdefault(model_key, {})[component] = path
    else:
      root_files[component] = path
  if root_files:
    found["_root"] = root_files
  return found


def resolve_model_files(input_root: Path, model_key: str) -> dict[str, Path]:
  staged = find_staged_models(input_root)
  if model_key in staged:
    return staged[model_key]
  root_files = staged.get("_root")
  if root_files:
    return root_files
  matching_files = {
    component: path
    for path in sorted(input_root.glob(f"{model_key}_*.onnx"))
    if (component := detect_component(path)) is not None
  }
  if matching_files:
    return matching_files

  named_sources = [files for key, files in staged.items() if key != "_root"]
  return named_sources[0] if len(named_sources) == 1 else {}


def find_staged_dm(input_root: Path) -> Path | None:
  if not input_root.is_dir():
    return None
  for candidate in DM_INPUT_CANDIDATES:
    path = input_root / candidate
    if path.is_file():
      return path
  for child in sorted(input_root.iterdir()):
    if child.is_dir():
      for candidate in DM_INPUT_CANDIDATES:
        path = child / candidate
        if path.is_file():
          return path
  return None


def get_metadata_value_by_name(model, name: str):
  for prop in model.metadata_props:
    if prop.key == name:
      return prop.value
  return None


def write_metadata(onnx_path: Path, output_path: Path) -> dict:
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
    "input_shapes": dict(get_name_and_shape(value) for value in model.graph.input),
    "output_shapes": dict(get_name_and_shape(value) for value in model.graph.output),
  }
  with open(output_path, "wb") as metadata_file:
    pickle.dump(metadata, metadata_file)
  return metadata


def infer_model_version(model_key: str, explicit_version: str | None) -> str:
  if explicit_version:
    return explicit_version.strip()
  if MODEL_VERSIONS_CACHE.is_file():
    try:
      version = json.loads(MODEL_VERSIONS_CACHE.read_text()).get(model_key)
      if isinstance(version, str):
        return version.strip()
    except Exception:
      pass
  return ""


def select_input_format(requested: str, files: dict[str, Path]) -> str:
  if requested == "supercombo":
    if "driving_supercombo" not in files:
      raise SystemExit("--input-format supercombo requires driving_supercombo.onnx")
    return requested
  if requested == "split":
    return requested
  return "supercombo" if "driving_supercombo" in files else "split"


def driving_compile_args(files: dict[str, Path], input_format: str) -> tuple[str, list[str]]:
  if input_format == "supercombo":
    return "supercombo", ["--supercombo-onnx", str(files["driving_supercombo"])]

  vision = files.get("driving_vision")
  primary = files.get("driving_on_policy") or files.get("driving_policy")
  off_policy = files.get("driving_off_policy")
  if vision is None or primary is None:
    missing = [
      name for name, present in (
        ("driving_vision", vision),
        ("driving_policy or driving_on_policy", primary),
      ) if present is None
    ]
    raise SystemExit(f"Missing required split ONNX files: {', '.join(missing)}")

  args = ["--vision-onnx", str(vision)]
  if off_policy is None:
    args += ["--policy-onnx", str(primary)]
    return "vision_policy", args

  args += ["--on-policy-onnx", str(primary), "--off-policy-onnx", str(off_policy)]
  return "vision_multi_policy", args


def remove_paths(paths: list[Path]) -> int:
  count = 0
  for path in paths:
    if path.is_file() or path.is_symlink():
      path.unlink()
      count += 1
  return count


def sha256_file(path: Path) -> str:
  digest = hashlib.sha256()
  with open(path, "rb") as artifact_file:
    for chunk in iter(lambda: artifact_file.read(1024 * 1024), b""):
      digest.update(chunk)
  return digest.hexdigest()


def multipart_output_paths(artifact: Path, output_dir: Path | None = None) -> list[Path]:
  output_dir = output_dir or artifact.parent
  return [
    *sorted(output_dir.glob(f"{artifact.name}.p[0-9][0-9]")),
    output_dir / f"{artifact.name}.sha256",
  ]


def install_local_artifact(artifact: Path, model_key: str, version: str) -> None:
  """Copy a freshly compiled local- model into the runtime dir modeld loads from,
  and ensure its <id>.json sidecar carries the correct version.

  The sidecar version is NOT cosmetic: without it _discover_local_models() records
  an empty version, which downstream parses on the wrong contract (a v15 model then
  drives like v11). Since we know the build version here, we write it so the local
  install is correct by default. Local models must be a single is_file() in
  /data/models to show in the picker. No-ops off-device (no /data/models).
  """
  if not MODELS_PATH.is_dir():
    print(f"  skipped auto-install: {MODELS_PATH} not present (not on device?)")
    return
  dest = MODELS_PATH / artifact.name
  shutil.copy2(artifact, dest)
  print(f"  installed -> {dest}")

  sidecar = MODELS_PATH / f"{model_key}.json"
  info: dict = {}
  if sidecar.is_file():
    try:
      loaded = json.loads(sidecar.read_text())
      if isinstance(loaded, dict):
        info = loaded
    except Exception as error:
      print(f"  WARN: existing sidecar {sidecar.name} is malformed, rewriting: {error}")
  if not version:
    if not str(info.get("version") or "").strip():
      print(f"  WARN: could not determine version -- set it by hand in {sidecar.name} "
            "or the model may drive on the wrong version contract")
    return
  # keep any user-set name/series; only guarantee a correct, non-empty version
  if str(info.get("version") or "").strip() == version and sidecar.is_file():
    print(f"  sidecar ok: {sidecar.name} (version {version})")
    return
  info.setdefault("name", model_key[len("local-"):].replace("_", " ").replace("-", " ").strip())
  info.setdefault("series", "Local")
  info["version"] = version
  sidecar.write_text(json.dumps(info, indent=2) + "\n")
  print(f"  wrote sidecar {sidecar.name} (version {version})")


def split_oversized_artifact(
  artifact: Path,
  output_dir: Path | None = None,
  chunk_size: int = DEFAULT_MULTIPART_SIZE,
  force: bool = False,
) -> list[Path]:
  artifact = artifact.resolve()
  output_dir = (output_dir or artifact.parent).resolve()
  if not artifact.is_file():
    raise FileNotFoundError(artifact)
  if chunk_size <= 0 or chunk_size >= REPOSITORY_FILE_LIMIT:
    raise ValueError("Multipart chunk size must be between 1 byte and 100 MiB.")

  remove_paths(multipart_output_paths(artifact, output_dir))
  if artifact.stat().st_size <= REPOSITORY_FILE_LIMIT and not force:
    return []

  output_dir.mkdir(parents=True, exist_ok=True)
  digest = hashlib.sha256()
  part_paths: list[Path] = []
  with open(artifact, "rb") as source:
    for index in range(100):
      part_path = output_dir / f"{artifact.name}.p{index:02d}"
      part_size = 0
      with open(part_path, "wb") as part_file:
        while part_size < chunk_size:
          chunk = source.read(min(1024 * 1024, chunk_size - part_size))
          if not chunk:
            break
          part_file.write(chunk)
          digest.update(chunk)
          part_size += len(chunk)
      if part_size == 0:
        part_path.unlink()
        break
      part_paths.append(part_path)
  if not part_paths:
    raise ValueError(f"Artifact is empty: {artifact}")

  checksum_path = output_dir / f"{artifact.name}.sha256"
  checksum_path.write_text(f"{digest.hexdigest()}  {artifact.name}\n")

  verify_digest = hashlib.sha256()
  for part_path in part_paths:
    with open(part_path, "rb") as part_file:
      for chunk in iter(lambda: part_file.read(1024 * 1024), b""):
        verify_digest.update(chunk)
  if verify_digest.hexdigest() != digest.hexdigest():
    remove_paths([*part_paths, checksum_path])
    raise RuntimeError("Split artifact failed checksum verification.")
  return [*part_paths, checksum_path]


def compile_driving(
  model_key: str,
  files: dict[str, Path],
  input_format: str,
  version: str,
  output_dir: Path,
  image_history_pipeline: str,
  external_gpu: bool = False,
) -> Path:
  model_type, source_args = driving_compile_args(files, input_format)
  output_path = output_dir / f"{model_key}_driving_tinygrad.pkl"
  removed = remove_paths(sorted({
    output_path,
    *multipart_output_paths(output_path, output_dir),
    *output_dir.glob("*_driving_tinygrad.pkl"),
    *output_dir.glob("*_driving_tinygrad.pkl.p[0-9][0-9]"),
    *output_dir.glob("*_driving_tinygrad.pkl.sha256"),
    *output_dir.glob("*_driving_*_tinygrad.pkl"),
    *output_dir.glob("*_driving_*_metadata.pkl"),
  }))
  if removed:
    print(f"  cleared {removed} existing driving output entries")

  frame_skip = MODEL_RUN_FREQ // MODEL_CONTEXT_FREQ
  command = [
    sys.executable,
    str(DRIVING_COMPILE_SCRIPT),
    "--model-type",
    model_type,
    "--model-size",
    f"{MEDMODEL_INPUT_SIZE[0]}x{MEDMODEL_INPUT_SIZE[1]}",
    "--camera-resolutions",
    *(f"{width}x{height}" for width, height in DEFAULT_CAMERA_RESOLUTIONS),
    "--output",
    str(output_path),
    "--frame-skip",
    str(frame_skip),
    "--image-history-pipeline",
    image_history_pipeline,
    *source_args,
  ]
  if version:
    command += ["--behavior-version", version]
  compile_env = build_compile_env()
  if external_gpu:
    for qcom_only_flag in ("IMAGE", "NOLOCALS", "OPENPILOT_HACKS"):
      compile_env.pop(qcom_only_flag, None)
    compile_env.update({
      "DEBUG": "2",
      "DEV": "USB+AMD:LLVM",
      "WARP_DEV": "QCOM",
      "FLOAT16": "1",
      "JIT_BATCH_SIZE": "0",
      "GMMU": "0",
    })
    command.append("--out-of-band")
  subprocess.run(command, cwd=REPO_ROOT, env=compile_env, check=True)
  return output_path


def compile_dm(onnx_path: Path, output_dir: Path) -> list[Path]:
  outputs = [
    output_dir / f"{DM_MODEL_NAME}_tinygrad.pkl",
    output_dir / f"{DM_MODEL_NAME}_metadata.pkl",
    *(output_dir / f"dm_warp_{width}x{height}_tinygrad.pkl" for width, height in DEFAULT_CAMERA_RESOLUTIONS),
  ]
  removed = remove_paths(outputs)
  if removed:
    print(f"  cleared {removed} existing DM output entries")

  subprocess.run(
    [sys.executable, str(COMPILE_SCRIPT), str(onnx_path), str(outputs[0])],
    cwd=REPO_ROOT,
    env=build_compile_env(),
    check=True,
  )
  write_metadata(onnx_path, outputs[1])
  dm_w, dm_h = DM_INPUT_SIZE
  for (cam_w, cam_h), output_path in zip(DEFAULT_CAMERA_RESOLUTIONS, outputs[2:], strict=True):
    subprocess.run(
      [
        sys.executable,
        str(DM_WARP_COMPILE_SCRIPT),
        "--camera-resolution",
        f"{cam_w}x{cam_h}",
        "--warp-to",
        f"{dm_w}x{dm_h}",
        "--output",
        str(output_path),
      ],
      cwd=REPO_ROOT,
      env=build_compile_env(),
      check=True,
    )
  return outputs


def list_models(staged: dict[str, dict[str, Path]], input_root: Path) -> int:
  for model_key, files in sorted(staged.items()):
    print(model_key)
    for component, path in sorted(files.items()):
      print(f"  {component}: {path}")
  if (dm_path := find_staged_dm(input_root)) is not None:
    print(DM_MODEL_KEY)
    print(f"  {DM_MODEL_NAME}: {dm_path}")
  if not staged and dm_path is None:
    print(f"No staged models found in {input_root}")
  return 0


def main() -> int:
  args = parse_args()
  if args.split_artifact:
    outputs = split_oversized_artifact(
      args.split_artifact,
      args.output_dir,
      args.chunk_size_mib * 1024 * 1024,
      force=True,
    )
    for output in outputs:
      print(f"  saved {output.name} ({output.stat().st_size} bytes)")
    return 0

  staged = find_staged_models(args.input_dir)
  if args.list:
    return list_models(staged, args.input_dir)

  args.output_dir.mkdir(parents=True, exist_ok=True)
  if args.dm:
    onnx_path = find_staged_dm(args.input_dir)
    if onnx_path is None:
      raise SystemExit(f"No staged DM ONNX found in {args.input_dir}")
    print(f"Compiling DM artifacts from {onnx_path} -> {args.output_dir}")
    for output in compile_dm(onnx_path, args.output_dir):
      print(f"  saved {output.name}")
    print("Done.")
    return 0

  if not args.model:
    available = ", ".join(sorted(key for key in staged if key != "_root"))
    raise SystemExit(f"Choose a model ID, for example ./models --sc2. Available: {available or 'none'}")

  model_key = args.model.strip()
  files = resolve_model_files(args.input_dir, model_key)
  if not files:
    raise SystemExit(f"No staged ONNX files found for {model_key} in {args.input_dir}")

  input_format = select_input_format(args.input_format, files)
  version = infer_model_version(model_key, args.version)
  if not version and input_format == "supercombo":
    version = "v15"
  version_label = version or "unspecified behavior"
  will_install = model_key.startswith("local-") and not args.no_install
  target = f"{args.output_dir}" + (f" -> {MODELS_PATH} (auto-install)" if will_install else "")
  print(f"Compiling {model_key} ({input_format}, {version_label}) from {args.input_dir} -> {target}")
  output = compile_driving(model_key, files, input_format, version, args.output_dir,
                           args.image_history_pipeline, args.external_gpu)
  print(f"  saved {output.name}")
  # Local models install as a single is_file() and never go to GitHub, so the >100 MiB
  # repo split is pointless for them (you'd only have to reassemble it). Keep one .pkl.
  keep_single = args.no_split or model_key.startswith("local-")
  if keep_single:
    is_local = model_key.startswith("local-")
    if output.stat().st_size > REPOSITORY_FILE_LIMIT:
      size_mb = output.stat().st_size / 1e6
      if is_local:
        print(f"  local model: kept as one {size_mb:.1f} MB file (repo split not needed)")
      else:
        print(f"  --no-split: kept one {size_mb:.1f} MB file; over 100 MB, so split it "
              "before committing to a repo (re-run without --no-split, or --split-artifact)")
    if is_local and not args.no_install:
      install_local_artifact(output, model_key, version)
  else:
    multipart_outputs = split_oversized_artifact(output)
    if multipart_outputs:
      print("  artifact exceeds 100 MiB; created repository-safe multipart files:")
      for multipart_output in multipart_outputs:
        print(f"    {multipart_output.name} ({multipart_output.stat().st_size} bytes)")
      output.unlink()
      print(f"  removed oversized source artifact {output.name}")
  print("Done.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
