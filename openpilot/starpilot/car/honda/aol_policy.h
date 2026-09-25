#pragma once

#include "selfdrive/pandad/aol_protocol.h"

inline bool honda_aol_param(uint16_t param) {
  return (param & 0x22U) == 0x22U && (param & 0x18U) == 0U;
}

inline constexpr AolSafetyProfile HONDA_AOL_PROFILE{20U, honda_aol_param, false};
