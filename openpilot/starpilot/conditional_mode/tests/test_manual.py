"""Frozen wheel mapping and one-drive manual intent, without a live publisher."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opendbc.car.structs import car
from opendbc.car.hyundai.ioniq6_media import MediaObservation, MediaSample
from openpilot.common.params import Params
from openpilot.starpilot.conditional_mode.manual import (
  Button, ButtonMap, ButtonTracker, Gesture, IoniqMediaMapCache, ManualSession, Press, read_button_map,
)
from openpilot.starpilot.conditional_mode.policy import ManualIntent, ModeChoice


ButtonType = car.CarState.ButtonEvent.Type


def state(*events, valid=True):
  return car.CarState(canValid=valid, buttonEvents=[car.CarState.ButtonEvent(type=button, pressed=pressed)
                                                   for button, pressed in events])


class ManualSettingsTests(unittest.TestCase):
  def test_one_media_map_read_per_edge_and_bounded_neutral_audit(self):
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      cache = IoniqMediaMapCache()
      original = read_button_map
      calls = []

      def read_once(source, *, include_ioniq_media=False):
        calls.append(include_ioniq_media)
        return original(source, include_ioniq_media=include_ioniq_media)

      def packet(mode, custom, stamp, now):
        media = MediaObservation((MediaSample(mode, custom, stamp),), stamp, 0, True)
        return cache.sample(params, media, now)

      with patch('openpilot.starpilot.conditional_mode.manual.read_button_map', side_effect=read_once):
        first = packet(False, False, 1_000_000_000, 10_000_000_000)
        for step in range(1, 5):
          self.assertEqual(packet(False, False, 1_000_000_000 + step * 200_000_000,
                                  10_000_000_000 + step * 200_000_000), first)
        self.assertEqual(len(calls), 1)
        packet(False, False, 2_000_000_000, 11_000_000_000)
        self.assertEqual(len(calls), 2)
        packet(True, False, 2_200_000_000, 11_200_000_000)
        self.assertEqual(len(calls), 3)
        packet(True, False, 2_400_000_000, 11_400_000_000)
        self.assertEqual(len(calls), 3)
        packet(False, False, 2_600_000_000, 11_600_000_000)
        self.assertEqual(len(calls), 4)
        params.put('ModeButtonControl', 6, block=True)
        changed = packet(True, False, 2_800_000_000, 11_800_000_000)
        self.assertEqual(changed.mode, 6)
        self.assertEqual(len(calls), 5)

  def test_registered_params_are_opt_in_and_corruption_is_preserved(self):
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      self.assertEqual(read_button_map(params), ButtonMap())
      params.put('LKASButtonControl', 5, block=True)
      params.put('LongDistanceButtonControl', 5, block=True)
      buttons = read_button_map(params, include_ioniq_media=True)
      self.assertEqual(buttons, ButtonMap(lkas=5, distance_long=5))
      self.assertTrue(buttons.assigned(Gesture(Button.LKAS, Press.SHORT)))
      self.assertTrue(buttons.assigned(Gesture(Button.DISTANCE, Press.LONG)))
      self.assertFalse(buttons.assigned(Gesture(Button.DISTANCE, Press.SHORT)))
      params.put('ModeButtonControl', 5, block=True)
      params.put('LongStarButtonControl', 5, block=True)
      buttons = read_button_map(params, include_ioniq_media=True)
      self.assertTrue(buttons.assigned(Gesture(Button.MODE, Press.SHORT)))
      self.assertTrue(buttons.assigned(Gesture(Button.CUSTOM, Press.LONG)))
      self.assertFalse(buttons.assigned(Gesture(Button.CUSTOM, Press.SHORT)))
      Path(params.get_param_path('ModeButtonControl')).write_bytes(b'05')
      self.assertIsNone(read_button_map(params, include_ioniq_media=True))
      self.assertEqual(read_button_map(params), ButtonMap(lkas=5, distance_long=5))
      params.put('ModeButtonControl', 5, block=True)
      path = Path(params.get_param_path('LongDistanceButtonControl'))
      path.write_bytes(b'05')
      self.assertIsNone(read_button_map(params))
      self.assertEqual(path.read_bytes(), b'05')
      params.put('LongDistanceButtonControl', 5, block=True)
      params.put('CancelButtonControl', 5, block=True)
      self.assertIsNone(read_button_map(params))  # cancel remap is unreviewed here


class ManualGestureTests(unittest.TestCase):
  @staticmethod
  def media(*samples, epoch=0, valid=True):
    return MediaObservation(tuple(MediaSample(mode, custom, stamp) for mode, custom, stamp in samples),
                            samples[-1][2] if samples else 1, epoch, valid)

  def test_media_uses_fresh_source_stamps_and_neutral_baseline(self):
    tracker = ButtonTracker()
    neutral = self.media((False, False, 1_400_000_000))
    held = self.media((True, False, 1_200_000_000))
    self.assertEqual(tracker.observe(state(), held), ())  # held at startup
    self.assertEqual(tracker.observe(state(), neutral), ())
    self.assertEqual(tracker.observe(state(), self.media((True, False, 1_600_000_000))), ())
    self.assertEqual(tracker.observe(state(), self.media()), ())  # 100 Hz cached state is not evidence
    self.assertEqual(tracker.observe(state(), self.media((False, False, 1_800_000_000))),
                     (Gesture(Button.MODE, Press.SHORT),))

  def test_media_long_very_long_and_source_loss(self):
    tracker = ButtonTracker()
    tracker.observe(state(), self.media((False, False, 1_000_000_000)))
    tracker.observe(state(), self.media((False, True, 1_200_000_000)))
    self.assertEqual(tracker.observe(state(), self.media((False, True, 1_400_000_000))), ())
    self.assertEqual(tracker.observe(state(), self.media((False, True, 1_800_000_000))),
                     (Gesture(Button.CUSTOM, Press.LONG),))
    for stamp in range(2_000_000_000, 3_800_000_000, 200_000_000):
      tracker.observe(state(), self.media((False, True, stamp)))
    self.assertEqual(tracker.observe(state(), self.media((False, True, 3_800_000_000))),
                     (Gesture(Button.CUSTOM, Press.VERY_LONG),))
    self.assertEqual(tracker.observe(state(), self.media((False, False, 4_000_000_000))), ())
    tracker.observe(state(), self.media((True, False, 4_200_000_000)))
    self.assertEqual(tracker.observe(state(), self.media(epoch=1, valid=False)), ())
    self.assertEqual(tracker.observe(state(), self.media((False, False, 4_400_000_000), epoch=1)), ())
    self.assertEqual(tracker.observe(state(), self.media((True, False, 4_600_000_000), epoch=1)), ())
    self.assertEqual(tracker.observe(state(), self.media((False, False, 4_800_000_000), epoch=1)),
                     (Gesture(Button.MODE, Press.SHORT),))

  def test_media_simultaneous_or_direct_swap_requires_neutral(self):
    tracker = ButtonTracker()
    tracker.observe(state(), self.media((False, False, 1_000_000_000)))
    tracker.observe(state(), self.media((True, False, 1_200_000_000)))
    self.assertEqual(tracker.observe(state(), self.media((False, True, 1_400_000_000))), ())
    self.assertEqual(tracker.observe(state(), self.media((True, True, 1_600_000_000))), ())
    self.assertEqual(tracker.observe(state(), self.media((False, True, 1_800_000_000))), ())
    self.assertEqual(tracker.observe(state(), self.media((False, False, 2_000_000_000))), ())
    self.assertEqual(tracker.observe(state(), self.media((False, True, 2_200_000_000))), ())
    self.assertEqual(tracker.observe(state(), self.media((False, False, 2_400_000_000))),
                     (Gesture(Button.CUSTOM, Press.SHORT),))
    # An ambiguous later sample discards an earlier release in the same CAN batch.
    self.assertEqual(tracker.observe(state(), self.media((True, False, 2_600_000_000),
                                                      (False, False, 2_700_000_000),
                                                      (True, True, 2_800_000_000))), ())

  def test_claim_is_limited_to_same_drive_and_saved_settings(self):
    tracker = ButtonTracker()
    tracker.observe(state())
    tracker.observe(state((ButtonType.gapAdjustCruise, True)))
    for _ in range(49):
      tracker.observe(state())
    tracker.claim(Gesture(Button.DISTANCE, Press.LONG), 100, 'a' * 64)
    tracker.keep_claim(100, 'b' * 64)
    tracker.observe(state((ButtonType.gapAdjustCruise, False)))
    self.assertFalse(tracker.suppress_distance_release)

    tracker.observe(state((ButtonType.gapAdjustCruise, True)))
    for _ in range(49):
      tracker.observe(state())
    tracker.claim(Gesture(Button.DISTANCE, Press.LONG), 100, 'a' * 64)
    tracker.keep_claim(101, 'a' * 64)
    tracker.observe(state((ButtonType.gapAdjustCruise, False)))
    self.assertFalse(tracker.suppress_distance_release)

    tracker.observe(state((ButtonType.gapAdjustCruise, True)))
    for _ in range(49):
      tracker.observe(state())
    tracker.claim(Gesture(Button.DISTANCE, Press.LONG), 100, 'a' * 64)
    tracker.observe(state((ButtonType.gapAdjustCruise, False)))
    self.assertTrue(tracker.suppress_distance_release)

  def test_lkas_press_and_distance_duration_edges(self):
    tracker = ButtonTracker()
    self.assertEqual(tracker.observe(state((ButtonType.lkas, True))), ())  # held at startup
    self.assertEqual(tracker.observe(state((ButtonType.lkas, False))), ())
    self.assertEqual(tracker.observe(state((ButtonType.lkas, True))), (Gesture(Button.LKAS, Press.SHORT),))
    self.assertEqual(tracker.observe(state((ButtonType.gapAdjustCruise, True))), ())
    self.assertEqual(tracker.observe(state()), ())
    self.assertEqual(tracker.observe(state((ButtonType.gapAdjustCruise, False))),
                     (Gesture(Button.DISTANCE, Press.SHORT),))
    self.assertEqual(tracker.observe(state((ButtonType.gapAdjustCruise, True))), ())
    emitted = []
    for _ in range(249):
      emitted.extend(tracker.observe(state()))
    self.assertEqual(emitted, [Gesture(Button.DISTANCE, Press.LONG), Gesture(Button.DISTANCE, Press.VERY_LONG)])
    self.assertEqual(tracker.observe(state((ButtonType.gapAdjustCruise, False))), ())

  def test_invalid_can_resets_held_state_and_requires_neutral(self):
    tracker = ButtonTracker()
    tracker.observe(state())
    tracker.observe(state((ButtonType.gapAdjustCruise, True)))
    self.assertEqual(tracker.observe(state(valid=False)), ())
    self.assertEqual(tracker.observe(state((ButtonType.gapAdjustCruise, False))), ())
    self.assertEqual(tracker.observe(state((ButtonType.lkas, True))), (Gesture(Button.LKAS, Press.SHORT),))


class ManualSessionTests(unittest.TestCase):
  def test_initial_none_requires_explicit_nonpersistent_drive(self):
    owner = ManualSession()
    self.assertIsNone(owner.start(ModeChoice.CEM, 100, 101, persist_manual=True))
    restored = owner.start(ModeChoice.CEM, 100, 101, persist_manual=True, persisted_code=2)
    self.assertEqual((restored.intent, owner.code), (ManualIntent.FORCE_EXPERIMENTAL, 2))
    self.assertIsNone(owner.start(ModeChoice.CCM, 100, 101, persist_manual=True, persisted_code=True))
    self.assertIsNone(owner.start(ModeChoice.STOCK, 100, 101, persist_manual=False))
    initial = owner.start(ModeChoice.CEM, 100, 101, persist_manual=False)
    self.assertEqual((initial.intent, initial.drive_id, initial.observed_mono_ns), (ManualIntent.NONE, 100, 101))

  def test_frozen_ce_and_cc_cycle_with_replay_rejection(self):
    for choice, first_code, second_code in ((ModeChoice.CEM, 1, 2), (ModeChoice.CCM, 2, 1)):
      with self.subTest(choice=choice):
        owner = ManualSession()
        owner.start(choice, 100, 101, persist_manual=False)
        first_state = owner.apply(sequence=1, drive_id=100, observed_ns=102,
                                  effective_experimental=True, assigned=True)
        self.assertEqual(first_state.intent, ManualIntent.FORCE_CHILL)
        self.assertEqual(owner.code, first_code)
        self.assertIsNone(owner.apply(sequence=1, drive_id=100, observed_ns=103,
                                      effective_experimental=False, assigned=True))
        self.assertIsNone(owner.apply(sequence=2, drive_id=101, observed_ns=104,
                                      effective_experimental=False, assigned=True))
        automatic = owner.apply(sequence=2, drive_id=100, observed_ns=104,
                                effective_experimental=False, assigned=True)
        self.assertEqual(automatic.intent, ManualIntent.NONE)
        second_state = owner.apply(sequence=3, drive_id=100, observed_ns=105,
                                   effective_experimental=False, assigned=True)
        self.assertEqual(second_state.intent, ManualIntent.FORCE_EXPERIMENTAL)
        self.assertEqual(owner.code, second_code)
        self.assertIsNone(owner.apply(sequence=4, drive_id=100, observed_ns=106,
                                      effective_experimental=True, assigned=False))


if __name__ == '__main__':
  unittest.main()
