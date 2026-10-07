from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import pytest

from openpilot.starpilot.ui.onroad_navigation_favorites import NavigationFavorites


@pytest.mark.parametrize('key', ['nav_home', 'nav_work'])
def test_card_changes_to_end_navigation_only_for_its_destination(key):
  fonts = Mock()
  fonts.measure.return_value = NS(width=200)
  card = NavigationFavorites(fonts)
  state = NS(customization={'layouts': {'large': {key: {'x': 100, 'y': 200, 'enabled': True}}}}, alert=NS(size='none'))
  label = key.removeprefix('nav_')
  place = {'id': label, 'label': label}
  card.document = {'favorites': [place], 'destination': None, 'enabled': True, 'token': 'key'}
  with patch('pyray.draw_rectangle_rounded'), patch('pyray.draw_rectangle_rounded_lines_ex'):
    card.render(key, state)
    assert [call.args[0] for call in fonts.draw.call_args_list] == [label.title(), 'Navigate']
    fonts.draw.reset_mock()
    card.document['destination'] = place
    card.render(key, state)
    assert [call.args[0] for call in fonts.draw.call_args_list] == ['End navigation', label.title()]
    fonts.draw.reset_mock()
    card.document['destination'] = {'id': 'another-place'}
    card.render(key, state)
    assert fonts.draw.call_args_list[0].args[0] == label.title()
    for change in ['alert', 'removed']:
      fonts.draw.reset_mock()
      state.alert.size = 'full' if change == 'alert' else 'none'
      state.customization['layouts']['large'][key]['enabled'] = change != 'removed'
      card.render(key, state)
      fonts.draw.assert_not_called()


def test_missing_favorite_shows_setup_hint():
  fonts = Mock()
  fonts.measure.return_value = NS(width=200)
  card = NavigationFavorites(fonts)
  state = NS(customization={'layouts': {'large': {'nav_home': {'x': 100, 'y': 200, 'enabled': True}}}}, alert=NS(size='none'))
  with patch('pyray.draw_rectangle_rounded'), patch('pyray.draw_rectangle_rounded_lines_ex'):
    card.render('nav_home', state)
  assert [call.args[0] for call in fonts.draw.call_args_list] == ['Home', 'Set in Galaxy']
