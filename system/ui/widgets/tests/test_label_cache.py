from types import SimpleNamespace

from openpilot.system.ui.widgets import label as label_mod


def _make_label(monkeypatch, width=100.0, text="hello", font_size=20, text_padding=0, elide_right=False, icon=None):
  wrap_calls = []
  measure_calls = []

  def fake_wrap(font, value, size, max_width, spacing=0):
    wrap_calls.append(value)
    return ["line"]

  def fake_measure(font, value, size, spacing=0):
    measure_calls.append(value)
    return SimpleNamespace(x=float(len(value)), y=float(len(value)) + 1)

  monkeypatch.setattr(label_mod, "wrap_text", fake_wrap)
  monkeypatch.setattr(label_mod, "measure_text_cached", fake_measure)
  monkeypatch.setattr(label_mod, "find_emoji", lambda value: [])
  monkeypatch.setattr(label_mod.gui_app, "font", lambda *args, **kwargs: None)

  widget = label_mod.Label(text, font_size=font_size, text_padding=text_padding,
                           elide_right=elide_right, icon=icon)
  widget._rect.width = width
  wrap_calls.clear()
  measure_calls.clear()
  return widget, wrap_calls, measure_calls


def test_update_text_skips_when_inputs_unchanged(monkeypatch):
  widget, wrap_calls, _ = _make_label(monkeypatch)

  widget._update_text(widget._text)
  widget._update_text(widget._text)

  assert wrap_calls == ["hello"]


def test_update_text_recomputes_when_text_changes(monkeypatch):
  widget, wrap_calls, _ = _make_label(monkeypatch)

  widget._update_text(widget._text)
  widget._update_text("world")

  assert wrap_calls == ["hello", "world"]


def test_update_text_recomputes_when_callable_text_changes(monkeypatch):
  widget, wrap_calls, _ = _make_label(monkeypatch)
  value = {"text": "hello"}
  widget._text = lambda: value["text"]

  widget._update_text(widget._text)
  widget._update_text(widget._text)
  assert wrap_calls == ["hello"]

  value["text"] = "world"
  widget._update_text(widget._text)
  assert wrap_calls == ["hello", "world"]


def test_update_text_recomputes_when_width_changes(monkeypatch):
  widget, wrap_calls, _ = _make_label(monkeypatch)

  widget._update_text(widget._text)
  widget._rect.width = 250.0
  widget._update_text(widget._text)

  assert wrap_calls == ["hello", "hello"]


def test_update_text_recomputes_when_font_size_changes(monkeypatch):
  widget, wrap_calls, _ = _make_label(monkeypatch)

  widget._update_text(widget._text)
  widget._font_size = 40
  widget._update_text(widget._text)

  assert wrap_calls == ["hello", "hello"]


def test_update_text_recomputes_when_text_padding_changes(monkeypatch):
  widget, wrap_calls, _ = _make_label(monkeypatch)

  widget._update_text(widget._text)
  widget._text_padding = 5
  widget._update_text(widget._text)

  assert wrap_calls == ["hello", "hello"]


def test_elide_right_branch_elides_overflowing_text(monkeypatch):
  widget, wrap_calls, measure_calls = _make_label(monkeypatch, width=10.0, text="abcdefghijklm", elide_right=True)

  widget._update_text(widget._text)

  assert wrap_calls == []
  assert widget._text_wrapped == ["abcdefg..."]

  measure_count = len(measure_calls)
  widget._update_text(widget._text)
  assert len(measure_calls) == measure_count


def test_elide_right_branch_accounts_for_icon_width(monkeypatch):
  icon = SimpleNamespace(width=5, height=5)
  widget, _, _ = _make_label(monkeypatch, width=30.0, text="abcdefghijklm", elide_right=True, icon=icon)

  widget._update_text(widget._text)

  assert widget._text_wrapped == ["abcdefg..."]


def test_update_text_cached_result_equals_recomputed_result(monkeypatch):
  widget, _, _ = _make_label(monkeypatch)
  widget._update_text(widget._text)
  cached = (list(widget._text_wrapped), list(widget._text_size), list(widget._emojis))

  widget._update_text(widget._text)
  assert (list(widget._text_wrapped), list(widget._text_size), list(widget._emojis)) == cached

  widget._cached_text_key = None
  widget._update_text(widget._text)
  assert (list(widget._text_wrapped), list(widget._text_size), list(widget._emojis)) == cached
