import time

from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.controllers.wheel_actions import WheelConsumer, WheelPublisher
from openpilot.starpilot.controllers.mode_actions import ModeActionPublisher, ModeActionOwner, publish_switchback, ModeIntent
from openpilot.starpilot.controllers.tests.test_wheel_actions import candidate, services, DRIVE, NOW


def test_actual_card_and_ui_publisher_coexist_and_modes_use_only_ui_channel():
  with OpenpilotPrefix():
    params = Params()
    _, cp = candidate(False)
    params.put('DistanceButtonControl', 8, block=True)
    card = messaging.PubMaster(['slcCruiseEvent'])
    ui = messaging.PubMaster(['slcAction'])
    ui_wheel = messaging.sub_sock('slcCruiseEvent', timeout=1000)
    planner_wheel = messaging.sub_sock('slcCruiseEvent', timeout=1000)
    planner_ui = messaging.sub_sock('slcAction', timeout=1000)
    time.sleep(0.05)
    producer = WheelPublisher(params)
    producer.publish((('DistanceButtonControl', 8),), cp, card, now_ns=NOW, drive_id=DRIVE,
                     source_car_ns=NOW, source_control_ns=NOW)
    sm = services(cp)
    one = messaging.recv_one(ui_wheel)
    two = messaging.recv_one(planner_wheel)
    assert WheelConsumer().accept(one, params, cp, sm, now_ns=NOW).action == 8
    assert WheelConsumer().accept(two, params, cp, sm, now_ns=NOW).action == 8
    sm['selfdriveState'] = type('State', (), {'enabled': True})()
    status = publish_switchback(None, ModeIntent(DRIVE, False, False), session='a' * 32,
                               sequence=1, now_ns=NOW, source_car_control_ns=NOW)
    sm['slcState'] = status.slcState
    for name in ('selfdriveState', 'slcState'):
      sm.logMonoTime[name], sm.recv_time[name] = NOW, NOW / 1e9
      sm.seen[name] = sm.alive[name] = sm.valid[name] = True
    request = ModeActionPublisher()
    assert request.dispatch('traffic', sm, cp, ui, now_ns=NOW)
    event = messaging.recv_one(planner_ui)
    assert str(event.slcAction.kind) == 'trafficModeToggle'
    assert ModeActionOwner().update(event, sm, cp, now_ns=NOW)
