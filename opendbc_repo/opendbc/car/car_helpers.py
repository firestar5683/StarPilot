import os
import time

from types import SimpleNamespace

from cereal import custom
from opendbc.car import gen_empty_fingerprint
from opendbc.car.can_definitions import CanRecvCallable, CanSendCallable
from opendbc.car.carlog import carlog
from opendbc.car.structs import CarParams, CarParamsT
from opendbc.car.fingerprints import eliminate_incompatible_cars, all_legacy_fingerprint_cars
from opendbc.car.fw_versions import ObdCallback, get_fw_versions_ordered, get_present_ecus, match_fw_to_car
from opendbc.car.mock.values import CAR as MOCK
from opendbc.car.toyota.values import ToyotaSafetyFlags
from opendbc.car.values import BRANDS
from opendbc.car.vin import get_vin, is_valid_vin, VIN_UNKNOWN
from openpilot.common.params import Params

FRAME_FINGERPRINT = 100  # 1s

StarPilotCarParams = custom.StarPilotCarParams


def load_interfaces(brand_names):
  ret = {}
  for brand_name in brand_names:
    path = f'opendbc.car.{brand_name}'
    CarInterface = __import__(path + '.interface', fromlist=['CarInterface']).CarInterface
    for model_name in brand_names[brand_name]:
      ret[model_name] = CarInterface
  return ret


def _get_interface_names() -> dict[str, list[str]]:
  # returns a dict of brand name and its respective models
  brand_names = {}
  for brand in BRANDS:
    brand_name = brand.__module__.split('.')[-2]
    brand_names[brand_name] = [model.value for model in brand]

  return brand_names


# imports from directory opendbc/car/<name>/
interface_names = _get_interface_names()
interfaces = load_interfaces(interface_names)

# Legacy Bolt rename migration. Keep here to prevent force-fingerprint
# params from selecting a removed platform name and crashing detection.
LEGACY_FORCED_CANDIDATE_MAP = {
  "CHEVROLET_BOLT_CC_2019_2021": "CHEVROLET_BOLT_CC_2018_2021",
}

GM_CANDIDATE_PREFIXES = ("CHEVROLET_", "GMC_", "CADILLAC_", "BUICK_", "HOLDEN_")
GM_CORE_FINGERPRINT_MSGS = frozenset((190, 201, 209, 211, 241))
GM_CAMERA_BUS = 2
GM_VOLT_CAMERA_MSG = 0x320


def _normalize_forced_candidate(candidate: str | None) -> str | None:
  if candidate is None:
    return None
  if isinstance(candidate, (bytes, bytearray)):
    candidate = candidate.decode("utf-8", errors="ignore")
  candidate = str(candidate)
  return LEGACY_FORCED_CANDIDATE_MAP.get(candidate, candidate)


def _normalize_gm_bolt_candidate(candidate: str | None, fingerprints: dict[int, dict], vin: str | None = None) -> str | None:
  """
  Normalize ambiguous/mismatched Bolt candidates using robust PT message signatures.
  This guards against occasional wrong variant selection causing persistent canError.
  """
  pt = fingerprints.get(0, {})
  if not pt:
    return candidate

  msg_211_len = pt.get(211)  # 2 on Gen1 Bolt, 3 on 2022+ Bolt
  msg_304_len = pt.get(304)  # 8 on 2017 Gen1, 1 on 2018-2021 Gen1
  has_pedal = 513 in pt
 
  # The 2022-23 Bolt ACC, pedal, and CC variants share the same FPv1
  # fingerprint. Recover an ambiguous match when the observed traffic
  # matches the Bolt family and the VIN confirms model year 2022/2023.
  bolt_2022_2023_signature = (
    pt.get(190) == 7 and
    msg_211_len == 3 and
    pt.get(566) == 8 and
    pt.get(458) == 5
  )
  vin_year = vin[9] if isinstance(vin, str) and len(vin) > 9 else None

  # VIN model-year codes: N=2022, P=2023.
  if candidate is None and bolt_2022_2023_signature and vin_year in ("N", "P"):
    return "CHEVROLET_BOLT_ACC_2022_2023_PEDAL" if has_pedal else "CHEVROLET_BOLT_ACC_2022_2023"
  # If detection failed entirely but the signature is clearly Bolt, recover to a sane default.
  
  if candidate is None and 170 in pt and 188 in pt and msg_211_len in (2, 3):
    if msg_211_len == 3:
      return "CHEVROLET_BOLT_ACC_2022_2023_PEDAL" if has_pedal else "CHEVROLET_BOLT_ACC_2022_2023"
    if msg_304_len == 8:
      return "CHEVROLET_BOLT_CC_2017"
    return "CHEVROLET_BOLT_CC_2018_2021"

  if not isinstance(candidate, str) or not candidate.startswith("CHEVROLET_BOLT_"):
    return candidate

  # Gen split based on stable message lengths.
  if msg_211_len == 2:
    # Gen1 Bolt. Keep 2017 distinct by 0x130 length when available.
    if msg_304_len == 8:
      return "CHEVROLET_BOLT_CC_2017"
    return "CHEVROLET_BOLT_CC_2018_2021"

  if msg_211_len == 3:
    # 2022+ Bolt family. Preserve pedal path when seen on bus.
    if has_pedal:
      return "CHEVROLET_BOLT_ACC_2022_2023_PEDAL"
    # Preserve CC-specific 2022 path if already selected; otherwise default ACC variant.
    if candidate == "CHEVROLET_BOLT_CC_2022_2023":
      return candidate
    return "CHEVROLET_BOLT_ACC_2022_2023"

  return candidate


def _apply_disable_openpilot_long(CP: CarParams, FPCP: StarPilotCarParams) -> None:
  CP.openpilotLongitudinalControl = False
  CP.pcmCruise = True
  FPCP.openpilotLongitudinalControlDisabled = True

  if CP.brand == "toyota":
    # Toyota stock longitudinal safety changes the forwarding rules so the
    # camera's ACC_CONTROL message can reach the PT bus again.
    for cfg in CP.safetyConfigs:
      cfg.safetyParam |= ToyotaSafetyFlags.STOCK_LONGITUDINAL.value
    for cfg in FPCP.safetyConfigs:
      cfg.safetyParam |= ToyotaSafetyFlags.STOCK_LONGITUDINAL.value


def _normalize_gm_volt_candidate(candidate: str | None, fingerprints: dict[int, dict]) -> str | None:
  cam = fingerprints.get(GM_CAMERA_BUS, {})
  has_live_camera_msg = GM_VOLT_CAMERA_MSG in cam

  if candidate == "CHEVROLET_VOLT_CAMERA" and not has_live_camera_msg:
    return "CHEVROLET_VOLT"

  if candidate == "CHEVROLET_VOLT" and has_live_camera_msg:
    return "CHEVROLET_VOLT_CAMERA"

  return candidate


def _is_gm_candidate(candidate: str | None) -> bool:
  return isinstance(candidate, str) and candidate.startswith(GM_CANDIDATE_PREFIXES)


def _get_gm_stored_candidate_fallback(fingerprints: dict[int, dict], stored_candidate: str | None,
                                      cached_candidate: str | None) -> str | None:
  pt = fingerprints.get(0, {})
  # Several GM variants intentionally share FPv1 signatures. If live matching
  # can't resolve them, reuse the last known GM platform instead of dropping to MOCK.
  if len(GM_CORE_FINGERPRINT_MSGS.intersection(pt.keys())) < 4:
    return None

  for candidate in (_normalize_forced_candidate(stored_candidate), _normalize_forced_candidate(cached_candidate)):
    candidate = _normalize_gm_volt_candidate(candidate, fingerprints)
    if _is_gm_candidate(candidate) and candidate != MOCK.MOCK and candidate in interfaces:
      return candidate

  return None


def _apply_starpilot_access_policy(candidate: str, starpilot_toggles: SimpleNamespace | None) -> str:
  # Branch-based dashcam gating was removed. Keep the resolved candidate even if
  # an older serialized toggle payload still contains block_user=True.
  return candidate


def can_fingerprint(can_recv: CanRecvCallable) -> tuple[str | None, dict[int, dict]]:
  finger = gen_empty_fingerprint()
  candidate_cars = {i: all_legacy_fingerprint_cars() for i in [0, 1]}  # attempt fingerprint on both bus 0 and 1
  frame = 0
  car_fingerprint = None
  done = False

  while not done:
    # can_recv(wait_for_one=True) may return zero or multiple packets, so we increment frame for each one we receive
    can_packets = can_recv(wait_for_one=True)
    for can_packet in can_packets:
      for can in can_packet:
        # The fingerprint dict is generated for all buses, this way the car interface
        # can use it to detect a (valid) multipanda setup and initialize accordingly
        if can.src < 128:
          if can.src not in finger:
            finger[can.src] = {}
          finger[can.src][can.address] = len(can.dat)

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

  return car_fingerprint, finger


# **** for use live only ****
def fingerprint(can_recv: CanRecvCallable, can_send: CanSendCallable, set_obd_multiplexing: ObdCallback, num_pandas: int,
                cached_params: CarParamsT | None) -> tuple[str | None, dict, str, list[CarParams.CarFw], CarParams.FingerprintSource, bool]:
  fixed_fingerprint = os.environ.get('FINGERPRINT', "")
  skip_fw_query = os.environ.get('SKIP_FW_QUERY', False)
  disable_fw_cache = os.environ.get('DISABLE_FW_CACHE', False)
  ecu_rx_addrs = set()

  if not fixed_fingerprint and Params().get_bool("NAPForcePreAP"):
    fixed_fingerprint = "TESLA_MODEL_S_PREAP"
    skip_fw_query = True
    carlog.warning("NAPForcePreAP enabled; forcing TESLA_MODEL_S_PREAP fingerprint")

  start_time = time.monotonic()
  if not skip_fw_query:
    if cached_params is not None and cached_params.brand != "mock" and len(cached_params.carFw) > 0 and \
       cached_params.carVin is not VIN_UNKNOWN and not disable_fw_cache:
      carlog.warning("Using cached CarParams")
      vin_rx_addr, vin_rx_bus, vin = -1, -1, cached_params.carVin
      car_fw = list(cached_params.carFw)
      cached = True
    else:
      carlog.warning("Getting VIN & FW versions")
      # enable OBD multiplexing for VIN query
      # NOTE: this takes ~0.1s and is relied on to allow sendcan subscriber to connect in time
      set_obd_multiplexing(True)
      # VIN query only reliably works through OBDII
      vin_rx_addr, vin_rx_bus, vin = get_vin(can_recv, can_send, (0, 1))
      ecu_rx_addrs = get_present_ecus(can_recv, can_send, set_obd_multiplexing, num_pandas=num_pandas)
      car_fw = get_fw_versions_ordered(can_recv, can_send, set_obd_multiplexing, vin, ecu_rx_addrs, num_pandas=num_pandas)
      cached = False

    exact_fw_match, fw_candidates = match_fw_to_car(car_fw, vin)
  else:
    vin_rx_addr, vin_rx_bus, vin = -1, -1, VIN_UNKNOWN
    exact_fw_match, fw_candidates, car_fw = True, set(), []
    cached = False

  if not is_valid_vin(vin):
    carlog.error({"event": "Malformed VIN", "vin": vin})
    vin = VIN_UNKNOWN
  carlog.warning("VIN %s", vin)

  # disable OBD multiplexing for CAN fingerprinting and potential ECU knockouts
  set_obd_multiplexing(False)

  fw_query_time = time.monotonic() - start_time

  # CAN fingerprint
  # drain CAN socket so we get the latest messages
  can_recv()
  car_fingerprint, finger = can_fingerprint(can_recv)

  exact_match = True
  source = CarParams.FingerprintSource.can

  # If FW query returns exactly 1 candidate, use it
  if len(fw_candidates) == 1:
    car_fingerprint = list(fw_candidates)[0]
    source = CarParams.FingerprintSource.fw
    exact_match = exact_fw_match

  if fixed_fingerprint:
    car_fingerprint = fixed_fingerprint
    source = CarParams.FingerprintSource.fixed

  carlog.error({"event": "fingerprinted", "car_fingerprint": str(car_fingerprint), "source": source, "fuzzy": not exact_match,
                "cached": cached, "fw_count": len(car_fw), "ecu_responses": list(ecu_rx_addrs), "vin_rx_addr": vin_rx_addr,
                "vin_rx_bus": vin_rx_bus, "fingerprints": repr(finger), "fw_query_time": fw_query_time})

  return car_fingerprint, finger, vin, car_fw, source, exact_match


def get_car(can_recv: CanRecvCallable, can_send: CanSendCallable, set_obd_multiplexing: ObdCallback, alpha_long_allowed: bool,
            is_release: bool, params: Params, num_pandas: int = 1, cached_params: CarParamsT | None = None, starpilot_toggles: SimpleNamespace = None):
  candidate, fingerprints, vin, car_fw, source, exact_match = fingerprint(can_recv, can_send, set_obd_multiplexing, num_pandas, cached_params)
  candidate = _normalize_gm_bolt_candidate(candidate, fingerprints, vin)
  candidate = _normalize_gm_volt_candidate(candidate, fingerprints)
  candidate = _normalize_forced_candidate(candidate)
  fingerprinted_candidate = candidate
  stored_candidate = _normalize_forced_candidate(params.get("CarModel"))
  cached_candidate = _normalize_forced_candidate(getattr(cached_params, "carFingerprint", None))

  if candidate is None:
    gm_fallback_candidate = _get_gm_stored_candidate_fallback(fingerprints, stored_candidate, cached_candidate)
    if gm_fallback_candidate is not None:
      carlog.error({
        "event": "using stored GM candidate after ambiguous live fingerprint",
        "candidate": gm_fallback_candidate,
        "stored_candidate": stored_candidate,
        "cached_candidate": cached_candidate,
      })
      candidate = gm_fallback_candidate

  if candidate is None or starpilot_toggles.force_fingerprint:
    if starpilot_toggles.force_fingerprint:
      forced_candidate = _normalize_forced_candidate(starpilot_toggles.car_model)
      candidate = forced_candidate
      if candidate not in interfaces and fingerprinted_candidate in interfaces:
        carlog.error({
          "event": "forced fingerprint unavailable; using live candidate",
          "forced_candidate": candidate,
          "live_candidate": fingerprinted_candidate,
        })
        candidate = fingerprinted_candidate
    else:
      carlog.error({"event": "car doesn't match any fingerprints", "fingerprints": repr(fingerprints)})
      candidate = "MOCK"
  else:
    params.put_nonblocking("CarMake", candidate.split('_')[0].title())
    params.put_nonblocking("CarModel", str(candidate))

  candidate = _apply_starpilot_access_policy(candidate, starpilot_toggles)

  # Legacy branch migration guard: normalize stale platform names from any source
  # (forced params, cached CarParams, fixed fingerprint env) before interface lookup.
  candidate = _normalize_forced_candidate(candidate)
  if candidate not in interfaces and fingerprinted_candidate in interfaces:
    carlog.error({
      "event": "normalized candidate unavailable; using live candidate",
      "candidate": candidate,
      "live_candidate": fingerprinted_candidate,
    })
    candidate = fingerprinted_candidate

  CarInterface = interfaces[candidate]
  CP: CarParams = CarInterface.get_params(candidate, fingerprints, car_fw, alpha_long_allowed, is_release, docs=False, starpilot_toggles=starpilot_toggles)
  CP.carVin = vin
  CP.carFw = car_fw
  CP.fingerprintSource = source
  CP.fuzzyFingerprint = not exact_match
  post_fingerprint_params = getattr(CarInterface, "apply_post_fingerprint_params", None)
  if post_fingerprint_params is not None:
    post_fingerprint_params(CP, candidate, fingerprints, car_fw)

  FPCP: StarPilotCarParams = CarInterface.get_starpilot_params(candidate, fingerprints, car_fw, CP, starpilot_toggles)

  if not CP.alphaLongitudinalAvailable and starpilot_toggles.disable_openpilot_long:
    _apply_disable_openpilot_long(CP, FPCP)

  return interfaces[CP.carFingerprint](CP, FPCP)


def get_demo_car_params():
  platform = MOCK.MOCK
  CarInterface = interfaces[platform]
  CP = CarInterface.get_non_essential_params(platform)
  return CP
