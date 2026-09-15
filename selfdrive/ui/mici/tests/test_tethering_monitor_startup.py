import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def _method(path: str, class_name: str, method_name: str) -> ast.FunctionDef:
  tree = ast.parse((ROOT / path).read_text())
  cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
  return next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name)


def _calls(method: ast.FunctionDef, name: str) -> list[ast.Call]:
  return [node for node in ast.walk(method) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name]


def test_mici_starts_tethering_monitor_before_opening_settings():
  main_init = _method("selfdrive/ui/mici/layouts/main.py", "MiciMainLayout", "__init__")
  manager_creation = _calls(main_init, "WifiManager")
  assert any(any(keyword.arg == "active" and isinstance(keyword.value, ast.Constant) and keyword.value.value is False
                 for keyword in call.keywords) for call in manager_creation)

  open_settings = _method("selfdrive/ui/mici/layouts/main.py", "MiciMainLayout", "_open_settings")
  settings_creation = _calls(open_settings, "SettingsLayout")
  assert any(len(call.args) == 1 and isinstance(call.args[0], ast.Attribute) and call.args[0].attr == "_wifi_manager"
             for call in settings_creation)

  settings_init = _method("selfdrive/ui/mici/layouts/settings/settings.py", "SettingsLayout", "__init__")
  network_creation = _calls(settings_init, "NetworkLayoutMici")
  assert any(len(call.args) == 1 and isinstance(call.args[0], ast.Name) and call.args[0].id == "wifi_manager"
             for call in network_creation)

  network_init = _method("selfdrive/ui/mici/layouts/settings/network/network_layout.py", "NetworkLayoutMici", "__init__")
  assert any(isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Attribute) and target.attr == "_wifi_manager" for target in node.targets)
             and isinstance(node.value, ast.Name) and node.value.id == "wifi_manager"
             for node in ast.walk(network_init))
