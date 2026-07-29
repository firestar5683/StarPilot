import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STATE_SOURCE = ROOT / "selfdrive/ui/lib/starpilot_state.py"
VEHICLE_SETTINGS_SOURCE = ROOT / "selfdrive/ui/layouts/settings/starpilot/vehicle.py"

EV9_CONTROL_KEYS = {
  "EV9LongPreinitPanda",
  "KiaEv9ClusterSideObjectsEnabled",
  "KiaEv9ClusterHeadwayEnabled",
  "KiaEv9ClusterObjectsEnabled",
}


def test_ev9_capability_requires_exact_fingerprint():
  tree = ast.parse(STATE_SOURCE.read_text())
  function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "is_ev9_fingerprint")
  namespace = {}
  exec(compile(ast.Module(body=[function], type_ignores=[]), str(STATE_SOURCE), "exec"), namespace)
  is_ev9_fingerprint = namespace["is_ev9_fingerprint"]

  assert is_ev9_fingerprint("KIA_EV9")
  assert not is_ev9_fingerprint("KIA_EV6")
  assert not is_ev9_fingerprint("KIA_EV9_GT_LINE")
  assert not is_ev9_fingerprint("")


def test_on_device_ev9_controls_are_scoped_to_ev9():
  source = VEHICLE_SETTINGS_SOURCE.read_text()
  scope_start = source.index("    if cs.isEV9:")
  scope_end = source.index("\n    return toggles", scope_start)

  for key in EV9_CONTROL_KEYS:
    occurrences = []
    offset = 0
    while (position := source.find(f'"{key}"', offset)) >= 0:
      occurrences.append(position)
      offset = position + 1

    assert occurrences
    assert all(scope_start < position < scope_end for position in occurrences)
