"""Bounded public GitHub metadata for the configured origin; never mutates Git."""

import copy
import hashlib
import os
import tempfile
import json
import re
import subprocess
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from http.client import HTTPException
from math import ceil
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


PAGE_SIZE = 25
CACHE_TTL = 60
IMMUTABLE_CACHE_TTL = 6 * 60 * 60
MAX_CACHE_ENTRIES = 64
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
HTTP_TIMEOUT = 10
_BLOCK_SIZE = 100
_cache = OrderedDict()
_cache_lock = threading.Lock()
_api_backoff_until = 0.0
_api_retry_at = 0.0
_api_request_lock = threading.Lock()
_raw_backoff_until = 0.0
_raw_retry_at = 0.0
_request_locks = {}
VERSION_CACHE_TTL = 6 * 60 * 60
MAX_VERSION_CACHE_ENTRIES = 1024
MAX_VERSION_BYTES = 64 * 1024
_VERSION_WORKERS = 4
_version_cache = OrderedDict()
_version_slots = threading.BoundedSemaphore(_VERSION_WORKERS)
SNAPSHOT_CACHE_DIR = Path('/data/starpilot/cache/version-history')
MAX_SNAPSHOT_FILES = 256
MAX_SNAPSHOT_BYTES = 128 * 1024
MAX_SNAPSHOT_TOTAL_BYTES = 16 * 1024 * 1024
SNAPSHOT_RETENTION = 30 * 86400
_snapshot_lock = threading.Lock()


class VersionHistoryError(Exception):
  """An invalid selection or actionable public metadata lookup failure."""


class HistoryUnavailable(VersionHistoryError):
  """A transport or quota failure that permits a labelled browsing snapshot."""


class _GitHubRedirectHandler(HTTPRedirectHandler):
  def redirect_request(self, req, fp, code, msg, headers, newurl):
    target = urlsplit(newurl)
    if target.scheme != 'https' or target.netloc != 'api.github.com':
      raise VersionHistoryError('GitHub returned an unsupported metadata redirect; retry later.')
    return super().redirect_request(req, fp, code, msg, headers, newurl)


_open_url = build_opener(_GitHubRedirectHandler()).open


class _RawGitHubRedirectHandler(HTTPRedirectHandler):
  def redirect_request(self, req, fp, code, msg, headers, newurl):
    target = urlsplit(newurl)
    if target.scheme != 'https' or target.netloc != 'raw.githubusercontent.com':
      raise VersionHistoryError('GitHub returned an unsupported version metadata redirect; retry later.')
    return super().redirect_request(req, fp, code, msg, headers, newurl)


_open_raw_url = build_opener(_RawGitHubRedirectHandler()).open


def _is_quota_failure(error):
  headers = error.headers or {}
  wait = headers.get('Retry-After', '').strip()
  return error.code == 429 or (error.code == 403 and
                              (headers.get('X-RateLimit-Remaining') == '0' or (wait.isdigit() and len(wait) <= 6)))


@contextmanager
def _request_lock(kind, url):
  """Coalesce identical misses without retaining locks after callers finish."""
  key = (kind, url)
  with _cache_lock:
    entry = _request_locks.setdefault(key, [threading.Lock(), 0])
    entry[1] += 1
  try:
    with entry[0]:
      yield
  finally:
    with _cache_lock:
      entry[1] -= 1
      if entry[1] == 0:
        del _request_locks[key]


def _retry_at(headers):
  wait = headers.get('Retry-After', '').strip()
  reset = headers.get('X-RateLimit-Reset', '').strip()
  if wait.isdigit() and len(wait) <= 6:
    return time.time() + int(wait)
  if reset.isdigit() and len(reset) <= 12 and int(reset) > time.time():
    return float(reset)
  return 0.0


def _record_quota_backoff(retry_at, raw=False):
  global _api_backoff_until, _api_retry_at, _raw_backoff_until, _raw_retry_at
  delay = max(1, retry_at - time.time()) if retry_at else 60
  deadline = time.monotonic() + delay
  with _cache_lock:
    if raw:
      if deadline > _raw_backoff_until:
        _raw_backoff_until, _raw_retry_at = deadline, retry_at
    elif deadline > _api_backoff_until:
      _api_backoff_until, _api_retry_at = deadline, retry_at


def _get_display_version(url):
  """Read only the numeric version literal; never import or execute remote code."""
  with _cache_lock:
    if time.monotonic() < _raw_backoff_until:
      raise HistoryUnavailable(_rate_limit_message(_raw_retry_at))
  request = Request(url, headers={'User-Agent': 'StarPilot-Galaxy-VersionPicker'})
  try:
    with _open_raw_url(request, timeout=HTTP_TIMEOUT) as response:
      raw = response.read(MAX_VERSION_BYTES + 1)
    if len(raw) > MAX_VERSION_BYTES:
      raise VersionHistoryError('GitHub version metadata is too large; retry later.')
    source = raw.decode('utf-8')
    assignments = re.findall(r'^STARPILOT_DISPLAY_VERSION\b[^\r\n]*', source, re.MULTILINE)
    if len(assignments) != 1:
      raise ValueError()
    match = re.fullmatch(r"""STARPILOT_DISPLAY_VERSION[ \t]*=[ \t]*(['"])((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))\1[ \t]*(?:#[^\r\n]*)?""", assignments[0])
    if match is None:
      raise ValueError()
    return match.group(2)
  except HTTPError as error:
    error.close()
    if error.code == 404:
      return None  # Older builds can predate the display-version file.
    if error.code in (403, 429):
      if _is_quota_failure(error):
        retry_at = _retry_at(error.headers or {})
        _record_quota_backoff(retry_at, raw=True)
        raise HistoryUnavailable(_rate_limit_message(retry_at)) from None
      raise VersionHistoryError('GitHub version metadata access is limited; retry later.') from None
    failure = HistoryUnavailable if 500 <= error.code < 600 else VersionHistoryError
    raise failure('GitHub version metadata is unavailable; retry later.') from None
  except (URLError, TimeoutError, OSError, HTTPException):
    raise HistoryUnavailable('Cannot reach GitHub version metadata; check connectivity and retry.') from None
  except (ValueError, UnicodeError):
    raise VersionHistoryError('GitHub returned invalid version metadata; retry later.') from None


def _display_version(base, sha):
  # The validated origin and full SHA make this an immutable public file URL.
  repository = base.removeprefix('https://api.github.com/repos/')
  url = f'https://raw.githubusercontent.com/{repository}/{sha}/selfdrive/ui/lib/starpilot_version.py'
  # Duplicate callers share one miss; cached values do not consume download slots.
  with _request_lock('raw', url):
    with _cache_lock:
      entry = _version_cache.get(url)
      if entry is not None and time.monotonic() - entry[0] < VERSION_CACHE_TTL:
        _version_cache.move_to_end(url)
        return entry[1]
    with _version_slots:
      # Check raw quota inside the slot, including workers queued by other callers.
      value = _get_display_version(url)
    with _cache_lock:
      _version_cache[url] = (time.monotonic(), value)
      _version_cache.move_to_end(url)
      while len(_version_cache) > MAX_VERSION_CACHE_ENTRIES:
        _version_cache.popitem(last=False)
    return value


def _rate_limit_message(retry_at):
  seconds = max(0, ceil(retry_at - time.time()))
  if seconds >= 120:
    suffix = f' in about {ceil(seconds / 60)} minutes'
  elif seconds:
    suffix = f' in {seconds} seconds'
  else:
    suffix = ' later'
  return f'GitHub rate limit or public access restriction; retry{suffix}.'


def _get_json(url):
  """Serialize public API requests and recheck quota after waiting for a turn."""
  with _api_request_lock:
    return _request_json(url)


def _request_json(url):
  """Fetch one bounded public API response. Kept separate for offline tests."""
  with _cache_lock:
    if time.monotonic() < _api_backoff_until:
      raise HistoryUnavailable(_rate_limit_message(_api_retry_at))
  request = Request(url, headers={'Accept': 'application/vnd.github+json',
                                  'User-Agent': 'StarPilot-Galaxy-VersionPicker',
                                  'X-GitHub-Api-Version': '2022-11-28'})
  try:
    with _open_url(request, timeout=HTTP_TIMEOUT) as response:
      raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
      raise VersionHistoryError('GitHub metadata response is too large; retry later.')
    return json.loads(raw)
  except HTTPError as error:
    error.close()
    if error.code in (403, 429):
      retry_at = _retry_at(error.headers or {})
      # Honor the complete server deadline. Unrelated 403s do not block lookups.
      if _is_quota_failure(error):
        _record_quota_backoff(retry_at)
      failure = HistoryUnavailable if _is_quota_failure(error) else VersionHistoryError
      raise failure(_rate_limit_message(retry_at)) from None
    if error.code == 404:
      raise VersionHistoryError('GitHub repository, branch, or commit not found; refresh and retry.') from None
    failure = HistoryUnavailable if 500 <= error.code < 600 else VersionHistoryError
    raise failure('GitHub metadata is unavailable; retry later.') from None
  except (URLError, TimeoutError, OSError, HTTPException):
    raise HistoryUnavailable('Cannot reach GitHub metadata; check connectivity and retry.') from None
  except (ValueError, UnicodeError, RecursionError):
    raise VersionHistoryError('GitHub returned invalid metadata; retry later.') from None


def _json(url, fresh=False, ttl=CACHE_TTL):
  with _request_lock('api', url):
    if not fresh:
      with _cache_lock:
        entry = _cache.get(url)
        if entry is not None and time.monotonic() - entry[0] < ttl:
          _cache.move_to_end(url)
          return copy.deepcopy(entry[1])
    value = _get_json(url)
    with _cache_lock:
      _cache[url] = (time.monotonic(), copy.deepcopy(value))
      _cache.move_to_end(url)
      while len(_cache) > MAX_CACHE_ENTRIES:
        _cache.popitem(last=False)
    return value


def _git(repo_path, *args):
  try:
    result = subprocess.run(['git', '-C', str(repo_path), *args], capture_output=True, text=True, timeout=5, check=True)
    return result.stdout.strip()
  except (subprocess.SubprocessError, OSError, ValueError):
    raise VersionHistoryError('Cannot read Git origin or validate branch in this repository.') from None


def _branch(repo_path, branch):
  if not isinstance(branch, str) or not branch or len(branch) > 255 or branch.startswith('-') or '@{' in branch:
    raise VersionHistoryError('Invalid branch name.')
  if _git(repo_path, 'check-ref-format', '--branch', branch) != branch:
    raise VersionHistoryError('Invalid branch name.')
  return branch


def _sha(value, label='commit'):
  if not isinstance(value, str) or re.fullmatch(r'[0-9a-fA-F]{40}', value) is None:
    raise VersionHistoryError(f'Invalid {label}; expected a full 40-character commit SHA.')
  return value.lower()


def _repository(repo_path):
  remote = _git(repo_path, 'config', '--get', 'remote.origin.url')
  ssh = re.fullmatch(r'git@github\.com:([^/]+)/([^/]+)', remote)
  if ssh:
    owner, name = ssh.groups()
  else:
    try:
      parsed = urlsplit(remote)
    except ValueError:
      raise VersionHistoryError('Configured origin must be a public GitHub repository.') from None
    allowed = ((parsed.scheme == 'https' and parsed.netloc == 'github.com') or
               (parsed.scheme == 'ssh' and parsed.netloc == 'git@github.com'))
    parts = parsed.path.strip('/').split('/')
    if not allowed or parsed.query or parsed.fragment or len(parts) != 2:
      raise VersionHistoryError('Configured origin must be a public GitHub repository.')
    owner, name = parts
  name = name.removesuffix('.git')
  if not re.fullmatch(r'[A-Za-z0-9-]+', owner) or not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in ('.', '..'):
    raise VersionHistoryError('Configured origin must be a public GitHub repository.')
  return f'https://api.github.com/repos/{owner}/{name}'


def _head(base, branch, fresh=False):
  data = _json(f'{base}/branches/{quote(branch, safe="")}', fresh=fresh)
  try:
    if data['name'] != branch:
      raise ValueError()
    return _sha(data['commit']['sha'], 'GitHub branch head')
  except (KeyError, TypeError, ValueError):
    raise VersionHistoryError('GitHub returned invalid branch metadata; retry later.') from None


def _ancestor(base, chosen, head):
  if chosen == head:
    return
  data = _json(f'{base}/compare/{chosen}...{head}', ttl=IMMUTABLE_CACHE_TTL)
  try:
    valid = data['status'] in ('ahead', 'identical') and _sha(data['merge_base_commit']['sha'], 'GitHub merge base') == chosen
  except (KeyError, TypeError, ValueError):
    raise VersionHistoryError('GitHub returned invalid branch ancestry; retry later.') from None
  if not valid:
    raise VersionHistoryError('Selected commit is no longer in this branch history. Refresh the branch and choose again.')


def _block(base, head, page):
  data = _json(f'{base}/commits?{urlencode({"sha": head, "per_page": _BLOCK_SIZE, "page": page})}', ttl=IMMUTABLE_CACHE_TTL)
  if not isinstance(data, list) or len(data) > _BLOCK_SIZE:
    raise VersionHistoryError('GitHub returned invalid commit history; retry later.')
  rows = []
  seen = set()
  try:
    for item in data:
      sha = _sha(item['sha'], 'GitHub commit')
      message = item['commit']['message']
      date = item['commit']['committer']['date']
      if not isinstance(message, str) or not message.strip() or not isinstance(date, str) or len(date) > 64 or sha in seen:
        raise ValueError()
      if datetime.fromisoformat(date.replace('Z', '+00:00')).tzinfo is None:
        raise ValueError()
      rows.append({'sha': sha, 'subject': message.splitlines()[0][:300], 'date': date})
      seen.add(sha)
    if page == 1 and (not rows or rows[0]['sha'] != head):
      raise ValueError()
  except (KeyError, IndexError, TypeError, ValueError):
    raise VersionHistoryError('GitHub returned invalid commit metadata; retry later.') from None
  return rows


def _snapshot_path(base, branch, page, requested_head):
  key = json.dumps([base, branch, page, requested_head], separators=(',', ':')).encode()
  return SNAPSHOT_CACHE_DIR / (hashlib.sha256(key).hexdigest() + '.json')


def _snapshot_time(value):
  if not isinstance(value, str) or len(value) > 64:
    raise ValueError()
  parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
  if parsed.tzinfo is None:
    raise ValueError()
  return parsed.timestamp()


def _validate_snapshot(data, base, branch, page, requested_head):
  if (data['repository'], data['branch'], data['page'], data['requestedHead']) != (base, branch, page, requested_head):
    raise ValueError()
  if type(page) is not int or page < 1 or type(data['page']) is not int or (page > 1 and requested_head is None):
    raise ValueError()
  if requested_head is not None:
    _sha(requested_head)
  stamp = _snapshot_time(data['cachedAt'])
  if not -60 <= time.time() - stamp <= SNAPSHOT_RETENTION:
    raise ValueError()
  result = data['result']
  head = _sha(result['head'])
  if (result['branch'] != branch or type(result['page']) is not int or result['page'] != page or
      type(result['hasMore']) is not bool or result.get('cached') or (requested_head is not None and head != requested_head)):
    raise ValueError()
  rows = result['commits']
  if not isinstance(rows, list) or len(rows) > PAGE_SIZE:
    raise ValueError()
  selected, seen = [], set()
  for row in rows:
    sha = _sha(row['sha'])
    if sha in seen or not isinstance(row['subject'], str) or not row['subject'].strip() or len(row['subject']) > 300:
      raise ValueError()
    _snapshot_time(row['date'])
    clean = {'sha': sha, 'subject': row['subject'], 'date': row['date']}
    if branch.lower() == 'starpilot' or 'version' in row:
      version = row['version']
      if version is not None and (not isinstance(version, str) or len(version) > 64 or
                                 re.fullmatch(r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)', version) is None):
        raise ValueError()
      clean['version'] = version
    selected.append(clean)
    seen.add(sha)
  if page == 1 and (not selected or selected[0]['sha'] != head):
    raise ValueError()
  return {'branch': branch, 'head': head, 'page': page, 'hasMore': result['hasMore'], 'commits': selected, 'cachedAt': data['cachedAt']}


def _load_history_snapshot(base, branch, page, requested_head):
  """Return a validated disk snapshot, or None; never validates installation."""
  try:
    path = _snapshot_path(base, branch, page, requested_head)
    if SNAPSHOT_CACHE_DIR.is_symlink() or path.is_symlink():
      return None
    with path.open('rb') as stream:
      raw = stream.read(MAX_SNAPSHOT_BYTES + 1)
    if len(raw) > MAX_SNAPSHOT_BYTES:
      return None
    return _validate_snapshot(json.loads(raw), base, branch, page, requested_head)
  except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, VersionHistoryError):
    return None


def _prune_history_snapshots():
  files = []
  for path in SNAPSHOT_CACHE_DIR.glob('*.json'):
    if re.fullmatch(r'[0-9a-f]{64}\.json', path.name) is None or path.is_symlink():
      continue
    stat = path.stat()
    if stat.st_size > MAX_SNAPSHOT_BYTES or time.time() - stat.st_mtime > SNAPSHOT_RETENTION:
      path.unlink()
    else:
      files.append((stat.st_mtime, path, stat.st_size))
  files.sort()
  total = sum(entry[2] for entry in files)
  while len(files) > MAX_SNAPSHOT_FILES or total > MAX_SNAPSHOT_TOTAL_BYTES:
    _, path, size = files.pop(0)
    path.unlink()
    total -= size


def _save_history_snapshot(base, branch, page, requested_head, result, saved_at=None):
  """Best-effort atomic snapshot. saved_at is the original timezone-aware ISO timestamp."""
  temporary = None
  try:
    if saved_at is None:
      saved_at = datetime.fromtimestamp(time.time(), timezone.utc).isoformat()
    data = {'repository': base, 'branch': branch, 'page': page, 'requestedHead': requested_head,
            'cachedAt': saved_at, 'result': result}
    _validate_snapshot(data, base, branch, page, requested_head)
    raw = json.dumps(data, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    if len(raw) > MAX_SNAPSHOT_BYTES:
      return False
    with _snapshot_lock:
      if SNAPSHOT_CACHE_DIR.is_symlink():
        return False
      SNAPSHOT_CACHE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
      SNAPSHOT_CACHE_DIR.chmod(0o700)
      fd, temporary = tempfile.mkstemp(prefix='.history-', suffix='.tmp', dir=SNAPSHOT_CACHE_DIR)
      with os.fdopen(fd, 'wb') as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(raw)
      stamp = _snapshot_time(saved_at)
      os.utime(temporary, (stamp, stamp))
      os.replace(temporary, _snapshot_path(base, branch, page, requested_head))
      temporary = None
      _prune_history_snapshots()
    return True
  except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, VersionHistoryError):
    return False
  finally:
    if temporary is not None:
      try:
        os.unlink(temporary)
      except OSError:
        pass


def list_versions(repo_path, branch, page=1, head=None):
  """Return 25 commits per page; later pages require the first page's head.

  Browsing caches branch heads for up to 60 seconds, then rejects pinned heads
  removed by a force push. Immutable SHA history is cached for six hours.
  Transport/quota failures may return a labelled disk snapshot up to 30 days old.
  Installation uses resolve_version, which always fetches the branch head fresh.
  """
  branch = _branch(repo_path, branch)
  if type(page) is not int or page < 1:
    raise VersionHistoryError('Invalid history page; expected a positive integer.')
  if page > 1 and head is None:
    raise VersionHistoryError('A pinned history head is required for subsequent pages.')
  pinned_head = _sha(head, 'history head') if head is not None else None
  base = _repository(repo_path)
  try:
    result = _list_versions(base, branch, page, pinned_head)
  except HistoryUnavailable as error:
    snapshot = _load_history_snapshot(base, branch, page, pinned_head)
    if snapshot is None:
      raise
    return dict(snapshot, cached=True, cacheReason=str(error))
  _save_history_snapshot(base, branch, page, pinned_head, result)
  return result


def _saved_display_versions(base, branch, page, requested_head, resolved_head):
  # A version literal belongs to an immutable SHA. Reuse its validated saved
  # value only after the live branch head and requested commit page are checked.
  snapshot = _load_history_snapshot(base, branch, page, requested_head)
  if snapshot is None or snapshot['head'] != resolved_head:
    return {}
  return {row['sha']: row['version'] for row in snapshot['commits'] if 'version' in row}


def _list_versions(base, branch, page, pinned_head):
  requested_head = pinned_head
  current = _head(base, branch)
  if pinned_head is not None:
    _ancestor(base, pinned_head, current)
  else:
    pinned_head = current
  block_page, offset = divmod((page - 1) * PAGE_SIZE, _BLOCK_SIZE)
  rows = _block(base, pinned_head, block_page + 1)
  end = offset + PAGE_SIZE
  has_more = len(rows) > end
  if end == _BLOCK_SIZE and len(rows) == _BLOCK_SIZE:
    has_more = bool(_block(base, pinned_head, block_page + 2))
  selected = rows[offset:end]
  if branch.lower() == 'starpilot' and selected:
    saved_versions = _saved_display_versions(base, branch, page, requested_head, pinned_head)
    pending = []
    for index, row in enumerate(selected):
      if row['sha'] in saved_versions:
        selected[index] = dict(row, version=saved_versions[row['sha']])
      else:
        pending.append(index)
    if not pending:
      return {'branch': branch, 'head': pinned_head, 'page': page, 'hasMore': has_more, 'commits': selected}
    executor = ThreadPoolExecutor(max_workers=_VERSION_WORKERS)
    try:
      futures = {executor.submit(_display_version, base, selected[index]['sha']): index for index in pending}
      for future in as_completed(futures):
        index = futures[future]
        selected[index] = dict(selected[index], version=future.result())
    finally:
      # Surface the first failure promptly and cancel queued work. At most four
      # already-running downloads can finish under their existing HTTP timeout.
      executor.shutdown(wait=False, cancel_futures=True)
  return {'branch': branch, 'head': pinned_head, 'page': page, 'hasMore': has_more, 'commits': selected}


def resolve_version(repo_path, branch, commit):
  """Resolve latest freshly, or prove an exact commit belongs to that branch."""
  branch = _branch(repo_path, branch)
  pinned = commit != 'latest'
  chosen = _sha(commit) if pinned else None
  base = _repository(repo_path)
  head = _head(base, branch, fresh=True)
  if pinned:
    _ancestor(base, chosen, head)
  return {'branch': branch, 'commit': chosen if pinned else head, 'head': head, 'pinned': pinned}
