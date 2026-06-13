#include "selfdrive/ui/ui.h"

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <cmath>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fcntl.h>
#include <mutex>
#include <sys/syscall.h>
#include <sys/types.h>
#include <thread>
#include <unistd.h>

#include <QtConcurrent>

#include "common/transformations/orientation.hpp"
#include "common/swaglog.h"
#include "common/util.h"
#include "common/watchdog.h"
#include "system/hardware/hw.h"

#define BACKLIGHT_DT 0.05
#define BACKLIGHT_TS 10.00

namespace {

enum class UIStallPhase {
  INIT = 0,
  UPDATE_START,
  AFTER_SOCKETS,
  AFTER_STATE,
  AFTER_STATUS,
  AFTER_WATCHDOG,
  AFTER_EMIT,
  AFTER_FS_UPDATE,
  IDLE,
};

std::atomic<uint64_t> ui_stall_last_progress_ns{0};
std::atomic<int> ui_stall_phase{static_cast<int>(UIStallPhase::INIT)};
std::atomic<uint64_t> ui_stall_frame{0};
std::atomic<bool> ui_stall_reported{false};
std::atomic<uint64_t> ui_stall_reported_ns{0};
std::atomic<int> ui_stall_reported_phase{static_cast<int>(UIStallPhase::INIT)};
std::atomic<pid_t> ui_main_tid{0};

double read_env_double(const char *name, double default_value) {
  const char *value = std::getenv(name);
  if (value == nullptr || *value == '\0') {
    return default_value;
  }

  char *end = nullptr;
  double parsed = std::strtod(value, &end);
  if (end == value || (end != nullptr && *end != '\0') || parsed <= 0.0) {
    return default_value;
  }
  return parsed;
}

const char *ui_stall_phase_name(UIStallPhase phase) {
  switch (phase) {
    case UIStallPhase::INIT: return "init";
    case UIStallPhase::UPDATE_START: return "update_start";
    case UIStallPhase::AFTER_SOCKETS: return "after_sockets";
    case UIStallPhase::AFTER_STATE: return "after_state";
    case UIStallPhase::AFTER_STATUS: return "after_status";
    case UIStallPhase::AFTER_WATCHDOG: return "after_watchdog";
    case UIStallPhase::AFTER_EMIT: return "after_emit";
    case UIStallPhase::AFTER_FS_UPDATE: return "after_fs_update";
    case UIStallPhase::IDLE: return "idle";
  }
  return "unknown";
}

std::string ui_stall_dump_dir() {
  return access("/data/log", W_OK) == 0 ? "/data/log" : "/tmp";
}

void write_stall_dump_section(int fd, const std::string &title, const std::string &body) {
  std::string output = "== " + title + " ==\n";
  output += body.empty() ? "<unavailable>\n" : body;
  if (!output.empty() && output.back() != '\n') {
    output += '\n';
  }
  HANDLE_EINTR(write(fd, output.data(), output.size()));
}

void write_ui_thread_snapshot(int fd) {
  const pid_t tid = ui_main_tid.load(std::memory_order_relaxed);
  if (tid <= 0) {
    write_stall_dump_section(fd, "main_thread", "<unavailable>");
    return;
  }

  write_stall_dump_section(fd, "main_thread", util::string_format("pid=%d tid=%d", getpid(), tid));

  const std::string task_dir = "/proc/self/task/" + std::to_string(tid);
  write_stall_dump_section(fd, "main_thread status", util::read_file(task_dir + "/status"));
  write_stall_dump_section(fd, "main_thread wchan", util::read_file(task_dir + "/wchan"));
  write_stall_dump_section(fd, "main_thread syscall", util::read_file(task_dir + "/syscall"));
  write_stall_dump_section(fd, "main_thread kernel_stack", util::read_file(task_dir + "/stack"));
}

double ui_elapsed_s(uint64_t now, uint64_t then) {
  if (then == 0 || now < then) {
    return 0.0;
  }
  return static_cast<double>(now - then) / 1e9;
}

bool ui_timestamp_anomaly(uint64_t now, uint64_t then, const char *context, UIStallPhase phase, uint64_t frame) {
  if (then == 0 || now >= then) {
    return false;
  }

  LOGW("UI stall monitor timestamp anomaly (%s now_ns=%llu then_ns=%llu phase=%s frame=%llu)",
       context,
       static_cast<unsigned long long>(now),
       static_cast<unsigned long long>(then),
       ui_stall_phase_name(phase),
       static_cast<unsigned long long>(frame));
  return true;
}

void ui_stall_progress(UIStallPhase phase, uint64_t frame = 0) {
  const uint64_t now = nanos_since_boot();
  ui_stall_phase.store(static_cast<int>(phase), std::memory_order_relaxed);
  ui_stall_frame.store(frame, std::memory_order_relaxed);
  ui_stall_last_progress_ns.store(now, std::memory_order_relaxed);

  if (ui_stall_reported.exchange(false, std::memory_order_relaxed)) {
    const uint64_t stall_started = ui_stall_reported_ns.load(std::memory_order_relaxed);
    const UIStallPhase stalled_phase = static_cast<UIStallPhase>(ui_stall_reported_phase.load(std::memory_order_relaxed));
    const double stalled_for_s = ui_elapsed_s(now, stall_started);
    if (ui_timestamp_anomaly(now, stall_started, "recover", stalled_phase, frame)) {
      ui_stall_reported_ns.store(0, std::memory_order_relaxed);
    }
    LOGW("UI stall recovered after %.1fs (stalled_phase=%s current_phase=%s frame=%llu)",
         stalled_for_s,
         ui_stall_phase_name(stalled_phase),
         ui_stall_phase_name(phase),
         static_cast<unsigned long long>(frame));
  }
}

void start_ui_stall_monitor() {
  static std::once_flag once;
  std::call_once(once, [] {
    ui_main_tid.store(static_cast<pid_t>(syscall(SYS_gettid)), std::memory_order_relaxed);
    ui_stall_progress(UIStallPhase::INIT, 0);

    const double stall_probe_dt = read_env_double("UI_STALL_PROBE_MAX_DT", 5.0);
    if (stall_probe_dt <= 0.0) {
      return;
    }

    std::thread([stall_probe_dt]() {
      using namespace std::chrono_literals;
      constexpr auto poll_interval = 250ms;

      while (true) {
        std::this_thread::sleep_for(poll_interval);

        const uint64_t now = nanos_since_boot();
        const uint64_t last_progress = ui_stall_last_progress_ns.load(std::memory_order_relaxed);
        if (last_progress == 0) {
          continue;
        }

        const UIStallPhase phase = static_cast<UIStallPhase>(ui_stall_phase.load(std::memory_order_relaxed));
        const uint64_t frame = ui_stall_frame.load(std::memory_order_relaxed);
        if (ui_timestamp_anomaly(now, last_progress, "probe", phase, frame)) {
          ui_stall_last_progress_ns.store(now, std::memory_order_relaxed);
          ui_stall_reported.store(false, std::memory_order_relaxed);
          continue;
        }

        const double stalled_for_s = ui_elapsed_s(now, last_progress);
        if (stalled_for_s < stall_probe_dt) {
          continue;
        }

        bool expected = false;
        if (!ui_stall_reported.compare_exchange_strong(expected, true, std::memory_order_relaxed)) {
          continue;
        }

        ui_stall_reported_ns.store(now, std::memory_order_relaxed);
        ui_stall_reported_phase.store(static_cast<int>(phase), std::memory_order_relaxed);

        const std::string path = ui_stall_dump_dir() + "/qt_ui_stall_" + std::to_string(getpid()) + "_" + std::to_string(now) + ".log";
        int fd = open(path.c_str(), O_CREAT | O_WRONLY | O_TRUNC | O_CLOEXEC, 0644);
        if (fd >= 0) {
          char header[384];
          const int header_len = std::snprintf(header, sizeof(header),
                                               "phase=%s frame=%llu stalled_for_s=%.3f now_ns=%llu last_progress_ns=%llu\n",
                                               ui_stall_phase_name(phase),
                                               static_cast<unsigned long long>(frame),
                                               stalled_for_s,
                                               static_cast<unsigned long long>(now),
                                               static_cast<unsigned long long>(last_progress));
          if (header_len > 0) {
            write(fd, header, header_len);
          }

          write_ui_thread_snapshot(fd);
          close(fd);
          LOGE("UI main thread stalled for %.1fs (phase=%s frame=%llu now_ns=%llu last_progress_ns=%llu dump=%s)",
               stalled_for_s,
               ui_stall_phase_name(phase),
               static_cast<unsigned long long>(frame),
               static_cast<unsigned long long>(now),
               static_cast<unsigned long long>(last_progress),
               path.c_str());
        } else {
          LOGE("UI main thread stalled for %.1fs (phase=%s frame=%llu now_ns=%llu last_progress_ns=%llu dump_open_failed errno=%d)",
               stalled_for_s,
               ui_stall_phase_name(phase),
               static_cast<unsigned long long>(frame),
               static_cast<unsigned long long>(now),
               static_cast<unsigned long long>(last_progress),
               errno);
        }
      }
    }).detach();
  });
}

}  // namespace

static void update_sockets(UIState *s) {
  s->sm->update(0);
}

static void update_state(UIState *s, StarPilotUIState *fs) {
  SubMaster &sm = *(s->sm);
  UIScene &scene = s->scene;

  if (sm.updated("liveCalibration")) {
    auto list2rot = [](const capnp::List<float>::Reader &rpy_list) ->Eigen::Matrix3f {
      return euler2rot({rpy_list[0], rpy_list[1], rpy_list[2]}).cast<float>();
    };

    auto live_calib = sm["liveCalibration"].getLiveCalibration();
    if (live_calib.getCalStatus() == cereal::LiveCalibrationData::Status::CALIBRATED) {
      auto device_from_calib = list2rot(live_calib.getRpyCalib());
      auto wide_from_device = list2rot(live_calib.getWideFromDeviceEuler());
      s->scene.view_from_calib = VIEW_FROM_DEVICE * device_from_calib;
      s->scene.view_from_wide_calib = VIEW_FROM_DEVICE * wide_from_device * device_from_calib;
    } else {
      s->scene.view_from_calib = s->scene.view_from_wide_calib = VIEW_FROM_DEVICE;
    }
  }
  if (sm.updated("pandaStates")) {
    auto pandaStates = sm["pandaStates"].getPandaStates();
    if (pandaStates.size() > 0) {
      scene.pandaType = pandaStates[0].getPandaType();

      if (scene.pandaType != cereal::PandaState::PandaType::UNKNOWN) {
        scene.ignition = false;
        for (const auto& pandaState : pandaStates) {
          scene.ignition |= pandaState.getIgnitionLine() || pandaState.getIgnitionCan();
        }
      }
    }
  } else if ((s->sm->frame - s->sm->rcv_frame("pandaStates")) > 5*UI_FREQ) {
    scene.pandaType = cereal::PandaState::PandaType::UNKNOWN;
  }
  if (sm.updated("wideRoadCameraState")) {
    auto cam_state = sm["wideRoadCameraState"].getWideRoadCameraState();
    float scale = (cam_state.getSensor() == cereal::FrameData::ImageSensor::AR0231) ? 6.0f : 1.0f;
    scene.light_sensor = std::max(100.0f - scale * cam_state.getExposureValPercent(), 0.0f);
  } else if (!sm.allAliveAndValid({"wideRoadCameraState"})) {
    scene.light_sensor = -1;
  }
  scene.started = sm["deviceState"].getDeviceState().getStarted() && scene.ignition;

  auto params = Params();
  scene.recording_audio = params.getBool("RecordAudio") && scene.started;

  StarPilotUIScene &starpilot_scene = fs->starpilot_scene;

  if (sm.updated("carState")) {
    const cereal::CarState::Reader &carState = sm["carState"].getCarState();
    starpilot_scene.parked = carState.getGearShifter() == cereal::CarState::GearShifter::PARK;
    starpilot_scene.reverse = carState.getGearShifter() == cereal::CarState::GearShifter::REVERSE;
    starpilot_scene.standstill = carState.getStandstill() && !starpilot_scene.reverse;
  }

  if (scene.started) {
    starpilot_scene.started_timer += 1;
  }
  scene.started |= starpilot_scene.starpilot_toggles.value("force_onroad").toBool();
  scene.started &= !starpilot_scene.starpilot_toggles.value("force_offroad").toBool();
}

void ui_update_params(UIState *s) {
  auto params = Params();
  s->scene.is_metric = params.getBool("IsMetric");
}

void UIState::updateStatus(StarPilotUIState *fs) {
  StarPilotUIScene &starpilot_scene = fs->starpilot_scene;
  QJsonObject &starpilot_toggles = starpilot_scene.starpilot_toggles;

  if (scene.started && sm->updated("selfdriveState")) {
    auto ss = (*sm)["selfdriveState"].getSelfdriveState();
    auto state = ss.getState();

    const UIStatus previous_status = status;

    if (state == cereal::SelfdriveState::OpenpilotState::PRE_ENABLED || state == cereal::SelfdriveState::OpenpilotState::OVERRIDING) {
      status = STATUS_OVERRIDE;
    } else if (starpilot_scene.switchback_mode_enabled && (ss.getEnabled() || starpilot_scene.always_on_lateral_active)) {
      status = STATUS_SWITCHBACK_MODE_ENABLED;
    } else if (starpilot_scene.always_on_lateral_active) {
      status = STATUS_ALWAYS_ON_LATERAL_ACTIVE;
    } else if (starpilot_scene.traffic_mode_enabled && ss.getEnabled()) {
      status = STATUS_TRAFFIC_MODE_ENABLED;
    } else {
      status = ss.getEnabled() ? STATUS_ENGAGED : STATUS_DISENGAGED;
    }

    const bool selfdrive_visible_alert = ss.getAlertSize() != cereal::SelfdriveState::AlertSize::NONE;
    bool starpilot_visible_alert = false;
    if (fs->sm->rcv_frame("starpilotSelfdriveState") > 0) {
      const auto fpss = (*fs->sm)["starpilotSelfdriveState"].getStarpilotSelfdriveState();
      starpilot_visible_alert = fpss.getAlertSize() != cereal::StarPilotSelfdriveState::AlertSize::NONE;
    }

    // Standby mode should wake for any visible onroad alert, not just elevated
    // alert statuses. Calibration uses NORMAL status but still needs to wake.
    starpilot_scene.wake_up_screen =
      selfdrive_visible_alert ||
      starpilot_visible_alert ||
      ss.getAlertStatus() != cereal::SelfdriveState::AlertStatus::NORMAL ||
      (status != previous_status && status != STATUS_OVERRIDE);
  }

  if (engaged() != engaged_prev) {
    engaged_prev = engaged();
    emit engagedChanged(engaged());
  }

  // Handle onroad/offroad transition
  if (scene.started != started_prev || sm->frame == 1) {
    if (scene.started) {
      status = STATUS_DISENGAGED;
      scene.started_frame = sm->frame;
    }
    started_prev = scene.started;
    emit offroadTransition(!scene.started);

    if (starpilot_toggles.value("tethering_config").toInt() == 2) {
      fs->wifi->setTetheringEnabled(scene.started);
    }
  }
}

UIState::UIState(QObject *parent) : QObject(parent) {
  start_ui_stall_monitor();
  sm = std::make_unique<SubMaster>(std::vector<const char*>{
    "modelV2", "controlsState", "liveCalibration", "radarState", "deviceState",
    "pandaStates", "carParams", "driverMonitoringState", "carState", "driverStateV2",
    "wideRoadCameraState", "managerState", "selfdriveState", "longitudinalPlan",
  });
  prime_state = new PrimeState(this);
  language = QString::fromStdString(Params().get("LanguageSetting"));

  // update timer
  timer = new QTimer(this);
  QObject::connect(timer, &QTimer::timeout, this, &UIState::update);
  timer->start(1000 / UI_FREQ);
  ui_stall_progress(UIStallPhase::IDLE, sm->frame);
}

void UIState::update() {
  ui_stall_progress(UIStallPhase::UPDATE_START, sm->frame);
  update_sockets(this);
  ui_stall_progress(UIStallPhase::AFTER_SOCKETS, sm->frame);
  update_state(this, starpilotUIState());
  ui_stall_progress(UIStallPhase::AFTER_STATE, sm->frame);
  updateStatus(starpilotUIState());
  ui_stall_progress(UIStallPhase::AFTER_STATUS, sm->frame);

  if (sm->frame % UI_FREQ == 0) {
    if (!watchdog_kick(nanos_since_boot())) {
      LOGE("UI watchdog kick failed at frame %llu", static_cast<unsigned long long>(sm->frame));
    }
    // Re-pin to the little cores: power-save can offline our core and the
    // kernel may rebalance us onto core 4 (the realtime control loop).
    if (!Hardware::PC()) {
      util::set_core_affinity({0, 1, 2, 3});
    }
  }
  ui_stall_progress(UIStallPhase::AFTER_WATCHDOG, sm->frame);
  emit uiUpdate(*this, *starpilotUIState());
  ui_stall_progress(UIStallPhase::AFTER_EMIT, sm->frame);

  StarPilotUIState *fs = starpilotUIState();
  StarPilotUIScene &starpilot_scene = fs->starpilot_scene;
  QJsonObject &starpilot_toggles = starpilot_scene.starpilot_toggles;

  if (starpilot_scene.downloading_update || starpilot_scene.starpilot_panel_active) {
    device()->resetInteractiveTimeout(starpilot_toggles.value("screen_timeout").toInt(), starpilot_toggles.value("screen_timeout_onroad").toInt());
  }

  fs->update();
  ui_stall_progress(UIStallPhase::AFTER_FS_UPDATE, sm->frame);
  ui_stall_progress(UIStallPhase::IDLE, sm->frame);
}

Device::Device(QObject *parent) : brightness_filter(BACKLIGHT_OFFROAD, BACKLIGHT_TS, BACKLIGHT_DT), QObject(parent) {
  setAwake(true);
  resetInteractiveTimeout();

  QObject::connect(uiState(), &UIState::uiUpdate, this, &Device::update);
}

void Device::update(const UIState &s, const StarPilotUIState &fs) {
  updateBrightness(s, fs);
  updateWakefulness(s, fs);
}

void Device::setAwake(bool on) {
  if (on != awake) {
    awake = on;
    Hardware::set_display_power(awake);
    LOGD("setting display power %d", awake);
    emit displayPowerChanged(awake);
  }
}

void Device::resetInteractiveTimeout(int timeout, int timeout_onroad) {
  if (timeout == -1) {
    timeout = (ignition_on ? 10 : 30);
  } else {
    timeout = (ignition_on ? timeout_onroad : timeout);
  }
  interactive_timeout = timeout * UI_FREQ;
}

void Device::updateBrightness(const UIState &s, const StarPilotUIState &fs) {
  const StarPilotUIScene &starpilot_scene = fs.starpilot_scene;
  const QJsonObject &starpilot_toggles = starpilot_scene.starpilot_toggles;
  const int screen_brightness_onroad = starpilot_toggles.value("screen_brightness_onroad").toInt();
  const int clamped_onroad_brightness = std::clamp(screen_brightness_onroad, 1, 100);

  float clipped_brightness = offroad_brightness;
  if (s.scene.started && s.scene.light_sensor >= 0) {
    clipped_brightness = s.scene.light_sensor;

    // CIE 1931 - https://www.photonstophotos.net/GeneralTopics/Exposure/Psychometric_Lightness_and_Gamma.htm
    if (clipped_brightness <= 8) {
      clipped_brightness = (clipped_brightness / 903.3);
    } else {
      clipped_brightness = std::pow((clipped_brightness + 16.0) / 116.0, 3.0);
    }

    // Scale back to 10% to 100%
    clipped_brightness = std::clamp(100.0f * clipped_brightness, 10.0f, 100.0f);
  }

  int brightness = brightness_filter.update(clipped_brightness);
  if (!awake) {
    brightness = 0;
  } else if (s.scene.started && !starpilot_scene.wake_up_screen && interactive_timeout == 0 && starpilot_toggles.value("standby_mode").toBool()) {
    brightness = 0;
  } else if (s.scene.started && screen_brightness_onroad != 101) {
    // Guard against stale params that may still contain the old onroad "off"
    // value. Standby mode is the only supported way to blank the screen onroad.
    brightness = interactive_timeout > 0 ? std::max(5, clamped_onroad_brightness) : clamped_onroad_brightness;
  } else if (starpilot_toggles.value("screen_brightness").toInt() != 101) {
    brightness = starpilot_toggles.value("screen_brightness").toInt();
  }

  if (brightness != last_brightness) {
    if (!brightness_future.isRunning()) {
      brightness_future = QtConcurrent::run(Hardware::set_brightness, brightness);
      last_brightness = brightness;
    }
  }
}

void Device::updateWakefulness(const UIState &s, const StarPilotUIState &fs) {
  const StarPilotUIScene &starpilot_scene = fs.starpilot_scene;
  const QJsonObject &starpilot_toggles = starpilot_scene.starpilot_toggles;
  const bool standby_mode = starpilot_toggles.value("standby_mode").toBool();
  const int screen_timeout = starpilot_toggles.value("screen_timeout").toInt();
  const int screen_timeout_onroad = starpilot_toggles.value("screen_timeout_onroad").toInt();

  bool ignition_state_changed = s.scene.ignition != ignition_on;
  ignition_on = s.scene.ignition;

  // Standby mode should extend the current wake window for alerts and status
  // changes, but it must not clear the timer every frame or manual wakes will
  // collapse immediately.
  if (ignition_on && standby_mode && starpilot_scene.wake_up_screen) {
    resetInteractiveTimeout(screen_timeout, screen_timeout_onroad);
  }

  if (ignition_state_changed) {
    resetInteractiveTimeout(screen_timeout, screen_timeout_onroad);
  } else if (interactive_timeout > 0 && --interactive_timeout == 0) {
    emit interactiveTimeout();
  }

  // Power the display from filtered onroad state rather than raw ignition so
  // brief ignition-line glitches do not blank the screen immediately.
  setAwake(s.scene.started || interactive_timeout > 0);
}

UIState *uiState() {
  static UIState ui_state;
  return &ui_state;
}

Device *device() {
  static Device _device;
  return &_device;
}
