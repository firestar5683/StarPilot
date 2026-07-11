#!/usr/bin/env python3
"""Passively capture EV9 DTCs requested by the existing car controller."""

import argparse
import datetime
import json
import pathlib
import sys
import time

# Running a script by file path puts only its own directory on sys.path. Add
# the openpilot repository root before importing cereal/openpilot modules.
OPENPILOT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(OPENPILOT_ROOT) not in sys.path:
  sys.path.insert(0, str(OPENPILOT_ROOT))

import cereal.messaging as messaging
from cereal import car

from openpilot.common.params import Params
from opendbc.car.uds import get_dtc_num_as_str, get_dtc_status_names


CAPTURE_PARAM = "KiaEv9DtcCaptureEnabled"
EV9_FINGERPRINT = "KIA_EV9"
EV9_DTC_TARGETS = {
  0x730: "adas",
  0x7C4: "forwardCamera",
  0x7C6: "combinationMeter",
  0x7D0: "forwardRadar",
  0x7D4: "eps",
}
READ_ALL_DTCS = b"\x19\x02\xFF"
READ_ALL_DTCS_RESPONSE = b"\x59\x02"


def collect_isotp_responses(logcan, timeout):
  """Collect response payloads without ever creating a sendcan publisher."""
  response_to_request = {addr + 8: addr for addr in EV9_DTC_TARGETS if addr != 0x730}
  states = {}
  responses = {}
  deadline = time.monotonic() + timeout

  while time.monotonic() < deadline and len(responses) < len(response_to_request):
    for event in messaging.drain_sock(logcan, wait_for_one=True):
      for msg in event.can:
        if msg.src != 1 or msg.address not in response_to_request or not msg.dat:
          continue
        dat = bytes(msg.dat)
        frame_type = dat[0] >> 4
        if frame_type == 0:
          responses[response_to_request[msg.address]] = dat[1:1 + (dat[0] & 0xF)]
        elif frame_type == 1:
          length = ((dat[0] & 0xF) << 8) | dat[1]
          states[msg.address] = [length, bytearray(dat[2:])]
        elif frame_type == 2 and msg.address in states:
          length, payload = states[msg.address]
          payload.extend(dat[1:])
          if len(payload) >= length:
            responses[response_to_request[msg.address]] = bytes(payload[:length])
            del states[msg.address]
  return responses


def load_ev9_car_params(params):
  for key in ("CarParams", "CarParamsPersistent", "CarParamsPrevRoute"):
    raw = params.get(key)
    if raw is None:
      continue
    with car.CarParams.from_bytes(raw) as cp:
      if str(cp.carFingerprint) != EV9_FINGERPRINT:
        continue
      return {
        "fingerprint": str(cp.carFingerprint),
        "firmwareBuses": {
          f"0x{addr:X}": sorted({int(fw.bus) for fw in cp.carFw if int(fw.address) == addr})
          for addr in EV9_DTC_TARGETS
        },
      }
  raise RuntimeError("KIA_EV9 CarParams are not available")


def require_parked_vehicle():
  sm = messaging.SubMaster(["carState", "pandaStates"])
  deadline = time.monotonic() + 10.0
  while time.monotonic() < deadline:
    sm.update(250)
    if sm.recv_frame["carState"] < 1 or not len(sm["pandaStates"]):
      continue
    cs = sm["carState"]
    if not cs.standstill or abs(cs.vEgo) > 0.05 or str(cs.gearShifter) != "park":
      raise RuntimeError(f"vehicle must be stationary in Park (standstill={cs.standstill}, vEgo={cs.vEgo}, gear={cs.gearShifter})")
    return {
      "standstill": bool(cs.standstill),
      "vEgo": float(cs.vEgo),
      "gear": str(cs.gearShifter),
      "safetyModel": str(sm["pandaStates"][0].safetyModel),
      "safetyParam": int(sm["pandaStates"][0].safetyParam),
    }
  raise RuntimeError("timed out waiting for live parked carState")


def parse_dtc_payload(payload):
  if not payload:
    return {"statusAvailabilityMask": None, "dtcs": [], "trailingBytes": ""}

  dtcs = []
  records = payload[1:]
  complete_len = len(records) - (len(records) % 4)
  for offset in range(0, complete_len, 4):
    record = records[offset:offset + 4]
    dtcs.append({
      "code": get_dtc_num_as_str(record[:3]),
      "raw": record[:3].hex().upper(),
      "status": int(record[3]),
      "statusNames": get_dtc_status_names(record[3]),
    })

  return {
    "statusAvailabilityMask": int(payload[0]),
    "dtcs": dtcs,
    "trailingBytes": records[complete_len:].hex(),
  }


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--label", default="suppressed", choices=("suppressed",))
  parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("/data/ev9_dtc_capture.jsonl"))
  parser.add_argument("--timeout", type=float, default=10.0)
  args = parser.parse_args()

  params = Params()
  result = {
    "capturedAt": datetime.datetime.now(datetime.UTC).isoformat(),
    "label": args.label,
    "request": READ_ALL_DTCS.hex(),
    "responsePrefix": READ_ALL_DTCS_RESPONSE.hex(),
    "bus": 1,
    "targets": {},
  }

  try:
    result["carParams"] = load_ev9_car_params(params)
    result["vehicleState"] = require_parked_vehicle()
    result["testConfig"] = {
      "enabled": params.get_bool("KiaEv9LongitudinalTestEnabled"),
      "stage": params.get_int("KiaEv9LongitudinalTestStage"),
      "probeMode": params.get_int("KiaEv9LongitudinalProbeMode"),
      "alphaLongitudinal": params.get_bool("AlphaLongitudinalEnabled"),
    }

    missing_bus = [addr for addr in EV9_DTC_TARGETS
                   if 1 not in result["carParams"]["firmwareBuses"][f"0x{addr:X}"]]
    if missing_bus:
      missing = ", ".join(hex(addr) for addr in missing_bus)
      raise RuntimeError(f"known ECU(s) were not firmware-queried on bus 1: {missing}")

    logcan = messaging.sub_sock("can", conflate=False, timeout=100)
    time.sleep(0.25)
    result["targets"][EV9_DTC_TARGETS[0x730]] = {
      "requestAddress": "0x730", "responseAddress": "0x738", "responded": False, "skipped": True,
      "skipReason": "preserve active ADAS CommunicationControl session", "dtcs": [],
    }

    # This changes only a Params flag. CarController remains the sole sendcan
    # publisher and clears the flag when its parked one-shot sequence ends.
    params.put_bool(CAPTURE_PARAM, True)
    responses = collect_isotp_responses(logcan, args.timeout)
    for addr, name in EV9_DTC_TARGETS.items():
      if addr == 0x730:
        continue
      raw_payload = responses.get(addr)
      positive = raw_payload is not None and raw_payload.startswith(READ_ALL_DTCS_RESPONSE)
      payload = raw_payload[len(READ_ALL_DTCS_RESPONSE):] if positive else None
      result["targets"][name] = {
        "requestAddress": f"0x{addr:X}",
        "responseAddress": f"0x{addr + 8:X}",
        "responded": raw_payload is not None,
        "positiveResponse": positive,
        "rawResponse": raw_payload.hex() if raw_payload is not None else "",
        **(parse_dtc_payload(payload) if positive else {"dtcs": []}),
      }
  except Exception as exc:
    result["error"] = f"{type(exc).__name__}: {exc}"
    raise
  finally:
    params.put_bool(CAPTURE_PARAM, False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as f:
      f.write(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
  main()
