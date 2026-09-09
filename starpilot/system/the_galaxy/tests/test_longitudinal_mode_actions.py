"""Exercise production action routes with private fake Params; no live writes."""
import ast
from pathlib import Path
from threading import Event
from time import monotonic

import pytest
from flask import Flask, jsonify, request

from openpilot.starpilot.common import longitudinal_mode_actions as actions
from test_longitudinal_mode import Params, mode

SOURCE = Path(__file__).resolve().parents[1] / "the_galaxy.py"


def payload(params, key, **extra):
  return {"key": key, "expected": {k: params.values[k] for k in mode.MODE_KEYS},
          "expires_at": monotonic()+1, "acknowledged": True, **extra}


def client_for(params, capable=True):
  setup = next(n for n in ast.parse(SOURCE.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'setup')
  routes = [n for n in setup.body if isinstance(n, ast.FunctionDef) and n.name == 'favorite_action']
  signals = []
  app = Flask(__name__)
  env = dict(app=app, request=request, jsonify=jsonify, params=params, params_memory=None,
             LONGITUDINAL_MODE_LOCK=mode.WRITE_LOCK, ModeError=mode.ModeError,
             longitudinal_mode_snapshot=mode.snapshot, set_longitudinal_mode=mode.set_mode,
             _get_longitudinal_mode_capable=lambda: capable,
             update_starpilot_toggles=lambda: signals.append(True),
             is_favorite_action_key=lambda key: key in actions.ACTION_TARGETS,
             trigger_favorite_action=lambda *_: pytest.fail('mode action reached legacy counter dispatcher'))
  exec(compile(ast.Module(body=routes, type_ignores=[]), str(SOURCE), 'exec'), env)
  return app.test_client(), signals, env


@pytest.mark.parametrize('onroad', [True, False])
@pytest.mark.parametrize('current', actions.MODE_ORDER)
@pytest.mark.parametrize('key', actions.ACTION_TARGETS)
def test_every_action_from_every_mode(onroad, current, key):
  params = Params({'IsOnroad': onroad, 'IsOffroad': not onroad,
                   'ExperimentalModeConfirmed': False,
                   **{k: k == mode.MODES[current] for k in mode.MODE_KEYS}})
  before = params.values.copy()
  client, signals, _ = client_for(params)
  response = client.post('/api/favorites/action', json=payload(params, key))
  assert response.status_code == 200, response.json
  target = actions.resolve_action_target(key, current)
  assert response.json['mode'] == target
  assert mode.snapshot(params, True)['mode'] == target
  assert params.values['ExperimentalModeConfirmed'] is False
  assert {k: v for k, v in before.items() if k not in mode.MODE_KEYS} == {k: v for k, v in params.values.items() if k not in mode.MODE_KEYS}
  assert signals == [True]
  if target == current:
    assert not params.writes


@pytest.mark.parametrize('values,capable', [({'SafeMode': True}, True), ({'SafeMode': None}, True),
  ({'IsOnroad': True}, True), ({'IsOffroad': None}, True), ({}, False)])
@pytest.mark.parametrize('key', actions.ACTION_TARGETS)
def test_guards(values, capable, key):
  params = Params(values)
  client, _, _ = client_for(params, capable)
  response = client.post('/api/favorites/action', json=payload(params, key))
  assert response.status_code == 403
  assert not params.writes


@pytest.mark.parametrize('deadline', [0, -1, True, None, 'tomorrow', float('inf')])
def test_expired_invalid_requests_never_write(deadline):
  params = Params()
  client, _, _ = client_for(params)
  response = client.post('/api/favorites/action', json={'key': actions.PREFIX + 'cycle', 'expires_at': deadline})
  assert response.status_code == 409
  assert not params.writes


def test_native_expiry_and_unknown_request():
  params = Params()
  client, _, _ = client_for(params)
  for body, status in [(None, 400), ([], 400), ({'key': 'bogus'}, 400),
                       ({'key': actions.PREFIX+'cycle', 'expires_at': monotonic()+100}, 409),
                       (payload(params, actions.PREFIX+'cycle'), 200)]:
    assert client.post('/api/favorites/action', json=body).status_code == status


@pytest.mark.parametrize('fail_at', [1, 2, 3])
def test_partial_write_failure_is_not_retried(fail_at):
  params = Params(fail_at=fail_at)
  client, signals, _ = client_for(params)
  response = client.post('/api/favorites/action', json=payload(params, actions.PREFIX+'experimental'))
  assert response.status_code == 500
  assert len(params.writes) == fail_at
  assert signals == [True]


def test_competing_writer_rejected_without_retry():
  params = Params()
  client, _, env = client_for(params)
  def stale_snapshot(*args):
    snapshot = mode.snapshot(*args)
    params.values['ConditionalChill'] = True
    return snapshot
  env['longitudinal_mode_snapshot'] = stale_snapshot
  assert client.post('/api/favorites/action', json=payload(params, actions.PREFIX+'cycle')).status_code == 409
  assert not params.writes


def test_delayed_request_expires_behind_server_lock():
  from threading import Thread
  from time import sleep
  params = Params()
  client, _, _ = client_for(params)
  entered = Event()
  results = []
  body = payload(params, actions.PREFIX+'cycle', expires_at=monotonic()+0.05)
  def send():
    entered.set()
    results.append(client.post('/api/favorites/action', json=body).status_code)
  with mode.WRITE_LOCK:
    thread = Thread(target=send)
    thread.start()
    assert entered.wait(1)
    sleep(0.1)
  thread.join(2)
  assert results == [409]
  assert not params.writes


@pytest.mark.parametrize('key', [actions.PREFIX+'experimental', actions.PREFIX+'cycle'])
def test_explicit_selection_acknowledgement_required(key):
  params = Params({'ConditionalExperimental':False,'ExperimentalModeConfirmed':False})
  client, _, _ = client_for(params)
  assert client.post('/api/favorites/action', json=payload(params, key, acknowledged=False)).status_code == 409
  assert not params.writes
  assert client.post('/api/favorites/action', json=payload(params, key)).status_code == 200
  assert params.values['ExperimentalModeConfirmed'] is False


def test_async_transport_does_not_block_queue_or_retry(monkeypatch):
  started, finish = Event(), Event()
  calls = []
  def failed(key, deadline):
    calls.append(key)
    started.set()
    assert finish.wait(2)
    raise OSError('uncertain response')
  monkeypatch.setattr(actions, '_post_action', failed)
  real_thread = actions.Thread
  workers = []
  def worker(**kwargs):
    t = real_thread(**kwargs)
    workers.append(t)
    return t
  monkeypatch.setattr(actions, 'Thread', worker)
  assert actions.request_mode_action(actions.PREFIX+'cycle')
  assert started.wait(1)
  assert not actions.request_mode_action(actions.PREFIX+'cycle')
  assert not actions.request_mode_action('unknown')
  finish.set()
  workers[0].join(2)
  assert not workers[0].is_alive()
  assert calls == [actions.PREFIX+'cycle']
  assert not actions._PENDING.locked()


def test_transport_only_targets_loopback_and_expires(monkeypatch):
  calls = []
  class Response:
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def read(self): return b'{"mode":"chill","locked":false,"values":{"ExperimentalMode":false,"ConditionalExperimental":false,"ConditionalChill":false}}'
  class Opener:
    def open(self, request, timeout):
      import json
      calls.append((request.full_url, json.loads(request.data) if request.data else None, timeout))
      return Response()
  def opener(handler):
    assert handler.proxies == {}
    return Opener()
  monkeypatch.setattr(actions, 'build_opener', opener)
  assert actions._post_action(actions.PREFIX+'chill', monotonic()+1)
  assert calls[0][0] == 'http://127.0.0.1:8082/api/longitudinal_mode'
  url, body, timeout = calls[1]
  assert url == 'http://127.0.0.1:8082/api/favorites/action'
  assert 0 < body['expires_at'] - monotonic() <= 1
  assert timeout == 1


@pytest.mark.parametrize('key,current,target', [
  (actions.PREFIX+'cycle','chill','experimental'),
  (actions.PREFIX+'experimental','chill','experimental'),
  ('ConditionalChill','conditional_chill','chill'),
  ('ConditionalChill','chill','conditional_chill'),
])
def test_native_request_acknowledgement_reaches_production_transaction(monkeypatch,key,current,target):
  import io,json
  params = Params({'ExperimentalModeConfirmed':False, **{k:k==mode.MODES[current] for k in mode.MODE_KEYS}})
  client, _, _ = client_for(params)
  posts=[]
  class Opener:
    def open(self,request,timeout):
      if request.get_method()=='GET':return io.BytesIO(json.dumps(mode.snapshot(params,True)).encode())
      body=json.loads(request.data);posts.append(body)
      response=client.post('/api/favorites/action',json=body)
      assert response.status_code==200,response.json
      return io.BytesIO(response.data)
  monkeypatch.setattr(actions,'build_opener',lambda *_:Opener())
  assert actions._post_action(key,monotonic()+1)
  assert len(posts)==1 and posts[0]['acknowledged'] is True
  assert mode.snapshot(params,True)['mode']==target
  assert params.values['ExperimentalModeConfirmed'] is False
