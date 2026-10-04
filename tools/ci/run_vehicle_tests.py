#!/usr/bin/env python3
"""Run explicitly scoped vehicle suites with collection and native-build evidence."""
import argparse
import ast
from collections import Counter
import hashlib
import importlib.machinery
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools import test_runner
from tools.ci import vehicle_pytest

RELEASE_TARGETS = (
  "opendbc_repo/opendbc/safety/tests/test_tesla_preap_stock.py",
  "opendbc_repo/opendbc/car/tesla/tests/test_preap_startup.py",
  "opendbc_repo/opendbc/car/tesla/tests/test_preap_stock.py",
  "openpilot/starpilot/car/tesla/tests/test_preap_intent.py",
  "openpilot/starpilot/car/tesla/tests/test_stock_events.py",
  "opendbc_repo/opendbc/car/ford/tests/test_aol_startup.py",
  "openpilot/starpilot/tests/test_ford_aol_intent.py",
  "opendbc_repo/opendbc/safety/tests/test_ford_aol.py",
  "opendbc_repo/opendbc/car/ford/tests/test_added_firmware_identity.py",
  "opendbc_repo/opendbc/car/ford/tests/test_required_source_health.py",
  "opendbc_repo/opendbc/car/ford/tests/test_blend_settings.py",
  "opendbc_repo/opendbc/car/ford/tests/test_blend_settings_startup.py",
  "opendbc_repo/opendbc/car/ford/tests/test_production_extensions.py",
  "opendbc_repo/opendbc/car/ford/tests/test_generic_canfd.py",
  "opendbc_repo/opendbc/safety/tests/test_ford_generic_canfd_extended.py",
  "opendbc_repo/opendbc/car/hyundai/tests/test_blended_stock_aol.py",
  "openpilot/starpilot/aol/tests/test_nexo_stock_aol.py",
  "opendbc_repo/opendbc/safety/tests/test_nexo_stock_aol.py",
  "opendbc_repo/opendbc/safety/tests/test_hyundai_stock_angle_aol.py",
  "opendbc_repo/opendbc/car/hyundai/tests/test_stock_angle_aol.py",
  "opendbc_repo/opendbc/car/hyundai/tests/test_g90_startup.py",
  "opendbc_repo/opendbc/safety/tests/test_hyundai_classic_long_aol.py",
  "openpilot/starpilot/aol/tests/test_classic_long_profiles.py",
  "opendbc_repo/opendbc/safety/tests/test_hyundai_shared_canfd_stock_aol.py",
  "opendbc_repo/opendbc/car/hyundai/tests/test_shared_canfd_stock_aol.py",
  "opendbc_repo/opendbc/safety/tests/test_hyundai_classic_scc_aol.py",
  "openpilot/starpilot/aol/tests/test_classic_scc_profiles.py",
  "opendbc_repo/opendbc/safety/tests/test_hyundai_blended.py",
  "opendbc_repo/opendbc/car/hyundai/tests/test_palisade_2023.py",
  "openpilot/starpilot/longitudinal/tests/test_output_max.py",
  "openpilot/starpilot/ui/tests/test_output_max_feature.py",
  "openpilot/starpilot/tests/test_output_max_namespace.py",
  "opendbc_repo/opendbc/car/gm/tests/test_conventional_pedal_transitions.py",
  "opendbc_repo/opendbc/car/gm/tests/test_conventional_pedal_disabled.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_cc_pedal_disabled.py",
  "opendbc_repo/opendbc/car/gm/tests/test_silverado_cc_pedal.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_silverado_pedal.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_cc_pedal.py",
  "opendbc_repo/opendbc/car/gm/tests/test_conventional_pedal.py",
  "openpilot/starpilot/tests/test_gm_conventional_pedal_startup.py",
  "tools/ci/test_release_safety.py",
  "opendbc_repo/opendbc/safety/tests/test_defaults.py::TestNoOutput",
  "opendbc_repo/opendbc/safety/tests/test_defaults.py::TestSilent",
  "opendbc_repo/opendbc/safety/tests/test_tesla.py::TestTeslaStockSafety",
  "opendbc_repo/opendbc/safety/tests/test_tesla_hw1.py",
  "opendbc_repo/opendbc/safety/tests/test_volvo_c1.py",
  "opendbc_repo/opendbc/safety/tests/test_tesla.py::TestTeslaFSD14StockSafety",
  "opendbc_repo/opendbc/safety/tests/test_mazda.py::TestMazdaSafety",
  "opendbc_repo/opendbc/safety/tests/test_toyota.py::TestToyotaStockLongitudinalTorque",
  "opendbc_repo/opendbc/safety/tests/test_toyota_auto_hold.py",
  "opendbc_repo/opendbc/safety/tests/test_gm.py::TestGmCameraSafety",
  "opendbc_repo/opendbc/safety/tests/test_gm.py::TestGmCameraEVSafety",
  "opendbc_repo/opendbc/safety/tests/test_gm_bolt_pedal.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_bolt_cc.py",
  "openpilot/starpilot/tests/test_bolt_disable_active_pedal.py::TestBoltDisableActivePedal",
  "opendbc_repo/opendbc/car/gm/tests/test_bolt_acc_cc.py",
  "opendbc_repo/opendbc/car/gm/tests/test_bolt_factory_acc.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_bolt_factory_stock.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_bolt_euv.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_volt_cc.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_volt_cc_gas.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_aol.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_ascm_intercept.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_sdgm_stock.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_cc_gateway_stock.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_camera_stock_four.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_volt_gateway_mapping.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_volt_alternate_brake.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_volt_ascm.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_ordinary_ascm.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_ordinary_sdgm.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_ordinary_cc.py",
  "opendbc_repo/opendbc/car/gm/tests/test_ordinary_cc.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_ordinary_camera.py",
  "opendbc_repo/opendbc/car/gm/tests/test_ordinary_camera.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_ordinary_camera_removed.py",
  "opendbc_repo/opendbc/car/gm/tests/test_ordinary_camera_removed.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_ascm_aol.py",
  "opendbc_repo/opendbc/car/gm/tests/test_ordinary_ascm.py",
  "openpilot/starpilot/longitudinal/tests/test_gm_suburban_outer.py",
  "opendbc_repo/opendbc/car/gm/tests/test_ordinary_sdgm.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_volt_camera.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_volt_camera_removed.py",
  "opendbc_repo/opendbc/car/gm/tests/test_volt_camera_removed.py",
  "opendbc_repo/opendbc/safety/tests/test_gm_volt_sdgm.py",
  "opendbc_repo/opendbc/car/gm/tests/test_volt_sdgm_control.py",
  "opendbc_repo/opendbc/car/gm/tests/test_volt_camera_control.py",
  "opendbc_repo/opendbc/safety/tests/test_hyundai_mrr35_angle_four.py",
  "opendbc_repo/opendbc/safety/tests/test_kia_ev6_2025_angle.py",
  "opendbc_repo/opendbc/safety/tests/test_hyundai_angle_hybrids_three.py",
  "opendbc_repo/opendbc/safety/tests/test_hyundai_ccnc_angle_two.py",
  "opendbc_repo/opendbc/safety/tests/test_hyundai_ioniq6_long.py",
  "opendbc_repo/opendbc/safety/tests/test_hyundai_ray_pedal.py",
  "opendbc_repo/opendbc/safety/tests/test_honda_mvl_stock.py",
  "opendbc_repo/opendbc/safety/tests/test_honda_stock_aol.py",
  "opendbc_repo/opendbc/safety/tests/test_mazda_stock_aol.py",
  "opendbc_repo/opendbc/car/mazda/tests/test_stock_aol_pause.py",
  "opendbc_repo/opendbc/safety/tests/test_honda_rdx_gas_cap.py",
  "opendbc_repo/opendbc/safety/tests/test_honda_aol_source.py",
  "opendbc_repo/opendbc/safety/tests/test_honda_aol_family.py",
  "opendbc_repo/opendbc/safety/tests/test_aol_defensive_config.py",
  "opendbc_repo/opendbc/safety/tests/test_honda_nidec_six.py",
  "opendbc_repo/opendbc/safety/tests/test_honda_interceptor.py",
  "opendbc_repo/opendbc/safety/tests/test_honda_bosch_radarless_three.py",
  "opendbc_repo/opendbc/safety/tests/test_subaru_gen2_angle_pair.py",
  "opendbc_repo/opendbc/safety/tests/test_subaru_ascent_angle.py",
  "opendbc_repo/opendbc/safety/tests/test_ford_three.py",
  "opendbc_repo/opendbc/safety/tests/test_hyundai_canfd_carnival.py",
)

# Vehicle tests import both the vendored car code and these host control owners.
# Presentation work can proceed independently; native binaries have separate
# provenance below. Keep result directories outside these source areas.
SOURCE_INPUT_PATHS = (
  "opendbc_repo", "openpilot/cereal", "openpilot/common", "openpilot/selfdrive/car",
  "openpilot/selfdrive/controls", "openpilot/selfdrive/locationd", "openpilot/selfdrive/selfdrived",
  "openpilot/starpilot/aol", "openpilot/starpilot/car", "openpilot/starpilot/lateral", "openpilot/starpilot/longitudinal",
  "openpilot/starpilot/speed_limits", "openpilot/starpilot/schema_cache.py", "msgq_repo", "rednose_repo",
  "openpilot/starpilot/vehicle_preferences.py",
  "openpilot/starpilot/vehicle_startup.py", "openpilot/starpilot/controller_extensions.py",
  "tools/ci", "tools/test_runner.py", "pyproject.toml", "uv.lock", "upstream-sync.json",
)


def source_input_snapshot():
  def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

  untracked = {}
  for raw_path in git("ls-files", "--others", "--exclude-standard", "-z", "--", *SOURCE_INPUT_PATHS).split(b"\0"):
    if raw_path:
      name = os.fsdecode(raw_path)
      path = ROOT / name
      data = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
      untracked[name] = hashlib.sha256(data).hexdigest()
  patch_bytes = git("diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--", *SOURCE_INPUT_PATHS)
  return {"revision": git("rev-parse", "HEAD").decode().strip(), "paths": list(SOURCE_INPUT_PATHS),
          "tracked_patch_sha256": hashlib.sha256(patch_bytes).hexdigest(), "untracked_sha256": untracked}


def sha256(path):
  return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def targets_for(suite):
  if suite == "interfaces":
    car_root = ROOT / "opendbc_repo/opendbc/car"
    return [str(path.relative_to(ROOT)) for path in sorted(car_root.rglob("test_*.py"))
            if path != car_root / "tests/test_models.py"]
  if suite == "safety-debug":
    return [str(path.relative_to(ROOT)) for path in sorted((ROOT / "opendbc_repo/opendbc/safety/tests").glob("test_*.py"))]
  if suite == "safety-release":
    return list(RELEASE_TARGETS)
  raise ValueError(f"Unknown vehicle test suite: {suite}")


def audit_interface_modules(targets, test_ids):
  """Expose empty modules and test declarations unsupported by unittest discovery."""
  modules, errors = [], []
  for target in targets:
    path = ROOT / target
    module = ".".join(path.relative_to(ROOT).with_suffix("").parts)
    selected = [test_id for test_id in test_ids if test_id.startswith(module + ".")]
    declarations = ast.parse(path.read_text(), filename=str(path))
    functions, missing_methods = [], []
    for node in declarations.body:
      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
        functions.append(node.name)
      elif isinstance(node, ast.ClassDef):
        for method in node.body:
          if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name.startswith("test_"):
            expected = f"{module}.{node.name}.{method.name}"
            if not any(test_id == expected or test_id.startswith((expected + "_", expected + "[")) for test_id in selected):
              missing_methods.append(f"{node.name}.{method.name}")
    if not selected:
      errors.append(f"Interface test module collected zero tests: {target}")
    for function in functions:
      expected = f"{module}.{function}"
      if not any(test_id == expected or test_id.startswith(expected + "[") for test_id in selected):
        errors.append(f"Declared module-level test was not collected: {target}: {function}")
    if missing_methods:
      errors.append(f"Declared interface tests were not collected: {target}: {missing_methods}")
    modules.append({"path": target, "source_sha256": sha256(path), "collected_count": len(selected),
                    "module_level_test_functions": functions, "uncollected_test_methods": missing_methods})
  return modules, errors


def interface_coverage(test_ids, platforms):
  prefix = ".TestCarInterfaces.test_car_interfaces_"
  matches = [(test_id.split(prefix, 1)[1], test_id) for test_id in test_ids if prefix in test_id]
  counts = Counter(platform for platform, _ in matches)
  if set(counts) != set(platforms) or any(count != 1 for count in counts.values()):
    missing, extra = sorted(set(platforms) - counts.keys()), sorted(counts.keys() - set(platforms))
    duplicates = sorted(platform for platform, count in counts.items() if count != 1)
    raise ValueError(f"Concrete interface collection mismatch: missing={missing}, extra={extra}, duplicates={duplicates}")
  return dict(matches)


def interface_execution_errors(platform_tests, records):
  by_id = {record["id"]: record for record in records}
  return [f"Concrete interface test for {platform} must pass: {by_id.get(test_id, {}).get('status', 'missing')} ({test_id})"
          for platform, test_id in platform_tests.items() if by_id.get(test_id, {}).get("status") != "passed"]


def vehicle_inventory():
  from opendbc.car.values import PLATFORMS
  from opendbc.car.tests.routes import non_tested_cars, routes
  return {"platform_ids": sorted(PLATFORMS), "platform_count": len(PLATFORMS),
          "platforms_without_route": sorted(set(PLATFORMS) - {str(route.car_model) for route in routes}),
          "declared_route_exemptions": sorted(str(platform) for platform in non_tested_cars)}


def source_provenance():
  def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()
  manifest = ROOT / "upstream-sync.json"
  return {"revision": git("rev-parse", "HEAD"), "status": git("status", "--porcelain"),
          "inputs": source_input_snapshot(),
          "manifest_sha256": sha256(manifest), "dependencies": json.loads(manifest.read_text())["dependencies"],
          "runner_sha256": sha256(ROOT / "tools/test_runner.py"), "suite_runner_sha256": sha256(__file__),
          "pytest_runner_sha256": sha256(ROOT / "tools/ci/vehicle_pytest.py")}


def native_provenance():
  import capnp.lib.capnp as native_capnp
  from opendbc.can import packer, parser
  path = Path(native_capnp.__file__).resolve()
  if not any(str(path).endswith(suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES):
    raise RuntimeError("Vehicle tests require the native pycapnp extension")
  expected = ROOT / "opendbc_repo/opendbc/can"
  if Path(packer.__file__).resolve().parent != expected or Path(parser.__file__).resolve().parent != expected:
    raise RuntimeError("Vehicle tests imported CAN code from outside the tracked dependency")
  return {"pycapnp": {"path": str(path), "sha256": sha256(path)},
          "can_implementation": "tracked upstream Python parser/packer", "can_sources": {
            str(Path(module.__file__).relative_to(ROOT)): sha256(module.__file__) for module in (packer, parser)}}


def build_safety_library(release, output):
  from opendbc.car.structs import CarParams
  from opendbc.safety.tests.libsafety import libsafety_py
  commands = []
  check_call = subprocess.check_call

  def record_command(command, *args, **kwargs):
    commands.append(list(command))
    return check_call(command, *args, **kwargs)

  with patch.object(libsafety_py.subprocess, "check_call", side_effect=record_command):
    built = Path(libsafety_py._build_libsafety(release=release))
  path = output / ("libsafety-release.so" if release else "libsafety-debug.so")
  shutil.copyfile(built, path)
  built.unlink()
  defines_debug = any("-DALLOW_DEBUG" in command for command in commands)
  if defines_debug == release or len(commands) != 2:
    raise RuntimeError("Safety build did not use the requested compile variant")
  libsafety_py.load(path)
  status = libsafety_py.libsafety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0)
  if (status == 0) != (not release):
    raise RuntimeError("Loaded safety library does not match the requested debug/release registry")
  return {"variant": "release" if release else "ALLOW_DEBUG", "path": str(path), "sha256": sha256(path),
          "commands": commands, "compiler": shutil.which(commands[0][0]),
          "compiler_version": subprocess.check_output([commands[0][0], "--version"], text=True).strip(),
          "all_output_hook_available": status == 0,
          "loader_sha256": sha256(libsafety_py.__file__)}


def run(suite, output, collect_only=False):
  output = Path(output).resolve()
  output.mkdir(parents=True, exist_ok=True)
  started = time.monotonic()
  tests, errors = [], []
  pytest_nodeids = []
  records, platform_tests, gate_errors = [], {}, []
  phase = "initialization"
  plan = {"schema_version": 1, "suite": suite, "status": "initializing", "workers": 1,
          "scope": "host synthetic interfaces" if suite == "interfaces" else "host safety hooks",
          "uncovered": ["historical route replay", "hardware and bus integration", "additional downstream vehicles",
                        "independent lateral/longitudinal feature transitions", "device firmware execution"],
          "targets": [], "selected_test_ids": [], "collection_errors": [],
          "fuzz_seed": os.environ.get("FUZZ_SEED"), "max_examples_override": os.environ.get("MAX_EXAMPLES")}
  if suite == "safety-release":
    plan["uncovered"].append("full release-mode behavioral safety suite; only explicit selected classes run")
  (output / "plan.json").write_text(json.dumps(plan, sort_keys=True, indent=2) + "\n")
  try:
    plan["targets"] = targets_for(suite)
    plan["source"] = source_provenance()
    plan.update(vehicle_inventory())
    plan["native"] = native_provenance()
    if suite != "interfaces" and not collect_only:
      plan["native"]["safety"] = build_safety_library(suite == "safety-release", output)
    phase = "collection"
    unittest_targets, pytest_targets = vehicle_pytest.split_targets(ROOT, plan["targets"])
    plan["runners"] = {"unittest": unittest_targets, "pytest": pytest_targets}
    tests, errors = test_runner.collect(unittest_targets, None) if unittest_targets else ([], [])
    pytest_nodeids, pytest_errors = vehicle_pytest.collect(pytest_targets)
    errors.extend(pytest_errors)
    ids = [test.id() for test in tests] + [vehicle_pytest.test_id(nodeid) for nodeid in pytest_nodeids]
    if len(set(ids)) != len(ids):
      errors.append("Vehicle runners selected duplicate test IDs")
    if suite == "interfaces":
      plan["module_collection"], module_errors = audit_interface_modules(plan["targets"], ids)
      errors.extend(module_errors)
      platform_tests = interface_coverage(ids, plan["platform_ids"])
    if not ids:
      errors.append("Vehicle suite collected no tests")
    plan.update(selected_test_ids=ids, interface_test_ids=platform_tests, collection_errors=errors,
                status="error" if errors else "not_run" if collect_only else "ready")
    (output / "plan.json").write_text(json.dumps(plan, sort_keys=True, indent=2) + "\n")
    print(f"{suite}: {len(ids)} tests; {len(platform_tests)} concrete platform interface tests; one process", flush=True)
    if collect_only and not errors:
      return 0
    if not errors:
      phase = "execution"
      records = test_runner.run_batch([test.id() for test in tests], capture_output=True) if tests else []
      pytest_records, pytest_errors = vehicle_pytest.run(pytest_nodeids)
      records.extend(pytest_records)
      errors.extend(pytest_errors)
      phase = "source verification"
      plan["source_after"] = source_provenance()
      if plan["source"].get("inputs") != plan["source_after"].get("inputs"):
        gate_errors.append("Vehicle/control source inputs changed during the suite; rerun against stable source")
  except Exception:
    errors.append(f"{phase} error:\n{traceback.format_exc()}")
    plan["error_phase"] = phase
  ids = [test.id() for test in tests] + [vehicle_pytest.test_id(nodeid) for nodeid in pytest_nodeids]
  records = test_runner.account_for_tests(ids, records, tests)
  if not errors and suite == "interfaces":
    gate_errors.extend(interface_execution_errors(platform_tests, records))
  elapsed = time.monotonic() - started
  exit_code = test_runner.report(records, errors + gate_errors, 10, elapsed)
  status = "error" if errors else "failed" if exit_code else "completed"
  test_runner.write_json_report(output / "results.json", ids, records, errors, elapsed, exit_code)
  result = json.loads((output / "results.json").read_text())
  result.update(status=status, gate_errors=gate_errors)
  if "error_phase" in plan:
    result["error_phase"] = plan["error_phase"]
  (output / "results.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
  by_id = {record["id"]: record for record in records}
  plan.update(status=status, exit_code=exit_code, collection_errors=errors, gate_errors=gate_errors, duration_seconds=elapsed,
              selected_test_ids=ids, interface_test_ids=platform_tests,
              result_counts=dict(Counter(record["status"] for record in records)),
              interface_results={platform: by_id[test_id] for platform, test_id in platform_tests.items()},
              result_sha256=sha256(output / "results.json"))
  if errors:
    (output / "plan.json").write_text(json.dumps(plan, sort_keys=True, indent=2) + "\n")
  (output / "coverage.json").write_text(json.dumps(plan, sort_keys=True, indent=2) + "\n")
  return exit_code


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--suite", choices=("interfaces", "safety-debug", "safety-release"), required=True)
  parser.add_argument("--output", type=Path, required=True)
  parser.add_argument("--collect-only", action="store_true")
  args = parser.parse_args()
  os.chdir(ROOT)
  # Keep the same generated examples across collection, execution, and reruns.
  os.environ.setdefault("FUZZ_SEED", "0")
  return run(args.suite, args.output, args.collect_only)


if __name__ == "__main__":
  raise SystemExit(main())
