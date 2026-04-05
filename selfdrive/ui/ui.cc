#include "selfdrive/ui/ui.h"

#include <algorithm>
#include <cmath>

#include <QtConcurrent>

#include "common/transformations/orientation.hpp"
#include "common/swaglog.h"
#include "common/util.h"
#include "common/watchdog.h"
#include "system/hardware/hw.h"

#define BACKLIGHT_DT 0.05
#define BACKLIGHT_TS 10.00

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
}

void UIState::update() {
  update_sockets(this);
  update_state(this, starpilotUIState());
  updateStatus(starpilotUIState());

  if (sm->frame % UI_FREQ == 0) {
    watchdog_kick(nanos_since_boot());
  }
  emit uiUpdate(*this, *starpilotUIState());

  StarPilotUIState *fs = starpilotUIState();
  StarPilotUIScene &starpilot_scene = fs->starpilot_scene;
  QJsonObject &starpilot_toggles = starpilot_scene.starpilot_toggles;

  if (starpilot_scene.downloading_update || starpilot_scene.starpilot_panel_active) {
    device()->resetInteractiveTimeout(starpilot_toggles.value("screen_timeout").toInt(), starpilot_toggles.value("screen_timeout_onroad").toInt());
  }

  fs->update();
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

  setAwake(s.scene.ignition || interactive_timeout > 0);
}

UIState *uiState() {
  static UIState ui_state;
  return &ui_state;
}

Device *device() {
  static Device _device;
  return &_device;
}
