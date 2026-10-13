import pytest
import fcntl

from openpilot.starpilot.replay.frames import HEADER_SIZE, SEQ, ReplayFramePublisher, ReplayFrameReader

SESSION = 'a' * 32


def test_coherent_epoch_and_viewer_close_preserves_owned_file(tmp_path):
  path = tmp_path / 'frame'
  publisher = ReplayFramePublisher(path, SESSION, 'compact', 4, 2)
  reader = ReplayFrameReader(path, SESSION, 'compact')
  try:
    publisher.publish(b'\x11' * 32, epoch=1, position=15.25, captured_ns=123)
    frame = reader.latest()
    assert (frame.data, frame.epoch, frame.position, frame.frame_id) == (b'\x11' * 32, 1, 15.25, 1)
    assert reader.latest() is None
    publisher.publish(b'\x22' * 32, epoch=2, position=2, captured_ns=456)
    assert reader.latest().epoch == 2
    reader.close()
    assert path.exists()
  finally:
    reader.close()
    publisher.close()
  assert not path.exists()


def test_reader_refuses_other_session_and_torn_frame(tmp_path):
  publisher = ReplayFramePublisher(tmp_path / 'frame', SESSION, 'compact', 4, 2)
  reader = ReplayFrameReader(publisher.path, SESSION)
  other = ReplayFrameReader(publisher.path, 'b' * 32)
  try:
    publisher.publish(b'x' * 32, epoch=1, position=0, captured_ns=1)
    assert other.latest() is None
    SEQ.pack_into(publisher.mm, 8, 3)
    assert reader.latest() is None
  finally:
    reader.close()
    other.close()
    publisher.close()


def test_reader_never_follows_symlink_or_accepts_permissive_file(tmp_path):
  path = tmp_path / 'frame'
  path.write_bytes(b'\0' * (HEADER_SIZE + 32))
  path.chmod(0o644)
  with pytest.raises(ValueError, match='Unsafe'):
    ReplayFrameReader(path, SESSION)
  path.chmod(0o600)
  link = tmp_path / 'link'
  link.symlink_to(path)
  with pytest.raises(OSError):
    ReplayFrameReader(link, SESSION)
  assert path.exists()


def test_publisher_rejects_unbounded_or_invalid_clock(tmp_path):
  with pytest.raises(ValueError):
    ReplayFramePublisher(tmp_path / 'frame', SESSION, 'large', 2160, 1080)
  publisher = ReplayFramePublisher(tmp_path / 'frame', SESSION, 'compact', 4, 2)
  try:
    for epoch, position in ((0, 0), (1, float('nan')), (1, -1)):
      with pytest.raises(ValueError):
        publisher.publish(b'x' * 32, epoch=epoch, position=position, captured_ns=1)
  finally:
    publisher.close()


def test_kernel_lock_prevents_copying_pixels_while_writer_is_active(tmp_path):
  publisher = ReplayFramePublisher(tmp_path / 'frame', SESSION, 'compact', 4, 2)
  reader = ReplayFrameReader(publisher.path, SESSION)
  try:
    publisher.publish(b'a' * 32, epoch=1, position=0, captured_ns=1)
    fcntl.flock(publisher.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert reader.latest() is None
    fcntl.flock(publisher.fd, fcntl.LOCK_UN)
    assert reader.latest().data == b'a' * 32
    fcntl.flock(reader.fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    with pytest.raises(RuntimeError, match='consumer stalled'):
      publisher.publish(b'b' * 32, epoch=2, position=1, captured_ns=2)
    assert publisher.frame_id == 1
    fcntl.flock(reader.fd, fcntl.LOCK_UN)
    publisher.publish(b'b' * 32, epoch=2, position=1, captured_ns=2)
    assert reader.latest().data == b'b' * 32
  finally:
    reader.close()
    publisher.close()
