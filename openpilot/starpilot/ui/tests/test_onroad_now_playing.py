from types import SimpleNamespace

import pytest

TRACK = {'source': 'spotify', 'status': 'playing', 'title': 'Midnight City', 'artist': 'M83', 'album': '',
         'durationMs': 200000, 'position': {'ms': 50000, 'at': 0, 'speed': 0.0}}


@pytest.fixture
def widget(monkeypatch):
  from openpilot.starpilot.ui import onroad_now_playing
  from openpilot.starpilot.ui.onroad_now_playing import NowPlayingWidget
  drawn = []
  for name in ('draw_rectangle_rounded', 'draw_triangle', 'draw_circle_v'):
    monkeypatch.setattr(onroad_now_playing.rl, name, lambda *args, name=name: drawn.append((name, args)))
  texts = []
  fonts = SimpleNamespace(measure=lambda text, role, size: SimpleNamespace(width=len(text) * size * .5),
                          draw=lambda text, *args: texts.append(text))
  return NowPlayingWidget(fonts, clock=lambda: 0.0), drawn, texts


def state(enabled=True, opacity=85, alert='none'):
  return SimpleNamespace(alert=SimpleNamespace(size=alert),
                         customization={'layouts': {'large': {'now_playing': {'x': 10, 'y': 20, 'enabled': enabled, 'opacity': opacity}}}})


def test_draws_text_and_background_with_the_chosen_opacity(widget):
  card, drawn, texts = widget
  card.track = TRACK
  card.render(state(opacity=50))
  assert texts == ['Midnight City', 'M83']
  assert drawn[0][0] == 'draw_rectangle_rounded' and drawn[0][1][3].a == round(235 * .5)


def test_paused_shows_a_play_mark_and_playing_shows_pause_bars(widget):
  card, drawn, _ = widget
  card.track = {**TRACK, 'status': 'paused'}
  card.render(state())
  assert any(name == 'draw_triangle' for name, _ in drawn)
  drawn.clear()
  card.track = TRACK
  card.render(state())
  assert not any(name == 'draw_triangle' for name, _ in drawn)


@pytest.mark.parametrize('current', [state(enabled=False), state(alert='full')])
def test_hidden_when_disabled_or_an_alert_is_up(widget, current):
  card, drawn, texts = widget
  card.track = TRACK
  card.render(current)
  assert drawn == [] and texts == []


def test_nothing_drawn_without_a_track(widget):
  card, drawn, texts = widget
  card.render(state())
  assert drawn == [] and texts == []
