#pragma once

#include "selfdrive/pandad/aol_protocol.h"

inline bool tesla_preap_aol_param(uint16_t param) {
  return param == 0U;
}

inline constexpr AolSafetyProfile TESLA_PREAP_AOL_PROFILE{39U, tesla_preap_aol_param, true};
