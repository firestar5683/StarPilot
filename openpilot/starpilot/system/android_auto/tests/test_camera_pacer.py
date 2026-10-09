from types import SimpleNamespace

from openpilot.starpilot.system.android_auto import current_car_ui
from openpilot.starpilot.system.android_auto.frame_source import FrameProducer, FrameRequest

STREAMS = SimpleNamespace(VISION_STREAM_NARROW_ROAD=0, VISION_STREAM_CABIN=1, VISION_STREAM_WIDE_ROAD=2)
STEP_MS = int(current_car_ui.CAMERA_WAIT_STEP * 1000)


class FakeSock:
  """A conflated CameraState socket and its poller: ``arrivals`` says whether each poll finds a message."""

  def __init__(self):
    self.arrivals: list[bool] = []
    self.timeouts: list[int] = []
    self._ready = False

  def poll(self, timeout_ms: int):
    self.timeouts.append(timeout_ms)
    self._ready = self.arrivals.pop(0) if self.arrivals else False
    return [self] if self._ready else []

  def receive(self, non_blocking: bool = False):
    ready, self._ready = self._ready, False
    return b"msg" if ready else None


def make_pacer():
  socks: dict[str, FakeSock] = {}

  def factory(name):
    socks[name] = FakeSock()
    return socks[name], socks[name]

  return current_car_ui.CameraPacer(sock_factory=factory, stream_types=STREAMS), socks


def test_draws_once_per_frame_of_the_shown_camera():
  pacer, socks = make_pacer()
  assert pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.0)  # nothing seen yet: quiet, draw now
  road = socks["narrowRoadCameraState"]
  road.arrivals = [True, False, True, False]
  assert pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.0)
  assert not pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.01)
  assert pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.05)
  assert not pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.06)  # same frame is never drawn twice
  assert road.timeouts == [0, 0, STEP_MS, STEP_MS, STEP_MS]


def test_subscribes_only_to_the_camera_on_screen():
  pacer, socks = make_pacer()
  pacer.wait(STREAMS.VISION_STREAM_WIDE_ROAD, 10.0)
  assert list(socks) == ["wideRoadCameraState"]
  pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.0)
  assert sorted(socks) == ["narrowRoadCameraState", "wideRoadCameraState"]


def test_quiet_camera_renders_at_the_encoder_rate():
  pacer, socks = make_pacer()
  pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.0)
  road = socks["narrowRoadCameraState"]
  road.arrivals = [True]
  assert pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.0)
  assert not pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.05)
  # The camera stopped: every later frame is drawn without waiting, not one per CAMERA_MAX_GAP.
  for i in range(10):
    assert pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.001 + current_car_ui.CAMERA_MAX_GAP + i / 30)
  assert road.timeouts[-10:] == [0] * 10
  # And pacing resumes when it comes back.
  road.arrivals = [True]
  assert pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 11.0)
  assert not pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 11.03)


def test_unknown_stream_does_not_block():
  pacer, socks = make_pacer()
  assert pacer.wait(99, 10.0)
  assert socks == {}


def test_stream_names_match_the_services():
  from openpilot.cereal.services import SERVICE_LIST
  from openpilot.cereal.visionipc import VisionStreamType
  pacer = current_car_ui.CameraPacer(sock_factory=lambda name: None)
  assert {VisionStreamType(stream) for stream in pacer.state_for_stream} == \
         {VisionStreamType.VISION_STREAM_NARROW_ROAD, VisionStreamType.VISION_STREAM_WIDE_ROAD, VisionStreamType.VISION_STREAM_CABIN}
  for state in pacer.state_for_stream.values():
    assert state in SERVICE_LIST


def test_twenty_hz_camera_inside_a_thirty_fps_budget_draws_every_camera_frame_once(tmp_path):
  """Simulate the renderer's gate: the 30 fps capture schedule, then the camera pacer."""
  producer = FrameProducer(str(tmp_path / "frames"))
  request = FrameRequest(1280, 720, 0, 0, 33_333)
  pacer, socks = make_pacer()
  camera_period, step = 0.05, 0.001
  next_camera, drawn, frames = 10.0, [], 0
  pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 9.9)
  road = socks["narrowRoadCameraState"]
  now = 10.0
  while now < 12.0:
    if producer.capture_delay(request, int(now * 1e9)) == 0:
      road.arrivals = [now >= next_camera]
      if pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, now):
        if now >= next_camera:
          frames += 1
          next_camera += camera_period
        drawn.append(now)
        producer.advance(request, int(now * 1e9))
    now = round(now + step, 6)
  assert frames == 40                      # every 20 Hz frame in two seconds
  assert len(drawn) == frames              # and nothing drawn in between
  gaps = [b - a for a, b in zip(drawn, drawn[1:], strict=False)]
  assert min(gaps) >= request.interval_us / 1e6 * 0.75 - 1e-9  # never faster than the encoder budget


def test_shorter_step_while_a_frame_is_still_on_the_gpu():
  pacer, socks = make_pacer()
  pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.0)
  sock = socks["narrowRoadCameraState"]
  sock.arrivals = [True, False, False]
  pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.0)
  pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.01, current_car_ui.READBACK_POLL_STEP)
  pacer.wait(STREAMS.VISION_STREAM_NARROW_ROAD, 10.02)
  assert sock.timeouts[-2:] == [int(current_car_ui.READBACK_POLL_STEP * 1000), STEP_MS]
