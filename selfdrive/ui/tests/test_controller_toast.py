import os
os.environ.setdefault('SCALE', '1')
from types import SimpleNamespace
import pytest
from cereal import log, custom
from openpilot.selfdrive.ui import controller_toast as toast


@pytest.mark.parametrize('width,height', [(536,240),(2160,1080)])
def test_card_is_inside_both_displays(width,height):
  x,y,w,h,small = toast.toast_geometry(width,height)
  assert 0 <= x < x+w <= width and 0 <= y < y+h <= height
  assert h < height/2


@pytest.mark.parametrize('service', ['selfdriveState', 'starpilotSelfdriveState'])
def test_alert_priority_expiry_and_no_replay(monkeypatch, service):
  now=[10.5]
  receipt=dict(id=1,at=10,title='Driving personality / selected',value='Standard',state='confirmed')
  memory=SimpleNamespace(get=lambda key: {'last_action':receipt})
  renderer=toast.ControllerToast(memory)
  class SM(dict):
    valid={'selfdriveState':True, 'starpilotSelfdriveState':True}
    alive=dict(valid)
  ss=SimpleNamespace(alertSize=log.SelfdriveState.AlertSize.none)
  sp=SimpleNamespace(alertSize=custom.StarPilotSelfdriveState.AlertSize.none)
  state=SimpleNamespace(started=True,sm=SM(selfdriveState=ss, starpilotSelfdriveState=sp),traffic_mode_enabled=False)
  current=state.sm[service]
  sizes=log.SelfdriveState.AlertSize if service == 'selfdriveState' else custom.StarPilotSelfdriveState.AlertSize
  rendered=[]
  monkeypatch.setattr(toast,'monotonic',lambda:now[0])
  monkeypatch.setattr(toast,'draw_receipt',lambda *args,**kw:rendered.append(args[0]['id']))
  monkeypatch.setattr(toast.gui_app,'request_high_fps',lambda:None)
  renderer.render(state);assert rendered == [1]
  current.alertSize=sizes.small
  renderer.render(state);assert rendered == [1]
  current.alertSize=sizes.none
  renderer.render(state);assert rendered == [1]
  receipt=dict(receipt,id=2,at=11);now[0]=11.5
  renderer.render(state);assert rendered == [1,2]
  now[0]=14.1;renderer.render(state);assert rendered == [1,2]


def test_missing_driving_state_suppresses_receipt(monkeypatch):
  receipt=dict(id=1,at=10,title='Action',value='On',state='confirmed')
  renderer=toast.ControllerToast(SimpleNamespace(get=lambda key: {'last_action':receipt}))
  state=SimpleNamespace(started=True,sm=SimpleNamespace(valid={}),traffic_mode_enabled=False)
  monkeypatch.setattr(toast,'monotonic',lambda:11)
  monkeypatch.setattr(toast,'draw_receipt',lambda *args,**kw:pytest.fail('Must not cover unknown alerts'))
  renderer.render(state)


@pytest.mark.parametrize('service', ['selfdriveState', 'starpilotSelfdriveState'])
@pytest.mark.parametrize('status', ['valid', 'alive'])
def test_unavailable_alert_stream_suppresses_without_replay(monkeypatch, service, status):
  receipt=dict(id=1,at=10,title='Action',value='On',state='confirmed')
  renderer=toast.ControllerToast(SimpleNamespace(get=lambda key: {'last_action':receipt}))
  class SM(dict):
    valid={'selfdriveState':True, 'starpilotSelfdriveState':True}
    alive=dict(valid)
  sm=SM(selfdriveState=SimpleNamespace(alertSize=log.SelfdriveState.AlertSize.none),
        starpilotSelfdriveState=SimpleNamespace(alertSize=custom.StarPilotSelfdriveState.AlertSize.none))
  getattr(sm, status)[service]=False
  state=SimpleNamespace(started=True,sm=sm,traffic_mode_enabled=False)
  monkeypatch.setattr(toast,'monotonic',lambda:11)
  monkeypatch.setattr(toast,'draw_receipt',lambda *args,**kw:pytest.fail('Unavailable alerts must suppress this receipt'))
  renderer.render(state)
  getattr(sm, status)[service]=True
  renderer.render(state)
