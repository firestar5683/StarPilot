"""Regression for the real Mac uiDebug/replay publisher port collision."""
import unittest

from cereal.services import SERVICE_LIST
from replay_namespace import choose_namespace, namespace_collisions, zmq_port
from replay_ui_controls import isolated_replay


FAILED_SESSION = 'a2daf09be6c143b98efea8e7471bfd49'
FAILED_NAMESPACE = 'roadscore-showcase-' + FAILED_SESSION
GOOD_SESSION = '00000000000000000000000000000001'


class ReplayNamespaceTests(unittest.TestCase):
  def test_hash_matches_cpp_fnv1a_port_vectors(self):
    # impl_zmq.cc hashes namespace + ':' + service as unsigned 64-bit FNV1a,
    # then maps into [8023, 65535). Empty namespace hashes the service alone.
    vectors = [
      ('', 'carState', 9041),
      ('test', 'modelV2', 50273),
      ('roadscore-showcase-simple', 'carState', 28976),
      (FAILED_NAMESPACE, 'uiDebug', 54090),
      (FAILED_NAMESPACE, 'starpilotSelfdriveState', 54090),
    ]
    for namespace, service, expected in vectors:
      with self.subTest(namespace=namespace, service=service):
        self.assertEqual(zmq_port(namespace, service), expected)

  def test_failed_session_has_real_ui_and_replay_collision(self):
    collisions = namespace_collisions(FAILED_NAMESPACE, SERVICE_LIST)
    self.assertEqual(set(collisions), {54090})
    self.assertEqual(set(collisions[54090]), {'uiDebug', 'starpilotSelfdriveState'})

  def test_selector_avoids_collision_across_every_runtime_service(self):
    namespace = choose_namespace(FAILED_SESSION, SERVICE_LIST)
    self.assertEqual(namespace, FAILED_NAMESPACE + '-1')
    self.assertEqual(namespace_collisions(namespace, SERVICE_LIST), {})
    ports = [zmq_port(namespace, service) for service in SERVICE_LIST]
    self.assertEqual(len(ports), len(set(ports)))
    self.assertNotIn(9000, ports)

  def test_good_base_namespace_is_preserved_deterministically(self):
    expected = 'roadscore-showcase-' + GOOD_SESSION
    self.assertEqual(namespace_collisions(expected, SERVICE_LIST), {})
    self.assertEqual(choose_namespace(GOOD_SESSION, SERVICE_LIST), expected)
    self.assertEqual(choose_namespace(GOOD_SESSION, reversed(list(SERVICE_LIST))), expected)

  def test_salted_session_keeps_the_exact_replay_isolation_guard(self):
    namespace = choose_namespace(FAILED_SESSION, SERVICE_LIST)
    session = namespace.removeprefix('roadscore-showcase-')
    self.assertEqual(session, FAILED_SESSION + '-1')
    environ = dict(ROADSCORE_REPLAY_UI_CONTROLS='1', SIMULATION='1', ZMQ='1',
                   ROADSCORE_PREPARED_SHOWCASE='1', ROADSCORE_SHOWCASE_SESSION=session,
                   OPENPILOT_ZMQ_NAMESPACE=namespace, OPENPILOT_PREFIX=namespace)
    self.assertTrue(isolated_replay(environ))
    self.assertFalse(isolated_replay({**environ, 'ROADSCORE_SHOWCASE_SESSION': FAILED_SESSION}))
    self.assertFalse(isolated_replay({**environ, 'OPENPILOT_ZMQ_NAMESPACE': FAILED_NAMESPACE}))

  def test_camera_port_is_reserved_even_without_service_pair_collision(self):
    session = '00000000000000000000000000001c59'
    namespace = 'roadscore-showcase-' + session
    self.assertEqual(zmq_port(namespace, 'carState'), 9000)
    collisions = namespace_collisions(namespace, ['carState'])
    self.assertIn(9000, collisions)
    self.assertIn('carState', collisions[9000])
    selected = choose_namespace(session, ['carState'])
    self.assertNotEqual(selected, namespace)
    self.assertNotEqual(zmq_port(selected, 'carState'), 9000)

  def test_retry_limit_fails_instead_of_returning_conflicting_namespace(self):
    with self.assertRaises(RuntimeError):
      choose_namespace(FAILED_SESSION, SERVICE_LIST, max_attempts=1)


if __name__ == '__main__':
  unittest.main()
