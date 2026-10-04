"""Typed classic SCC admission and physical intent regressions."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.classic_scc_aol import qualified, aol_word, native_accepts, ClassicSccLkasSources
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from openpilot.starpilot.aol.intent import AolSettings, AOL_TOGGLE
from openpilot.starpilot.car.hyundai.aol import policy_for, create_intent

IDENTITIES = (CAR.HYUNDAI_SONATA, CAR.HYUNDAI_ELANTRA, CAR.HYUNDAI_IONIQ,
              CAR.HYUNDAI_KONA_EV, CAR.HYUNDAI_IONIQ_EV_LTD, CAR.HYUNDAI_ELANTRA_2024, CAR.HYUNDAI_ELANTRA_HEV_2024)


def params(identity, source=None):
  fp = gen_empty_fingerprint()
  if source is not None:
    fp[0][source] = 8
  return CarInterface.get_params(identity, fp, [], False, False, False)


class TestClassicSccProfiles(unittest.TestCase):
  def test_typed_factory_marker_retains_stock_tuning(self):
    dashcam = params(CAR.KIA_OPTIMA_H)
    self.assertTrue(dashcam.dashcamOnly)  # Existing different-SCC12-checksum gate.
    self.assertFalse(qualified(dashcam))
    for identity in IDENTITIES:
      for source in (None, 0x391, 0x50c):
        with self.subTest(identity=identity, source=source):
          cp = params(identity, source)
          self.assertTrue(qualified(cp))
          self.assertEqual(bool(cp.flags & HyundaiFlags.HAS_LDA_BUTTON), source is not None)
          before = (cp.mass, cp.wheelbase, cp.steerRatio, cp.lateralTuning.which(),
                    cp.steerActuatorDelay, cp.longitudinalActuatorDelay)
          policy = policy_for(cp)
          cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
          cp.alternativeExperience |= policy.alternative_experience_addition
          self.assertEqual(cp.safetyConfigs[0].safetyParam, aol_word(cp))
          self.assertTrue(native_accepts(cp, int(cp.safetyConfigs[0].safetyModel.raw), aol_word(cp)))
          self.assertFalse(cp.openpilotLongitudinalControl)
          self.assertTrue(cp.pcmCruise)
          self.assertEqual(before, (cp.mass, cp.wheelbase, cp.steerRatio, cp.lateralTuning.which(),
                                    cp.steerActuatorDelay, cp.longitudinalActuatorDelay))

  def test_actual_card_publication_constructs_stock_controls(self):
    import gc
    import os
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.car.card import Car
    from openpilot.selfdrive.controls.controlsd import Controls
    from openpilot.selfdrive.controls.lib.latcontrol_pid import LatControlPID
    from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
    from opendbc.car.hyundai.radar_interface import RadarInterface

    for identity in IDENTITIES:
      for source in (None, 0x391, 0x50c):
        for enabled in (False, True):
          with self.subTest(identity=identity, source=source, aol=enabled), OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
            saved = Params()
            saved.put_bool('OpenpilotEnabledToggle', True, block=True)
            saved.put_bool('AlwaysOnLateral', enabled, block=True)
            saved.put('LKASButtonControl', AOL_TOGGLE, block=True)
            saved.put('MainCruiseButtonControl', AOL_TOGGLE, block=True)
            cp = params(identity, source)
            original_word = int(cp.safetyConfigs[0].safetyParam)
            original_model = cp.safetyConfigs[0].safetyModel
            original_tuning = cp.lateralTuning.which()
            ci = CarInterface(cp)
            card = Car(CI=ci, RI=RadarInterface(cp))
            with structs.CarParams.from_bytes(saved.get('CarParams')) as published:
              self.assertEqual(published.carFingerprint, identity)
              self.assertFalse(published.passive)
              self.assertTrue(published.pcmCruise)
              self.assertFalse(published.openpilotLongitudinalControl)
              self.assertEqual(published.safetyConfigs[0].safetyModel, original_model)
              self.assertEqual(published.safetyConfigs[0].safetyParam, aol_word(published) if enabled else original_word)
              self.assertEqual(published.alternativeExperience, 32 if enabled else 0)
              self.assertEqual(published.lateralTuning.which(), original_tuning)
              self.assertEqual(bool(published.flags & HyundaiFlags.HAS_LDA_BUTTON), source is not None)
            controls = Controls()
            self.assertEqual(controls.CP.to_dict(), card.CP.to_dict())
            self.assertIsInstance(controls.LaC, LatControlPID if original_tuning == 'pid' else LatControlTorque)
            self.assertEqual(card.aol_qualified, enabled)
            del controls, card, ci
            gc.collect()

  def test_namespace_gas_model_long_and_transport_fail_closed(self):
    cp = params(CAR.HYUNDAI_SONATA)
    for field, value in (('flags', int(cp.flags) | int(HyundaiFlags.EV)),
                         ('openpilotLongitudinalControl', True), ('pcmCruise', False),
                         ('passive', True), ('notCar', True), ('alternativeExperience', 1)):
      bad = cp.as_reader().as_builder()
      setattr(bad, field, value)
      self.assertFalse(qualified(bad), field)
    for word in (4, 0x1000, 0x2000, 0x8000, 0x4001):
      bad = cp.as_reader().as_builder()
      bad.safetyConfigs[0].safetyParam = word
      self.assertFalse(qualified(bad))
    bad = cp.as_reader().as_builder()
    bad.safetyConfigs = [structs.CarParams.SafetyConfig(safetyModel='noOutput'), *cp.safetyConfigs]
    self.assertFalse(qualified(bad))
    bad = params(CAR.KIA_OPTIMA_H)
    bad.safetyConfigs[0].safetyModel = structs.CarParams.SafetyModel.hyundai
    self.assertFalse(qualified(bad))
    for identity in (CAR.KIA_FORTE_2019_NON_SCC, CAR.HYUNDAI_IONIQ_5, CAR.KIA_RAY_EV):
      self.assertFalse(qualified(params(identity)))

  def test_physical_lkas_neutral_fault_and_native_rejection(self):
    settings = AolSettings(True, 0., AOL_TOGGLE, 0, (0, 0, 0), (0, 0, 0))
    owner = create_intent(params(CAR.HYUNDAI_SONATA, 0x391), settings)
    cs = structs.CarState(canValid=True, gearShifter='drive')
    cs.cruiseState.available = True
    cs.buttonEvents = [{'type': 'lkas', 'pressed': True}]
    owner.update(cs, now_ns=1, fault_active=False)
    self.assertFalse(owner.allowed_latch)
    cs.buttonEvents = [{'type': 'lkas', 'pressed': False}]
    owner.update(cs, now_ns=2, fault_active=False)
    cs.buttonEvents = [{'type': 'lkas', 'pressed': True}]
    owner.update(cs, now_ns=3, fault_active=False)
    self.assertTrue(owner.allowed_latch)
    owner.update(cs, now_ns=4, native_rejection_ns=4, fault_active=False)
    self.assertFalse(owner.allowed_latch)
    owner.update(cs, now_ns=5, fault_active=False)
    self.assertFalse(owner.allowed_latch)

  def test_main_level_and_fresh_normal_engagement_intent(self):
    settings = AolSettings(True, 0., 0, 0, (0, 0, 0), (0, 0, 0))
    cs = structs.CarState(canValid=True, gearShifter='drive')
    main = create_intent(params(CAR.HYUNDAI_ELANTRA), settings)
    main.update(cs, now_ns=1, fault_active=False)
    self.assertFalse(main.allowed_latch)
    cs.cruiseState.available = True
    main.update(cs, now_ns=2, fault_active=False)
    self.assertTrue(main.allowed_latch)
    cs.canTimeout = True
    main.update(cs, now_ns=3, fault_active=False)
    self.assertFalse(main.allowed_latch)
    cs.canTimeout = False
    assigned = AolSettings(True, 0., AOL_TOGGLE, 0, (0, 0, 0), (0, 0, 0))
    for field in (None, 'gasPressed', 'brakePressed', 'steerFaultTemporary', 'steerFaultPermanent'):
      with self.subTest(field=field):
        owner = create_intent(params(CAR.HYUNDAI_SONATA, 0x391), assigned)
        state = cs.as_reader().as_builder()
        state.cruiseState.enabled = True
        if field:
          setattr(state, field, True)
        owner.update(state, now_ns=4, standard_enabled=False, fault_active=False)
        self.assertFalse(owner.allowed_latch)
        owner.update(state, now_ns=5, standard_enabled=True, fault_active=False)
        self.assertEqual(owner.allowed_latch, field is None)
    # Cancel and a deliberate LKAS press take precedence over auto engage.
    for button in ('cancel', 'lkas'):
      owner = create_intent(params(CAR.HYUNDAI_SONATA, 0x391), assigned)
      cs.cruiseState.enabled = True
      cs.buttonEvents = [{'type': button, 'pressed': True}]
      owner.update(cs, now_ns=6, standard_enabled=True, fault_active=False)
      self.assertFalse(owner.allowed_latch)

  def test_original_sonata_selection_and_elantra_pulse(self):
    now = 1_000_000_000
    hybrid = ClassicSccLkasSources(CAR.HYUNDAI_SONATA_HYBRID)
    sonata = ClassicSccLkasSources(CAR.HYUNDAI_SONATA)
    elantra = ClassicSccLkasSources(CAR.HYUNDAI_ELANTRA_HEV_2024)
    def clu(button=0, swl=0):
      data = bytearray(8)
      data[7] = button
      data[4] = swl << 4
      return bytes(data)
    with patch('opendbc.car.hyundai.classic_scc_aol.time.CLOCK_BOOTTIME', 7, create=True), \
         patch('opendbc.car.hyundai.classic_scc_aol.time.clock_gettime_ns', side_effect=lambda _: now):
      for owner in (hybrid, sonata, elantra):
        owner.update([(now, [(0x391, bytes(8), 0), (0x50c, bytes(8), 0)])])
      now += 10_000_000
      hybrid.update([(now, [(0x50c, clu(swl=4), 0)])])
      self.assertTrue(hybrid.held)
      self.assertEqual(hybrid.selected, 'swl_stat')  # Host selection, never native permission.
      sonata.update([(now, [(0x50c, clu(button=1), 0)])])
      self.assertFalse(sonata.held)  # Original Sonata uses BCM only.
      elantra.update([(now-1, [(0x50c, clu(button=1), 0)]), (now, [(0x50c, clu(), 0)])])
      self.assertTrue(elantra.held)  # Any current-frame pressed sample survives release.
      now += 10_000_000
      elantra.update([(now, [(0x50c, clu(), 0)])])
      self.assertFalse(elantra.held)

  def test_actual_card_fresh_standard_observation_keeps_long_gate(self):
    import ast
    import inspect
    import textwrap
    from openpilot.selfdrive.car.card import Car
    tree = ast.parse(textwrap.dedent(inspect.getsource(Car.state_update)))
    names = ('host_enabled', 'host_control_enabled')
    statements = [node for node in tree.body[0].body if isinstance(node, ast.Assign) and
                  any(isinstance(target, ast.Name) and target.id in names for target in node.targets)]
    self.assertEqual([node.targets[0].id for node in statements], list(names))
    code = compile(ast.Module(body=statements, type_ignores=[]), 'actual-card-host-observation', 'exec')
    call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call) and
                isinstance(node.func, ast.Attribute) and node.func.attr == 'update' and
                isinstance(node.func.value, ast.Attribute) and node.func.value.attr == 'aol_card_intent')
    selected = next(keyword.value for keyword in call.keywords if keyword.arg == 'standard_enabled')
    selector = compile(ast.Expression(selected), 'actual-card-stock-capability', 'eval')
    from openpilot.starpilot.car.hyundai.classic_scc_intent import ClassicSccCardIntent
    from openpilot.starpilot.car.hyundai.forte_intent import ForteCardIntent
    from openpilot.starpilot.car.gm.aol import GmAolCardIntent
    from openpilot.starpilot.aol.intent import AolCardIntent
    self.assertTrue(ClassicSccCardIntent.observe_stock_engagement)
    for intent_type in (ForteCardIntent, GmAolCardIntent, AolCardIntent):
      self.assertFalse(getattr(intent_type, 'observe_stock_engagement', False))

    cp = params(CAR.HYUNDAI_SONATA)
    for valid, alive, previous, enabled, age, healthy in ((True,True,True,True,1,True),
         (False,True,True,True,1,True), (True,False,True,True,1,True),
         (True,True,False,True,1,True), (True,True,True,False,1,True),
         (True,True,True,True,200_000_000,True), (True,True,True,True,1,False)):
      sm = SimpleNamespace(valid={'carControl':valid}, alive={'carControl':alive})
      class Inputs:
        def __getitem__(self, key):
          return SimpleNamespace(enabled=self.enabled)
      inputs = Inputs()
      inputs.enabled = enabled
      inputs.valid, inputs.alive = sm.valid, sm.alive
      context = SimpleNamespace(CP=cp, CC_prev=SimpleNamespace(enabled=previous), sm=inputs)
      scope = {'self':context, 'CS':SimpleNamespace(canValid=healthy, canTimeout=False),
               'now_ns':1_000_000_000, 'control_log_ns':1_000_000_000-age,
               'slc_physical':SimpleNamespace(STATE_MAX_AGE_NS=150_000_000)}
      exec(code, scope)
      self.assertEqual(scope['host_enabled'], all((valid,alive,previous,enabled,healthy)) and age<=150_000_000)
      self.assertFalse(scope['host_control_enabled'])  # Stock SCC cannot enable SLC host LONG.
      for capability in (False, True):
        context.aol_card_intent = SimpleNamespace(observe_stock_engagement=capability)
        self.assertEqual(eval(selector, scope), scope['host_enabled'] if capability else scope['host_control_enabled'])
      context.aol_card_intent = SimpleNamespace()
      self.assertEqual(eval(selector, scope), scope['host_control_enabled'])
      cp.openpilotLongitudinalControl, cp.pcmCruise = True, False
      exec(code, scope)
      self.assertEqual(eval(selector, scope), scope['host_enabled'])
      cp.openpilotLongitudinalControl, cp.pcmCruise = False, True


  def test_source_expiry_and_identical_stamp_never_manufacture_neutral(self):
    owner = ClassicSccLkasSources(CAR.HYUNDAI_ELANTRA_HEV_2024)
    now = 1_000_000_000
    pressed = bytes([0x10]) + bytes(7)
    with patch('opendbc.car.hyundai.classic_scc_aol.time.CLOCK_BOOTTIME', 7, create=True), \
         patch('opendbc.car.hyundai.classic_scc_aol.time.clock_gettime_ns', side_effect=lambda _: now):
      owner.update([(now, [(0x391, bytes(8), 0)])])
      now += 10_000_000
      owner.update([(now, [(0x391, pressed, 0)])])
      self.assertEqual(owner.edges, [True])
      now += 310_000_000
      owner.update([])
      self.assertEqual(owner.edges, [])
      self.assertFalse(owner.neutral_seen)
      owner.update([(now, [(0x391, pressed, 0)])])
      self.assertEqual(owner.edges, [])
      owner.update([(now, [(0x391, bytes(8), 0)])])
      self.assertEqual(owner.edges, [])
      self.assertFalse(owner.neutral_seen)
      now += 10_000_000
      owner.update([(now, [(0x391, bytes(8), 0)])])
      self.assertEqual(owner.edges, [False])
      now += 10_000_000
      owner.update([(now, [(0x391, pressed, 0)])])
      self.assertEqual(owner.edges, [True])

  def test_partial_dropout_other_source_neutral_cannot_rearm_held_source(self):
    owner = ClassicSccLkasSources(CAR.HYUNDAI_ELANTRA_HEV_2024)
    now = 1_000_000_000
    pressed = bytes([0x10]) + bytes(7)
    with patch('opendbc.car.hyundai.classic_scc_aol.time.CLOCK_BOOTTIME', 7, create=True), \
         patch('opendbc.car.hyundai.classic_scc_aol.time.clock_gettime_ns', side_effect=lambda _: now):
      owner.update([(now, [(0x391, bytes(8), 0)])])
      now += 10_000_000
      owner.update([(now, [(0x391, pressed, 0)])])
      self.assertEqual(owner.edges, [True])
      now += 310_000_000
      owner.update([(now, [(0x50c, bytes(8), 0)])])
      self.assertEqual(owner.edges, [])
      self.assertFalse(owner.neutral_seen)
      now += 10_000_000
      owner.update([(now, [(0x391, pressed, 0)])])
      self.assertEqual(owner.edges, [])
      now += 10_000_000
      owner.update([(now, [(0x391, bytes(8), 0)])])
      self.assertEqual(owner.edges, [False])
      now += 10_000_000
      owner.update([(now, [(0x391, pressed, 0)])])
      self.assertEqual(owner.edges, [True])
