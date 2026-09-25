#pragma once

#include "openpilot/selfdrive/pandad/aol_protocol.h"

static inline bool ford_aol_param(uint16_t param) {
  bool result = false;
  switch (param) {
    case 8U: case 9U: case 10U: case 11U: case 12U: case 13U:
    case 18U: case 19U: case 32U: case 33U: case 66U: case 67U:
      result = true;
      break;
    default:
      break;
  }
  return result;
}
inline constexpr AolSafetyProfile FORD_AOL_PROFILE{6U, ford_aol_param, true};
