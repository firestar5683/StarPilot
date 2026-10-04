import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[3]
BOLT = 'gm.CHEVROLET_BOLT_CC_2018_2021'


def fingerprints(path):
  tree = ast.parse(path.read_text())
  node = next((item.value for item in tree.body if isinstance(item, ast.Assign) and
               any(isinstance(target, ast.Name) and target.id == 'FINGERPRINTS' for target in item.targets)), None)
  if node is None:
    return {}
  uses = [item for item in ast.walk(tree) if isinstance(item, ast.Name) and item.id == "FINGERPRINTS"]
  if len(uses) != 1 or not isinstance(node, ast.Dict):
    raise ValueError("Fingerprint inventory requires evaluation of dynamic declarations")
  return {f'{path.parent.name}.{key.attr}': ast.literal_eval(value) for key, value in zip(node.keys, node.values)}


def production_eliminator(inventory):
  tree = ast.parse((ROOT / 'car/fingerprints.py').read_text())
  tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and
               node.name in ('is_valid_for_fingerprint', 'eliminate_incompatible_cars')]
  scope = dict(_FINGERPRINTS=inventory, _DEBUG_ADDRESS={1880: 8})
  exec(compile(tree, 'fingerprints.py', 'exec'), scope)
  return scope['eliminate_incompatible_cars']


class TestBoltAutoFingerprint(unittest.TestCase):
  def setUp(self):
    self.inventory = {}
    for path in (ROOT / 'car').glob('*/fingerprints.py'):
      self.inventory.update(fingerprints(path))
    self.eliminate = production_eliminator(self.inventory)

  def candidates(self, messages):
    candidates = list(self.inventory)
    for address, length in messages:
      candidates = self.eliminate(SimpleNamespace(address=address, dat=bytes(length)), candidates)
    return candidates

  def test_expected_bolt_tables(self):
    variants = self.inventory[BOLT]
    self.assertEqual(len(variants), 8)
    digest = hashlib.sha256(json.dumps(variants, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    self.assertEqual(digest, 'e255d49d3b5322c990405ed8e8a9591087a2dc88452ca46fc38ea911518ffda9')

  def test_all_variants_uniquely_identify_bolt(self):
    self.assertGreaterEqual(len(self.inventory), 22)
    for index, variant in enumerate(self.inventory[BOLT]):
      with self.subTest(variant=index):
        self.assertEqual(self.candidates(variant.items()), [BOLT])

  def test_pedal_does_not_eliminate_any_bolt_variant(self):
    for index, variant in enumerate(self.inventory[BOLT]):
      with self.subTest(variant=index):
        self.assertEqual(self.candidates([*variant.items(), (0x201, 6)]), [BOLT])

  def test_incorrect_pedal_length_eliminates_bolt(self):
    self.assertEqual(self.eliminate(SimpleNamespace(address=0x201, dat=bytes(7)), [BOLT]), [])

  def test_existing_variants_do_not_gain_bolt_collision(self):
    for car, variants in self.inventory.items():
      if car == BOLT:
        continue
      for index, variant in enumerate(variants):
        with self.subTest(car=car, variant=index):
          baseline = [candidate for candidate in self.candidates(variant.items()) if candidate != BOLT]
          if baseline == [car]:
            self.assertEqual(self.candidates(variant.items()), [car])


if __name__ == '__main__':
  unittest.main()
