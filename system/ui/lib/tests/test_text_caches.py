from types import SimpleNamespace

from openpilot.system.ui.lib import text_measure, wrap_text


def _fake_font(font_id: int = 1):
  return SimpleNamespace(texture=SimpleNamespace(id=font_id))


def test_measure_cache_hits_and_is_bounded(monkeypatch):
  calls = []

  def fake_measure(font, text, font_size, spacing):
    calls.append((font.texture.id, text, font_size, spacing))
    return SimpleNamespace(x=float(len(text)), y=1.0)

  monkeypatch.setattr(text_measure, "font_fallback", lambda font: font)
  monkeypatch.setattr(text_measure, "find_emoji", lambda text: [])
  monkeypatch.setattr(text_measure.rl, "measure_text_ex", fake_measure)
  text_measure._cache.clear()

  font = _fake_font()

  first = text_measure.measure_text_cached(font, "hello", 10)
  second = text_measure.measure_text_cached(font, "hello", 10)
  assert second is first
  assert len(calls) == 1

  for i in range(text_measure._CACHE_MAXSIZE + 50):
    text_measure.measure_text_cached(font, f"text-{i}", 10)

  assert len(text_measure._cache) == text_measure._CACHE_MAXSIZE

  calls.clear()
  evicted = text_measure.measure_text_cached(font, "hello", 10)
  assert len(calls) == 1
  assert evicted is not first
  assert (evicted.x, evicted.y) == (first.x, first.y)


def test_wrap_cache_hits_and_is_bounded(monkeypatch):
  monkeypatch.setattr(wrap_text, "font_fallback", lambda font: font)
  monkeypatch.setattr(wrap_text, "measure_text_cached", lambda font, text, font_size, spacing=0: SimpleNamespace(x=float(len(text)), y=1.0))
  wrap_text._cache.clear()

  font = _fake_font()

  first = wrap_text.wrap_text(font, "some words here", 20, 1000)
  second = wrap_text.wrap_text(font, "some words here", 20, 1000)
  assert second is first

  for i in range(wrap_text._CACHE_MAXSIZE + 25):
    wrap_text.wrap_text(font, f"unique text {i}", 20, 1000)

  assert len(wrap_text._cache) == wrap_text._CACHE_MAXSIZE
