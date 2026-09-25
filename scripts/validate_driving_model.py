#!/usr/bin/env python3
"""Exercise a compiled catalog model on synthetic NV12 frames without starting modeld."""
import argparse
import gc
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

CAMERAS = ((1928, 1208), (1344, 760))
REQUIRED_SHAPES = {"plan": (1, 33, 15), "lane_lines": (1, 4, 33, 2), "road_edges": (1, 2, 33, 2),
                   "lead": (1, 3, 6, 4), "pose": (1, 6)}
REQUIRED_KEYS = frozenset((*REQUIRED_SHAPES, "lane_lines_prob", "lead_prob", "meta", "desire_state", "desire_pred",
                           "wide_from_device_euler", "road_transform"))


def sha256_file(path: Path) -> str:
  digest = hashlib.sha256()
  with path.open("rb") as file:
    for block in iter(lambda: file.read(1024 * 1024), b""):
      digest.update(block)
  return digest.hexdigest()


def check_outputs(outputs: dict[str, np.ndarray], version: str) -> dict[str, str]:
  required = REQUIRED_KEYS | ({"action"} if version in ("v14", "v15", "v16") else set())
  if missing := required - outputs.keys():
    raise ValueError(f"Missing parsed outputs: {sorted(missing)}")
  shapes = REQUIRED_SHAPES | ({"action": (1, 2)} if "action" in outputs else {})
  hashes = {}
  for name, value in outputs.items():
    array = np.asarray(value)
    if not array.size or not np.isfinite(array).all():
      raise ValueError(f"Empty or non-finite parsed output: {name}")
    if name in shapes and array.shape != shapes[name]:
      raise ValueError(f"Incorrect parsed {name} shape: {array.shape}, expected {shapes[name]}")
    hashes[name] = hashlib.sha256(array.tobytes()).hexdigest()
  return hashes


def fill_nv12(frame: np.ndarray, width: int, height: int, step: int, seed: int) -> None:
  from openpilot.system.camerad.cameras.nv12_info import get_nv12_info

  stride, y_height, uv_height, _ = get_nv12_info(width, height)
  frame.fill(16)
  y = frame[:stride * y_height].reshape(y_height, stride)
  x_coordinate = np.arange(width, dtype=np.uint32)[None, :]
  y_coordinate = np.arange(height, dtype=np.uint32)[:, None]
  y[:height, :width] = 16 + ((x_coordinate * 3 + y_coordinate * 5 + step * 17 + seed) % 220)
  uv = frame[stride * y_height:stride * (y_height + uv_height)].reshape(uv_height, stride)
  uv.fill(128)
  uv[:height // 2, :width:2] = 96 + ((step * 3 + seed) % 64)
  uv[:height // 2, 1:width:2] = 96 + ((step * 7 + seed) % 64)


def frame_transform(width: int, height: int, step: int) -> np.ndarray:
  return np.array([[0.8 * width / 512, 0, 0.1 * width + math.sin(step) * 2],
                   [0, 0.8 * height / 256, 0.1 * height + math.cos(step) * 2], [0, 0, 1]], dtype=np.float32)


def upload_frames(runner, frames: dict[str, np.ndarray]) -> None:
  from tinygrad import Device, Tensor

  for name, frame in frames.items():
    runner._blob_cache[(name, frame.ctypes.data)] = Tensor(frame, device=runner.warp_device).realize()
  Device[runner.warp_device].synchronize()
  if runner.queue_device != runner.warp_device:
    Device[runner.queue_device].synchronize()


def validate_camera(artifact: Path, version: str, camera: tuple[int, int], steps: int, seed: int,
                    gpu: bool, max_p95_ms: float | None = None, runner_factory=None, action_update=None, initial_action=None) -> dict:
  device_frames = runner_factory is None
  if runner_factory is None:
    from openpilot.starpilot.models.runner import CatalogModelState, action_from_outputs
    from openpilot.cereal import log
    runner_factory, action_update = CatalogModelState, action_from_outputs
    initial_action = log.ModelDataV2.Action()
  width, height = camera
  start = time.perf_counter()
  runner = runner_factory(width, height, artifact, version, gpu)
  load_ms = (time.perf_counter() - start) * 1000
  start = time.perf_counter()
  runner.warmup()
  warmup_ms = (time.perf_counter() - start) * 1000
  frames = {name: np.zeros(runner.frame_buf_size, dtype=np.uint8) for name in runner.vision_input_names}
  previous_action = initial_action
  latencies, changed, baseline = [], set(), None
  output_shapes = {}
  actions = []
  for step in range(steps):
    for index, frame in enumerate(frames.values()):
      fill_nv12(frame, width, height, step, seed + index * 97)
    transforms = {name: frame_transform(width, height, step + index) for index, name in enumerate(frames)}
    desire = np.zeros(8, dtype=np.float32)
    if step % 4 == 0:
      desire[1 + (step // 4) % 2] = 1
    speed = 5.0 + step % 20
    inputs = {"desire_pulse": desire, "traffic_convention": np.array([step % 2, 1 - step % 2], dtype=np.float32),
              "action_t": np.array([.2, .4], dtype=np.float32),
              "prev_action": np.array([previous_action.desiredCurvature * max(1., speed) ** 2,
                                        previous_action.desiredAcceleration], dtype=np.float32),
              "lateral_control_params": np.array([speed, .2], dtype=np.float32)}
    if device_frames:
      upload_frames(runner, frames)
    start = time.perf_counter()
    outputs = runner.run(frames, transforms, inputs)
    latencies.append((time.perf_counter() - start) * 1000)
    hashes = check_outputs(outputs, version)
    if baseline is None:
      baseline = hashes
      output_shapes = {name: list(np.asarray(value).shape) for name, value in outputs.items()}
    else:
      if hashes.keys() != baseline.keys():
        raise ValueError("Parsed output names changed between frames")
      changed.update(name for name, value in hashes.items() if value != baseline[name])
    previous_action = action_update(outputs, version, previous_action, .2, .4, speed)
    action = [float(previous_action.desiredCurvature), float(previous_action.desiredAcceleration)]
    if not np.isfinite(action).all():
      raise ValueError("Non-finite derived driving action")
    actions.append(action)
  if not changed.intersection(REQUIRED_KEYS | {"action"}):
    raise ValueError("Driving outputs stayed unchanged across changing frames and inputs")
  timing = {"min": float(np.min(latencies)), "median": float(np.median(latencies)),
            "p95": float(np.percentile(latencies, 95)), "max": float(np.max(latencies))}
  if max_p95_ms is not None and timing["p95"] > max_p95_ms:
    raise ValueError(f"p95 latency {timing['p95']:.2f} ms exceeds {max_p95_ms:.2f} ms")
  result = {"passed": True, "camera": [width, height], "steps": steps, "seed": seed,
            "load_ms": load_ms, "warmup_ms": warmup_ms, "inference_ms": timing,
            "changed_outputs": sorted(changed), "output_shapes": output_shapes, "last_output_sha256": hashes,
            "last_action": {"desired_curvature": actions[-1][0], "desired_acceleration": actions[-1][1]},
            "execution_device": getattr(runner, "queue_device", None), "warp_device": getattr(runner, "warp_device", None)}
  del runner
  gc.collect()
  return result


def parse_args(argv=None):
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("artifact", type=Path)
  parser.add_argument("--version", required=True, choices=tuple(f"v{number}" for number in range(8, 17)))
  parser.add_argument("--steps", type=int, default=24)
  parser.add_argument("--seed", type=int, default=42)
  parser.add_argument("--gpu", action="store_true")
  parser.add_argument("--max-p95-ms", type=float)
  parser.add_argument("--build-receipt", type=Path)
  parser.add_argument("--source-dir", type=Path, help="Also verify the build receipt's ONNX source hashes")
  parser.add_argument("--report", type=Path)
  parser.add_argument("--camera", choices=("1928x1208", "1344x760"), help=argparse.SUPPRESS)
  args = parser.parse_args(argv)
  if args.steps < 2:
    parser.error("--steps must be at least 2")
  if args.max_p95_ms is not None and (not math.isfinite(args.max_p95_ms) or args.max_p95_ms <= 0):
    parser.error("--max-p95-ms must be positive and finite")
  if args.seed < 0:
    parser.error("--seed must be nonnegative")
  return args


def main(argv=None):
  args = parse_args(argv)
  artifact = args.artifact.resolve()
  report_path = args.report or artifact.with_suffix(".validation.json")
  receipt_path = args.build_receipt or artifact.with_suffix(".build.json")
  protected = {artifact, receipt_path.resolve()}
  report = {"passed": False, "validation": "synthetic_nv12_catalog_runner", "artifact": str(artifact),
            "behavior_version": args.version, "steps": args.steps, "seed": args.seed, "cameras": []}
  try:
    if args.camera:
      camera = tuple(map(int, args.camera.split("x")))
      report.update(validate_camera(artifact, args.version, camera, args.steps, args.seed, args.gpu, args.max_p95_ms))
    else:
      before = sha256_file(artifact)
      report.update(artifact_sha256=before, artifact_size=artifact.stat().st_size, sources_verified=False)
      if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text())
        if receipt.get("artifact_sha256") != before or receipt.get("behavior_version") != args.version:
          raise ValueError("Build receipt does not match artifact hash/behavior version")
        source_hashes = receipt.get("source_sha256", {})
        report.update(build_receipt_sha256=sha256_file(receipt_path), source_sha256=source_hashes,
                      compiler_revision=receipt.get("compiler_revision"), artifact_abi=receipt.get("artifact_abi"))
        if args.source_dir:
          if not source_hashes or any(Path(name).name != name for name in source_hashes):
            raise ValueError("Build receipt has no bounded source filenames")
          protected.update((args.source_dir / name).resolve() for name in source_hashes)
          if {name: sha256_file(args.source_dir / name) for name in source_hashes} != source_hashes:
            raise ValueError("Source hashes do not match build receipt")
          report["sources_verified"] = True
      elif args.build_receipt or args.source_dir:
        raise ValueError("Build receipt required for requested source verification")
      # Separate processes release all device allocations between camera formats.
      with tempfile.TemporaryDirectory(prefix="starpilot-model-validation-") as temporary:
        for width, height in CAMERAS:
          child_report = Path(temporary) / f"{width}x{height}.json"
          command = [sys.executable, str(Path(__file__).resolve()), str(artifact), "--version", args.version,
                     "--steps", str(args.steps), "--seed", str(args.seed), "--camera", f"{width}x{height}",
                     "--report", str(child_report)]
          if args.gpu:
            command.append("--gpu")
          if args.max_p95_ms is not None:
            command += ["--max-p95-ms", str(args.max_p95_ms)]
          completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
          result = json.loads(child_report.read_text()) if child_report.is_file() else {
            "passed": False, "camera": [width, height], "error": "Validation process exited without a report"}
          if completed.returncode:
            result["passed"] = False
          report["cameras"].append(result)
      if sha256_file(artifact) != before:
        raise ValueError("Artifact changed during validation")
      report["passed"] = all(camera["passed"] for camera in report["cameras"])
  except Exception as error:
    report.update(passed=False, error=f"{type(error).__name__}: {error}")
  if report_path.resolve() in protected:
    print("Refusing to overwrite a validation input with its report", file=sys.stderr)
    return 1
  report_path.parent.mkdir(parents=True, exist_ok=True)
  report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
  print(f"{'PASS' if report['passed'] else 'FAIL'}: {report_path}")
  return 0 if report["passed"] else 1


if __name__ == "__main__":
  raise SystemExit(main())
