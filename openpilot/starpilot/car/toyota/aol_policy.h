#pragma once

#include "selfdrive/pandad/aol_protocol.h"

inline bool toyota_aol_param(uint16_t param) {
  return (param == 73U) || (param == 585U);
}

inline constexpr AolSafetyProfile TOYOTA_AOL_PROFILE{2U, toyota_aol_param, true};
