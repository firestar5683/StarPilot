#include "starpilot/ui/starpilot_ui.h"

#include <cstdlib>
#include <string>

#include <QDebug>
#include <QJsonParseError>

#include "system/hardware/hw.h"

static void update_state(StarPilotUIState *fs) {
  StarPilotUIScene &starpilot_scene = fs->starpilot_scene;

  SubMaster &fpsm = *(fs->sm);
  fpsm.update(0);

  const char *desktop_fake_wifi_env = std::getenv("SP_ALLOW_DESKTOP_FAKE_WIFI");
  const bool desktop_force_online = Hardware::PC() && desktop_fake_wifi_env != nullptr && std::string(desktop_fake_wifi_env) != "0";
  if (desktop_force_online) {
    starpilot_scene.online = true;
  }

  if (fpsm.updated("deviceState")) {
    const cereal::DeviceState::Reader &deviceState = fpsm["deviceState"].getDeviceState();
    if (!desktop_force_online) {
      starpilot_scene.online = deviceState.getNetworkType() != cereal::DeviceState::NetworkType::NONE;
    }
  }
  starpilot_scene.switchback_mode_enabled = fs->params_memory.getBool("SwitchbackModeEnabled");

  if (fpsm.updated("starpilotCarState")) {
    const cereal::StarPilotCarState::Reader &starpilotCarState = fpsm["starpilotCarState"].getStarpilotCarState();
    starpilot_scene.always_on_lateral_active = !starpilot_scene.enabled && starpilotCarState.getAlwaysOnLateralEnabled();
    starpilot_scene.traffic_mode_enabled = starpilotCarState.getTrafficModeEnabled();
  }
  if (fpsm.updated("starpilotPlan")) {
    const cereal::StarPilotPlan::Reader &starpilotPlan = fpsm["starpilotPlan"].getStarpilotPlan();
    if (starpilotPlan.getThemeUpdated()) {
      emit fs->themeUpdated();
    }
    capnp::Text::Reader toggles = starpilotPlan.getStarpilotToggles();
    QByteArray current_toggles(toggles.cStr(), toggles.size());
    // starpilot_process only broadcasts the full toggles JSON periodically and
    // sends an empty string on every other frame. Skip the empty broadcasts so
    // we don't parse "" (QJsonParseError "illegal value") every frame.
    if (!current_toggles.trimmed().isEmpty()) {
      static QByteArray previous_toggles;
      if (previous_toggles != current_toggles) {
        QJsonParseError parse_error;
        QJsonDocument toggles_doc = QJsonDocument::fromJson(current_toggles, &parse_error);
        if (parse_error.error == QJsonParseError::NoError && toggles_doc.isObject()) {
          QJsonObject updated_toggles = starpilot_scene.starpilot_toggles;
          const QJsonObject parsed_toggles = toggles_doc.object();
          for (auto it = parsed_toggles.begin(); it != parsed_toggles.end(); ++it) {
            updated_toggles.insert(it.key(), it.value());
          }
          starpilot_scene.starpilot_toggles = updated_toggles;
        } else {
          qWarning() << "Ignoring invalid StarPilot toggles JSON:" << parse_error.errorString();
        }
        previous_toggles = current_toggles;
      }
    }
  }

  // Keep force drive-state toggles authoritative from params so UI state
  // switches immediately even if starpilotPlan is delayed.
  starpilot_scene.starpilot_toggles["force_offroad"] = fs->params.getBool("ForceOffroad");
  starpilot_scene.starpilot_toggles["force_onroad"] = fs->params.getBool("ForceOnroad");

  if (fpsm.updated("selfdriveState")) {
    const cereal::SelfdriveState::Reader &selfdriveState = fpsm["selfdriveState"].getSelfdriveState();
    starpilot_scene.enabled = selfdriveState.getEnabled();
  }
}

StarPilotUIState::StarPilotUIState(QObject *parent) : QObject(parent) {
  sm = std::make_unique<SubMaster, const std::initializer_list<const char *>>({
    "carControl", "deviceState", "starpilotCarState", "starpilotDeviceState",
    "starpilotPlan", "starpilotRadarState", "starpilotSelfdriveState", "liveDelay",
    "liveParameters", "liveTorqueParameters", "liveTracks", "mapdExtendedOut", "mapdOut", "selfdriveState"
  });

  // Provide sane local defaults until starpilotPlan publishes real toggles.
  starpilot_scene.starpilot_toggles = {
    {"debug_mode", false},
    {"driver_camera_in_reverse", false},
    {"force_offroad", false},
    {"force_onroad", false},
    {"screen_brightness", 101},
    {"screen_brightness_onroad", 101},
    {"screen_timeout", 30},
    {"screen_timeout_onroad", 10},
    {"sidebar_color1", "#FFFFFFFF"},
    {"sidebar_color2", "#FFFFFFFF"},
    {"sidebar_color3", "#FFFFFFFF"},
    {"simple_mode", false},
    {"standby_mode", false},
    {"tethering_config", 0},
  };

  wifi = new WifiManager(this);

  if (params.getInt("TetheringEnabled") == 1) {
    wifi->setTetheringEnabled(true);
  }
}

StarPilotUIState *starpilotUIState() {
  static StarPilotUIState starpilot_ui_state;
  return &starpilot_ui_state;
}

void StarPilotUIState::update() {
  update_state(this);

  starpilot_scene.conditional_status = starpilot_scene.enabled ? params_memory.getInt("CEStatus") : 0;
  starpilot_scene.driver_camera_timer = starpilot_scene.reverse && starpilot_scene.starpilot_toggles.value("driver_camera_in_reverse").toBool() ? starpilot_scene.driver_camera_timer + 1 : 0;
}
