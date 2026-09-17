from types import SimpleNamespace

from openpilot.system.ui.widgets import label as label_mod


def _make_label(monkeypatch, width=100.0, text="hello", font_size=20):
  wrap_calls = []
  monkeypatch.setattr(label_mod, "wrap_text", lambda font, value, size, max_width, spacing=0: wrap_calls.append(value) or ["line"])
  monkeypatch.setattr(label_mod, "measure_text_cached", lambda *args, **kwargs: SimpleNamespace(x=1.0, y=1.0))
  monkeypatch.setattr(label_mod, "find_emoji", lambda value: [])

  widget = object.__new__(label_mod.Label)
  widget._text = text
  widget._font = None
  widget._font_size = font_size
  widget._text_padding = 0
  widget._elide_right = False
  widget._icon = None
  widget._rect = SimpleNamespace(width=width)
  widget._cached_text_key = None
  return widget, wrap_calls


def test_update_text_skips_when_inputs_unchanged(monkeypatch):
  widget, wrap_calls = _make_label(monkeypatch)

  widget._update_text(widget._text)
  widget._update_text(widget._text)

  assert wrap_calls == ["hello"]


def test_update_text_recomputes_when_text_changes(monkeypatch):
  widget, wrap_calls = _make_label(monkeypatch)

  widget._update_text(widget._text)
  widget._update_text("world")

  assert wrap_calls == ["hello", "world"]


def test_update_text_recomputes_when_width_changes(monkeypatch):
  widget, wrap_calls = _make_label(monkeypatch)

  widget._update_text(widget._text)
  widget._rect.width = 250.0
  widget._update_text(widget._text)

  assert wrap_calls == ["hello", "hello"]


def test_update_text_recomputes_when_font_size_changes(monkeypatch):
  widget, wrap_calls = _make_label(monkeypatch)

  widget._update_text(widget._text)
  widget._font_size = 40
  widget._update_text(widget._text)

  assert wrap_calls == ["hello", "hello"]
