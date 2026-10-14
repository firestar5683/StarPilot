#pragma once

#include <chrono>
#include <condition_variable>
#include <map>
#include <mutex>
#include <set>
#include <vector>

#include "tools/replay/route.h"

constexpr int MIN_SEGMENTS_CACHE = 5;
constexpr int MAX_SEGMENT_LOAD_ATTEMPTS = 3;  // Includes the initial load.

using SegmentMap = std::map<int, std::shared_ptr<Segment>>;

class SegmentManager {
public:
  struct EventData {
    std::vector<Event> events;  //  Events extracted from the segments
    SegmentMap segments;        // Associated segments that contributed to these events
    bool isSegmentLoaded(int n) const { return segments.find(n) != segments.end(); }
  };

  SegmentManager(const std::string &route_name, uint32_t flags, const std::string &data_dir = "", bool auto_source = false)
      : route_(route_name, data_dir, auto_source, flags & LOCAL_MACHINE_FLAG), flags_(flags), event_data_(std::make_shared<EventData>()) {
    if (flags & LOCAL_MACHINE_FLAG) segment_cache_limit_ = 2;
  }
  ~SegmentManager();
  void stop();

  bool load();
  void setCurrentSegment(int seg_num, bool seeking = false);
  int previousSegment(int seg_num) const {
    auto it = segments_.lower_bound(seg_num);
    return it == segments_.begin() ? -1 : std::prev(it)->first;
  }
  void setPlayable(const std::set<int> &numbers, int64_t boot_offset) {
    std::lock_guard lock(mutex_);
    for (auto it = segments_.begin(); it != segments_.end();) {
      if (!numbers.count(it->first)) it = segments_.erase(it); else ++it;
    }
    boot_offset_ = boot_offset;
  }
  void setCallback(const std::function<void()> &callback) { onSegmentMergedCallback_ = callback; }
  void setBenchmarkCallback(const std::function<void(int, const std::string&)> &callback) { onBenchmarkEvent_ = callback; }
  void setFailureCallback(const std::function<void(int)> &callback) { onFailure_ = callback; }
  void setFilters(const std::vector<bool> &filters) { filters_ = filters; }
  const std::shared_ptr<EventData> getEventData() const { return std::atomic_load(&event_data_); }
  bool hasSegment(int n) const { return segments_.find(n) != segments_.end(); }

  Route route_;
  int segment_cache_limit_ = MIN_SEGMENTS_CACHE;

private:
  void manageSegmentCache();
  void loadSegmentsInRange(SegmentMap::iterator begin, SegmentMap::iterator cur, SegmentMap::iterator end);
  bool mergeSegments(const SegmentMap::iterator &begin, const SegmentMap::iterator &end);

  std::vector<bool> filters_;
  uint32_t flags_;

  std::mutex mutex_;
  std::condition_variable cv_;
  std::thread thread_;
  int cur_seg_num_ = -1;
  bool prefer_previous_ = false;
  int64_t boot_offset_ = -1;
  bool needs_update_ = false;
  bool exit_ = false;

  SegmentMap segments_;
  std::shared_ptr<EventData> event_data_;
  std::function<void()> onSegmentMergedCallback_ = nullptr;
  std::function<void(int, const std::string&)> onBenchmarkEvent_ = nullptr;
  std::function<void(int)> onFailure_ = nullptr;
  std::set<int> merged_segments_;
  struct LoadAttempt {
    int count = 0;
    std::chrono::steady_clock::time_point retry_at = std::chrono::steady_clock::time_point::max();
  };
  // Accessed only by the cache management thread.
  std::map<int, LoadAttempt> load_attempts_;
  std::chrono::steady_clock::time_point next_retry_ = std::chrono::steady_clock::time_point::max();
};
