#pragma once
#include <algorithm>
#include <vector>

inline bool startup_cache_ready(const std::vector<int> &route, const std::vector<int> &loaded,
                                int current, int cache_limit) {
  auto cur = std::lower_bound(route.begin(), route.end(), current);
  if (cur == route.end() || *cur != current || cache_limit <= 0) return false;
  auto begin = cur - std::min<int>(cache_limit / 2, cur - route.begin());
  auto end = begin + std::min<int>(cache_limit, route.end() - begin);
  begin = end - std::min<int>(cache_limit, end - route.begin());
  return std::all_of(begin, end, [&](int segment) {
    return std::binary_search(loaded.begin(), loaded.end(), segment);
  });
}
