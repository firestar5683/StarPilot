"""Optional replay-control forwarding; no video, audio, or transport synchronization.

Integration contract: apply the local action independently, then call submit from
the HTTP/control thread and poll its Future. Never wait on it in an audio callback.
Nothing is contacted at import/construction, or unless enabled=True and an
explicit Galaxy peer were supplied. There is no discovery, pairing,
credential lookup, retry of writes, or launch/vehicle-control endpoint.

Galaxy's demo.available attests to a <=2 second fresh replay app status; the POST
checks that status and its own presentation session again. Its requested_* reply
only acknowledges command receipt. A subsequent status read confirms adoption.
Timeout after a POST can mean the peer applied it: report uncertainty, never
retry or roll back either target. Local playback remains the caller's concern.
"""
from concurrent.futures import Future
from dataclasses import dataclass, field
import json
import ipaddress
import math
import re
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


DISCLOSURE = 'Controls only; video and music are not synchronized.'
ACTIONS = {'demo_engagement': ('mode', ('recorded', 'engaged', 'disengaged')),
           'demo_signal': ('signal_mode', ('recorded', 'left', 'right', 'off'))}


@dataclass(frozen=True)
class GalaxyPeer:
  """Explicit Galaxy tunnel with cookie, or separately opted-in private LAN URL.

  Cookie format comes from Galaxy's /api/galaxy/session UI. This helper never
  calls that endpoint or reads credential files. The existing LAN service has no
  login check: it authorizes replay commands by offroad state and fresh session.
  allow_lan_http=True permits only a literal RFC1918 IPv4 address on port 8082,
  without credentials. It is not an authenticated/encrypted transport. The caller
  must explicitly select that local device. URLs/secrets stay out of repr.
  """
  base_url: str = field(repr=False)
  session_cookie: str | None = field(default=None, repr=False)
  name: str = 'comma'
  allow_lan_http: bool = False

  def __post_init__(self):
    try:
      url = urlsplit(self.base_url)
      plain = (not any(char.isspace() for char in self.base_url)
               and url.hostname and not url.username and not url.password
               and not url.query and not url.fragment)
      tunnel = plain and url.scheme == 'https' and url.port in (None, 443) and re.fullmatch(r'/[A-Za-z0-9]{16}/?', url.path)
      lan = False
      if plain and url.scheme == 'http' and self.allow_lan_http is True and url.port == 8082 and url.path in ('', '/'):
        address = ipaddress.IPv4Address(url.hostname)
        lan = any(address in ipaddress.IPv4Network(network) for network in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
    except (TypeError, ValueError):
      tunnel = lan = False
    if not (tunnel or lan) or type(self.allow_lan_http) is not bool:
      raise ValueError('Explicit HTTPS Galaxy tunnel or opted-in private IPv4 LAN address on port 8082 required')
    if not isinstance(self.name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', self.name):
      raise ValueError('A short peer name is required')
    if lan:
      if self.session_cookie is not None:
        raise ValueError('Credentials are not sent over LAN HTTP')
    else:
      credential = unquote(self.session_cookie) if isinstance(self.session_cookie, str) else ''
      if not re.fullmatch(re.escape(url.path.strip('/')) + r':[a-fA-F0-9]{64}', credential):
        raise ValueError('Explicit Galaxy session cookie must match the configured tunnel slug')
      object.__setattr__(self, 'session_cookie', quote(credential, safe=''))
    object.__setattr__(self, 'base_url', self.base_url.rstrip('/'))


class _NoRedirect(HTTPRedirectHandler):
  def redirect_request(self, request, fp, code, msg, headers, newurl):
    raise ValueError('Peer redirect rejected')


def _http_json(method, url, payload, headers, timeout):
  """One bounded-size response, no redirect, ambient proxy, or credential cache."""
  body = None if payload is None else json.dumps(payload).encode()
  request = Request(url, data=body, headers=headers, method=method)
  with build_opener(ProxyHandler({}), _NoRedirect()).open(request, timeout=timeout) as response:
    if response.status != 200:
      raise ValueError('Unexpected peer response')
    if response.headers.get_content_type() != 'application/json':
      raise ValueError('Expected peer JSON')
    content = response.read(65537)
    if len(content) > 65536:
      raise ValueError('Peer response too large')
    result = json.loads(content)
    if not isinstance(result, dict):
      raise ValueError('Expected peer status object')
    return result


def _session(status):
  if not isinstance(status, dict):
    raise ValueError('invalid_peer_status')
  demo = status.get('demo')
  live = status.get('live', {})
  if (status.get('available') is not True or status.get('offroad') is not True
      or (demo.get('readiness',status.get('state')) if isinstance(demo,dict) else None) not in ('READY', 'GENERATING')
      or not isinstance(demo, dict) or demo.get('available') is not True
      or (isinstance(live, dict) and live.get('enabled') is True)):
    raise ValueError('peer_not_ready_for_replay')
  # Current Galaxy omits these fields; reject contradictory richer replies too.
  if (status.get('input_mode', 'replay') != 'replay'
      or status.get('mode') in ('stored', 'stored-score', 'live')
      or status.get('route') == 'live' or status.get('judging_locked') is True):
    raise ValueError('peer_not_ready_for_replay')
  session = demo.get('session_id')
  if (not isinstance(session, str) or not 1 <= len(session) <= 256
      or any(ord(char) < 32 for char in session)
      or demo.get('mode') not in ACTIONS['demo_engagement'][1]
      or demo.get('signal_mode') not in ACTIONS['demo_signal'][1]):
    raise ValueError('invalid_peer_session')
  return session


class PairedDemoControls:
  """At most one background action; overloaded/disabled submissions finish now.

  submit(action, value) returns a Future of {targets: {name: result}, disclosure,
  music_video_synchronized: False}. Caller combines its own local target outcome.
  Results distinguish disabled/rejected/busy/failed/timed_out/acknowledged/applied.
  There is no queue of stale controls, and each action fetches the peer session.
  """
  def __init__(self, peer=None, *, enabled=False, timeout=1.5, transport=_http_json):
    if type(enabled) is not bool or (peer is not None and not isinstance(peer, GalaxyPeer)):
      raise ValueError('Explicit peer and boolean enable required')
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not .1 <= timeout <= 5:
      raise ValueError('Timeout must be between 0.1 and 5 seconds')
    if enabled and peer is None:
      raise ValueError('Enabling paired controls requires an explicit peer')
    self.peer, self.enabled, self.timeout, self.transport = peer, enabled, timeout, transport
    self._lock = threading.Lock()
    self._active = None
    self._closed = False
    self._bound_session = None
    self._write_revision = 0

  def read_status(self):
    """Read applied Galaxy state on a background thread; never from audio/HTTP.

    The first validated read pins this peer replay session. Later sessions are
    rejected until a new forwarder is constructed. Return the full validated
    JSON plus Mac receipt/request times for a separate clock consumer; those
    timestamps alone do not establish playback synchronization.
    """
    with self._lock:
      if self._closed or not self.enabled:raise ValueError('forwarder_disabled')
      if self._active is not None:raise ValueError('peer_action_in_progress')
      revision = self._write_revision
    started = time.monotonic()
    headers = {'Accept':'application/json','Cache-Control':'no-store'}
    if self.peer.session_cookie is not None:headers['Cookie']='galaxy_session='+self.peer.session_cookie
    status = self.transport('GET',self.peer.base_url+'/api/roadscore/status',None,headers,min(self.timeout,.75))
    received = time.monotonic()
    if received-started >= min(self.timeout,.75):raise TimeoutError()
    session = _session(status)
    with self._lock:
      if self._closed:raise ValueError('forwarder_disabled')
      if revision != self._write_revision or self._active is not None:raise ValueError('peer_action_in_progress')
      if self._bound_session is None:self._bound_session=session
      elif session != self._bound_session:raise ValueError('peer_session_changed')
    return dict(session_id=session,mode=status['demo']['mode'],signal_mode=status['demo']['signal_mode'],
                request_started_wall=started,received_wall=received,peer_status=status)

  def _result(self, status, action, value, *, acknowledged=False, applied=False,
              error=None, session_id=None, delivery_unknown=False):
    name = self.peer.name if self.peer else 'peer'
    return {'targets': {name: {'status': status, 'action': action, 'value': value,
                              'acknowledged': acknowledged, 'applied': applied,
                              'error': error, 'session_id': session_id,
                              'delivery_unknown': delivery_unknown}},
            'disclosure': DISCLOSURE, 'music_video_synchronized': False}

  def submit(self, action, value):
    """Nonblocking submission for a control/HTTP thread, never an audio callback."""
    future = Future()
    # A caller cancellation cannot undo a possibly delivered peer command.
    future.set_running_or_notify_cancel()
    if type(action) is not str or type(value) is not str or action not in ACTIONS or value not in ACTIONS[action][1]:
      future.set_result(self._result('rejected', action, value, error='unsupported_replay_action'))
      return future
    with self._lock:
      if self._closed or not self.enabled:
        future.set_result(self._result('disabled', action, value))
        return future
      if self._active is not None:
        future.set_result(self._result('busy', action, value, error='peer_action_in_progress'))
        return future
      operation = {'future': future, 'action': action, 'value': value,
                   'sent': False, 'acknowledged': False, 'session': None, 'settled': False}
      self._active = operation
      self._write_revision += 1
    deadline = time.monotonic() + self.timeout
    timer = threading.Timer(self.timeout, self._expire, args=(operation,))
    timer.daemon = True
    timer.start()
    threading.Thread(target=self._run, args=(operation, deadline, timer),
                     name='paired-replay-control', daemon=True).start()
    return future

  def _finish(self, operation, status, error=None, applied=False):
    with self._lock:
      if operation['settled']:
        return
      operation['settled'] = True
      result = self._result(status, operation['action'], operation['value'], error=error, applied=applied,
                            acknowledged=operation['acknowledged'], session_id=operation['session'],
                            delivery_unknown=operation['sent'] and not operation['acknowledged'])
    # Future callbacks may call submit/close; do not invoke them under our lock.
    operation['future'].set_result(result)

  def _expire(self, operation):
    self._finish(operation, 'acknowledged' if operation['acknowledged'] else 'timed_out',
                 'peer_application_unconfirmed' if operation['acknowledged'] else 'peer_timeout')

  def _run(self, operation, deadline, timer):
    def request(method, endpoint, payload=None):
      remaining = deadline - time.monotonic()
      with self._lock:
        if self._closed or operation['settled'] or remaining <= 0:
          raise TimeoutError()
        if method == 'POST':
          operation['sent'] = True
      headers = {'Accept': 'application/json', 'Content-Type': 'application/json',
                 'Cache-Control': 'no-store'}
      if self.peer.session_cookie is not None:
        headers['Cookie'] = 'galaxy_session=' + self.peer.session_cookie
      result = self.transport(method, self.peer.base_url + '/api/roadscore/' + endpoint,
                              payload, headers, min(remaining, .75))
      if time.monotonic() >= deadline:
        raise TimeoutError()
      return result

    try:
      action, value = operation['action'], operation['value']
      field_name = ACTIONS[action][0]
      session = _session(request('GET', 'status'))
      with self._lock:
        if self._bound_session is not None and session != self._bound_session:
          raise ValueError('peer_session_changed')
      operation['session'] = session
      reply = request('POST', action, {'session_id': session, field_name: value})
      if (not isinstance(reply, dict) or reply.get('requested_' + field_name) != value
          or not isinstance(reply.get('demo'), dict) or reply['demo'].get('available') is not True
          or reply['demo'].get('session_id') != session):
        raise ValueError('invalid_peer_acknowledgement')
      operation['acknowledged'] = True
      while True:
        status = request('GET', 'status')
        if _session(status) != session:
          raise ValueError('peer_session_changed')
        if status['demo'][field_name] == value:
          self._finish(operation, 'applied', applied=True)
          break
        # Only status reads are repeated. Never resend a possibly applied write.
        time.sleep(min(.05, max(0., deadline - time.monotonic())))
    except TimeoutError:
      self._expire(operation)
    except HTTPError as error:
      self._finish(operation, 'failed', 'peer_http_' + str(error.code))
    except (OSError, URLError):
      self._finish(operation, 'failed', 'peer_transport_error')
    except Exception as error:
      known = {'peer_not_ready_for_replay', 'invalid_peer_status', 'invalid_peer_session',
               'invalid_peer_acknowledgement', 'peer_session_changed'}
      self._finish(operation, 'failed', str(error) if str(error) in known else 'invalid_peer_response')
    finally:
      timer.cancel()
      with self._lock:
        if self._active is operation:
          self._active = None

  def close(self):
    """Stop accepting commands without waiting for a blocked peer transport."""
    with self._lock:
      self._closed = True
      active = self._active
    if active is not None:
      self._finish(active, 'failed', 'forwarder_closed')
