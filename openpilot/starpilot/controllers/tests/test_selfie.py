import threading
from types import SimpleNamespace

from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.starpilot.controllers.selfie import SelfieCapture, authority
from openpilot.starpilot.controllers.wheel_actions import cp_fingerprint
from openpilot.starpilot.galaxy.camera_snapshot import SnapshotUnavailable
from openpilot.starpilot.galaxy.sentry_events import SentryEvents
from openpilot.starpilot.sentry_mode.storage import EventStore


class Camera:
  def __init__(self):
    self.entered = threading.Event()
    self.release = threading.Event()
    self.done = threading.Event()

  def capture(self, name, *, permitted):
    assert name == 'cabin'
    self.entered.set()
    assert self.release.wait(2)
    if not permitted():
      raise SnapshotUnavailable('Authority lost')
    return b'\xff\xd8fixture\xff\xd9'


class Store(EventStore):
  def __init__(self, root):
    super().__init__(root)
    self.done = threading.Event()

  def record(self, *args, **kwargs):
    try:
      return super().record(*args, **kwargs)
    finally:
      self.done.set()


def test_async_capture_records_real_index_and_galaxy_image(tmp_path):
  camera, store = Camera(), Store(tmp_path / 'events')
  owner = SelfieCapture(camera=camera, store=store, clock=lambda: 100)
  assert owner.submit(lambda: True)
  assert camera.entered.wait(2)
  assert owner.busy
  assert not owner.submit(lambda: True)
  camera.release.set()
  assert store.done.wait(2)
  owner.worker.join(2)
  assert not owner.busy
  events = SentryEvents(store).snapshot()['events']
  assert len(events) == 1
  assert events[0]['kind'] == 'selfie'
  assert events[0]['images'] == ['cabin']
  assert SentryEvents(store).image(events[0]['eventId'], 'cabin') == b'\xff\xd8fixture\xff\xd9'


def test_denied_or_revoked_capture_never_publishes_event(tmp_path):
  camera, store = Camera(), Store(tmp_path / 'events')
  owner = SelfieCapture(camera=camera, store=store)
  allowed = [False]
  assert not owner.submit(lambda: allowed[0])
  assert not camera.entered.is_set()
  allowed[0] = True
  assert owner.submit(lambda: allowed[0])
  assert camera.entered.wait(2)
  allowed[0] = False
  camera.release.set()
  owner.worker.join(2)
  assert not owner.busy
  assert SentryEvents(store).snapshot()['events'] == []


def test_actual_factory_identity_and_fresh_drive_sources_admit_only_same_session():
  cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  drive, now = 1_000_000_000, 2_000_000_000
  class Messages:
    def __getitem__(self, name):
      return self.data[name]
  sm = Messages()
  sm.data = {'deviceState': SimpleNamespace(started=True, startedMonoTime=drive),
             'carState': SimpleNamespace(canValid=True, canTimeout=False)}
  sm.logMonoTime = dict.fromkeys(sm.data, now - 10_000_000)
  sm.recv_time = dict.fromkeys(sm.data, (now - 10_000_000) / 1e9)
  sm.seen = sm.alive = sm.valid = dict.fromkeys(sm.data, True)
  args = {'drive_id': drive, 'fingerprint': cp_fingerprint(cp), 'now_ns': now}
  assert authority(sm, cp, **args)
  sm.data['deviceState'].startedMonoTime = drive + 1
  assert not authority(sm, cp, **args)
  sm.data['deviceState'].startedMonoTime = drive
  sm.data['carState'].canValid = False
  assert not authority(sm, cp, **args)
  sm.data['carState'].canValid = True
  assert not authority(sm, cp, **{**args, 'now_ns': now + 300_000_000})
  cp.dashcamOnly = True
  assert not authority(sm, cp, **args)


def test_selfie_is_local_even_when_motion_notifications_are_configured(tmp_path):
  from openpilot.starpilot.sentry_mode.notifications import NotificationOwner
  store = EventStore(tmp_path / 'events')
  calls, clock = [], [1.]
  owner = NotificationOwner(tmp_path / 'notifications', store,
                            clock=lambda: clock[0], transport=lambda *args: calls.append(args) or 200)
  try:
    owner.action({'action': 'configure', 'channel': 'ntfy', 'enabled': True,
                  'url': 'https://example.test/events', 'token': ''})
    store.record('selfie', 100, permitted=lambda: True, images={'cabin': b'\xff\xd8fixture\xff\xd9'})
    clock[0] = store.snapshot()["events"][0]["wallTimeNs"] / 1e9 + 1
    owner.tick()
    assert not calls
    assert owner.state['jobs'] == {}
  finally:
    owner.close()


def test_no_fresh_camera_frame_releases_worker_without_record(tmp_path):
  class MissingCamera:
    def capture(self, name, *, permitted):
      raise SnapshotUnavailable('No fresh camera frame')
  store = EventStore(tmp_path / 'events')
  owner = SelfieCapture(camera=MissingCamera(), store=store)
  assert owner.submit(lambda: True)
  owner.worker.join(2)
  assert not owner.busy and owner.last_result is None
  assert SentryEvents(store).snapshot()['events'] == []
