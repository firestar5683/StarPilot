import pytest

from openpilot.starpilot.system.android_auto import hw_encoder, supervisor


def test_comma_session_requires_hardware_even_if_configured_auto_or_software(monkeypatch):
  monkeypatch.setattr(supervisor, 'COMMA_HARDWARE', True)
  assert supervisor.encoder_preference('auto') == 'hardware'
  assert supervisor.encoder_preference('software') == 'hardware'
  monkeypatch.setattr(supervisor, 'COMMA_HARDWARE', False)
  assert supervisor.encoder_preference('auto') == 'auto'
  assert supervisor.encoder_preference('software') == 'software'


@pytest.mark.parametrize('failure', ['initialize', 'first_idr'])
def test_required_hardware_failure_never_calls_software_encoder(tmp_path, monkeypatch, failure):
  library = tmp_path / 'libaa_encoder.so'
  library.touch()
  monkeypatch.setattr(hw_encoder, 'LIBRARY', library)
  events = []

  class Hardware:
    def __init__(self, *_args, **_kwargs):
      events.append('hardware_init')
      if failure == 'initialize':
        raise RuntimeError('hardware init failed')

    def encode_rgba(self, _pixels, *, keyframe):
      assert keyframe
      events.append('first_idr')
      raise RuntimeError('hardware first IDR failed')

    def close(self):
      events.append('hardware_closed')

  def software(*_args, **_kwargs):
    events.append('software_init')
    raise AssertionError('software encoder must not start')

  monkeypatch.setattr(hw_encoder, 'HardwareH264Encoder', Hardware)
  monkeypatch.setattr(hw_encoder, 'H264Encoder', software)
  with pytest.raises(RuntimeError, match='hardware .* failed'):
    hw_encoder.create_encoder(1280, 720, preference='hardware', bitrate_kbps=6000,
                              margin_height=0, software_fps=15, log=lambda *_a, **_k: None)
  assert 'software_init' not in events
  assert ('hardware_closed' in events) == (failure == 'first_idr')
