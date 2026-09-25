// On-device SIMD regression: exact scalar agreement, row padding, tail lanes.
#include <algorithm>
#include <cstdio>
#include <random>
#include <stdexcept>
#include <vector>
#include "starpilot/system/android_auto/hw/rgba_to_nv12.h"

int main() {
  std::mt19937 random(7319);
  for (int width : {2, 14, 16, 18, 30, 32, 800, 802, 1280}) {
    int height = 38, stride = (width + 127) / 128 * 128;
    size_t offset = stride * 64, size = offset + stride * height / 2 + 32;
    std::vector<uint8_t> rgba(width * height * 4), actual(size, 0xa5), expected(size, 0xa5);
    for (auto &byte : rgba) byte = random() % 256;
    rgba_to_nv12(rgba.data(), actual.data(), width, height, stride, offset);
    for (int y = 0; y < height; y += 2) {
      for (int x = 0; x < width; x += 2) {
        int r = 0, g = 0, b = 0;
        for (int dy = 0; dy < 2; ++dy) {
          for (int dx = 0; dx < 2; ++dx) {
            const auto *p = rgba.data() + ((y + dy) * width + x + dx) * 4;
            expected[(y + dy) * stride + x + dx] = (66 * p[0] + 129 * p[1] + 25 * p[2] + 128) / 256 + 16;
            r += p[0]; g += p[1]; b += p[2];
          }
        }
        r = (r + 2) / 4; g = (g + 2) / 4; b = (b + 2) / 4;
        // Adding the output bias before division gives floor for negatives too.
        expected[offset + y / 2 * stride + x] = (-38 * r - 74 * g + 112 * b + 128 + 32768) / 256;
        expected[offset + y / 2 * stride + x + 1] = (112 * r - 94 * g - 18 * b + 128 + 32768) / 256;
      }
    }
    if (actual != expected) throw std::runtime_error("SIMD conversion or padding mismatch");
  }
  puts("PASS: SIMD pixels, tail lanes, row padding, and output bounds");
}
