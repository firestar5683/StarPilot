from typing import cast
from collections import Counter
from contextlib import ExitStack
from dataclasses import replace
import os
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import numpy as np

from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.selfdrive.controls import plannerd
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.tests.test_curve_runtime_loop import bus, NOW
from openpilot.starpilot.curve_speed.host import CurveHost
from openpilot.starpilot.curve_speed.preferences import MASTER_KEY
from openpilot.starpilot.curve_speed.status import StatusPublisher, observation
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR


class TestCurveStatus(unittest.TestCase):
  def packet(self, outer=None, *, numpy_applied=None):
    cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    cp.pcmCruise = False
    host = CurveHost(enabled=True, replay=True)
    planner = LongitudinalPlanner(cp, init_v=25.0)
    for n in range(30):
      stamp = NOW + n * 50_000_000
      sm = bus(stamp)
      ceiling, result = plannerd.curve_for_frame(host, sm, cp, stamp)
      planner.update(sm, curve_ceiling=ceiling)
      plannerd.confirm_curve_frame(host, planner, stamp)
    if numpy_applied is not None:
      planner.last_curve_ceiling_applied = np.bool_(numpy_applied)
      vars(host.runtime)['enabled'] = np.bool_(host.runtime.enabled)
      vars(host.runtime)['document_valid'] = np.bool_(host.runtime.document_valid)
      vars(host.runtime)['was_controlling'] = np.bool_(host.runtime.was_controlling and numpy_applied)
      vars(host.runtime)['glow'] = np.bool_(host.runtime.glow)
      result = replace(result, candidate_mps=np.float32(result.candidate_mps),
                       ceiling_mps=np.float32(result.ceiling_mps), training=np.bool_(result.training),
                       progress=np.float32(result.progress), binding_distance_m=np.float32(result.binding_distance_m))
    packet = StatusPublisher().attach(outer, host, result, planner, now_ns=stamp, model_ns=stamp,
                                      persistence_status='idle', road_curvature=cast(float, np.float32(0.01)) if numpy_applied is not None else None)
    return packet, stamp

  def test_planner_attach_serializes_numpy_scalars_without_crashing(self):
    for applied in (False, True):
      with self.subTest(applied=applied):
        packet, stamp = self.packet(numpy_applied=applied)
        decoded = messaging.log_from_bytes(packet.to_bytes())
        status = observation(decoded.slcState, stamp)
        assert status is not None
        self.assertEqual(status.applied, applied)
        self.assertEqual(status.controlling, applied)
        assert status.road_curvature is not None
        self.assertAlmostEqual(status.road_curvature, 0.01, places=6)

  def test_status_reports_actual_composition_and_has_independent_expiry(self):
    packet, stamp = self.packet()
    decoded = messaging.log_from_bytes(packet.to_bytes())
    status = observation(decoded.slcState, stamp)
    assert status is not None
    self.assertTrue(status.applied and status.controlling and status.curve_only)
    self.assertFalse(decoded.slcState.enabled or decoded.slcState.hasPending or decoded.slcState.hasAccepted)
    self.assertIsNone(observation(decoded.slcState, stamp + 100_000_001))
    self.assertIsNone(observation(decoded.slcState, stamp - 1))
    self.assertIsNone(observation(messaging.new_message('slcState').slcState, stamp))

  def test_existing_slc_fields_and_invalid_outer_flag_are_preserved(self):
    outer = messaging.new_message('slcState')
    outer.valid = False
    outer.slcState.enabled = True
    outer.slcState.sessionId = 'slc-session'
    outer.slcState.hasPending = True
    outer.slcState.pendingSpeedLimit = 15.0
    before = outer.slcState.to_dict()
    packet, stamp = self.packet(outer)
    decoded = messaging.log_from_bytes(packet.to_bytes())
    after = decoded.slcState.to_dict()
    after.pop('curve')
    self.assertEqual(before, after)
    self.assertFalse(decoded.valid)
    status = observation(decoded.slcState, stamp)
    self.assertTrue(status.applied)
    self.assertFalse(status.curve_only)

  def test_invalid_and_contradictory_nested_status_is_not_displayable(self):
    packet, stamp = self.packet()
    baseline = packet.to_bytes()
    for field, value in (('version', 0), ('sessionId', ''), ('sequence', 0), ('configured', False),
                         ('hasCeiling', False), ('calibrationProgress', 101.0), ('ceilingMps', float('nan')),
                         ('training', True), ('modelMonoTime', stamp + 1), ('plannerStatus', 'not_binding')):
      with self.subTest(field=field):
        altered = messaging.log_from_bytes(baseline).as_builder()
        setattr(altered.slcState.curve, field, value)
        self.assertIsNone(observation(altered.slcState, stamp))

  def test_main_publishes_once_per_model_in_all_runtime_combinations(self):
    cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    cp.pcmCruise = False
    cp_bytes = cp.to_bytes()
    for slc_on, curve_on in ((False, False), (True, False), (False, True), (True, True)):
      with self.subTest(slc=slc_on, curve=curve_on), tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
        params = Params(directory)
        params.put('CarParams', cp_bytes, block=True)
        params.put_bool(MASTER_KEY, True, block=True)
        sm = bus(NOW)
        for name in ('deviceState', 'slcDashboardObservation'):
          sm.messages[name] = getattr(messaging.new_message(name), name)
          sm.valid[name] = sm.alive[name] = True
          sm.logMonoTime[name] = NOW
        sm.frame = 1
        sm.updated = dict.fromkeys(sm.messages, True)
        sm.all_checks = lambda *_args, **_kwargs: True
        steps = 0

        def update(current=sm):
          nonlocal steps
          steps += 1
          if steps > 2:
            raise StopIteration('end of bounded model trace')
          stamp = NOW + steps * 50_000_000
          current.logMonoTime = dict.fromkeys(current.messages, stamp)

        sm.update = update
        sent = []
        subscriptions = []

        class Publisher:
          def __init__(self, services, sink=sent):
            self.services = services
            self.sink = sink
            self.assert_unique = len(services) == len(set(services))
            if not self.assert_unique:
              raise AssertionError('duplicate publisher service')

          def send(self, name, message):
            if name not in self.services:
              raise AssertionError('undeclared publisher service')
            self.sink.append((name, message.to_bytes()))

        def sub_sock(name, collector=subscriptions, **kwargs):
          collector.append((name, kwargs))
          return object()

        stack.enter_context(patch.dict(os.environ, {'SLC_REPLAY_RUNTIME': str(int(slc_on)), 'CURVE_REPLAY_RUNTIME': str(int(curve_on)),
                                                   'LONG_PLANNER_REPLAY_RUNTIME': '0', 'SLC_VISION_DEVELOPMENT': '0', 'REPLAY': '1'}))
        stack.enter_context(patch.object(plannerd, 'Params', return_value=params))
        stack.enter_context(patch.object(plannerd, 'config_realtime_process'))
        stack.enter_context(patch.object(plannerd, 'LaneDepartureWarning', return_value=NS(
          update=lambda *_args: None, left=False, right=False)))
        stack.enter_context(patch.object(messaging, 'SubMaster', return_value=sm))
        stack.enter_context(patch.object(messaging, 'PubMaster', Publisher))
        stack.enter_context(patch.object(messaging, 'sub_sock', side_effect=sub_sock))
        stack.enter_context(patch.object(messaging, 'recv_one_or_none', return_value=None))
        with self.assertRaises(StopIteration):
          plannerd.main()
        counts = Counter(name for name, _raw in sent)
        self.assertEqual(counts['longitudinalPlan'], 2)
        self.assertEqual(counts['slcState'], 2)  # Display-only signs still publish with both controllers off.
        self.assertEqual(sum(name == 'slcCruiseEvent' for name, _kw in subscriptions), 1)
        self.assertTrue(all(not kw['conflate'] for _name, kw in subscriptions))
        for name, raw in sent:
          if name == 'slcState':
            event = messaging.log_from_bytes(raw)
            observed = observation(event.slcState, event.logMonoTime)
            self.assertEqual(observed is not None, curve_on)
            if observed is not None:
              self.assertEqual(observed.curve_only, not slc_on)
