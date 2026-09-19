import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototype'))
from launch_health import LaunchFailure, check_children, describe_failure, write_failure
from overlay_view import overlay_view


class LaunchHealthTests(unittest.TestCase):
  def test_dead_tunnel_detected_while_receiver_still_compiles(self):
    children = {'receiver': Mock(poll=lambda: None), 'semantic_tunnel': Mock(poll=lambda: 255)}
    with self.assertRaises(LaunchFailure) as caught:
      check_children(children, remote=True, include_receiver=True)
    status = describe_failure(caught.exception)
    self.assertEqual(status['failure_kind'], 'connection_lost')
    self.assertEqual(status['failure_component'], 'semantic_tunnel')
    self.assertEqual(overlay_view(status)['note'], 'Connection lost')

  def test_receiver_ssh_exit_distinct_from_remote_application_error(self):
    for code, kind in [(255, 'connection_lost'), (1, 'launch_failed'), (0, 'launch_failed')]:
      with self.subTest(code=code):
        with self.assertRaises(LaunchFailure) as caught:
          check_children({'receiver': Mock(poll=lambda: code)}, remote=True, include_receiver=True)
        self.assertEqual(describe_failure(caught.exception)['failure_kind'], kind)
    check_children({'receiver': Mock(poll=lambda: 0)}, remote=True, include_receiver=True, allow_clean_receiver=True)

  def test_planner_failure_and_timeout_are_not_gpu_diagnoses(self):
    for error in (LaunchFailure('semantic_planner', -9), TimeoutError('Receiver readiness deadline elapsed')):
      status = describe_failure(error)
      self.assertEqual(status['readiness'], 'DEGRADED')
      self.assertNotIn('worker_failed', status)
      self.assertIn('failure_cause', status)

  def test_persisted_failure_replaces_preparing_without_losing_profile(self):
    with tempfile.TemporaryDirectory() as root:
      path = Path(root)/'roadscore_status.json'
      path.write_text(json.dumps({'readiness': 'PREPARING', 'profile': 'prism', 'job_inflight': True}))
      failure = describe_failure(LaunchFailure('receiver', 255, True))
      write_failure(path, failure)
      state = json.loads(path.read_text())
      self.assertEqual(state['profile'], 'prism')
      self.assertEqual(state['readiness'], 'DEGRADED')
      self.assertFalse(state['job_inflight'])
      self.assertNotIn('worker_failed', state)
      self.assertEqual(state['failure_exit_code'], 255)
      self.assertEqual(overlay_view(state)['note'], 'Connection lost')
      path.write_text('{}')
      write_failure(path, failure)
      self.assertEqual(json.loads(path.read_text())['readiness'], 'DEGRADED')


if __name__ == '__main__':
  unittest.main()
