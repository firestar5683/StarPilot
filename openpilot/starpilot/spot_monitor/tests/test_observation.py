"""Serialized V-ASM wire and historical @136 compatibility tests."""

import math
import unittest

from openpilot.cereal import log
from openpilot.starpilot.spot_monitor.inference import MODEL_SHA256
from openpilot.starpilot.spot_monitor.observation import ObservationReader


SESSION = "a" * 32
OTHER_SESSION = "c" * 32
FINGERPRINT = "b" * 64
M = 1_000_000
# Actual frozen StarPilotLateralManeuverPlanDEPRECATED Event bytes, emitted by
# the frozen parser in a separate process (Cap'n Proto IDs cannot be loaded
# twice into one process). The historical field remains curvature in 1/m.
FROZEN_CURVATURE_EVENT = bytes.fromhex(
  "00000000050000000000000002000100000000000000000086000000000000000000000001000000cdcc4c3c00000000")


def packet(*, session=SESSION, sequence=1, frame_id=0, observed=1000*M,
           eof=900*M, side_eof=None, side_frame_id=0, valid=True):
  msg = log.Event.new_message()
  msg.init("spotMonitorState")
  msg.valid = valid
  msg.logMonoTime = observed
  obs = msg.spotMonitorState.init("observation")
  obs.version = 1
  obs.producerSessionId = session
  obs.sequence = sequence
  obs.modelSha256 = MODEL_SHA256
  obs.settingsFingerprint = FINGERPRINT
  obs.observedMonoTime = observed
  obs.observedBootTime = observed
  obs.sourceFrameId = frame_id
  obs.sourceFrameEofBootTime = eof
  obs.validUntilBootTime = eof + 500*M
  left = obs.init("left")
  left.status = "warning"
  left.confidence = 0.96
  left.warning = True
  left.sourceFrameId = side_frame_id
  left.sourceFrameEofBootTime = eof if side_eof is None else side_eof
  left.sourceObservedMonoTime = left.sourceFrameEofBootTime
  left.validUntilBootTime = left.sourceFrameEofBootTime + 3000*M
  return msg


def read(reader, msg, *, now=1100*M, fingerprint=FINGERPRINT, boot_offset=0):
  msg.clear_write_flag()  # The cached-event regression serializes one builder twice.
  with log.Event.from_bytes(msg.to_bytes()) as event:
    return reader.read(event, now_mono_ns=now, now_boot_ns=now + boot_offset,
                       settings_fingerprint=fingerprint)


class ObservationWireTest(unittest.TestCase):
  def test_historical_curvature_has_no_vasm_version(self):
    with log.Event.from_bytes(FROZEN_CURVATURE_EVENT) as event:
      self.assertEqual(event.which(), "spotMonitorState")
      self.assertAlmostEqual(event.spotMonitorState.desiredCurvature, 0.0125)
      self.assertEqual(event.spotMonitorState.observation.version, 0)
      self.assertFalse(ObservationReader().read(event, now_mono_ns=1100*M,
                                                now_boot_ns=1100*M,
                                                settings_fingerprint=FINGERPRINT).display_left.warning)

  def test_serialized_warning_expires_even_when_cached_event_is_reused(self):
    reader = ObservationReader()
    first = packet()
    self.assertTrue(read(reader, first).display_left.warning)
    self.assertTrue(reader.current_at(now_mono_ns=1200*M, now_boot_ns=1200*M,
                                      settings_fingerprint=FINGERPRINT).display_left.warning)
    # The camera may publish at 1 Hz; validated warnings retain the original
    # 3-second hold even though a new frame must be admitted within 500 ms.
    self.assertTrue(read(reader, first, now=1401*M).display_left.warning)
    self.assertFalse(reader.current_at(now_mono_ns=3901*M, now_boot_ns=3901*M,
                                       settings_fingerprint=FINGERPRINT).display_left.warning)

  def test_new_frame_does_not_renew_other_side_hold(self):
    reader = ObservationReader()
    self.assertTrue(read(reader, packet()).display_left.warning)
    later = packet(sequence=2, frame_id=1, observed=1500*M, eof=1450*M,
                   side_eof=900*M)
    self.assertTrue(read(reader, later, now=1550*M).display_left.warning)
    very_late = packet(sequence=3, frame_id=2, observed=4000*M, eof=3950*M,
                       side_eof=900*M)
    self.assertFalse(read(reader, very_late, now=4050*M).display_left.warning)

  def test_replay_invalid_loss_and_session_retirement(self):
    reader = ObservationReader()
    self.assertTrue(read(reader, packet()).display_left.warning)
    self.assertTrue(read(reader, packet(sequence=1, valid=False)).display_left.warning)
    self.assertFalse(read(reader, packet(sequence=2, frame_id=1, observed=1200*M,
                                         eof=1150*M, valid=False), now=1250*M).display_left.warning)
    self.assertTrue(read(reader, packet(session=OTHER_SESSION, observed=1400*M,
                                        eof=1350*M), now=1450*M).display_left.warning)
    self.assertTrue(read(reader, packet(session=SESSION, observed=1500*M,
                                        eof=1450*M, valid=False), now=1550*M).display_left.warning)

  def test_invalid_reset_retires_old_session_before_delayed_valid_packet(self):
    reader = ObservationReader()
    self.assertTrue(read(reader, packet()).display_left.warning)
    self.assertFalse(read(reader, packet(session=OTHER_SESSION, sequence=0,
                                         observed=1200*M, eof=0, valid=False),
                          now=1250*M).display_left.warning)
    # The old producer's later sequence remains in-flight after its reset.
    self.assertFalse(read(reader, packet(session=SESSION, sequence=2, frame_id=1,
                                         observed=1300*M, eof=1250*M), now=1350*M).display_left.warning)
    self.assertTrue(read(reader, packet(session=OTHER_SESSION, observed=1400*M,
                                        eof=1350*M), now=1450*M).display_left.warning)

  def test_backward_clock_cannot_resurrect_expired_warning(self):
    reader = ObservationReader()
    self.assertTrue(read(reader, packet()).display_left.warning)
    self.assertFalse(reader.current_at(now_mono_ns=3901*M, now_boot_ns=3901*M,
                                       settings_fingerprint=FINGERPRINT).display_left.warning)
    self.assertFalse(reader.current_at(now_mono_ns=1100*M, now_boot_ns=1100*M,
                                       settings_fingerprint=FINGERPRINT).display_left.warning)
    self.assertFalse(read(reader, packet(sequence=2, frame_id=1,
                                         observed=1200*M, eof=1150*M), now=1250*M).display_left.warning)

  def test_bad_source_settings_hash_and_resume_fail_closed(self):
    for mutate in (lambda m: setattr(m.spotMonitorState.observation, "modelSha256", "0" * 64),
                   lambda m: setattr(m.spotMonitorState.observation, "settingsFingerprint", "0" * 64),
                   lambda m: setattr(m.spotMonitorState.observation, "validUntilBootTime", 9000*M),
                   lambda m: setattr(m.spotMonitorState.observation.left, "sourceObservedMonoTime", 500*M),
                   lambda m: setattr(m.spotMonitorState.observation.left, "confidence", math.nan)):
      with self.subTest(mutate=mutate):
        msg = packet()
        mutate(msg)
        self.assertFalse(read(ObservationReader(), msg).display_left.warning)
    reader = ObservationReader()
    self.assertTrue(read(reader, packet()).display_left.warning)
    self.assertFalse(reader.current_at(now_mono_ns=1200*M, now_boot_ns=10200*M,
                                       settings_fingerprint=FINGERPRINT).display_left.warning)
    # A queued pre-resume packet cannot claim the new BOOT/MONO epoch.
    self.assertFalse(read(reader, packet(sequence=2, frame_id=1, observed=1150*M,
                                         eof=1100*M), now=1200*M, boot_offset=9000*M).display_left.warning)

  def test_nonzero_boot_offset_and_future_frame_bounds(self):
    def shifted():
      msg = packet()
      wire = msg.spotMonitorState.observation
      wire.observedBootTime += 9000*M
      wire.sourceFrameEofBootTime += 9000*M
      wire.validUntilBootTime += 9000*M
      wire.left.sourceFrameEofBootTime += 9000*M
      wire.left.validUntilBootTime += 9000*M
      return msg

    self.assertTrue(read(ObservationReader(), shifted(), now=1100*M,
                         boot_offset=9000*M).display_left.warning)
    future = shifted()
    future.spotMonitorState.observation.sourceFrameEofBootTime = 10150*M
    self.assertFalse(read(ObservationReader(), future, now=1100*M,
                          boot_offset=9000*M).display_left.warning)


if __name__ == "__main__":
  unittest.main()
