import unittest
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.car.hyundai.blended_longitudinal import BlendedLongitudinalOwner, DISABLE, ENABLE, Phase, Outcome
from opendbc.car.hyundai.values import HyundaiFlags


class TestBlendedLifecycle(unittest.TestCase):
  def setUp(self):
    self.scope = patch('opendbc.car.hyundai.blended_longitudinal.is_blended', return_value=True)
    self.scope.start()
    self.addCleanup(self.scope.stop)
    self.cp = SimpleNamespace(flags=HyundaiFlags.CANFD_LKA_STEER_MSG.value,
                              openpilotLongitudinalControl=True, pcmCruise=False,
                              safetyConfigs=[SimpleNamespace(safetyParam=0x2014)])
    self.calls = []

  def owner(self, exchange):
    return BlendedLongitudinalOwner(self.cp, SimpleNamespace(ECAN=1), exchange,
                                    restore_exchange=lambda *a, **kw: exchange(*a, **kw, com_cont_req=ENABLE, reset=True, require_response=True))

  def test_rejected_start_restores_stock_and_exact_ecu(self):
    def exchange(*args, **kwargs):
      self.calls.append(kwargs)
      return kwargs['com_cont_req'] == ENABLE
    owner = self.owner(exchange)
    self.assertEqual(owner.begin(None, None, unpublished=True, admission=True).outcome, Outcome.STOCK)
    self.assertEqual([c['com_cont_req'] for c in self.calls], [DISABLE, ENABLE])
    self.assertTrue(self.calls[-1]['require_response'])
    self.assertEqual(ENABLE, b'\x28\x00\x01')
    self.assertTrue(all(c['bus'] == 1 and c['addr'] == 0x730 and c['reset'] is True for c in self.calls))
    self.assertEqual(self.cp.safetyConfigs[0].safetyParam, 0x2010)
    self.assertFalse(self.cp.openpilotLongitudinalControl)
    self.assertTrue(self.cp.pcmCruise)
    self.assertFalse(owner.active())
    self.assertEqual(owner.phase, Phase.RESTORED)

  def test_cancel_during_disable_never_grants_long_ownership(self):
    def exchange(*args, **kwargs):
      self.calls.append(kwargs)
      if kwargs['com_cont_req'] == DISABLE:
        owner.cancel()
      return True
    owner = self.owner(exchange)
    self.assertEqual(owner.begin(None, None, unpublished=True, admission=True).outcome, Outcome.STOCK)
    self.assertEqual(len(self.calls), 2)
    self.assertFalse(owner.active())
    self.assertTrue(owner.restore_confirmed)

  def test_success_then_deinit_and_restore_failure_not_reported_success(self):
    owner = self.owner(lambda *args, **kw: kw['com_cont_req'] == DISABLE)
    self.assertEqual(owner.begin(None, None, unpublished=True, admission=True).outcome, Outcome.OWNED)
    self.assertTrue(owner.active())
    self.assertFalse(owner.restore(None, None))
    self.assertEqual(owner.phase, Phase.FAILED)
    self.assertFalse(owner.active())

  def test_published_cp_or_missing_admission_cannot_start(self):
    owner = self.owner(lambda *a, **k: self.fail('Unexpected ECU exchange'))
    with self.assertRaises(RuntimeError):
      owner.begin(None, None, unpublished=False, admission=True)
    self.assertEqual(self.cp.safetyConfigs[0].safetyParam, 0x2014)
    self.assertEqual(owner.begin(None, None, unpublished=True, admission=False).outcome, Outcome.STOCK_UNTOUCHED)
    self.assertEqual(self.cp.safetyConfigs[0].safetyParam, 0x2010)

  def test_partial_disable_and_restore_timeout_cannot_admit_stock_cp(self):
    owner = self.owner(lambda *args, **kwargs: False)
    result = owner.begin(None, None, unpublished=True, admission=True)
    self.assertEqual(result.outcome, Outcome.ABORT_UNCERTAIN)
    self.assertFalse(result.admissible)
    with self.assertRaises(TypeError):
      bool(result)
    with self.assertRaises(RuntimeError):
      owner.publication_cp()
    self.assertFalse(owner.active())

  def test_cancelled_constructor_with_failed_restore_forbids_continuation(self):
    def exchange(*args, **kwargs):
      if kwargs['com_cont_req'] == DISABLE:
        owner.cancel()
        return True
      return False
    owner = self.owner(exchange)
    result = owner.begin(None, None, unpublished=True, admission=True)
    self.assertEqual(result.outcome, Outcome.ABORT_UNCERTAIN)
    with self.assertRaises(RuntimeError):
      owner.publication_cp()

  def test_real_protocol_empty_response_cannot_confirm_restoration(self):
    from opendbc.car.hyundai.blended_disable_ecu import disable_ecu

    class Query:
      def __init__(self, *args, **kwargs):
        self.request = args[4][0]

      def get_data(self, *args, **kwargs):
        return {(0x738, None): b''} if self.request == b'\x10\x03' else {}
    with patch('opendbc.car.hyundai.blended_disable_ecu.IsoTpParallelQuery', Query), \
         patch('opendbc.car.hyundai.blended_disable_ecu.time.sleep'):
      self.assertFalse(disable_ecu(None, None, bus=1, addr=0x730, com_cont_req=ENABLE,
                                   reset=True, retry=1, require_response=True))

  def test_restore_query_requires_unsuppressed_request_and_exact_ack_prefix(self):
    from opendbc.car.hyundai.blended_disable_ecu import restore_ecu

    class Query:
      reply = True

      def __init__(self, *args, **kwargs):
        self.request, self.response = args[4][0], args[5][0]
        if self.request == ENABLE and self.response != b'\x68\x00':
          raise AssertionError('Restoration requires matched acknowledgment')

      def get_data(self, *args, **kwargs):
        return {(0x738, None): b''} if self.request == b'\x10\x03' or self.reply else {}
    with patch('opendbc.car.hyundai.blended_disable_ecu.IsoTpParallelQuery', Query):
      self.assertEqual(ENABLE, b'\x28\x00\x01')
      self.assertTrue(restore_ecu(None, None, bus=1, addr=0x730, retry=1))
      Query.reply = False
      self.assertFalse(restore_ecu(None, None, bus=1, addr=0x730, retry=1))

  def test_real_precreate_builder_clone_has_no_source_alias(self):
    from opendbc.car import gen_empty_fingerprint
    from opendbc.car.hyundai.interface import CarInterface
    from opendbc.car.hyundai.values import CAR
    from opendbc.car.hyundai.blended_longitudinal import candidate_from_stock
    cp = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, gen_empty_fingerprint(), [], False, False, False)
    before = cp.to_bytes()
    self.assertIsNone(candidate_from_stock(cp, alpha_requested=True))
    candidate = candidate_from_stock(cp, alpha_requested=True, native_qualified=True)
    self.assertIsNotNone(candidate)
    cp.clear_write_flag()
    self.assertEqual(cp.to_bytes(), before)
    self.assertTrue(candidate.openpilotLongitudinalControl)
    self.assertEqual(candidate.safetyConfigs[0].safetyParam, 0x2004)
    candidate.pcmCruise = True
    cp.clear_write_flag()
    self.assertEqual(cp.to_bytes(), before)

  def test_alpha_candidate_radar_and_final_fields_preserve_stock_builder(self):
    from opendbc.car.hyundai.tests.test_palisade_2023 import params
    from opendbc.car.hyundai.blended_longitudinal import candidate_from_stock
    for hda2 in (False, True):
      for radar_unavailable in (False, True):
        cp = params('hdaii' if hda2 else 'hdai')
        cp.radarUnavailable = radar_unavailable
        before = cp.to_dict()
        candidate = candidate_from_stock(cp, alpha_requested=True, native_qualified=True)
        self.assertIsNotNone(candidate)
        self.assertTrue(candidate.radarUnavailable)
        self.assertTrue(candidate.openpilotLongitudinalControl)
        self.assertFalse(candidate.pcmCruise)
        self.assertEqual(candidate.safetyConfigs[0].safetyParam, 0x2014 if hda2 else 0x2004)
        expected = dict(before)
        expected.update(alphaLongitudinalAvailable=True, openpilotLongitudinalControl=True,
                        pcmCruise=False, radarUnavailable=True, stopAccel=candidate.stopAccel,
                        safetyConfigs=candidate.to_dict()['safetyConfigs'])
        self.assertEqual(candidate.to_dict(), expected)
        self.assertEqual(cp.to_dict(), before)

  def test_actual_card_constructor_failure_closes_registered_owner(self):
    import openpilot.selfdrive.car.card as card
    calls = []

    class PartialCar:
      def __init__(self):
        self.vehicle_startup = SimpleNamespace(close=lambda: calls.append('closed'))
        raise RuntimeError('Constructor failed after owner registration')
    with patch.object(card, 'Car', PartialCar), patch.object(card, 'config_realtime_process'):
      with self.assertRaisesRegex(RuntimeError, 'Constructor failed'):
        card.main()
    self.assertEqual(calls, ['closed'])

  def test_actual_prepare_without_admission_configure_close_leaves_stock_untouched(self):
    from opendbc.car import gen_empty_fingerprint
    from opendbc.car.hyundai.interface import CarInterface
    from opendbc.car.hyundai.values import CAR
    from opendbc.car.hyundai.blended_longitudinal import BlendedStartup
    cp = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, gen_empty_fingerprint(), [], False, False, False)
    startup = BlendedStartup(cp, cp, (lambda *a: self.fail('Unexpected receive'),
                                     lambda *a: self.fail('Unexpected send')))
    selected = startup.prepare(admission=lambda: False)
    self.assertIs(selected, cp)
    self.assertEqual(startup.owner.result.outcome, Outcome.STOCK_UNTOUCHED)
    self.assertFalse(startup.owner.takeover_attempted)
    self.assertFalse(startup.owner.restore_confirmed)
    startup.configure(SimpleNamespace(CC=SimpleNamespace()))
    startup.close()
    startup.close()
    self.assertFalse(cp.openpilotLongitudinalControl)

  def test_post_handoff_close_without_diagnostic_admission_never_sends_uds(self):
    from opendbc.car import gen_empty_fingerprint
    from opendbc.car.hyundai.interface import CarInterface
    from opendbc.car.hyundai.values import CAR
    from opendbc.car.hyundai.blended_longitudinal import BlendedStartup
    cp = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, gen_empty_fingerprint(), [], False, False, False)
    startup = BlendedStartup(cp, cp, (lambda *a: self.fail('Unexpected receive'),
                                     lambda *a: self.fail('Unexpected send')))
    startup.owner.takeover_attempted = True
    startup.owner.phase = Phase.OWNED
    startup.diagnostic_admission = lambda: False
    with self.assertRaisesRegex(RuntimeError, 'Diagnostic admission unavailable'):
      startup.close()
    self.assertEqual(startup.owner.result.outcome, Outcome.ABORT_UNCERTAIN)

  def test_actual_parser_rewarm_requires_every_source_after_transaction_floor(self):
    from opendbc.car.hyundai.tests.test_palisade_2023 import params, feed
    from opendbc.car.hyundai.interface import CarInterface
    from opendbc.car.hyundai.blended_longitudinal import BlendedStartup, candidate_from_stock, TakeoverResult
    cp = params('hdai')
    ci = CarInterface(cp)
    for tick in range(12):
      feed(ci, tick)
    candidate = candidate_from_stock(cp, alpha_requested=True, native_qualified=True)
    startup = BlendedStartup(cp, candidate, (lambda *a: None, lambda *a: None))
    startup.owner.phase = Phase.OWNED
    startup.owner.result = TakeoverResult(Outcome.OWNED)
    startup.source_floor_ns = 1_100_000_000
    self.assertTrue(startup.sources_current(ci, 1_120_000_000))
    startup.source_floor_ns = 1_110_000_000
    self.assertFalse(startup.sources_current(ci, 1_120_000_000))

  def test_actual_publish_ack_occurs_after_send_lock_release_before_worker_stop(self):
    import openpilot.selfdrive.car.card as card
    from openpilot.starpilot.vehicle_startup import VehicleStartupOwner
    context = VehicleStartupOwner()
    calls = []

    def sent(frames, *, valid):
      acquired = context.send_lock.acquire(blocking=False)
      self.assertTrue(acquired, 'Worker join would deadlock while sender lock is held')
      if acquired:
        context.send_lock.release()
      self.assertEqual(calls, ['published'])
      calls.append('ack')
    context.owner = SimpleNamespace(sent=sent)
    car = card.Car.__new__(card.Car)
    car.vehicle_startup = context
    car.pm = SimpleNamespace(send=lambda *args: calls.append('published'))
    card.Car.publish_sendcan(car, [], valid=True)
    self.assertEqual(calls, ['published', 'ack'])

  def test_handoff_waits_for_sent_tester_and_later_panda_loss_inhibits(self):
    from opendbc.car.hyundai.tests.test_palisade_2023 import params
    from opendbc.car.hyundai.blended_longitudinal import BlendedStartup, candidate_from_stock, TakeoverResult
    cp = params('hdai')
    candidate = candidate_from_stock(cp, alpha_requested=True, native_qualified=True)
    startup = BlendedStartup(cp, candidate, (lambda *a: None, lambda *a: None))
    startup.owner.phase = Phase.OWNED
    startup.owner.result = TakeoverResult(Outcome.OWNED)
    self.assertTrue(startup.before_control(configured=True, sources_current=True, control_current=True))
    self.assertFalse(startup.handed_off)
    self.assertFalse(startup.stop_event.is_set())
    startup.sent([], valid=True)
    self.assertFalse(startup.handed_off)
    from opendbc.car import make_tester_present_msg
    tester = make_tester_present_msg(startup.owner.address, startup.owner.bus, suppress_response=True)
    startup.sent([tester], valid=False)
    self.assertFalse(startup.handed_off)
    startup.sent([tester], valid=True)
    self.assertTrue(startup.handed_off)
    self.assertTrue(startup.stop_event.is_set())
    self.assertFalse(startup.before_control(configured=False, sources_current=True, control_current=True))
    startup.check()
    self.assertTrue(startup.owner.active())
    self.assertTrue(startup.before_control(configured=True, sources_current=True, control_current=True))

  def test_transient_sources_pause_output_and_keep_only_owned_diagnostics(self):
    from opendbc.car.hyundai.tests.test_palisade_2023 import params
    from opendbc.car.hyundai.blended_longitudinal import BlendedStartup, candidate_from_stock, TakeoverResult
    from opendbc.car import make_tester_present_msg
    cp = params('hdai')
    candidate = candidate_from_stock(cp, alpha_requested=True, native_qualified=True)
    sent = []
    now = [10.]
    startup = BlendedStartup(cp, candidate, (lambda *a: None, lambda frames: sent.extend(frames)))
    startup.clock = lambda: now[0]
    startup.started_at = 1.
    startup.owner.phase = Phase.OWNED
    startup.owner.result = TakeoverResult(Outcome.OWNED)
    tester = make_tester_present_msg(startup.owner.address, startup.owner.bus, suppress_response=True)
    startup.sent([tester], valid=True)
    self.assertTrue(startup.handed_off)
    for missing in ('sources_current', 'control_current'):
      evidence = {'configured': True, 'sources_current': True, 'control_current': True}
      evidence[missing] = False
      self.assertFalse(startup.before_control(**evidence))
      startup.check()
      self.assertTrue(startup.owner.active())
    now[0] = 10.9
    startup.maintain(configured=True)
    self.assertEqual(sent, [])
    now[0] = 11.
    startup.maintain(configured=True)
    self.assertEqual(sent, [tester])
    startup.maintain(configured=True)
    self.assertEqual(sent, [tester])
    now[0] = 11.1
    startup.maintain(configured=False)
    self.assertEqual(sent, [tester])
    self.assertFalse(startup.before_control(configured=False, sources_current=True, control_current=True))
    # Continuous diagnostic cadence is maintained during a long control/input
    # pause. This does not assert session continuity across a long Panda outage.
    for second in range(12, 81):
      now[0] = float(second)
      startup.maintain(configured=True)
    self.assertEqual(sent, [tester] * 70)
    self.assertIsNone(startup.fault, 'Startup-only deadline must not end a running drive')
    self.assertTrue(startup.before_control(configured=True, sources_current=True, control_current=True))
    now[0] = 80.5
    startup.sent([tester], valid=True)
    now[0] = 81.4
    startup.maintain(configured=True)
    self.assertEqual(sent, [tester] * 70, 'A normal sent tester must update diagnostic cadence')

  def test_actual_card_maintenance_runs_before_initialization_and_never_applies(self):
    import openpilot.selfdrive.car.card as card
    calls = []
    CS = SimpleNamespace()
    car = card.Car.__new__(card.Car)
    car.state_update = lambda: (CS, None)
    car.state_publish = lambda *args: calls.append('state')
    car.CP = SimpleNamespace(passive=False)

    class SM(dict):
      seen = {'onroadEvents': False}
    car.sm = SM(onroadEvents=[])
    car.vehicle_startup = SimpleNamespace(owner=object(), maintain=lambda **kw: calls.append(('maintain', kw)))
    car.startup_panda_configured = lambda: True
    car.controls_update = lambda *args: self.fail('Controls are not initialized')
    card.Car.step(car)
    self.assertEqual(calls, [('maintain', {'configured': True}), 'state'])
    self.assertIs(car.CS_prev, CS)


class TestBlendedStartupScope(unittest.TestCase):
  def test_factory_availability_does_not_select_long_and_excludes_hdaii_release(self):
    from opendbc.car.hyundai.tests.test_palisade_2023 import params
    from opendbc.car.hyundai.blended_longitudinal import startup_owner
    for topology in ('hdai', '110', 'hdaii'):
      for release in (False, True):
        cp = params(topology, alpha=True, release=release)
        enabled = topology != 'hdaii' and not release
        self.assertEqual(cp.alphaLongitudinalAvailable, enabled)
        self.assertFalse(cp.openpilotLongitudinalControl)
        self.assertTrue(cp.pcmCruise)
        before = cp.to_dict()
        callbacks = (lambda *a: None, lambda *a: None)
        self.assertIsNone(startup_owner(cp, callbacks, requested=False))
        owner = startup_owner(cp, callbacks, requested=True)
        self.assertEqual(owner is not None, enabled)
        if owner is not None:
          self.assertEqual(owner.owner.cp.safetyConfigs[0].safetyParam, 0x2004)
          self.assertIs(owner.prepare(admission=lambda: False), cp)
          owner.close()
        self.assertEqual(cp.to_dict(), before)

  def test_exact_gate_and_consumed_stopping_owner_agree(self):
    from opendbc.car.hyundai.tests.test_palisade_2023 import params
    from opendbc.car.hyundai.blended_longitudinal import hdai_startup_qualified, candidate_from_stock
    from opendbc.car.hyundai.blended_stopping import eligible
    stock = params()
    active = candidate_from_stock(stock, alpha_requested=True, native_qualified=hdai_startup_qualified(stock))
    self.assertTrue(hdai_startup_qualified(active))
    self.assertTrue(eligible(active))
    self.assertFalse(eligible(stock))
    for field, value in (('passive', True), ('dashcamOnly', True), ('notCar', True),
                         ('alternativeExperience', 32), ('carFingerprint', 'foreign')):
      cp = active.as_reader().as_builder()
      setattr(cp, field, value)
      self.assertFalse(hdai_startup_qualified(cp), field)
      self.assertFalse(eligible(cp), field)
    for flag in (HyundaiFlags.USE_FCA, HyundaiFlags.CANFD_LKA_STEER_MSG, HyundaiFlags.LEGACY):
      cp = active.as_reader().as_builder()
      cp.flags |= flag.value
      self.assertFalse(hdai_startup_qualified(cp))
    self.assertFalse(hdai_startup_qualified(stock, is_release=True))

  def test_active_constructor_requires_exact_prepared_transaction(self):
    from opendbc.car.hyundai.tests.test_palisade_2023 import params
    from opendbc.car.hyundai.blended_longitudinal import BlendedStartup, candidate_from_stock, TakeoverResult
    from opendbc.car.hyundai.interface import CarInterface
    from openpilot.starpilot.vehicle_startup import VehicleStartupOwner
    stock = params()
    active = candidate_from_stock(stock, alpha_requested=True, native_qualified=True)
    # Use the actual interface dispatcher while avoiding parser construction.

    class Interface(CarInterface):
      pass
    ci = Interface.__new__(Interface)
    ci.CP = active
    context = VehicleStartupOwner()
    with self.assertRaisesRegex(RuntimeError, 'matching prepared startup owner'):
      context.configure(ci)
    owner = BlendedStartup(stock, active, (lambda *a: None, lambda *a: None))
    self.assertFalse(owner.prepared_for(active))
    owner.owner.phase = Phase.OWNED
    owner.owner.result = TakeoverResult(Outcome.OWNED)
    owner.source_floor_ns = 1
    self.assertTrue(owner.prepared_for(active))
    foreign = active.as_reader().as_builder()
    foreign.safetyConfigs[0].safetyParam = 0x2014
    self.assertFalse(owner.prepared_for(foreign))
    active.alternativeExperience = 32
    self.assertFalse(owner.prepared_for(active), 'Shared CP mutation must not rewrite the prepared snapshot')
    active.alternativeExperience = 0
    owner.owner.cancel()
    self.assertFalse(owner.prepared_for(active))


if __name__ == '__main__':
  unittest.main()
