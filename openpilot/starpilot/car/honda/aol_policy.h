#pragma once

#include "selfdrive/pandad/aol_protocol.h"

inline bool honda_aol_param(uint16_t param) {
  return (param == 34U) || (param == 35U) || (param == 163U);
}

inline constexpr AolSafetyProfile HONDA_AOL_PROFILE{20U, honda_aol_param, false};


inline bool honda_stock_aol_param(uint16_t param) {
  return (param == 0U) || (param == 1U) || (param == 8U) || (param == 9U) || (param == 10U) || (param == 11U);
}

inline bool honda_nidec_aol_param(uint16_t param) {
  return (param == 0U) || (param == 4U) || (param == 260U);
}

inline constexpr AolSafetyProfile HONDA_STOCK_AOL_PROFILE{20U, honda_stock_aol_param, true};
inline constexpr AolSafetyProfile HONDA_NIDEC_AOL_PROFILE{1U, honda_nidec_aol_param, true};
