#include "tools/replay/route.h"

#include <array>
#include <filesystem>
#include <regex>
#include <fcntl.h>
#include <sys/file.h>

#include "json11/json11.hpp"
#include "common/hardware/hw.h"
#include "tools/replay/py_downloader.h"
#include "tools/replay/replay.h"
#include "tools/replay/util.h"

Route::Route(const std::string &route, const std::string &data_dir, bool auto_source, bool local_only)
    : data_dir_(data_dir), auto_source_(auto_source), local_only_(local_only), route_string_(route) {}

std::shared_ptr<unique_fd> SegmentFile::openLocal(const std::string &path) const {
  const auto name = std::filesystem::path(path).filename().string();
  auto expected = identities.find(name);
  if (!directory || expected == identities.end()) return nullptr;
  auto fd = std::make_shared<unique_fd>(openat(*directory, name.c_str(), O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK));
  struct stat current = {};
  const auto &original = expected->second;
  if (*fd < 0 || fstat(*fd, &current) || !S_ISREG(current.st_mode)) return nullptr;
#ifdef __APPLE__
  const bool changed_time = current.st_mtimespec.tv_sec != original.st_mtimespec.tv_sec || current.st_mtimespec.tv_nsec != original.st_mtimespec.tv_nsec;
#else
  const bool changed_time = current.st_mtim.tv_sec != original.st_mtim.tv_sec || current.st_mtim.tv_nsec != original.st_mtim.tv_nsec;
#endif
  if (current.st_dev != original.st_dev || current.st_ino != original.st_ino || current.st_size != original.st_size ||
      changed_time) return nullptr;
  return fd;
}

RouteIdentifier Route::parseRoute(const std::string &str) {
  RouteIdentifier identifier = {};
  static const std::regex pattern(R"(^(([a-z0-9]{16})[|_/])?(.{20})((--|/)((-?\d+(:(-?\d+)?)?)|(:-?\d+)))?$)");
  std::smatch match;

  if (std::regex_match(str, match, pattern)) {
    identifier.dongle_id = match[2].str();
    identifier.timestamp = match[3].str();
    identifier.str = identifier.dongle_id + "|" + identifier.timestamp;

    const auto separator = match[5].str();
    const auto range_str = match[6].str();
    if (!range_str.empty()) {
      if (separator == "/") {
        const auto pos = range_str.find(':');
        int begin_seg = pos == 0 ? 0 : std::stoi(range_str.substr(0, pos));
        identifier.begin_segment = identifier.end_segment = begin_seg;
        if (pos != std::string::npos) {
          auto end_seg_str = range_str.substr(pos + 1);
          identifier.end_segment = end_seg_str.empty() ? -1 : std::stoi(end_seg_str);
        }
      } else if (separator == "--") {
        identifier.begin_segment = std::atoi(range_str.c_str());
      }
    }
  }
  return identifier;
}

bool Route::load() {
  route_ = parseRoute(route_string_);
  if (route_.str.empty() || (data_dir_.empty() && route_.dongle_id.empty())) {
    rInfo("invalid route format");
    return false;
  }

  // Parse the timestamp from the route identifier (only applicable for old route formats).
  struct tm tm_time = {0};
  if (strptime(route_.timestamp.c_str(), "%Y-%m-%d--%H-%M-%S", &tm_time)) {
    date_time_ = mktime(&tm_time);
  }

  if (!loadSegments()) {
    rInfo("Failed to load segments");
    return false;
  }

  return true;
}

bool Route::loadSegments() {
  if (local_only_ && (data_dir_.empty() || auto_source_)) return false;
  if (!auto_source_) {
    bool ret = data_dir_.empty() ? loadFromServer() : loadFromLocal();
    if (ret) {
      // Trim segments
      if (route_.begin_segment > 0) {
        segments_.erase(segments_.begin(), segments_.lower_bound(route_.begin_segment));
      }
      if (route_.end_segment >= 0) {
        segments_.erase(segments_.upper_bound(route_.end_segment), segments_.end());
      }
    }
    return !segments_.empty();
  }
  return loadFromAutoSource();
}

bool Route::loadFromAutoSource() {
  auto origin_prefix = getenv("OPENPILOT_PREFIX");
  if (origin_prefix) {
    setenv("OPENPILOT_PREFIX", "", 1);
  }
  auto cmd = util::string_format("../auto_source.py \"%s\"", route_string_.c_str());
  auto log_files = split(util::check_output(cmd), '\n');
  if (origin_prefix) {
    setenv("OPENPILOT_PREFIX", origin_prefix, 1);
  }

  const static std::regex rx(R"(\/(\d+)\/)");
  for (int i = 0; i < log_files.size(); ++i) {
    int seg_num = i;
    std::smatch match;
    if (std::regex_search(log_files[i], match, rx)) {
      seg_num = std::stoi(match[1]);
    }
    addFileToSegment(seg_num, log_files[i]);
  }
  return !segments_.empty();
}

bool Route::loadFromServer() {
  std::string result = PyDownloader::getRouteFiles(route_.str);
  if (result.empty()) {
    err_ = RouteLoadError::NetworkError;
    rWarning("Failed to fetch route files from server");
    return false;
  }

  // Check for error field in JSON response
  std::string parse_err;
  auto json = json11::Json::parse(result, parse_err);
  if (!parse_err.empty()) {
    err_ = RouteLoadError::NetworkError;
    rWarning("Failed to parse route files response");
    return false;
  }

  if (json.is_object() && json["error"].is_string()) {
    const std::string &error = json["error"].string_value();
    if (error == "unauthorized") {
      rWarning(">> Unauthorized. Authenticate with openpilot/tools/lib/auth.py <<");
      err_ = RouteLoadError::Unauthorized;
    } else if (error == "not_found") {
      rWarning("The specified route could not be found on the server.");
      err_ = RouteLoadError::FileNotFound;
    } else {
      rWarning("API error: %s", error.c_str());
      err_ = RouteLoadError::NetworkError;
    }
    return false;
  }

  return loadFromJson(json);
}

bool Route::loadFromJson(const json11::Json &json) {
  const static std::regex rx(R"(\/(\d+)\/)");
  for (const auto &value : json.object_items()) {
    const auto &urlArray = value.second.array_items();
    for (const auto &url : urlArray) {
      std::string url_str = url.string_value();
      std::smatch match;
      if (std::regex_search(url_str, match, rx)) {
        addFileToSegment(std::stoi(match[1]), url_str);
      }
    }
  }
  return !segments_.empty();
}

bool Route::loadFromLocal() {
  if (local_only_) {
    auto root = std::make_shared<unique_fd>(open(data_dir_.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    if (*root < 0) return false;
    const std::string prefix = route_.dongle_id.empty() ? route_.timestamp : route_.dongle_id + "|" + route_.timestamp;
    try {
      for (const auto &entry : std::filesystem::directory_iterator(data_dir_)) {
        std::string name = entry.path().filename().string();
        std::replace(name.begin(), name.end(), '_', '|');
        if (name.rfind(prefix + "--", 0) != 0) continue;
        const auto number = name.substr(prefix.size() + 2);
        if (number.empty() || number.size() > 6 || number.find_first_not_of("0123456789") != std::string::npos) return false;
        const int n = std::stoi(number);
        if (n < route_.begin_segment || (route_.end_segment >= 0 && n > route_.end_segment)) continue;
        if (segments_.size() >= 512 || segments_.count(n)) return false;
        auto directory = std::make_shared<unique_fd>(openat(*root, entry.path().filename().c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
        if (*directory < 0 || flock(*directory, LOCK_SH | LOCK_NB)) return false;
        size_t count = 0;
        for (const auto &file : std::filesystem::directory_iterator(entry.path())) {
          const auto filename = file.path().filename().string();
          if (++count > 32 || util::ends_with(filename, ".lock")) return false;
          struct stat info = {};
          if (fstatat(*directory, filename.c_str(), &info, AT_SYMLINK_NOFOLLOW)) return false;
          if (!S_ISREG(info.st_mode)) continue;
          const std::set<std::string> recognized = {"rlog", "rlog.zst", "rlog.bz2", "qlog", "qlog.zst", "qlog.bz2",
                                                   "fcamera.hevc", "dcamera.hevc", "ecamera.hevc", "qcamera.ts"};
          if (!recognized.count(filename)) continue;
          addFileToSegment(n, file.path().string());
          if (segments_.count(n)) {
            if (info.st_size <= 0 || info.st_size > 512LL * 1024 * 1024) return false;
            segments_[n].directory = directory;
            segments_[n].identities[filename] = info;
          }
        }
      }
    } catch (const std::filesystem::filesystem_error &error) {
      rError("Local route changed: %s", error.what());
      return false;
    }
    return !segments_.empty();
  }
  std::string pattern = route_.timestamp + "--";
  for (const auto &entry : std::filesystem::directory_iterator(data_dir_)) {
    if (entry.is_directory() && entry.path().filename().string().find(pattern) != std::string::npos) {
      std::string segment = entry.path().string();
      int seg_num = std::atoi(segment.substr(segment.rfind("--") + 2).c_str());

      for (const auto &file : std::filesystem::directory_iterator(segment)) {
        if (file.is_regular_file()) {
          addFileToSegment(seg_num, file.path().string());
        }
      }
    }
  }
  return !segments_.empty();
}

void Route::addFileToSegment(int n, const std::string &file) {
  std::string name = extractFileName(file);
  auto pos = name.find_last_of("--");
  name = pos != std::string::npos ? name.substr(pos + 2) : name;

  if (name == "rlog.bz2" || name == "rlog.zst" || name == "rlog") {
    segments_[n].rlog = file;
  } else if (name == "qlog.bz2" || name == "qlog.zst" || name == "qlog") {
    segments_[n].qlog = file;
  } else if (name == "fcamera.hevc") {
    segments_[n].narrow_road_cam = file;
  } else if (name == "dcamera.hevc") {
    segments_[n].cabin_cam = file;
  } else if (name == "ecamera.hevc") {
    segments_[n].wide_road_cam = file;
  } else if (name == "qcamera.ts") {
    segments_[n].qcamera = file;
  }
}

// class Segment

Segment::Segment(int n, const SegmentFile &files, uint32_t flags, const std::vector<bool> &filters,
                 std::function<void(int, bool)> callback, int64_t boot_offset)
    : seg_num(n), flags(flags), boot_offset_(boot_offset), filters_(filters), on_load_finished_(callback) {
  // [NarrowRoadCam, CabinCam, WideRoadCam, log]. fallback to qcamera/qlog
  const std::array file_list = {
      (flags & REPLAY_FLAG_QCAMERA) || files.narrow_road_cam.empty() ? files.qcamera : files.narrow_road_cam,
      flags & REPLAY_FLAG_CABIN_CAMERA ? files.cabin_cam : "",
      flags & REPLAY_FLAG_WIDE_ROAD ? files.wide_road_cam : "",
      files.rlog.empty() ? files.qlog : files.rlog,
  };
  std::vector<std::pair<int, std::string>> jobs;
  for (int i = 0; i < file_list.size(); ++i) {
    if (!file_list[i].empty() && (!(flags & REPLAY_FLAG_NO_VIPC) || i >= MAX_CAMERAS)) {
      std::string source = file_list[i];
      if (flags & REPLAY_FLAG_LOCAL_MACHINE) {
        auto fd = files.openLocal(source);
        if (!fd) { abort_ = true; continue; }
        source = "/proc/self/fd/" + std::to_string(static_cast<int>(*fd));
        source_fds_.push_back(std::move(fd));
      }
      jobs.emplace_back(i, source);
    }
  }
  loading_ = jobs.size();
  if (jobs.empty()) {
    load_state_ = LoadState::Failed;
  } else {
    for (const auto &[id, source] : jobs) threads_.emplace_back(&Segment::loadFile, this, id, source);
  }
}

Segment::~Segment() {
  {
    std::lock_guard lock(mutex_);
    on_load_finished_ = nullptr;  // Prevent callback after destruction
  }
  abort_ = true;
  for (auto &thread : threads_) {
    if (thread.joinable()) thread.join();
  }
}

void Segment::loadFile(int id, const std::string file) {
  const bool local_cache = !(flags & REPLAY_FLAG_NO_FILE_CACHE);
  bool success = false;
  if (id < MAX_CAMERAS) {
    frames[id] = std::make_unique<FrameReader>();
    success = frames[id]->load((CameraType)id, file, flags & REPLAY_FLAG_NO_HW_DECODER, &abort_, local_cache);
  } else {
    log = std::make_unique<LogReader>(filters_, flags & REPLAY_FLAG_LOCAL_MACHINE ? 128 * 1024 * 1024 : 0, boot_offset_);
    success = log->load(file, &abort_, local_cache);
    if ((flags & REPLAY_FLAG_LOCAL_MACHINE) && log->corrupt()) success = false;
  }

  if (!success) {
    // abort all loading jobs.
    abort_ = true;
  }

  if (--loading_ == 0) {
    std::lock_guard lock(mutex_);
    load_state_ = !abort_ ? LoadState::Loaded : LoadState::Failed;
    if (on_load_finished_) {
      on_load_finished_(seg_num, !abort_);
    }
  }
}

Segment::LoadState Segment::getState() {
  std::scoped_lock lock(mutex_);
  return load_state_;
}
