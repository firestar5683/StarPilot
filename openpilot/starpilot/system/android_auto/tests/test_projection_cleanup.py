"""Projection retries must not strand native encoders, renderers or workers."""
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from openpilot.starpilot.system.android_auto import supervisor, hw_encoder, display_profile, media_audio, media_status, nav_status
from openpilot.starpilot.system.android_auto.identity import DEFAULT_CONFIG


@pytest.fixture
def projection(monkeypatch):
  owner = supervisor.Supervisor.__new__(supervisor.Supervisor)
  owner.config = dict(DEFAULT_CONFIG, view='unavailable')
  owner._stop = Event()
  owner._synthetic = False
  owner._renderer_command = owner._frame_path = owner._car_frame_path = owner._touch_path = owner._control_path = None
  owner._stage = owner._set = owner.log = Mock()
  owner._stream = Mock()
  mode = SimpleNamespace(width=800, height=480, fps=30, margin_width=0, margin_height=0, as_dict=dict)
  session = Mock(audio=None, nav=None)
  session.start.return_value = mode
  encoder, source, watch = Mock(), Mock(label='car'), Mock()
  audio, nav = Mock(), Mock()
  monkeypatch.setattr(supervisor, 'ProjectionSession', Mock(return_value=session))
  monkeypatch.setattr(hw_encoder, 'create_encoder', Mock(return_value=(encoder, 30)))
  monkeypatch.setattr(display_profile, 'record_screen', Mock())
  source_factory = Mock(return_value=source)
  monkeypatch.setattr(supervisor, 'ViewSource', source_factory)
  monkeypatch.setattr(supervisor, 'LinkWatch', Mock(return_value=watch))
  monkeypatch.setattr(media_audio.MediaAudio, 'create', Mock(return_value=audio))
  monkeypatch.setattr(media_status.MediaStatus, 'create', Mock(return_value=None))
  monkeypatch.setattr(nav_status.NavStatus, 'create', Mock(return_value=nav))
  def run():
    owner._project(None, Mock(), SimpleNamespace(cert='cert', key='key'), connect=Mock())
  return SimpleNamespace(owner=owner, session=session, encoder=encoder, source=source, watch=watch,
                         audio=audio, nav=nav, source_factory=source_factory, run=run)


def test_failed_view_setup_releases_encoder_on_every_retry(projection):
  p = projection
  p.source_factory.side_effect = RuntimeError('view setup failed')
  for _ in range(20):
    with pytest.raises(RuntimeError, match='view setup failed'):
      p.run()
  assert p.encoder.close.call_count == 20
  p.owner._stream.assert_not_called()


def test_failed_watch_start_releases_view_and_encoder(projection):
  p = projection
  p.watch.start.side_effect = RuntimeError('thread start failed')
  with pytest.raises(RuntimeError, match='thread start failed'):
    p.run()
  for close in (p.watch.stop, p.source.close, p.encoder.close):
    close.assert_called_once()


@pytest.mark.parametrize('failing', ['audio', 'nav', 'source'])
def test_one_cleanup_failure_still_releases_every_resource(projection, failing):
  p = projection
  getattr(p, failing).close.side_effect = RuntimeError('cleanup failed')
  with pytest.raises(RuntimeError, match='cleanup failed'):
    p.run()
  for close in (p.audio.close, p.nav.close, p.watch.stop, p.source.close, p.encoder.close):
    close.assert_called_once()


def test_stream_failure_and_stop_release_resources_and_shutdown(projection):
  p = projection
  p.owner._stop.set()
  p.owner._stream.side_effect = RuntimeError('stream failed')
  with pytest.raises(RuntimeError, match='stream failed'):
    p.run()
  for close in (p.audio.close, p.nav.close, p.watch.stop, p.source.close, p.encoder.close, p.session.shutdown):
    close.assert_called_once()


def test_stream_already_closed_optional_services_are_not_closed_twice(projection):
  p = projection
  def stream(*args):
    p.audio.close()
    p.nav.close()
    p.session.audio = p.session.nav = None
  p.owner._stream.side_effect = stream
  p.run()
  p.audio.close.assert_called_once()
  p.nav.close.assert_called_once()
  p.encoder.close.assert_called_once()
