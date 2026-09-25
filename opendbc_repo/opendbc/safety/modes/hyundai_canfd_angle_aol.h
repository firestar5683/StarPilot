#pragma once

static inline bool hyundai_canfd_angle_aol_param(uint16_t param) {
  bool result = false;
  switch (param) {
    case 0x4008U:
    case 0x4010U:
    case 0x4028U:
    case 0x4090U:
    case 0x4208U:
    case 0x4228U:
    case 0x4408U:
    case 0x440AU:
    case 0x4410U:
    case 0x4412U:
    case 0x4428U:
    case 0x442AU:
    case 0x4490U:
    case 0x4492U:
    case 0x4608U:
    case 0x460AU:
    case 0x4628U:
    case 0x462AU:
    case 0x4809U:
    case 0x4811U:
    case 0x4829U:
    case 0x4891U:
    case 0x4A09U:
    case 0x4A29U:
    case 0x4C08U:
    case 0x4C28U:
    case 0x4E08U:
    case 0x4E28U:
    case 0x5008U:
    case 0x5010U:
    case 0x5028U:
    case 0x5090U:
    case 0x5208U:
    case 0x5228U:
    case 0x5491U:
    case 0x5809U:
    case 0x5811U:
    case 0x5829U:
    case 0x5891U:
    case 0x5A09U:
    case 0x5A29U:
    case 0x5C91U:
    case 0x6008U:
    case 0x600AU:
    case 0x6010U:
    case 0x6012U:
    case 0x6028U:
    case 0x602AU:
    case 0x6090U:
    case 0x6092U:
    case 0x6208U:
    case 0x620AU:
    case 0x6228U:
    case 0x622AU:
    case 0x6808U:
    case 0x680AU:
    case 0x6810U:
    case 0x6812U:
    case 0x6828U:
    case 0x682AU:
    case 0x6890U:
    case 0x6892U:
    case 0x6A08U:
    case 0x6A0AU:
    case 0x6A28U:
    case 0x6A2AU:
    case 0x7008U:
    case 0x700AU:
    case 0x7010U:
    case 0x7012U:
    case 0x7028U:
    case 0x702AU:
    case 0x7090U:
    case 0x7092U:
    case 0x7208U:
    case 0x720AU:
    case 0x7228U:
    case 0x722AU:
    case 0x7809U:
    case 0x7829U:
      result = true;
      break;
    default:
      break;
  }
  return result;
}
