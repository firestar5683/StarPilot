import math
from types import SimpleNamespace as NS

import pytest

from openpilot.cereal import messaging
from openpilot.common.params import Params
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.starpilot.controllers.coast import CoastOwner, CoastRuntime
from openpilot.starpilot.controllers.wheel_actions import WheelPublisher
from openpilot.starpilot.controllers.tests.test_wheel_actions import Publisher, DRIVE, NOW
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import messages


def sample(owner, **changes):
  values = {'admitted': True, 'active': True, 'gas': False, 'brake': False, 'speed_mps': 20.0,
                'target_mps': 20.0, 'delta_mps': 2.0, 'pitch': 0.0, 'lead_relevant': False, 'stop_context': False}
  values.update(changes)
  return owner.sample(**values)


def test_original_pulse_hysteresis_grade_and_effective_target():
  owner = CoastOwner()
  assert owner.toggle(14, long_active=True)
  assert sample(owner).speed_ceiling_mps == 18.0
  assert sample(owner, speed_mps=18.26).pulse_coasting
  assert not sample(owner, speed_mps=18.25).pulse_coasting
  assert not sample(owner, speed_mps=19.74).pulse_coasting
  assert sample(owner, speed_mps=19.75).pulse_coasting
  assert not sample(owner, pitch=math.radians(3)).pulse_coasting
  assert not sample(owner, pitch=None).pulse_coasting
  assert not sample(owner, pitch=math.radians(2.51)).pulse_coasting
  assert sample(owner, pitch=math.radians(2.5)).pulse_coasting
  assert sample(owner, target_mps=15.0).speed_ceiling_mps == 13.0


@pytest.mark.parametrize('restriction', [{'lead_relevant': True}, {'stop_context': True}, {'target_mps': 5.0},
                                         {'target_mps': 4.0}, {'delta_mps': 0.0}])
def test_pulse_cannot_coast_into_lead_stop_or_low_target(restriction):
  owner = CoastOwner()
  owner.toggle(14, long_active=True)
  assert not sample(owner, **restriction).pulse_coasting


def test_force_coast_driver_reset_inactive_freeze_and_source_loss():
  owner = CoastOwner()
  owner.toggle(2, long_active=True)
  owner.toggle(14, long_active=True)
  assert sample(owner).force_decel
  assert sample(owner, active=False).brake_floor is None
  assert owner.force_coast and owner.pulse_glide
  assert not sample(owner, gas=True).force_decel
  assert owner.pulse_glide
  sample(owner, admitted=False)
  assert not owner.pulse_glide and not owner.force_coast


def run_planner(params, cp, *, action=0, lead=False):
  class Services(dict):
    pass
  runtime, publisher = CoastRuntime(), WheelPublisher()
  sender = Publisher()
  planner = LongitudinalPlanner(cp, init_v=20.0)
  for frame in range(65):
    now = NOW + frame * 50_000_000
    data, _ = messages(lead=lead)
    sm = Services(data)
    sm['deviceState'] = NS(started=True, startedMonoTime=DRIVE)
    sm['carState'].canValid = True
    sm['carState'].vCruise = 100.0
    sm['carControl'].enabled = sm['carControl'].longActive = True
    sm.logMonoTime = dict.fromkeys(sm, now)
    sm.recv_time = dict.fromkeys(sm, now / 1e9)
    sm.seen = sm.valid = sm.alive = dict.fromkeys(sm, True)
    if frame == 0 and action:
      params.put('DistanceButtonControl', action, block=True)
      command = (('DistanceButtonControl', action),)
    else:
      command = (('', 0),)
    publisher.publish(command, cp, sender, now_ns=now, drive_id=DRIVE, source_car_ns=now, source_control_ns=now)
    runtime.receive(messaging.log_from_bytes(sender.events[-1][1]), params, cp, sm, now_ns=now)
    planner.update(sm, now_ns=now, drive_id=DRIVE, wheel_coast=(runtime, params))
  return planner, runtime


def test_actual_wheel_receipt_changes_cruise_but_preserves_native_mpc_lead_braking(tmp_path):
  params = Params(str(tmp_path))
  cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  ordinary, _ = run_planner(params, cp)
  coast, owner = run_planner(params, cp, action=2)
  assert owner.owner.force_coast
  assert coast.a_cruise < ordinary.a_cruise
  assert coast.mpc.params[0, 4] == ordinary.mpc.params[0, 4]
  lead, _ = run_planner(params, cp, action=14, lead=True)
  native_lead, _ = run_planner(params, cp, lead=True)
  assert lead.output_a_target == pytest.approx(native_lead.output_a_target)
  assert lead.output_a_target < lead.a_cruise
