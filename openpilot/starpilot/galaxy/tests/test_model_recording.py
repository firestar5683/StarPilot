import unittest
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from openpilot.cereal import messaging
from openpilot.cereal.services import SERVICE_LIST
from openpilot.starpilot.models.receipt import ModelReceiptOwner, recorded_model_message, logged_model_load
from openpilot.starpilot.models.status import ModelLoad, ModelVariant
from openpilot.starpilot.galaxy.drive_analysis import analyze_route
from openpilot.starpilot.galaxy.tests.test_drive_analysis import event, write, selection, BASE


class ModelRecordingTest(unittest.TestCase):
  def test_actual_model_heartbeat_transport_and_late_route_qlog(self):
    load = ModelLoad(123, 17, BASE - 500_000_000, 'sc23', ModelVariant.SMALL, 'a' * 64)
    owner = ModelReceiptOwner()
    owner.load = load

    class Publisher:
      def send(self, service, message):
        self.service = service
        self.raw = message.to_bytes()

    publisher = Publisher()
    self.assertTrue(owner.publish(publisher, BASE + 200_000_000))
    self.assertEqual(publisher.service, 'modelIdentity')
    self.assertTrue(SERVICE_LIST['modelIdentity'].should_log)
    self.assertEqual(SERVICE_LIST['modelIdentity'].decimation, 1)
    heartbeat = messaging.log_from_bytes(publisher.raw)
    self.assertEqual(heartbeat.which(), 'logMessage')
    self.assertEqual(logged_model_load(str(heartbeat.logMessage)), load)
    self.assertFalse(owner.publish(publisher, BASE + 1_000_000_000))
    message = messaging.new_message(None, valid=True, logMonoTime=BASE + 200_000_000)
    message.logMessage = recorded_model_message(load)
    with TemporaryDirectory() as directory:
      events = [
        event('carState', BASE, vEgo=5),
        event('selfdriveState', BASE, enabled=True),
        event('drivingModelData', BASE + 100_000_000, big=False),
        message,
        event('carState', BASE + 500_000_000, vEgo=5),
        event('selfdriveState', BASE + 500_000_000, enabled=True),
        event('sentinel', BASE + 500_000_000, type='endOfRoute'),
      ]
      result = analyze_route(Path(directory), selection(write(Path(directory), 0, events, kind='qlog')), permitted=lambda: True)
      self.assertTrue(result['complete'], result)
      self.assertIn('(', result['model'])
      self.assertNotIn('identity not recorded', result['model'])

  def test_recorder_socket_accepts_existing_event_union(self):
    from openpilot.common.prefix import OpenpilotPrefix

    prefix = OpenpilotPrefix()
    prefix.__enter__()
    self.addCleanup(prefix.__exit__, None, None, None)
    publisher = messaging.PubMaster(['modelIdentity'])
    subscriber = messaging.sub_sock('modelIdentity', timeout=1000)
    load = ModelLoad(123, 17, BASE, 'sc23', ModelVariant.SMALL, 'a' * 64)
    owner = ModelReceiptOwner()
    owner.load = load
    time.sleep(0.05)
    self.assertTrue(owner.publish(publisher, BASE + 5_000_000_000))
    received = messaging.recv_one(subscriber)
    self.assertIsNotNone(received)
    self.assertEqual(received.which(), 'logMessage')
    self.assertEqual(logged_model_load(str(received.logMessage)), load)
