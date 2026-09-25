"""Mixed longitudinal CAN message builders."""
from opendbc.car.hyundai.hyundaican import hyundai_checksum
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.values import HyundaiFlags


def create_checksum_can_canfd_blended(packer, bus, addr, values):
  dat = packer.make_can_msg(addr, bus, values)[1]
  return hyundai_checksum(dat[1:8])


def create_acc_commands_can_canfd_blended(packer, enabled, accel, upper_jerk, idx, hud_control, set_speed,
                                          stopping, long_override, use_fca, CP):
  commands = []
  bus = CanBus(CP).ECAN

  scc11_values = {
    "aReqRaw": accel,
    "aReqValue": accel,
    "JerkUpperLimit": upper_jerk,
    "JerkLowerLimit": 5.0,
    "ComfortBandUpper": 0.0,
    "ComfortBandLower": 0.0,
    "COUNTER": idx % 0x10,
  }
  scc11_values["CHECKSUM"] = create_checksum_can_canfd_blended(packer, bus, "SCC11", scc11_values)
  commands.append(packer.make_can_msg("SCC11", bus, scc11_values))

  scc12_values = {
    "MainMode_ACC": 1,
    "ACCMode_Inactive": 0 if enabled else 1,
    "TauGapSet": hud_control.leadDistanceBars,
    "VSetDis": set_speed if enabled else 0,
    "ACC_ObjDist": 1,
    "ACCMode": 2 if enabled and long_override else 1 if enabled else 0,
    "StopReq": 1 if stopping else 0,
    "ACC_ObjDist_Ref": 1,
    "COUNTER": idx % 0x10,
  }
  scc12_values["CHECKSUM"] = create_checksum_can_canfd_blended(packer, bus, "SCC12", scc12_values)
  commands.append(packer.make_can_msg("SCC12", bus, scc12_values))

  scc14_values = {
    "ACC_ObjRelSpd": 0,
    "ObjValid": 1,
    "ObjStatus": 1,
    "COUNTER": idx % 0x10,
  }
  scc14_values["CHECKSUM"] = create_checksum_can_canfd_blended(packer, bus, "SCC14", scc14_values)
  commands.append(packer.make_can_msg("SCC14", bus, scc14_values))

  if use_fca and not (CP.flags & HyundaiFlags.CAMERA_SCC):
    fca11_values = {
      "cr_vsm_deccmd": 255,
      "cf_vsm_deccmdact": 127,
      "COUNTER": idx % 0x10,
    }
    fca11_values["CHECKSUM"] = create_checksum_can_canfd_blended(packer, bus, "FCA11", fca11_values)
    commands.append(packer.make_can_msg("FCA11", bus, fca11_values))

  return commands


def create_acc_commands_can_canfd_blended_hda2(packer, enabled, accel, accel_last, upper_jerk, idx,
                                               hud_control, set_speed, stopping, long_override, use_fca, CP):
  commands = []
  bus = CanBus(CP).ECAN
  jerk = 5.0

  if not enabled or long_override:
    accel_raw, accel_value = 0.0, 0.0
  else:
    accel_raw = accel
    accel_value = max(accel_last - jerk / 50.0, min(accel, accel_last + jerk / 50.0))

  message_values = [
    ("SCC11", {
      "aReqRaw": accel_raw,
      "aReqValue": accel_value,
      "JerkUpperLimit": upper_jerk,
      "JerkLowerLimit": jerk if enabled else 1.0,
    }),
    ("SCC12", {
      "MainMode_ACC": 1,
      "ACCMode_Inactive": 0 if enabled else 1,
      "TauGapSet": hud_control.leadDistanceBars,
      "VSetDis": set_speed,
      "ACC_ObjDist": 1,
      "ACCMode": 2 if enabled and long_override else 1 if enabled else 0,
      "StopReq": 1 if stopping else 0,
    }),
    ("SCC14", {
      "ACC_ObjRelSpd": 0,
      "ObjValid": 0,
      "ObjStatus": 2 if hud_control.leadVisible and enabled else 1 if hud_control.leadVisible else 0,
    }),
  ]

  if use_fca and not (CP.flags & HyundaiFlags.CAMERA_SCC):
    # Retained original bytes; the FCA deceleration sentinel semantics remain unverified.
    message_values.append(("FCA11", {
      "cr_vsm_deccmd": 255,
      "cf_vsm_deccmdact": 0,
    }))

  for name, values in message_values:
    values["COUNTER"] = idx % 0xF
    values["CHECKSUM"] = create_checksum_can_canfd_blended(packer, bus, name, values)
    commands.append(packer.make_can_msg(name, bus, values))

  return commands


def create_radar_aux_messages(packer, CAN, frame, hda2=False):
  commands = []

  message_specs = (
    ("RADAR_0x363", 2, {"FCA_ESA": 1}),
    ("RADAR_0x398", 5, {"BYTE4": 0x80, "BYTE5": 0x5D}),
    ("RADAR_0x399", 5, {"BYTE2": 0x02}),
    ("RADAR_0x39a", 5, {"BYTE7": 0xFF}),
    ("RADAR_0x39b", 5, {}),
    ("RADAR_0x39c", 5, {"BYTE5": 0xE0, "BYTE6": 0x79}),
    ("RADAR_0x43a", 20, {"BYTE2": 0x07}),
  ) if hda2 else (
    ("RADAR_0x363", 2, {"FCA_ESA": 1}),
    ("RADAR_0x398", 5, {"BYTE4": 0x80, "BYTE5": 0x10}),
  )

  for addr, freq, values in message_specs:
    if frame % freq != 0:
      continue

    msg_values = values | {"COUNTER": frame % (0xF if hda2 else 0x10)}
    msg_values["CHECKSUM"] = create_checksum_can_canfd_blended(packer, CAN.ECAN, addr, msg_values)
    commands.append(packer.make_can_msg(addr, CAN.ECAN, msg_values))

  return commands



def create_blended_adrv_messages(packer, CAN, frame):
  # Exact reached original create_adrv_messages(..., blended_hda2=True) branch.
  return [packer.make_can_msg("ADRV_0x51", CAN.ACAN, {})]
