import os
import time
from collections.abc import Callable

import openpilot.system.sentry as sentry

from cereal import car, custom
from openpilot.common.params import Params
from openpilot.selfdrive.car.interfaces import get_interface_attr
from openpilot.selfdrive.car.fingerprints import eliminate_incompatible_cars, all_legacy_fingerprint_cars
from openpilot.selfdrive.car.vin import get_vin, is_valid_vin, VIN_UNKNOWN
from openpilot.selfdrive.car.fw_versions import get_fw_versions_ordered, get_present_ecus, match_fw_to_car, set_obd_multiplexing
from openpilot.selfdrive.car.mock.values import CAR as MOCK
from openpilot.selfdrive.car.gm.values import CAR as GM_CAR, CanBus as GMCanBus
from openpilot.common.swaglog import cloudlog
import cereal.messaging as messaging
from openpilot.selfdrive.car import gen_empty_fingerprint
from openpilot.system.version import get_build_metadata

FRAME_FINGERPRINT = 100  # 1s
SOURCE_BRANCH_FILE = "/data/media/0/starpilot_source_branch"

EventName = car.CarEvent.EventName
FrogPilotEventName = custom.FrogPilotCarEvent.EventName


def get_startup_event(car_recognized, controller_available, fw_seen):
  event = FrogPilotEventName.customStartupAlert

  if not car_recognized:
    if fw_seen:
      event = EventName.startupNoCar
    else:
      event = EventName.startupNoFw
  elif car_recognized and not controller_available:
    event = EventName.startupNoControl
  return event


def get_one_can(logcan):
  while True:
    can = messaging.recv_one_retry(logcan)
    if len(can.can) > 0:
      return can


def load_interfaces(brand_names):
  ret = {}
  for brand_name in brand_names:
    path = f'openpilot.selfdrive.car.{brand_name}'
    CarInterface = __import__(path + '.interface', fromlist=['CarInterface']).CarInterface
    CarState = __import__(path + '.carstate', fromlist=['CarState']).CarState
    CarController = __import__(path + '.carcontroller', fromlist=['CarController']).CarController
    for model_name in brand_names[brand_name]:
      ret[model_name] = (CarInterface, CarController, CarState)
  return ret


def _get_interface_names() -> dict[str, list[str]]:
  # returns a dict of brand name and its respective models
  brand_names = {}
  for brand_name, brand_models in get_interface_attr("CAR").items():
    brand_names[brand_name] = [model.value for model in brand_models]

  return brand_names


# imports from directory selfdrive/car/<name>/
interface_names = _get_interface_names()
interfaces = load_interfaces(interface_names)


def can_fingerprint(next_can: Callable) -> tuple[str | None, dict[int, dict], dict[int, set[int]]]:
  finger = gen_empty_fingerprint()
  nonzero_addrs = {bus: set() for bus in finger}
  candidate_cars = {i: all_legacy_fingerprint_cars() for i in [0, 1]}  # attempt fingerprint on both bus 0 and 1
  frame = 0
  car_fingerprint = None
  done = False

  while not done:
    a = next_can()

    for can in a.can:
      # The fingerprint dict is generated for all buses, this way the car interface
      # can use it to detect a (valid) multipanda setup and initialize accordingly
      if can.src < 128:
        if can.src not in finger:
          finger[can.src] = {}
          nonzero_addrs[can.src] = set()
        finger[can.src][can.address] = len(can.dat)
        if any(can.dat):
          nonzero_addrs[can.src].add(can.address)

      for b in candidate_cars:
        # Ignore extended messages and VIN query response.
        if can.src == b and can.address < 0x800 and can.address not in (0x7df, 0x7e0, 0x7e8):
          candidate_cars[b] = eliminate_incompatible_cars(can, candidate_cars[b])

    # if we only have one car choice and the time since we got our first
    # message has elapsed, exit
    for b in candidate_cars:
      if len(candidate_cars[b]) == 1 and frame > FRAME_FINGERPRINT:
        # fingerprint done
        car_fingerprint = candidate_cars[b][0]

    # bail if no cars left or we've been waiting for more than 2s
    failed = (all(len(cc) == 0 for cc in candidate_cars.values()) and frame > FRAME_FINGERPRINT) or frame > 200
    succeeded = car_fingerprint is not None
    done = failed or succeeded

    frame += 1

  return car_fingerprint, finger, nonzero_addrs


# **** for use live only ****
def fingerprint(logcan, sendcan, num_pandas):
  fixed_fingerprint = os.environ.get('FINGERPRINT', "")
  skip_fw_query = os.environ.get('SKIP_FW_QUERY', False)
  disable_fw_cache = os.environ.get('DISABLE_FW_CACHE', False)
  ecu_rx_addrs = set()
  params = Params()

  start_time = time.monotonic()
  if not skip_fw_query:
    cached_params = params.get("CarParamsCache")
    if cached_params is not None:
      with car.CarParams.from_bytes(cached_params) as cached_params:
        if cached_params.carName == "mock":
          cached_params = None

    if cached_params is not None and len(cached_params.carFw) > 0 and \
       cached_params.carVin is not VIN_UNKNOWN and not disable_fw_cache:
      cloudlog.warning("Using cached CarParams")
      vin_rx_addr, vin_rx_bus, vin = -1, -1, cached_params.carVin
      car_fw = list(cached_params.carFw)
      cached = True
    else:
      cloudlog.warning("Getting VIN & FW versions")
      # enable OBD multiplexing for VIN query
      # NOTE: this takes ~0.1s and is relied on to allow sendcan subscriber to connect in time
      set_obd_multiplexing(params, True)
      # VIN query only reliably works through OBDII
      vin_rx_addr, vin_rx_bus, vin = get_vin(logcan, sendcan, (0, 1))
      ecu_rx_addrs = get_present_ecus(logcan, sendcan, num_pandas=num_pandas)
      car_fw = get_fw_versions_ordered(logcan, sendcan, vin, ecu_rx_addrs, num_pandas=num_pandas)
      cached = False

    exact_fw_match, fw_candidates = match_fw_to_car(car_fw, vin)
  else:
    vin_rx_addr, vin_rx_bus, vin = -1, -1, VIN_UNKNOWN
    exact_fw_match, fw_candidates, car_fw = True, set(), []
    cached = False

  if not is_valid_vin(vin):
    cloudlog.event("Malformed VIN", vin=vin, error=True)
    vin = VIN_UNKNOWN
  cloudlog.warning("VIN %s", vin)
  params.put("CarVin", vin)

  # disable OBD multiplexing for CAN fingerprinting and potential ECU knockouts
  set_obd_multiplexing(params, False)
  params.put_bool("FirmwareQueryDone", True)

  fw_query_time = time.monotonic() - start_time

  # CAN fingerprint
  # drain CAN socket so we get the latest messages
  messaging.drain_sock_raw(logcan)
  car_fingerprint, finger, nonzero_addrs = can_fingerprint(lambda: get_one_can(logcan))

  exact_match = True
  source = car.CarParams.FingerprintSource.can

  # If FW query returns exactly 1 candidate, use it
  if len(fw_candidates) == 1:
    car_fingerprint = list(fw_candidates)[0]
    source = car.CarParams.FingerprintSource.fw
    exact_match = exact_fw_match

  if fixed_fingerprint:
    car_fingerprint = fixed_fingerprint
    source = car.CarParams.FingerprintSource.fixed

  cloudlog.event("fingerprinted", car_fingerprint=car_fingerprint, source=source, fuzzy=not exact_match, cached=cached,
                 fw_count=len(car_fw), ecu_responses=list(ecu_rx_addrs), vin_rx_addr=vin_rx_addr, vin_rx_bus=vin_rx_bus,
                 fingerprints=repr(finger), fw_query_time=fw_query_time, error=True)

  return car_fingerprint, finger, nonzero_addrs, vin, car_fw, source, exact_match


def get_car_interface(CP, FPCP):
  CarInterface, CarController, CarState = interfaces[CP.carFingerprint]
  return CarInterface(CP, FPCP, CarController, CarState)

def get_cached_car_fingerprint(params: Params) -> str | None:
  for key in ("CarParamsPersistent", "CarParamsCache", "CarParams"):
    cp_bytes = params.get(key)
    if cp_bytes is None:
      continue
    try:
      with car.CarParams.from_bytes(cp_bytes) as cached_cp:
        if cached_cp.carFingerprint:
          return cached_cp.carFingerprint
    except Exception:
      continue
  return None

def clear_stale_car_params(params: Params, candidate: str) -> None:
  cached_fingerprint = get_cached_car_fingerprint(params)
  if cached_fingerprint is None or cached_fingerprint == candidate:
    return

  stale_keys = (
    "CarParams",
    "CarParamsCache",
    "CarParamsPersistent",
    "FrogPilotCarParams",
    "FrogPilotCarParamsPersistent",
    "CarModelName",
  )
  for key in stale_keys:
    params.remove(key)

  cloudlog.warning("cleared stale car params after fingerprint change: %s -> %s", cached_fingerprint, candidate)

def migrate_legacy_bolt_candidate(candidate: str) -> str:
  source_branch = ""
  try:
    with open(SOURCE_BRANCH_FILE, encoding="utf-8") as f:
      source_branch = f.read().strip()
  except OSError:
    pass

  migration_branch = source_branch or get_build_metadata().channel
  replacements = {}
  if migration_branch in {"TorqueTune", "TorquePedal"}:
    replacements = {
      "CHEVROLET_BOLT_EUV": GM_CAR.CHEVROLET_BOLT_ACC_2022_2023,
      "CHEVROLET_BOLT_CC": GM_CAR.CHEVROLET_BOLT_CC_2022_2023,
    }
  elif migration_branch in {"TotallyTune", "StarPilot-2017", "StarPilot 2017"}:
    replacements = {
      "CHEVROLET_BOLT_CC": GM_CAR.CHEVROLET_BOLT_CC_2017,
    }
  elif migration_branch in {"StarPilot"}:
    replacements = {
      "CHEVROLET_BOLT_CC": GM_CAR.CHEVROLET_BOLT_CC_2019_2021,
    }

  normalized_candidate = candidate[4:] if candidate.startswith("CAR.") else candidate
  return replacements.get(normalized_candidate, normalized_candidate)


def get_car(logcan, sendcan, experimental_long_allowed, params, num_pandas=1, frogpilot_toggles=None):
  candidate, fingerprints, nonzero_addrs, vin, car_fw, source, exact_match = fingerprint(logcan, sendcan, num_pandas)

  if candidate is None or frogpilot_toggles.force_fingerprint:
    if frogpilot_toggles.car_model is not None:
      candidate = frogpilot_toggles.car_model
    else:
      cloudlog.event("car doesn't match any fingerprints", fingerprints=repr(fingerprints), error=True)
      candidate = "MOCK"
  else:
    params.put_nonblocking("CarMake", candidate.split('_')[0].title())
    params.put_nonblocking("CarModel", candidate)

  # Branch migration can leave legacy Bolt candidate names active in params/cache.
  # Remap the selected candidate itself so fingerprint selection and params stay in sync.
  migrated_candidate = migrate_legacy_bolt_candidate(candidate)
  if candidate != migrated_candidate:
    cloudlog.warning("legacy Bolt candidate migration: %s -> %s", candidate, migrated_candidate)
    candidate = migrated_candidate
    params.put_nonblocking("CarMake", candidate.split('_')[0].title())
    params.put_nonblocking("CarModel", candidate)
    params.remove("CarModelName")

  # VIN-based Bolt year mapping (selfdrive-only, bolt variants only)
  if not frogpilot_toggles.force_fingerprint and is_valid_vin(vin):
    bolt_variants = {
      "CHEVROLET_BOLT_EUV",
      "CHEVROLET_BOLT_CC",
      "CAR.CHEVROLET_BOLT_EUV",
      "CAR.CHEVROLET_BOLT_CC",
      GM_CAR.CHEVROLET_BOLT_ACC_2022_2023,
      GM_CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
      GM_CAR.CHEVROLET_BOLT_CC_2022_2023,
      GM_CAR.CHEVROLET_BOLT_CC_2019_2021,
      GM_CAR.CHEVROLET_BOLT_CC_2017,
    }
    if candidate in bolt_variants:
      year_code = vin[9:10]
      year_map = {
        "H": GM_CAR.CHEVROLET_BOLT_CC_2017,       # 2017
        "J": GM_CAR.CHEVROLET_BOLT_CC_2019_2021,  # 2018
        "K": GM_CAR.CHEVROLET_BOLT_CC_2019_2021,  # 2019
        "L": GM_CAR.CHEVROLET_BOLT_CC_2019_2021,  # 2020
        "M": GM_CAR.CHEVROLET_BOLT_CC_2019_2021,  # 2021
        "N": GM_CAR.CHEVROLET_BOLT_ACC_2022_2023, # 2022
        "P": GM_CAR.CHEVROLET_BOLT_ACC_2022_2023, # 2023
      }
      if year_code in year_map:
        vin_candidate = year_map[year_code]
        if vin_candidate == GM_CAR.CHEVROLET_BOLT_ACC_2022_2023:
          has_acc_data = (
            0x370 in nonzero_addrs.get(GMCanBus.CAMERA, set()) or
            0x370 in nonzero_addrs.get(GMCanBus.POWERTRAIN, set())
          )
          has_pedal_msg = 0x201 in fingerprints.get(GMCanBus.POWERTRAIN, {})
          if has_acc_data:
            vin_candidate = GM_CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL if has_pedal_msg else GM_CAR.CHEVROLET_BOLT_ACC_2022_2023
          else:
            vin_candidate = GM_CAR.CHEVROLET_BOLT_CC_2022_2023
        if candidate != vin_candidate:
          prev_candidate = candidate
          candidate = vin_candidate
          params.put_nonblocking("CarMake", candidate.split('_')[0].title())
          params.put_nonblocking("CarModel", candidate)
          params.remove("CarModelName")
          cloudlog.warning("VIN Bolt override: %s -> %s", prev_candidate, candidate)

  # Always prefer live fingerprint naming for Bolt variants to avoid stale manual labels.
  if candidate in {
    GM_CAR.CHEVROLET_BOLT_ACC_2022_2023,
    GM_CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
    GM_CAR.CHEVROLET_BOLT_CC_2022_2023,
    GM_CAR.CHEVROLET_BOLT_CC_2019_2021,
    GM_CAR.CHEVROLET_BOLT_CC_2017,
    "CHEVROLET_BOLT_EUV",
    "CHEVROLET_BOLT_CC",
    "CAR.CHEVROLET_BOLT_EUV",
    "CAR.CHEVROLET_BOLT_CC",
  }:
    params.remove("CarModelName")

  if frogpilot_toggles.block_user:
    candidate = MOCK.MOCK
    sentry.capture_block()

  clear_stale_car_params(params, candidate)

  CarInterface, _, _ = interfaces[candidate]
  CP = CarInterface.get_params(candidate, fingerprints, car_fw, experimental_long_allowed, frogpilot_toggles, docs=False)
  FPCP = CarInterface.get_frogpilot_params(candidate, fingerprints, car_fw, CP, frogpilot_toggles)
  CP.carVin = vin
  CP.carFw = car_fw
  CP.fingerprintSource = source
  CP.fuzzyFingerprint = not exact_match

  return get_car_interface(CP, FPCP), CP, FPCP

def write_car_param(platform=MOCK.MOCK):
  params = Params()
  CarInterface, _, _ = interfaces[platform]
  CP = CarInterface.get_non_essential_params(platform)
  params.put("CarParams", CP.to_bytes())

def get_demo_car_params():
  platform = MOCK.MOCK
  CarInterface, _, _ = interfaces[platform]
  CP = CarInterface.get_non_essential_params(platform)
  return CP
