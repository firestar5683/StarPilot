from types import SimpleNamespace as NS
from unittest.mock import Mock
import pytest
from openpilot.starpilot.drive_state.owner import DriveStateOwner, Mode, Rejected
from openpilot.starpilot.drive_state.control import DriveStateControl
from openpilot.starpilot.drive_state.tests.test_owner import Params, BOOT


@pytest.fixture
def fixture(tmp_path):
  params = Params()
  owner = DriveStateOwner(params, tmp_path / 'lock', alive=lambda _: True)
  owner.initialize(pid=1, birth=2, boot=BOOT)
  physical = NS(allowed=Mock(return_value=True))
  now = [0.0]
  control = DriveStateControl(owner, physical, effective=lambda: False, clock=lambda: now[0])
  return NS(owner=owner, control=control, physical=physical, now=now)


def test_requested_state_does_not_claim_effective_started_and_status_reads_bounded(fixture):
  f = fixture
  f.owner.snapshot = Mock(wraps=f.owner.snapshot)
  status = f.control.snapshot()
  f.control.cycle(status, lambda: True)
  status = f.control.snapshot()
  assert status['mode'] == 'offroad' and status['effective'] == 'offroad'
  f.control.cycle(status, lambda: True)
  status = f.control.snapshot()
  assert status['mode'] == 'onroad' and status['effective'] == 'offroad'
  calls = f.owner.snapshot.call_count
  for _ in range(100):
    f.control.snapshot()
  assert f.owner.snapshot.call_count == calls
  f.now[0] += 0.5
  f.control.snapshot()
  assert f.owner.snapshot.call_count == calls + 1


def test_small_cycle_and_expired_physical_source_explicit_auto_recovery(fixture):
  f = fixture
  for mode in ('offroad', 'onroad', 'auto'):
    status = f.control.snapshot()
    assert f.control.next_mode(status).value == mode
    f.control.cycle(status, lambda: True)
  f.control.cycle(f.control.snapshot(), lambda: True)
  f.physical.allowed.return_value = False
  f.now[0] += 0.5
  status = f.control.snapshot()
  assert status['mode'] == 'offroad' and f.control.next_mode(status) == Mode.AUTO
  f.control.cycle(status, lambda: True)
  assert f.control.snapshot()['mode'] == 'auto'


def test_displayed_admission_is_not_reused_for_action_and_auth_revocation(fixture):
  f = fixture
  status = f.control.snapshot()
  f.physical.allowed.return_value = False
  with pytest.raises(Rejected):
    f.control.change('onroad', status['revision'], lambda: True)
  assert f.owner.snapshot().mode == Mode.AUTO
  f.physical.allowed.return_value = True
  with pytest.raises(Rejected):
    f.control.cycle(status, lambda: False)


def test_actual_native_small_and_big_dispatch_same_owner(fixture):
  from openpilot.starpilot.ui.runtime_app import StarShellSession
  from openpilot.starpilot.ui.shell import ShellMode, ShellRequest
  from openpilot.starpilot.ui.presentation import Profile
  from openpilot.starpilot.ui.settings_state import Destination, DestinationAvailability, SettingsAction, SettingsActionKind
  from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsState, FeatureUiAction

  f = fixture
  native = object.__new__(StarShellSession)
  native.drive_state = f.control
  native.profile = Profile.COMPACT
  native._mode = ShellMode.SETTINGS
  native.selected = Destination.STAR
  native._snapshot_cache = None
  native._emit(
    ShellRequest(
      'settings',
      SettingsAction(
        SettingsActionKind.REQUEST_DESTINATION,
        DestinationAvailability(Destination.FORCE_DRIVE, True, request_value="offroad", request_revision=f.owner.snapshot().revision),
      ),
    )
  )
  assert f.owner.snapshot().mode == Mode.OFFROAD
  native.profile = Profile.LARGE
  native.selected = Destination.SYSTEM
  native.display_scroll = 0
  native.display_snapshot = lambda: FeatureSettingsState(rows=())
  native.power_snapshot = lambda: FeatureSettingsState(rows=())
  native.map_snapshot = lambda: NS(rows=())
  state = native.system_snapshot()
  row = state.rows[-1]
  native._display_ui(FeatureUiAction('change', row, 1))
  assert f.owner.snapshot().mode == Mode.ONROAD
  native._display_ui(FeatureUiAction('change', native.system_snapshot().rows[-1], 1))
  assert f.owner.snapshot().mode == Mode.AUTO


def test_actual_settings_gesture_tracks_pipeline_epoch_not_physical_parked_flag():
  from unittest.mock import patch
  from openpilot.starpilot.ui.runtime_app import StarShellSession
  from openpilot.starpilot.ui.settings_state import Destination

  native = object.__new__(StarShellSession)
  native.selected = Destination.STAR
  native.cancel = Mock()
  native.confirmed_offroad = lambda: False
  snapshot = NS(selected=Destination.STAR, device=NS(offroad=False))
  native._settings_touch = snapshot
  native._settings_pipeline = (False, 10)
  fake = NS(started=False, started_frame=10, is_offroad=lambda: True)
  with patch('openpilot.starpilot.ui.runtime_app.ui_state', fake):
    assert native._settings_gesture_snapshot() is snapshot
    # Even an Off->On->Off sequence changes the existing drive epoch.
    fake.started_frame = 20
    assert native._settings_gesture_snapshot() is None
    fake.started = True
    native._settings_pipeline = (True, 20)
    assert native._settings_gesture_snapshot() is snapshot
    # Ordinary onroad setting gesture remains valid; parked authority still revokes.
    snapshot.device.offroad = True
    assert native._settings_gesture_snapshot() is None


def test_small_rendered_action_revision_is_bound_not_reinterpreted(fixture):
  from openpilot.starpilot.ui.runtime_app import StarShellSession
  from openpilot.starpilot.ui.shell import ShellMode, ShellRequest
  from openpilot.starpilot.ui.presentation import Profile
  from openpilot.starpilot.ui.settings_state import Destination, DestinationAvailability, SettingsAction, SettingsActionKind

  f = fixture
  old = f.control.snapshot()
  action = SettingsAction(
    SettingsActionKind.REQUEST_DESTINATION, DestinationAvailability(Destination.FORCE_DRIVE, True, request_value='offroad', request_revision=old['revision'])
  )
  f.control.change('onroad', old['revision'], lambda: True)
  native = object.__new__(StarShellSession)
  native.drive_state = f.control
  native.profile = Profile.COMPACT
  native._mode = ShellMode.SETTINGS
  native.selected = Destination.STAR
  native._snapshot_cache = None
  native._emit(ShellRequest('settings', action))
  assert f.owner.snapshot().mode == Mode.ONROAD
  assert 'refresh' in native.notice


def test_actual_manager_process_predicate_stops_park_producers_and_auto_recovers(fixture):
  from openpilot.starpilot.drive_state.tests.test_evidence import Messages
  from openpilot.starpilot.drive_state.evidence import PhysicalSource
  from openpilot.system.manager.process_config import procs, only_onroad

  assert only_onroad(True, None, None)
  assert not only_onroad(False, None, None)
  processes = {process.name: process for process in procs}
  assert processes['card'].should_run is only_onroad
  assert processes['selfdrived'].should_run is only_onroad
  messages = Messages()
  now = [1_000_000_000]
  physical = PhysicalSource(messages, mono=lambda: now[0], boot=lambda: now[0] + 10_000_000_000)
  now[0] = 2_100_000_000
  messages.values['pandaStates'][0].ignitionLine = True
  control = DriveStateControl(fixture.owner, physical, effective=lambda: False, clock=lambda: now[0] / 1e9)
  control.cycle(control.snapshot(), lambda: True)
  now[0] += 500_000_000
  messages.logMonoTime['pandaStates'] = now[0] + 10_000_000_000
  messages.recv_time['pandaStates'] = now[0] / 1e9
  status = control.snapshot()
  assert not status['overrideAllowed'] and control.next_mode(status) == Mode.AUTO
  control.cycle(status, lambda: True)
  assert fixture.owner.snapshot().mode == Mode.AUTO


def test_concurrent_old_snapshot_cannot_repopulate_cache_after_acknowledged_change(fixture):
  import threading

  f = fixture
  read, release, committed = threading.Event(), threading.Event(), threading.Event()
  original_snapshot = f.owner.snapshot
  original_request = f.owner.request
  first = [True]

  def held_snapshot():
    state = original_snapshot()
    if first[0]:
      first[0] = False
      read.set()
      assert release.wait(2)
    return state

  def request(*args, **kwargs):
    state = original_request(*args, **kwargs)
    committed.set()
    return state

  revision = original_snapshot().revision
  f.owner.snapshot = held_snapshot
  f.owner.request = request
  results = []
  reader = threading.Thread(target=lambda: results.append(f.control.snapshot()))
  writer = threading.Thread(target=lambda: f.control.change('onroad', revision, lambda: True))
  reader.start()
  assert read.wait(2)
  writer.start()
  assert committed.wait(2)  # Owner writes do not join the snapshot/cache lock.
  release.set()
  reader.join(2)
  writer.join(2)
  assert not reader.is_alive() and not writer.is_alive()
  assert results[0]['mode'] == 'auto'
  assert f.control.snapshot()['mode'] == 'onroad'


def test_native_offroad_confirmation_preserves_revision_without_requiring_healthy_can(fixture):
  from unittest.mock import patch
  from openpilot.starpilot.ui.runtime_app import StarShellSession
  from openpilot.starpilot.ui.shell import ShellMode
  from openpilot.starpilot.ui.settings_state import Destination
  from openpilot.system.ui.widgets import DialogResult

  f = fixture
  native = object.__new__(StarShellSession)
  native.drive_state = f.control
  from openpilot.starpilot.ui.presentation import Profile
  native.profile = Profile.LARGE
  native._mode = ShellMode.SETTINGS
  native.selected = Destination.SYSTEM
  native._snapshot_cache = None
  fake = NS(started=True, started_frame=10)
  revision = f.owner.snapshot().revision
  with patch('openpilot.starpilot.ui.runtime_app.ui_state', fake), \
       patch('openpilot.starpilot.ui.runtime_app.gui_app.push_widget') as push:
    native._drive_change('offroad', revision)
    assert f.owner.snapshot().mode == Mode.AUTO
    dialog = push.call_args.args[0]
    dialog._callback(DialogResult.CANCEL)
    assert f.owner.snapshot().mode == Mode.AUTO
    fake.started_frame = 11
    dialog._callback(DialogResult.CONFIRM)
    assert f.owner.snapshot().mode == Mode.AUTO
    native._drive_change('offroad', revision)
    f.physical.allowed.return_value = False
    push.call_args.args[0]._callback(DialogResult.CONFIRM)
    assert f.owner.snapshot().mode == Mode.OFFROAD
