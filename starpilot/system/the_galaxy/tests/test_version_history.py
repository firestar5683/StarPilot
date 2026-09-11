import importlib.util
import io
from http.client import IncompleteRead
import subprocess
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request

import pytest


MODULE = Path(__file__).resolve().parents[1] / 'version_history.py'


@pytest.fixture
def history(tmp_path, monkeypatch):
  assert MODULE.exists(), 'The branch history implementation must exist'
  spec = importlib.util.spec_from_file_location('version_history_under_test', MODULE)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  monkeypatch.setattr(module, "SNAPSHOT_CACHE_DIR", tmp_path / "history-cache", raising=False)
  return module


@pytest.fixture
def repo(tmp_path):
  subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
  subprocess.run(['git', '-C', str(tmp_path), 'remote', 'add', 'origin', 'https://github.com/firestar5683/openpilot.git'], check=True)
  return tmp_path


def commit(n):
  return {'sha': f'{n:040x}', 'commit': {'message': f'Change {n}\n\nDetails', 'committer': {'date': '2026-09-11T12:00:00Z'}}}


class GitHub:
  def __init__(self):
    self.heads = {'main': 120, 'feature/slash': 60}
    self.requests = []
    self.invalid_compare = None

  def __call__(self, url):
    self.requests.append(url)
    parsed = urlparse(url)
    assert parsed.scheme == 'https' and parsed.netloc == 'api.github.com'
    assert parsed.path.startswith('/repos/firestar5683/openpilot/')
    path = parsed.path.split('/openpilot/')[1]
    if path.startswith('branches/'):
      branch = unquote(path[len('branches/'):])
      return {'name': branch, 'commit': {'sha': f'{self.heads[branch]:040x}'}}
    if path.startswith('compare/'):
      base, head = (int(part, 16) for part in path[len('compare/'):].split('...'))
      return self.invalid_compare or {'status': 'identical' if base == head else ('ahead' if base < head else 'behind'),
                                     'merge_base_commit': {'sha': f'{min(base, head):040x}'}}
    assert path == 'commits'
    query = parse_qs(parsed.query)
    head, page, size = int(query['sha'][0], 16), int(query['page'][0]), int(query['per_page'][0])
    start = head - (page - 1) * size
    return [commit(n) for n in range(start, max(0, start - size), -1)]


@pytest.fixture
def api(history, monkeypatch):
  fake = GitHub()
  monkeypatch.setattr(history, '_get_json', fake)
  return fake


def test_lists_25_commits_and_keeps_page_head_when_branch_advances(history, repo, api):
  first = history.list_versions(repo, 'main')
  assert first == {'branch': 'main', 'head': f'{120:040x}', 'page': 1, 'hasMore': True,
                   'commits': [{'sha': f'{n:040x}', 'subject': f'Change {n}', 'date': '2026-09-11T12:00:00Z'} for n in range(120, 95, -1)]}
  api.heads['main'] = 121
  second = history.list_versions(repo, 'main', page=2, head=first['head'])
  assert second['head'] == first['head']
  assert second['commits'][0]['sha'] == f'{95:040x}'
  last = history.list_versions(repo, 'main', page=5, head=first['head'])
  assert len(last['commits']) == 20 and last['hasMore'] is False


def test_slash_branch_and_switch_do_not_reuse_other_branch_head(history, repo, api):
  history.list_versions(repo, 'main')
  slash = history.list_versions(repo, 'feature/slash')
  assert slash['branch'] == 'feature/slash' and slash['head'] == f'{60:040x}'
  with pytest.raises(history.VersionHistoryError, match='branch'):
    history.list_versions(repo, 'feature/slash', page=2, head=f'{120:040x}')


@pytest.mark.parametrize('branch', ['', '-main', '../main', 'main~1', 'main..old', 'a b', '@{-1}', 'a\nb', None])
def test_invalid_branches_never_reach_network(history, repo, api, branch):
  with pytest.raises(history.VersionHistoryError, match='branch'):
    history.list_versions(repo, branch)
  assert not api.requests


@pytest.mark.parametrize('value', ['abcd', 'g' * 40, 'a' * 41, 'HEAD', '--help', None])
def test_invalid_exact_commit_is_rejected(history, repo, api, value):
  with pytest.raises(history.VersionHistoryError, match='commit'):
    history.resolve_version(repo, 'main', value)
  assert not api.requests


@pytest.mark.parametrize('url', ['git@github.com:firestar5683/openpilot.git', 'ssh://git@github.com/firestar5683/openpilot.git', 'https://github.com/firestar5683/openpilot'])
def test_github_remote_formats(history, repo, api, url):
  subprocess.run(['git', '-C', str(repo), 'remote', 'set-url', 'origin', url], check=True)
  assert history.resolve_version(repo, 'main', 'latest')['commit'] == f'{120:040x}'


@pytest.mark.parametrize('url', ['https://gitlab.com/owner/repo.git', 'https://github.com.evil.test/owner/repo', '/local/repo', 'https://user:secret@github.com/owner/repo', 'https://github.com/owner/repo?x=1', 'https://github.com/owner/repo/extra'])
def test_rejects_untrusted_origin_without_network_or_credential_disclosure(history, repo, api, url):
  subprocess.run(['git', '-C', str(repo), 'remote', 'set-url', 'origin', url], check=True)
  with pytest.raises(history.VersionHistoryError, match='origin') as exc:
    history.list_versions(repo, 'main')
  assert 'secret' not in str(exc.value) and not api.requests


def test_resolve_refreshes_cached_head_and_validates_pin(history, repo, api):
  history.list_versions(repo, 'main')
  api.heads['main'] = 121
  assert history.resolve_version(repo, 'main', 'latest') == {'branch': 'main', 'commit': f'{121:040x}', 'head': f'{121:040x}', 'pinned': False}
  assert history.resolve_version(repo, 'main', f'{100:040x}') == {'branch': 'main', 'commit': f'{100:040x}', 'head': f'{121:040x}', 'pinned': True}
  assert history.resolve_version(repo, 'main', f'{121:040x}')['pinned'] is True


@pytest.mark.parametrize('comparison', [{'status': 'diverged', 'merge_base_commit': {'sha': f'{50:040x}'}}, {'status': 'ahead', 'merge_base_commit': {'sha': f'{50:040x}'}}, {}, {'status': 'behind', 'merge_base_commit': {'sha': f'{100:040x}'}}])
def test_exact_pin_rejects_cross_branch_or_invalid_ancestry(history, repo, api, comparison):
  api.invalid_compare = comparison
  if not comparison:
    api.invalid_compare = {'status': None}
  with pytest.raises(history.VersionHistoryError, match='branch|GitHub'):
    history.resolve_version(repo, 'main', f'{100:040x}')


def test_stale_head_after_branch_rewrite_is_rejected_after_browser_ttl(history, repo, api, monkeypatch):
  clock = [100.0]
  monkeypatch.setattr(history.time, 'monotonic', lambda: clock[0])
  old = history.list_versions(repo, 'main')['head']
  api.heads['main'] = 80
  # Browsing can reuse a head for 60 seconds; installation always refreshes.
  assert history.list_versions(repo, 'main', page=2, head=old)['head'] == old
  clock[0] += 61
  with pytest.raises(history.VersionHistoryError, match='branch'):
    history.list_versions(repo, 'main', page=2, head=old)


@pytest.mark.parametrize('kwargs', [{'page': 0}, {'page': True}, {'page': 1.5}, {'page': '2'}, {'page': 2}, {'head': 'HEAD'}])
def test_rejects_invalid_or_unpinned_pagination(history, repo, api, kwargs):
  with pytest.raises(history.VersionHistoryError):
    history.list_versions(repo, 'main', **kwargs)
  assert not api.requests


@pytest.mark.parametrize('body', [{}, {'commit': {'sha': 'oops'}}, {'commit': {'sha': f'{120:040x}'}, 'name': 'different'}])
def test_invalid_branch_response(history, repo, monkeypatch, body):
  monkeypatch.setattr(history, '_get_json', lambda url: body)
  with pytest.raises(history.VersionHistoryError, match='GitHub'):
    history.list_versions(repo, 'main')


@pytest.mark.parametrize('rows', [None, {}, [{}], [dict(commit(120), sha='wrong')], [dict(commit(120), commit={'message': 'x', 'committer': {'date': 'bad'}})], [commit(119)], [commit(120), commit(120)]])
def test_invalid_commit_response(history, repo, monkeypatch, rows):
  fake = GitHub()
  monkeypatch.setattr(history, '_get_json', lambda url: rows if '/commits?' in url else fake(url))
  with pytest.raises(history.VersionHistoryError, match='GitHub'):
    history.list_versions(repo, 'main')


def test_cache_expires_and_returns_independent_results(history, repo, api, monkeypatch):
  clock = [100.0]
  monkeypatch.setattr(history.time, 'monotonic', lambda: clock[0])
  first = history.list_versions(repo, 'main')
  first['commits'][0]['subject'] = 'corrupt'
  count = len(api.requests)
  assert history.list_versions(repo, 'main')['commits'][0]['subject'] == 'Change 120'
  assert len(api.requests) == count
  api.heads['main'] = 121
  clock[0] += 61
  assert history.list_versions(repo, 'main')['head'] == f'{121:040x}'


@pytest.mark.parametrize('code', [403, 429, 404, 500])
def test_http_errors_are_actionable(history, repo, monkeypatch, code):
  def fail(*args, **kwargs):
    raise HTTPError('https://api.github.com/', code, 'failure', {'Retry-After': '60'}, io.BytesIO(b'{}'))
  monkeypatch.setattr(history, '_open_url', fail)
  with pytest.raises(history.VersionHistoryError, match='rate limit|retry|not found'):
    history.list_versions(repo, 'main')


def test_network_failure_is_retryable(history, repo, monkeypatch):
  def fail(*args, **kwargs):
    raise URLError('offline')
  monkeypatch.setattr(history, '_open_url', fail)
  with pytest.raises(history.VersionHistoryError, match='retry'):
    history.list_versions(repo, 'main')


@pytest.mark.parametrize('content', [b'{broken', b'x' * (4 * 1024 * 1024 + 1)], ids=['invalid-json', 'oversized-json'])
def test_http_invalid_or_oversized_json_is_bounded(history, repo, monkeypatch, content):
  monkeypatch.setattr(history, '_open_url', lambda *a, **kw: io.BytesIO(content))
  with pytest.raises(history.VersionHistoryError, match='GitHub'):
    history.list_versions(repo, 'main')


def test_truncated_http_response_is_retryable(history, repo, monkeypatch):
  class Truncated(io.BytesIO):
    def read(self, *args):
      raise IncompleteRead(b'partial', 100)
  monkeypatch.setattr(history, '_open_url', lambda *a, **kw: Truncated())
  with pytest.raises(history.VersionHistoryError, match='retry'):
    history.list_versions(repo, 'main')


def test_full_block_has_more_is_exact(history, repo, api, monkeypatch):
  clock = [100.0]
  monkeypatch.setattr(history.time, 'monotonic', lambda: clock[0])
  api.heads['main'] = 100
  page = history.list_versions(repo, 'main', page=4, head=f'{100:040x}')
  assert len(page['commits']) == 25 and page['hasMore'] is False
  api.heads['main'] = 101
  clock[0] += 61  # Let browsing discover the new branch head.
  page = history.list_versions(repo, 'main', page=4, head=f'{101:040x}')
  assert page['hasMore'] is True


def test_evicted_branch_is_refreshed_after_many_branches(history, repo, api):
  history.list_versions(repo, 'main')
  for n in range(65):
    api.heads[f'branch{n}'] = 1
    history.list_versions(repo, f'branch{n}')
  api.heads['main'] = 121
  assert history.list_versions(repo, 'main')['head'] == f'{121:040x}'


@pytest.mark.parametrize('url', ['https://evil.test/data', 'http://api.github.com/repos/a/b', 'https://api.github.com.evil.test/data'])
def test_redirects_cannot_leave_github_api(history, url):
  handler = history._GitHubRedirectHandler()
  with pytest.raises(history.VersionHistoryError, match='redirect'):
    handler.redirect_request(Request('https://api.github.com/repos/a/b'), None, 301, 'Moved', {}, url)


def test_canonical_github_repository_redirect_is_allowed(history):
  redirected = history._GitHubRedirectHandler().redirect_request(Request('https://api.github.com/repos/firestar5683/openpilot'), None, 301, 'Moved', {}, 'https://api.github.com/repos/firestar5683/StarPilot')
  assert redirected.full_url == 'https://api.github.com/repos/firestar5683/StarPilot'


def test_history_has_no_artificial_depth_limit(history, repo, api):
  api.heads['main'] = 30000
  result = history.list_versions(repo, 'main', page=1001, head=f'{30000:040x}')
  assert len(result['commits']) == 25
  assert result['commits'][0]['sha'] == f'{5000:040x}'
  assert result['hasMore'] is True
  assert len(api.requests) == 2


def test_starpilot_versions_come_from_each_exact_sha(history, repo, api, monkeypatch):
  api.heads['StarPilot'] = 3
  requests = []
  def raw(request, **kwargs):
    requests.append(request.full_url)
    sha = request.full_url.split('/')[-5]
    version = '6.7.7' if int(sha, 16) >= 2 else '6.7.6'
    return io.BytesIO(f'STARPILOT_DISPLAY_VERSION = "{version}"\n'.encode())
  monkeypatch.setattr(history, '_open_raw_url', raw, raising=False)
  rows = history.list_versions(repo, 'StarPilot')['commits']
  assert [r.get('version') for r in rows] == ['6.7.7', '6.7.7', '6.7.6']
  assert len(requests) == 3
  assert all(url.startswith('https://raw.githubusercontent.com/firestar5683/openpilot/') for url in requests)
  assert all(url.endswith('/selfdrive/ui/lib/starpilot_version.py') for url in requests)
  assert [r['sha'] for r in rows] == [f'{n:040x}' for n in (3, 2, 1)]


def test_other_branches_do_not_fetch_starpilot_versions(history, repo, api, monkeypatch):
  def raw(*args, **kwargs):
    pytest.fail('Other branches must not request StarPilot version files')
  monkeypatch.setattr(history, '_open_raw_url', raw, raising=False)
  assert len(history.list_versions(repo, 'main')['commits']) == 25


def test_missing_old_version_file_is_explicit_and_cached(history, repo, api, monkeypatch):
  api.heads['StarPilot'] = 1
  calls = []
  def raw(request, **kwargs):
    calls.append(request.full_url)
    raise HTTPError(request.full_url, 404, 'Not Found', {}, io.BytesIO())
  monkeypatch.setattr(history, '_open_raw_url', raw, raising=False)
  first = history.list_versions(repo, 'StarPilot')
  assert first['commits'][0]['version'] is None
  assert history.list_versions(repo, 'StarPilot')['commits'][0]['version'] is None
  assert len(calls) == 1


@pytest.mark.parametrize('body', [
  b'STARPILOT_DISPLAY_VERSION = "6.7.7-beta"\n',
  b'STARPILOT_DISPLAY_VERSION = str(6.7)\n',
  b'STARPILOT_DISPLAY_VERSION = "6.7.7"; raise RuntimeError()\n',
  b'STARPILOT_DISPLAY_VERSION = "6.7.7"\nSTARPILOT_DISPLAY_VERSION = "6.7.6"\n',
  b'not python',
  b'\xff',
  b'x' * (64 * 1024 + 1),
], ids=['non-numeric', 'expression', 'extra-statement', 'ambiguous', 'missing-literal', 'invalid-encoding', 'oversized'])
def test_invalid_version_metadata_is_retryable(history, repo, api, monkeypatch, body):
  api.heads['StarPilot'] = 1
  monkeypatch.setattr(history, '_open_raw_url', lambda *a, **kw: io.BytesIO(body), raising=False)
  with pytest.raises(history.VersionHistoryError, match='version.*retry'):
    history.list_versions(repo, 'StarPilot')


@pytest.mark.parametrize('failure', [
  HTTPError('https://raw.githubusercontent.com/', 429, 'Slow down', {}, io.BytesIO()),
  HTTPError('https://raw.githubusercontent.com/', 500, 'Unavailable', {}, io.BytesIO()),
  URLError('offline'), IncompleteRead(b'partial', 100),
])
def test_version_network_failure_is_not_cached_as_missing(history, repo, api, monkeypatch, failure):
  api.heads['StarPilot'] = 1
  def fail(*args, **kwargs):
    raise failure
  monkeypatch.setattr(history, '_open_raw_url', fail, raising=False)
  with pytest.raises(history.VersionHistoryError, match='retry'):
    history.list_versions(repo, 'StarPilot')
  monkeypatch.setattr(history, '_open_raw_url', lambda *a, **kw: io.BytesIO(b'STARPILOT_DISPLAY_VERSION = "6.7.7"\n'))
  assert history.list_versions(repo, 'StarPilot')['commits'][0]['version'] == '6.7.7'


def test_version_cache_outlives_branch_cache_and_expires(history, repo, api, monkeypatch):
  api.heads['StarPilot'] = 1
  clock = [100.0]
  monkeypatch.setattr(history.time, 'monotonic', lambda: clock[0])
  calls = []
  def raw(*args, **kwargs):
    calls.append(1)
    return io.BytesIO(b'STARPILOT_DISPLAY_VERSION = "6.7.7"\n')
  monkeypatch.setattr(history, '_open_raw_url', raw, raising=False)
  assert history.list_versions(repo, 'StarPilot')['commits'][0]['version'] == '6.7.7'
  clock[0] += 3600
  history.list_versions(repo, 'StarPilot')
  assert len(calls) == 1
  clock[0] += 24 * 3600
  history.list_versions(repo, 'StarPilot')
  assert len(calls) == 2


@pytest.mark.parametrize('callers', [1, 2])
def test_version_requests_are_parallel_and_bounded(history, repo, api, monkeypatch, callers):
  import threading
  import time
  api.heads['StarPilot'] = 8
  lock = threading.Lock()
  counts = {'active': 0, 'peak': 0}
  def raw(*args, **kwargs):
    with lock:
      counts['active'] += 1
      counts['peak'] = max(counts['peak'], counts['active'])
    time.sleep(0.03)
    with lock:
      counts['active'] -= 1
    return io.BytesIO(b'STARPILOT_DISPLAY_VERSION = "6.7.7"\n')
  monkeypatch.setattr(history, '_open_raw_url', raw, raising=False)
  from concurrent.futures import ThreadPoolExecutor
  with ThreadPoolExecutor(max_workers=callers) as clients:
    results = list(clients.map(lambda _: history.list_versions(repo, 'StarPilot'), range(callers)))
  assert all(row['version'] == '6.7.7' for result in results for row in result['commits'])
  assert 1 < counts['peak'] <= 4


@pytest.mark.parametrize('url', ['https://evil.test/file', 'http://raw.githubusercontent.com/file', 'https://api.github.com/file'])
def test_raw_redirects_stay_on_https_raw_github(history, url):
  with pytest.raises(history.VersionHistoryError, match='redirect'):
    history._RawGitHubRedirectHandler().redirect_request(Request('https://raw.githubusercontent.com/a/b'), None, 301, 'Moved', {}, url)


def test_failed_version_request_cancels_pending_work_promptly(history, repo, api, monkeypatch):
  from concurrent.futures import ThreadPoolExecutor
  import threading
  api.heads['StarPilot'] = 25
  started = threading.Barrier(4)
  release = threading.Event()
  downloads = []
  class RecordingExecutor(ThreadPoolExecutor):
    def submit(self, *args, **kwargs):
      future = super().submit(*args, **kwargs)
      downloads.append(future)
      return future
  monkeypatch.setattr(history, 'ThreadPoolExecutor', RecordingExecutor)
  def raw(request, **kwargs):
    if int(request.full_url.split('/')[-5], 16) >= 22:
      started.wait(timeout=5)
    if request.full_url.split('/')[-5] == f'{25:040x}':
      raise URLError('offline')
    release.wait(timeout=5)
    return io.BytesIO(b'STARPILOT_DISPLAY_VERSION = "6.7.7"\n')
  monkeypatch.setattr(history, '_open_raw_url', raw)
  with ThreadPoolExecutor(max_workers=1) as caller:
    result = caller.submit(history.list_versions, repo, 'StarPilot')
    try:
      with pytest.raises(history.VersionHistoryError, match='retry'):
        result.result(timeout=1)
    finally:
      release.set()
  assert sum(future.cancelled() for future in downloads) >= 20
  for future in downloads:
    if not future.cancelled():
      try:
        future.result(timeout=2)
      except history.VersionHistoryError:
        pass


def test_version_cache_is_bounded_and_preserves_recent_entries(history, monkeypatch):
  calls = []
  def raw(request, **kwargs):
    calls.append(request.full_url)
    return io.BytesIO(b'STARPILOT_DISPLAY_VERSION = "6.7.7"\n')
  monkeypatch.setattr(history, '_open_raw_url', raw)
  monkeypatch.setattr(history, 'MAX_VERSION_CACHE_ENTRIES', 2)
  base = 'https://api.github.com/repos/firestar5683/openpilot'
  for n in (1, 2, 1, 3, 1):
    assert history._display_version(base, f'{n:040x}') == '6.7.7'
  assert len(calls) == 3
  history._display_version(base, f'{2:040x}')
  assert len(calls) == 4


def test_version_cache_does_not_mix_repository_origins(history, monkeypatch):
  def raw(request, **kwargs):
    version = '6.7.7' if '/firestar5683/' in request.full_url else '6.7.6'
    return io.BytesIO(f"STARPILOT_DISPLAY_VERSION = '{version}' # display\n".encode())
  monkeypatch.setattr(history, '_open_raw_url', raw)
  assert history._display_version('https://api.github.com/repos/firestar5683/openpilot', f'{1:040x}') == '6.7.7'
  assert history._display_version('https://api.github.com/repos/other/openpilot', f'{1:040x}') == '6.7.6'


def test_raw_canonical_repository_redirect_is_allowed(history):
  url = 'https://raw.githubusercontent.com/firestar5683/StarPilot/' + f'{1:040x}' + '/selfdrive/ui/lib/starpilot_version.py'
  redirected = history._RawGitHubRedirectHandler().redirect_request(Request('https://raw.githubusercontent.com/firestar5683/openpilot/file'), None, 301, 'Moved', {}, url)
  assert redirected.full_url == url


def test_paging_reuses_head_and_immutable_blocks_for_six_hours(history, repo, api, monkeypatch):
  clock = [100.0]
  monkeypatch.setattr(history.time, 'monotonic', lambda: clock[0])
  first = history.list_versions(repo, 'main')
  assert len(api.requests) == 2
  history.list_versions(repo, 'main', page=2, head=first['head'])
  assert len(api.requests) == 2
  clock[0] += 3600
  history.list_versions(repo, 'main', page=3, head=first['head'])
  assert len(api.requests) == 3  # Only the mutable head refreshes.
  clock[0] += 6 * 3600
  history.list_versions(repo, 'main', page=3, head=first['head'])
  assert len(api.requests) == 5  # Head plus expired immutable block.


def test_immutable_ancestry_cache_outlives_browser_head_cache(history, repo, api, monkeypatch):
  clock = [100.0]
  monkeypatch.setattr(history.time, 'monotonic', lambda: clock[0])
  base = 'https://api.github.com/repos/firestar5683/openpilot'
  history._ancestor(base, f'{100:040x}', f'{120:040x}')
  clock[0] += 3600
  history._ancestor(base, f'{100:040x}', f'{120:040x}')
  assert len(api.requests) == 1
  clock[0] += 6 * 3600
  history._ancestor(base, f'{100:040x}', f'{120:040x}')
  assert len(api.requests) == 2


def test_install_rejects_force_push_during_browser_cache_window(history, repo, api):
  old = history.list_versions(repo, 'main')['head']
  api.heads['main'] = 80
  with pytest.raises(history.VersionHistoryError, match='branch'):
    history.resolve_version(repo, 'main', old)


@pytest.mark.parametrize('headers,expected', [
  ({'Retry-After': '90', 'X-RateLimit-Reset': '3280'}, '90 seconds'),
  ({'X-RateLimit-Reset': '3280'}, '38 minutes'),
  ({'Retry-After': 'bad', 'X-RateLimit-Reset': '3280'}, '38 minutes'),
  ({'X-RateLimit-Reset': '999'}, 'retry later'),
])
def test_rate_limit_reports_retry_time(history, monkeypatch, headers, expected):
  monkeypatch.setattr(history.time, 'time', lambda: 1000.0)
  def fail(*args, **kwargs):
    raise HTTPError('https://api.github.com/', 403, 'Limited', headers, io.BytesIO())
  monkeypatch.setattr(history, '_open_url', fail)
  with pytest.raises(history.VersionHistoryError, match=expected):
    history._get_json('https://api.github.com/repos/a/b')


@pytest.mark.parametrize('code', [403, 429])
def test_rate_limit_short_backoff_is_shared_and_then_retries(history, monkeypatch, code):
  clock = [1000.0]
  monkeypatch.setattr(history.time, 'time', lambda: clock[0])
  monkeypatch.setattr(history.time, 'monotonic', lambda: clock[0])
  calls = []
  def raw(*args, **kwargs):
    calls.append(1)
    if len(calls) == 1:
      raise HTTPError('https://api.github.com/', code, 'Limited', {'X-RateLimit-Reset': '3280', 'X-RateLimit-Remaining': '0'}, io.BytesIO())
    return io.BytesIO(b'{"ok": true}')
  monkeypatch.setattr(history, '_open_url', raw)
  for path in ('branches/main', 'commits'):
    with pytest.raises(history.VersionHistoryError, match='38 minutes'):
      history._get_json('https://api.github.com/repos/a/b/' + path)
  assert len(calls) == 1
  clock[0] += 61
  assert history._get_json('https://api.github.com/repos/a/b/branches/main') == {'ok': True}
  assert len(calls) == 2


def test_unrelated_403_does_not_backoff_other_metadata(history, monkeypatch):
  calls = []
  def raw(*args, **kwargs):
    calls.append(1)
    if len(calls) == 1:
      raise HTTPError('https://api.github.com/', 403, 'Forbidden', {}, io.BytesIO())
    return io.BytesIO(b'{"ok": true}')
  monkeypatch.setattr(history, '_open_url', raw)
  with pytest.raises(history.VersionHistoryError, match='restriction'):
    history._get_json('https://api.github.com/repos/a/b')
  assert history._get_json('https://api.github.com/repos/c/d') == {'ok': True}


def test_backoff_keeps_cached_history_available_but_does_not_stale_install_head(history, repo, monkeypatch):
  fake = GitHub()
  original_get_json = history._get_json
  monkeypatch.setattr(history, '_get_json', fake)
  first = history.list_versions(repo, 'main')
  # Restore the actual transport, then establish a known quota backoff.
  monkeypatch.setattr(history, '_get_json', original_get_json)
  def fail(*args, **kwargs):
    raise HTTPError('https://api.github.com/', 403, 'Limited', {'X-RateLimit-Remaining': '0'}, io.BytesIO())
  monkeypatch.setattr(history, '_open_url', fail)
  with pytest.raises(history.VersionHistoryError, match='retry'):
    history._get_json('https://api.github.com/repos/a/b')
  assert history.list_versions(repo, 'main', page=2, head=first['head'])['commits'][0]['sha'] == f'{95:040x}'
  with pytest.raises(history.VersionHistoryError, match='retry'):
    history.resolve_version(repo, 'main', 'latest')



def offline_reload(history, monkeypatch):
  spec = importlib.util.spec_from_file_location('history_reloaded_offline', MODULE)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  monkeypatch.setattr(module, 'SNAPSHOT_CACHE_DIR', history.SNAPSHOT_CACHE_DIR, raising=False)
  def fail(*args, **kwargs):
    raise URLError('offline')
  monkeypatch.setattr(module, '_open_url', fail)
  return module


def test_snapshot_survives_module_reload_and_keeps_original_timestamp(history, repo, api, monkeypatch):
  first = history.list_versions(repo, 'main')
  offline = offline_reload(history, monkeypatch)
  cached = offline.list_versions(repo, 'main')
  assert cached['cached'] is True
  assert cached['commits'] == first['commits'] and cached['head'] == first['head']
  assert 'retry' in cached['cacheReason']
  original_time = cached['cachedAt']
  assert offline.list_versions(repo, 'main')['cachedAt'] == original_time


def test_snapshot_pagination_requires_the_exact_requested_head(history, repo, api, monkeypatch):
  first = history.list_versions(repo, 'main')
  page = history.list_versions(repo, 'main', page=2, head=first['head'])
  offline = offline_reload(history, monkeypatch)
  assert offline.list_versions(repo, 'main', page=2, head=first['head'])['commits'] == page['commits']
  with pytest.raises(offline.VersionHistoryError, match='retry'):
    offline.list_versions(repo, 'main', page=2, head=f'{119:040x}')
  with pytest.raises(offline.VersionHistoryError, match='retry'):
    offline.list_versions(repo, 'main', page=3, head=first['head'])


def test_snapshot_does_not_cross_repository_origins(history, repo, api, monkeypatch):
  history.list_versions(repo, 'main')
  subprocess.run(['git', '-C', str(repo), 'remote', 'set-url', 'origin', 'https://github.com/other/openpilot'], check=True)
  offline = offline_reload(history, monkeypatch)
  with pytest.raises(offline.VersionHistoryError, match='retry'):
    offline.list_versions(repo, 'main')


def test_snapshot_never_bypasses_install_freshness(history, repo, api, monkeypatch):
  first = history.list_versions(repo, 'main')
  offline = offline_reload(history, monkeypatch)
  for chosen in ('latest', first['head']):
    with pytest.raises(offline.VersionHistoryError, match='retry'):
      offline.resolve_version(repo, 'main', chosen)


@pytest.mark.parametrize('failure_kind', ['rewrite', '404', 'malformed'])
def test_snapshot_does_not_hide_invalid_live_metadata(history, repo, api, monkeypatch, failure_kind):
  first = history.list_versions(repo, 'main')
  history.list_versions(repo, 'main', page=2, head=first['head'])
  live = offline_reload(history, monkeypatch)
  if failure_kind == 'rewrite':
    fake = GitHub()
    fake.heads['main'] = 80
    monkeypatch.setattr(live, '_get_json', fake)
  elif failure_kind == '404':
    def missing(*args, **kwargs):
      raise HTTPError('https://api.github.com/', 404, 'Missing', {}, io.BytesIO())
    monkeypatch.setattr(live, '_open_url', missing)
  else:
    monkeypatch.setattr(live, '_get_json', lambda url: {})
  with pytest.raises(live.VersionHistoryError):
    live.list_versions(repo, 'main', page=2, head=first['head'])


@pytest.mark.parametrize('damage', ['corrupt', 'oversized', 'origin', 'branch', 'page', 'requested_head', 'row_sha', 'row_date',
                                    'row_subject', 'row_version', 'head_mismatch', 'duplicate', 'old', 'future', 'naive_time'])
def test_invalid_snapshot_is_ignored(history, repo, api, monkeypatch, damage):
  import json
  from datetime import datetime, timedelta, timezone
  history.list_versions(repo, 'main')
  path = next(history.SNAPSHOT_CACHE_DIR.glob('*.json'))
  data = json.loads(path.read_text())
  if damage == 'corrupt':
    path.write_text('{broken')
  elif damage == 'oversized':
    path.write_bytes(b'x' * (128 * 1024 + 1))
  else:
    if damage == 'origin':
      data['repository'] = 'https://api.github.com/repos/other/openpilot'
    elif damage == 'branch':
      data['branch'] = 'other'
    elif damage == 'page':
      data['result']['page'] = 2
    elif damage == 'requested_head':
      data['requestedHead'] = f'{119:040x}'
    elif damage == 'row_sha':
      data['result']['commits'][0]['sha'] = 'HEAD'
    elif damage == 'row_date':
      data['result']['commits'][0]['date'] = 'yesterday'
    elif damage == 'row_subject':
      data['result']['commits'][0]['subject'] = []
    elif damage == 'row_version':
      data['result']['commits'][0]['version'] = '<script>'
    elif damage == 'head_mismatch':
      data['result']['head'] = f'{119:040x}'
    elif damage == 'duplicate':
      data['result']['commits'][1] = data['result']['commits'][0]
    elif damage == 'old':
      data['cachedAt'] = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    elif damage == 'future':
      data['cachedAt'] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    elif damage == 'naive_time':
      data['cachedAt'] = '2026-09-11T12:00:00'
    path.write_text(json.dumps(data))
  offline = offline_reload(history, monkeypatch)
  with pytest.raises(offline.VersionHistoryError, match='retry'):
    offline.list_versions(repo, 'main')


def test_snapshot_storage_failure_does_not_fail_online_browsing(history, repo, api):
  history.SNAPSHOT_CACHE_DIR.write_text('not a directory')
  assert len(history.list_versions(repo, 'main')['commits']) == 25


def test_snapshot_preload_timestamp_is_truthful_and_permissions_private(history, repo, api):
  from datetime import datetime, timedelta, timezone
  first = history.list_versions(repo, 'main')
  saved_at = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
  base = 'https://api.github.com/repos/firestar5683/openpilot'
  assert history._save_history_snapshot(base, 'main', 1, None, first, saved_at=saved_at)
  cached = history._load_history_snapshot(base, 'main', 1, None)
  assert cached['cachedAt'] == saved_at
  path = next(history.SNAPSHOT_CACHE_DIR.glob('*.json'))
  assert path.stat().st_mode & 0o777 == 0o600
  assert history.SNAPSHOT_CACHE_DIR.stat().st_mode & 0o777 == 0o700
  assert not list(history.SNAPSHOT_CACHE_DIR.glob('*.tmp'))


def test_snapshot_prunes_file_count_and_total_bytes(history, repo, api, monkeypatch):
  monkeypatch.setattr(history, 'MAX_SNAPSHOT_FILES', 3)
  for n in range(5):
    api.heads[f'branch{n}'] = 120
    history.list_versions(repo, f'branch{n}')
  files = list(history.SNAPSHOT_CACHE_DIR.glob('*.json'))
  assert len(files) == 3
  one_file_size = max(path.stat().st_size for path in files)
  monkeypatch.setattr(history, 'MAX_SNAPSHOT_TOTAL_BYTES', one_file_size + 20)
  api.heads['branch5'] = 120
  history.list_versions(repo, 'branch5')
  assert sum(path.stat().st_size for path in history.SNAPSHOT_CACHE_DIR.glob('*.json')) <= one_file_size + 20


def test_snapshot_prunes_old_files_on_successful_write(history, repo, api, monkeypatch):
  history.list_versions(repo, 'main')
  now = history.time.time()
  monkeypatch.setattr(history.time, 'time', lambda: now + 31 * 86400)
  api.heads['other'] = 120
  history.list_versions(repo, 'other')
  assert len(list(history.SNAPSHOT_CACHE_DIR.glob('*.json'))) == 1



@pytest.mark.parametrize('code', [403, 429])
def test_quota_failure_uses_labelled_snapshot(history, repo, api, monkeypatch, code):
  first = history.list_versions(repo, 'main')
  offline = offline_reload(history, monkeypatch)
  def limited(*args, **kwargs):
    raise HTTPError('https://api.github.com/', code, 'Limited', {'Retry-After': '90'}, io.BytesIO())
  monkeypatch.setattr(offline, '_open_url', limited)
  result = offline.list_versions(repo, 'main')
  assert result['cached'] is True and result['commits'] == first['commits']
  assert '90 seconds' in result['cacheReason']


@pytest.mark.parametrize('failure_kind', ['offline', 'invalid'])
def test_starpilot_snapshot_fallback_only_for_version_transport_failure(history, repo, api, monkeypatch, failure_kind):
  api.heads['StarPilot'] = 3
  monkeypatch.setattr(history, '_open_raw_url', lambda *a, **kw: io.BytesIO(b'STARPILOT_DISPLAY_VERSION = "6.7.7"\n'))
  first = history.list_versions(repo, 'StarPilot')
  offline = offline_reload(history, monkeypatch)
  monkeypatch.setattr(offline, '_get_json', api)
  def raw(*args, **kwargs):
    if failure_kind == 'offline':
      raise URLError('offline')
    return io.BytesIO(b'not a version literal')
  monkeypatch.setattr(offline, '_open_raw_url', raw)
  if failure_kind == 'offline':
    result = offline.list_versions(repo, 'StarPilot')
    assert result['cached'] is True and result['commits'] == first['commits']
  else:
    with pytest.raises(offline.VersionHistoryError, match='invalid version'):
      offline.list_versions(repo, 'StarPilot')


def test_atomic_snapshot_write_failure_leaves_no_partial_file(history, repo, api, monkeypatch):
  def fail(*args, **kwargs):
    raise OSError('disk full')
  monkeypatch.setattr(history.os, 'replace', fail)
  result = history.list_versions(repo, 'main')
  assert len(result['commits']) == 25 and 'cached' not in result
  assert not list(history.SNAPSHOT_CACHE_DIR.iterdir())


def test_unreadable_snapshot_is_ignored(history, repo, api, monkeypatch):
  history.list_versions(repo, 'main')
  offline = offline_reload(history, monkeypatch)
  original_open = Path.open
  def denied(path, *args, **kwargs):
    if path.parent == history.SNAPSHOT_CACHE_DIR:
      raise PermissionError('cache unavailable')
    return original_open(path, *args, **kwargs)
  monkeypatch.setattr(Path, 'open', denied)
  with pytest.raises(offline.HistoryUnavailable):
    offline.list_versions(repo, 'main')


def test_cached_response_cannot_be_resaved_with_a_new_timestamp(history, repo, api, monkeypatch):
  history.list_versions(repo, 'main')
  offline = offline_reload(history, monkeypatch)
  cached = offline.list_versions(repo, 'main')
  assert not offline._save_history_snapshot('https://api.github.com/repos/firestar5683/openpilot', 'main', 1, None, cached)
  assert offline.list_versions(repo, 'main')['cachedAt'] == cached['cachedAt']



@pytest.mark.parametrize('transport', ['api', 'raw'])
@pytest.mark.parametrize('code,headers,fallback', [
  (403, {}, False),
  (403, {'Retry-After': 'invalid'}, False),
  (403, {'Retry-After': '90'}, True),
  (403, {'X-RateLimit-Remaining': '0'}, True),
  (429, {}, True),
  (503, {}, True),
])
def test_http_failure_snapshot_fallback_boundary(history, repo, api, monkeypatch, transport, code, headers, fallback):
  branch = 'main' if transport == 'api' else 'StarPilot'
  api.heads['StarPilot'] = 3
  monkeypatch.setattr(history, '_open_raw_url', lambda *a, **kw: io.BytesIO(b'STARPILOT_DISPLAY_VERSION = "6.7.7"\n'))
  first = history.list_versions(repo, branch)
  offline = offline_reload(history, monkeypatch)
  def fail(*args, **kwargs):
    raise HTTPError('https://github.com/', code, 'Unavailable', headers, io.BytesIO())
  if transport == 'api':
    monkeypatch.setattr(offline, '_open_url', fail)
  else:
    monkeypatch.setattr(offline, '_get_json', api)
    monkeypatch.setattr(offline, '_open_raw_url', fail)
  if fallback:
    result = offline.list_versions(repo, branch)
    assert result['cached'] is True and result['commits'] == first['commits']
  else:
    with pytest.raises(offline.VersionHistoryError) as error:
      offline.list_versions(repo, branch)
    assert not isinstance(error.value, offline.HistoryUnavailable)


def test_empty_snapshot_preload_timestamp_is_rejected(history, repo, api):
  first = history.list_versions(repo, 'main')
  assert not history._save_history_snapshot('https://api.github.com/repos/firestar5683/openpilot', 'main', 1, None, first, saved_at='')
