"""Runs the playlink resolver and stores the opt-in Google refresh token.

Secrets go over pipes, never arguments, environment or logs. Only an AAS token
the user chose to remember is persisted.
"""
from __future__ import annotations

import json
import os
import re
import selectors
import time
import stat
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from openpilot.starpilot.system.android_auto.play_package import RUNTIME

BINARY = RUNTIME / 'playlink'
TOKEN_PATH = Path('/data/starpilot/aa_token')
MAX_TOKEN = 3072


class PlayError(RuntimeError):
  pass


def validate_credentials(email: str, token: str) -> None:
  if not isinstance(email, str) or not email.isascii() or len(email) > 254 or not re.fullmatch(r'[^\s@]{1,200}@[^\s@]{1,120}', email):
    raise PlayError('Enter the Google account email used to sign in')
  if not isinstance(token, str) or len(token) > MAX_TOKEN or not re.fullmatch(r'(?:oauth2_4/|aas_et/)[A-Za-z0-9._~/+=-]+', token):
    raise PlayError('Paste a valid Google oauth_token or AAS token')


def validate_url(url: str) -> None:
  try:
    parsed = urlsplit(url)
    valid = (parsed.scheme == 'https' and parsed.hostname == 'play.googleapis.com' and parsed.port in (None, 443)
             and not parsed.username and not parsed.password and parsed.path == '/download/by-token/download' and not parsed.fragment)
  except (TypeError, ValueError):
    valid = False
  if not valid:
    raise PlayError('Google Play returned an invalid download link')


class GoogleRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self, req, fp, code, msg, headers, newurl):
    parsed = urlsplit(newurl)
    host = parsed.hostname or ''
    if (parsed.scheme != 'https' or parsed.port not in (None, 443) or parsed.username or parsed.password or
        not (host == 'play.googleapis.com' or host.endswith('.gvt1.com'))):
      raise PlayError('Google Play redirected outside its download servers')
    return super().redirect_request(req, fp, code, msg, headers, newurl)


def resolve(email: str, token: str, *, remember: bool = False, progress=lambda stage: None) -> dict:
  validate_credentials(email, token)
  progress('authenticating')
  # Callers only see allowlisted stage names; all other resolver output stays private.
  process = None
  output = bytearray()
  output_size = 0
  deadline = time.monotonic() + 120
  stage = 'authenticating'
  try:
    process = subprocess.Popen([str(BINARY)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    process.stdin.write(json.dumps({'email': email, 'token': token, 'remember': remember}).encode())
    process.stdin.close()
    token = ''
    with selectors.DefaultSelector() as selector:
      selector.register(process.stdout, selectors.EVENT_READ)
      while True:
        progress(stage)  # also checks cancellation while Google is responding
        if time.monotonic() >= deadline:
          raise PlayError('Google Play timed out; try signing in again')
        if not selector.select(timeout=0.5):
          continue
        chunk = os.read(process.stdout.fileno(), 4096)
        if not chunk:
          break
        output.extend(chunk)
        output_size += len(chunk)
        if output_size > 32768:
          raise PlayError('Google Play returned an invalid response')
        marker = b'{"stage":"resolving"}\n'
        if output.startswith(marker):
          del output[:len(marker)]
          stage = 'resolving'
      process.wait(timeout=max(0.01, deadline - time.monotonic()))
    if process.returncode != 0:
      raise PlayError('Google Play sign-in or delivery failed; sign in again and ensure Play terms are accepted on your account')
  except subprocess.TimeoutExpired:
    raise PlayError('Google Play timed out; try signing in again') from None
  except OSError:
    raise PlayError('Google Play support is unavailable in this build; use manual upload') from None
  finally:
    token = ''
    if process is not None:
      if process.poll() is None:
        process.kill()
      process.wait()
      process.stdout.close()
      if not process.stdin.closed:
        process.stdin.close()
  try:
    value = json.loads(output)
    if not isinstance(value, dict) or value.get('status') != 'ok':
      raise ValueError
    validate_url(value['url'])
    if remember:
      validate_credentials(email, value['aas_token'])
      if not value['aas_token'].startswith('aas_et/'):
        raise ValueError
  except (KeyError, TypeError, ValueError, PlayError):
    raise PlayError('Google Play returned an invalid response') from None
  progress('resolving')
  return {'url': value['url'], **({'aas_token': value['aas_token']} if remember else {})}


class TokenStore:
  def __init__(self, path: Path = TOKEN_PATH):
    self.path = path

  def exists(self) -> bool:
    return self.path.is_file()

  def save(self, email: str, token: str) -> None:
    validate_credentials(email, token)
    if not token.startswith('aas_et/'):
      raise PlayError('Only a refresh token can be remembered')
    self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.aa-token-', dir=self.path.parent)
    try:
      with os.fdopen(fd, 'w') as handle:
        json.dump({'email': email, 'token': token}, handle)
        handle.flush()
        os.fsync(handle.fileno())
      os.replace(name, self.path)
    finally:
      Path(name).unlink(missing_ok=True)

  def load(self) -> dict:
    fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as handle:
      info = os.fstat(handle.fileno())
      if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
        raise PlayError('Saved Google credentials must be private to the device user')
      value = json.loads(handle.read(4097))
    if not isinstance(value, dict):
      raise PlayError('Saved Google credentials are invalid')
    validate_credentials(value.get('email'), value.get('token'))
    if not value['token'].startswith('aas_et/'):
      raise PlayError('Saved Google credentials are invalid')
    return value

  def forget(self) -> None:
    self.path.unlink(missing_ok=True)
