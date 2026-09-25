import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.plannerd import lead_approach_for_frame, update_curve_frame
from openpilot.starpilot.curve_speed.host import CurveHost
from openpilot.starpilot.lateral.lane_change_preferences import LaneChangePolicy
from openpilot.starpilot.longitudinal.lead_approach import LeadApproachKey, SOURCES
from openpilot.starpilot.longitudinal.lead_approach_runtime import LeadApproachPreferences
from openpilot.starpilot.longitudinal.profile_runtime import ProfileTuning
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import messages, message_bytes, snapshot

BASE_NS = 10_000_000_000
DRIVE_NS = BASE_NS - 1_000_000_000
FRAME_NS = 50_000_000
KEY = LeadApproachKey('saved-source', DRIVE_NS)
SPEED = 21.535


class Frame(dict):
  def __init__(self, index, *, approach=True, lane_change=False):
    payloads, self.envelopes = messages(lead=True)
    super().__init__(payloads)
    self.now_ns = BASE_NS + index * FRAME_NS + 10_000_000
    self.logMonoTime = dict.fromkeys(SOURCES, self.now_ns - 10_000_000)
    self.valid = dict.fromkeys(SOURCES, True)
    self.alive = dict.fromkeys(SOURCES, True)
    self['carState'].vEgo = SPEED
    self['carState'].canValid = True
    self['carControl'].longActive = True
    for lead in (self['radarState'].leadOne, self['radarState'].leadTwo):
      lead.dRel = 38.9 if approach else 180.
      lead.vLead = lead.vLeadK = 18.04 if approach else 24.
      lead.vRel = lead.vLead - SPEED
      lead.aLeadK = -.026 if approach else 0.
      lead.modelProb = .984
      lead.radar = False
    if lane_change:
      self['modelV2'].meta.laneChangeState = 'laneChangeStarting'
      self['modelV2'].meta.laneChangeDirection = 'left'

  def with_drive(self):
    event = messaging.new_message('deviceState')
    event.deviceState.started = True
    event.deviceState.startedMonoTime = DRIVE_NS
    self['deviceState'] = event.deviceState
    self.logMonoTime['deviceState'] = self.now_ns - 20_000_000
    self.valid['deviceState'] = self.alive['deviceState'] = True
    return self


class NativeLeadApproachTests(unittest.TestCase):
  def setUp(self):
    self.cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    self.assertTrue(self.cp.openpilotLongitudinalControl)

  def planner(self):
    return LongitudinalPlanner(self.cp, init_v=SPEED)

  def test_native_mpc_receives_original_ramp_and_inputs_stay_unchanged(self):
    default, selected = self.planner(), self.planner()
    follows = []
    for index in range(20):
      sm = Frame(index, approach=index < 8)
      before = message_bytes(sm.envelopes)
      default.update(sm, now_ns=sm.now_ns)
      selected.update(sm, now_ns=sm.now_ns, lead_approach_key=KEY)
      self.assertEqual(message_bytes(sm.envelopes), before)
      self.assertEqual(default.mpc.solution_status, 0)
      self.assertEqual(selected.mpc.solution_status, 0)
      follows.append(float(selected.mpc.params[0, 4]))
      if index == 7:
        self.assertEqual(selected.mpc.source, default.mpc.source)
        self.assertLess(selected.output_a_target, default.output_a_target)
    self.assertAlmostEqual(follows[0], 1.5)
    self.assertAlmostEqual(follows[1], 1.55)
    self.assertAlmostEqual(follows[7], 1.73104381, places=7)
    self.assertAlmostEqual(follows[8], follows[7] - .03)
    self.assertAlmostEqual(follows[-1], 1.45)

  def test_opt_out_invalid_source_or_override_keeps_default_native_output(self):
    for defect in ('no_key', 'stale', 'old_drive', 'gas', 'brake', 'stop', 'off', 'force'):
      with self.subTest(defect=defect):
        default, selected = self.planner(), self.planner()
        for index in range(10):
          sm = Frame(index)
          if defect == 'stale':
            sm.logMonoTime['radarState'] = sm.now_ns - 250_000_001
          elif defect == 'old_drive':
            sm.logMonoTime['modelV2'] = DRIVE_NS - 1
          elif defect in ('gas', 'brake'):
            setattr(sm['carState'], defect + 'Pressed', True)
          elif defect == 'stop':
            sm['modelV2'].action.shouldStop = True
          elif defect == 'off':
            sm['carControl'].longActive = False
          elif defect == 'force':
            sm['controlsState'].forceDecel = True
          default.update(sm, now_ns=sm.now_ns)
          selected.update(sm, now_ns=sm.now_ns, lead_approach_key=None if defect == 'no_key' else KEY)
          self.assertEqual(snapshot(default), snapshot(selected))
          for field in ('x_sol', 'u_sol', 'params'):
            np.testing.assert_array_equal(getattr(default.mpc, field), getattr(selected.mpc, field))

  def test_approach_priority_resets_lane_gap_ramp_before_release(self):
    planner = self.planner()
    policy = LaneChangePolicy(minimum_speed_mps=0., close_gap=True, close_gap_seconds=.75)
    follows = []
    for index in range(25):
      sm = Frame(index, approach=index < 8, lane_change=True)
      planner.update(sm, now_ns=sm.now_ns, lead_approach_key=KEY, lane_change_policy=policy)
      follows.append(float(planner.mpc.params[0, 4]))
      if planner.lead_approach.effective > 1.45:
        self.assertGreater(follows[-1], 1.45)
        self.assertIsNone(planner.lane_change_gap.ramped_follow)
    first_base = follows.index(1.45)
    self.assertGreater(first_base, 8)
    self.assertAlmostEqual(follows[first_base + 1], 1.42)
    self.assertLess(follows[-1], 1.45)

  def test_custom_profile_and_curve_use_same_selected_follow_time(self):
    profile = ProfileTuning('standard', 1.8, 1., 1., 1., 1., 1.)
    for host in (None, CurveHost(enabled=False, replay=True)):
      planner = self.planner()
      seen = []
      def capture(*args, follow_time_s, seen=seen, **kwargs):
        seen.append(follow_time_s)
        return None, None
      with patch('openpilot.selfdrive.controls.plannerd.curve_for_frame', side_effect=capture):
        for index in range(8):
          sm = Frame(index)
          update_curve_frame(planner, sm, self.cp, sm.now_ns, host=host, profile_tuning=profile,
                             lead_approach_key=KEY)
          self.assertGreater(planner.mpc.params[0, 4], planner.last_profile.follow_seconds)
          if host is not None:
            self.assertEqual(seen[-1], float(planner.mpc.params[0, 4]))

  def test_registered_saved_opt_in_needs_current_started_device_evidence(self):
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      preferences = LeadApproachPreferences(params)
      sm = Frame(0).with_drive()
      self.assertIsNone(lead_approach_for_frame(preferences, sm, self.cp, sm.now_ns))
      params.put_bool('LeadApproachBuffer', True, block=True)
      sm = Frame(20).with_drive()
      key = lead_approach_for_frame(preferences, sm, self.cp, sm.now_ns)
      self.assertIsNotNone(key)
      self.assertEqual(key.drive_id, DRIVE_NS)
      for defect in ('invalid', 'dead', 'future', 'stale', 'not_started', 'unknown_drive'):
        bad = Frame(20).with_drive()
        if defect == 'invalid':
          bad.valid['deviceState'] = False
        elif defect == 'dead':
          bad.alive['deviceState'] = False
        elif defect == 'not_started':
          bad['deviceState'].started = False
        elif defect == 'unknown_drive':
          bad['deviceState'].startedMonoTime = 0
        else:
          bad.logMonoTime['deviceState'] = bad.now_ns + 1 if defect == 'future' else bad.now_ns - 1_000_000_001
        self.assertIsNone(lead_approach_for_frame(preferences, bad, self.cp, bad.now_ns))
      Path(params.get_param_path('LeadApproachBuffer')).write_bytes(b'0')
      sm = Frame(40).with_drive()
      self.assertIsNone(lead_approach_for_frame(preferences, sm, self.cp, sm.now_ns))


if __name__ == '__main__':
  unittest.main()
