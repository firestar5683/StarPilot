import os
import math
from types import SimpleNamespace
import hypothesis.strategies as st
import pytest
from hypothesis import Phase, given, settings
from collections.abc import Callable
from typing import Any

from cereal import custom
from opendbc.can import CANParser
from opendbc.car import Bus, DT_CTRL, CanData, structs
from opendbc.car.car_helpers import _apply_disable_openpilot_long, interfaces
from opendbc.car.chrysler.carcontroller import CarController as ChryslerCarController
from opendbc.car.chrysler.carstate import CarState as ChryslerCarState
from opendbc.car.chrysler.interface import CarInterface as ChryslerCarInterface
from opendbc.car.chrysler.values import CAR as CHRYSLER_CAR, DBC as CHRYSLER_DBC, ChryslerSafetyFlags, ChryslerStarPilotFlags
from opendbc.car.fingerprints import FW_VERSIONS
from opendbc.car.fw_versions import FW_QUERY_CONFIGS
from opendbc.car.hyundai.interface import CarInterface as HyundaiCarInterface
from opendbc.car.hyundai.values import CAR as HYUNDAI_CAR, HyundaiStarPilotSafetyFlags
from opendbc.car.gm.values import CAR as GM_CAR, CanBus as GMCanBus, GMSafetyFlags
from opendbc.car.interfaces import CarInterfaceBase, CarStateBase, get_interface_attr
from opendbc.car.mock.values import CAR as MOCK
from opendbc.car.toyota.values import CAR as TOYOTA_CAR, ToyotaSafetyFlags
from opendbc.car.values import PLATFORMS

DrawType = Callable[[st.SearchStrategy], Any]

ALL_ECUS = {ecu for ecus in FW_VERSIONS.values() for ecu in ecus.keys()}
ALL_ECUS |= {ecu for config in FW_QUERY_CONFIGS.values() for ecu in config.extra_ecus}

ALL_REQUESTS = {tuple(r.request) for config in FW_QUERY_CONFIGS.values() for r in config.requests}

# From panda/python/__init__.py
DLC_TO_LEN = [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64]

MAX_EXAMPLES = int(os.environ.get('MAX_EXAMPLES', '15'))


class DummyCarState(CarStateBase):
  def __init__(self, CP: structs.CarParams, FPCP: custom.StarPilotCarParams):
    super().__init__(CP, FPCP)
    self.next_button_events: list[structs.CarState.ButtonEvent] = []

  def update(self, can_parsers, starpilot_toggles):
    ret = structs.CarState()
    ret.buttonEvents = list(self.next_button_events)
    return ret, custom.StarPilotCarState.new_message()


class DummyCarController:
  def __init__(self, dbc_names, CP):
    self.CP = CP

  def update(self, CC, CS, now_nanos, starpilot_toggles=None):
    return structs.CarControl.Actuators(), []


class DummyCarInterface(CarInterfaceBase):
  CarState = DummyCarState
  CarController = DummyCarController

  @staticmethod
  def _get_params(ret, candidate, fingerprint, car_fw, alpha_long, is_release, docs):
    return ret


def get_test_starpilot_toggles() -> SimpleNamespace:
  return SimpleNamespace(
    always_on_lateral_lkas=False,
    car_model="",
    cluster_offset=1.0,
    disable_openpilot_long=False,
    force_fingerprint=False,
    lock_doors=False,
    reverse_cruise_increase=False,
    sng_hack=False,
    subaru_sng=False,
    subaru_sng_manual_parking_brake=False,
    tesla_cooperative_steering=False,
    unlock_doors=False,
    vEgoStopping=0.5,
    volt_sng=False,
  )


def get_fuzzy_car_interface(car_name: str, draw: DrawType) -> CarInterfaceBase:
  # Fuzzy CAN fingerprints and FW versions to test more states of the CarInterface
  fingerprint_strategy = st.fixed_dictionaries({0: st.dictionaries(st.integers(min_value=0, max_value=0x800),
                                                                   st.sampled_from(DLC_TO_LEN))})

  # only pick from possible ecus to reduce search space
  car_fw_strategy = st.lists(st.builds(
    lambda fw, req: structs.CarParams.CarFw(ecu=fw[0], address=fw[1], subAddress=fw[2] or 0, request=req),
    st.sampled_from(sorted(ALL_ECUS)),
    st.sampled_from(sorted(ALL_REQUESTS)),
  ))

  params_strategy = st.fixed_dictionaries({
    'fingerprints': fingerprint_strategy,
    'car_fw': car_fw_strategy,
    'alpha_long': st.booleans(),
  })

  params: dict = draw(params_strategy)
  # reduce search space by duplicating CAN fingerprints across all buses
  params['fingerprints'] |= {key + 1: params['fingerprints'][0] for key in range(6)}

  # initialize car interface
  CarInterface = interfaces[car_name]
  starpilot_toggles = get_test_starpilot_toggles()
  car_params = CarInterface.get_params(car_name, params['fingerprints'], params['car_fw'],
                                       alpha_long=params['alpha_long'], is_release=False, docs=False,
                                       starpilot_toggles=starpilot_toggles)
  fp_car_params = CarInterface.get_starpilot_params(car_name, params['fingerprints'], params['car_fw'], car_params, starpilot_toggles)
  car_interface = CarInterface(car_params, fp_car_params)
  car_interface.starpilot_toggles = starpilot_toggles
  return car_interface


class TestCarInterfaces:
  def test_distance_button_state_tracks_gap_adjust_edges(self):
    CP = structs.CarParams()
    CP.carFingerprint = MOCK.MOCK
    FPCP = custom.StarPilotCarParams.new_message()
    car_interface = DummyCarInterface(CP, FPCP)

    pressed_event = structs.CarState.ButtonEvent(pressed=True, type=structs.CarState.ButtonEvent.Type.gapAdjustCruise)
    released_event = structs.CarState.ButtonEvent(pressed=False, type=structs.CarState.ButtonEvent.Type.gapAdjustCruise)

    car_interface.CS.next_button_events = [pressed_event]
    _, fp_ret = car_interface.update([], get_test_starpilot_toggles())
    assert fp_ret.distancePressed

    car_interface.CS.next_button_events = []
    _, fp_ret = car_interface.update([], get_test_starpilot_toggles())
    assert fp_ret.distancePressed

    car_interface.CS.next_button_events = [released_event]
    _, fp_ret = car_interface.update([], get_test_starpilot_toggles())
    assert not fp_ret.distancePressed

  def test_onroad_distance_button_does_not_replace_native_button_events(self):
    CP = structs.CarParams()
    CP.carFingerprint = MOCK.MOCK
    FPCP = custom.StarPilotCarParams.new_message()
    car_interface = DummyCarInterface(CP, FPCP)
    car_interface.params_memory = SimpleNamespace(get_bool=lambda key: True)

    native_event = structs.CarState.ButtonEvent(pressed=True, type=structs.CarState.ButtonEvent.Type.decelCruise)
    car_interface.CS.next_button_events = [native_event]

    ret, fp_ret = car_interface.update([], get_test_starpilot_toggles())

    assert any(be.type == structs.CarState.ButtonEvent.Type.decelCruise and be.pressed for be in ret.buttonEvents)
    assert any(be.type == structs.CarState.ButtonEvent.Type.gapAdjustCruise and be.pressed for be in ret.buttonEvents)
    assert fp_ret.distancePressed

  def test_chrysler_missing_lkas_signal_defaults_unpressed(self):
    assert not ChryslerCarState.get_lkas_button({"TRACTION_BUTTON": {"TRACTION_OFF": 1}}, is_ram=False)
    assert ChryslerCarState.get_lkas_button({"TRACTION_BUTTON": {"TOGGLE_LKAS": 1}}, is_ram=False)
    assert ChryslerCarState.get_lkas_button({
      "Center_Stack_1": {"LKAS_Button": 0},
      "Center_Stack_2": {"LKAS_Button": 1},
    }, is_ram=True)

  def test_chrysler_wd_mod_enables_steer_to_zero(self):
    fingerprint = {bus: {} for bus in range(8)}
    fingerprint[0][0x4FF] = 8
    toggles = get_test_starpilot_toggles()

    car_params = ChryslerCarInterface.get_params(
      CHRYSLER_CAR.CHRYSLER_PACIFICA_2020,
      fingerprint,
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=toggles,
    )
    assert car_params.minSteerSpeed > 0.

    fp_car_params = ChryslerCarInterface.get_starpilot_params(
      CHRYSLER_CAR.CHRYSLER_PACIFICA_2020,
      fingerprint,
      [],
      car_params,
      toggles,
    )
    assert fp_car_params.flags & ChryslerStarPilotFlags.NO_MIN_STEERING_SPEED
    assert car_params.minSteerSpeed == 0.

    controller = ChryslerCarController({Bus.pt: CHRYSLER_DBC[car_params.carFingerprint][Bus.pt]}, car_params)
    controller.FPCP = fp_car_params
    controller.frame = 202

    CC = structs.CarControl()
    CC.latActive = True
    CC.actuators.torque = 0.1
    CC = CC.as_reader()
    CS = SimpleNamespace(
      out=SimpleNamespace(vEgo=0.0, steeringTorqueEps=0.0, gearShifter=structs.CarState.GearShifter.drive),
      lkas_car_model=-1,
      button_counter=0,
      button_message="CRUISE_BUTTONS",
      auto_high_beam=0,
    )
    _, can_sends = controller.update(CC, CS, 0, toggles)

    lkas_parser = CANParser(CHRYSLER_DBC[car_params.carFingerprint][Bus.pt], [("LKAS_COMMAND", 50)], 0)
    lkas_parser.update([0, can_sends])
    assert lkas_parser.vl["LKAS_COMMAND"]["LKAS_CONTROL_BIT"] == 1

  @pytest.mark.parametrize("candidate", (CHRYSLER_CAR.JEEP_GRAND_CHEROKEE, CHRYSLER_CAR.JEEP_GRAND_CHEROKEE_2019))
  def test_jeep_brake_hold_safety_capability_is_provisioned(self, candidate):
    car_params = ChryslerCarInterface.get_params(
      candidate,
      {bus: {} for bus in range(8)},
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=get_test_starpilot_toggles(),
    )

    assert car_params.safetyConfigs[0].safetyParam & ChryslerSafetyFlags.JEEP_BRAKE_HOLD.value

  def test_jeep_brake_hold_safety_capability_is_not_provisioned_for_non_jeep(self):
    car_params = ChryslerCarInterface.get_params(
      CHRYSLER_CAR.CHRYSLER_PACIFICA_2020,
      {bus: {} for bus in range(8)},
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=get_test_starpilot_toggles(),
    )

    assert not car_params.safetyConfigs[0].safetyParam & ChryslerSafetyFlags.JEEP_BRAKE_HOLD.value

  def test_gm_bolt_gen2_pedal_safety_flags(self):
    CarInterface = interfaces[GM_CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL]

    pedal_fingerprint = {bus: {} for bus in range(8)}
    pedal_fingerprint[GMCanBus.POWERTRAIN][0x201] = 6
    pedal_params = CarInterface.get_params(
      GM_CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
      pedal_fingerprint,
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=get_test_starpilot_toggles(),
    )
    assert pedal_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_NO_ACC.value
    assert pedal_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_BOLT_2022_PEDAL.value

    acc_fingerprint = {bus: {} for bus in range(8)}
    acc_params = CarInterface.get_params(
      GM_CAR.CHEVROLET_BOLT_ACC_2022_2023,
      acc_fingerprint,
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=get_test_starpilot_toggles(),
    )
    assert not (acc_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_NO_ACC.value)

  def test_hyundai_aol_lkas_on_engage_flag_is_set_for_stock_long(self):
    toggles = SimpleNamespace(always_on_lateral_lkas=True)
    fingerprint = {bus: {} for bus in range(8)}
    fingerprint[0][0x391] = 8

    car_params = HyundaiCarInterface.get_params(
      HYUNDAI_CAR.HYUNDAI_SONATA_HYBRID,
      fingerprint,
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=toggles,
    )
    assert not car_params.openpilotLongitudinalControl

    fp_car_params = HyundaiCarInterface.get_starpilot_params(
      HYUNDAI_CAR.HYUNDAI_SONATA_HYBRID,
      fingerprint,
      [],
      car_params,
      toggles,
    )
    assert fp_car_params.safetyConfigs[-1].safetyParam & HyundaiStarPilotSafetyFlags.AOL_LKAS_ON_ENGAGE.value

  def test_toyota_disable_openpilot_long_sets_stock_long_safety_flag(self):
    CarInterface = interfaces[TOYOTA_CAR.TOYOTA_PRIUS_TSS2]
    fingerprint = {bus: {} for bus in range(8)}
    toggles = get_test_starpilot_toggles()

    car_params = CarInterface.get_params(
      TOYOTA_CAR.TOYOTA_PRIUS_TSS2,
      fingerprint,
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=toggles,
    )
    assert car_params.openpilotLongitudinalControl
    assert not car_params.alphaLongitudinalAvailable
    assert not (car_params.safetyConfigs[0].safetyParam & ToyotaSafetyFlags.STOCK_LONGITUDINAL.value)

    fp_car_params = CarInterface.get_starpilot_params(
      TOYOTA_CAR.TOYOTA_PRIUS_TSS2,
      fingerprint,
      [],
      car_params,
      toggles,
    )

    _apply_disable_openpilot_long(car_params, fp_car_params)

    assert not car_params.openpilotLongitudinalControl
    assert car_params.pcmCruise
    assert fp_car_params.openpilotLongitudinalControlDisabled
    assert car_params.safetyConfigs[0].safetyParam & ToyotaSafetyFlags.STOCK_LONGITUDINAL.value
    assert fp_car_params.safetyConfigs[0].safetyParam & ToyotaSafetyFlags.STOCK_LONGITUDINAL.value

  # FIXME: Due to the lists used in carParams, Phase.target is very slow and will cause
  #  many generated examples to overrun when max_examples > ~20, don't use it
  @pytest.mark.parametrize("car_name", sorted(PLATFORMS))
  @settings(max_examples=MAX_EXAMPLES, deadline=None,
            phases=(Phase.reuse, Phase.generate, Phase.shrink))
  @given(data=st.data())
  def test_car_interfaces(self, car_name, data):
    car_interface = get_fuzzy_car_interface(car_name, data.draw)
    car_params = car_interface.CP.as_reader()

    assert car_params.mass > 1
    assert car_params.wheelbase > 0
    # centerToFront is center of gravity to front wheels, assert a reasonable range
    assert car_params.wheelbase * 0.3 < car_params.centerToFront < car_params.wheelbase * 0.7
    assert car_params.maxLateralAccel > 0

    # Longitudinal sanity checks
    assert len(car_params.longitudinalTuning.kpV) == len(car_params.longitudinalTuning.kpBP)
    assert len(car_params.longitudinalTuning.kiV) == len(car_params.longitudinalTuning.kiBP)

    # Lateral sanity checks
    if car_params.steerControlType != structs.CarParams.SteerControlType.angle:
      tune = car_params.lateralTuning
      if tune.which() == 'pid':
        if car_name != MOCK.MOCK:
          assert not math.isnan(tune.pid.kf) and tune.pid.kf > 0
          assert len(tune.pid.kpV) > 0 and len(tune.pid.kpV) == len(tune.pid.kpBP)
          assert len(tune.pid.kiV) > 0 and len(tune.pid.kiV) == len(tune.pid.kiBP)

      elif tune.which() == 'torque':
        assert not math.isnan(tune.torque.latAccelFactor) and tune.torque.latAccelFactor > 0
        assert not math.isnan(tune.torque.friction) and tune.torque.friction > 0

    # Run car interface
    # TODO: use hypothesis to generate random messages
    now_nanos = 0
    CC = structs.CarControl().as_reader()
    for _ in range(10):
      car_interface.update([], car_interface.starpilot_toggles)
      car_interface.apply(CC, now_nanos, car_interface.starpilot_toggles)
      now_nanos += DT_CTRL * 1e9  # 10 ms

    CC = structs.CarControl()
    CC.enabled = True
    CC.latActive = True
    CC.longActive = True
    CC = CC.as_reader()
    for _ in range(10):
      car_interface.update([], car_interface.starpilot_toggles)
      car_interface.apply(CC, now_nanos, car_interface.starpilot_toggles)
      now_nanos += DT_CTRL * 1e9  # 10ms

    # Test radar interface
    radar_interface = car_interface.RadarInterface(car_params)
    assert radar_interface

    # Run radar interface once
    radar_interface.update([])
    if not car_params.radarUnavailable and radar_interface.rcp is not None and \
       hasattr(radar_interface, '_update') and hasattr(radar_interface, 'trigger_msg'):
      radar_interface._update([radar_interface.trigger_msg])

    # Test radar fault
    if not car_params.radarUnavailable and radar_interface.rcp is not None:
      cans = [(0, [CanData(0, b'', 0) for _ in range(5)])]
      rr = radar_interface.update(cans)
      assert rr is None or len(rr.errors) > 0

  def test_interface_attrs(self):
    """Asserts basic behavior of interface attribute getter"""
    num_brands = len(get_interface_attr('CAR'))
    assert num_brands >= 12

    # Should return value for all brands when not combining, even if attribute doesn't exist
    ret = get_interface_attr('FAKE_ATTR')
    assert len(ret) == num_brands

    # Make sure we can combine dicts
    ret = get_interface_attr('DBC', combine_brands=True)
    assert len(ret) >= 160

    # We don't support combining non-dicts
    ret = get_interface_attr('CAR', combine_brands=True)
    assert len(ret) == 0

    # If brand has None value, it shouldn't return when ignore_none=True is specified
    none_brands = {b for b, v in get_interface_attr('FINGERPRINTS').items() if v is None}
    assert len(none_brands) >= 1

    ret = get_interface_attr('FINGERPRINTS', ignore_none=True)
    none_brands_in_ret = none_brands.intersection(ret)
    assert len(none_brands_in_ret) == 0, f'Brands with None values in ignore_none=True result: {none_brands_in_ret}'
