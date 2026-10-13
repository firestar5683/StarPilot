"""Actual consumer: 20 Hz cached sources, 100 Hz caller, genuine hard epoch."""
import unittest

from openpilot.cereal import messaging
from openpilot.starpilot.conditional_mode.consumer import ModeConsumer
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.status import LIFETIME_NS, MODEL_MAX_AGE_NS

T = 10_000_000_000
MS = 1_000_000
DRIVE = T - 1_000 * MS
FINGERPRINT = 'a' * 64
SESSION = 'b' * 32


def proposal(model, car, observed, sequence):
  event = messaging.new_message('slcState', valid=True, logMonoTime=observed)
  event.slcState.conditionalMode = {
    'version': 1, 'sessionId': SESSION, 'sequence': sequence,
    'observedMonoTime': observed, 'validUntilMonoTime': observed + LIFETIME_NS,
    'driveStartMonoTime': DRIVE, 'modelMonoTime': model, 'carStateMonoTime': car,
    'settingsRevision': 1, 'settingsFingerprint': FINGERPRINT,
    'choice': 'conditionalExperimental', 'hasOverride': True,
    'experimental': True, 'status': 'proposed', 'reason': 'cem_stop', 'statusCode': 8,
  }
  return messaging.log_from_bytes(event.to_bytes())


class TestWaitingBarrier(unittest.TestCase):
  def setUp(self):
    self.consumer = ModeConsumer()
    first = proposal(T - 202 * MS, T - 201 * MS, T - 200 * MS, 1)
    self.assertFalse(self.sample(first, T - 200 * MS).accepted)
    warm = proposal(T - 152 * MS, T - 151 * MS, T - 150 * MS, 2)
    self.assertTrue(self.sample(warm, T - 150 * MS).accepted)
    fault = proposal(T - 2 * MS, T - MS, T, 3)
    self.assertFalse(self.sample(fault, T, authority=False).accepted)
    self.assertEqual(self.consumer.barrier_ns, T)
    self.assertIsNone(self.consumer.last)

  def sample(self, event, now, *, model=None, car=None, authority=True, receipt=None):
    value = event.slcState.conditionalMode
    return self.consumer.sample(event.slcState, now_ns=now, now_boot_ns=now + 1_000 * MS,
      sample_skew_ns=1000, message_ns=int(event.logMonoTime),
      receipt_ns=int(event.logMonoTime) if receipt is None else receipt,
      drive_id=DRIVE, model_ns=int(value.modelMonoTime) if model is None else model,
      car_state_ns=int(value.carStateMonoTime) if car is None else car,
      authority=authority, stock_experimental=False, choice=ModeChoice.CEM,
      settings_fingerprint=FINGERPRINT)

  def cached(self, tick):
    now = T + tick * 10 * MS
    # A genuinely new model tick reaches this caller 30 ms after its source time.
    source_tick = (tick * 10 - 30) // 50
    if source_tick < 1:
      return proposal(T - 2 * MS, T - MS, T, 3), T - 2 * MS, T
    model = T + source_tick * 50 * MS
    event = proposal(model, model - MS, model + 5 * MS, 3 + source_tick)
    receipt = model + 30 * MS
    self.assertLessEqual(receipt, now)
    self.assertLess(now - model, MODEL_MAX_AGE_NS)
    self.assertLess(now - int(event.slcState.conditionalMode.carStateMonoTime), LIFETIME_NS)
    return event, model, receipt

  def test_20hz_post_fault_sources_recover_100hz_without_chasing_clock(self):
    for tick in range(1, 31):
      now = T + tick * 10 * MS
      event, model, receipt = self.cached(tick)
      result = self.sample(event, now, model=model, car=now - MS, receipt=receipt)
      if tick < 8:
        self.assertFalse(result.accepted, 'Pre-fault model cannot cross the epoch')
      else:
        self.assertGreater(model, T)
        self.assertGreater(int(event.slcState.conditionalMode.carStateMonoTime), T)
        self.assertTrue(result.accepted, 'Genuinely post-fault paired sources must recover')
        self.assertTrue(result.experimental)
    self.assertEqual(self.consumer.barrier_ns, T)

  def test_waiting_on_same_old_sources_never_accepts_or_moves_epoch(self):
    event = proposal(T - 2 * MS, T - MS, T, 3)
    for tick in range(1, 8):
      self.assertFalse(self.sample(event, T + tick * 10 * MS).accepted)
      self.assertIsNone(self.consumer.last)
    self.assertEqual(self.consumer.barrier_ns, T)

  def test_new_model_alone_cannot_accept_old_car(self):
    event = proposal(T + 50 * MS, T + 49 * MS, T + 55 * MS, 4)
    self.assertFalse(self.sample(event, T + 80 * MS, car=T - MS, receipt=T + 80 * MS).accepted)
    self.assertIsNone(self.consumer.last)
    result = self.sample(event, T + 90 * MS, car=T + 89 * MS, receipt=T + 80 * MS)
    self.assertTrue(result.accepted)
    self.assertEqual(self.consumer.barrier_ns, T)

  def test_fresh_envelope_cannot_renew_pre_fault_proposal_sources(self):
    for model, car in ((T - MS, T + 49 * MS), (T + 50 * MS, T - MS)):
      with self.subTest(model=model, car=car):
        event = proposal(model, car, T + 55 * MS, 4)
        result = self.sample(event, T + 80 * MS, model=T + 50 * MS,
                             car=T + 79 * MS, receipt=T + 80 * MS)
        self.assertFalse(result.accepted)
        self.assertIsNone(self.consumer.last)

  def test_new_authority_fault_requires_newer_sources_again(self):
    event = proposal(T + 50 * MS, T + 49 * MS, T + 55 * MS, 4)
    self.assertFalse(self.sample(event, T + 80 * MS, authority=False, receipt=T + 80 * MS).accepted)
    self.assertEqual(self.consumer.barrier_ns, T + 80 * MS)
    for tick in range(9, 13):
      self.assertFalse(self.sample(event, T + tick * 10 * MS, car=T + (tick * 10 - 1) * MS,
                                   receipt=T + 80 * MS).accepted)
    newer = proposal(T + 100 * MS, T + 99 * MS, T + 105 * MS, 5)
    self.assertTrue(self.sample(newer, T + 130 * MS, car=T + 129 * MS, receipt=T + 130 * MS).accepted)
    self.assertEqual(self.consumer.barrier_ns, T + 80 * MS)

  def test_actual_source_age_failures_still_invalidate(self):
    for source in ('model', 'car'):
      with self.subTest(source=source):
        consumer = self.consumer
        event = proposal(T + 250 * MS, T + 249 * MS, T + 255 * MS, 4)
        now = T + 300 * MS
        changes = {'model': now - MODEL_MAX_AGE_NS - 1} if source == 'model' else {'car': now - LIFETIME_NS - 1}
        self.assertFalse(self.sample(event, now, receipt=now, **changes).accepted)
        self.assertEqual(consumer.barrier_ns, now)
        self.assertIsNone(consumer.last)
        self.consumer = ModeConsumer()
        self.consumer.offset_ns = 1_000 * MS
        self.consumer.drive_id = DRIVE
        self.consumer.last_now_ns = T
        self.consumer.barrier_ns = T

  def test_original_proposal_expiry_cannot_be_renewed(self):
    event = proposal(T + 50 * MS, T + 49 * MS, T + 55 * MS, 4)
    now = T + 155 * MS + 1
    result = self.sample(event, now, model=T + 150 * MS, car=now - MS, receipt=T + 100 * MS)
    self.assertFalse(result.accepted)
    self.assertIsNone(self.consumer.last)
    self.assertEqual(self.consumer.barrier_ns, T)
