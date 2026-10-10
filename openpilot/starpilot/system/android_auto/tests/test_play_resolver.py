"""No live Google account or APK required for resolver/import regression tests."""
import json
import os
import sys
from unittest.mock import Mock

import pytest

from openpilot.starpilot.system.android_auto import apk_identity, play_resolver

EMAIL = 'user@example.com'
TOKEN = 'oauth2_4/test-secret'
AAS = 'aas_et/test-refresh'
URL = 'https://play.googleapis.com/download/by-token/download?token=private'


def fake_binary(tmp_path, monkeypatch, body):
  binary = tmp_path / 'playlink'
  binary.write_text(f'#!{sys.executable}\n' + body)
  binary.chmod(0o700)
  monkeypatch.setattr(play_resolver, 'BINARY', binary)


def test_pipe_protocol_private_arguments_and_stages(tmp_path, monkeypatch):
  fake_binary(tmp_path, monkeypatch, f'''import sys, json, os
assert len(sys.argv) == 1
assert not any("oauth2_4/" in value for value in os.environ.values())
request = json.load(sys.stdin)
assert request == {{"email": {EMAIL!r}, "token": {TOKEN!r}, "remember": True}}
print('{{"stage":"resolving"}}', flush=True)
print(json.dumps({{"status": "ok", "url": {URL!r}, "aas_token": {AAS!r}}}))
''')
  stages = []
  result = play_resolver.resolve(EMAIL, TOKEN, remember=True, progress=stages.append)
  assert result == {'url': URL, 'aas_token': AAS}
  assert stages[0] == 'authenticating' and stages[-1] == 'resolving'


@pytest.mark.parametrize('body', [
  'import sys; print("oauth2_4/private", file=sys.stderr); sys.exit(1)',
  'print("oauth2_4/private")',
  'print("x" * 40000)',
  'print(\'{"status":"ok","url":"http://127.0.0.1/secret"}\')',
])
def test_failures_never_echo_child_output(tmp_path, monkeypatch, body):
  fake_binary(tmp_path, monkeypatch, body)
  with pytest.raises(play_resolver.PlayError) as error:
    play_resolver.resolve(EMAIL, TOKEN)
  assert 'private' not in str(error.value) and '127.0.0.1' not in str(error.value)


def test_cancellation_kills_child(tmp_path, monkeypatch):
  pid_file = tmp_path / 'pid'
  fake_binary(tmp_path, monkeypatch, f'import os, time\nopen({str(pid_file)!r}, "w").write(str(os.getpid()))\ntime.sleep(20)\n')
  def progress(_stage):
    if pid_file.exists():
      raise RuntimeError('cancelled')
  with pytest.raises(RuntimeError, match='cancelled'):
    play_resolver.resolve(EMAIL, TOKEN, progress=progress)
  with pytest.raises(ProcessLookupError):
    os.kill(int(pid_file.read_text()), 0)


@pytest.mark.parametrize('url', ['https://play.googleapis.com.evil/download/by-token/download',
                                'http://play.googleapis.com/download/by-token/download',
                                'https://user@play.googleapis.com/download/by-token/download',
                                'https://play.googleapis.com:444/download/by-token/download',
                                'https://play.googleapis.com/other'])
def test_rejects_unexpected_download_hosts(url):
  with pytest.raises(play_resolver.PlayError):
    play_resolver.validate_url(url)


def test_token_store_permissions_and_forget(tmp_path):
  store = play_resolver.TokenStore(tmp_path / 'private' / 'aa_token')
  store.save(EMAIL, AAS)
  assert store.path.stat().st_mode & 0o777 == 0o600
  assert store.load() == {'email': EMAIL, 'token': AAS}
  assert not list(store.path.parent.glob('.aa-token-*'))
  store.path.chmod(0o644)
  with pytest.raises(play_resolver.PlayError):
    store.load()
  store.forget()
  store.forget()
  assert not store.exists()


def test_token_store_rejects_symlink(tmp_path):
  target = tmp_path / 'elsewhere'
  target.write_text('{}')
  path = tmp_path / 'aa_token'
  path.symlink_to(target)
  with pytest.raises(OSError):
    play_resolver.TokenStore(path).load()


@pytest.mark.parametrize('remember', [False, True])
def test_google_import_installs_and_cleans_private_package(tmp_path, monkeypatch, remember):
  store = play_resolver.TokenStore(tmp_path / 'aa_token')
  job = apk_identity.ImportJob(work_dir=tmp_path / 'work', identity_dir=tmp_path / 'identity', token_store=store)
  monkeypatch.setattr(play_resolver, 'resolve', Mock(return_value={'url': URL, 'aas_token': AAS}))
  def download(url, destination, progress, **kwargs):
    assert kwargs == {"google_play": True}
    assert url == URL and destination.stat().st_mode & 0o077 == 0
    destination.write_bytes(b'package')
    progress(7, 7)
  monkeypatch.setattr(apk_identity, 'download', download)
  monkeypatch.setattr(apk_identity, 'extract_identity', Mock(return_value=({'key': b'private'}, {'expires': '2027-01-01T00:00:00+00:00'})))
  install = Mock()
  monkeypatch.setattr(apk_identity, 'install_identity', install)
  job.start_google_import(email=EMAIL, oauth_token=TOKEN, save_token=remember)
  job.thread.join(3)
  assert job.status()['state'] == 'done'
  install.assert_called_once()
  assert not list(job.work_dir.iterdir())
  assert store.exists() is remember
  assert all(secret not in json.dumps(job.status()) for secret in (TOKEN, AAS, URL, EMAIL))


def test_download_exception_redacted_and_old_identity_preserved(tmp_path, monkeypatch):
  job = apk_identity.ImportJob(work_dir=tmp_path / 'work', token_store=play_resolver.TokenStore(tmp_path / 'token'))
  monkeypatch.setattr(play_resolver, 'resolve', Mock(return_value={'url': URL}))
  monkeypatch.setattr(apk_identity, 'download', Mock(side_effect=apk_identity.IdentityImportError(URL, 'DOWNLOAD')))
  install = Mock()
  monkeypatch.setattr(apk_identity, 'install_identity', install)
  job.start_google_import(email=EMAIL, oauth_token=TOKEN)
  job.thread.join(3)
  assert job.status()['state'] == 'failed' and URL not in json.dumps(job.status())
  assert not list(job.work_dir.iterdir())
  install.assert_not_called()


def test_revoked_session_never_resolves_or_installs(tmp_path, monkeypatch):
  resolve = Mock()
  monkeypatch.setattr(play_resolver, 'resolve', resolve)
  job = apk_identity.ImportJob(work_dir=tmp_path / 'work')
  job.start_google_import(email=EMAIL, oauth_token=TOKEN, enabled=lambda: False)
  job.thread.join(3)
  assert job.status()['code'] == 'CANCELLED'
  resolve.assert_not_called()
