import ast
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from opendbc.car import structs
from openpilot.starpilot.lateral.bolt_policy import BOLT_GENERATIONS
from openpilot.starpilot.lateral.torque_runtime import TorqueHost, runtime_enabled
from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, FieldChoice, PlatformProfile, serialize_document


class TestBoltTorqueAdmission(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)
    self.params = SimpleNamespace(get_param_path=lambda key: str(self.root / key))

  def cp(self, identity):
    cp = structs.CarParams.new_message()
    cp.brand, cp.carFingerprint = 'gm', identity
    cp.steerControlType = structs.CarParams.SteerControlType.torque
    tune = cp.lateralTuning.init('torque')
    tune.latAccelFactor, tune.latAccelOffset, tune.friction = 2.0, 0.0, 0.1
    return cp

  def document(self, cp, friction=None):
    if friction is None:
      friction = FieldChoice('custom', .14)
    tune = cp.lateralTuning.torque
    basis = (float(tune.latAccelFactor), float(tune.latAccelOffset), float(tune.friction))
    raw = serialize_document({str(cp.carFingerprint): PlatformProfile(basis, FieldChoice(), friction)})
    (self.root / DOCUMENT_KEY).write_bytes(raw)

  def test_defaults_and_canonical_opt_in(self):
    for identity in BOLT_GENERATIONS:
      with self.subTest(identity=identity):
        cp = self.cp(identity)
        for file in self.root.iterdir():
          file.unlink()
        self.assertFalse(runtime_enabled(cp, self.params))
        self.document(cp)
        self.assertTrue(runtime_enabled(cp, self.params))
        (self.root / 'AdvancedLateralTune').write_bytes(b'0')
        self.assertTrue(runtime_enabled(cp, self.params))
        (self.root / 'AdvancedLateralTune').write_bytes(b'1')
        self.assertTrue(runtime_enabled(cp, self.params))

  def test_retired_flag_is_irrelevant_and_document_read_failure_denies(self):
    cp = self.cp(next(iter(BOLT_GENERATIONS)))
    self.document(cp)
    for raw in (b'true', b'2', b'', b'1\n'):
      (self.root / 'AdvancedLateralTune').write_bytes(raw)
      self.assertTrue(runtime_enabled(cp, self.params))
    with patch('openpilot.starpilot.lateral.torque_runtime._raw', side_effect=PermissionError):
      self.assertFalse(runtime_enabled(cp, self.params))

  def test_opt_in_requires_valid_vehicle_friction_document(self):
    cp = self.cp(next(iter(BOLT_GENERATIONS)))
    (self.root / 'AdvancedLateralTune').write_bytes(b'1')
    self.assertFalse(runtime_enabled(cp, self.params))
    self.document(cp, FieldChoice())
    self.assertFalse(runtime_enabled(cp, self.params))
    self.document(self.cp(list(BOLT_GENERATIONS)[1]))
    self.assertFalse(runtime_enabled(cp, self.params))
    (self.root / DOCUMENT_KEY).write_bytes(b'{bad')
    self.assertFalse(runtime_enabled(cp, self.params))
    self.document(cp)
    (self.root / 'ForceAutoTuneOff').write_bytes(b'bad')
    self.assertFalse(runtime_enabled(cp, self.params))

  def test_actual_controls_host_assignment_defaults_and_saved_choice(self):
    source = Path(__file__).resolve().parents[3] / 'selfdrive/controls/controlsd.py'
    tree = ast.parse(source.read_text())
    controls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Controls')
    init = next(node for node in controls.body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
    assignment = next(node for node in init.body if isinstance(node, ast.Assign) and
                      any(isinstance(target, ast.Attribute) and target.attr == 'torque_host' for target in node.targets))
    code = compile(ast.Module(body=[assignment], type_ignores=[]), str(source), 'exec')
    cp = self.cp('CHEVROLET_BOLT_CC_2018_2021')
    current = SimpleNamespace(CP=cp, params=self.params, torque_learning_allowed=False,
                              lateral_controller_selection=SimpleNamespace(policy=None))
    environment = {'self': current, 'TorqueHost': TorqueHost, 'torque_runtime_enabled': runtime_enabled}
    exec(code, environment)
    self.assertIsNone(current.torque_host)
    self.document(cp)
    (self.root / 'AdvancedLateralTune').write_bytes(b'1')
    exec(code, environment)
    self.assertIsInstance(current.torque_host, TorqueHost)


if __name__ == '__main__':
  unittest.main()
