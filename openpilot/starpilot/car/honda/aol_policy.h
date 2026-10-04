#pragma once

#include "selfdrive/pandad/aol_protocol.h"

inline bool honda_aol_param(uint16_t param) {
  return (param == 34U) || (param == 35U);
}

inline constexpr AolSafetyProfile HONDA_AOL_PROFILE{20U, honda_aol_param, false};
