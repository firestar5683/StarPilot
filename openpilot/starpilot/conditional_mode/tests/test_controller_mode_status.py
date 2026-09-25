"""Controller Traffic receipts retain the dependency-free shared status owner."""

from typing import Any
import unittest
from types import SimpleNamespace as NS
from openpilot.starpilot.conditional_mode.traffic_status import TrafficDisplayProjector




def changed_arguments(arguments: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
  return {**arguments, **changes}

class TestControllerModeStatus(unittest.TestCase):
  def test_controller_source_without_wheel_assignment_retains_freshness_guards(self):
    now = 10_000_000_000
    wire = NS(version=1, sessionId='a'*32, sequence=1, observedMonoTime=now,
              validUntilMonoTime=now+100_000_000, driveStartMonoTime=now-1_000_000_000,
              sourceEpoch=1, sourceBootTime=now+2_000_000_000-5_000_000,
              settingsFingerprint='b'*64, buttonMapFingerprint='', controllerSource=True,
              accepted=True, effective=True, reason='active', profileTargetReady=True,
              profileReason='qualified')
    reader = TrafficDisplayProjector()
    args: dict[str, Any] = {'now_mono_ns': now, 'now_boot_ns': now+2_000_000_000, 'drive_id': now-1_000_000_000,
                'settings_fingerprint': 'b'*64, 'map_fingerprint': None, 'map_assigned': False,
                'profile_valid': True, 'long_active': True, 'selfdrive_enabled': True, 'car_valid': True, 'system_long': True}
    self.assertEqual(reader.project(NS(trafficMode=wire), **args).state, 'active')
    self.assertIsNone(reader.project(NS(trafficMode=wire), **changed_arguments(args, {'now_mono_ns': now+100_000_001})))
    self.assertIsNone(reader.project(NS(trafficMode=wire), **changed_arguments(args, {'settings_fingerprint': 'c'*64})))
    wire.controllerSource = False
    self.assertIsNone(reader.project(NS(trafficMode=wire), **args))

  def test_ui_shim_uses_same_projector_owner(self):
    from openpilot.starpilot.ui.traffic_status import TrafficDisplayProjector as UIProjector
    self.assertIs(UIProjector, TrafficDisplayProjector)
