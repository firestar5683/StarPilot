#!/usr/bin/env python3
# simple pandad wrapper that updates the panda first
import os
import struct
import usb1
import time
import signal
import subprocess

from cereal import custom
from panda import Panda, PandaDFU, PandaProtocolMismatch, FW_PATH
from opendbc.car.structs import CarParams
from opendbc.car.hyundai.values import HyundaiFlags
from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params, UnknownKeyName
from openpilot.system.hardware import HARDWARE
from openpilot.common.swaglog import cloudlog


EV9_LONG_PREINIT_STATUS_VERSION = 4
EV9_LONG_PREINIT_LEGACY_STATUS_VERSION = 3
EV9_LONG_PREINIT_H7_APP = "panda_h7.bin.signed"
EV9_LONG_PREINIT_FIRMWARE_NAMES = (
  "panda_h7_ev9_long_preinit.bin.signed",
  "panda_h7_ev9_long_preinit_hkg_remote.bin.signed",
  "panda_h7_ev9_long_preinit_can_ignition_only.bin.signed",
  "panda_h7_ev9_long_preinit_hkg_remote_can_ignition_only.bin.signed",
)
EV9_LONG_PREINIT_SAFETY_PARAM = 0x495
EV9_LONG_PREINIT_OPTIONAL_SAFETY_PARAM = 0x800

EV9_PREINIT_STATE_COLLECTING = 0
EV9_PREINIT_STATE_WAIT_SESSION = 1
EV9_PREINIT_STATE_WAIT_COMM_CONTROL = 2
EV9_PREINIT_STATE_WAIT_SUPPRESSION = 3
EV9_PREINIT_STATE_ACTIVE = 4
EV9_PREINIT_STATE_HANDOFF = 5
EV9_PREINIT_STATE_ABORTED = 6
EV9_PREINIT_STATE_RESTORING = 7
EV9_PREINIT_STATE_READY_PENDING_RESPONSE = 8

EV9_PREINIT_FLAG_START_INTENT = 0x02
EV9_PREINIT_FLAG_SUPPRESSION_CONFIRMED = 0x04
EV9_PREINIT_FLAG_BRIDGE_ACTIVE = 0x08
EV9_PREINIT_FLAG_HOST_HANDOFF = 0x10
EV9_PREINIT_FLAG_RESTORE_SENT = 0x40

EV9_PREINIT_IN_FLIGHT_STATES = frozenset({
  EV9_PREINIT_STATE_WAIT_SESSION,
  EV9_PREINIT_STATE_WAIT_COMM_CONTROL,
  EV9_PREINIT_STATE_WAIT_SUPPRESSION,
  EV9_PREINIT_STATE_ACTIVE,
  EV9_PREINIT_STATE_HANDOFF,
  EV9_PREINIT_STATE_RESTORING,
  EV9_PREINIT_STATE_READY_PENDING_RESPONSE,
})
EV9_PREINIT_PRESERVE_FLAGS = (EV9_PREINIT_FLAG_START_INTENT |
                              EV9_PREINIT_FLAG_SUPPRESSION_CONFIRMED |
                              EV9_PREINIT_FLAG_BRIDGE_ACTIVE |
                              EV9_PREINIT_FLAG_HOST_HANDOFF |
                              EV9_PREINIT_FLAG_RESTORE_SENT)

# Keep a local reader so the wrapper can inspect ownership before importing a
# newer panda Python package, and so upgrading the host cannot reset or reflash
# a legacy v3 Panda while it still owns a suppressed ADAS ECU.
EV9_LONG_PREINIT_LEGACY_STATUS_STRUCT = struct.Struct("<14BH11I")
EV9_LONG_PREINIT_STATUS_STRUCT = struct.Struct("<14BH12I")
EV9_LONG_PREINIT_TIMING_STRUCT = struct.Struct("<4B15I")


def get_selected_firmware_name(app_fn: str, remote_start: bool, hkg_remote_start: bool,
                               ignore_ignition_line: bool, ev9_long_preinit: bool = False) -> str:
  h7 = app_fn == EV9_LONG_PREINIT_H7_APP
  if ev9_long_preinit and h7:
    name_parts = ["panda_h7", "ev9", "long", "preinit"]
    if hkg_remote_start:
      name_parts.extend(["hkg", "remote"])
    if ignore_ignition_line:
      name_parts.append("can_ignition_only")
    return "_".join(name_parts) + ".bin.signed"

  if not remote_start and not hkg_remote_start and not ignore_ignition_line:
    return app_fn

  name_parts = ["panda_h7" if h7 else "panda"]
  if hkg_remote_start:
    name_parts.extend(["hkg", "remote"])
  elif remote_start:
    name_parts.append("remote")
  if ignore_ignition_line:
    name_parts.append("can_ignition_only")
  return "_".join(name_parts) + ".bin.signed"


def get_expected_firmware_path(panda: Panda, remote_start: bool, hkg_remote_start: bool,
                               ignore_ignition_line: bool, ev9_long_preinit: bool = False) -> str:
  app_fn = panda.get_mcu_type().config.app_fn
  selected_fn = get_selected_firmware_name(app_fn, remote_start, hkg_remote_start, ignore_ignition_line, ev9_long_preinit)
  if selected_fn != app_fn:
    selected_path = os.path.join(FW_PATH, selected_fn)
    if os.path.isfile(selected_path):
      return selected_path
    if ev9_long_preinit and app_fn == EV9_LONG_PREINIT_H7_APP:
      raise FileNotFoundError(f"Selected EV9 Panda preinit firmware not found: {selected_path}")
    cloudlog.warning(f"Selected panda firmware not found: {selected_path}, falling back to default")
  return os.path.join(FW_PATH, app_fn)


def get_expected_signature(panda: Panda, remote_start: bool, hkg_remote_start: bool,
                           ignore_ignition_line: bool, ev9_long_preinit: bool = False) -> bytes:
  try:
    fn = get_expected_firmware_path(panda, remote_start, hkg_remote_start, ignore_ignition_line, ev9_long_preinit)
    return Panda.get_signature_from_firmware(fn)
  except Exception:
    cloudlog.exception("Error computing expected signature")
    return b""


def get_remote_start_boots_comma(params: Params) -> bool:
  try:
    return params.get_bool("RemoteStartBootsComma")
  except UnknownKeyName:
    return False


def get_hkg_remote_start_boots_comma(params: Params) -> bool:
  try:
    return params.get_bool("HKGRemoteStartBootsComma")
  except UnknownKeyName:
    return False


def get_ignore_ignition_line(params: Params) -> bool:
  try:
    return (params.get("CarMake", encoding="utf-8") or "").lower() == "gm" and params.get_bool("IgnoreIgnitionLine")
  except UnknownKeyName:
    return False


def get_ev9_long_preinit_panda(params: Params) -> bool:
  """Select preinit firmware only for an explicitly armed, persistently identified EV9."""
  try:
    enabled = (params.get_bool("EV9LongPreinitPanda") and
               params.get_bool("OpenpilotEnabledToggle") and
               params.get_bool("AlphaLongitudinalEnabled"))
  except UnknownKeyName:
    return False
  if not enabled:
    return False

  # The cached suppressed-start path in card requires both schemas. Suppressing
  # ADAS without StarPilotCarParamsPersistent would remove frames needed to
  # finish a fresh fingerprint.
  cached_fpcp = params.get("StarPilotCarParamsPersistent")
  if not cached_fpcp:
    return False
  try:
    with custom.StarPilotCarParams.from_bytes(cached_fpcp):
      pass
  except Exception:
    cloudlog.exception("Unable to read persistent StarPilotCarParams for EV9 Panda firmware selection")
    return False

  cached_params = params.get("CarParamsPersistent")
  if cached_params is None:
    return False
  try:
    with CarParams.from_bytes(cached_params) as CP:
      if len(CP.safetyConfigs) == 0:
        return False
      safety = CP.safetyConfigs[-1]
      required_flags = (HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEERING |
                        HyundaiFlags.CANFD_LKA_STEERING_ALT | HyundaiFlags.CANFD_ANGLE_STEERING)
      return (CP.brand == "hyundai" and str(CP.carFingerprint) == "KIA_EV9" and
              CP.openpilotLongitudinalControl and not CP.pcmCruise and
              safety.safetyModel == CarParams.SafetyModel.hyundaiCanfdEv9 and
              (safety.safetyParam & ~EV9_LONG_PREINIT_OPTIONAL_SAFETY_PARAM) == EV9_LONG_PREINIT_SAFETY_PARAM and
              (CP.flags & int(required_flags)) == int(required_flags) and
              any(fw.ecu == CarParams.Ecu.adas and fw.address == 0x730 for fw in CP.carFw))
  except Exception:
    cloudlog.exception("Unable to read persistent CarParams for EV9 Panda firmware selection")
    return False


def _get_raw_ev9_long_preinit_status(panda: Panda):
  handle = getattr(panda, "_handle", None)
  if handle is None:
    return None

  try:
    dat = handle.controlRead(Panda.REQUEST_IN, 0xe9, 0, 0, EV9_LONG_PREINIT_STATUS_STRUCT.size)
  except usb1.USBError:
    return None

  if len(dat) == EV9_LONG_PREINIT_STATUS_STRUCT.size and dat[0] == EV9_LONG_PREINIT_STATUS_VERSION:
    status = EV9_LONG_PREINIT_STATUS_STRUCT.unpack(dat)
  elif len(dat) == EV9_LONG_PREINIT_LEGACY_STATUS_STRUCT.size and dat[0] == EV9_LONG_PREINIT_LEGACY_STATUS_VERSION:
    legacy_status = EV9_LONG_PREINIT_LEGACY_STATUS_STRUCT.unpack(dat)
    status = (*legacy_status, 0)
  else:
    return None

  result = {
    "valid": True,
    "version": status[0],
    "state": status[1],
    "flags": status[13] if status[0] == EV9_LONG_PREINIT_STATUS_VERSION else 0,
    "fingerprint": status[2],
    "attempts": status[3],
    "last_service": status[4],
    "last_response": status[5],
    "last_nrc": status[6],
    "communication_type": status[7],
    "trigger": status[8],
    "first_ecan_len": status[9],
    "powertrain_state": status[10],
    "powertrain_boot_state": status[11],
    "powertrain_init_state": status[12],
    "first_ecan_addr": status[14],
    "first_can_us": status[15],
    "state_started_us": status[16],
    "trigger_us": status[17],
    "first_ecan_us": status[18],
    "driver_braking_us": status[19],
    "pre_ready_us": status[20],
    "ignition_us": status[21],
    "session_response_us": status[22],
    "comm_control_us": status[23],
    "last_powertrain_us": status[24],
    "ready_us": status[25],
    "outcome_us": status[26],
    "timing_valid": False,
  }

  if result["version"] == EV9_LONG_PREINIT_STATUS_VERSION:
    try:
      timing_dat = handle.controlRead(Panda.REQUEST_IN, 0xe9, 1, 0, EV9_LONG_PREINIT_TIMING_STRUCT.size)
    except usb1.USBError:
      return result
    if len(timing_dat) == EV9_LONG_PREINIT_TIMING_STRUCT.size:
      timing = EV9_LONG_PREINIT_TIMING_STRUCT.unpack(timing_dat)
      if timing[0] == EV9_LONG_PREINIT_STATUS_VERSION and timing[1] == 1:
        try:
          verified_dat = handle.controlRead(Panda.REQUEST_IN, 0xe9, 0, 0, EV9_LONG_PREINIT_STATUS_STRUCT.size)
        except usb1.USBError:
          return result
        if len(verified_dat) == EV9_LONG_PREINIT_STATUS_STRUCT.size and verified_dat[0] == EV9_LONG_PREINIT_STATUS_VERSION:
          verified = EV9_LONG_PREINIT_STATUS_STRUCT.unpack(verified_dat)
          coherent = all(status[index] == verified[index] for index in (0, 1, 13, 17, 22, 23, 25, 26)) and \
            timing[2] == verified[13] and timing[6] == verified[22] and timing[7] == verified[23] and \
            timing[12] == verified[25]
          if coherent:
            result.update({
              "timing_valid": True,
              "timing_flags": timing[2],
              "cycle_started_us": timing[4],
              "session_request_us": timing[5],
              "timing_session_response_us": timing[6],
              "timing_comm_control_us": timing[7],
              "comm_control_response_us": timing[8],
              "last_critical_adas_us": timing[9],
              "first_replacement_us": timing[10],
              "suppression_confirmed_us": timing[11],
              "timing_ready_us": timing[12],
              "handoff_us": timing[13],
              "restore_us": timing[14],
              "abort_us": timing[15],
              "last_host_tx_us": timing[16],
              "last_tester_present_us": timing[17],
              "last_vehicle_frame_us": timing[18],
            })
          else:
            result["valid"] = False
  return result


def get_ev9_long_preinit_status(panda: Panda):
  # Use the local reader for mutation decisions so timing coherence does not
  # depend on the version of the imported panda Python package.
  raw_status = _get_raw_ev9_long_preinit_status(panda)
  if raw_status is not None or getattr(panda, "_handle", None) is not None:
    return raw_status

  status_reader = getattr(panda, "get_ev9_long_preinit_status", None)
  if status_reader is not None:
    try:
      status = status_reader()
      if status is not None:
        return status
    except usb1.USBError:
      pass
  return _get_raw_ev9_long_preinit_status(panda)


def ev9_long_preinit_status_valid(status) -> bool:
  return status is not None and status.get("valid", True) and status.get("version") in (
    EV9_LONG_PREINIT_LEGACY_STATUS_VERSION, EV9_LONG_PREINIT_STATUS_VERSION,
  )


def ev9_long_preinit_active(status) -> bool:
  if not ev9_long_preinit_status_valid(status):
    return False
  return (status.get("state") in (EV9_PREINIT_STATE_ACTIVE, EV9_PREINIT_STATE_HANDOFF) or
          bool(status.get("flags", 0) & (EV9_PREINIT_FLAG_SUPPRESSION_CONFIRMED | EV9_PREINIT_FLAG_BRIDGE_ACTIVE)))


def ev9_long_preinit_must_preserve(status) -> bool:
  if not ev9_long_preinit_status_valid(status):
    return False
  legacy_ambiguous_disable = (status.get("version") == EV9_LONG_PREINIT_LEGACY_STATUS_VERSION and
                              status.get("comm_control_us", 0) != 0)
  return (legacy_ambiguous_disable or status.get("state") in EV9_PREINIT_IN_FLIGHT_STATES or
          bool(status.get("flags", 0) & EV9_PREINIT_PRESERVE_FLAGS))


def ev9_long_preinit_firmware_selected(panda: Panda, enabled: bool) -> bool:
  return enabled and panda.is_internal() and panda.get_mcu_type().config.app_fn == EV9_LONG_PREINIT_H7_APP


def ev9_long_preinit_resident_signature(signature: bytes) -> bool:
  if not signature:
    return False
  for firmware_name in EV9_LONG_PREINIT_FIRMWARE_NAMES:
    firmware_path = os.path.join(FW_PATH, firmware_name)
    if os.path.isfile(firmware_path) and Panda.get_signature_from_firmware(firmware_path) == signature:
      return True
  return False


def ev9_long_preinit_status_snapshot(status):
  if not ev9_long_preinit_status_valid(status):
    return None
  return tuple(status.get(key, 0) for key in (
    "version", "state", "flags", "attempts", "state_started_us", "comm_control_us", "outcome_us",
  ))


def ev9_long_preinit_status_stable(first_status, second_status) -> bool:
  return ev9_long_preinit_status_snapshot(first_status) == ev9_long_preinit_status_snapshot(second_status)


def ev9_long_preinit_flash_blocked(status, firmware_selected: bool, ignition_on: bool,
                                   resident_firmware: bool = False, status_stable: bool = True) -> bool:
  if resident_firmware and not ev9_long_preinit_status_valid(status):
    return True
  preinit_sensitive = firmware_selected or resident_firmware or ev9_long_preinit_status_valid(status)
  return ev9_long_preinit_must_preserve(status) or (preinit_sensitive and (ignition_on or not status_stable))


def ev9_long_preinit_reset_blocked(status, firmware_selected: bool, resident_firmware: bool = False,
                                   ignition_on: bool = False, status_stable: bool = True) -> bool:
  # A selected resident image must retain everything collected before pandad
  # starts, even if the vehicle has not reached an in-flight state yet.
  return (firmware_selected or resident_firmware or ev9_long_preinit_must_preserve(status) or
          (ev9_long_preinit_status_valid(status) and (ignition_on or not status_stable)))


def panda_ignition_on(panda: Panda) -> bool:
  health = panda.health()
  return bool(health["ignition_line"] or health["ignition_can"])


def flash_panda(panda_serial: str, remote_start: bool, hkg_remote_start: bool,
                ignore_ignition_line: bool, ev9_long_preinit: bool = False,
                preinit_recovery_blocked: bool = False) -> Panda:
  try:
    panda = Panda(panda_serial)
  except PandaProtocolMismatch:
    if ev9_long_preinit or preinit_recovery_blocked:
      cloudlog.error("Panda protocol mismatch with EV9 preinit armed/latched; refusing hardware recovery")
    else:
      cloudlog.warning("detected protocol mismatch, reflashing panda")
      HARDWARE.recover_internal_panda()
    raise

  internal_panda = panda.is_internal()
  preinit_status = None if panda.bootstub or not internal_panda else get_ev9_long_preinit_status(panda)
  if ev9_long_preinit_must_preserve(preinit_status):
    cloudlog.warning(f"Preserving in-flight EV9 Panda preinit firmware on {panda_serial}: {preinit_status}")
    return panda

  preinit_firmware_selected = ev9_long_preinit_firmware_selected(panda, ev9_long_preinit)
  fw_path = get_expected_firmware_path(panda, remote_start, hkg_remote_start, ignore_ignition_line, preinit_firmware_selected)
  fw_signature = get_expected_signature(panda, remote_start, hkg_remote_start, ignore_ignition_line, preinit_firmware_selected)

  panda_version = "bootstub" if panda.bootstub else panda.get_version()
  panda_signature = b"" if panda.bootstub else panda.get_signature()
  resident_preinit_firmware = ev9_long_preinit_resident_signature(panda_signature)
  cloudlog.warning(f"Panda {panda_serial} connected, version: {panda_version}, signature {panda_signature.hex()[:16]}, expected {fw_signature.hex()[:16]}")

  if panda.bootstub or panda_signature != fw_signature:
    # Status can advance while signatures are read from disk. Recheck at the
    # last possible point before a firmware mutation.
    status_before_health = None if panda.bootstub or not (internal_panda or resident_preinit_firmware) else \
      get_ev9_long_preinit_status(panda)
    preinit_sensitive = (preinit_firmware_selected or resident_preinit_firmware or
                         ev9_long_preinit_status_valid(status_before_health))
    ignition_on = panda_ignition_on(panda) if preinit_sensitive and not panda.bootstub else False
    status_after_health = get_ev9_long_preinit_status(panda) if preinit_sensitive and not panda.bootstub else status_before_health
    status_stable = ev9_long_preinit_status_stable(status_before_health, status_after_health)
    preinit_status = status_after_health if ev9_long_preinit_status_valid(status_after_health) else status_before_health
    if ev9_long_preinit_flash_blocked(preinit_status, preinit_firmware_selected, ignition_on,
                                      resident_preinit_firmware, status_stable):
      if preinit_sensitive and ignition_on and not ev9_long_preinit_must_preserve(preinit_status):
        cloudlog.error(f"Refusing to change resident EV9 Panda preinit firmware while ignition is on: {panda_serial}")
        return panda
      cloudlog.warning(f"Preserving in-flight EV9 Panda preinit firmware on {panda_serial}: {preinit_status}")
      return panda
    cloudlog.info("Panda firmware out of date, update required")
    panda.flash(fn=fw_path)
    cloudlog.info("Done flashing")

  if panda.bootstub:
    bootstub_version = panda.get_version()
    cloudlog.info(f"Flashed firmware not booting, flashing development bootloader. {bootstub_version=}, {internal_panda=}")
    if internal_panda:
      HARDWARE.recover_internal_panda()
    panda.recover(reset=(not internal_panda))
    cloudlog.info("Done flashing bootstub")

  if panda.bootstub:
    cloudlog.info("Panda still not booting, exiting")
    raise AssertionError

  panda_signature = panda.get_signature()
  if panda_signature != fw_signature:
    cloudlog.info("Version mismatch after flashing, exiting")
    raise AssertionError

  return panda


def main() -> None:
  # signal pandad to close the relay and exit
  def signal_handler(signum, frame):
    cloudlog.info(f"Caught signal {signum}, exiting")
    nonlocal do_exit
    do_exit = True
    if process is not None:
      process.send_signal(signal.SIGINT)

  process = None
  do_exit = False
  signal.signal(signal.SIGINT, signal_handler)

  count = 0
  first_run = True
  params = Params()
  no_internal_panda_count = 0
  preinit_resident_latched = False

  while not do_exit:
    try:
      count += 1
      cloudlog.event("pandad.flash_and_connect", count=count)
      params.remove("PandaSignatures")
      ev9_long_preinit = get_ev9_long_preinit_panda(params)
      preinit_resident_latched |= ev9_long_preinit

      # Handle missing internal panda
      if no_internal_panda_count > 0:
        if preinit_resident_latched:
          cloudlog.error("Panda missing with resident EV9 preinit latched; refusing hardware reset/recovery")
        elif no_internal_panda_count == 3:
          cloudlog.info("No pandas found, putting internal panda into DFU")
          HARDWARE.recover_internal_panda()
        else:
          cloudlog.info("No pandas found, resetting internal panda")
          HARDWARE.reset_internal_panda()
        time.sleep(3)  # wait to come back up

      # Flash all Pandas in DFU mode
      dfu_serials = PandaDFU.list()
      if len(dfu_serials) > 0 and preinit_resident_latched:
        cloudlog.error("Panda in DFU with resident EV9 preinit latched; refusing automatic recovery")
        time.sleep(1)
      elif len(dfu_serials) > 0:
        for serial in dfu_serials:
          cloudlog.info(f"Panda in DFU mode found, flashing recovery {serial}")
          PandaDFU(serial).recover()
        time.sleep(1)

      panda_serials = Panda.list()
      if len(panda_serials) == 0:
        no_internal_panda_count += 1
        continue

      cloudlog.info(f"{len(panda_serials)} panda(s) found, connecting - {panda_serials}")

      # Flash pandas
      pandas: list[Panda] = []
      remote_start = get_remote_start_boots_comma(params)
      hkg_remote_start = get_hkg_remote_start_boots_comma(params)
      ignore_ignition_line = get_ignore_ignition_line(params)
      for serial in panda_serials:
        pandas.append(flash_panda(serial, remote_start, hkg_remote_start, ignore_ignition_line,
                                  ev9_long_preinit, preinit_resident_latched))

      # Ensure internal panda is present if expected
      internal_pandas = [panda for panda in pandas if panda.is_internal()]
      if HARDWARE.has_internal_panda() and len(internal_pandas) == 0:
        cloudlog.error("Internal panda is missing, trying again")
        no_internal_panda_count += 1
        continue
      no_internal_panda_count = 0

      # sort pandas to have deterministic order
      # * the internal one is always first
      # * then sort by hardware type
      # * as a last resort, sort by serial number
      pandas.sort(key=lambda x: (not x.is_internal(), x.get_type(), x.get_usb_serial()))
      panda_serials = [p.get_usb_serial() for p in pandas]

      # log panda fw versions
      params.put("PandaSignatures", b','.join(p.get_signature() for p in pandas))

      resident_ev9_long_preinit = False
      ev9_preinit_serials = []
      for panda in pandas:
        # check health for lost heartbeat
        health = panda.health()
        if health["heartbeat_lost"]:
          params.put_bool("PandaHeartbeatLost", True)
          cloudlog.event("heartbeat lost", deviceState=health, serial=panda.get_usb_serial())
        if health["som_reset_triggered"]:
          params.put_bool("PandaSomResetTriggered", True)
          cloudlog.event("panda.som_reset_triggered", health=health, serial=panda.get_usb_serial())

        preinit_firmware_selected = ev9_long_preinit_firmware_selected(panda, ev9_long_preinit)
        resident_preinit_firmware = ev9_long_preinit_resident_signature(panda.get_signature())
        preinit_status = get_ev9_long_preinit_status(panda) if panda.is_internal() or resident_preinit_firmware else None
        resident_status = ev9_long_preinit_status_valid(preinit_status)
        resident_ev9_long_preinit |= resident_status or resident_preinit_firmware
        if resident_status or resident_preinit_firmware:
          ev9_preinit_serials.append(panda.get_usb_serial())

        preinit_sensitive = resident_status or resident_preinit_firmware or preinit_firmware_selected
        verified_status = get_ev9_long_preinit_status(panda) if first_run and preinit_sensitive else preinit_status
        status_stable = ev9_long_preinit_status_stable(preinit_status, verified_status)
        preinit_status = verified_status if ev9_long_preinit_status_valid(verified_status) else preinit_status
        verified_ignition_on = panda_ignition_on(panda) if first_run and preinit_sensitive else bool(
          health["ignition_line"] or health["ignition_can"]
        )
        preserve_preinit = ev9_long_preinit_reset_blocked(
          preinit_status, preinit_firmware_selected, resident_preinit_firmware,
          verified_ignition_on, status_stable,
        )
        if first_run and preserve_preinit:
          cloudlog.warning(f"Preserving EV9 Panda preinit state on {panda.get_usb_serial()}: {preinit_status}")
        elif first_run:
          # reset panda to ensure we're in a good state
          cloudlog.info(f"Resetting panda {panda.get_usb_serial()}")
          panda.reset(reconnect=True)

      preinit_resident_latched |= bool(ev9_preinit_serials)

      for p in pandas:
        p.close()
    # TODO: wrap all panda exceptions in a base panda exception
    except (usb1.USBErrorNoDevice, usb1.USBErrorPipe):
      # a panda was disconnected while setting everything up. let's try again
      cloudlog.exception("Panda USB exception while setting up")
      continue
    except PandaProtocolMismatch:
      cloudlog.exception("pandad.protocol_mismatch")
      continue
    except Exception:
      cloudlog.exception("pandad.uncaught_exception")
      continue

    first_run = False

    # run pandad with all connected serials as arguments
    run_ev9_long_preinit = ev9_long_preinit or resident_ev9_long_preinit
    if (get_remote_start_boots_comma(params) or get_hkg_remote_start_boots_comma(params) or
        get_ignore_ignition_line(params) or run_ev9_long_preinit):
      os.environ["BOARDD_SKIP_FW_CHECK"] = "1"
    else:
      os.environ.pop("BOARDD_SKIP_FW_CHECK", None)
    if ev9_preinit_serials:
      os.environ["BOARDD_EV9_LONG_PREINIT_SERIALS"] = ",".join(ev9_preinit_serials)
    else:
      os.environ.pop("BOARDD_EV9_LONG_PREINIT_SERIALS", None)
    os.environ['MANAGER_DAEMON'] = 'pandad'
    process = subprocess.Popen(["./pandad", *panda_serials], cwd=os.path.join(BASEDIR, "selfdrive/pandad"))
    process.wait()


if __name__ == "__main__":
  main()
