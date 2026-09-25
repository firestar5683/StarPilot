"""Synthetic Tesla fixture using real vehicle code and an isolated C safety build.

Axis inputs are controller inputs, not product modes or physical qualification.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.tesla.fingerprints import FW_VERSIONS
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.values import CAR
from opendbc.safety.tests.libsafety import libsafety_py

ROOT = Path(__file__).resolve().parents[3]
DBC = "tesla_model3_party"
MODERN_PLATFORMS = (CAR.TESLA_MODEL_3, CAR.TESLA_MODEL_Y)
EPS = (structs.CarParams.Ecu.eps, 0x730, None)


def sha256(path):
  return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def car_params(platform, profile="marker489", longitudinal=True, settings_present=True, firmware=None):
  if firmware is None:
    if profile == "unknown":
      firmware = b"synthetic-unknown-EPS-response"
    else:
      firmware = FW_VERSIONS[platform][EPS][0]
  fw = structs.CarParams.CarFw(ecu=EPS[0], address=EPS[1], brand="tesla", fwVersion=firmware)
  fingerprint = gen_empty_fingerprint()
  if profile != "two_bit":
    bus, address = (0, 0x054) if profile == "marker054" else (2, 0x489)
    fingerprint[bus][address] = 8
  if settings_present:
    fingerprint[2][0x293] = 8
  return CarInterface.get_params(platform, fingerprint, [fw], longitudinal, False, False)


class NativeSafety:
  """Own one library handle; never replace the shared libsafety_py.libsafety."""
  def __init__(self):
    self.directory = tempfile.TemporaryDirectory(prefix="tesla-contract-safety-")
    directory = Path(self.directory.name)
    source = ROOT / "opendbc_repo/opendbc/safety/tests/libsafety/safety.c"
    compiler = shutil.which("cc")
    if compiler is None:
      self.directory.cleanup()
      raise RuntimeError("A C compiler is required for the Tesla safety contract")
    obj, library = directory / "safety.o", directory / "safety.so"
    commands = [
      [compiler, "-fPIC", "-Wall", "-Wextra", "-Werror", "-nostdlib", "-fno-builtin", "-std=gnu11",
       "-Wfatal-errors", "-Wno-pointer-to-int-cast", "-g", "-O0", "-fno-omit-frame-pointer", "-DALLOW_DEBUG",
       "-I", str(ROOT / "opendbc_repo"), "-c", str(source), "-o", str(obj)],
      [compiler, "-shared", str(obj), "-o", str(library), "-fsanitize=undefined", "-fno-sanitize-recover=undefined"],
    ]
    try:
      for command in commands:
        subprocess.run(command, check=True, capture_output=True, text=True)
      self.provenance = {
        "commands": commands,
        "compiler": compiler,
        "compiler_sha256": sha256(Path(compiler).resolve()),
        "compiler_version": subprocess.check_output([compiler, "--version"], text=True).strip(),
        "library_sha256": sha256(library),
        "object_sha256": sha256(obj),
        "variant": "host C safety with ALLOW_DEBUG; no coverage instrumentation or device firmware",
        "sanitizer_scope": "upstream linker flags only; compile is not UBSan-instrumented",
      }
      self.lib = libsafety_py.ffi.dlopen(str(library))
    except BaseException:
      self.directory.cleanup()
      raise

  def close(self):
    libsafety_py.ffi.dlclose(self.lib)
    self.directory.cleanup()

  def reset(self, cp):
    config = cp.safetyConfigs[0]
    if self.lib.set_safety_hooks(config.safetyModel.raw, config.safetyParam) != 0:
      raise RuntimeError("Tesla safety hook rejected fixture configuration")
    self.lib.init_tests()

  def rx(self, message):
    address, data, bus = message
    return bool(self.lib.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data)))

  def tx(self, message):
    address, data, bus = message
    return bool(self.lib.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data)))


class TeslaFixture:
  # Synthetic 100Hz host schedule; required safety inputs use their declared rates.
  INPUTS = (
    (0, "DI_speed", 2, {"DI_vehicleSpeed": 36.0}),
    (0, "DI_systemStatus", 1, {"DI_gear": 4, "DI_accelPedalPos": 0}),
    (0, "ESP_status", 2, {"ESP_driverBrakeApply": 1}),
    (0, "EPAS3S_sysStatus", 1, {"EPAS3S_internalSAS": 0, "EPAS3S_eacStatus": 1,
                                "EPAS3S_torsionBarTorque": 0, "EPAS3S_handsOnLevel": 0}),
    (0, "DI_state", 10, {"DI_cruiseState": 2, "DI_autoparkState": 0, "DI_speedUnits": 1, "DI_digitalSpeed": 36}),
    (0, "ESP_B", 2, {"ESP_vehicleSpeed": 36, "ESP_vehicleStandstillSts": 0, "ESP_wheelSpeedsQF": 1}),
    (0, "UI_warning", 10, {"buckleStatus": 1, "anyDoorOpen": 0}),
    (2, "SCCM_steeringAngleSensor", 1, {"SCCM_steeringAngleSpeed": 0}),
    (2, "DAS_status", 10, {}),
    (2, "DAS_settings", 10, {"DAS_autosteerEnabled": 0}),
    (2, "DAS_control", 4, {"DAS_accState": 4, "DAS_aebEvent": 0, "DAS_accelMin": 0, "DAS_accelMax": 0}),
    (2, "DAS_steeringControl", 2, {"DAS_steeringControlType": 0, "DAS_steeringAngleRequest": 0}),
  )

  def __init__(self, safety, platform=CAR.TESLA_MODEL_Y, profile="marker489", longitudinal=True, settings_present=True):
    self.cp = car_params(platform, profile, longitudinal, settings_present)
    self.interface = CarInterface(self.cp)
    self.safety = safety
    safety.reset(self.cp)
    self.packers = {bus: CANPacker(DBC) for bus in (0, 2)}
    self.decoder = CANParser(DBC, [("DAS_steeringControl", 50), ("DAS_control", 25), ("APS_eacMonitor", 10)], 0)
    for bus, name, _, _ in self.INPUTS:
      parser = self.interface.can_parsers[Bus.party if bus == 0 else Bus.ap_party]
      _ = parser.vl[name]  # Real parser's normal lazy subscription, without disabling any checks.
    self.frame = 0
    self.history = []
    self.last_actuators = None

  def step(self, lateral=False, longitudinal=False, accel=0.0, angle=0.0, cancel=False, overrides=None, control_callback=None):
    nanos = 1_000_000_000 + self.frame * 10_000_000
    self.safety.lib.set_timer(nanos // 1000)
    incoming = []
    for bus, name, period, defaults in self.INPUTS:
      if self.frame % period:
        continue
      values = defaults | (overrides or {}).get(name, {})
      packer = self.packers[bus]
      unknown = values.keys() - packer.dbc.name_to_msg[name].sigs.keys()
      if unknown:
        raise ValueError(f"Unknown fixture signals for {name}: {unknown}")
      incoming.append(packer.make_can_msg(name, bus, values))
    rx_accepted = [self.safety.rx(message) for message in incoming]
    self.safety.lib.safety_tick()
    state = self.interface.update([(nanos, incoming)])
    if control_callback is None:
      cc = structs.CarControl.new_message()
      cc.enabled = lateral or longitudinal
      cc.latActive, cc.longActive = lateral, longitudinal
      cc.actuators.steeringAngleDeg, cc.actuators.accel = angle, accel
      cc.cruiseControl.cancel = cancel
      cc = cc.as_reader()
    else:
      # The callback sees this frame's actual parsed state and returns the command unchanged.
      cc = control_callback(state, nanos)
    input_hash = sha256_bytes(cc.as_builder().to_bytes()) if control_callback is not None else None
    actuators, outgoing = self.interface.apply(cc, nanos)
    self.last_actuators = actuators
    self.decoder.update([(nanos, outgoing)])
    decoded = []
    for address, data, bus in outgoing:
      decoded.append({"address": address, "bus": bus, "data_hex": data.hex(),
                      "signals": dict(self.decoder.vl[address]),
                      "decoded_fresh": all(t == nanos for t in self.decoder.ts_nanos[address].values()),
                      "safety_tx_accepted": self.safety.tx((address, data, bus))})
    record = {"frame": self.frame, "nanos": nanos,
              "inputs": {"enabled": bool(cc.enabled), "latActive": bool(cc.latActive), "longActive": bool(cc.longActive),
                         "accel": float(cc.actuators.accel), "angle": float(cc.actuators.steeringAngleDeg),
                         "cancel": bool(cc.cruiseControl.cancel)},
              "incoming": [{"address": a, "bus": b, "data_hex": d.hex()} for a, d, b in incoming],
              "can_valid": bool(state.canValid), "can_timeout": bool(state.canTimeout),
              "rx_accepted": rx_accepted, "safety_config_valid": bool(self.safety.lib.safety_config_valid()),
              "controls_allowed": bool(self.safety.lib.get_controls_allowed()),
              "longitudinal_allowed": bool(self.safety.lib.get_longitudinal_allowed()),
              "invalid_lkas_setting": bool(state.invalidLkasSetting), "stock_lkas": bool(state.stockLkas),
              "steering_disengage": bool(state.steeringDisengage), "brake_pressed": bool(state.brakePressed),
              "actual_angle": float(actuators.steeringAngleDeg), "outgoing": decoded}
    if input_hash is not None:
      record["car_control_sha256"] = input_hash
    self.frame += 1
    self.history.append(record)
    return record

  def run(self, frames=20, **kwargs):
    return [self.step(**kwargs) for _ in range(frames)]

  def prime(self):
    return self.run(30)[-1]


def messages(records, address):
  return [message for record in records for message in record["outgoing"] if message["address"] == address]


def sha256_bytes(data):
  return hashlib.sha256(data).hexdigest()
