"""Drive-scoped stopped duration and native display-source regression checks."""

import unittest
from unittest.mock import patch

from opendbc.car.structs import car as car_schema

from openpilot.starpilot.ui.onroad_customization import STOPPED_TIMER_WIDGET, default_document
from openpilot.starpilot.ui.onroad_stopped_timer import (ENGAGED, EXPERIMENTAL, TRAFFIC, StoppedTimer,
                                                       duration_color, duration_text)
from openpilot.starpilot.ui.runtime_snapshot import RuntimeSnapshotAdapter
from openpilot.starpilot.ui.shell import ShellMode
from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW, ui_fake


SECOND = 1_000_000_000


class StoppedTimerTests(unittest.TestCase):
  def test_projection_timer_enablement_overrides_native_choice(self):
    for native_enabled, projection_enabled in ((False, True), (True, False)):
      with self.subTest(native_enabled=native_enabled, projection_enabled=projection_enabled):
        ui = ui_fake()
        car = ui.sm.messages['carState']
        car.canValid, car.canTimeout, car.standstill = True, False, True
        car.gearShifter = car_schema.CarState.GearShifter.drive
        adapter = RuntimeSnapshotAdapter(ui)
        document = default_document()
        document['layouts']['compact'][STOPPED_TIMER_WIDGET]['enabled'] = native_enabled
        with patch('openpilot.starpilot.ui.runtime_snapshot.read_customization', return_value=document):
          for second in (0, 61):
            now = NOW + second * SECOND
            for name in ('deviceState', 'pandaStates', 'carState'):
              ui.sm.logMonoTime[name] = now
            state = adapter.build(ShellMode.ONROAD, now_ns=now, stopped_timer_enabled=projection_enabled).onroad
        self.assertEqual(state.stopped_duration_s, 61 if projection_enabled else None)
        self.assertEqual(document['layouts']['compact'][STOPPED_TIMER_WIDGET]['enabled'], native_enabled)

  def test_first_drive_minute_then_elapsed_and_color_transitions(self):
    timer = StoppedTimer()
    def step(second):
      return timer.step(now_ns=second * SECOND, drive_key=(1, 1), car_fresh=True,
                        standstill=True, reverse=False, enabled=True)
    self.assertIsNone(step(1))
    self.assertIsNone(step(59))
    self.assertEqual(step(61), 60)
    self.assertEqual(duration_text(60), ("1 minute", "0 seconds"))
    self.assertEqual(duration_text(121), ("2 minutes", "1 second"))
    self.assertEqual(duration_color(0), ENGAGED)
    self.assertEqual(duration_color(60), ENGAGED)
    self.assertEqual(duration_color(150), EXPERIMENTAL)
    self.assertEqual(duration_color(300), TRAFFIC)

  def test_movement_reverse_source_loss_disabled_and_new_drive_reset(self):
    timer = StoppedTimer()
    def step(second, *, drive=(1, 1), fresh=True, standstill=True, reverse=False, enabled=True):
      return timer.step(now_ns=second * SECOND, drive_key=drive, car_fresh=fresh,
                        standstill=standstill, reverse=reverse, enabled=enabled)
    self.assertIsNone(step(1))
    self.assertEqual(step(62), 61)
    self.assertIsNone(step(63, standstill=False))
    self.assertIsNone(step(64))
    self.assertEqual(step(65), 1)
    self.assertIsNone(step(66, reverse=True))
    self.assertIsNone(step(67))
    self.assertEqual(step(68), 1)
    self.assertIsNone(step(69, fresh=False))
    self.assertIsNone(step(70))
    self.assertEqual(step(71), 1)
    self.assertIsNone(step(72, enabled=False))
    self.assertIsNone(step(73))
    self.assertEqual(step(74), 1)
    self.assertIsNone(step(75, drive=None))
    self.assertIsNone(step(76, drive=(2, 2)))
    self.assertIsNone(step(135, drive=(2, 2)))
    self.assertEqual(step(136, drive=(2, 2)), 60)
    self.assertEqual(step(137, drive=(2, 2)), 61)
    self.assertIsNone(step(10, drive=(2, 2)), "a regressed monotonic clock clears the interval")

  def test_runtime_requires_post_start_fresh_valid_car_and_clears_on_loss(self):
    ui = ui_fake()
    car = ui.sm.messages["carState"]
    car.canValid = True
    car.canTimeout = False
    car.standstill = True
    car.gearShifter = car_schema.CarState.GearShifter.drive
    adapter = RuntimeSnapshotAdapter(ui)
    timer_on = default_document()
    timer_on["layouts"]["compact"][STOPPED_TIMER_WIDGET]["enabled"] = True
    def refresh(now_ns, *, car_age_ns=0):
      for name in ("deviceState", "pandaStates", "carState"):
        ui.sm.logMonoTime[name] = now_ns - (car_age_ns if name == "carState" else 0)
      with patch("openpilot.starpilot.ui.runtime_snapshot.read_customization", return_value=timer_on):
        return adapter.build(ShellMode.ONROAD, now_ns=now_ns).onroad.stopped_duration_s
    self.assertIsNone(refresh(NOW))
    self.assertIsNone(refresh(NOW + 59 * SECOND))
    self.assertEqual(refresh(NOW + 61 * SECOND), 61)
    self.assertIsNone(refresh(NOW + 62 * SECOND, car_age_ns=201_000_000))
    self.assertIsNone(refresh(NOW + 63 * SECOND))
    self.assertEqual(refresh(NOW + 64 * SECOND), 1)
    car.gearShifter = car_schema.CarState.GearShifter.reverse
    self.assertIsNone(refresh(NOW + 65 * SECOND))
    car.gearShifter = car_schema.CarState.GearShifter.drive
    self.assertIsNone(refresh(NOW + 66 * SECOND))
    ui.started_frame = 4
    self.assertIsNone(refresh(NOW + 67 * SECOND), "old carState receive cannot seed the next drive")
    ui.sm.recv_frame["carState"] = 5
    self.assertIsNone(refresh(NOW + 68 * SECOND))
    self.assertIsNone(refresh(NOW + 126 * SECOND))
    self.assertEqual(refresh(NOW + 127 * SECOND), 59)
    self.assertEqual(refresh(NOW + 129 * SECOND), 61)


if __name__ == "__main__":
  unittest.main()


def test_replay_seek_during_standstill_does_not_invent_duration():
  from unittest.mock import Mock
  from openpilot.tools.replay.display_clock import ClockSample
  ui = ui_fake()
  ui.replay_clock = Mock()
  car = ui.sm.messages['carState']
  car.canValid, car.canTimeout, car.standstill = True, False, True
  car.gearShifter = car_schema.CarState.GearShifter.drive
  adapter = RuntimeSnapshotAdapter(ui)
  def step(second, epoch=1):
    now = NOW + second * SECOND
    ui.replay_sample = ui.sm.replay_sample = ClockSample(now, None, now, epoch=epoch, paused=True, valid=True)
    for name in ('deviceState', 'carState'):
      ui.sm.logMonoTime[name] = now
    return adapter.build(ShellMode.ONROAD, stopped_timer_enabled=True).onroad.stopped_duration_s
  assert step(0) is None
  assert step(61) is None
  car.standstill = False
  assert step(62) is None
  car.standstill = True
  assert step(63) is None
  assert step(65) == 2
  assert step(100, epoch=2) is None
  assert step(161, epoch=2) is None
