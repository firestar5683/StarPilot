#include "tools/replay/framereader.h"

#include <map>
#include <memory>
#include <tuple>
#include <utility>
#include <chrono>

#include "common/util.h"
#include "common/yuv.h"
#include "tools/replay/py_tools.h"
#include "tools/replay/util.h"
#include "common/hardware/hw.h"

#ifdef __APPLE__
#define HW_DEVICE_TYPE AV_HWDEVICE_TYPE_VIDEOTOOLBOX
#define HW_PIX_FMT AV_PIX_FMT_VIDEOTOOLBOX
#else
#define HW_DEVICE_TYPE AV_HWDEVICE_TYPE_CUDA
#define HW_PIX_FMT AV_PIX_FMT_CUDA
#endif

namespace {

enum AVPixelFormat get_hw_format(AVCodecContext *ctx, const enum AVPixelFormat *pix_fmts) {
  enum AVPixelFormat *hw_pix_fmt = reinterpret_cast<enum AVPixelFormat *>(ctx->opaque);
  for (const enum AVPixelFormat *p = pix_fmts; *p != -1; p++) {
    if (*p == *hw_pix_fmt) return *p;
  }
  rWarning("Please run replay with the --no-hw-decoder flag!");
  *hw_pix_fmt = AV_PIX_FMT_NONE;
  return AV_PIX_FMT_YUV420P;
}

struct DecoderManager {
  std::shared_ptr<VideoDecoder> acquire(CameraType type, AVCodecParameters *codecpar, bool hw_decoder) {
    auto key = std::tuple(type, codecpar->width, codecpar->height, codecpar->codec_id, hw_decoder);
    std::unique_lock lock(mutex_);
    for (auto it = decoders_.begin(); it != decoders_.end();) {
      if (it->second.expired()) it = decoders_.erase(it);
      else ++it;
    }
    if (auto it = decoders_.find(key); it != decoders_.end()) {
      if (auto decoder = it->second.lock()) return decoder;
    }

    std::shared_ptr<VideoDecoder> decoder;
    #ifndef __APPLE__
    if (!Hardware::PC() && hw_decoder && codecpar->codec_id == AV_CODEC_ID_HEVC) {
      decoder = std::make_shared<V4LVideoDecoder>();
    } else
    #endif
    {
      decoder = std::make_shared<FFmpegVideoDecoder>();
    }

    if (!decoder->open(codecpar, hw_decoder && (Hardware::PC() || codecpar->codec_id == AV_CODEC_ID_HEVC))) {
      return nullptr;
    }
    decoders_[key] = decoder;
    return decoder;
  }

  std::mutex mutex_;
  std::map<std::tuple<CameraType, int, int, AVCodecID, bool>, std::weak_ptr<VideoDecoder>> decoders_;
};

DecoderManager decoder_manager;

}  // namespace

FrameReader::FrameReader() {
  av_log_set_level(AV_LOG_QUIET);
}

FrameReader::~FrameReader() {
  if (decoder_) {
    std::lock_guard lock(decoder_->lock_);
    if (decoder_->active_reader_ == this) decoder_->active_reader_ = nullptr;
  }
  if (input_ctx) avformat_close_input(&input_ctx);
}

bool FrameReader::load(CameraType type, const std::string &url, bool no_hw_decoder, std::atomic<bool> *abort, bool local_cache) {
  std::string local_file_path;
  if (url.find("https://") == 0 || url.find("http://") == 0) {
    local_file_path = PyTools::download(url, local_cache, abort);
    if (local_file_path.empty()) return false;
  } else {
    local_file_path = url;
  }
  return loadFromFile(type, local_file_path, no_hw_decoder, abort);
}

bool FrameReader::loadFromFile(CameraType type, const std::string &file, bool no_hw_decoder, std::atomic<bool> *abort) {
  abort_ = abort;
  if (avformat_open_input(&input_ctx, file.c_str(), nullptr, nullptr) != 0 ||
      avformat_find_stream_info(input_ctx, nullptr) < 0) {
    rError("Failed to open input file or find video stream");
    return false;
  }
  input_ctx->probesize = 10 * 1024 * 1024;  // 10MB

  video_stream_idx_ = av_find_best_stream(input_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
  if (video_stream_idx_ < 0) {
    rError("No video stream found in file");
    return false;
  }

  auto *codecpar = input_ctx->streams[video_stream_idx_]->codecpar;
  if (getenv("SP_REPLAY_CONTEXT") && (codecpar->width <= 0 || codecpar->height <= 0 ||
      codecpar->width > 2048 || codecpar->height > 1536 || codecpar->width % 2 || codecpar->height % 2)) return false;
  decoder_ = decoder_manager.acquire(type, codecpar, !no_hw_decoder);
  if (!decoder_) {
    return false;
  }
  width = decoder_->width;
  height = decoder_->height;
  if (getenv("SP_REPLAY_CONTEXT") && (width <= 0 || height <= 0 || width > 2048 || height > 1536 || width % 2 || height % 2)) return false;

  AVPacket pkt;
  packets_info.reserve(60 * 20);  // 20fps, one minute
  while (!(abort && *abort) && av_read_frame(input_ctx, &pkt) == 0) {
    if (pkt.stream_index == video_stream_idx_) {
      packets_info.emplace_back(PacketInfo{.flags = pkt.flags, .pos = pkt.pos});
      if (getenv("SP_REPLAY_CONTEXT") && packets_info.size() > 5000) { av_packet_unref(&pkt); return false; }
    }
    av_packet_unref(&pkt);
  }
  avio_seek(input_ctx->pb, 0, SEEK_SET);
  return !packets_info.empty();
}

bool FrameReader::get(int idx, VisionBuf *buf) {
  if (!buf || buf->width != width || buf->height != height || buf->stride < width ||
      (abort_ && *abort_) || idx < 0 || idx >= packets_info.size()) {
    return false;
  }
  std::lock_guard lock(decoder_->lock_);
  return decoder_->decode(this, idx, buf);
}

// class VideoDecoder

FFmpegVideoDecoder::FFmpegVideoDecoder() {
  av_frame_ = av_frame_alloc();
  hw_frame_ = av_frame_alloc();
}

FFmpegVideoDecoder::~FFmpegVideoDecoder() {
  if (hw_device_ctx) av_buffer_unref(&hw_device_ctx);
  if (decoder_ctx) avcodec_free_context(&decoder_ctx);
  av_frame_free(&av_frame_);
  av_frame_free(&hw_frame_);
}

bool FFmpegVideoDecoder::open(AVCodecParameters *codecpar, bool hw_decoder) {
  const AVCodec *decoder = avcodec_find_decoder(codecpar->codec_id);
  if (!decoder) return false;

  decoder_ctx = avcodec_alloc_context3(decoder);
  if (!decoder_ctx || avcodec_parameters_to_context(decoder_ctx, codecpar) != 0) {
    rError("Failed to allocate or initialize codec context");
    return false;
  }
  width = decoder_ctx->width;
  height = decoder_ctx->height;

  if (hw_decoder && !initHardwareDecoder(HW_DEVICE_TYPE)) {
    rWarning("No device with hardware decoder found. fallback to CPU decoding.");
  }

  if (avcodec_open2(decoder_ctx, decoder, nullptr) < 0) {
    rError("Failed to open codec");
    return false;
  }
  return true;
}

bool FFmpegVideoDecoder::initHardwareDecoder(AVHWDeviceType hw_device_type) {
  const AVCodecHWConfig *config = nullptr;
  for (int i = 0; (config = avcodec_get_hw_config(decoder_ctx->codec, i)) != nullptr; i++) {
    if (config->methods & AV_CODEC_HW_CONFIG_METHOD_HW_DEVICE_CTX && config->device_type == hw_device_type) {
      hw_pix_fmt = config->pix_fmt;
      break;
    }
  }
  if (!config) {
    rWarning("Hardware configuration not found");
    return false;
  }

  int ret = av_hwdevice_ctx_create(&hw_device_ctx, hw_device_type, nullptr, nullptr, 0);
  if (ret < 0) {
    hw_pix_fmt = AV_PIX_FMT_NONE;
    rWarning("Failed to create specified HW device %d.", ret);
    return false;
  }

  decoder_ctx->hw_device_ctx = av_buffer_ref(hw_device_ctx);
  decoder_ctx->opaque = &hw_pix_fmt;
  decoder_ctx->get_format = get_hw_format;
  return true;
}

bool FFmpegVideoDecoder::decode(FrameReader *reader, int idx, VisionBuf *buf) {
  int current_idx = idx;
  if (active_reader_ != reader || idx != reader->prev_idx + 1) {
    // seeking to the nearest key frame
    for (int i = idx; i >= 0; --i) {
      if (reader->packets_info[i].flags & AV_PKT_FLAG_KEY) {
        current_idx = i;
        break;
      }
    }

    auto pos = reader->packets_info[current_idx].pos;
    int ret = avformat_seek_file(reader->input_ctx, 0, pos, pos, pos, AVSEEK_FLAG_BYTE);
    if (ret < 0) {
      rError("Failed to seek to byte position %lld: %d", pos, AVERROR(ret));
      return false;
    }
    avcodec_flush_buffers(decoder_ctx);
  }
  reader->prev_idx = idx;
  active_reader_ = reader;

  AVPacket pkt;
  while (!(reader->abort_ && *reader->abort_) && av_read_frame(reader->input_ctx, &pkt) >= 0) {
    // Skip non-video packets
    if (pkt.stream_index != reader->video_stream_idx_) {
      av_packet_unref(&pkt);
      continue;
    }

    AVFrame *frame = decodeFrame(&pkt);
    av_packet_unref(&pkt);
    if (!frame) {
      rError("Failed to decode frame at index %d", current_idx);
      return false;
    }

    if (current_idx++ == idx) {
      return copyBuffer(frame, buf);
    }
  }
  rError("Failed to find frame at index %d", idx);
  return false;
}

AVFrame *FFmpegVideoDecoder::decodeFrame(AVPacket *pkt) {
  int ret = avcodec_send_packet(decoder_ctx, pkt);
  if (ret < 0) {
    rError("Error sending a packet for decoding: %d", ret);
    return nullptr;
  }

  ret = avcodec_receive_frame(decoder_ctx, av_frame_);
  if (ret != 0) {
    rError("avcodec_receive_frame error: %d", ret);
    return nullptr;
  }

  if (av_frame_->format == hw_pix_fmt && av_hwframe_transfer_data(hw_frame_, av_frame_, 0) < 0) {
    rError("error transferring frame data from GPU to CPU");
    return nullptr;
  }
  return (av_frame_->format == hw_pix_fmt) ? hw_frame_ : av_frame_;
}

bool FFmpegVideoDecoder::copyBuffer(AVFrame *f, VisionBuf *buf) {
  if (f->width != width || f->height != height) return false;
  if (hw_pix_fmt == HW_PIX_FMT) {
    for (int i = 0; i < height/2; i++) {
      memcpy(buf->y + (i*2 + 0)*buf->stride, f->data[0] + (i*2 + 0)*f->linesize[0], width);
      memcpy(buf->y + (i*2 + 1)*buf->stride, f->data[0] + (i*2 + 1)*f->linesize[0], width);
      memcpy(buf->uv + i*buf->stride, f->data[1] + i*f->linesize[1], width);
    }
  } else {
    yuv::i420_to_nv12(f->data[0], f->linesize[0],
                      f->data[1], f->linesize[1],
                      f->data[2], f->linesize[2],
                      buf->y, buf->stride,
                      buf->uv, buf->stride,
                      width, height);
  }
  return true;
}

#ifndef __APPLE__
bool V4LVideoDecoder::open(AVCodecParameters *codecpar, bool hw_decoder) {
  if (codecpar->codec_id != AV_CODEC_ID_HEVC) {
    rError("Hardware decoder only supports HEVC codec");
    return false;
  }
  width = codecpar->width;
  height = codecpar->height;
  v4l_decoder = std::make_unique<V4LDecoder>();
  return v4l_decoder->init(V4LDecoder::DEVICE, width, height, V4L2_PIX_FMT_HEVC);
}

bool V4LVideoDecoder::decode(FrameReader *reader, int idx, VisionBuf *buf) {
  int from_idx = idx;
  const bool reset = active_reader_ != reader || idx != reader->prev_idx + 1;
  const bool next_segment = active_reader_ && active_reader_ != reader && idx == 0 &&
                            size_t(active_reader_->prev_idx + 1) == active_reader_->getFrameCount() &&
                            (reader->packets_info[0].flags & AV_PKT_FLAG_KEY);
  if (reset) {
    // A drained decoder accepts the new file's keyframe without reallocating its capture buffers.
    if (decoded_ && !next_segment) {
      v4l_decoder = std::make_unique<V4LDecoder>();
      if (!v4l_decoder->init(V4LDecoder::DEVICE, width, height, V4L2_PIX_FMT_HEVC)) return false;
    }
    // seeking to the nearest key frame
    for (int i = idx; i >= 0; --i) {
      if (reader->packets_info[i].flags & AV_PKT_FLAG_KEY) {
        from_idx = i;
        break;
      }
    }

    auto pos = reader->packets_info[from_idx].pos;
    int ret = avformat_seek_file(reader->input_ctx, 0, pos, pos, pos, AVSEEK_FLAG_BYTE);
    if (ret < 0) {
      rError("Failed to seek to byte position %lld: %d", pos, AVERROR(ret));
      return false;
    }
  }
  reader->prev_idx = idx;
  active_reader_ = reader;
  decoded_ = true;
  bool result = false;
  AVPacket pkt;
  v4l_decoder->avctx = reader->input_ctx;
  for (int i = from_idx; i <= idx; ++i) {
    if (reader->abort_ && *reader->abort_) return false;
    if (av_read_frame(reader->input_ctx, &pkt) == 0) {
      if (reset && i == from_idx) {
        // Loggerd writes HEVC headers once per segment; a fresh decoder needs them after a seek.
        const auto *codec = reader->input_ctx->streams[reader->video_stream_idx_]->codecpar;
        if (codec->extradata_size > 0) {
          const int size = pkt.size;
          if (av_grow_packet(&pkt, codec->extradata_size) < 0) { av_packet_unref(&pkt); return false; }
          memmove(pkt.data + codec->extradata_size, pkt.data, size);
          memcpy(pkt.data, codec->extradata, codec->extradata_size);
        }
      }
      const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(1);
      bool queued = false;
      V4LDecodedFrame frame;
      while (!(reader->abort_ && *reader->abort_) && std::chrono::steady_clock::now() < deadline) {
        if (!queued) queued = v4l_decoder->queuePacket(&pkt, 0);
        if (!v4l_decoder->pump(frame, 50)) break;
        if (frame.buf) break;
      }
      if (frame.buf) {
        // Qualcomm capture surfaces include alignment padding; retain the recorded visible dimensions.
        if (frame.buf->width < buf->width || frame.buf->height < buf->height || frame.buf->stride < buf->width) {
          rError("Hardware decoder surface %zux%zu cannot cover recorded frame %zux%zu", frame.buf->width, frame.buf->height, buf->width, buf->height);
          v4l_decoder->releaseFrame(frame.buf); av_packet_unref(&pkt); return false;
        }
        for (size_t row = 0; row < buf->height; ++row) memcpy(buf->y + row * buf->stride, frame.buf->y + row * frame.buf->stride, buf->width);
        for (size_t row = 0; row < buf->height / 2; ++row) memcpy(buf->uv + row * buf->stride, frame.buf->uv + row * frame.buf->stride, buf->width);
        v4l_decoder->releaseFrame(frame.buf);
        result = i == idx;
      } else {
        rError("Hardware decoder produced no frame for packet %d", i);
        av_packet_unref(&pkt);
        return false;
      }
      av_packet_unref(&pkt);
    }
  }
  return result;
}
#endif
