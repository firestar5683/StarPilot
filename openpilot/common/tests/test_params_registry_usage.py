import ast
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
KEY_METHODS = {
  'get', 'get_bool', 'get_int', 'get_float', 'put', 'put_bool', 'put_int', 'put_float',
  'put_nonblocking', 'put_bool_nonblocking', 'remove', 'get_default_value', 'check_key',
  'get_type', 'get_param_path', 'cpp2python',
}


def literal_params_calls(source):
  tree = ast.parse(source)
  owners = set()
  mappings = set()
  for node in ast.walk(tree):
    if not isinstance(node, (ast.Assign, ast.AnnAssign)):
      continue
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    value = node.value
    if isinstance(value, ast.Call) and ast.unparse(value.func).split('.')[-1] == 'Params':
      owners.update(ast.unparse(target) for target in targets)
    if (isinstance(value, ast.Dict) or
        isinstance(value, ast.Attribute) and value.attr == 'query_params'):
      mappings.update(ast.unparse(target) for target in targets)
  for node in ast.walk(tree):
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr not in KEY_METHODS:
      continue
    receiver = ast.unparse(node.func.value)
    direct = isinstance(node.func.value, ast.Call) and ast.unparse(node.func.value.func).split('.')[-1] == 'Params'
    conventional = re.search(r'(?:^|\.)(?:params\w*|\w*_params)$', receiver) is not None
    if not direct and (receiver not in owners and not conventional or receiver in mappings and receiver not in owners):
      continue
    key = node.args[0] if node.args else next((keyword.value for keyword in node.keywords if keyword.arg == 'key'), None)
    if isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value:
      yield node.lineno, key.value


def test_literal_runtime_params_keys_are_registered():
  registered = set(re.findall(r'^\s*\{"([^"\n]+)",', (ROOT / 'openpilot/common/params_keys.h').read_text(), re.MULTILINE))
  assert registered
  missing = []
  for base in (ROOT / 'openpilot', ROOT / 'opendbc_repo/opendbc'):
    for path in sorted(base.rglob('*.py')):
      if {'tests', 'test', '__pycache__'} & set(path.parts):
        continue
      for line, key in literal_params_calls(path.read_text()):
        if key not in registered:
          missing.append(f'{path.relative_to(ROOT)}:{line}: {key}')
  assert not missing, '\n'.join(missing)


def test_audit_recognizes_direct_conventional_constructor_and_keyword_calls():
  source = '''
params.get("Read")
self.params.put_bool("Write", True)
store = Params()
store.get_default_value("Default")
Params().get_bool(key="Direct")
params.get(dynamic_key)
raw_namespace.joinpath("LegacyOnly").read_bytes()
'''
  assert [key for _, key in literal_params_calls(source)] == ['Read', 'Write', 'Default', 'Direct']


def test_audit_excludes_query_dicts_and_empty_namespace_path():
  source = '''
params = server.query_params
params.get("provider")
query_params = {"provider": "test"}
query_params.get("provider")
Params().get_param_path("")
'''
  assert list(literal_params_calls(source)) == []
