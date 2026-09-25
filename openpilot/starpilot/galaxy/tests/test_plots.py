"""Plots projection, bounded worker, actual IPC and authenticated HTTP."""

import http.client
import json
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import threading
import time
import unittest
import uuid
from unittest import mock

from openpilot.cereal import messaging
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.plots import MessagingPlotsReader, PlotReading, Plots, extract, finite
from openpilot.starpilot.galaxy.server import make_server


def controls(kind='torqueState', **fields):
  state = NS(which=lambda: kind, torqueState=NS(p=0.2, i=0.1, d=0.0, f=0.3, desiredLateralAccel=0.4, actualLateralAccel=0.35), pidState=NS(p=0.2, i=0.1, f=0.3))
  return NS(
    lateralControlState=state,
    active=True,
    longControlState='pid',
    vPid=12.0,
    desiredCurvature=0.01,
    curvature=0.009,
    aTarget=0.6,
    upAccelCmd=0.2,
    uiAccelCmd=0.1,
    ufAccelCmd=0.3,
    **fields,
  )


def pose(valid=True):
  return NS(velocityDevice=NS(valid=valid, x=12.0), accelerationDevice=NS(valid=valid, x=0.5))


class PlotsTest(unittest.TestCase):
  def test_projection_sources_and_missing_values(self):
    read = extract(
      controls(),
      pose(),
      controls_fresh=True,
      pose_fresh=True,
      controls_valid=True,
      pose_valid=True,
      state=NS(active=True),
      state_fresh=True,
      plan=NS(aTarget=0.6),
      plan_fresh=True,
      car_control=NS(longActive=True),
      car_control_fresh=True,
    )
    self.assertEqual((read['lateralSource'], read['longitudinalSource'], read['lateralTermsSource']), ('torqueState', 'aTarget', 'torqueState'))
    self.assertEqual((read['desiredLateralAccel'], read['actualLongitudinalAccel']), (0.4, 0.5))
    aol = extract(
      controls(),
      pose(),
      controls_fresh=True,
      pose_fresh=True,
      controls_valid=True,
      pose_valid=True,
      state=NS(active=False),
      state_fresh=True,
      car_control=NS(latActive=True, longActive=False),
      car_control_fresh=True,
    )
    self.assertEqual((aol['controlsActive'], aol['lateralControlActive'], aol['longitudinalControlActive']), (False, True, False))
    long_only = extract(
      controls(),
      pose(),
      controls_fresh=True,
      pose_fresh=True,
      controls_valid=True,
      pose_valid=True,
      state=NS(active=True),
      state_fresh=True,
      car_control=NS(latActive=False, longActive=True),
      car_control_fresh=True,
    )
    self.assertEqual((long_only['controlsActive'], long_only['lateralControlActive'], long_only['longitudinalControlActive']), (True, False, True))
    fallback = extract(
      controls(kind='pidState'),
      pose(False),
      controls_fresh=True,
      pose_fresh=True,
      controls_valid=True,
      pose_valid=True,
      state=NS(active=True),
      state_fresh=True,
      car_state=NS(vEgo=12.0),
      car_state_fresh=True,
    )
    self.assertEqual(fallback['lateralSource'], 'curvature')
    self.assertEqual(fallback['speedSource'], 'carState')
    self.assertEqual(fallback['lateralTermsSource'], 'pidState')
    self.assertIsNone(fallback['lateralD'])
    self.assertIsNone(fallback['actualLongitudinalAccel'])
    self.assertEqual(fallback['desiredLateralAccel'], 1.44)
    stale = extract(controls(), pose(), controls_fresh=False, pose_fresh=True, controls_valid=True, pose_valid=True, state=NS(active=True), state_fresh=True)
    self.assertIsNone(stale['desiredLateralAccel'])
    self.assertIsNone(stale['controlsActive'])
    self.assertIsNone(finite(float('nan')))
    self.assertIsNone(finite(float('inf')))
    self.assertIsNone(finite(10**400))
    corrupt = controls()
    corrupt.lateralControlState.torqueState.actualLateralAccel = float('nan')
    output = extract(
      corrupt,
      pose(),
      controls_fresh=True,
      pose_fresh=True,
      controls_valid=True,
      pose_valid=True,
      state=NS(active=True),
      state_fresh=True,
      plan=NS(aTarget=0.6),
      plan_fresh=True,
      car_control=NS(longActive=True),
      car_control_fresh=True,
    )
    self.assertEqual(output['lateralSource'], 'curvature')
    self.assertTrue(
      all(
        value is None or isinstance(value, float)
        for key, value in output.items()
        if key in ('desiredLateralAccel', 'actualLateralAccel', 'actualLongitudinalAccel')
      )
    )

  def test_worker_idle_and_reconnect(self):
    readers = []

    class Reader:
      def __init__(self):
        self.closed = False
        readers.append(self)

      def sample(self, now):
        return PlotReading({'controlsFresh': True, 'speedMps': 1.0}, 0.0, (1,))

      def close(self):
        self.closed = True

    source = Plots(reader_factory=Reader)
    with mock.patch('openpilot.starpilot.galaxy.plots.SAMPLE_INTERVAL_S', 0.01), mock.patch('openpilot.starpilot.galaxy.plots.CLIENT_IDLE_S', 0.06):
      try:
        source.snapshot()
        deadline = time.monotonic() + 1
        while source.snapshot()['state'] != 'current' and time.monotonic() < deadline:
          time.sleep(0.005)
        self.assertEqual(source.snapshot()['state'], 'current')
        time.sleep(0.1)
        # The last request above has expired; its worker must release IPC before the next one.
        self.assertTrue(readers[0].closed)
        source.snapshot()
        deadline = time.monotonic() + 1
        while len(readers) < 2 and time.monotonic() < deadline:
          time.sleep(0.005)
        self.assertGreaterEqual(len(readers), 2)
      finally:
        source.close()
    self.assertTrue(readers[-1].closed)

  def test_producer_session_changes_across_process_instances(self):
    first = Plots(reader_factory=lambda: None)
    second = Plots(reader_factory=lambda: None)
    self.assertRegex(first.session_id, r'^[0-9a-f]{16}$')
    self.assertNotEqual(first.session_id, second.session_id)
    first.close()
    second.close()

  def test_sample_age_and_boot_status_do_not_renew_without_reader_data(self):
    now = [100.0]

    class Reader:
      def sample(self, timestamp):
        return PlotReading({'controlsFresh': True, 'speedMps': 1.0}, 0.0, (1,))

      def close(self):
        pass

    source = Plots(reader_factory=Reader, clock=lambda: now[0])
    with (
      mock.patch('openpilot.starpilot.galaxy.plots.SAMPLE_INTERVAL_S', 5.0),
      mock.patch('openpilot.starpilot.galaxy.plots.boot_stabilizing', return_value=True),
    ):
      try:
        source.snapshot()
        deadline = time.monotonic() + 1
        while source.snapshot()['state'] != 'current' and time.monotonic() < deadline:
          time.sleep(0.005)
        self.assertTrue(source.snapshot()['bootStabilizing'])
        now[0] += 1.6
        aged = source.snapshot()
        self.assertEqual(aged['state'], 'stale')
        self.assertIsNone(aged['values'])
        self.assertGreaterEqual(aged['sampleAgeSeconds'], 1.5)
      finally:
        source.close()

  def test_publisher_age_budget_survives_worker_and_http_delay(self):
    now = [100.0]

    class Reader:
      def sample(self, timestamp):
        return PlotReading({'controlsFresh': True, 'speedMps': 1.0}, 1.4, (1,))

      def close(self):
        pass

    source = Plots(reader_factory=Reader, clock=lambda: now[0])
    with mock.patch('openpilot.starpilot.galaxy.plots.SAMPLE_INTERVAL_S', 5.0):
      try:
        source.snapshot()
        deadline = time.monotonic() + 1
        while source.snapshot()['state'] != 'current' and time.monotonic() < deadline:
          time.sleep(0.005)
        initial = source.snapshot()
        self.assertEqual(initial['state'], 'current')
        self.assertGreaterEqual(initial['sampleAgeSeconds'], 1.4)
        self.assertLessEqual(initial['sampleAgeSeconds'], 1.401)
        now[0] += 0.09
        self.assertEqual(source.snapshot()['state'], 'current')
        now[0] += 0.11
        aged = source.snapshot()
        self.assertEqual(aged['state'], 'stale')
        self.assertIsNone(aged['values'])
        self.assertGreaterEqual(aged['sampleAgeSeconds'], 1.6)
        self.assertLessEqual(aged['sampleAgeSeconds'], 1.601)
      finally:
        source.close()

  def test_repeated_source_sample_does_not_renew_age_or_history(self):
    now = [100.0]
    sampled = threading.Event()

    class Reader:
      def sample(self, timestamp):
        sampled.set()
        return PlotReading({'controlsFresh': True, 'speedMps': 1.0}, max(0.0, now[0] - 98.6), (1,))

      def close(self):
        pass

    source = Plots(reader_factory=Reader, clock=lambda: now[0])
    with mock.patch('openpilot.starpilot.galaxy.plots.SAMPLE_INTERVAL_S', 0.01):
      try:
        source.snapshot()
        deadline = time.monotonic() + 1
        while source.snapshot()['state'] != 'current' and time.monotonic() < deadline:
          time.sleep(0.005)
        initial = source.snapshot()
        self.assertEqual(initial['sampleIndex'], 1)
        self.assertGreaterEqual(initial['sampleAgeSeconds'], 1.4)
        self.assertLessEqual(initial['sampleAgeSeconds'], 1.401)
        sampled.clear()
        now[0] += 0.2
        self.assertTrue(sampled.wait(1))
        deadline = time.monotonic() + 1
        while source.snapshot()['sampleAgeSeconds'] < 1.6 and time.monotonic() < deadline:
          time.sleep(0.005)
        aged = source.snapshot()
        self.assertEqual(aged['sampleIndex'], 1)
        self.assertEqual(aged['state'], 'stale')
        self.assertIsNone(aged['values'])
        self.assertGreaterEqual(aged['sampleAgeSeconds'], 1.6)
      finally:
        source.close()

  def test_resume_rearms_only_after_new_producer_events(self):
    services = ('controlsState', 'deviceMotion', 'selfdriveState', 'longitudinalPlan', 'carControl', 'carState')

    class Cached:
      def __init__(self):
        self.seen = dict.fromkeys(services, True)
        self.valid = dict.fromkeys(services, True)
        self.recv_time = dict.fromkeys(services, 100.05)
        self.logMonoTime = dict.fromkeys(services, 100_050_000_000)
        self.data = {
          'controlsState': controls(),
          'deviceMotion': pose(),
          'selfdriveState': NS(active=True),
          'longitudinalPlan': NS(aTarget=0.6),
          'carControl': NS(latActive=True, longActive=True),
          'carState': NS(vEgo=12.0),
        }

      def update(self, timeout):
        self.asserted_timeout = timeout

      def __getitem__(self, key):
        return self.data[key]

    reader = object.__new__(MessagingPlotsReader)
    cached = Cached()
    reader.started_ns = 100_000_000_000
    reader.boot_offset_ns = 1_000_000_000
    with (
      mock.patch.object(reader, 'sm', cached, create=True),
      mock.patch.object(time, 'CLOCK_BOOTTIME', 7, create=True),
      mock.patch('openpilot.starpilot.galaxy.plots.paired_boot_offset_ns', side_effect=[1_000_000_000, 1_090_000_000, 1_090_000_000]),
      mock.patch('openpilot.starpilot.galaxy.plots.time.monotonic', side_effect=[100.1, 100.1, 100.21]),
      mock.patch('openpilot.starpilot.galaxy.plots.time.monotonic_ns', return_value=100_100_000_000),
    ):
      self.assertTrue(reader.sample(0).values['controlsFresh'])
      self.assertFalse(reader.sample(0).values['controlsFresh'])
      for service in services:
        cached.recv_time[service] = 100.2
        cached.logMonoTime[service] = 100_200_000_000
      self.assertTrue(reader.sample(0).values['controlsFresh'])

  def test_reader_preserves_original_event_age_on_repeated_ipc_sample(self):
    services = ('controlsState', 'deviceMotion', 'selfdriveState', 'longitudinalPlan', 'carControl', 'carState')

    class Cached:
      def __init__(self):
        self.seen = dict.fromkeys(services, True)
        self.valid = dict.fromkeys(services, True)
        self.recv_time = dict.fromkeys(services, 98.6)
        self.logMonoTime = dict.fromkeys(services, 98_600_000_000)
        self.data = {
          'controlsState': controls(),
          'deviceMotion': pose(),
          'selfdriveState': NS(active=True),
          'longitudinalPlan': NS(aTarget=0.6),
          'carControl': NS(latActive=True, longActive=True),
          'carState': NS(vEgo=12.0),
        }

      def update(self, timeout):
        pass

      def __getitem__(self, key):
        return self.data[key]

    reader = object.__new__(MessagingPlotsReader)
    cached = Cached()
    reader.started_ns = 98_000_000_000
    reader.boot_offset_ns = 1_000_000_000
    with (
      mock.patch.object(reader, 'sm', cached, create=True),
      mock.patch.object(time, 'CLOCK_BOOTTIME', 7, create=True),
      mock.patch('openpilot.starpilot.galaxy.plots.paired_boot_offset_ns', return_value=1_000_000_000),
      mock.patch('openpilot.starpilot.galaxy.plots.time.monotonic', side_effect=[100.0, 100.2]),
    ):
      first = reader.sample(0)
      second = reader.sample(0)
    self.assertTrue(first.values['controlsFresh'])
    self.assertAlmostEqual(first.source_age_seconds, 1.4)
    self.assertEqual(second.signature, (0,) * len(services))
    self.assertFalse(second.values['controlsFresh'])
    self.assertIsNone(second.source_age_seconds)

  def test_typed_ipc_through_authenticated_http(self):
    messaging.set_fake_prefix('galaxy_plots_http_' + uuid.uuid4().hex)
    with tempfile.TemporaryDirectory() as directory:
      owner = GalaxyAccessOwner(Path(directory) / 'access')
      owner.configure('password123', lambda: True)
      source = Plots()
      server = make_server(port=0, owner=owner, plots=source)
      server_thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
      server_thread.start()
      publisher = messaging.PubMaster(['controlsState', 'selfdriveState', 'deviceMotion', 'longitudinalPlan', 'carControl'])

      def request(path, method='GET', body=None, headers=None):
        # Exercise the password-backed forwarded path.
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=2)
        try:
          connection.request(method, path, body=body, headers={'Forwarded': 'for=203.0.113.8', **(headers or {})})
          response = connection.getresponse()
          return response.status, json.loads(response.read()), dict(response.getheaders())
        finally:
          connection.close()

      try:
        self.assertEqual(request('/api/plots/live')[0], 401)
        self.assertIsNone(source.worker)
        origin = f'http://127.0.0.1:{server.server_port}'
        status, _, headers = request('/api/auth/login', 'POST', json.dumps({'password': 'password123'}), {'Content-Type': 'application/json', 'Origin': origin})
        self.assertEqual(status, 200)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        self.assertEqual(request('/api/plots/live', headers={'Cookie': cookie})[1]['state'], 'stale')
        control = messaging.new_message('controlsState', valid=True)
        control.controlsState.lateralControlState.init('torqueState')
        control.controlsState.lateralControlState.torqueState.desiredLateralAccel = 0.42
        control.controlsState.lateralControlState.torqueState.actualLateralAccel = 0.37
        state = messaging.new_message('selfdriveState', valid=True)
        state.selfdriveState.active = True
        motion = messaging.new_message('deviceMotion', valid=True)
        motion.deviceMotion.velocityDevice.valid = True
        motion.deviceMotion.velocityDevice.x = 12.0
        motion.deviceMotion.accelerationDevice.valid = True
        motion.deviceMotion.accelerationDevice.x = 0.5
        plan = messaging.new_message('longitudinalPlan', valid=True)
        plan.longitudinalPlan.aTarget = 0.6
        car_control = messaging.new_message('carControl', valid=True)
        car_control.carControl.longActive = True
        car_control.carControl.latActive = True
        deadline = time.monotonic() + 2
        result = None
        while time.monotonic() < deadline:
          for name, event in [
            ('controlsState', control),
            ('selfdriveState', state),
            ('deviceMotion', motion),
            ('longitudinalPlan', plan),
            ('carControl', car_control),
          ]:
            event.clear_write_flag()
            publisher.send(name, event)
          _, result, _ = request('/api/plots/live', headers={'Cookie': cookie})
          if (
            result['state'] == 'current'
            and result['values']['poseFresh']
            and result['values']['desiredLongitudinalAccel'] is not None
            and result['values']['longitudinalControlActive']
          ):
            break
          time.sleep(0.02)
        assert result is not None
        self.assertEqual(result['state'], 'current')
        self.assertEqual(result['values']['desiredLateralAccel'], 0.42)
        self.assertEqual(result['values']['lateralSource'], 'torqueState')
        self.assertEqual(result['values']['actualLongitudinalAccel'], 0.5)
        self.assertEqual(result['values']['desiredLongitudinalAccel'], 0.6)
        self.assertTrue(result['values']['longitudinalControlActive'])
        self.assertTrue(result['values']['lateralControlActive'])
      finally:
        server.shutdown()
        server_thread.join(2)
        server.server_close()
        del publisher
        messaging.delete_fake_prefix()

  def test_authenticated_http_lazy_and_late_revoke(self):
    class Paused:
      def __init__(self):
        self.calls = 0
        self.entered = threading.Event()
        self.release = threading.Event()
        self.closed = False

      def snapshot(self):
        self.calls += 1
        self.entered.set()
        self.release.wait(2)
        return {'schemaVersion': 1, 'state': 'stale', 'sampleIndex': 0, 'sampleAgeSeconds': None, 'values': None, 'error': ''}

      def close(self):
        self.closed = True

    with tempfile.TemporaryDirectory() as directory:
      owner = GalaxyAccessOwner(Path(directory) / 'access')
      plots = Paused()
      server = make_server(port=0, owner=owner, plots=plots)
      worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
      worker.start()

      def request(path, method='GET', body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        try:
          conn.request(method, path, body=body, headers={'Forwarded': 'for=203.0.113.8', **(headers or {})})
          response = conn.getresponse()
          return response.status, response.read(), dict(response.getheaders())
        finally:
          conn.close()

      try:
        self.assertEqual(request('/api/plots/live')[0], 503)
        owner.configure('password123', lambda: True)
        self.assertEqual(request('/api/plots/live')[0], 401)
        self.assertEqual(plots.calls, 0)
        origin = f'http://127.0.0.1:{server.server_port}'
        status, _, headers = request('/api/auth/login', 'POST', json.dumps({'password': 'password123'}), {'Content-Type': 'application/json', 'Origin': origin})
        self.assertEqual(status, 200)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        plots.release.set()
        status, body, headers = request('/api/plots/live', headers={'Cookie': cookie})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['state'], 'stale')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        plots.release.clear()
        plots.entered.clear()
        delayed = []
        request_thread = threading.Thread(target=lambda: delayed.append(request('/api/plots/live', headers={'Cookie': cookie})))
        request_thread.start()
        self.assertTrue(plots.entered.wait(1))
        self.assertEqual(request('/api/auth/logout', 'POST', '{}', {'Content-Type': 'application/json', 'Origin': origin, 'Cookie': cookie})[0], 200)
        plots.release.set()
        request_thread.join(2)
        self.assertEqual(delayed[0][0], 401)
        self.assertNotIn(b'"sampleIndex"', delayed[0][1])
      finally:
        plots.release.set()
        server.shutdown()
        worker.join(2)
        server.server_close()
      self.assertTrue(plots.closed)


if __name__ == '__main__':
  unittest.main()
