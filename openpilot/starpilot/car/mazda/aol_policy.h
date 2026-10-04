#pragma once

#include "selfdrive/pandad/aol_protocol.h"

inline bool mazda_aol_param(uint16_t param) {
  return param == 0U;
}

inline constexpr AolSafetyProfile MAZDA_AOL_PROFILE{13U, mazda_aol_param, true};
