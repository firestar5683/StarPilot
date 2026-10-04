import pytest

from opendbc.can import CANPacker
from opendbc.car import structs
from opendbc.car.ford.interface import CarInterface
from opendbc.car.ford.tests.test_three_ports import params
from opendbc.car.ford.values import CAR, FordFlags


BASE_PT = (
  ("BrakeSysFeatures", 50),
  ("Yaw_Data_FD1", 100),
  ("DesiredTorqBrk", 50),
  ("EngVehicleSpThrottle", 100),
  ("EngBrakeData", 10),
  ("EPAS_INFO", 50),
  ("Cluster_Info1_FD1", 10),
  ("Steering_Data_FD1", 10),
  ("BodyInfo_3_FD1", 2),
  ("RCMStatusMessage2_FD1", 10),
)
BASE_CAMERA = (("ACCDATA", 50), ("ACCDATA_2", 50), ("ACCDATA_3", 5), ("IPMA_Data", 1))
SOURCE_CASES = (
  (CAR.FORD_EDGE_MK2, "TransGearData", "GearLvrPos_D_Actl", "SteeringPinion_Data_Alt"),
  (CAR.FORD_MONDEO_MK5, "Gear_Shift_by_Wire_FD1", "TrnRng_D_RqGsm", "SteeringPinion_Data"),
  (CAR.FORD_TRANSIT_MK5, "PowertrainData_10", "TrnRng_D_Rq", "SteeringPinion_Data"),
)


def inventory(candidate):
  cp = params(candidate)
  gear, gear_signal, steering = next(row[1:] for row in SOURCE_CASES if row[0] == candidate)
  pt = list(BASE_PT) + [(gear, 10), (steering, 100)]
  camera = list(BASE_CAMERA)
  if candidate == CAR.FORD_EDGE_MK2:
    pt.extend((("ParkAid_Data", 50), ("INSTRUMENT_PANEL", 1)))
  elif candidate == CAR.FORD_MONDEO_MK5:
    pt.append(("Lane_Assist_Data3_FD1", 30))
  else:
    pt.extend((("INSTRUMENT_PANEL", 1), ("Lane_Assist_Data3_FD1", 30)))
    camera.append(("LateralMotionControl", 20))
  return cp, gear, gear_signal, steering, [(name, 0, rate) for name, rate in pt] + [(name, 2, rate) for name, rate in camera]


def stream(packer, entries, tick, gear, gear_signal, *, omitted=None, wrong_bus=None):
  fields = {
    "BrakeSysFeatures": {"Veh_V_ActlBrk": 72, "VehVActlBrk_D_Qf": 3},
    "Yaw_Data_FD1": {"VehYawWActl_D_Qf": 3},
    "EngBrakeData": {"BpedDrvAppl_D_Actl": 1, "CcStat_D_Actl": 3},
    "SteeringPinion_Data": {"StePinCompAnEst_D_Qf": 3},
    "SteeringPinion_Data_Alt": {"StePinRelInit_An_Sns": 5},
    "ParkAid_Data": {"ExtSteeringAngleReq2": 5},
    "Lane_Assist_Data3_FD1": {"LatCtlSte_D_Stat": 1, "LaActAvail_D_Actl": 3},
    gear: {gear_signal: 3},
  }
  frames = []
  for name, bus, rate in entries:
    if name == omitted or (tick > 0 and (tick * rate) // 100 == ((tick - 1) * rate) // 100):
      continue
    values = fields.get(name, {})
    assert set(values) <= set(packer.dbc.name_to_msg[name].sigs)
    frames.append(packer.make_can_msg(name, 1 if name == wrong_bus else bus, values))
  return frames


@pytest.mark.parametrize('candidate,gear,gear_signal,steering', SOURCE_CASES)
@pytest.mark.parametrize('lost_kind', ('speed', 'brake', 'gear', 'steering', 'wrong-bus-speed'))
def test_actual_whole_parser_critical_source_loss_and_recovery(candidate, gear, gear_signal, steering, lost_kind):
  cp, selected_gear, selected_signal, selected_steering, entries = inventory(candidate)
  assert (selected_gear, selected_signal, selected_steering) == (gear, gear_signal, steering)
  assert cp.transmissionType == structs.CarParams.TransmissionType.automatic
  assert cp.flags & FordFlags.NEW_PORT
  ci = CarInterface(cp)
  ci.update([])
  packer = CANPacker('ford_lincoln_base_pt')
  for tick in range(200):
    out = ci.update([(1_000_000_000 + tick * 10_000_000, stream(packer, entries, tick, gear, gear_signal))])
  assert out.canValid
  assert out.gearShifter == structs.CarState.GearShifter.drive
  assert not out.vehicleSensorsInvalid
  lost = {'speed': 'BrakeSysFeatures', 'brake': 'EngBrakeData', 'gear': gear, 'steering': steering, 'wrong-bus-speed': 'BrakeSysFeatures'}[lost_kind]
  for tick in range(200, 500):
    frames = stream(
      packer,
      entries,
      tick,
      gear,
      gear_signal,
      omitted=None if lost_kind == 'wrong-bus-speed' else lost,
      wrong_bus=lost if lost_kind == 'wrong-bus-speed' else None,
    )
    out = ci.update([(1_000_000_000 + tick * 10_000_000, frames)])
  assert not out.canValid
  for tick in range(500, 700):
    out = ci.update([(1_000_000_000 + tick * 10_000_000, stream(packer, entries, tick, gear, gear_signal))])
  assert out.canValid
