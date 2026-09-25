"""Worker failure must terminate the supervisor instead of hiding missing IMU."""
import ctypes
import errno
import threading

from typing import cast
from unittest.mock import Mock, patch

from openpilot.cereal import log

from openpilot.common.test import OpenpilotTestCase
from openpilot.system.sensord import sensord
from openpilot.system.manager.process_config import managed_processes


class TestSensorWorkerLifecycle(OpenpilotTestCase):
  def test_interrupt_worker_failure_stops_polling_and_shuts_down_sensors(self):
    for failed_index in (0, 1):
      with self.subTest(failed_index=failed_index):
        sensors = [Mock(), Mock(), Mock()]
        threads = []

        class Worker:
          def __init__(self, target, args, daemon, threads=threads, failed_index=failed_index):
            self.failed_index = failed_index
            self.event = args[1] if target is sensord.interrupt_loop else args[-1]
            self.index = len(threads)
            self.started = False
            self.joined = False
            threads.append(self)
          def start(self):
            self.started = True
          def is_alive(self):
            return self.started and self.index != self.failed_index and not self.event.is_set()
          def join(self):
            self.joined = True

        with patch.object(sensord, 'config_realtime_process'), \
             patch.object(sensord, 'LSM6DS3_Accel', return_value=sensors[0]), \
             patch.object(sensord, 'LSM6DS3_Gyro', return_value=sensors[1]), \
             patch.object(sensord, 'LSM6DS3_Temp', return_value=sensors[2]), \
             patch.object(sensord.threading, 'Thread', Worker), \
             patch.object(sensord.time, 'sleep', side_effect=AssertionError('Dead worker must not be hidden by live sibling')), \
             patch.object(sensord.cloudlog, 'error') as error:
          sensord.main()
        self.assertEqual(len(threads), 2)
        self.assertTrue(all(t.started for t in threads))
        self.assertTrue(all(t.event.is_set() for t in threads))
        error.assert_called_once_with('Sensor worker exited; stopping sensord for recovery')
        for sensor in sensors:
          sensor.reset.assert_called_once()
          sensor.init.assert_called_once()
          sensor.shutdown.assert_called_once()

  def test_sensor_manager_recovery_is_enabled_without_changing_onroad_gate(self):
    process = managed_processes['sensord']
    self.assertTrue(process.restart_on_exit)
    self.assertFalse(process.sigkill)


  def test_actual_interrupt_acquisition_failure_is_not_valid_sensor_data(self):
    sensor = Mock()
    with patch.object(sensord.messaging, 'PubMaster') as publisher, \
         patch.object(sensord, 'gpiochip_get_ro_value_fd', side_effect=OSError(errno.EBUSY, 'line already requested')):
      with self.assertRaises(OSError) as failure:
        sensord.interrupt_loop([(sensor, 'accelerometer', True)], threading.Event(), {})
    self.assertEqual(failure.exception.errno, errno.EBUSY)
    publisher.return_value.send.assert_not_called()
    sensor.get_event.assert_not_called()

  def test_three_fresh_interrupt_cycles_publish_only_valid_readings(self):
    for cycle in range(3):
      with self.subTest(cycle=cycle):
        event = threading.Event()
        irq = sensord.gpioevent_data()
        irq.timestamp = 1_000_001_000
        irq.id = 1
        raw_irq = bytes(irq)
        self.assertEqual(len(raw_irq), ctypes.sizeof(sensord.gpioevent_data))
        reads = []
        published = {}
        sensors = []
        for service, field in (('accelerometer', 'acceleration'), ('gyroscope', 'gyroUncalibrated')):
          sensor = Mock()
          def reading(stamp, field=field):
            data = log.SensorEventData.new_message()
            data.timestamp = stamp
            data.source = log.SensorEventData.SensorSource.lsm6ds3
            data.init(field).v = [0., 0., 0.]
            return data
          sensor.get_event.side_effect = reading
          sensor.is_data_valid.side_effect = [False, True]
          sensors.append((cast(sensord.Sensor, sensor), service, True))

        def receive(*_, reads=reads, event=event, raw_irq=raw_irq):
          reads.append(True)
          if len(reads) == 2:
            event.set()
          return raw_irq

        with patch.object(sensord.messaging, 'PubMaster') as publisher, \
             patch.object(sensord, 'gpiochip_get_ro_value_fd', return_value=20) as acquire, \
             patch.object(sensord.os.path, 'exists', return_value=False), \
             patch.object(sensord.select, 'poll') as poller, \
             patch.object(sensord.os, 'read', side_effect=receive), \
             patch.object(sensord.time, 'time_ns', return_value=2_000_000_000), \
             patch.object(sensord.time, 'monotonic_ns', return_value=1_000_000_000), \
             patch.object(sensord.time, 'monotonic', return_value=cycle + 10.):
          poller.return_value.poll.return_value = [(20, sensord.select.POLLIN)]
          sensord.interrupt_loop(sensors, event, published)
        acquire.assert_called_once_with('sensord', 0, 84)
        self.assertEqual(published, {'accelerometer': cycle + 10., 'gyroscope': cycle + 10.})
        self.assertEqual(len(reads), 2)
        self.assertEqual(publisher.return_value.send.call_count, 2)
        for call in publisher.return_value.send.call_args_list:
          service, message = call.args
          self.assertTrue(message.valid)
          self.assertEqual(getattr(message, service).timestamp, 1000)
        for sensor, _, _ in sensors:
          self.assertEqual(sensor.get_event.call_count, 2)
          self.assertEqual(sensor.is_data_valid.call_count, 2)


  def test_three_cycles_of_alive_missing_or_single_stalled_imu_exit_before_alert(self):
    for cycle in range(3):
      for healthy_accel in (False, True):
        with self.subTest(cycle=cycle, healthy_accel=healthy_accel):
          now = [10. + cycle * 10.]
          baseline = now[0]
          sensors = [Mock(), Mock(), Mock()]
          workers = []
          publications = {}

          class Worker:
            def __init__(self, target, args, daemon, publications=publications, workers=workers):
              self.event = args[1] if target is sensord.interrupt_loop else args[-1]
              self.started = False
              if target is sensord.interrupt_loop:
                publications['last'] = args[2]
              workers.append(self)
            def start(self, publications=publications, baseline=baseline):
              self.started = True
              self_baseline = publications['last']
              assert self_baseline == {'accelerometer': baseline, 'gyroscope': baseline}
            def is_alive(self):
              return self.started and not self.event.is_set()
            def join(self):
              pass

          def wait(seconds, now=now, healthy_accel=healthy_accel, publications=publications, baseline=baseline):
            self.assertEqual(seconds, 1)
            now[0] += seconds
            if healthy_accel:
              publications['last']['accelerometer'] = now[0]
            self.assertLess(now[0] - baseline, 10.)

          with patch.object(sensord, 'config_realtime_process'), \
               patch.object(sensord, 'LSM6DS3_Accel', return_value=sensors[0]), \
               patch.object(sensord, 'LSM6DS3_Gyro', return_value=sensors[1]), \
               patch.object(sensord, 'LSM6DS3_Temp', return_value=sensors[2]), \
               patch.object(sensord.threading, 'Thread', Worker), \
               patch.object(sensord.time, 'monotonic', side_effect=lambda now=now: now[0]), \
               patch.object(sensord.time, 'sleep', side_effect=wait), \
               patch.object(sensord.cloudlog, 'error') as error:
            sensord.main()
          self.assertEqual(now[0] - baseline, 2.)
          error.assert_called_once_with('Sensor publication stalled: %s',
                                       'gyroscope' if healthy_accel else 'accelerometer,gyroscope')
          self.assertTrue(all(worker.event.is_set() for worker in workers))
          for sensor in sensors:
            sensor.reset.assert_called_once()
            sensor.init.assert_called_once()
            sensor.shutdown.assert_called_once()

  def test_invalid_readings_and_failed_sends_do_not_renew_publication(self):
    for cycle in range(3):
      for valid in (False, True):
        with self.subTest(cycle=cycle, valid=valid):
          event = threading.Event()
          irq = sensord.gpioevent_data()
          irq.timestamp = 1_000_001_000
          sensor = Mock()
          data = log.SensorEventData.new_message()
          data.timestamp = 1000
          data.source = log.SensorEventData.SensorSource.lsm6ds3
          data.init('acceleration').v = [0., 0., 0.]
          sensor.get_event.return_value = data
          sensor.is_data_valid.return_value = valid
          published = {'accelerometer': 10.}

          def receive(*_, event=event, irq=irq):
            event.set()
            return bytes(irq)

          with patch.object(sensord.messaging, 'PubMaster') as publisher, \
               patch.object(sensord, 'gpiochip_get_ro_value_fd', return_value=20), \
               patch.object(sensord.os.path, 'exists', return_value=False), \
               patch.object(sensord.select, 'poll') as poller, \
               patch.object(sensord.os, 'read', side_effect=receive), \
               patch.object(sensord.time, 'time_ns', return_value=2_000_000_000), \
               patch.object(sensord.time, 'monotonic_ns', return_value=1_000_000_000), \
               patch.object(sensord.time, 'monotonic', return_value=15.), \
               patch.object(sensord.cloudlog, 'exception'):
            poller.return_value.poll.return_value = [(20, sensord.select.POLLIN)]
            publisher.return_value.send.side_effect = OSError('publication failed')
            sensord.interrupt_loop([(sensor, 'accelerometer', True)], event, published)
          self.assertEqual(published, {'accelerometer': 10.})
          self.assertEqual(publisher.return_value.send.call_count, int(valid))


  def test_three_empty_irq_poll_cycles_never_renew_imu_publication(self):
    for cycle in range(3):
      with self.subTest(cycle=cycle):
        event = threading.Event()
        published = {'accelerometer': 10., 'gyroscope': 10.}
        sensor = Mock()
        polls = []

        def empty_poll(timeout, polls=polls, event=event):
          self.assertEqual(timeout, 100)
          polls.append(True)
          if len(polls) == 3:
            event.set()
          return []

        with patch.object(sensord.messaging, 'PubMaster') as publisher, \
             patch.object(sensord, 'gpiochip_get_ro_value_fd', return_value=20), \
             patch.object(sensord.os.path, 'exists', return_value=False), \
             patch.object(sensord.select, 'poll') as poller, \
             patch.object(sensord.cloudlog, 'error'), \
             patch.object(sensord.time, 'time_ns', return_value=2_000_000_000), \
             patch.object(sensord.time, 'monotonic_ns', return_value=1_000_000_000):
          poller.return_value.poll.side_effect = empty_poll
          sensord.interrupt_loop([(sensor, 'accelerometer', True)], event, published)
        self.assertEqual(len(polls), 3)
        self.assertEqual(published, {'accelerometer': 10., 'gyroscope': 10.})
        publisher.return_value.send.assert_not_called()
        sensor.get_event.assert_not_called()
