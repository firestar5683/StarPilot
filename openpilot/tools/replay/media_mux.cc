// Copy composed H.264 into one timestamped fMP4 fragment per frame. No encoder or file owner.
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/opt.h>
}

namespace {
constexpr size_t MAX_BYTES = 1024 * 1024;
void checked(int result, const char *action) {
  if (result >= 0) return;
  char text[AV_ERROR_MAX_STRING_SIZE];
  av_strerror(result, text, sizeof(text));
  throw std::runtime_error(std::string(action) + ": " + text);
}
void error_text(char *out, size_t length, const std::exception &error) {
  if (length) snprintf(out, length, "%s", error.what());
}

// Keep SPS/PPS only: the first keyframe is a packet, not codec initialization data.
std::vector<uint8_t> headers(const uint8_t *data, size_t size) {
  std::vector<uint8_t> out;
  auto start = [&](size_t at) -> size_t {
    if (at + 3 <= size && data[at] == 0 && data[at + 1] == 0 && data[at + 2] == 1) return 3;
    if (at + 4 <= size && data[at] == 0 && data[at + 1] == 0 && data[at + 2] == 0 && data[at + 3] == 1) return 4;
    return 0;
  };
  bool sps = false, pps = false;
  for (size_t at = 0; at < size;) {
    size_t prefix = start(at);
    if (!prefix) { ++at; continue; }
    size_t end = at + prefix;
    while (end < size && !start(end)) ++end;
    if (at + prefix < end) {
      unsigned type = data[at + prefix] & 31;
      if (type == 7 || type == 8) {
        sps |= type == 7; pps |= type == 8;
        out.insert(out.end(), data + at, data + end);
      }
    }
    at = end;
  }
  if (!sps || !pps || out.size() > 65536) throw std::runtime_error("Keyframe lacks bounded H264 SPS/PPS");
  return out;
}

struct Mux {
  AVFormatContext *context = nullptr;
  AVIOContext *io = nullptr;
  AVStream *stream = nullptr;
  std::vector<uint8_t> pending;
  int64_t last_pts = -1;
  ~Mux() {
    if (context) avformat_free_context(context);
    if (io) { av_freep(&io->buffer); avio_context_free(&io); }
  }
  static int write(void *opaque, const uint8_t *data, int size) {
    auto &pending = static_cast<Mux *>(opaque)->pending;
    if (size < 0 || pending.size() + size > MAX_BYTES) return AVERROR(ENOSPC);
    pending.insert(pending.end(), data, data + size);
    return size;
  }
  void initialize(int width, int height, const uint8_t *data, size_t size) {
    if (width <= 0 || width > 1280 || height <= 0 || height > 720 || width % 2 || height % 2 || size > MAX_BYTES)
      throw std::runtime_error("Unsupported replay media geometry");
    checked(avformat_alloc_output_context2(&context, nullptr, "mp4", nullptr), "allocate MP4 muxer");
    auto *buffer = static_cast<unsigned char *>(av_malloc(8192));
    if (!buffer) throw std::bad_alloc();
    io = avio_alloc_context(buffer, 8192, 1, this, nullptr, write, nullptr);
    if (!io) { av_free(buffer); throw std::bad_alloc(); }
    context->pb = io;
    context->flags |= AVFMT_FLAG_CUSTOM_IO;
    stream = avformat_new_stream(context, nullptr);
    if (!stream) throw std::bad_alloc();
    stream->time_base = AVRational{1, 1000000};
    auto *codec = stream->codecpar;
    codec->codec_type = AVMEDIA_TYPE_VIDEO;
    codec->codec_id = AV_CODEC_ID_H264;
    codec->width = width; codec->height = height;
    codec->format = AV_PIX_FMT_YUV420P;
    auto extra = headers(data, size);
    codec->extradata = static_cast<unsigned char *>(av_mallocz(extra.size() + AV_INPUT_BUFFER_PADDING_SIZE));
    if (!codec->extradata) throw std::bad_alloc();
    codec->extradata_size = extra.size();
    memcpy(codec->extradata, extra.data(), extra.size());
    AVDictionary *options = nullptr;
    av_dict_set(&options, "movflags", "empty_moov+default_base_moof+frag_custom+skip_trailer", 0);
    int result = avformat_write_header(context, &options);
    av_dict_free(&options);
    checked(result, "write MP4 initialization");
    avio_flush(io);
    checked(io->error, "flush MP4 initialization");
  }
  int take(uint8_t *out, size_t capacity) {
    if (!out || pending.size() > capacity) throw std::runtime_error("Replay fragment exceeds output capacity");
    int size = pending.size();
    memcpy(out, pending.data(), size);
    pending.clear();
    return size;
  }
  int frame(const uint8_t *data, size_t size, int64_t pts, int64_t duration, bool keyframe, uint8_t *out, size_t capacity) {
    if (!data || !size || size > MAX_BYTES || pts < 0 || pts <= last_pts || duration <= 0 || duration > 1000000 || !pending.empty())
      throw std::runtime_error("Invalid replay media packet or clock");
    auto packet = std::unique_ptr<AVPacket, void(*)(AVPacket *)>(av_packet_alloc(), [](AVPacket *p) { av_packet_free(&p); });
    if (!packet) throw std::bad_alloc();
    checked(av_new_packet(packet.get(), size), "allocate replay packet");
    memcpy(packet->data, data, size);
    packet->stream_index = stream->index;
    packet->pts = packet->dts = av_rescale_q(pts, AVRational{1, 1000000}, stream->time_base);
    packet->duration = av_rescale_q(duration, AVRational{1, 1000000}, stream->time_base);
    packet->flags = keyframe ? AV_PKT_FLAG_KEY : 0;
    // Preserve the caller's exact DTS at each fragment rather than allowing
    // movenc to infer the next tfdt from the previous sample duration.
    checked(av_opt_set(context->priv_data, "movflags", "+frag_discont", 0), "set replay fragment clock");
    checked(av_write_frame(context, packet.get()), "mux replay frame");
    checked(av_write_frame(context, nullptr), "flush replay fragment");
    avio_flush(io);
    checked(io->error, "write replay fragment");
    last_pts = pts;
    return take(out, capacity);
  }
};
}

extern "C" {
void *replay_mux_create(int width, int height, const uint8_t *first, size_t size, char *error, size_t length) {
  try {
    auto mux = std::make_unique<Mux>();
    mux->initialize(width, height, first, size);
    return mux.release();
  } catch (const std::exception &e) { error_text(error, length, e); return nullptr; }
}
int replay_mux_init(void *handle, uint8_t *out, size_t capacity, char *error, size_t length) {
  try {
    if (!handle) throw std::runtime_error("Replay muxer closed");
    return static_cast<Mux *>(handle)->take(out, capacity);
  } catch (const std::exception &e) { error_text(error, length, e); return -1; }
}
int replay_mux_frame(void *handle, const uint8_t *data, size_t size, int64_t pts, int64_t duration, int keyframe,
                     uint8_t *out, size_t capacity, char *error, size_t length) {
  try {
    if (!handle) throw std::runtime_error("Replay muxer closed");
    return static_cast<Mux *>(handle)->frame(data, size, pts, duration, keyframe, out, capacity);
  } catch (const std::exception &e) { error_text(error, length, e); return -1; }
}
void replay_mux_close(void *handle) { delete static_cast<Mux *>(handle); }
}
