"""Toyota native gas withdrawal may precede its parsed host pedal edge.

Host tests use real SelfdriveD/Controls constructors and genuine event processing;
CAN acquisition, perception, clocks and serialized native peers are fixtures.
The separate native RX/TX test proves Toyota's actual independent mask semantics
without setting controlsAllowed or a permission mask.
"""
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from opendbc.can import CANPacker
from opendbc.car import structs
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR
from opendbc.safety.tests.libsafety import libsafety_py
from openpilot.cereal import log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as callers

IDENTITIES = (CAR.TOYOTA_COROLLA_TSS2, CAR.TOYOTA_RAV4_TSS2, CAR.TOYOTA_PRIUS)


def params(identity):
  fw, fp = [], {0: {}, 1: {}, 2: {}}
  if identity == CAR.TOYOTA_PRIUS:
    fp[0][0x2FF] = 8
    fw = [structs.CarParams.CarFw.new_message(ecu=structs.CarParams.Ecu.eps,
                                             fwVersion=b'8965B47070' + bytes(6))]
  return CarInterface.get_params(identity, fp, fw, False, False, False)


def state():
  observed = callers.car_state()
  observed.cruiseState.enabled = observed.cruiseState.available = True
  observed.cruiseState.speed = observed.cruiseState.speedCluster = 25.
  return observed


def setup_callers(cleanup, identity):
  cleanup.enter_context(OpenpilotPrefix())
  cleanup.enter_context(patch.dict('os.environ', {'SIMULATION': '0', 'REPLAY': '0'}))
  case = callers.IoniqAvailabilityTests(methodName='runTest')
  cleanup.callback(case.doCleanups)
  sd, controls, drive = case._authority_callers(True, cp=params(identity), genuine_events=True)
  for tick in range(10):
    axis, host, command = drive(tick, observed_state=state())
    assert axis.lateralActive and axis.longitudinalActive and command.latActive and command.longActive
    assert host.enabled and not sd.aol_authority_lost
  return sd, controls, drive


@pytest.mark.parametrize('identity', IDENTITIES)
def test_native_gas_mask_before_host_pedal_keeps_real_lateral_grant(identity):
  with ExitStack() as cleanup:
    sd, _, drive = setup_callers(cleanup, identity)
    # Production10Hz Panda publication and independent mask arrive before CAN's
    # host gas sample. Toyota legitimately keeps overall controlsAllowed true.
    axis, host, command = drive(10, observed_state=state(), native_request_long=True,
                                long_allowed=False, panda_controls_allowed=True)
    assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names, 'TOYOTA_NATIVE_GAS_ORDERING'
    assert host.enabled and axis.lateralActive and command.latActive
    assert not axis.longitudinalActive and not command.longActive
    for tick in range(11, 31):
      axis, host, command = drive(tick, observed_state=state(), gas=True,
                                  native_request_long=True, long_allowed=False, panda_controls_allowed=True)
      assert host.enabled and axis.lateralActive and command.latActive
      assert not axis.longitudinalActive and not command.longActive
      assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
    # Releasing gas cannot invent LONG before its actual native grant returns.
    axis, _, command = drive(31, observed_state=state(), native_request_long=True,
                              long_allowed=False, panda_controls_allowed=True)
    assert axis.lateralActive and command.latActive and not command.longActive
    axis, host, command = drive(32, observed_state=state(), native_request_long=True,
                                long_allowed=True, panda_controls_allowed=True)
    assert host.enabled and axis.lateralActive and axis.longitudinalActive
    assert command.latActive and command.longActive


@pytest.mark.parametrize('fault', ('lat_denied', 'native_invalid', 'rx_fault', 'relay_fault', 'proof_missing'))
def test_toyota_other_faults_still_withdraw_immediately(fault):
  with ExitStack() as cleanup:
    sd, _, drive = setup_callers(cleanup, CAR.TOYOTA_COROLLA_TSS2)
    kwargs = {'observed_state': state(), 'native_request_long': True, 'long_allowed': False, 'panda_controls_allowed': True}
    if fault == 'lat_denied':
      kwargs['allowed'] = False
    elif fault == 'native_invalid':
      kwargs['native_valid'] = False
    elif fault == 'rx_fault':
      kwargs['panda_fault'] = True
    elif fault == 'relay_fault':
      kwargs['relay_fault'] = True
    else:
      sd.aol_published_input_proof = None
    axis, host, command = drive(10, **kwargs)
    assert log.OnroadEvent.EventName.controlsMismatch in sd.events.names
    assert not host.enabled and not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive


def test_toyota_persistent_controls_allowed_loss_keeps_original_counter():
  with ExitStack() as cleanup:
    sd, _, drive = setup_callers(cleanup, CAR.TOYOTA_COROLLA_TSS2)
    for tick in range(10, 221):
      axis, host, command = drive(tick, observed_state=state(), native_request_long=True,
                                  long_allowed=False, panda_controls_allowed=False)
      assert not axis.longitudinalActive and not command.longActive
      if log.OnroadEvent.EventName.controlsMismatch in sd.events.names:
        break
      assert host.enabled and axis.lateralActive and command.latActive
    assert sd.mismatch_counter >= 200
    assert log.OnroadEvent.EventName.controlsMismatch in sd.events.names
    assert not host.enabled and not command.latActive


@pytest.mark.parametrize('word', (73, 4169))
def test_actual_native_gas_withdraws_only_long_while_overall_controls_stays_true(word):
  safety = libsafety_py.libsafety
  packer = CANPacker('toyota_nodsu_pt_generated')
  safety.set_alternative_experience(32)
  assert safety.set_safety_hooks(structs.CarParams.SafetyModel.toyota, word) == 0
  # Synthetic native clock/USB heartbeat/request transport; no permission setter.
  safety.set_timer(1_000_000)
  safety.set_aol_test_heartbeat(True)
  def rx(name, fields):
    address, data, bus = packer.make_can_msg(name, 0, fields)
    assert safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data))
  def tx(name, fields):
    address, data, bus = packer.make_can_msg(name, 0, fields)
    return bool(safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data)))
  try:
    for name, fields in (
      ('WHEEL_SPEEDS', {f'WHEEL_SPEED_{w}': 72. for w in ('FL', 'FR', 'RL', 'RR')}),
      ('STEER_TORQUE_SENSOR', {}), ('BRAKE_MODULE', {}),
      ('PCM_CRUISE_2', {'MAIN_ON': 1}), ('GEAR_PACKET', {'GEAR': 0}),
      ('BODY_CONTROL_STATE', {'SEATBELT_DRIVER_UNLATCHED': 0}), ('EPS_STATUS', {'LKA_STATE': 1}),
      ('PCM_CRUISE', {'CRUISE_ACTIVE': 1, 'GAS_RELEASED': 1}),
    ):
      rx(name, fields)
    safety.aol_set_host_request(3)
    assert safety.get_controls_allowed() and safety.safety_config_valid()
    assert safety.aol_get_permission_mask() == 3
    rx('PCM_CRUISE', {'CRUISE_ACTIVE': 1, 'GAS_RELEASED': 0})
    assert safety.get_controls_allowed() and safety.safety_config_valid()
    assert safety.aol_get_permission_mask() == 1
    assert not tx('ACC_CONTROL', {'ACCEL_CMD': .5})
    assert tx('ACC_CONTROL', {'ACCEL_CMD': 0.})
    assert tx('STEERING_LKA', {'STEER_TORQUE_CMD': 0, 'STEER_REQUEST': 1})
  finally:
    safety.set_alternative_experience(0)
    safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)
