"""The actual paired sampler bounds midpoint error without renewing proposals."""
import unittest
from unittest.mock import patch

from openpilot.starpilot.conditional_mode import projection
from openpilot.starpilot.conditional_mode.consumer import ModeConsumer
from openpilot.starpilot.conditional_mode.policy import ManualIntent
from openpilot.starpilot.conditional_mode.preferences import manual_for_drive
from openpilot.starpilot.conditional_mode.status import LIFETIME_NS
from openpilot.starpilot.conditional_mode.tests import test_status_consumer as transport
from openpilot.starpilot.conditional_mode.tests.test_projection import MONO, BOOT, CP, FakeSubMaster, serialized_scene


class TestPairedClock(unittest.TestCase):
  def setUp(self):
    self.fixture = transport.TestModeTransport(methodName='runTest')
    self.fixture.setUp()
    self.addCleanup(self.fixture.doCleanups)
    self.fixture.consumer = ModeConsumer()
    self.sample(None, MONO)

  def pair(self, now, *, offset=-500, skew=2000):
    before = now - skew // 2
    after = before + skew
    with patch.object(projection.time, 'monotonic_ns', side_effect=(before, after)), \
         patch.object(projection.time, 'clock_gettime_ns', return_value=now + offset):
      result = projection.paired_clocks_ns()
    self.assertIsNotNone(result)
    assert result is not None
    self.assertEqual(result, (now, now + offset, skew))
    return result

  def sample(self, event, now, *, offset=-500, skew=2000, **changes):
    mono, boot, error = self.pair(now, offset=offset, skew=skew)
    return self.fixture.consume(event, mono, now_boot_ns=boot, sample_skew_ns=error, **changes)

  def test_asymmetric_actual_clock_pair_accepts_fresh_proposal(self):
    now = MONO + 50_000_000
    event, _, _ = self.fixture.produce(now)
    result = self.sample(event, now)
    self.assertTrue(result.accepted)
    self.assertTrue(result.experimental)
    self.assertIsNone(self.fixture.consumer.rejection)

  def test_exact_midpoint_half_skew_bound_accepts_even_and_odd_pairs(self):
    for skew in (1999, 2000):
      with self.subTest(skew=skew):
        now = MONO + 50_000_000 + skew
        event, _, _ = self.fixture.produce(now)
        self.assertTrue(self.sample(event, now, offset=-(skew // 2), skew=skew).accepted)
        self.assertIsNone(self.fixture.consumer.rejection)

  def test_negative_offset_beyond_midpoint_bound_rejected(self):
    for skew in (1999, 2000):
      with self.subTest(skew=skew):
        now = MONO + 50_000_000
        event, _, _ = self.fixture.produce(now)
        self.assertFalse(self.sample(event, now, offset=-(skew // 2)-1, skew=skew).accepted)
        self.assertEqual(self.fixture.consumer.rejection, 'clock_inputs')
        self.assertIsNone(self.fixture.consumer.last)

  def test_valid_zero_and_positive_offsets_accept_fresh_proposals(self):
    for offset in (0, 100_000):
      with self.subTest(offset=offset):
        now = MONO + 50_000_000 + offset
        event, _, _ = self.fixture.produce(now)
        self.assertTrue(self.sample(event, now, offset=offset).accepted)
        self.assertIsNone(self.fixture.consumer.rejection)

  def test_true_clock_discontinuity_remains_rejected(self):
    now = MONO + 50_000_000
    event, _, _ = self.fixture.produce(now)
    self.assertFalse(self.sample(event, now, offset=2_000_000).accepted)
    self.assertEqual(self.fixture.consumer.rejection, 'discontinuity')
    self.assertEqual(self.fixture.consumer.barrier_ns, now)

  def test_sampling_bound_cannot_renew_original_proposal_expiry(self):
    now = MONO + 50_000_000
    # Same-time typed model/car sources remove an unrelated earlier source-age
    # limit, so this test reaches the proposal's exact original expiry.
    sm = FakeSubMaster(serialized_scene(stamp=BOOT + now - MONO), now)
    proposal = self.fixture.host.sample(
      sm, CP, now_mono_ns=now, now_boot_ns=BOOT + now - MONO, sample_skew_ns=1000,
      drive_id=self.fixture.drive_id, settings_owner=self.fixture.owner,
      manual=manual_for_drive(ManualIntent.FORCE_EXPERIMENTAL, self.fixture.drive_id, self.fixture.drive_id + 1),
      selected_t_follow_s=1.45, selected_t_follow_observed_mono_ns=now)
    event = self.fixture.publisher.attach(None, proposal, self.fixture.owner.current,
      now_ns=now, drive_id=self.fixture.drive_id, model_ns=now, car_state_ns=now)
    original_envelope = event.to_bytes()
    self.assertEqual(event.logMonoTime, now)
    self.assertTrue(self.sample(event, now, message_ns=now, receipt_ns=now,
                                model_ns=now, car_state_ns=now).accepted)
    original = self.fixture.consumer.last
    assert original is not None
    self.assertEqual(original.expires_ns, now + LIFETIME_NS)
    expiry = original.expires_ns
    self.assertTrue(self.sample(event, expiry, message_ns=now, receipt_ns=now,
                                model_ns=expiry, car_state_ns=expiry).accepted)
    self.assertEqual(self.fixture.consumer.last, original)
    self.assertEqual(event.to_bytes(), original_envelope)
    self.assertFalse(self.sample(event, expiry + 1, message_ns=now, receipt_ns=now,
                                 model_ns=expiry + 1, car_state_ns=expiry + 1).accepted)
    self.assertEqual(self.fixture.consumer.rejection, 'proposal_invalid')
    self.assertEqual(self.fixture.consumer.last, original)
    self.assertEqual(self.fixture.consumer.last.expires_ns, expiry)
    self.assertEqual(event.to_bytes(), original_envelope)

  def test_monotonic_rollback_and_drive_change_still_require_new_sources(self):
    now = MONO + 50_000_000
    event, _, _ = self.fixture.produce(now)
    self.assertTrue(self.sample(event, now).accepted)
    self.assertFalse(self.sample(event, now - 1).accepted)
    self.assertEqual(self.fixture.consumer.rejection, 'discontinuity')
    self.assertIsNone(self.fixture.consumer.last)
    self.assertFalse(self.sample(event, now + 1, drive_id=self.fixture.drive_id + 1).accepted)
    self.assertEqual(self.fixture.consumer.rejection, 'discontinuity')
    self.assertEqual(self.fixture.consumer.barrier_ns, now + 1)
