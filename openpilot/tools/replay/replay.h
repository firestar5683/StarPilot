#pragma once

#include <algorithm>
#include <functional>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

#include "tools/replay/camera.h"
#include "tools/replay/display_clock.h"
#include "tools/replay/seg_mgr.h"
#include "tools/replay/timeline.h"

#define DEMO_ROUTE "5beb9b58bd12b691/0000010a--a51155e496"

enum REPLAY_FLAGS {
  REPLAY_FLAG_NONE = 0x0000,
  REPLAY_FLAG_CABIN_CAMERA = 0x0002,
  REPLAY_FLAG_WIDE_ROAD = 0x0004,
  REPLAY_FLAG_NO_LOOP = 0x0010,
  REPLAY_FLAG_NO_FILE_CACHE = 0x0020,
  REPLAY_FLAG_QCAMERA = 0x0040,
  REPLAY_FLAG_NO_HW_DECODER = 0x0100,
  REPLAY_FLAG_NO_VIPC = 0x0400,
  REPLAY_FLAG_ALL_SERVICES = 0x0800,
  REPLAY_FLAG_BENCHMARK = 0x1000,
  REPLAY_FLAG_LOCAL_MACHINE = LOCAL_MACHINE_FLAG,
};

struct BenchmarkStats {
  uint64_t process_start_ts = 0;
  std::vector<std::pair<uint64_t, std::string>> timeline;
};

class Replay {
public:
  Replay(const std::string &route, std::vector<std::string> allow, std::vector<std::string> block, SubMaster *sm = nullptr,
         uint32_t flags = REPLAY_FLAG_NONE, const std::string &data_dir = "", bool auto_source = false);
  ~Replay();
  void stop();
  bool load();
  RouteLoadError lastRouteError() const { return route().lastError(); }
  void start(int seconds = 0) { seekTo(min_seconds_ + seconds, false); }
  void pause(bool pause);
  void seekToFlag(FindFlag flag);
  void seekTo(double seconds, bool relative);
  inline bool isPaused() const { return user_paused_; }
  inline int segmentCacheLimit() const { return seg_mgr_->segment_cache_limit_; }
  inline void setSegmentCacheLimit(int n) { seg_mgr_->segment_cache_limit_ = std::max(hasFlag(REPLAY_FLAG_LOCAL_MACHINE) ? 2 : MIN_SEGMENTS_CACHE, n); }
  inline bool hasFlag(REPLAY_FLAGS flag) const { return flags_ & flag; }
  void setLoop(bool loop) { loop ? flags_ &= ~REPLAY_FLAG_NO_LOOP : flags_ |= REPLAY_FLAG_NO_LOOP; }
  bool loop() const { return !(flags_ & REPLAY_FLAG_NO_LOOP); }
  const Route &route() const { return seg_mgr_->route_; }
  inline double currentSeconds() const {
    const uint64_t now = cur_mono_time_, origin = route_start_ts_;
    return now >= origin ? double(now - origin) / 1e9 : 0.0;
  }
  inline std::time_t routeDateTime() const { return route_date_time_; }
  inline uint64_t routeStartNanos() const { return route_start_ts_; }
  inline double toSeconds(uint64_t mono_time) const { return (mono_time - route_start_ts_) / 1e9; }
  inline double minSeconds() const { return min_seconds_; }
  inline double maxSeconds() const { return max_seconds_; }
  void setSpeed(float speed);
  inline float getSpeed() const { return speed_; }
  inline const std::string &carFingerprint() const { return car_fingerprint_; }
  inline const std::shared_ptr<std::vector<Timeline::Entry>> getTimeline() const { return timeline_.getEntries(); }
  inline const std::optional<Timeline::Entry> findAlertAtTime(double sec) const { return timeline_.findAlertAtTime(sec); }
  const std::shared_ptr<SegmentManager::EventData> getEventData() const { return seg_mgr_->getEventData(); }
  void installEventFilter(std::function<bool(const Event *)> filter) { event_filter_ = filter; }
  void waitForFinished();
  std::string state() const;
  std::string error() const;
  uint64_t epoch() const { return epoch_; }
  uint64_t appliedEpoch() const { return applied_epoch_; }
  bool canSeek(double seconds) const;
  struct SeekRange { int segment; double begin, end; };
  const std::vector<SeekRange> &seekRanges() const { return seek_ranges_; }
  int64_t wallMinusMonoNanos() const { return wall_minus_mono_ns_; }
  bool legacyClock() const { return legacy_clock_; }
  void setLoadAbort(std::atomic<bool> *abort) { load_abort_ = abort; }
  const BenchmarkStats &getBenchmarkStats() const { return benchmark_stats_; }

  // Event callback functions
  std::function<void()> onSegmentsMerged = nullptr;
  std::function<void(double)> onSeeking = nullptr;
  std::function<void(double)> onSeekedTo = nullptr;
  std::function<void(std::shared_ptr<LogReader>)> onQLogLoaded = nullptr;

private:
  void setupServices(const std::vector<std::string> &allow, const std::vector<std::string> &block);
  void setupSegmentManager(bool has_filters);
  void startStream(const std::shared_ptr<Segment> segment);
  void streamThread();
  void handleSegmentMerge();
  void interruptStream(const std::function<bool()>& update_fn);
  std::vector<Event>::const_iterator publishEvents(std::vector<Event>::const_iterator first,
                                                   std::vector<Event>::const_iterator last,
                                                   int &last_processed_segment,
                                                   uint64_t &segment_start_time);
  bool publishMessage(const Event *e);
  void publishFrame(const Event *e);
  void checkSeekProgress();
  bool publishSnapshot();
  void fail(const std::string &message);
  bool loadMachineRoute();
  int segmentAt(double seconds) const;

  std::unique_ptr<SegmentManager> seg_mgr_;
  Timeline timeline_;
  ReplayDisplayClock display_clock_;

  pthread_t stream_thread_id = 0;
  std::thread stream_thread_;
  std::mutex stream_lock_;
  std::atomic<bool> user_paused_ = false;
  std::condition_variable stream_cv_;
  std::atomic<int> current_segment_ = 0;
  std::atomic<double> seeking_to_ = -1.0;
  std::atomic<bool> exit_ = false;
  std::atomic<bool> *load_abort_ = nullptr;
  std::atomic<bool> interrupt_requested_ = false;
  enum class State {Preparing, Paused, Playing, Seeking, Buffering, Ended, Failed};
  std::atomic<State> state_ = State::Preparing;
  std::atomic<uint64_t> epoch_ = 0;
  std::atomic<uint64_t> applied_epoch_ = 0;
  mutable std::mutex error_lock_;
  std::string error_;
  std::vector<SeekRange> seek_ranges_;
  int64_t boot_offset_ns_ = -1;
  bool legacy_clock_ = false;
  std::atomic<int64_t> wall_minus_mono_ns_ = 0;
  bool events_ready_ = false;
  std::time_t route_date_time_ = 0;
  std::atomic<uint64_t> route_start_ts_ = 0;
  std::atomic<uint64_t> cur_mono_time_ = 0;
  cereal::Event::Which cur_which_ = cereal::Event::Which::INIT_DATA;
  std::atomic<double> min_seconds_ = 0;
  std::atomic<double> max_seconds_ = 0;
  SubMaster *sm_ = nullptr;
  std::vector<const char *> active_services_;
  std::unique_ptr<PubMaster> pm_;
  std::vector<const char*> sockets_;
  std::unique_ptr<CameraServer> camera_server_;
  std::atomic<uint32_t> flags_ = REPLAY_FLAG_NONE;

  std::string car_fingerprint_;
  std::atomic<float> speed_ = 1.0;
  std::function<bool(const Event *)> event_filter_ = nullptr;

  std::shared_ptr<SegmentManager::EventData> event_data_ = std::make_shared<SegmentManager::EventData>();

  BenchmarkStats benchmark_stats_;
  std::condition_variable benchmark_cv_;
  std::mutex benchmark_lock_;
  bool benchmark_done_ = false;
};
