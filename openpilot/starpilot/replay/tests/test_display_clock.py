from pathlib import Path
import tempfile
import uuid

from openpilot.tools.replay.display_clock import DisplayClockReader, MAGIC, RECORD, VALID


def test_device_context_enables_owned_clock_and_opens_late_publisher(monkeypatch):
  monkeypatch.setattr('openpilot.tools.replay.display_clock.sys.platform', 'darwin')
  prefix = 'replay-' + uuid.uuid4().hex
  with tempfile.TemporaryDirectory(prefix='replay-clock-'):
    directory = Path('/tmp') / ('msgq_' + prefix)
    directory.mkdir(mode=0o700)
    path = directory / 'display-clock'
    env = {'SP_REPLAY_CONTEXT': '1', 'OPENPILOT_PREFIX': prefix, 'SP_REPLAY_CLOCK_PATH': str(path)}
    reader = DisplayClockReader(env)
    try:
      assert DisplayClockReader.enabled(env)
      assert not reader.sample(10_000_000_000).valid
      path.write_bytes(RECORD.pack(2, MAGIC, 1, VALID, 1, 100_000_000_000, 10_000_000_000, 1, 0, 10_000_000_000, 0))
      path.chmod(0o600)
      assert reader.sample(10_300_000_000).valid is False  # the heartbeat expired, even for a new mapping
      sample = reader.sample(10_000_000_000)
      assert sample.valid and sample.now_ns == 100_000_000_000
      reader.close()
      assert reader.sample(10_000_000_000).valid is False
    finally:
      reader.close()
      path.unlink(missing_ok=True)
      directory.rmdir()


def test_device_context_does_not_weaken_prefix_or_path():
  expected = '/dev/shm/msgq_replay-test/display-clock'
  good = {'SP_REPLAY_CONTEXT': '1', 'OPENPILOT_PREFIX': 'replay-test', 'SP_REPLAY_CLOCK_PATH': expected}
  assert DisplayClockReader.enabled(good)
  for change in ({'OPENPILOT_PREFIX': 'd'}, {'OPENPILOT_PREFIX': '../replay-test'},
                 {'SP_REPLAY_CLOCK_PATH': '/data/params/d'}, {'SP_REPLAY_CONTEXT': '0'}):
    assert not DisplayClockReader.enabled(good | change)
