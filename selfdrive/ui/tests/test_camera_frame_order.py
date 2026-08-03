from types import SimpleNamespace

import pytest

from openpilot.selfdrive.ui.mici.onroad import cameraview as mici_cameraview
from openpilot.selfdrive.ui.onroad import cameraview as big_cameraview


class FakeFrame:
  def __init__(self, frame_id: int, idx: int):
    self.frame_id = frame_id
    self.idx = idx


def _camera_view():
  view = big_cameraview.CameraView.__new__(big_cameraview.CameraView)
  view._name = "camerad"
  view._stream_type = big_cameraview.VisionStreamType.VISION_STREAM_ROAD
  view.frame = None
  view._last_frame_id = -1
  view._regressive_frame_count = 0
  view._texture_needs_update = False
  view._external_texture_id = 0
  view._closed = True
  return view


def test_mici_uses_shared_camera_view():
  assert issubclass(mici_cameraview.CameraView, big_cameraview.CameraView)
  assert mici_cameraview.CameraView._use_upstream_engaged_color
  assert not big_cameraview.CameraView._use_upstream_engaged_color


def test_pending_switch_is_cancelled_when_requested_stream_is_current():
  view = _camera_view()
  view._stream_type = big_cameraview.VisionStreamType.VISION_STREAM_ROAD
  view._target_stream_type = big_cameraview.VisionStreamType.VISION_STREAM_DRIVER
  view._target_client = object()
  view._switching = True

  view.switch_stream(big_cameraview.VisionStreamType.VISION_STREAM_ROAD)

  assert view._target_client is None
  assert view._target_stream_type is None
  assert not view._switching


def test_reentry_switch_request_keeps_matching_candidate():
  view = _camera_view()
  candidate = object()
  view._onroad_reentry_pending = True
  view._reentry_stream_selected = True
  view._target_stream_type = view._stream_type
  view._target_client = candidate
  view._switching = True

  view.switch_stream(view._stream_type)

  assert view._target_client is candidate
  assert view._target_stream_type == view._stream_type
  assert view._switching


def test_onroad_reentry_selects_requested_stream_before_rendering(monkeypatch):
  view = _camera_view()
  view._name = "camerad"
  view._stream_type = big_cameraview.VisionStreamType.VISION_STREAM_WIDE_ROAD
  view.client = object()
  view._target_client = object()
  view._target_stream_type = big_cameraview.VisionStreamType.VISION_STREAM_ROAD
  view._switching = True
  view._onroad_reentry_pending = True
  view._reentry_stream_selected = False
  view._clear_textures = lambda: None
  clients = []

  class FakeClient:
    def __init__(self, name, stream_type, conflate):
      self.name = name
      self.stream_type = stream_type
      self.conflate = conflate
      clients.append(self)

  monkeypatch.setattr(big_cameraview, "VisionIpcClient", FakeClient)
  view.switch_stream(big_cameraview.VisionStreamType.VISION_STREAM_ROAD)

  assert clients == []
  assert view.client is None
  assert view.stream_type == big_cameraview.VisionStreamType.VISION_STREAM_ROAD
  assert view._target_client is None
  assert view._target_stream_type is None
  assert not view._switching
  assert view._reentry_stream_selected


def test_onroad_reentry_guard_clears_on_first_fresh_frame():
  view = _camera_view()
  view._onroad_reentry_pending = True
  view._reentry_stream_selected = True

  assert view._accept_frame(FakeFrame(frame_id=1, idx=0), packet_frame_id=1)
  assert not view._onroad_reentry_pending
  assert not view._reentry_stream_selected


def test_standalone_camera_reentry_selects_configured_stream():
  view = _camera_view()
  view._switching = False
  view._onroad_reentry_pending = True
  view._reentry_stream_selected = False
  selected = []
  placeholders = []
  view._select_reentry_stream = lambda stream_type: (
    selected.append(stream_type), setattr(view, "_reentry_stream_selected", True)
  )
  view._draw_placeholder = lambda rect: placeholders.append(rect)
  view._ensure_connection = lambda: False

  view._render(object())

  assert selected == [view._stream_type]
  assert len(placeholders) == 1


def test_reused_egl_slot_cannot_move_camera_backwards(monkeypatch):
  monkeypatch.setattr(big_cameraview.cloudlog, "warning", lambda *_args, **_kwargs: None)
  monkeypatch.setattr(big_cameraview, "PC", False)
  view = _camera_view()

  displayed = FakeFrame(frame_id=10, idx=0)
  assert view._accept_frame(displayed, packet_frame_id=10)

  # camerad cycles back to this shared slot while it remains displayed.
  displayed.frame_id = 30
  view._observe_displayed_frame()

  delayed = FakeFrame(frame_id=20, idx=1)
  assert not view._accept_frame(delayed, packet_frame_id=20)
  assert view.frame is displayed
  assert view._last_frame_id == 30
  assert view._regressive_frame_count == 1


def test_texture_camera_accepts_regressive_replay_frame(monkeypatch):
  monkeypatch.setattr(big_cameraview, "PC", True)
  view = _camera_view()

  assert view._accept_frame(FakeFrame(frame_id=1140, idx=0), packet_frame_id=1140)
  rewind = FakeFrame(frame_id=660, idx=1)

  assert view._accept_frame(rewind, packet_frame_id=660)
  assert view.frame is rewind
  assert view._last_frame_id == 660
  assert view._regressive_frame_count == 0


def test_newer_camera_frame_is_accepted():
  view = _camera_view()
  view._last_frame_id = 30
  view._regressive_frame_count = 2
  newer = FakeFrame(frame_id=31, idx=2)

  assert view._accept_frame(newer, packet_frame_id=31)
  assert view.frame is newer
  assert view._last_frame_id == 31
  assert view._regressive_frame_count == 0
  assert view._texture_needs_update


def test_shared_camera_has_upstream_shaders_and_driver_enhancement():
  assert "samplerExternalOES" in big_cameraview.FRAME_FRAGMENT_SHADER_EXTERNAL
  assert "pow(color.rgb, vec3(1.0/1.28))" in big_cameraview.FRAME_FRAGMENT_SHADER_EXTERNAL
  assert "uniform sampler2D texture0" in big_cameraview.FRAME_FRAGMENT_SHADER_YUV
  assert "uniform sampler2D texture1" in big_cameraview.FRAME_FRAGMENT_SHADER_YUV
  assert "uniform int enhance_driver" in big_cameraview.FRAME_FRAGMENT_SHADER_EXTERNAL
  assert "uniform int enhance_driver" in big_cameraview.FRAME_FRAGMENT_SHADER_YUV
  assert "uniform int engaged" not in big_cameraview.FRAME_FRAGMENT_SHADER_EXTERNAL
  assert "uniform int engaged" not in big_cameraview.FRAME_FRAGMENT_SHADER_YUV
  assert hasattr(big_cameraview.CameraView, "_render_egl")
  assert hasattr(big_cameraview.CameraView, "_fallback_to_textures")


def test_shared_camera_falls_back_after_repeated_regressive_frames(monkeypatch):
  monkeypatch.setattr(big_cameraview.cloudlog, "warning", lambda *_args, **_kwargs: None)
  monkeypatch.setattr(big_cameraview, "PC", False)
  view = _camera_view()
  view._use_egl = True
  view.frame = FakeFrame(frame_id=30, idx=0)
  view._last_frame_id = 30
  fallback_reasons = []
  view._fallback_to_textures = fallback_reasons.append

  for frame_id in (20, 19, 18):
    assert not view._accept_frame(FakeFrame(frame_id=frame_id, idx=1), packet_frame_id=frame_id)

  assert fallback_reasons == ["repeated regressive frames"]
  assert view.frame.frame_id == 30


def test_shared_camera_fallback_reloads_texture_backend(monkeypatch):
  view = _camera_view()
  view._use_egl = True
  view.shader = SimpleNamespace(id=1)
  events = []
  view._clear_textures = lambda: events.append("clear")
  view._load_frame_shader = lambda: events.append(("shader", view._use_egl))
  view._initialize_textures = lambda: events.append("textures")
  monkeypatch.setattr(big_cameraview.cloudlog, "error", lambda *_args, **_kwargs: None)
  monkeypatch.setattr(big_cameraview.rl, "unload_shader", lambda _shader: events.append("unload_shader"))

  view._fallback_to_textures("test")

  assert events == ["clear", "unload_shader", ("shader", False), "textures"]
  assert not view._use_egl


def test_connection_retry_does_not_wait_for_advertisement_and_uses_fresh_candidate(monkeypatch):
  view = _camera_view()
  view._name = "camerad"
  view._clear_textures = lambda: None
  view.client = SimpleNamespace(is_connected=lambda: False)
  view._target_client = None
  view._target_stream_type = None
  view._switching = False
  view.available_streams = []
  view.last_connection_attempt = 0.0

  candidates = []

  class FakeClient:
    @staticmethod
    def available_streams(_name, block=False):
      pytest.fail("startup connection waited for stream advertisement")

    def __init__(self, *_args, **_kwargs):
      candidates.append(self)
      self.connected = False
      self.num_buffers = 0

    def is_connected(self):
      return self.connected

    def connect(self, _block):
      return False

  monkeypatch.setattr(big_cameraview, "VisionIpcClient", FakeClient)
  monkeypatch.setattr(big_cameraview.rl, "get_time", lambda: 1.0)

  assert not view._ensure_connection()
  assert view.client is None
  assert len(candidates) == 1

  monkeypatch.setattr(big_cameraview.rl, "get_time", lambda: 1.3)
  assert not view._ensure_connection()
  assert len(candidates) == 2
  assert candidates[0] is not candidates[1]


def test_candidate_is_not_active_until_first_consistent_frame(monkeypatch):
  view = _camera_view()
  view._name = "camerad"
  view._clear_textures = lambda: None
  view._initialize_textures = lambda: None
  view.client = None
  view._target_client = None
  view._target_stream_type = None
  view._switching = False
  view.available_streams = []
  view.last_connection_attempt = 0.0

  class FakeClient:
    @staticmethod
    def available_streams(_name, block=False):
      return [view._stream_type]

    def __init__(self, *_args, **_kwargs):
      self.connected = False
      self.num_buffers = 1
      self.frame_id = -1
      self.frames = [None, FakeFrame(frame_id=42, idx=0)]

    def is_connected(self):
      return self.connected

    def connect(self, _block):
      self.connected = True
      return True

    def recv(self, timeout_ms=0):
      frame = self.frames.pop(0)
      if frame is not None:
        self.frame_id = frame.frame_id
      return frame

  monkeypatch.setattr(big_cameraview, "VisionIpcClient", FakeClient)
  monkeypatch.setattr(big_cameraview.rl, "get_time", lambda: 1.0)

  assert not view._ensure_connection()
  assert view.client is None
  candidate = view._target_client
  assert candidate is not None

  assert view._ensure_connection()
  assert view.client is candidate
  assert view.frame.frame_id == 42
  assert view._target_client is None
  assert not view._switching


def test_inconsistent_candidate_frame_is_discarded(monkeypatch):
  view = _camera_view()
  view._name = "camerad"
  view._clear_textures = lambda: None
  view.client = None
  view._target_client = None
  view._target_stream_type = None
  view._switching = False
  view.available_streams = []
  view.last_connection_attempt = 0.0

  class FakeClient:
    @staticmethod
    def available_streams(_name, block=False):
      return [view._stream_type]

    def __init__(self, *_args, **_kwargs):
      self.connected = False
      self.num_buffers = 1
      self.frame_id = 10

    def is_connected(self):
      return self.connected

    def connect(self, _block):
      self.connected = True
      return True

    def recv(self, timeout_ms=0):
      return FakeFrame(frame_id=9, idx=0)

  monkeypatch.setattr(big_cameraview, "VisionIpcClient", FakeClient)
  monkeypatch.setattr(big_cameraview.rl, "get_time", lambda: 1.0)

  assert not view._ensure_connection()
  assert view.client is None
  assert view._target_client is None
  assert view._target_stream_type == view._stream_type
  assert not view._switching


def test_disconnected_candidate_is_discarded_without_reconnect():
  view = _camera_view()

  class Candidate:
    num_buffers = 1

    def __init__(self):
      self.connected = True

    def is_connected(self):
      return self.connected

    def connect(self, _block):
      pytest.fail("discarded candidate was reconnected")

    def recv(self, timeout_ms=0):
      self.connected = False
      return None

  candidate = Candidate()
  view._target_client = candidate
  view._target_stream_type = view._stream_type
  view._switching = True

  view._handle_switch()

  assert view._target_client is None
  assert not view._switching
  assert view._target_stream_type == view._stream_type


def test_steady_state_packet_content_mismatch_is_rejected():
  view = _camera_view()
  displayed = FakeFrame(frame_id=10, idx=0)
  assert view._accept_frame(displayed, packet_frame_id=10)

  delayed = FakeFrame(frame_id=12, idx=1)
  assert not view._accept_frame(delayed, packet_frame_id=11)
  assert view.frame is displayed
  assert view._last_frame_id == 10


def test_egl_image_creation_failure_is_reported(monkeypatch):
  view = _camera_view()
  view.frame = SimpleNamespace(idx=0, width=1928, height=1208, stride=2048, fd=7, uv_offset=2473984)
  view.egl_texture = SimpleNamespace(id=1)
  view._external_texture_id = 11
  view.egl_images = {}
  monkeypatch.setattr(big_cameraview, "create_egl_image", lambda *_args: None)

  assert not view._render_egl(None, None)
  assert view.egl_images == {}


def test_invalid_egl_texture_is_reported_without_binding(monkeypatch):
  view = _camera_view()
  view.frame = SimpleNamespace(idx=0)
  view.egl_texture = SimpleNamespace(id=0)
  view._external_texture_id = 11
  view.egl_images = {0: object()}
  monkeypatch.setattr(big_cameraview, "bind_egl_image_to_texture",
                      lambda *_args: pytest.fail("invalid EGL texture was bound"))

  assert not view._render_egl(None, None)


def test_invalid_external_texture_is_reported_without_binding(monkeypatch):
  view = _camera_view()
  view.frame = SimpleNamespace(idx=0)
  view.egl_texture = SimpleNamespace(id=7)
  view.egl_images = {0: object()}
  monkeypatch.setattr(big_cameraview, "bind_egl_image_to_texture",
                      lambda *_args: pytest.fail("invalid external texture was bound"))

  assert not view._render_egl(None, None)


def test_egl_render_always_ends_shader_mode(monkeypatch):
  view = _camera_view()
  view.frame = SimpleNamespace(idx=0, width=1928, height=1208)
  view.egl_texture = SimpleNamespace(id=1, width=0, height=0)
  view._external_texture_id = 11
  view.egl_images = {0: object()}
  view.shader = SimpleNamespace(id=1)
  view._update_shader_state = lambda: None
  events = []
  monkeypatch.setattr(big_cameraview, "bind_egl_image_to_texture", lambda *_args: None)
  monkeypatch.setattr(big_cameraview.rl, "begin_shader_mode", lambda *_args: events.append("begin"))
  def fail_draw(*_args):
    raise RuntimeError("draw failed")

  monkeypatch.setattr(big_cameraview.rl, "draw_texture_pro", fail_draw)
  monkeypatch.setattr(big_cameraview.rl, "end_shader_mode", lambda: events.append("end"))

  with pytest.raises(RuntimeError, match="draw failed"):
    view._render_egl(None, None)

  assert events == ["begin", "end"]


def test_egl_render_keeps_external_and_raylib_texture_targets_separate(monkeypatch):
  view = _camera_view()
  image = object()
  view.frame = SimpleNamespace(idx=3, width=1928, height=1208)
  view.egl_texture = SimpleNamespace(id=7, width=1, height=1)
  view._external_texture_id = 11
  view.egl_images = {3: image}
  view.shader = object()
  view._update_shader_state = lambda: None
  bound = []
  drawn = []
  monkeypatch.setattr(big_cameraview, "bind_egl_image_to_texture",
                      lambda texture_id, egl_image: bound.append((texture_id, egl_image)))
  monkeypatch.setattr(big_cameraview.rl, "begin_shader_mode", lambda _shader: None)
  monkeypatch.setattr(big_cameraview.rl, "end_shader_mode", lambda: None)
  monkeypatch.setattr(big_cameraview.rl, "draw_texture_pro", lambda texture, *_args: drawn.append(texture.id))

  assert view._render_egl(None, None)
  assert bound == [(11, image)]
  assert drawn == [7]


def test_driver_enhancement_tracks_active_stream(monkeypatch):
  view = _camera_view()
  view.shader = SimpleNamespace(id=1)
  view._enhance_driver_loc = 2
  view._enhance_driver_val = [0]
  values = []
  monkeypatch.setattr(big_cameraview.rl, "set_shader_value",
                      lambda _shader, _loc, value, _type: values.append(value[0]))

  view._stream_type = big_cameraview.VisionStreamType.VISION_STREAM_ROAD
  view._update_shader_state()
  view._stream_type = big_cameraview.VisionStreamType.VISION_STREAM_DRIVER
  view._update_shader_state()
  view._stream_type = big_cameraview.VisionStreamType.VISION_STREAM_WIDE_ROAD
  view._update_shader_state()

  assert values == [0, 1, 0]


def test_texture_fallback_survives_egl_cleanup_failure(monkeypatch):
  view = _camera_view()
  view._use_egl = True
  view.shader = SimpleNamespace(id=1)
  events = []

  def fail_cleanup():
    raise RuntimeError("cleanup failed")

  view._clear_textures = fail_cleanup
  view._load_frame_shader = lambda: events.append(("shader", view._use_egl))
  view._initialize_textures = lambda: events.append("textures")
  monkeypatch.setattr(big_cameraview.cloudlog, "error", lambda *_args, **_kwargs: None)
  monkeypatch.setattr(big_cameraview.cloudlog, "exception", lambda *_args, **_kwargs: None)
  monkeypatch.setattr(big_cameraview.rl, "unload_shader", lambda _shader: events.append("unload_shader"))

  view._fallback_to_textures("test")

  assert not view._use_egl
  assert events == ["unload_shader", ("shader", False), "textures"]
