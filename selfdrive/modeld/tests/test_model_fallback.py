import pytest

from openpilot.selfdrive.modeld import modeld


class FakeParams:
  def __init__(self):
    self.values = {}

  def put(self, key, value):
    self.values[key] = value


@pytest.mark.parametrize(("model_output", "dropped_frames", "external_gpu_active", "expected"), [
  (object(), 0, False, True),
  (object(), 1, False, False),
  (object(), 2, False, False),
  (object(), 0, True, True),
  (object(), 1, True, False),
  (object(), 2, True, False),
  (None, 0, False, False),
  (None, 1, True, False),
])
def test_model_output_is_suppressed_after_vipc_drop_for_both_runtimes(model_output, dropped_frames, external_gpu_active, expected):
  assert modeld._should_publish_model_output(model_output, dropped_frames, external_gpu_active) is expected


def test_incompatible_downloaded_model_falls_back_to_builtin(monkeypatch):
  calls = []
  builtin_model = object()

  def load_model(cam_w, cam_h, external_gpu_active, **kwargs):
    calls.append((cam_w, cam_h, external_gpu_active, kwargs.get("model_id_override")))
    if len(calls) == 1:
      raise TypeError("incompatible artifact")
    return builtin_model

  params = FakeParams()
  monkeypatch.setattr(modeld, "ModelState", load_model)
  monkeypatch.setattr(modeld.cloudlog, "exception", lambda *_args, **_kwargs: None)

  assert modeld._load_model_state(1928, 1208, "custom-model", False, params) is builtin_model
  assert calls == [
    (1928, 1208, False, "custom-model"),
    (1928, 1208, False, modeld.BUILTIN_MODEL_KEY),
  ]
  assert params.values == {
    "Model": modeld.BUILTIN_MODEL_KEY,
    "DrivingModel": modeld.BUILTIN_MODEL_KEY,
    "DrivingModelName": "Regret Driven Framework V4",
  }


def test_builtin_model_load_failure_is_not_hidden(monkeypatch):
  monkeypatch.setattr(modeld, "ModelState", lambda *_args, **_kwargs: (_ for _ in ()).throw(TypeError("bad builtin")))

  with pytest.raises(TypeError, match="bad builtin"):
    modeld._load_model_state(1928, 1208, modeld.BUILTIN_MODEL_KEY, False, FakeParams())
