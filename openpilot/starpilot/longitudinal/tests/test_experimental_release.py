"""Committed Dom release-rule oracles and actual native planner handoff behavior."""

import math
import unittest
from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

import numpy as np

from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.starpilot.longitudinal.experimental_release import (
  ExperimentalRelease, ReleaseFrame, ReleaseLead, SOURCES, MAX_FRAME_GAP_NS, MAX_SOURCE_AGE_NS, project,
)
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import messages
from openpilot.starpilot.longitudinal.tests.test_ioniq6_start import candidate
from openpilot.starpilot.longitudinal.tests.test_throttle_gate import Frame

KEY = ('settings-owner', 1, 1_000_000_000, 'conditional_experimental')
BASE_NS = 10_000_000_000
FRAME_NS = 50_000_000
LEAD = ReleaseLead(11., 6.8, 0., True, 1., 0.)


def frame(index, *, experimental=False, speed=6.75, lead=LEAD):
  stamp = BASE_NS + index * FRAME_NS
  return ReleaseFrame(stamp + 10_000_000, stamp, experimental, speed, lead)


def step(owner, value, *, key=KEY, previous=-.25, target=-.03, follow=1.45, blocked=False):
  return owner.step(key, value, previous_target=previous, target=target, follow_seconds=follow, blocked=blocked)


def armed(*, speed=6.75, lead=LEAD):
  owner = ExperimentalRelease()
  assert step(owner, frame(0, experimental=True, speed=speed, lead=lead)) is None
  step(owner, frame(1, speed=speed, lead=lead))
  return owner


def native_frame(index, *, experimental=True):
  sm = Frame(messages(lead=True, e2e=experimental)[0])
  stamp = BASE_NS + index * FRAME_NS
  for name in SOURCES:
    sm.logMonoTime[name] = stamp
    sm.valid[name] = sm.alive[name] = True
  sm['carControl'].longActive = True
  sm['carState'].canValid = True
  sm['carState'].vEgo = 6.75
  sm['carState'].aEgo = -.25
  sm['modelV2'].action.desiredAcceleration = -.25
  sm['modelV2'].action.shouldStop = False
  sm['radarState'].leadTwo.present = False
  lead = sm['radarState'].leadOne
  lead.dRel = 11.
  lead.vLead = lead.vLeadK = 6.8
  lead.vRel = .05
  lead.aLeadK = 0.
  return sm, stamp + 10_000_000


class ExperimentalReleaseTests(unittest.TestCase):
  def test_committed_low_and_high_speed_oracles_and_exact_trigger(self):
    # Original c96528ff helper/tests: low-speed -.25 -> -.19; high-speed .03 -> .09.
    owner = armed()
    self.assertAlmostEqual(step(owner, frame(2)), -.19)
    high = ReleaseLead(55.15, 23.73, .4, True, .997, 0.)
    owner = armed(speed=23.96, lead=high)
    self.assertAlmostEqual(step(owner, frame(2, speed=23.96, lead=high), previous=.03, target=.44, follow=1.13), .09)
    for delta, expected in ((math.nextafter(.12, 0.), None), (.12, .06), (math.nextafter(.12, 1.), .06)):
      with self.subTest(delta=delta):
        self.assertEqual(step(armed(), frame(2), previous=0., target=delta), expected)
    self.assertIsNone(step(armed(), frame(2), target=-.3))

  def test_exact_hold_windows_expiry_and_reentry(self):
    for speed, hold in ((11.999, 3_000_000_000), (12., 750_000_000)):
      with self.subTest(speed=speed):
        lead = replace(LEAD, speed=speed, distance=speed * 2.)
        owner = armed(speed=speed, lead=lead)
        until = frame(1).now_ns + hold
        self.assertEqual(owner.release_until_ns, until)
        for index in range(2, hold // FRAME_NS + 1):
          self.assertIsNotNone(step(owner, frame(index, speed=speed, lead=lead)))
        last = replace(frame(1, speed=speed, lead=lead), now_ns=until - 1, model_ns=until - 10_000_001)
        self.assertIsNotNone(step(owner, last))
        self.assertIsNone(step(owner, replace(last, now_ns=until, model_ns=last.model_ns + 1)))
        self.assertIsNone(step(owner, replace(last, now_ns=until + 1, model_ns=last.model_ns + 2, experimental=True)))
        self.assertEqual(owner.release_until_ns, 0)

  def test_original_lead_exclusions_and_boundaries(self):
    cases = (replace(LEAD, speed=0.), replace(LEAD, speed=5.74), replace(LEAD, speed=8.26),
             replace(LEAD, acceleration=-.200001), replace(LEAD, radar=False, probability=.899999),
             replace(LEAD, lateral_offset=1.500001), replace(LEAD, distance=6.75 * 1.45 - .000001), None)
    for lead in cases:
      with self.subTest(lead=lead):
        self.assertIsNone(step(armed(), frame(2, lead=lead)))
    for lead in (replace(LEAD, speed=5.75), replace(LEAD, speed=8.25), replace(LEAD, acceleration=-.2),
                 replace(LEAD, radar=False, probability=.9), replace(LEAD, lateral_offset=1.5),
                 replace(LEAD, distance=6.75 * 1.45)):
      with self.subTest(boundary=lead):
        self.assertIsNotNone(step(armed(), frame(2, lead=lead)))

  def test_changed_or_absent_owner_and_invalid_frames_cannot_reuse_edge(self):
    keys = (None, ('other-owner', *KEY[1:]), (KEY[0], 2, *KEY[2:]),
            (KEY[0], KEY[1], KEY[2] + 1, KEY[3]), (*KEY[:3], 'conditional_chill'), (*KEY[:3], 'stock'),
            (KEY[0], True, KEY[2], KEY[3]))
    for key in keys:
      with self.subTest(key=key):
        owner = armed()
        self.assertIsNone(step(owner, frame(2), key=key))
        self.assertIsNone(step(owner, frame(3)))
    for invalid in (None, replace(frame(2), speed=float('nan')), replace(frame(2), lead=replace(LEAD, probability=float('nan')))):
      owner = armed()
      self.assertIsNone(step(owner, invalid))
      self.assertIsNone(step(owner, frame(3)))
    for changes in ({'blocked': True}, {'target': float('nan')}, {'previous': float('inf')}, {'follow': float('nan')}):
      owner = armed()
      self.assertIsNone(step(owner, frame(2), **changes))
      self.assertIsNone(step(owner, frame(3)))

  def test_repeated_backward_and_gapped_model_or_receipt_clocks_reset(self):
    previous = frame(1)
    for field in ('model_ns', 'now_ns'):
      for difference in (0, -1, MAX_FRAME_GAP_NS + 1):
        owner = armed()
        value = replace(frame(2), **{field: getattr(previous, field) + difference})
        self.assertIsNone(step(owner, value))
        self.assertIsNone(step(owner, frame(6)))
    owner = armed()
    self.assertIsNotNone(step(owner, replace(previous, now_ns=previous.now_ns + MAX_FRAME_GAP_NS,
                                           model_ns=previous.model_ns + MAX_FRAME_GAP_NS)))

  def test_projection_preserves_mpc_lead_selection_and_rejects_unavailable_sources(self):
    cp = SimpleNamespace(openpilotLongitudinalControl=True)
    sm, now = native_frame(0)
    self.assertIsNotNone(project(sm, cp, now, lead_index=0, conditional_handoff=KEY).lead)
    self.assertIsNone(project(sm, cp, now, lead_index=1, conditional_handoff=KEY).lead)
    self.assertEqual(project(sm, cp, now, lead_index=None, conditional_handoff=KEY).lead, project(sm, cp, now, lead_index=0, conditional_handoff=KEY).lead)
    sm['radarState'].leadTwo = sm['radarState'].leadOne
    sm['radarState'].leadTwo.dRel = 30.
    self.assertEqual(project(sm, cp, now, lead_index=1, conditional_handoff=KEY).lead.distance, 30.)
    for name in SOURCES:
      for defect in ('invalid', 'dead', 'stale', 'future'):
        value, now = native_frame(0)
        if defect == 'invalid':
          value.valid[name] = False
        elif defect == 'dead':
          value.alive[name] = False
        else:
          value.logMonoTime[name] = now - MAX_SOURCE_AGE_NS - 1 if defect == 'stale' else now + 1
        with self.subTest(source=name, defect=defect):
          self.assertIsNone(project(value, cp, now, lead_index=0, conditional_handoff=KEY))
    for message, field, value in (('carState', 'canValid', False), ('carState', 'canTimeout', True),
                                  ('carState', 'gasPressed', True), ('carState', 'brakePressed', True),
                                  ('carState', 'standstill', True), ('carControl', 'longActive', False),
                                  ('selfdriveState', 'enabled', False), ('controlsState', 'forceDecel', True)):
      sm, now = native_frame(0)
      setattr(sm[message], field, value)
      self.assertIsNone(project(sm, cp, now, lead_index=0, conditional_handoff=KEY))
    sm, now = native_frame(0)
    sm['modelV2'].action.shouldStop = True
    self.assertIsNone(project(sm, cp, now, lead_index=0, conditional_handoff=KEY))
    sm['modelV2'].action.shouldStop = False
    self.assertIsNone(project(sm, SimpleNamespace(openpilotLongitudinalControl=False), now, lead_index=0, conditional_handoff=KEY))


  def test_restart_rejects_each_fresh_but_previous_drive_source(self):
    cp = SimpleNamespace(openpilotLongitudinalControl=True)
    current_key = (KEY[0], KEY[1], BASE_NS, KEY[3])
    for name in SOURCES:
      with self.subTest(source=name):
        sm, now = native_frame(0)
        self.assertIsNotNone(project(sm, cp, now, lead_index=0, conditional_handoff=current_key))
        sm.logMonoTime[name] = BASE_NS - 1
        self.assertLess(now - sm.logMonoTime[name], MAX_SOURCE_AGE_NS)
        value = project(sm, cp, now, lead_index=0, conditional_handoff=current_key)
        self.assertIsNone(value)
        owner = armed()
        self.assertIsNone(step(owner, value, key=current_key))
        self.assertEqual(owner.release_until_ns, 0)
    sm, now = native_frame(0)
    for key in (None, (), (KEY[0], 1, 0, KEY[3]), (KEY[0], 1, now + 1, KEY[3])):
      self.assertIsNone(project(sm, cp, now, lead_index=0, conditional_handoff=cast(Any, key)))


class NativeExperimentalReleaseTests(unittest.TestCase):
  def test_qualified_mode_exit_caps_actual_native_target_before_integration(self):
    cp = candidate()[1]
    native = LongitudinalPlanner(cp, init_v=6.75, init_a=-.25)
    opted = LongitudinalPlanner(cp, init_v=6.75, init_a=-.25)
    for index in range(16):
      sm, now = native_frame(index, experimental=index < 15)
      native.update(sm, now_ns=now)
      opted.update(sm, now_ns=now, conditional_handoff=KEY)
      self.assertEqual(native.mpc.solution_status, 0)
      self.assertEqual(opted.mpc.solution_status, 0)
      np.testing.assert_array_equal(native.a_desired_trajectory, opted.a_desired_trajectory)
      np.testing.assert_array_equal(native.j_desired_trajectory, opted.j_desired_trajectory)
      if index < 15:
        self.assertEqual(native.output_a_target, opted.output_a_target)
    self.assertAlmostEqual(native.output_a_target, -.114283067148166, places=7)
    self.assertAlmostEqual(opted.output_a_target, -.19)
    self.assertAlmostEqual(opted.v_desired_filter.x - native.v_desired_filter.x,
                           .05 * (opted.output_a_target - native.output_a_target) / 2.)
    self.assertEqual(native.mpc.source, opted.mpc.source)
    self.assertFalse(opted.output_should_stop)

  def test_default_and_unavailable_authority_preserve_native_sequences(self):
    cp = candidate()[1]
    for defect in ('no_owner', 'changed_owner', 'missing_freshness', 'override', 'force_decel', 'long_off', 'model_stop', 'braking'):
      with self.subTest(defect=defect):
        native = LongitudinalPlanner(cp, init_v=6.75, init_a=-.25)
        opted = LongitudinalPlanner(cp, init_v=6.75, init_a=-.25)
        for index in range(18):
          sm, now = native_frame(index, experimental=index < 15 or defect == 'braking')
          key = KEY
          if defect == 'no_owner':
            key = None
          elif defect == 'missing_freshness':
            sm.valid['radarState'] = False
          elif index >= 15:
            if defect == 'changed_owner':
              key = (KEY[0], 2, KEY[2], KEY[3])
            elif defect == 'override':
              sm['carState'].gasPressed = True
            elif defect == 'force_decel':
              sm['controlsState'].forceDecel = True
            elif defect == 'long_off':
              sm['carControl'].longActive = False
            elif defect == 'model_stop':
              sm['modelV2'].action.shouldStop = True
            elif defect == 'braking':
              sm['modelV2'].action.desiredAcceleration = -.8
          native.update(sm, now_ns=now)
          opted.update(sm, now_ns=now, conditional_handoff=key)
          self.assertEqual(native.output_a_target, opted.output_a_target)
          self.assertEqual(native.output_should_stop, opted.output_should_stop)
          self.assertEqual(native.mpc.source, opted.mpc.source)
          np.testing.assert_array_equal(native.a_desired_trajectory, opted.a_desired_trajectory)
