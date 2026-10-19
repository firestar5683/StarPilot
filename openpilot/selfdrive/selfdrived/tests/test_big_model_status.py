"""A native chestnut's loss soft-disables; a Jetlink hand-back keeps the small model driving."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from openpilot.cereal import messaging
from jetlink.openpilot.hooks import Hooks
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.selfdrived.events import Events, ET, EventName
from openpilot.selfdrive.selfdrived.helpers import jetlink_in_control, update_jetlink_swaps
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
from openpilot.starpilot.aol.runtime import AxisDecision
from openpilot.starpilot.models import jetlink_adapter
from openpilot.starpilot.models.tests.jetlink_fixture import ARMED_PAUSED, AXES_IDLE, rule


class Sources:
  def __init__(self):
    self.data = {name: getattr(messaging.new_message(name), name) for name in ('modelV2', 'deviceState', 'carControl')}
    self.seen = dict.fromkeys(self.data, True)
    self.alive = dict.fromkeys(self.data, True)
    self.valid = dict.fromkeys(self.data, True)

  def __getitem__(self, key):
    return self.data[key]


def fixture(chestnut=None):
  drive = SelfdriveD.__new__(SelfdriveD)
  vars(drive)['params'] = SimpleNamespace(get=lambda key: chestnut)
  vars(drive)['sm'] = Sources()
  drive.enabled = True
  drive.big_model_active = drive.big_model_chestnut = drive.big_model_failed = False
  drive.events = Events()
  return drive


class TestBigModelStatus(unittest.TestCase):
  def test_failure_edge_restarts_settling_once_until_recovery(self):
    drive = fixture(True)
    drive.sm['deviceState'].chestnutPresent = True
    drive.big_model_ready_t = -1.0
    drive.sm['modelV2'].big = True
    with patch('openpilot.selfdrive.selfdrived.helpers.time.monotonic', side_effect=[50.0, 70.0]) as clock:
      self.assertFalse(drive.update_big_model_status())
      self.assertEqual(drive.big_model_ready_t, -1.0)
      clock.assert_not_called()
      drive.sm['modelV2'].big = False
      self.assertTrue(drive.update_big_model_status())
      self.assertEqual(drive.big_model_ready_t, 50.0)
      self.assertIn(EventName.bigModelFailed, drive.events.names)
      self.assertTrue(drive.update_big_model_status())
      self.assertEqual(drive.big_model_ready_t, 50.0)
      clock.assert_called_once_with()
      drive.sm['modelV2'].big = True
      self.assertFalse(drive.update_big_model_status())
      drive.sm['modelV2'].big = False
      self.assertTrue(drive.update_big_model_status())
      self.assertEqual(drive.big_model_ready_t, 70.0)
      self.assertEqual(clock.call_count, 2)

  def test_unattributed_big_model_demotion_retains_native_failure(self):
    drive = fixture()
    drive.sm['modelV2'].big = True
    self.assertFalse(drive.update_big_model_status())
    self.assertTrue(drive.big_model_active)
    self.assertFalse(drive.big_model_chestnut)
    drive.sm['modelV2'].big = False
    self.assertTrue(drive.update_big_model_status())
    self.assertIn(EventName.bigModelFailed, drive.events.names)
    self.assertTrue(drive.events.contains(ET.SOFT_DISABLE))

  def test_native_chestnut_loss_still_soft_disables(self):
    drive = fixture(True)
    drive.sm['deviceState'].chestnutPresent = True
    drive.sm['modelV2'].big = True
    self.assertFalse(drive.update_big_model_status())
    self.assertTrue(drive.big_model_chestnut)
    drive.sm['modelV2'].big = False
    self.assertTrue(drive.update_big_model_status())
    self.assertIn(EventName.bigModelFailed, drive.events.names)
    self.assertTrue(drive.events.contains(ET.SOFT_DISABLE))
    self.assertTrue(drive.events.contains(ET.PERMANENT))

  def test_remote_execution_does_not_inherit_failed_chestnut_startup_marker(self):
    drive = fixture(False)
    drive.sm['modelV2'].big = True
    self.assertFalse(drive.update_big_model_status())
    self.assertFalse(drive.big_model_chestnut)
    drive.sm['modelV2'].big = False
    self.assertTrue(drive.update_big_model_status())
    self.assertTrue(drive.events.contains(ET.SOFT_DISABLE))

  def test_stale_or_invalid_remote_output_cannot_clear_failure(self):
    for field in ('alive', 'valid'):
      with self.subTest(field=field):
        drive = fixture()
        drive.sm['modelV2'].big = True
        self.assertFalse(drive.update_big_model_status())
        getattr(drive.sm, field)['modelV2'] = False
        self.assertTrue(drive.update_big_model_status())
        self.assertIn(EventName.bigModelFailed, drive.events.names)

  def test_local_small_and_unseen_remote_never_report_execution(self):
    drive = fixture()
    self.assertFalse(drive.update_big_model_status())
    self.assertFalse(drive.big_model_active)
    drive.sm['modelV2'].big = True
    drive.sm.seen['modelV2'] = False
    self.assertFalse(drive.update_big_model_status())
    self.assertFalse(drive.big_model_active)
    self.assertNotIn(EventName.bigModelFailed, drive.events.names)

  def test_actual_aol_lateral_execution_latches_until_all_axes_disengage(self):
    for axis in ('latActive', 'longActive'):
      with self.subTest(axis=axis):
        drive = fixture()
        drive.enabled = False
        setattr(drive.sm['carControl'], axis, True)
        drive.sm['modelV2'].big = True
        self.assertFalse(drive.update_big_model_status())
        self.assertTrue(drive.big_model_active)
        drive.sm['modelV2'].big = False
        self.assertTrue(drive.update_big_model_status())
        self.assertTrue(drive.events.contains(ET.SOFT_DISABLE))
        self.assertTrue(drive.big_model_active)
        setattr(drive.sm['carControl'], axis, False)
        drive.update_big_model_status()
        self.assertFalse(drive.big_model_active)
        self.assertFalse(drive.update_big_model_status())

  def test_chestnut_startup_invalid_frame_does_not_report_run_failure(self):
    drive = fixture(True)
    drive.sm['deviceState'].chestnutPresent = True
    drive.sm['modelV2'].big = True
    drive.sm.valid['modelV2'] = False
    self.assertFalse(drive.update_big_model_status())
    self.assertFalse(drive.big_model_active)
    self.assertNotIn(EventName.bigModelFailed, drive.events.names)
    drive.sm.valid['modelV2'] = True
    self.assertFalse(drive.update_big_model_status())
    self.assertTrue(drive.big_model_active)
    drive.sm.valid['modelV2'] = False
    self.assertTrue(drive.update_big_model_status())
    self.assertIn(EventName.bigModelFailed, drive.events.names)

  def test_fresh_chestnut_execution_overrides_cached_negative_load_marker(self):
    drive = fixture(False)
    drive.sm['deviceState'].chestnutPresent = True
    drive.sm['modelV2'].big = True
    self.assertFalse(drive.update_big_model_status())
    self.assertTrue(drive.big_model_chestnut)
    drive.sm['modelV2'].big = False
    self.assertTrue(drive.update_big_model_status())
    self.assertIn(EventName.bigModelFailed, drive.events.names)

  def test_loaded_chestnut_with_initial_valid_small_output_is_a_failure(self):
    drive = fixture(True)
    drive.sm['deviceState'].chestnutPresent = True
    drive.sm['modelV2'].big = False
    self.assertTrue(drive.update_big_model_status())
    self.assertFalse(drive.big_model_active)
    self.assertIn(EventName.bigModelFailed, drive.events.names)

  def test_chestnut_failure_and_physical_loss_are_preserved(self):
    drive = fixture(False)
    drive.sm['deviceState'].chestnutPresent = True
    self.assertTrue(drive.update_big_model_status())
    self.assertIn(EventName.bigModelFailed, drive.events.names)
    drive = fixture(True)
    drive.sm['modelV2'].big = True
    drive.sm['deviceState'].chestnutPresent = True
    self.assertFalse(drive.update_big_model_status())
    drive.sm['deviceState'].chestnutPresent = False
    self.assertTrue(drive.update_big_model_status())
    self.assertIn(EventName.bigModelFailed, drive.events.names)


class TestStatusParamThrottle(unittest.TestCase):
  def test_status_params_are_read_once_per_ten_frames(self):
    from openpilot.selfdrive.selfdrived.helpers import STATUS_PARAM_FRAMES, throttled_param
    reads = []
    owner = SimpleNamespace(sm=SimpleNamespace(frame=0))
    def read(key):
      reads.append(key)
      return len(reads)
    for frame in range(3 * STATUS_PARAM_FRAMES):
      owner.sm.frame = frame
      throttled_param(owner, "ChestnutLoading", read)
    self.assertEqual(len(reads), 3)
    owner.sm.frame = 3 * STATUS_PARAM_FRAMES
    self.assertEqual(throttled_param(owner, "ChestnutLoading", read), 4)   # a fresh read past the window

  def test_without_a_frame_counter_every_call_reads(self):
    from openpilot.selfdrive.selfdrived.helpers import throttled_param
    reads = []
    owner = SimpleNamespace(sm=SimpleNamespace())
    for _ in range(3):
      throttled_param(owner, "ChestnutActive", lambda key: reads.append(key))
    self.assertEqual(len(reads), 3)


DISARMED = SimpleNamespace(allowedLatch=False, lateralArmed=False)


def jetlink_drive(chestnut=None, intent=None, axes=None):
  """A drive with Jetlink's swap tracker, past AOL's grace, idle unless given AOL's intent (heard and alive) and
  axis decision or engaged by the test."""
  drive = fixture(chestnut)
  drive.enabled = drive.active = False
  drive.big_model_ready_t = 0.
  drive.jetlink_settling = drive.jetlink_link_lost = False
  drive.jetlink_hooks = Hooks(jetlink_adapter.API, jetlink_adapter.adapter)
  drive.jetlink_swaps = drive.jetlink_hooks.swap_events(DT_CTRL)
  drive.aol_replay = drive.axis_transport_required = True
  drive.aol_axis_decision = axes or AxisDecision()
  drive.sm.frame = int(jetlink_adapter.AOL_GRACE_S / DT_CTRL)
  drive.sm.data['aolIntentWire'] = intent
  drive.sm.seen['aolIntentWire'] = drive.sm.alive['aolIntentWire'] = intent is not None
  return drive


def no_record(drive):
  """modeld's runtime record unreadable or stale: the tracker's own read of it finds none."""
  drive.jetlink_hooks.runtime = lambda: None


class TestJetlinkSwaps(unittest.TestCase):
  def swaps(self, drive, ticks, state, big):
    # state None: the tracker reads modeld's runtime record itself
    drive.sm['modelV2'].big = big
    if state is not None:
      drive.jetlink_hooks.runtime = lambda: SimpleNamespace(state=state, active=big)
    return [update_jetlink_swaps(drive, jetlink_in_control(drive)) for _ in range(ticks)]

  def test_swap_in_refuses_engaging_then_settles(self):
    drive = jetlink_drive()
    self.swaps(drive, 10, 'ready', False)
    with patch('openpilot.selfdrive.selfdrived.helpers.time.monotonic', return_value=42.):
      flags = self.swaps(drive, 1, 'running', True)
    self.assertIn(EventName.bigModelLoading, drive.events.names)
    self.assertEqual(drive.big_model_ready_t, 0.)
    flags += self.swaps(drive, 149, 'running', True)
    self.assertTrue(flags[0].no_entry and not flags[-1].no_entry)
    self.assertEqual(drive.big_model_ready_t, 0.)  # no native grace restart
    self.assertFalse(drive.jetlink_link_lost)

  def test_hand_back_during_an_aol_pause_warns_and_never_disables(self):
    # AOL armed but paused: its axes are idle and only its intent says so, as the swap itself reads it
    drive = jetlink_drive(intent=b"intent")
    with patch("openpilot.starpilot.aol.wire.decode_intent", return_value=ARMED_PAUSED):
      self.swaps(drive, 200, 'running', True)
      self.assertFalse(drive.update_big_model_status())
      flags = self.swaps(drive, 600, 'retrying', False)
    self.assertTrue(flags[0].link_lost and flags[0].settling)
    self.assertTrue(drive.jetlink_link_lost is False and flags[-1].link_lost is False)
    self.assertFalse(drive.update_big_model_status())
    self.assertFalse(drive.events.contains(ET.SOFT_DISABLE))

  def test_hand_back_with_nothing_in_control_is_no_warning(self):
    drive = jetlink_drive()
    self.swaps(drive, 200, 'running', True)
    flags = self.swaps(drive, 10, 'retrying', False)
    self.assertFalse(any(f.link_lost for f in flags))
    self.assertFalse(drive.jetlink_link_lost)

  def test_a_record_gap_is_not_a_switch(self):
    # the big model still drives while modeld's record failed or went stale
    drive = jetlink_drive()
    drive.enabled = drive.active = True
    self.swaps(drive, 200, 'running', True)
    no_record(drive)
    flags = self.swaps(drive, 50, None, True) + self.swaps(drive, 50, 'running', True)
    self.assertFalse(any(f.no_entry or f.link_lost or f.settling for f in flags))

  def test_a_native_chestnut_or_no_jetlink_is_no_swap(self):
    drive = jetlink_drive(True)
    drive.enabled = drive.active = True
    no_record(drive)
    flags = self.swaps(drive, 10, None, True) + self.swaps(drive, 10, None, False)
    self.assertFalse(any(f.no_entry or f.link_lost or f.settling for f in flags))

  def test_selfdrived_and_the_adapter_agree_on_in_control(self):
    # one rule, aol_in_control(), over selfdrived's own state and over the adapter's reads of the same messages
    lateral = SimpleNamespace(**{**vars(AXES_IDLE), "desiredLateral": True})
    cases = [  # intent heard, alive, decoded, axes as published, the answer
      (False, False, DISARMED, AXES_IDLE, False),
      (False, False, DISARMED, lateral, True),
      (True, False, DISARMED, AXES_IDLE, True),
      (True, True, None, AXES_IDLE, True),
      (True, True, ARMED_PAUSED, AXES_IDLE, True),
      (True, True, SimpleNamespace(allowedLatch=True, lateralArmed=False), AXES_IDLE, True),
      (True, True, DISARMED, AXES_IDLE, False),
      (True, True, DISARMED, lateral, True),
      (True, True, DISARMED, SimpleNamespace(**{**vars(AXES_IDLE), "longitudinalActive": True}), True),
    ]
    for heard, alive, decoded, published, expected in cases:
      with self.subTest(heard=heard, alive=alive, decoded=decoded, axes=vars(published)):
        drive = jetlink_drive(intent=b"intent" if heard else None,
                              axes=AxisDecision(published.desiredLateral, published.desiredLongitudinal,
                                                published.lateralActive, published.longitudinalActive))
        drive.sm.alive['aolIntentWire'] = alive
        op = rule(aol={"aolIntentWire": b"intent", "aolAxisState": published} if heard else {"aolAxisState": published})
        op._aol.alive["aolIntentWire"] = alive
        with patch("openpilot.starpilot.aol.wire.decode_intent", return_value=decoded):
          self.assertEqual((jetlink_in_control(drive), op.in_control()), (expected, expected))
    drive, op = jetlink_drive(), rule(core={"selfdriveState": SimpleNamespace(enabled=True, active=True)})
    drive.enabled = drive.active = True
    self.assertEqual((jetlink_in_control(drive), op.in_control()), (True, True))


class TestJetlinkAdapterValidation(unittest.TestCase):
  def test_runtime_poll_is_bounded_and_not_duplicated_by_tracker(self):
    drive = jetlink_drive()
    runtime = SimpleNamespace(state='running', active=True)
    with patch.object(drive.jetlink_hooks, 'runtime', return_value=runtime) as poll:
      drive.sm['modelV2'].big = True
      for _ in range(200):
        update_jetlink_swaps(drive, False)
      self.assertEqual(poll.call_count, 10)  # five polls per 100 control ticks
    self.assertEqual(drive.big_model_ready_t, 0.)

  def test_invalid_model_values_cannot_create_swaps_or_handbacks(self):
    for field in ('seen', 'alive', 'valid'):
      for previous_big in (False, True):
        with self.subTest(field=field, previous_big=previous_big):
          drive = jetlink_drive()
          drive.enabled = drive.active = True
          drive.jetlink_hooks.runtime = lambda: SimpleNamespace(state='running', active=True)
          drive.sm['modelV2'].big = previous_big
          for _ in range(200):
            update_jetlink_swaps(drive, True)
          getattr(drive.sm, field)['modelV2'] = False
          drive.sm['modelV2'].big = not previous_big
          for _ in range(100):
            flags = update_jetlink_swaps(drive, True)
            self.assertFalse(flags.no_entry or flags.link_lost or flags.settling)
          self.assertEqual(drive.big_model_ready_t, 0.)

  def test_runtime_gap_does_not_supply_demotion_provenance(self):
    drive = jetlink_drive()
    drive.enabled = drive.active = True
    drive.jetlink_hooks.runtime = lambda: SimpleNamespace(state='running', active=True)
    drive.sm['modelV2'].big = True
    update_jetlink_swaps(drive, True)
    self.assertFalse(drive.update_big_model_status())
    drive.jetlink_hooks.runtime = lambda: None
    drive._jetlink_runtime_ticks = 0
    drive.sm['modelV2'].big = False
    update_jetlink_swaps(drive, True)
    self.assertTrue(drive.update_big_model_status())
    self.assertIn(EventName.bigModelFailed, drive.events.names)

  def test_missing_or_incompatible_api_has_no_demotion_exemption(self):
    from jetlink.openpilot.hooks import Off
    for hooks in (jetlink_adapter._NoJetlink('missing'), Off('incompatible API')):
      with self.subTest(hooks=type(hooks).__name__):
        drive = fixture()
        drive.jetlink_hooks = hooks
        drive.jetlink_swaps = hooks.swap_events(DT_CTRL)
        drive.sm['modelV2'].big = True
        self.assertFalse(drive.update_big_model_status())
        drive.sm['modelV2'].big = False
        self.assertTrue(drive.update_big_model_status())
