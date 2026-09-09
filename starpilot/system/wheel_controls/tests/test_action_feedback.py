import json
from types import SimpleNamespace
import pytest
from openpilot.starpilot.common.action_feedback import ActionFeedback, visible_receipt
from openpilot.starpilot.common import favorite_slots as fav, longitudinal_mode_actions as mode
from openpilot.starpilot.common.tests.test_favorite_slots import FakeParams
from openpilot.starpilot.system.wheel_controls import wheel_controlsd as wheel


def setup(key, *, favorite=False):
  p, m = FakeParams(), FakeParams()
  p.types['GoatScream'] = fav.ParamKeyType.BOOL
  p.types['AccelerationProfile'] = fav.ParamKeyType.INT
  if favorite:
    p.put(fav.FAVORITE_SLOTS_PARAM, [dict(key=key, enabled=True)])
  else:
    wheel.set_controller_action_slot(0, key, 'old label', p)
  now = [10.0]
  return p, m, ActionFeedback(p, m, lambda: now[0]), now, 0 if favorite else 3


@pytest.mark.parametrize('favorite', [False, True])
def test_toggle_readback_and_latest_value(favorite):
  p, m, f, now, index = setup('GoatScream', favorite=favorite)
  assert f.execute(index, wheel.execute_controller_key)
  assert (f.receipt['value'], f.receipt['state']) == ('On', 'confirmed')
  assert f.execute(index, wheel.execute_controller_key)
  assert f.receipt['value'] == 'Off'
  assert visible_receipt({'last_action':f.receipt}, now[0] + 2.9)
  assert visible_receipt({'last_action':f.receipt}, now[0] + 3) is None


def test_deferred_write_never_claims_success_until_readback():
  p, m, f, now, index = setup('GoatScream')
  f.execute(index, lambda *a, **kw: True)
  assert f.receipt['state'] == 'pending'
  now[0] += 1.6; f.update()
  assert f.receipt['state'] == 'unconfirmed'


def test_deferred_write_confirmed_and_enum_label():
  p, m, f, now, index = setup('AccelerationProfile')
  p.put_int('AccelerationProfile', 0)
  f.execute(index, lambda *a, **kw: True)
  assert f.receipt['state'] == 'pending'
  p.put_int('AccelerationProfile', 1); f.update()
  assert f.receipt['state'] == 'confirmed'
  assert f.receipt['value'] == 'Eco' and f.receipt['selected'] == 1


@pytest.mark.parametrize('selected', range(3))
def test_personality_exact_result(selected):
  p, m, f, now, index = setup(wheel.CONTROLLER_ACTION_CYCLE_PERSONALITY)
  def dispatch(*a, **kw):
    p.put_int('LongitudinalPersonality', selected)
    return True
  f.execute(index, dispatch)
  assert f.receipt['selected'] == selected
  assert f.receipt['value'] == ('Aggressive','Standard','Relaxed')[selected]


@pytest.mark.parametrize('selected', mode.MODE_ORDER)
@pytest.mark.parametrize('favorite', [False, True])
def test_mode_waits_for_server_result(selected, favorite, monkeypatch):
  p, m, f, now, index = setup(mode.PREFIX+'cycle', favorite=favorite)
  callbacks = []
  monkeypatch.setattr(mode, 'request_mode_action', lambda key, on_result: callbacks.append(on_result) or True)
  f.execute(index, lambda *a, **kw: pytest.fail('Must use acknowledged mode transaction'))
  assert f.receipt['state'] == 'pending'
  callbacks[0](selected)
  assert f.receipt['state'] == 'confirmed'
  assert f.receipt['selected'] == mode.MODE_ORDER.index(selected)


def test_late_mode_reply_does_not_replace_newer_press(monkeypatch):
  p, m, f, now, index = setup(mode.PREFIX+'cycle')
  callbacks = []
  monkeypatch.setattr(mode, 'request_mode_action', lambda key, on_result: callbacks.append(on_result) or True)
  f.execute(index, None)
  wheel.set_controller_action_slot(0, 'GoatScream', 'Goat', p)
  f.execute(index, wheel.execute_controller_key)
  callbacks[0]('experimental')
  assert f.receipt['value'] == 'On'


@pytest.mark.parametrize('outcome', [False, None])
def test_busy_or_failed_mode_never_shows_success(outcome, monkeypatch):
  p, m, f, now, index = setup(mode.PREFIX+'cycle')
  def request(key, on_result):
    if outcome is None: on_result(None)
    return outcome is None
  monkeypatch.setattr(mode, 'request_mode_action', request)
  f.execute(index, None)
  assert f.receipt['state'] in ('blocked','unconfirmed')


def test_rejected_action_and_async_counter_are_distinct():
  p, m, f, now, index = setup(wheel.CONTROLLER_ACTION_ENGAGE)
  assert not f.execute(index, wheel.execute_controller_key)
  assert f.receipt['state'] == 'blocked'
  p.put_bool('IsOnroad', True)
  assert f.execute(index, wheel.execute_controller_key)
  assert f.receipt['state'] == 'requested'
  assert m.get_int('WheelControlEngageCounter') == 1


def test_hid_receipt_published_but_learning_and_testing_do_not_execute():
  p, m, f, now, index = setup('GoatScream')
  source = wheel.InputSource('/test','test','Test controller',5,1,1)
  wheel.upsert_mapping(source, 30, index, p)
  daemon = wheel.WheelControlsDaemon(p,m)
  try:
    daemon.testing = True; daemon._handle_key(source,30)
    assert daemon.feedback.receipt is None and not p.get_bool('GoatScream')
    daemon.testing = False; daemon._handle_key(source,30)
    daemon._publish_status(10)
    assert daemon.feedback.receipt['value'] == 'On'
    assert m.get(wheel.STATUS_PARAM)['last_action']['state'] == 'confirmed'
  finally:
    daemon.selector.close()


@pytest.mark.parametrize('bad', [None, {}, {'at':float('nan')}, {'at':float('inf')}, {'at':100,'state':'confirmed','title':'x','value':'y'}])
def test_malformed_or_future_receipts_not_shown(bad):
  assert visible_receipt({'last_action':bad},10) is None


@pytest.mark.parametrize('result', ['conditional_chill', None])
def test_async_request_reports_confirmed_response_or_failure(monkeypatch,result):
  monkeypatch.setattr(mode,'Thread', lambda target, **kw: SimpleNamespace(start=target))
  calls=[]
  def post(key, deadline, callback):
    if result: callback(result);return True
    raise TimeoutError()
  monkeypatch.setattr(mode,'_post_action',post)
  assert mode.request_mode_action(mode.PREFIX+'cycle',on_result=calls.append)
  assert calls == [result]
