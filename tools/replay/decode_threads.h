#pragma once

// Zero means unspecified: preserve FFmpeg's existing default behavior.
inline int replay_decode_threads(const char *value) {
  if (value == nullptr) return 0;
  if (value[0] >= '1' && value[0] <= '4' && value[1] == '\0') return value[0] - '0';
  return -1;
}
