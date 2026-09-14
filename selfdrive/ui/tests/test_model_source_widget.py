from types import SimpleNamespace

from openpilot.selfdrive.ui.onroad.starpilot.widgets import model_source


class FakeSubMaster:
  def __init__(self, *, selfdrive_frame: int, model_frame: int, model_alive: bool, enabled: bool):
    self.recv_frame = {"selfdriveState": selfdrive_frame, "modelV2": model_frame}
    self.alive = {"modelV2": model_alive}
    self._selfdrive_state = SimpleNamespace(enabled=enabled)

  def __getitem__(self, service: str):
    assert service == "selfdriveState"
    return self._selfdrive_state


def test_model_source_status_prioritizes_loading_then_fallback_then_failure():
  status = model_source.ModelSourceWidget._status_for

  assert status(True, True, True) is model_source.ModelSourceStatus.LOADING
  assert status(False, True, True) is model_source.ModelSourceStatus.FALLBACK_ENGAGED
  assert status(False, False, True) is model_source.ModelSourceStatus.FAILED
  assert status(False, False, False) is model_source.ModelSourceStatus.ACTIVE


def test_model_source_failure_detection_matches_the_backend_state_contract():
  failed = model_source.ModelSourceWidget._big_model_failed

  assert failed(False, True, False, True)
  assert failed(True, False, False, True)
  assert failed(True, True, True, False)
  assert not failed(True, True, False, True)


def test_model_source_shows_a_pending_big_model_as_still_loading():
  # The big model loads in the background, so "loaded, waiting for a disengage" must read
  # as in-progress rather than as a failure.
  status = model_source.ModelSourceWidget._status_for
  failed = model_source.ModelSourceWidget._big_model_failed

  assert status(False, False, False, True) is model_source.ModelSourceStatus.LOADING
  assert not failed(False, True, False, True, True)
  # Chestnut going away while pending is still a genuine failure.
  assert failed(False, False, False, True, True)


def test_model_source_latches_small_model_engagement_until_the_big_model_recovers(monkeypatch):
  widget = object.__new__(model_source.ModelSourceWidget)
  widget._small_model_engaged = False
  widget._engaged = False
  widget._fade_time = 0.0
  widget._status = None

  sm = FakeSubMaster(selfdrive_frame=11, model_frame=11, model_alive=True, enabled=True)
  monkeypatch.setattr(
    model_source,
    "ui_state",
    SimpleNamespace(
      sm=sm,
      started_frame=10,
      usbgpu=True,
      usbgpu_compiled=True,
      usbgpu_active=False,
      usbgpu_loading=False,
      usbgpu_pending=False,
    ),
  )
  monkeypatch.setattr(model_source.rl, "get_time", lambda: 42.0)

  widget._update_state()

  assert widget._small_model_engaged
  assert widget._status is model_source.ModelSourceStatus.FALLBACK_ENGAGED
  assert widget._fade_time == 42.0

  model_source.ui_state.usbgpu_active = True
  widget._update_state()

  assert not widget._small_model_engaged
  assert widget._status is model_source.ModelSourceStatus.ACTIVE


def test_model_source_uses_the_approved_big_ui_footprint():
  assert model_source.ModelSourceWidget.SIZE == (300.0, 208.0)
  assert model_source.ModelSourceWidget.ICON_SIZES[model_source.ModelSourceStatus.FAILED] == (300, 176)


def test_model_source_loads_and_centers_the_scaled_assets(monkeypatch):
  calls = []

  def texture(path, width, height):
    calls.append((path, width, height))
    return SimpleNamespace(width=width, height=height)

  monkeypatch.setattr(model_source, "gui_app", SimpleNamespace(target_fps=60, texture=texture))
  widget = model_source.ModelSourceWidget()
  widget._status = model_source.ModelSourceStatus.FAILED
  widget._shown_status = model_source.ModelSourceStatus.FAILED
  widget._fade_time = 1.0
  rendered = []
  monkeypatch.setattr(model_source.rl, "get_time", lambda: 2.0)
  monkeypatch.setattr(model_source.rl, "draw_texture_ex", lambda *_args: rendered.append(_args))

  widget._render(model_source.rl.Rectangle(1830, 436, 300, 208))

  assert calls == [
    ("icons_mici/egpu_loading.png", 240, 176),
    ("icons_mici/egpu_green.png", 240, 176),
    ("icons_mici/egpu_orange.png", 300, 176),
    ("icons_mici/egpu_crossed.png", 240, 208),
  ]
  assert not widget.blocks_pointer
  assert rendered[0][1].x == 1830
  assert rendered[0][1].y == 452
