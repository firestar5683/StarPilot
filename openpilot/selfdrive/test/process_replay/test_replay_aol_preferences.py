import pytest

from openpilot.selfdrive.test.process_replay.process_replay import generate_params_config, get_custom_params_from_lr


def test_historical_replay_explicitly_preserves_pre_aol_scenario():
  assert generate_params_config()['AlwaysOnLateral'] is False
  assert generate_params_config(lr=[])['AlwaysOnLateral'] is False


@pytest.mark.parametrize('value', [True, False, b'1', b'0'])
def test_explicit_replay_aol_choice_overrides_historical_default(value):
  assert generate_params_config(custom_params={'AlwaysOnLateral': value})['AlwaysOnLateral'] == value


def test_unconverted_recorded_settings_are_not_silently_seeded():
  with pytest.raises(ValueError, match='source schema provenance'):
    get_custom_params_from_lr([])
