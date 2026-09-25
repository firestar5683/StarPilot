import unittest

from openpilot.starpilot.ui.conditional_status import ConditionalDisplayProjector
from openpilot.starpilot.ui.tests.test_conditional_status import DRIVE, NOW, SOURCE, acknowledged


class ConditionalDisplayCadenceTests(unittest.TestCase):
  def setUp(self):
    self.projector = ConditionalDisplayProjector()

  def project(self, ack, *, now=NOW, source=SOURCE, enabled=True, experimental=True):
    return self.projector.project(
      ack, now_ns=now, event_ns=int(ack.conditionalModeAck.observedMonoTime),
      selfdrive_ns=source, drive_id=DRIVE, selfdrive_experimental=experimental,
      selfdrive_enabled=enabled, long_active=True, car_valid=True, system_long=True)

  def test_independent_sockets_do_not_clear_a_fresh_unchanged_mode(self):
    ack = acknowledged()
    first = self.project(ack)
    self.assertIsNotNone(first)
    for elapsed in (10_000_000, 20_000_000, 40_000_000, 199_000_000):
      self.assertEqual(self.project(ack, now=NOW + elapsed, source=NOW + elapsed - 1_000_000), first)
    self.assertIsNone(self.project(ack, now=NOW + 200_000_001, source=NOW + 199_000_000))

  def test_newer_state_must_still_match_and_explicit_rejection_wins(self):
    ack = acknowledged()
    self.assertIsNotNone(self.project(ack))
    self.assertIsNone(self.project(ack, now=NOW + 10_000_000, source=NOW + 9_000_000, enabled=False))
    self.assertIsNone(self.project(ack, now=NOW + 10_000_000, source=NOW + 9_000_000, experimental=False))
    self.assertIsNotNone(self.project(ack, source=SOURCE - 1))
    self.assertIsNone(self.project(ack, source=SOURCE - 50_000_001))
    self.assertIsNone(self.project(ack, source=NOW + 1))
    rejected = acknowledged(sequence=2, accepted=False, experimental=False, observed_ns=NOW + 10_000_000)
    self.assertIsNone(self.project(rejected, now=NOW + 10_000_000, source=NOW + 9_000_000, experimental=False))
    self.assertIsNone(self.project(ack, now=NOW + 11_000_000, source=NOW + 10_000_000))
