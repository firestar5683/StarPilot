import ast

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GALAXY_PATH = REPO_ROOT / "starpilot/system/the_galaxy/the_galaxy.py"


def _function_nodes(source, *names):
  tree = ast.parse(source)
  wanted = set(names)
  return {
    node.name: node
    for node in ast.walk(tree)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted
  }


def _called_names(node):
  names = set()
  for child in ast.walk(node):
    if not isinstance(child, ast.Call):
      continue
    if isinstance(child.func, ast.Name):
      names.add(child.func.id)
    elif isinstance(child.func, ast.Attribute):
      names.add(child.func.attr)
  return names


def test_starpilot_daemon_subscribes_only_to_derived_vehicle_state():
  source = (REPO_ROOT / "starpilot/system/vehicle_telemetryd.py").read_text()
  tree = ast.parse(source)
  services = next(
    ast.literal_eval(node.value)
    for node in tree.body
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "VEHICLE_TELEMETRY_SERVICES" for target in node.targets)
  )
  assert services == ["starpilotCarState", "pandaStates", "carParams", "deviceState"]
  assert '"can"' not in source
  assert "from panda" not in source
  assert "import panda" not in source
  assert "can_recv" not in source


def test_galaxy_has_no_legacy_raw_can_telemetry_sampler():
  source = GALAXY_PATH.read_text()
  for forbidden in (
    "_VEHICLE_TELEMETRY_CAN_SM",
    "def _capture_can_frames",
    "def _build_egmp_can_telemetry_payload",
    "def _build_vehicle_telemetry_payload",
    "def _start_vehicle_telemetry_background_sampler",
    '"/api/vehicle/telemetry/samples"',
    '"/api/vehicle/telemetry/known"',
  ):
    assert forbidden not in source


def test_galaxy_telemetry_routes_are_cache_only():
  source = GALAXY_PATH.read_text()
  route_names = (
    "vehicle_telemetry",
    "vehicle_telemetry_status",
    "vehicle_telemetry_config",
    "galaxy_session",
    "create_external_app_pairing",
    "pair_external_app",
  )
  functions = _function_nodes(source, *route_names)
  assert set(functions) == set(route_names)

  forbidden_calls = {"CANParser", "Panda", "SubMaster", "sub_sock", "can_send"}
  for name, node in functions.items():
    assert not (_called_names(node) & forbidden_calls), name
