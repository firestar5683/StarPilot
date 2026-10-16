// Linux LP64 regression for the production V4LDecoder linked from replay_lib.
// Only this executable wraps the device syscalls and VisionBuf allocation/free.
#include "common/tests/native_test.h"
#include "system/loggerd/encoder/v4l_decoder.h"
#include "tools/replay/framereader.h"

#include <cerrno>
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <map>
#include <new>
#include <string>
#include <sys/ioctl.h>
#include <unistd.h>
#include <vector>

static_assert(sizeof(size_t) == 8, "The wrapped allocate symbol requires Linux LP64");

namespace {
constexpr char TEST_DEVICE[] = "/dev/replay-v4l-lifecycle-test";
constexpr int NONZERO_DEVICE_FD = 1000001;  // Never passed to the real kernel.
enum class Failure { none, open_device, output_format, capture_format, capture_queue, output_queue };

struct Fixture {
  static Fixture *current;
  int video_fd = NONZERO_DEVICE_FD;
  Failure failure = Failure::none;
  bool opened = false;
  bool allow_decoder_device = false, track_packet_unrefs = false;
  int open_attempts = 0, closes = 0, allocations = 0, frees = 0;
  int output_formats = 0, capture_formats = 0, capture_queries = 0;
  int capture_queue_failures = 0, output_queue_failures = 0, packet_buffer_unrefs = 0;
  std::map<VisionBuf *, void *> live;
  std::vector<std::string> errors;

  Fixture() { current = this; }
  ~Fixture() {
    // Test-owned backing memory is reclaimed even when a regression fails.
    // Assertions inspect live/frees before this emergency harness cleanup.
    for (auto [buffer, memory] : live) { (void)buffer; std::free(memory); }
    current = nullptr;
  }
  void check_clean(int expected_allocations, int expected_closes) const {
    CHECK(errors.empty());
    CHECK(!opened);
    CHECK(live.empty());
    CHECK(allocations == expected_allocations);
    CHECK(frees == expected_allocations);
    CHECK(closes == expected_closes);
  }
};
Fixture *Fixture::current = nullptr;
int decoder_opens = 0;

void complete_format(v4l2_format *format) {
  auto &pixel = format->fmt.pix_mp;
  pixel.num_planes = 1;
  pixel.plane_fmt[0].bytesperline = pixel.width;
  pixel.plane_fmt[0].sizeimage = format->type == V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE ?
    4096 : pixel.width * pixel.height * 3 / 2;
}
}  // namespace

extern "C" int __real_open(const char *, int, ...);
extern "C" int __real_close(int);
extern "C" int __real_ioctl(int, unsigned long, ...);
extern "C" void __real__ZN9VisionBuf8allocateEm(VisionBuf *, size_t);
extern "C" int __real__ZN9VisionBuf4freeEv(VisionBuf *);
extern "C" void __real_av_packet_unref(AVPacket *);

extern "C" void __wrap_av_packet_unref(AVPacket *packet) {
  auto *fixture = Fixture::current;
  if (fixture && fixture->track_packet_unrefs && packet && packet->buf) ++fixture->packet_buffer_unrefs;
  __real_av_packet_unref(packet);
}

extern "C" int __wrap_open(const char *path, int flags, ...) {
  if (std::strcmp(path, V4LDecoder::DEVICE) == 0) ++decoder_opens;
  mode_t mode = 0;
  bool needs_mode = (flags & O_CREAT) != 0;
#ifdef O_TMPFILE
  needs_mode = needs_mode || (flags & O_TMPFILE) == O_TMPFILE;
#endif
  if (needs_mode) {
    va_list arguments;
    va_start(arguments, flags);
    mode = static_cast<mode_t>(va_arg(arguments, int));
    va_end(arguments);
  }
  auto *fixture = Fixture::current;
  if (fixture && (std::strcmp(path, TEST_DEVICE) == 0 ||
                  (fixture->allow_decoder_device && std::strcmp(path, V4LDecoder::DEVICE) == 0))) {
    ++fixture->open_attempts;
    if (fixture->failure == Failure::open_device) { errno = ENOENT; return -1; }
    if (fixture->opened) fixture->errors.emplace_back("device opened twice without close");
    fixture->opened = true;
    return fixture->video_fd;
  }
  return __real_open(path, flags, mode);
}

extern "C" int __wrap_close(int fd) {
  auto *fixture = Fixture::current;
  if (fixture && fd == fixture->video_fd) {
    if (!fixture->opened) fixture->errors.emplace_back("close of unopened/already closed device");
    fixture->opened = false;
    ++fixture->closes;
    return 0;
  }
  return __real_close(fd);
}

extern "C" int __wrap_ioctl(int fd, unsigned long request, ...) {
  va_list arguments;
  va_start(arguments, request);
  void *argument = va_arg(arguments, void *);
  va_end(arguments);
  auto *fixture = Fixture::current;
  if (!fixture || fd != fixture->video_fd) return __real_ioctl(fd, request, argument);
  if (!fixture->opened) {
    fixture->errors.emplace_back("ioctl after device close");
    errno = EBADF;
    return -1;
  }
  switch (request) {
    case VIDIOC_S_FMT: {
      auto *format = static_cast<v4l2_format *>(argument);
      const bool output = format->type == V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
      if (output) ++fixture->output_formats;
      else ++fixture->capture_formats;
      if ((output && fixture->failure == Failure::output_format) ||
          (!output && fixture->failure == Failure::capture_format)) { errno = EINVAL; return -1; }
      complete_format(format);
      return 0;
    }
    case VIDIOC_G_FMT:
      ++fixture->capture_queries;
      complete_format(static_cast<v4l2_format *>(argument));
      return 0;
    case VIDIOC_QBUF: {
      const auto *buffer = static_cast<v4l2_buffer *>(argument);
      if (buffer->type == V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE && fixture->failure == Failure::capture_queue) {
        ++fixture->capture_queue_failures;
        errno = EIO;
        return -1;
      }
      if (buffer->type == V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE && fixture->failure == Failure::output_queue) {
        ++fixture->output_queue_failures;
        fixture->track_packet_unrefs = true;  // Exclude any static-FFmpeg demux housekeeping.
        errno = EIO;
        return -1;
      }
      return 0;
    }
    case VIDIOC_SUBSCRIBE_EVENT:
    case VIDIOC_REQBUFS:
    case VIDIOC_S_PARM:
    case VIDIOC_S_CTRL:
    case VIDIOC_S_EXT_CTRLS:
    case VIDIOC_STREAMON:
    case VIDIOC_STREAMOFF:
    case VIDIOC_DECODER_CMD:
      return 0;
    default:
      fixture->errors.emplace_back("unhandled fake decoder ioctl");
      errno = ENOTTY;
      return -1;
  }
}

extern "C" void __wrap__ZN9VisionBuf8allocateEm(VisionBuf *buffer, size_t length) {
  auto *fixture = Fixture::current;
  if (!fixture) { __real__ZN9VisionBuf8allocateEm(buffer, length); return; }
  if (!fixture->opened) fixture->errors.emplace_back("allocation without open device");
  if (fixture->live.count(buffer)) {
    fixture->errors.emplace_back("allocation overwrote a live buffer");
    return;
  }
  void *memory = std::calloc(1, length + sizeof(uint64_t));
  if (!memory) throw std::bad_alloc();
  buffer->addr = memory;
  buffer->len = length;
  buffer->mmap_len = length + sizeof(uint64_t);
  buffer->frame_id = reinterpret_cast<uint64_t *>(static_cast<uint8_t *>(memory) + length);
  buffer->fd = -10000 - fixture->allocations;  // No real DMA descriptor exists.
  buffer->handle = 10000 + fixture->allocations;
  fixture->live.emplace(buffer, memory);
  ++fixture->allocations;
}

extern "C" int __wrap__ZN9VisionBuf4freeEv(VisionBuf *buffer) {
  auto *fixture = Fixture::current;
  if (!fixture) return __real__ZN9VisionBuf4freeEv(buffer);
  if (fixture->opened) fixture->errors.emplace_back("owned buffer freed before device close");
  auto found = fixture->live.find(buffer);
  if (found == fixture->live.end()) {
    fixture->errors.emplace_back("unallocated/double-freed buffer");
    errno = EINVAL;
    return -1;
  }
  std::free(found->second);
  fixture->live.erase(found);
  ++fixture->frees;
  // Match production VisionBuf::free(): it does NOT clear pointer/fd fields.
  return 0;
}

namespace {
void test_uninitialized_destructor() {
  Fixture fixture;
  fixture.video_fd = 0;
  { V4LDecoder decoder; }
  CHECK(fixture.open_attempts == 0);
  fixture.check_clean(0, 0);
}

void test_repeated_init_and_destruction() {
  Fixture fixture;
  for (int cycle = 0; cycle < 32; ++cycle) {
    fixture.video_fd = cycle % 2 ? NONZERO_DEVICE_FD : 0;
    {
      V4LDecoder decoder;
      REQUIRE(decoder.init(TEST_DEVICE, 128, 72, V4L2_PIX_FMT_HEVC));
      CHECK(decoder.fd == fixture.video_fd);
      CHECK(fixture.live.size() == OUTPUT_BUFFER_COUNT + CAPTURE_BUFFER_COUNT);
      CHECK(fixture.allocations == (cycle + 1) * 24);
    }
    fixture.check_clean((cycle + 1) * 24, cycle + 1);
  }
  CHECK(fixture.open_attempts == 32);
  CHECK(fixture.output_formats == 32);
  CHECK(fixture.capture_formats == 32);
  CHECK(fixture.capture_queries == 32);
}

void test_open_failure_does_not_close_stdin() {
  Fixture fixture;
  fixture.video_fd = 0;
  fixture.failure = Failure::open_device;
  {
    V4LDecoder decoder;
    REQUIRE(!decoder.init(TEST_DEVICE, 128, 72, V4L2_PIX_FMT_HEVC));
    CHECK(decoder.fd == -1);
    fixture.check_clean(0, 0);
  }
  CHECK(fixture.open_attempts == 1);
  fixture.check_clean(0, 0);
}

void test_format_failure_cleans_partial_init(Failure failure, int allocated) {
  Fixture fixture;
  fixture.video_fd = failure == Failure::capture_format ? 0 : NONZERO_DEVICE_FD;
  fixture.failure = failure;
  {
    V4LDecoder decoder;
    // Init failure is a recoverable false return, never an escaping ioctl exception.
    REQUIRE(!decoder.init(TEST_DEVICE, 128, 72, V4L2_PIX_FMT_HEVC));
    CHECK(decoder.fd == -1);
    fixture.check_clean(allocated, 1);  // Cleanup must occur before returning false.
  }
  fixture.check_clean(allocated, 1);  // Destructor must not repeat close/free.
  CHECK(fixture.open_attempts == 1);
  CHECK(fixture.output_formats == 1);
  CHECK(fixture.capture_formats == (failure == Failure::capture_format ? 1 : 0));
  CHECK(fixture.capture_queries == 0);
}

void test_capture_queue_failure_cleans_all_buffers() {
  Fixture fixture;
  fixture.video_fd = 0;
  fixture.failure = Failure::capture_queue;
  {
    V4LDecoder decoder;
    REQUIRE(!decoder.init(TEST_DEVICE, 128, 72, V4L2_PIX_FMT_HEVC));
    CHECK(decoder.fd == -1);
    CHECK(fixture.capture_queue_failures == 1);
    fixture.check_clean(24, 1);
  }
  fixture.check_clean(24, 1);
}

void test_same_object_reinitializes_after_success_and_failure() {
  Fixture fixture;
  {
    V4LDecoder decoder;
    REQUIRE(decoder.init(TEST_DEVICE, 128, 72, V4L2_PIX_FMT_HEVC));
    REQUIRE(decoder.init(TEST_DEVICE, 128, 72, V4L2_PIX_FMT_HEVC));
    CHECK(fixture.allocations == 48 && fixture.frees == 24 && fixture.closes == 1);
    fixture.failure = Failure::capture_queue;
    REQUIRE(!decoder.init(TEST_DEVICE, 128, 72, V4L2_PIX_FMT_HEVC));
    fixture.check_clean(72, 3);
    fixture.failure = Failure::none;
    REQUIRE(decoder.init(TEST_DEVICE, 128, 72, V4L2_PIX_FMT_HEVC));
    CHECK(fixture.live.size() == 24);
  }
  CHECK(fixture.open_attempts == 4);
  fixture.check_clean(96, 4);
}

struct RawVideoFile {
  char path[48] = "/tmp/replay-v4l-packet-XXXXXX";
  int fd = -1;
  RawVideoFile() {
    fd = mkstemp(path);
    REQUIRE(fd >= 0);
  }
  ~RawVideoFile() { if (fd >= 0) close(fd); unlink(path); }
};

void test_frame_reader_ioctl_exception_releases_packet() {
  RawVideoFile file;
  const uint8_t pixels[6] = {30, 40, 50, 60, 128, 128};
  REQUIRE(write(file.fd, pixels, sizeof(pixels)) == static_cast<ssize_t>(sizeof(pixels)));
  Fixture fixture;
  fixture.allow_decoder_device = true;  // Only this case may intercept the production path.
  {
    FrameReader reader;
    AVDictionary *options = nullptr;
    av_dict_set(&options, "video_size", "2x2", 0);
    av_dict_set(&options, "pixel_format", "yuv420p", 0);
    av_dict_set(&options, "framerate", "20", 0);
    const int opened = avformat_open_input(&reader.input_ctx, file.path, av_find_input_format("rawvideo"), &options);
    av_dict_free(&options);
    REQUIRE(opened == 0);
    REQUIRE(reader.input_ctx->nb_streams == 1);
    reader.video_stream_idx_ = 0;
    reader.width = reader.height = 2;
    reader.packets_info.push_back({AV_PKT_FLAG_KEY, 0});
    const auto free_parameters = [](AVCodecParameters *parameters) { avcodec_parameters_free(&parameters); };
    std::unique_ptr<AVCodecParameters, decltype(free_parameters)> parameters(avcodec_parameters_alloc(), free_parameters);
    REQUIRE(parameters != nullptr);
    REQUIRE(avcodec_parameters_copy(parameters.get(), reader.input_ctx->streams[0]->codecpar) == 0);
    parameters->codec_id = AV_CODEC_ID_HEVC;  // Keep the actual demuxer's parameters rawvideo.
    parameters->width = parameters->height = 2;
    reader.decoder_ = std::make_shared<V4LVideoDecoder>();
    REQUIRE(reader.decoder_->open(parameters.get(), true));
    CHECK(fixture.live.size() == 24);
    uint8_t output[6] = {};
    VisionBuf buffer;
    buffer.width = buffer.height = buffer.stride = 2;
    buffer.y = output;
    buffer.uv = output + 4;
    fixture.failure = Failure::output_queue;
    const bool decoded = reader.get(0, &buffer);
    fixture.track_packet_unrefs = false;
    CHECK(!decoded);
    CHECK(fixture.output_queue_failures == 1);
    CHECK(fixture.packet_buffer_unrefs == 1);
    CHECK(reader.decoder_->active_reader_ == nullptr);
  }
  fixture.check_clean(24, 1);
}

// Hardware test: two consecutive HEVC segments.
void test_evicted_reader_handoff(const char *first, const char *second) {
  auto previous = std::make_unique<FrameReader>();
  REQUIRE(previous->loadFromFile(NarrowRoadCam, first, false));
  REQUIRE(dynamic_cast<V4LVideoDecoder *>(previous->decoder_.get()) != nullptr);
  REQUIRE(previous->getFrameCount() > 2);
  std::vector<uint8_t> pixels(previous->width * previous->height * 3 / 2);
  VisionBuf buffer;
  buffer.width = buffer.stride = previous->width;
  buffer.height = previous->height;
  buffer.y = pixels.data();
  buffer.uv = pixels.data() + buffer.width * buffer.height;
  REQUIRE(previous->get(previous->getFrameCount() - 1, &buffer));
  auto decoder = previous->decoder_;
  previous.reset();
  CHECK(decoder->active_reader_ == nullptr);

  auto next = std::make_unique<FrameReader>();
  REQUIRE(next->loadFromFile(NarrowRoadCam, second, false));
  REQUIRE(next->decoder_ == decoder);
  REQUIRE(next->getFrameCount() > 2);
  int before = decoder_opens;
  REQUIRE(next->get(0, &buffer));
  CHECK(decoder_opens == before);
  const auto first_pixels = pixels;

  REQUIRE(next->get(1, &buffer));
  before = decoder_opens;
  REQUIRE(next->get(0, &buffer));
  CHECK(decoder_opens == before + 1);
  CHECK(pixels == first_pixels);

  REQUIRE(next->get(1, &buffer));
  next.reset();
  FrameReader partial;
  REQUIRE(partial.loadFromFile(NarrowRoadCam, first, false));
  REQUIRE(partial.decoder_ == decoder);
  before = decoder_opens;
  REQUIRE(partial.get(0, &buffer));
  CHECK(decoder_opens == before + 1);
}
}  // namespace

int main(int argc, char **argv) {
  return run_native_test([&] {
    REQUIRE(argc == 1 || argc == 3);
    if (argc == 3) {
      test_evicted_reader_handoff(argv[1], argv[2]);
      return;
    }
    test_uninitialized_destructor();
    test_repeated_init_and_destruction();
    test_open_failure_does_not_close_stdin();
    test_format_failure_cleans_partial_init(Failure::output_format, 0);
    test_format_failure_cleans_partial_init(Failure::capture_format, 8);
    test_capture_queue_failure_cleans_all_buffers();
    test_same_object_reinitializes_after_success_and_failure();
    test_frame_reader_ioctl_exception_releases_packet();
  });
}
