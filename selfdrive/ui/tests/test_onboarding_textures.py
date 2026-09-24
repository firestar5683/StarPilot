import threading

from openpilot.selfdrive.ui.layouts import onboarding


def test_release_unloads_textures_and_images_once(monkeypatch):
  unloaded = []
  monkeypatch.setattr(onboarding.rl, "unload_texture", lambda texture: unloaded.append(("texture", texture)))
  monkeypatch.setattr(onboarding.rl, "unload_image", lambda image: unloaded.append(("image", image)))

  guide = object.__new__(onboarding.TrainingGuide)
  guide._lock = threading.Lock()
  guide._released = False
  guide._textures = ["texture-0", "texture-1"]
  guide._image_objs = ["image-0"]

  guide.release()

  assert guide._textures == []
  assert guide._image_objs == []
  assert unloaded == [("texture", "texture-0"), ("texture", "texture-1"), ("image", "image-0")]

  # releasing again must not unload anything twice
  guide.release()
  assert unloaded == [("texture", "texture-0"), ("texture", "texture-1"), ("image", "image-0")]


def test_preload_thread_does_not_append_after_release(monkeypatch):
  unloaded = []
  monkeypatch.setattr(onboarding.gui_app, "_load_image_from_path", lambda path, *args, **kwargs: f"image:{path}")
  monkeypatch.setattr(onboarding.rl, "unload_image", lambda image: unloaded.append(image))

  guide = object.__new__(onboarding.TrainingGuide)
  guide._lock = threading.Lock()
  guide._released = False
  guide._textures = []
  guide._image_objs = []
  guide._image_paths = ["a.png", "b.png", "c.png"]

  guide.release()
  guide._preload_thread()

  assert guide._image_objs == []
  assert unloaded == ["image:b.png"]


def test_hide_event_releases_textures(monkeypatch):
  unloaded = []
  monkeypatch.setattr(onboarding.rl, "unload_texture", lambda texture: unloaded.append(texture))
  monkeypatch.setattr(onboarding.rl, "unload_image", lambda image: None)

  guide = object.__new__(onboarding.TrainingGuide)
  guide._children = []
  guide._lock = threading.Lock()
  guide._released = False
  guide._textures = ["texture-0"]
  guide._image_objs = []

  guide.hide_event()

  assert guide._released
  assert guide._textures == []
  assert unloaded == ["texture-0"]


def test_onboarding_window_registers_guide_as_child(monkeypatch):
  created = []

  class FakeGuide:
    def __init__(self, completed_callback=None):
      self.rendered = False
      created.append(self)

    def render(self, rect):
      self.rendered = True

  monkeypatch.setattr(onboarding, "TrainingGuide", FakeGuide)

  window = object.__new__(onboarding.OnboardingWindow)
  window._children = []
  window._training_guide = None
  window._state = onboarding.OnboardingState.ONBOARDING
  window._rect = onboarding.rl.Rectangle(0, 0, 100, 100)

  window._render(None)

  assert created == [window._training_guide]
  assert window._training_guide in window._children
  assert window._training_guide.rendered


def test_onboarding_window_hide_event_releases_child_guide(monkeypatch):
  unloaded = []
  monkeypatch.setattr(onboarding.rl, "unload_texture", lambda texture: unloaded.append(texture))
  monkeypatch.setattr(onboarding.rl, "unload_image", lambda image: None)

  guide = object.__new__(onboarding.TrainingGuide)
  guide._children = []
  guide._lock = threading.Lock()
  guide._released = False
  guide._textures = ["texture-0"]
  guide._image_objs = []

  window = object.__new__(onboarding.OnboardingWindow)
  window._children = []
  window._child(guide)

  window.hide_event()

  assert guide._released
  assert unloaded == ["texture-0"]
