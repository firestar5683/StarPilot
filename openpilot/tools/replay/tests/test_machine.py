"""Synthetic local replay only: unique private buses, no decoder or driving services."""
import contextlib
import bz2
import json
import os
from pathlib import Path
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from unittest.mock import patch

from openpilot.cereal import log
from openpilot.common.basedir import BASEDIR


BINARY = Path(os.environ.get("REPLAY_TEST_BINARY", Path(BASEDIR) / "openpilot/tools/replay/replay"))
FFMPEG = shutil.which("ffmpeg", path=os.defpath)
BOOT, MONO, WALL = 40_000_000_000, 37_000_000_000, 1_791_878_400_000_000_000


def message(kind, stamp, *, valid=True, **fields):
  event = log.Event.new_message(logMonoTime=stamp, valid=valid)
  data = event.init(kind)
  for key, value in fields.items():
    setattr(data, key, value)
  return event.to_bytes()


def segment(root, number, times, *, video=True, clocks=True, inconsistent=False, compressed=False, clock_spikes=False, paired_clocks=True,
            wide_leads=False, inconsistent_pair=False, invalid_clocks=False):
  path = root / f"00000001--1234567890--{number}"
  path.mkdir()
  events = [message("initData", BOOT, wallTimeNanos=WALL)]
  mono = MONO if clocks and paired_clocks else BOOT
  if clocks:
    for offset in ((0, 200_000_000, 400_000_000, 600_000_000) if clock_spikes else (0, 200_000_000)):
      wall = WALL + offset + (10_000_000 if inconsistent and offset else 0)
      if clock_spikes and offset in (200_000_000, 400_000_000):
        wall += 12_000_000
      event = log.Event.new_message(logMonoTime=mono + offset, valid=not invalid_clocks)
      event.init("clocks").wallTimeNanos = wall
      if paired_clocks:
        event.clocks.deprecated.monotonicNanos = mono + offset
        event.clocks.deprecated.bootTimeNanos = BOOT + offset + (10_000_000 if inconsistent_pair and offset else 0)
      events.append(event.to_bytes())
  if wide_leads:
    events.append(message("wideRoadEncodeIdx", BOOT + 50_000_000, frameId=0,
                          type="fullHEVC", segmentNum=number, segmentId=0,
                          timestampSof=BOOT + 10_000_000, timestampEof=BOOT + 20_000_000))
    (path / "ecamera.hevc").write_bytes(b"unused-with-no-vipc")
  for index, seconds in enumerate(times):
    delta = round(seconds * 1e9)
    events.extend((message("carState", mono + delta, vEgo=float(index + 1)),
                   message("selfdriveState", mono + delta, enabled=False),
                   message("narrowRoadEncodeIdx", BOOT + delta, frameId=index,
                           type="fullHEVC", segmentNum=number, segmentId=index,
                           timestampSof=BOOT + delta - 50_000_000,
                           timestampEof=BOOT + delta - 40_000_000)))
  payload = b"".join(events)
  (path / ("rlog.bz2" if compressed else "rlog")).write_bytes(bz2.compress(payload) if compressed else payload)
  if video:
    (path / "fcamera.hevc").write_bytes(b"unused-with-no-vipc")


class Machine:
  def __init__(self, segments, **options):
    self.directory = tempfile.TemporaryDirectory(prefix="replay-machine-")
    self.root = Path(self.directory.name)
    self.routes = self.root / "routes"
    self.routes.mkdir()
    for number, times, video in segments:
      segment(self.routes, number, times, video=video, **options)
    for name in ("params", "cache"):
      (self.root / name).mkdir(mode=0o700)
    self.ipc = Path("/dev/shm") / f"msgq_replay-test-{uuid.uuid4().hex}"
    self.ipc.mkdir(mode=0o700)
    clock = self.ipc / "display-clock"
    clock.touch(mode=0o600)
    clock.write_bytes(bytes(80))
    self.env = dict(os.environ, SP_REPLAY_CONTEXT="1", SP_REPLAY_PARENT_PID=str(os.getpid()),
                    OPENPILOT_PREFIX=self.ipc.name.removeprefix("msgq_"), PARAMS_ROOT=str(self.root / "params"),
                    COMMA_CACHE=str(self.root / "cache"), SP_REPLAY_CLOCK_PATH=str(clock))
    self.command = [str(BINARY), "--machine", "--no-vipc", "--data_dir", str(self.routes), "00000001--1234567890"]
    if options.get('wide_leads'):
      self.command.insert(2, '--wide-road')
    self.stderr = tempfile.TemporaryFile(mode="w+")
    self.process = None
    self.statuses = queue.Queue()

  def start(self):
    self.process = subprocess.Popen(self.command, env=self.env, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=self.stderr, text=True)
    def reader():
      stdout = self.process.stdout
      assert stdout is not None
      for line in stdout:
        try:
          self.statuses.put(json.loads(line))
        except ValueError as error:
          self.statuses.put(error)
    self.thread = threading.Thread(target=reader, daemon=True)
    self.thread.start()
    return self

  def wait(self, predicate, timeout=8):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
      try:
        value = self.statuses.get(timeout=.1)
      except queue.Empty:
        continue
      if isinstance(value, Exception):
        raise value
      last = value
      if predicate(value):
        return value
    self.stderr.seek(0)
    raise AssertionError(f"No matching status; last={last}, stderr={self.stderr.read()[-6000:]}")

  def command_status(self, op, request, **fields):
    self.process.stdin.write(json.dumps(dict(op=op, requestId=request, **fields)) + "\n")
    self.process.stdin.flush()
    return self.wait(lambda status: status["lastRequestId"] == request)

  def close(self):
    if self.process:
      self.process.stdin.close()
      if self.process.poll() is None:
        try:
          self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
          self.process.kill()
          self.process.wait(timeout=3)
      self.process.stdout.close()
      self.thread.join(timeout=1)
    self.stderr.close()
    shutil.rmtree(self.ipc)
    self.directory.cleanup()

  def __enter__(self):
    return self.start()

  def __exit__(self, *_):
    self.close()


@unittest.skipUnless(BINARY.is_file() and os.name == "posix", "build the replay test binary first")
class TestMachine(unittest.TestCase):
  def test_pause_seek_rate_clock_and_eof(self):
    with Machine([(0, [.1, .2, .3], True)]) as engine:
      initial = engine.wait(lambda value: value["state"] == "paused")
      self.assertEqual(initial["routeStartNs"], MONO)
      self.assertEqual(initial["wallMinusMonoNs"], str(WALL - MONO))
      self.assertEqual(initial["seekRanges"], [[.1, .35]])
      self.assertTrue(initial["paused"])
      epoch = initial["epoch"]
      sought = engine.command_status("seek", "a1", position=.25)
      self.assertEqual(sought["state"], "paused")
      self.assertGreater(sought["epoch"], epoch)
      self.assertAlmostEqual(sought["position"], .25)
      invalid = engine.command_status("seek", "a2", position=10)
      self.assertEqual(invalid["error"], "invalid_position")
      self.assertEqual(invalid["epoch"], sought["epoch"])
      self.assertIsNone(engine.process.poll())
      self.assertEqual(engine.command_status("rate", "a3", rate=2)["rate"], 2)
      engine.command_status("pause", "a4", paused=False)
      ended = engine.wait(lambda value: value["state"] == "ended")
      self.assertTrue(ended["paused"])
      self.assertIsNone(engine.process.poll())
      engine.command_status("seek", "a5", position=.1)
      self.assertEqual(engine.command_status("stop", "a6")["lastRequestId"], "a6")
      self.assertEqual(engine.process.wait(timeout=3), 0)

  def test_gap_does_not_skip_and_seek_is_recoverable(self):
    with Machine([(0, [.1, .2, .3], True), (2, [4.1, 4.2, 4.3], True)]) as engine:
      initial = engine.wait(lambda value: value["state"] == "paused")
      self.assertEqual(initial["seekRanges"], [[.1, .35], [4.1, 4.35]])
      engine.command_status("pause", "b1", paused=False)
      gap = engine.wait(lambda value: value["state"] == "buffering" and value["error"] == "recording_gap")
      self.assertAlmostEqual(gap["position"], .35)
      self.assertTrue(gap["paused"])
      invalid = engine.command_status("seek", "b2", position=2)
      self.assertEqual(invalid["error"], "invalid_position")
      self.assertEqual(invalid["epoch"], gap["epoch"])
      recovered = engine.command_status("seek", "b3", position=4.1)
      self.assertEqual(recovered["state"], "paused")
      engine.command_status("pause", "b4", paused=False)
      engine.wait(lambda value: value["state"] == "ended")

  def test_first_playable_segment_uses_actual_index_time(self):
    with Machine([(0, [.1], False), (1, [65.1, 65.2], True)]) as engine:
      initial = engine.wait(lambda value: value["state"] == "paused")
      self.assertEqual(initial["start"], 65.1)
      self.assertEqual(initial["seekRanges"], [[65.1, 65.25]])

  def test_optional_wide_camera_does_not_precede_primary_camera_range(self):
    with Machine([(0, [.1, .2], True)], wide_leads=True) as engine:
      initial = engine.wait(lambda value: value["state"] == "paused")
      self.assertEqual(initial["start"], .1)
      self.assertEqual(initial["position"], .1)

  def test_compressed_fd_and_paused_raw_camera_index(self):
    from openpilot.cereal import messaging
    engine = Machine([(0, [.1, .2, .3], True)], compressed=True)
    with patch.dict(os.environ, engine.env):
      socket = messaging.sub_sock("narrowRoadEncodeIdx", timeout=1000)
    try:
      engine.start()
      engine.wait(lambda value: value["state"] == "paused")
      # A subscriber that connected before the publisher needs the same explicit
      # paused re-prime as the compositor's late VisionIPC connection.
      messaging.recv_one(socket)
      engine.command_status("seek", "c0", position=.1)
      message = messaging.recv_one(socket)
      self.assertIsNotNone(message)
      self.assertEqual(message.logMonoTime, BOOT + 100_000_000)
      self.assertEqual(message.narrowRoadEncodeIdx.timestampSof, BOOT + 50_000_000)
      engine.command_status("seek", "c1", position=.25)
      message = messaging.recv_one(socket)
      self.assertIsNotNone(message)
      self.assertEqual(message.logMonoTime, BOOT + 200_000_000)
      self.assertEqual(message.narrowRoadEncodeIdx.frameId, 1)
      self.assertEqual(message.narrowRoadEncodeIdx.timestampSof, BOOT + 150_000_000)
      self.assertEqual(list((engine.root / "cache").iterdir()), [])
    finally:
      del socket
      engine.close()

  def test_display_clock_precedes_message_after_scheduler_resync(self):
    from openpilot.cereal import messaging
    from openpilot.tools.replay.display_clock import DisplayClockReader

    engine = Machine([(0, [.1, 2.1], True)])
    stamp = MONO + 1_500_000_000
    source = engine.routes / "00000001--1234567890--0/rlog"
    with source.open("ab") as output:
      output.write(message("carState", stamp, vEgo=42.0))
    with patch.dict(os.environ, engine.env):
      socket = messaging.sub_sock("carState", timeout=1000)
      clock = DisplayClockReader()
    try:
      engine.start()
      engine.wait(lambda value: value["state"] == "paused")
      messaging.recv_one(socket)
      engine.command_status("seek", "c101", position=.1)
      self.assertIsNotNone(messaging.recv_one(socket))
      engine.command_status("pause", "c102", paused=False)
      # The >1 s gap resets scheduling without waiting for recorded time.
      # No selected-service clock anchor follows this message for another .6 s.
      received = messaging.recv_one(socket)
      while received is not None and received.logMonoTime < stamp:
        received = messaging.recv_one(socket)
      self.assertIsNotNone(received)
      self.assertEqual(received.logMonoTime, stamp)
      sample = clock.sample()
      self.assertTrue(sample.valid)
      self.assertGreaterEqual(sample.now_ns, received.logMonoTime)
    finally:
      clock.close()
      del socket
      engine.close()

  @unittest.skipUnless(sys.platform == "linux", "Linux V4L decoder lifecycle")
  def test_decoder_releases_resources_after_initialization_failure(self):
    native_test = BINARY.parent / "tests/test_v4l_decoder_lifecycle"
    self.assertTrue(native_test.is_file())
    result = subprocess.run([str(native_test)], timeout=10, capture_output=True, text=True)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

  def test_bounded_decompression(self):
    from openpilot.tools.lib.file_downloader import decompress_file
    with tempfile.TemporaryDirectory(prefix="replay-decompress-") as temporary:
      source, output = Path(temporary) / "rlog.bz2", Path(temporary) / "output"
      source.write_bytes(bz2.compress(bytes(8192)))
      with self.assertRaises(ValueError):
        decompress_file(source, output, max_bytes=4096)

  @unittest.skipUnless(FFMPEG, "installed system ffmpeg fixture encoder required")
  def test_shared_decoder_returns_correct_pixels(self):
    assert FFMPEG is not None
    native_test = BINARY.parent / "tests/test_route"
    self.assertTrue(native_test.is_file())
    with tempfile.TemporaryDirectory(prefix="replay-decode-") as temporary:
      root = Path(temporary)
      clips = []
      for name, levels in (("a", (30, 90, 120)), ("b", (200, 220, 240))):
        raw, clip = root / (name + ".yuv"), root / (name + ".ts")
        raw.write_bytes(b"".join(bytes([level]) * (32 * 18) + bytes([128]) * (32 * 18 // 2) for level in levels))
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "yuv420p",
                        "-s", "32x18", "-r", "20", "-i", str(raw), "-c:v", "libx264", "-qp", "0", "-bf", "0",
                        "-g", "100", "-tune", "zerolatency", "-f", "mpegts", str(clip)], check=True, timeout=10)
        clips.append(str(clip))
      subprocess.run([str(native_test), *clips], check=True, timeout=10, capture_output=True)

  def test_legacy_recordings_keep_original_timestamps_without_clock_admission(self):
    for options in ({"clocks": False}, {"paired_clocks": False}, {"paired_clocks": False, "inconsistent": True},
                    {"paired_clocks": False, "clock_spikes": True}, {"paired_clocks": False, "invalid_clocks": True}):
      with self.subTest(options=options), Machine([(0, [.1, .2], True)], **options) as engine:
        ready = engine.wait(lambda value: value["state"] == "paused")
        self.assertEqual(ready["routeStartNs"], BOOT)
        self.assertEqual(ready["position"], .1)
        self.assertIn("Legacy recording", ready["sourceWarnings"][0])
        self.assertEqual(ready["wallMinusMonoNs"], "0" if options.get("clocks") is False or options.get("invalid_clocks") else str(WALL - BOOT))
        self.assertFalse(any(path.name in ("can", "sendcan") for path in engine.ipc.iterdir()))

  def test_inconsistent_explicit_clock_pairs_fail_closed(self):
    with Machine([(0, [.1], True)], inconsistent_pair=True) as engine:
      failed = engine.wait(lambda value: value["state"] == "failed")
      self.assertIn("inconsistent", failed["error"])
      self.assertEqual(engine.process.wait(timeout=3), 2)

  def test_legacy_missing_initial_segments_preserve_route_positions(self):
    with Machine([(2, [121.1, 121.2], True)], clocks=False) as engine:
      ready = engine.wait(lambda value: value["state"] == "paused")
      self.assertEqual(ready["routeStartNs"], BOOT)
      self.assertEqual(ready["start"], 121.1)
      self.assertEqual(ready["seekRanges"], [[121.1, 121.25]])

  def test_selected_segment_starts_at_recorded_boundary_instead_of_assumed_minute(self):
    for number, position in ((0, .1), (2, 121.137)):
      with self.subTest(segment=number):
        engine = Machine([(0, [.1, .2], True), (2, [121.137, 121.237], True)])
        engine.command[2:2] = ['--start-segment', str(number)]
        with engine:
          ready = engine.wait(lambda value: value['state'] == 'paused')
          self.assertAlmostEqual(ready['position'], position)
          self.assertTrue(ready['paused'])

  def test_selected_missing_segment_fails_instead_of_playing_another_segment(self):
    engine = Machine([(0, [.1, .2], True)])
    engine.command[2:2] = ['--start-segment', '1']
    with engine:
      failed = engine.wait(lambda value: value.get('error') == 'Selected segment has no playable footage')
      self.assertTrue(failed['paused'])
      self.assertEqual(engine.process.wait(timeout=3), 2)

  def test_legacy_wall_correction_and_backwards_seek_follow_recorded_clock_validity(self):
    engine = Machine([(0, [.1, .2, .3, .4], True)], clocks=False)
    correction = 70 * 86400 * 1_000_000_000
    source = engine.routes / "00000001--1234567890--0/rlog"
    with source.open("ab") as output:
      for seconds, adjustment, valid in ((.15, 0, True), (.25, correction, True), (.35, correction, False)):
        offset = round(seconds * 1e9)
        output.write(message("clocks", BOOT + offset, wallTimeNanos=WALL + offset + adjustment, valid=valid))
    with engine:
      ready = engine.wait(lambda value: value["state"] == "paused")
      self.assertEqual(ready["wallMinusMonoNs"], "0")
      for request, seconds, expected in (("c1", .2, WALL - BOOT), ("c2", .3, WALL - BOOT + correction),
                                          ("c3", .4, 0), ("c4", .2, WALL - BOOT), ("c5", .1, 0)):
        status = engine.command_status("seek", request, position=seconds)
        self.assertEqual(status["wallMinusMonoNs"], str(expected))

  def test_explicit_clock_pairs_survive_wall_clock_correction(self):
    with Machine([(0, [.1, .2], True)], paired_clocks=True, inconsistent=True) as engine:
      ready = engine.wait(lambda value: value["state"] == "paused")
      self.assertEqual(ready["routeStartNs"], MONO)
      self.assertEqual(ready["sourceWarnings"], [])
      corrected = engine.command_status("seek", "c0", position=.2)
      self.assertEqual(corrected["wallMinusMonoNs"], str(WALL - MONO + 10_000_000))

  def test_explicit_clock_pair_does_not_require_a_valid_wall_clock(self):
    with Machine([(0, [.1, .2], True)], invalid_clocks=True) as engine:
      ready = engine.wait(lambda value: value["state"] == "paused")
      self.assertEqual(ready["routeStartNs"], MONO)
      self.assertEqual(ready["sourceWarnings"], [])
      self.assertEqual(ready["wallMinusMonoNs"], "0")

  def test_parent_death_kills_engine(self):
    engine = Machine([(0, [.1, .2], True)])
    child = None
    try:
      script = """
import json, os, subprocess, sys, time
env = json.loads(sys.argv[1])
env['SP_REPLAY_PARENT_PID'] = str(os.getpid())
p = subprocess.Popen(sys.argv[2:], env=env, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(p.pid, flush=True)
time.sleep(30)
"""
      parent = subprocess.Popen([os.sys.executable, "-c", script, json.dumps(engine.env), *engine.command], stdout=subprocess.PIPE, text=True)
      child = int(parent.stdout.readline())
      time.sleep(.3)
      parent.kill()
      parent.wait(timeout=3)
      parent.stdout.close()
      deadline = time.monotonic() + 3
      while time.monotonic() < deadline:
        path = Path(f"/proc/{child}/stat")
        try:
          state = path.read_text().split()[2]
        except (FileNotFoundError, ProcessLookupError):
          break
        if state == "Z":
          break
        time.sleep(.02)
      else:
        self.fail("Engine survived renderer parent death")
    finally:
      if child:
        with contextlib.suppress(ProcessLookupError):
          os.kill(child, signal.SIGKILL)
      engine.close()
