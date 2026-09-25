#pragma once

// From yummydirtx/openpilot tools/android_auto/rgba_to_nv12.h (MIT), pinned at
// 672a16f6183567c0ada53654f8527d97e1a483fa.

#include <arm_neon.h>
#include <cstddef>
#include <cstdint>

// BT.601 limited-range conversion into the encoder's padded ION allocation.
// Sixteen RGBA pixels at a time, no temporary full-frame image. Chroma is the
// rounded average of each 2x2 block. Dimensions must be positive and even.
inline uint8x16_t rgba_luma(const uint8x16x4_t &p) {
  auto half = [](uint8x8_t r, uint8x8_t g, uint8x8_t b) {
    uint16x8_t y = vmull_u8(r, vdup_n_u8(66));
    y = vmlal_u8(y, g, vdup_n_u8(129));
    y = vmlal_u8(y, b, vdup_n_u8(25));
    return vadd_u8(vrshrn_n_u16(y, 8), vdup_n_u8(16));
  };
  return vcombine_u8(half(vget_low_u8(p.val[0]), vget_low_u8(p.val[1]), vget_low_u8(p.val[2])),
                     half(vget_high_u8(p.val[0]), vget_high_u8(p.val[1]), vget_high_u8(p.val[2])));
}

inline void rgba_to_nv12(const uint8_t *rgba, uint8_t *output, int width, int height, int stride, size_t uv_offset) {
  for (int row = 0; row < height; row += 2) {
    const uint8_t *top = rgba + size_t(row) * width * 4, *bottom = top + width * 4;
    uint8_t *y0 = output + row * stride, *y1 = y0 + stride;
    uint8_t *uv = output + uv_offset + (row / 2) * stride;
    int x = 0;
    for (; x + 16 <= width; x += 16) {
      auto a = vld4q_u8(top + x * 4), b = vld4q_u8(bottom + x * 4);
      vst1q_u8(y0 + x, rgba_luma(a));
      vst1q_u8(y1 + x, rgba_luma(b));
      auto average = [](uint8x16_t a, uint8x16_t b) {
        return vreinterpretq_s16_u16(vrshrq_n_u16(vaddq_u16(vpaddlq_u8(a), vpaddlq_u8(b)), 2));
      };
      auto r = average(a.val[0], b.val[0]), g = average(a.val[1], b.val[1]), blue = average(a.val[2], b.val[2]);
      auto u = vmlaq_n_s16(vmlaq_n_s16(vmulq_n_s16(r, -38), g, -74), blue, 112);
      auto v = vmlaq_n_s16(vmlaq_n_s16(vmulq_n_s16(r, 112), g, -94), blue, -18);
      uint8x8x2_t chroma = {{vmovn_u16(vreinterpretq_u16_s16(vaddq_s16(vrshrq_n_s16(u, 8), vdupq_n_s16(128)))),
                            vmovn_u16(vreinterpretq_u16_s16(vaddq_s16(vrshrq_n_s16(v, 8), vdupq_n_s16(128))))}};
      vst2_u8(uv + x, chroma);
    }
    for (; x < width; x += 2) {
      int r = 0, g = 0, b = 0;
      for (int dy = 0; dy < 2; ++dy) {
        for (int dx = 0; dx < 2; ++dx) {
          const auto *p = (dy ? bottom : top) + (x + dx) * 4;
          (dy ? y1 : y0)[x + dx] = ((66 * p[0] + 129 * p[1] + 25 * p[2] + 128) >> 8) + 16;
          r += p[0]; g += p[1]; b += p[2];
        }
      }
      r = (r + 2) / 4; g = (g + 2) / 4; b = (b + 2) / 4;
      uv[x] = ((-38 * r - 74 * g + 112 * b + 128) >> 8) + 128;
      uv[x + 1] = ((112 * r - 94 * g - 18 * b + 128) >> 8) + 128;
    }
  }
}
