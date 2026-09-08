import crcmod
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.values import CAR, HyundaiFlags

hyundai_checksum = crcmod.mkCrcFun(0x11D, initCrc=0xFD, rev=False, xorOut=0xdf)


def create_lkas11(packer, frame, CP, apply_torque, steer_req,
                  torque_fault, lkas11, sys_warning, sys_state, enabled,
                  left_lane, right_lane,
                  left_lane_depart, right_lane_depart, lka_icon):
  values = {s: lkas11[s] for s in [
    "CF_Lkas_LdwsActivemode",
    "CF_Lkas_LdwsSysState",
    "CF_Lkas_SysWarning",
    "CF_Lkas_LdwsLHWarning",
    "CF_Lkas_LdwsRHWarning",
    "CF_Lkas_HbaLamp",
    "CF_Lkas_FcwBasReq",
    "CF_Lkas_HbaSysState",
    "CF_Lkas_FcwOpt",
    "CF_Lkas_HbaOpt",
    "CF_Lkas_FcwSysState",
    "CF_Lkas_FcwCollisionWarning",
    "CF_Lkas_FusionState",
    "CF_Lkas_FcwOpt_USM",
    "CF_Lkas_LdwsOpt_USM",
  ]}
  values["CF_Lkas_LdwsSysState"] = sys_state
  values["CF_Lkas_SysWarning"] = 3 if sys_warning else 0
  values["CF_Lkas_LdwsLHWarning"] = left_lane_depart
  values["CF_Lkas_LdwsRHWarning"] = right_lane_depart
  values["CR_Lkas_StrToqReq"] = apply_torque
  values["CF_Lkas_ActToi"] = steer_req
  values["CF_Lkas_ToiFlt"] = torque_fault  # seems to allow actuation on CR_Lkas_StrToqReq
  values["CF_Lkas_MsgCount"] = frame % 0x10

  if CP.carFingerprint in (CAR.HYUNDAI_SONATA, CAR.HYUNDAI_PALISADE, CAR.KIA_NIRO_EV, CAR.KIA_NIRO_HEV_2021, CAR.KIA_NIRO_PHEV_2022, CAR.HYUNDAI_SANTA_FE,
                           CAR.HYUNDAI_IONIQ_EV_2020, CAR.HYUNDAI_IONIQ_PHEV, CAR.KIA_SELTOS, CAR.HYUNDAI_ELANTRA_2021, CAR.GENESIS_G70_2020,
                           CAR.HYUNDAI_ELANTRA_HEV_2021, CAR.HYUNDAI_SONATA_HYBRID, CAR.HYUNDAI_KONA_EV, CAR.HYUNDAI_KONA_HEV, CAR.HYUNDAI_KONA_EV_2022,
                           CAR.HYUNDAI_SANTA_FE_2022, CAR.KIA_K5_2021, CAR.HYUNDAI_IONIQ_HEV_2022, CAR.HYUNDAI_SANTA_FE_HEV_2022,
                           CAR.HYUNDAI_SANTA_FE_PHEV_2022, CAR.KIA_STINGER_2022, CAR.KIA_K5_HEV_2020, CAR.KIA_CEED, CAR.KIA_XCEED_PHEV,
                           CAR.HYUNDAI_AZERA_6TH_GEN, CAR.HYUNDAI_AZERA_HEV_6TH_GEN, CAR.HYUNDAI_CUSTIN_1ST_GEN, CAR.HYUNDAI_KONA_2022, CAR.KIA_RAY_EV,
                           CAR.HYUNDAI_ELANTRA_2024, CAR.HYUNDAI_ELANTRA_HEV_2024):
    values["CF_Lkas_LdwsActivemode"] = int(left_lane) + (int(right_lane) << 1)
    values["CF_Lkas_LdwsOpt_USM"] = 2

    # FcwOpt_USM 5 = Orange blinking car + lanes
    # FcwOpt_USM 4 = Orange car + lanes
    # FcwOpt_USM 3 = Green blinking car + lanes
    # FcwOpt_USM 2 = Green car + lanes
    # FcwOpt_USM 1 = White car + lanes
    # FcwOpt_USM 0 = No car + lanes
    values["CF_Lkas_FcwOpt_USM"] = lka_icon if CP.carFingerprint == CAR.GENESIS_G70_2020 else 2 if enabled else 1

    # SysWarning 4 = keep hands on wheel
    # SysWarning 5 = keep hands on wheel (red)
    # SysWarning 6 = keep hands on wheel (red) + beep
    # Note: the warning is hidden while the blinkers are on
    values["CF_Lkas_SysWarning"] = 4 if sys_warning else 0

  # Likely cars lacking the ability to show individual lane lines in the dash
  elif CP.carFingerprint in (CAR.KIA_OPTIMA_G4, CAR.KIA_OPTIMA_G4_FL, CAR.HYUNDAI_KONA_NON_SCC):
    # SysWarning 4 = keep hands on wheel + beep
    values["CF_Lkas_SysWarning"] = 4 if sys_warning else 0

    # SysState 0 = no icons
    # SysState 1-2 = white car + lanes
    # SysState 3 = green car + lanes, green steering wheel
    # SysState 4 = green car + lanes
    values["CF_Lkas_LdwsSysState"] = lka_icon if CP.carFingerprint == CAR.HYUNDAI_KONA_NON_SCC else 3 if enabled else 1
    values["CF_Lkas_LdwsOpt_USM"] = 2  # non-2 changes above SysState definition

    # these have no effect
    values["CF_Lkas_LdwsActivemode"] = 0
    values["CF_Lkas_FcwOpt_USM"] = 0

  elif CP.carFingerprint == CAR.HYUNDAI_GENESIS:
    # This field is actually LdwsActivemode
    # Genesis and Optima fault when forwarding while engaged
    values["CF_Lkas_LdwsActivemode"] = 2

  if CP.carFingerprint == CAR.KIA_RAY_EV:
    if not enabled:
      values["CF_Lkas_LdwsActivemode"] = lkas11["CF_Lkas_LdwsActivemode"]
      values["CF_Lkas_LdwsSysState"] = lkas11["CF_Lkas_LdwsSysState"]
      values["CF_Lkas_FcwOpt_USM"] = lkas11["CF_Lkas_FcwOpt_USM"]
    values["CF_Lkas_LdwsOpt_USM"] = 0
    values["CF_Lkas_Chksum"] = 0

  dat = packer.make_can_msg("LKAS11", 0, values)[1]

  if CP.flags & HyundaiFlags.CHECKSUM_CRC8:
    # CRC Checksum as seen on 2019 Hyundai Santa Fe
    dat = dat[:6] + dat[7:8]
    checksum = hyundai_checksum(dat)
  elif CP.flags & HyundaiFlags.CHECKSUM_6B:
    # Checksum of first 6 Bytes, as seen on 2018 Kia Sorento
    checksum = sum(dat[:6]) % 256
  else:
    # Checksum of first 6 Bytes and last Byte as seen on 2018 Kia Stinger
    checksum = (sum(dat[:6]) + dat[7]) % 256

  values["CF_Lkas_Chksum"] = checksum

  return packer.make_can_msg("LKAS11", 0, values)


def create_lkas12(packer, lkas12):
  values = {s: lkas12[s] for s in (
    "CF_Lkas_TsrSlifOpt",
    "CF_LkasTsrStatus",
    "CF_Lkas_TsrSpeed_Display_Clu",
    "CF_LkasTsrSpeed_Display_Navi",
    "CF_Lkas_TsrAddinfo_Display",
    "CF_Lkas_Daw_USM",
  ) if s in lkas12}
  values["CF_LkasDawStatus"] = 0
  return packer.make_can_msg("LKAS12", 0, values)


def create_checksum_can_canfd_blended(packer, bus, addr, values):
  dat = packer.make_can_msg(addr, bus, values)[1]
  return hyundai_checksum(dat[1:8])


def create_lkas11_can_canfd_blended(packer, frame, CP, apply_steer, steer_req,
                                    torque_fault, lkas11, sys_warning, sys_state, enabled,
                                    left_lane, right_lane,
                                    left_lane_depart, right_lane_depart, msg_364,
                                    include_alerts=True, counter_mod=0x10):
  bus = CanBus(CP).ECAN
  values = {
    "CF_Lkas_LdwsActivemode": int(left_lane) + (int(right_lane) << 1),
    "CF_Lkas_LdwsLHWarning": left_lane_depart,
    "CF_Lkas_LdwsRHWarning": right_lane_depart,
    "CF_Lkas_FcwOpt_USM": 2 if enabled else 1,
    "CR_Lkas_StrToqReq": apply_steer,
    "CF_Lkas_ActToi": steer_req,
    "CF_Lkas_ToiFlt": torque_fault,
    "CF_Lkas_MsgCount": frame % counter_mod,
    "NEW_SIGNAL_1": 0,
    "NEW_SIGNAL_5": 100,
  }
  values["CF_Lkas_Chksum"] = create_checksum_can_canfd_blended(packer, bus, "LKAS11", values)

  alerts_364 = {k: v for k, v in msg_364.items() if k not in ("CHECKSUM", "COUNTER")} if msg_364 else {}
  alerts_364.setdefault("BYTE2", 0)
  alerts_364.setdefault("BYTE3", 0)
  alerts_364.setdefault("DAW_Status", 0)
  alerts_364["DAW_Warning"] = 0
  alerts_364.setdefault("BYTE5", 0)
  alerts_364.setdefault("BYTE6", 0)
  alerts_364.setdefault("BYTE7", 0)
  alerts_364["COUNTER"] = frame % counter_mod
  alerts_364["CHECKSUM"] = create_checksum_can_canfd_blended(packer, bus, "ALERTS_364", alerts_364)

  ret = [packer.make_can_msg("LKAS11", bus, values)]
  if include_alerts:
    ret.append(packer.make_can_msg("ALERTS_364", bus, alerts_364))
  return ret


def create_clu11(packer, frame, clu11, button, CP):
  values = {s: clu11[s] for s in [
    "CF_Clu_CruiseSwState",
    "CF_Clu_CruiseSwMain",
    "CF_Clu_SldMainSW",
    "CF_Clu_ParityBit1",
    "CF_Clu_VanzDecimal",
    "CF_Clu_Vanz",
    "CF_Clu_SPEED_UNIT",
    "CF_Clu_DetentOut",
    "CF_Clu_RheostatLevel",
    "CF_Clu_CluInfo",
    "CF_Clu_AmpInfo",
    "CF_Clu_AliveCnt1",
  ]}
  values["CF_Clu_CruiseSwState"] = button
  values["CF_Clu_AliveCnt1"] = frame % 0x10
  # send buttons to camera on camera-scc based cars
  if CP.flags & HyundaiFlags.CAMERA_SCC:
    bus = 2
  elif CP.flags & HyundaiFlags.CAN_CANFD_BLENDED:
    bus = CanBus(CP).ECAN
  else:
    bus = 0
  return packer.make_can_msg("CLU11", bus, values)


def create_lfahda_mfc(packer, enabled, frame=None, CP=None, lfa_icon=None):
  if lfa_icon is None:
    lfa_icon = 2 if enabled else 0

  values = {
    "LFA_Icon_State": lfa_icon,
  }
  can_canfd_blended = CP is not None and bool(CP.flags & HyundaiFlags.CAN_CANFD_BLENDED)
  bus = CanBus(CP).ECAN if can_canfd_blended else 0
  if can_canfd_blended:
    values["COUNTER"] = 0 if frame is None else frame % 0x10
    values["CHECKSUM"] = create_checksum_can_canfd_blended(packer, bus, "LFAHDA_MFC", values)
  return packer.make_can_msg("LFAHDA_MFC", bus, values)


def create_ray_lfahda_mfc(packer, lat_active, lfa_icon):
  values = {
    "HDA_USM": 2,
    "HDA_Icon_State": 2 if lfa_icon else 0,
    "HDA_VSetReq": 0,
    "HDA_Icon_Wheel": int(lat_active),
    "LFA_Icon_State": lfa_icon,
  }
  return packer.make_can_msg("LFAHDA_MFC", 0, values)


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
    # These values reproduce the stock status bytes without requesting AEB/FCA actuation.
    message_values.append(("FCA11", {
      "cr_vsm_deccmd": 255,
      "cf_vsm_deccmdact": 0,
    }))

  for name, values in message_values:
    values["COUNTER"] = idx % 0xF
    values["CHECKSUM"] = create_checksum_can_canfd_blended(packer, bus, name, values)
    commands.append(packer.make_can_msg(name, bus, values))

  return commands


def create_acc_commands(packer, enabled, accel, upper_jerk, idx, hud_control, set_speed, stopping, long_override, use_fca, CP,
                        main_cruise_enabled=True):
  commands = []

  scc11_values = {
    "MainMode_ACC": int(bool(main_cruise_enabled)),
    "TauGapSet": hud_control.leadDistanceBars,
    "VSetDis": set_speed if enabled else 0,
    "AliveCounterACC": idx % 0x10,
    "ObjValid": 1, # close lead makes controls tighter
    "ACC_ObjStatus": 1, # close lead makes controls tighter
    "ACC_ObjLatPos": 0,
    "ACC_ObjRelSpd": 0,
    "ACC_ObjDist": 1, # close lead makes controls tighter
    }
  commands.append(packer.make_can_msg("SCC11", 0, scc11_values))

  scc12_values = {
    "ACCMode": 2 if enabled and long_override else 1 if enabled else 0,
    "StopReq": 1 if stopping else 0,
    "aReqRaw": accel,
    "aReqValue": accel,  # stock ramps up and down respecting jerk limit until it reaches aReqRaw
    "CR_VSM_Alive": idx % 0xF,
  }

  # Keep ESC/TCS happy on non-FCA cars without explicitly showing the disabled AEB icon.
  if not use_fca:
    scc12_values["CF_VSM_ConfMode"] = 1
    scc12_values["AEB_Status"] = 2

  scc12_dat = packer.make_can_msg("SCC12", 0, scc12_values)[1]
  scc12_values["CR_VSM_ChkSum"] = 0x10 - sum(sum(divmod(i, 16)) for i in scc12_dat) % 0x10

  commands.append(packer.make_can_msg("SCC12", 0, scc12_values))

  scc14_values = {
    "ComfortBandUpper": 0.0, # stock usually is 0 but sometimes uses higher values
    "ComfortBandLower": 0.0, # stock usually is 0 but sometimes uses higher values
    "JerkUpperLimit": upper_jerk, # stock usually is 1.0 but sometimes uses higher values
    "JerkLowerLimit": 5.0, # stock usually is 0.5 but sometimes uses higher values
    "ACCMode": 2 if enabled and long_override else 1 if enabled else 4, # stock will always be 4 instead of 0 after first disengage
    "ObjGap": 2 if hud_control.leadVisible else 0, # 5: >30, m, 4: 25-30 m, 3: 20-25 m, 2: < 20 m, 0: no lead
  }
  commands.append(packer.make_can_msg("SCC14", 0, scc14_values))

  # Only send FCA11 on cars where it exists on the bus
  # On Camera SCC cars, FCA11 is not disabled, so we forward stock FCA11 back to the car forward hooks
  if use_fca and not (CP.flags & HyundaiFlags.CAMERA_SCC):
    # note that some vehicles most likely have an alternate checksum/counter definition
    # https://github.com/commaai/opendbc/commit/9ddcdb22c4929baf310295e832668e6e7fcfa602
    fca11_values = {
      "CR_FCA_Alive": idx % 0xF,
      "PAINT1_Status": 1,
      "FCA_DrvSetStatus": 1,
      "FCA_Status": 2,
    }
    fca11_dat = packer.make_can_msg("FCA11", 0, fca11_values)[1]
    fca11_values["CR_FCA_ChkSum"] = hyundai_checksum(fca11_dat[:7])
    commands.append(packer.make_can_msg("FCA11", 0, fca11_values))

  return commands


def create_acc_opt(packer, CP):
  commands = []

  scc13_values = {
    "SCCDrvModeRValue": 2,
    "SCC_Equip": 1,
    "Lead_Veh_Dep_Alert_USM": 2,
  }
  commands.append(packer.make_can_msg("SCC13", 0, scc13_values))

  # TODO: this needs to be detected and conditionally sent on unsupported long cars
  # On Camera SCC cars, FCA12 is not disabled, so we forward stock FCA12 back to the car forward hooks
  if not (CP.flags & HyundaiFlags.CAMERA_SCC):
    fca12_values = {
      "FCA_DrvSetState": 2,
      "FCA_USM": 2,
    }
    commands.append(packer.make_can_msg("FCA12", 0, fca12_values))

  return commands


def create_frt_radar_opt(packer):
  frt_radar11_values = {
    "CF_FCA_Equip_Front_Radar": 1,
  }
  return packer.make_can_msg("FRT_RADAR11", 0, frt_radar11_values)


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
