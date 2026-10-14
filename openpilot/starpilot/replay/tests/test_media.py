import json
import os
import re
from pathlib import Path
import subprocess
import pytest

from openpilot.starpilot.replay.media import MediaMux, MediaStore, codec_string, media_descriptor


def store(tmp_path):
  session = tmp_path / ('a' * 32)
  session.mkdir(mode=0o700)
  return MediaStore(session, session.name, 1280, 640)


def test_publish_requires_initialization_without_creating_fragments(tmp_path):
  media = store(tmp_path)
  with pytest.raises(ValueError, match='initialized'):
    media.publish(b'frame', position=0., keyframe=True)
  assert media.sequence == 0 and not media.fragments
  assert not media.manifest.exists() and not list(media.root.iterdir())


def test_bounded_fragments_evict_whole_gop_and_keep_init(tmp_path):
  media = store(tmp_path)
  media.begin(1, 'avc1.42c01f', b'initialization')
  for index in range(60):
    media.publish(b'frame' + bytes([index]), position=index / 20, keyframe=index % 10 == 0)
  summary = media.summary()
  assert summary['firstSequence'] == 21
  assert summary['lastSequence'] == 60
  assert media.fragments[0]['keyframe']
  assert len(list(media.directory.iterdir())) == 41
  assert media_descriptor(media.manifest.parent, 1, 0)['available']
  assert media_descriptor(media.manifest.parent, 1, 1)['code'] == 'media_evicted'
  assert media_descriptor(media.manifest.parent, 1, 61)['code'] == 'media_pending'


def test_seek_retires_old_epoch_and_paths_are_fixed(tmp_path):
  media = store(tmp_path)
  media.begin(1, 'avc1.42c01f', b'init')
  media.publish(b'frame', position=50, keyframe=True)
  old = media.directory
  media.begin(2, 'avc1.42c01f', b'init2')
  media.publish(b'new', position=5, keyframe=True)
  assert not old.exists()
  assert media_descriptor(media.manifest.parent, 1, 1)['code'] == 'media_epoch_changed'
  descriptor = media_descriptor(media.manifest.parent, 2, 1)
  assert descriptor['firstPosition'] == 5
  value = json.loads(media.manifest.read_text())
  value['fragments'][0]['mediaPath'] = '/etc/passwd'
  media.manifest.write_text(json.dumps(value))
  with pytest.raises(ValueError, match='path'):
    media_descriptor(media.manifest.parent, 2, 1)


def test_codec_requires_real_sps():
  assert codec_string(b'\0\0\0\1\x67\x42\xc0\x1f\x80') == 'avc1.42c01f'
  with pytest.raises(ValueError):
    codec_string(b'not video')


def test_descriptor_rejects_symlink_metadata(tmp_path):
  session = tmp_path / ('a' * 32)
  session.mkdir()
  target = tmp_path / 'other'
  target.write_text('{}')
  (session / 'media.json').symlink_to(target)
  with pytest.raises(OSError):
    media_descriptor(session, 1, 0)


def test_descriptor_survives_manifest_replacement_after_open(tmp_path, monkeypatch):
  media = store(tmp_path)
  media.begin(1, 'avc1.42c01f', b'init')
  media.publish(b'frame', position=10, keyframe=True)
  original_open = os.open

  def replace_after_open(path, *args, **kwargs):
    fd = original_open(path, *args, **kwargs)
    if Path(path) == media.manifest:
      media.publish(b'next', position=10.05, keyframe=False)
      assert os.fstat(fd).st_nlink == 0
    return fd

  monkeypatch.setattr(os, 'open', replace_after_open)
  descriptor = media_descriptor(media.manifest.parent, 1, 1)
  assert descriptor['available'] and descriptor['length'] == len(b'frame')
  assert media.sequence == 2


def test_descriptor_rejects_hard_linked_metadata(tmp_path):
  media = store(tmp_path)
  media.begin(1, 'avc1.42c01f', b'init')
  os.link(media.manifest, tmp_path / 'linked.json')
  with pytest.raises(ValueError, match='Unsafe'):
    media_descriptor(media.manifest.parent, 1, 0)


def test_mux_copy_has_explicit_pts_and_independent_initialization(tmp_path):
  root = Path(__file__).parents[4]
  library = Path(os.environ.get('SP_REPLAY_TEST_MUX_LIBRARY', root / 'openpilot/tools/replay/libmedia_mux.so'))
  ffmpeg = root / '.venv/lib/python3.12/site-packages/ffmpeg/install/bin/ffmpeg'
  ffprobe = ffmpeg.with_name('ffprobe')
  if not library.exists() or not ffmpeg.exists() or not ffprobe.exists():
    # shortcut: ty drops pytest's reason argument; remove the ignore when its callable binding is fixed.
    pytest.skip('Host replay muxer and bundled FFmpeg must be built')  # ty: ignore[too-many-positional-arguments]
  source = tmp_path / 'fixture.ts'
  subprocess.run([str(ffmpeg), '-nostdin', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pixel_format', 'yuv420p',
                  '-video_size', '32x18', '-framerate', '20', '-i', 'pipe:0',
                  '-frames:v', '1', '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency',
                  '-x264-params', 'aud=1:repeat-headers=1:annexb=1', '-f', 'mpegts', str(source)],
                 input=bytes([16]) * (32 * 18) + bytes([128]) * (32 * 18 // 2), check=True)
  encoded = subprocess.run([str(ffprobe), '-v', 'error', '-show_packets', '-show_data', '-select_streams', 'v:0',
                            '-of', 'json', str(source)], check=True, capture_output=True, text=True)
  data = json.loads(encoded.stdout)['packets'][0]['data']
  packet = bytes.fromhex(''.join(re.findall(r'^[0-9a-f]+: ([0-9a-f ]+?)  ', data, re.MULTILINE)))
  mux = MediaMux(32, 18, packet, library=library)
  try:
    first = mux.frame(packet, pts_us=0, keyframe=True)
    second = mux.frame(packet, pts_us=125000, keyframe=True)
    clip = tmp_path / 'probe.mp4'
    clip.write_bytes(mux.init + first + second)
    result = subprocess.run([str(ffprobe), '-v', 'error', '-show_packets', '-of', 'json', str(clip)], check=True, capture_output=True, text=True)
    packets = json.loads(result.stdout)['packets']
    assert [float(row['pts_time']) for row in packets] == [0, .125]
    assert [float(row['duration_time']) for row in packets] == [.05, .05]
    assert 'K' in packets[0]['flags']
    assert b'ftyp' in mux.init and b'moov' in mux.init and b'moof' in first and b'mdat' in first
    with pytest.raises(RuntimeError, match='clock'):
      mux.frame(packet, pts_us=124999, keyframe=True)
  finally:
    mux.close()


def test_transport_clock_uses_capture_intervals_and_excludes_pauses():
  from openpilot.starpilot.replay.media import FrameTimeline
  clock = FrameTimeline()
  assert clock.next(1, 1_000_000_000) == (0, True)
  assert clock.next(1, 1_060_000_000) == (60000, False)
  assert clock.next(1, 1_125_000_000) == (125000, False)
  clock.flush()
  assert clock.next(1, 10_000_000_000) == (175000, False)
  assert clock.next(1, 10_058_823_529) == (233823, False)
  for i in range(5):
    clock.next(1, 10_100_000_000 + i * 50_000_000)
  assert clock.next(1, 10_350_000_000)[1] is True
  assert clock.next(2, 11_000_000_000) == (0, True)
  with pytest.raises(ValueError):
    clock.next(1, 12_000_000_000)
  with pytest.raises(ValueError):
    clock.next(2, 10_000_000_000)


def test_transport_clock_compresses_long_stalls_without_losing_fractional_time():
  from openpilot.starpilot.replay.media import FrameTimeline
  clock = FrameTimeline()
  assert clock.next(1, 1_000_000_000)[0] == 0
  assert clock.next(1, 1_058_823_529)[0] == 58823
  assert clock.next(1, 1_117_647_058)[0] == 117647
  assert clock.next(1, 4_000_000_000)[0] == 167647
  clock.flush()
  assert clock.next(1, 5_000_000_000)[0] == 217647


@pytest.mark.parametrize('mutation', [
  lambda value: [],
  lambda value: {**value, 'fragments': ['not a descriptor']},
  lambda value: {**value, 'firstSequence': '1'},
  lambda value: {**value, 'codec': 'avc1.invalid'},
])
def test_descriptor_rejects_malformed_metadata(tmp_path, mutation):
  media = store(tmp_path)
  media.begin(1, 'avc1.42c01f', b'init')
  media.publish(b'frame', position=10, keyframe=True)
  media.manifest.write_text(json.dumps(mutation(json.loads(media.manifest.read_text()))))
  with pytest.raises(ValueError):
    media_descriptor(media.manifest.parent, 1, 1)


def test_descriptor_rejects_nonfinite_source_position(tmp_path):
  media = store(tmp_path)
  media.begin(1, 'avc1.42c01f', b'init')
  media.publish(b'frame', position=10, keyframe=True)
  value = json.loads(media.manifest.read_text())
  value['fragments'][0]['firstPosition'] = float('nan')
  media.manifest.write_text(json.dumps(value))
  with pytest.raises(ValueError, match='position'):
    media_descriptor(media.manifest.parent, 1, 1)


def test_batch_uses_one_manifest_snapshot_and_obeys_byte_budget(tmp_path, monkeypatch):
  media = store(tmp_path)
  media.begin(1, 'avc1.42c01f', b'init')
  for index in range(9):
    media.publish(b'x' * 200000, position=index / 20, keyframe=index == 0)
  original_open, opens = os.open, []
  def observed_open(path, *args, **kwargs):
    if Path(path) == media.manifest:
      opens.append(path)
    return original_open(path, *args, **kwargs)
  monkeypatch.setattr(os, 'open', observed_open)
  batch = media_descriptor(media.manifest.parent, 1, 1, 8)
  assert len(opens) == 1
  assert [row['sequence'] for row in batch['fragments']] == [1, 2, 3, 4, 5]
  assert sum(row['length'] for row in batch['fragments']) == 1000000
  partial = media_descriptor(media.manifest.parent, 1, 9, 8)
  assert [row['sequence'] for row in partial['fragments']] == [9]
  assert media_descriptor(media.manifest.parent, 1, 10, 8)['code'] == 'media_pending'
  value = json.loads(media.manifest.read_text())
  value['fragments'][1]['mediaPath'] = '/etc/passwd'
  media.manifest.write_text(json.dumps(value))
  with pytest.raises(ValueError, match='path'):
    media_descriptor(media.manifest.parent, 1, 1, 8)


@pytest.mark.parametrize('count', [0, 9, True, 1.5])
def test_descriptor_rejects_invalid_batch_count(tmp_path, count):
  media = store(tmp_path)
  with pytest.raises(ValueError):
    media_descriptor(media.manifest.parent, 1, 1, count)
