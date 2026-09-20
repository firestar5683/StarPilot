import ast
import importlib.util
from pathlib import Path

PATH = Path(__file__).parents[1] / 'prototype' / 'parked_car_evidence.py'
spec = importlib.util.spec_from_file_location('parked_car_evidence', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_redacts_nested_vin_and_retains_exact_firmware_bytes():
  assert module.clean({'carVin': 'private', 'nested': {'vin': 'secret', 'fwVersion': b'Y4003.05.4'}}) == {
    'nested': {'fwVersion': {'ascii': 'Y4003.05.4', 'hex': '59343030332e30352e34'}}}


def test_collector_has_no_publish_param_mutation_or_shell_calls():
  tree = ast.parse(PATH.read_text())
  forbidden = {'PubMaster', 'pub_sock', 'send', 'put', 'put_bool', 'put_nonblocking', 'remove',
               'system', 'Popen', 'run', 'check_output'}
  calls = [node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
  assert not forbidden.intersection(calls)
