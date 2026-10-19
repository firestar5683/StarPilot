"""Exports keep recorded coverage, remain private, and become ready only after cleanup."""
from types import SimpleNamespace
from typing import NoReturn
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from unittest.mock import patch

import pytest

from openpilot.starpilot.galaxy.recording_media import _ffmpeg_binary
from openpilot.starpilot.replay.export import MAX_EXPORT_BYTES, ExportSource, ExportVideo, disk_budget, export_ranges
from openpilot.starpilot.replay.owner import ReplayOwner, Rejected
from openpilot.starpilot.replay.tests.test_owner import CLIENT, OTHER, ROUTE, Catalog, wait_for


@pytest.fixture
def packet(tmp_path, monkeypatch):
  monkeypatch.setattr('openpilot.starpilot.replay.export.shutil.disk_usage', lambda directory: SimpleNamespace(total=100 * 1024 ** 3, free=90 * 1024 ** 3))
  binary = _ffmpeg_binary()
  output = tmp_path / 'frame.ts'
  subprocess.run([str(binary), '-nostdin', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pixel_format', 'yuv420p',
                  '-video_size', '32x18', '-framerate', '20', '-i', 'pipe:0', '-frames:v', '1', '-c:v', 'libx264',
                  '-preset', 'ultrafast', '-tune', 'zerolatency', '-x264-params', 'aud=1:repeat-headers=1:annexb=1',
                  '-f', 'mpegts', str(output)], input=bytes([16]) * (32 * 18) + bytes([128]) * (32 * 18 // 2), check=True)
  probe = subprocess.run([str(binary.with_name('ffprobe')), '-v', 'error', '-show_packets', '-show_data', '-select_streams', 'v:0',
                          '-of', 'json', str(output)], check=True, capture_output=True)
  data = json.loads(probe.stdout)['packets'][0]['data']
  return bytes.fromhex(''.join(re.findall(r'^[0-9a-f]+: ([0-9a-f ]+?)  ', data, re.MULTILINE)))


def test_recorded_ranges_use_actual_segment_ids_and_reject_overlap():
  status = {'start': 0, 'end': 93, 'segmentRanges': [[2, 0, .15], [7, 92.75, 93]]}
  assert export_ranges(status, 7) == [(92.75, 93)]
  assert export_ranges(status, None) == [(0, .15), (92.75, 93)]
  assert export_ranges({**status, 'segmentRanges': [[2, 0, 1], [7, 1, 2]]}, None) == [(0, 2)]
  for rows in ([[2, 0, 1], [7, .5, 2]], [[2, 0, 1], [2, 2, 3]], [[7, 0, float('nan')]], []):
    with pytest.raises(ValueError):
      export_ranges({**status, 'segmentRanges': rows}, 7)
  with pytest.raises(ValueError):
    export_ranges(status, 1)


@pytest.mark.parametrize(('written', 'timeout'), [(0, 30), (8 * 1024 ** 3, 522), (MAX_EXPORT_BYTES, 2058)])
def test_export_mp4_preserves_coverage_and_scales_finalization_time(tmp_path, packet, written, timeout):
  writer = ExportVideo(tmp_path, 32, 18, [(0, .15), (92.75, 93)], MAX_EXPORT_BYTES)
  commands = []
  engine = SimpleNamespace(command=lambda command: commands.append(command))
  try:
    for position in (0, .05, .1):
      writer.frame(packet, position=position, keyframe=True)
    assert not writer.advance(engine, {'position': .15, 'paused': False}, False)
    assert commands[-1]['op'] == 'pause' and commands[-1]['paused']
    assert not writer.advance(engine, {'position': .15, 'paused': True}, True), 'drain readback before advancing'
    assert not writer.advance(engine, {'position': .15, 'paused': True}, False)
    assert commands[-1]['op'] == 'seek' and commands[-1]['position'] == 92.75
    for position in (92.75, 92.8, 92.85, 92.9, 92.95):
      writer.frame(packet, position=position, keyframe=True)
    assert writer.advance(engine, {'position': 93, 'paused': True}, False)
    # Exercise large-export deadlines without writing multi-gigabyte fixtures.
    writer.written = max(writer.written, written)
    with patch('openpilot.starpilot.replay.export.subprocess.run', wraps=subprocess.run) as run:
      writer.finalize()
    assert run.call_args_list[0].kwargs['timeout'] == timeout
  finally:
    writer.close()
  assert not (tmp_path / 'export.part').exists()
  probe = subprocess.run([str(_ffmpeg_binary().with_name('ffprobe')), '-v', 'error', '-show_packets', '-show_format',
                          '-of', 'json', str(tmp_path / 'export.mp4')], check=True, capture_output=True)
  info = json.loads(probe.stdout)
  assert float(info['format']['duration']) == pytest.approx(.4)
  assert [float(row['pts_time']) for row in info['packets']] == pytest.approx([i * .05 for i in range(8)])


def test_partial_video_and_storage_shortage_cannot_be_finalized(tmp_path, packet, monkeypatch):
  writer = ExportVideo(tmp_path, 32, 18, [(0, 2)], 1024 ** 2)
  try:
    with pytest.raises(ValueError, match='beginning'):
      writer.frame(packet, position=1, keyframe=True)
    writer.frame(packet, position=0, keyframe=True)
    with pytest.raises(ValueError, match='lost video'):
      writer.frame(packet, position=.8, keyframe=True)
    with pytest.raises(ValueError, match='end'):
      writer.advance(SimpleNamespace(command=lambda command: None), {'position': 2, 'paused': True}, False)
    monkeypatch.setattr('openpilot.starpilot.replay.export.shutil.disk_usage', lambda directory: SimpleNamespace(total=100 * 1024 ** 3, free=10 * 1024 ** 3))
    assert disk_budget(tmp_path) == 0
    writer.disk_check_at = 0
    with pytest.raises(OSError, match='free recording storage'):
      writer.write(b'x')
  finally:
    writer.close()
  assert not (tmp_path / 'export.mp4').exists()


def _reject_engine_resume(_command) -> NoReturn:
  __tracebackhide__ = True
  raise pytest.fail.Exception('an ended engine must not resume')


def test_export_finishes_at_actual_engine_eof(tmp_path, packet):
  from openpilot.tools.replay.tests.test_machine import BINARY, Machine
  if not BINARY.is_file():
    raise pytest.skip.Exception('build the replay test binary first')
  with Machine([(0, [.1, .2, .3], True)]) as engine:
    initial = engine.wait(lambda status: status['state'] == 'paused')
    engine.command_status('pause', 'a4', paused=False)
    ended = engine.wait(lambda status: status['state'] == 'ended')
  assert ended['position'] < ended['end']
  stopped = SimpleNamespace(command=_reject_engine_resume)
  writer = ExportVideo(tmp_path, 32, 18, [(initial['start'], initial['end'])], 1024 ** 2)
  try:
    for position in (.1, .2, .3):
      writer.frame(packet, position=position, keyframe=True)
    assert not writer.advance(stopped, ended, True), 'the last readback must drain before finalization'
    assert writer.advance(stopped, ended, False)
    writer.finalize()
  finally:
    writer.close()
  assert (tmp_path / 'export.mp4').is_file()


def test_early_engine_eof_cannot_hide_missing_export_coverage(tmp_path, packet):
  writer = ExportVideo(tmp_path, 32, 18, [(0, 2)], 1024 ** 2)
  engine = SimpleNamespace(command=_reject_engine_resume)
  try:
    writer.frame(packet, position=0, keyframe=True)
    with pytest.raises(ValueError, match='end of the selected coverage'):
      writer.advance(engine, {'state': 'ended', 'position': .1, 'end': 2, 'paused': True}, False)
  finally:
    writer.close()
  assert not (tmp_path / 'export.mp4').exists()


def export_request(owner, **extra):
  return {'op': 'export-start', 'routeId': ROUTE, 'clientId': CLIENT, 'requestId': 'd' * 32,
          'expectedOwnerId': owner.owner_id, **extra}


@pytest.fixture
def exporting_owner(tmp_path, monkeypatch):
  monkeypatch.setattr('openpilot.starpilot.replay.owner.disk_budget', lambda directory: 1024 ** 3)
  catalog = Catalog(tmp_path / 'logs')
  catalog.root.mkdir()
  gate = tmp_path / 'finish'
  allowed = [True]
  children = []
  script = '''import json,os,pathlib,sys,time
folder=pathlib.Path(sys.argv[1]); gate=pathlib.Path(sys.argv[2])
s={'event':'status','state':'paused','position':0.,'start':0.,'end':1.,'rate':1.,'paused':True,'epoch':1,
   'frameReady':True,'mediaReady':False,'lastRequestId':None,'error':None,'exportState':'rendering','exportProgress':.1}
print(json.dumps(s),flush=True)
while not gate.exists(): time.sleep(.01)
p=folder/'export.mp4'; p.write_bytes(b'finished-video'); p.chmod(0o600)
s.update(exportState='ready',exportProgress=1.,error='recording_gap')
print(json.dumps(s),flush=True)
'''
  def spawn(command, **kwargs):
    directory = command[command.index('--session-dir') + 1]
    assert '--export-budget' in command
    children.append(subprocess.Popen([sys.executable, '-u', '-c', script, directory, str(gate)], **kwargs))
    return children[-1]
  owner = ReplayOwner(catalog, root=tmp_path / 'replay', authority=lambda: allowed[0], spawn=spawn)
  yield owner, catalog, gate, allowed
  owner.close()
  assert all(child.poll() is not None for child in children)


def test_export_survives_viewer_lease_and_publishes_only_after_cleanup(exporting_owner):
  owner, catalog, gate, _ = exporting_owner
  snapshot = b'{"version":1,"values":{}}'
  owner.view_display = CLIENT, ROUTE, snapshot
  started = owner.dispatch(export_request(owner, segment=2))
  sid = started['sessionId']
  wait_for(lambda: owner.status['state'] == 'paused')
  owner.lease_at = -1000
  assert (owner.root / 'sessions' / sid / 'display.json').read_bytes() == snapshot
  with pytest.raises(Rejected, match='unavailable'):
    owner.dispatch({'op': 'export-file', 'exportId': sid, 'clientId': CLIENT})
  time.sleep(.2)
  assert owner.worker is not None, 'exports do not use the preview lease'
  gate.touch()
  wait_for(lambda: owner.worker is None)
  result = owner.dispatch({'op': 'status', 'clientId': CLIENT})['export']
  assert result['state'] == 'ready' and result['segment'] == 2 and result['owned']
  assert catalog.released == 1 and not (owner.root / 'sessions' / sid).exists()
  assert not owner.dispatch({'op': 'status', 'clientId': OTHER})['export']['owned']
  with pytest.raises(Rejected):
    owner.dispatch({'op': 'export-file', 'exportId': sid, 'clientId': OTHER})
  receipt = owner.dispatch({'op': 'export-file', 'exportId': sid, 'clientId': CLIENT})
  source = ExportSource(owner.root, sid, receipt['bytes'])
  try:
    assert os.read(source.fd, 100) == b'finished-video'
    with pytest.raises(BlockingIOError):
      fd = os.open(owner.root / 'exports' / sid / 'replay.mp4', os.O_RDONLY)
      try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
      finally:
        os.close(fd)
    with pytest.raises(Rejected, match='downloading'):
      owner.dispatch({'op': 'export-clear', 'routeId': ROUTE})
    assert not owner._expire_export(replace=True)
    owner.export['expires'] = time.monotonic() - 1
    assert owner.dispatch({'op': 'status', 'clientId': CLIENT})['export']['expiresInSeconds'] == 0
  finally:
    source.close()
  owner.worker = object()
  owner.status['purpose'] = 'view'
  try:
    assert 'export' not in owner.dispatch({'op': 'status', 'clientId': CLIENT}), 'an unrelated preview cannot extend the export cache lifetime'
  finally:
    owner.worker = None
  owner.dispatch({'op': 'export-clear', 'routeId': ROUTE})
  assert owner.export is None and not list((owner.root / 'exports').iterdir())


def test_cancelled_export_never_becomes_downloadable(exporting_owner):
  owner, catalog, _, _ = exporting_owner
  started = owner.dispatch(export_request(owner))
  wait_for(lambda: owner.status['state'] == 'paused')
  owner.dispatch({'op': 'stop', 'sessionId': started['sessionId'], 'clientId': CLIENT, 'requestId': 'e' * 32})
  wait_for(lambda: owner.worker is None)
  assert owner.export['state'] == 'cancelled'
  assert catalog.released == 1 and not list((owner.root / 'exports').iterdir())


def test_lost_authority_fails_export_and_releases_sources(exporting_owner):
  owner, catalog, _, allowed = exporting_owner
  owner.dispatch(export_request(owner))
  wait_for(lambda: owner.status['state'] == 'paused')
  allowed[0] = False
  wait_for(lambda: owner.worker is None)
  assert owner.export['state'] == 'failed' and owner.export['error'] == 'not_offroad'
  assert catalog.released == 1
