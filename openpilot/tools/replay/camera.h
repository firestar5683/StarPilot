#pragma once

#include <memory>
#include <set>
#include <tuple>
#include <utility>

#include "openpilot/cereal/visionstream.h"
#include "msgq/visionipc/visionipc_server.h"
#include "common/queue.h"
#include "tools/replay/framereader.h"
#include "tools/replay/logreader.h"

class CameraServer {
public:
  CameraServer(std::pair<int, int> camera_size[MAX_CAMERAS] = nullptr, int buffer_count = 40);
  ~CameraServer();
  void pushFrame(CameraType type, FrameReader* fr, const Event *event);
  bool waitForSent();
  bool failed() const { return failed_; }

protected:
  struct Camera {
    CameraType type;
    VisionStreamType stream_type;
    int width;
    int height;
    std::thread thread;
    SafeQueue<std::pair<FrameReader*, const Event *>> queue;
    std::set<VisionBuf *> cached_buf;
  };
  void startVipcServer();
  void cameraThread(Camera &cam);
  VisionBuf *getFrame(Camera &cam, FrameReader *fr, int32_t segment_id, uint32_t frame_id);

  Camera cameras_[MAX_CAMERAS] = {
      {.type = NarrowRoadCam, .stream_type = VISION_STREAM_NARROW_ROAD},
      {.type = CabinCam, .stream_type = VISION_STREAM_CABIN},
      {.type = WideRoadCam, .stream_type = VISION_STREAM_WIDE_ROAD},
  };
  std::atomic<int> publishing_ = 0;
  std::atomic<bool> failed_ = false;
  std::mutex sent_mutex_;
  std::condition_variable sent_cv_;
  const int buffer_count_;
  std::unique_ptr<VisionIpcServer> vipc_server_;
};
