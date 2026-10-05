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


def test_release_while_preload_is_loading_discards_pending_image(monkeypatch):
  loading, resume = threading.Event(), threading.Event()
  unloaded = []
  def load(path):
    loading.set()
    assert resume.wait(2)
    return path
  monkeypatch.setattr(onboarding.gui_app, '_load_image_from_path', load)
  monkeypatch.setattr(onboarding.rl, 'unload_image', unloaded.append)
  guide = object.__new__(onboarding.TrainingGuide)
  guide._lock, guide._released = threading.Lock(), False
  guide._textures, guide._image_objs = [], []
  guide._image_paths = ['first', 'pending', 'unused']
  thread = threading.Thread(target=guide._preload_thread)
  thread.start()
  try:
    assert loading.wait(2)
    guide.release()
  finally:
    resume.set()
    thread.join(2)
  assert not thread.is_alive()
  assert guide._image_objs == []
  assert unloaded == ['pending']


def test_first_texture_is_private_and_settings_review_constructs_fresh(monkeypatch):
  from openpilot.selfdrive.ui.layouts.settings import device
  monkeypatch.setattr(onboarding.TrainingGuide, '_load_image_paths',
                      lambda self: setattr(self, '_image_paths', ['first']))
  monkeypatch.setattr(onboarding.gui_app, '_load_image_from_path', lambda path: path)
  monkeypatch.setattr(onboarding.gui_app, '_load_texture_from_image', lambda image: 'private:' + image)
  def shared_texture(*args, **kwargs):
    raise AssertionError('Shared texture cache used')
  monkeypatch.setattr(onboarding.gui_app, 'texture', shared_texture)
  monkeypatch.setattr(onboarding.rl, 'unload_texture', lambda texture: None)
  guides = []
  monkeypatch.setattr(device.gui_app, 'push_widget', guides.append)
  owner = object.__new__(device.DeviceLayout)
  device.DeviceLayout._on_review_training_guide(owner)
  guides[0].hide_event()
  device.DeviceLayout._on_review_training_guide(owner)
  assert guides[0] is not guides[1]
  assert guides[0]._textures == []
  assert guides[1]._textures == ['private:first']
  guides[1].hide_event()
