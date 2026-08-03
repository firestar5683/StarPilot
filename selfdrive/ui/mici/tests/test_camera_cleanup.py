import gc
from types import SimpleNamespace
import weakref

import pytest

from openpilot.selfdrive.ui.onroad import cameraview as big_cameraview
from openpilot.selfdrive.ui.onroad import augmented_road_view as big_augmented_road_view
from openpilot.selfdrive.ui.mici.onroad import augmented_road_view as mici_augmented_road_view


def test_road_transition_releases_camera_buffers(monkeypatch):
  module = big_cameraview

  class FakeClient:
    pass

  view = module.CameraView.__new__(module.CameraView)
  old_client = FakeClient()
  old_client_ref = weakref.ref(old_client)
  view._name = "camerad"
  view._stream_type = object()
  view.client = old_client
  view.frame = None
  view.available_streams = [object()]
  view._target_client = FakeClient()
  view._target_stream_type = object()
  view._switching = True
  view._texture_needs_update = False
  view._regressive_frame_count = 2
  view.last_connection_attempt = 123.0
  view._closed = True
  cleared = []
  view._clear_textures = lambda: cleared.append(True)

  del old_client

  view._offroad_transition()
  gc.collect()

  assert old_client_ref() is None
  assert cleared == [True]
  assert view.frame is None
  assert view.available_streams == []
  assert view._target_client is None
  assert view._target_stream_type is None
  assert view._switching is False
  assert view._texture_needs_update
  assert view._regressive_frame_count == 0
  assert view.last_connection_attempt == 0.0


def test_transition_callback_does_not_retain_camera_view(monkeypatch):
  module = big_cameraview

  class FakeClient:
    pass

  callbacks = []
  monkeypatch.setattr(module, "TICI", False)
  monkeypatch.setattr(module, "VisionIpcClient", lambda *_args, **_kwargs: FakeClient())
  monkeypatch.setattr(module.rl, "load_shader_from_memory", lambda *_args: SimpleNamespace(id=1))
  monkeypatch.setattr(module.rl, "get_shader_location", lambda *_args: 0)
  monkeypatch.setattr(module.rl, "unload_shader", lambda *_args: None)
  monkeypatch.setattr(module.ui_state, "add_offroad_transition_callback", callbacks.append)
  monkeypatch.setattr(module.ui_state, "remove_offroad_transition_callback", callbacks.remove)

  view = module.CameraView("camerad", object())
  view_ref = weakref.ref(view)
  assert len(callbacks) == 1

  del view
  gc.collect()

  assert view_ref() is None
  assert callbacks == []


def test_stream_switch_releases_graphics_before_old_client():
  module = big_cameraview

  events = []

  class FakeClient:
    pass

  class FakeFrame:
    pass

  view = module.CameraView.__new__(module.CameraView)
  old_client = FakeClient()
  old_client_finalizer = weakref.finalize(old_client, events.append, "client")
  old_frame = FakeFrame()
  old_frame.frame_id = 10
  old_frame.owner = old_client
  old_frame_finalizer = weakref.finalize(old_frame, events.append, "frame")
  view.client = old_client
  view._target_client = FakeClient()
  view._target_stream_type = object()
  view._stream_type = object()
  view._switching = True
  view.frame = old_frame
  view._regressive_frame_count = 2
  view._texture_needs_update = False
  view._closed = True
  view._clear_textures = lambda: events.append("graphics")
  view._initialize_textures = lambda: events.append("initialize")
  del old_frame
  del old_client

  view._complete_switch(SimpleNamespace(frame_id=11))
  gc.collect()

  assert old_client_finalizer.alive is False
  assert old_frame_finalizer.alive is False
  assert events == ["graphics", "frame", "client", "initialize"]
  assert view._regressive_frame_count == 0


def test_egl_cleanup_deletes_texture_before_images(monkeypatch):
  module = big_cameraview

  events = []
  view = module.CameraView.__new__(module.CameraView)
  view.texture_y = None
  view.texture_uv = None
  view.egl_texture = SimpleNamespace(id=7)
  view._external_texture_id = 11
  view.egl_images = {0: object(), 1: object()}
  view._closed = True

  view._use_egl = True

  monkeypatch.setattr(module.rl, "unload_texture", lambda _texture: events.append("texture"))
  monkeypatch.setattr(module, "destroy_external_texture", lambda _texture: events.append("external"))
  monkeypatch.setattr(module, "destroy_egl_image", lambda _image: events.append("image"))

  view._clear_textures()

  assert events == ["external", "texture", "image", "image"]
  assert view.egl_texture is None
  assert view._external_texture_id == 0
  assert view.egl_images == {}


def test_egl_cleanup_synchronizes_after_backend_switch(monkeypatch):
  module = big_cameraview

  events = []
  view = module.CameraView.__new__(module.CameraView)
  view.texture_y = None
  view.texture_uv = None
  view.egl_texture = SimpleNamespace(id=7)
  view._external_texture_id = 11
  view.egl_images = {0: object()}
  view._use_egl = False
  view._closed = True

  monkeypatch.setattr(module, "is_egl_initialized", lambda: True)
  monkeypatch.setattr(module.rl, "rl_draw_render_batch_active", lambda: events.append("flush"))
  monkeypatch.setattr(module, "finish_gl", lambda: events.append("finish"))
  monkeypatch.setattr(module.rl, "unload_texture", lambda _texture: events.append("texture"))
  monkeypatch.setattr(module, "destroy_external_texture", lambda _texture: events.append("external"))
  monkeypatch.setattr(module, "destroy_egl_image", lambda _image: events.append("image"))

  view._clear_textures()

  assert events == ["flush", "finish", "external", "texture", "image"]


def test_reverse_activation_cancels_mismatched_pending_switch():
  view = mici_augmented_road_view.AugmentedRoadView.__new__(mici_augmented_road_view.AugmentedRoadView)
  view._stream_type = mici_augmented_road_view.DRIVER_CAM
  view._target_stream_type = mici_augmented_road_view.WIDE_CAM
  view._target_client = object()
  view._switching = True
  view._closed = True
  view._update_reverse_driver_camera_state = lambda: True

  view._switch_stream_if_needed(None, mici_augmented_road_view.CAMERA_VIEW_AUTO)

  assert view._target_client is None
  assert view._target_stream_type is None
  assert not view._switching


def test_onroad_reentry_keeps_matching_candidate_alive():
  for module in (big_augmented_road_view, mici_augmented_road_view):
    view = module.AugmentedRoadView.__new__(module.AugmentedRoadView)
    candidate = object()
    view._stream_type = module.ROAD_CAM
    view._target_stream_type = module.ROAD_CAM
    view._target_client = candidate
    view._switching = True
    view._onroad_reentry_pending = True
    view._reentry_stream_selected = True
    view.available_streams = [module.ROAD_CAM]
    view._closed = True
    view._update_reverse_driver_camera_state = lambda: False
    view._refresh_available_streams = lambda: pytest.fail("reentry selection was repeated")

    view._switch_stream_if_needed(None, module.CAMERA_VIEW_STANDARD)

    assert view._target_client is candidate
    assert view._target_stream_type == module.ROAD_CAM
    assert view._switching


def test_onroad_transition_marks_camera_reentry(monkeypatch):
  module = big_cameraview

  class FakeClient:
    pass

  view = module.CameraView.__new__(module.CameraView)
  view._name = "camerad"
  view._stream_type = object()
  view.client = FakeClient()
  view.frame = None
  view.available_streams = []
  view._target_client = None
  view._target_stream_type = None
  view._switching = False
  view._texture_needs_update = False
  view._regressive_frame_count = 1
  view._closed = True
  view._onroad_reentry_pending = False
  view._reentry_stream_selected = False
  view._clear_textures = lambda: None

  monkeypatch.setattr(module.ui_state, "is_onroad", lambda: True)

  view._offroad_transition()

  assert view._onroad_reentry_pending
  assert not view._reentry_stream_selected
