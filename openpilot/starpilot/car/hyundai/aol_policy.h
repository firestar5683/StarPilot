#pragma once

#include "selfdrive/pandad/aol_protocol.h"

inline bool hyundai_aol_param(uint16_t param) {
  // Existing mode28 entry also transports exact ordinary PE/EV9 requests.
  return param == 0x0811U || param == 0x0891U || param == 0x8815U || param == 0x8895U || param == 0x5491U || param == 0x5C91U;
}

inline constexpr AolSafetyProfile HYUNDAI_AOL_PROFILE{28U, hyundai_aol_param, true};

inline bool hyundai_classic_aol_param(uint16_t param) {
  return param == 0x1400U || param == 0x1C00U || param == 0x1440U || param == 0x1C40U ||
         param == 0x1402U || param == 0x1C02U || param == 0x1441U || param == 0x1C41U;
}

inline constexpr AolSafetyProfile HYUNDAI_CLASSIC_AOL_PROFILE{8U, hyundai_classic_aol_param, true};
