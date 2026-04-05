#include "starpilot/ui/qt/offroad/data_settings.h"
#include "starpilot/ui/qt/offroad/device_settings.h"
#include "starpilot/ui/qt/offroad/starpilot_settings.h"
#include "starpilot/ui/qt/offroad/lateral_settings.h"
#include "starpilot/ui/qt/offroad/longitudinal_settings.h"
#include "starpilot/ui/qt/offroad/maps_settings.h"
#include "starpilot/ui/qt/offroad/model_settings.h"
#include "starpilot/ui/qt/offroad/navigation_settings.h"
#include "starpilot/ui/qt/offroad/sounds_settings.h"
#include "starpilot/ui/qt/offroad/theme_settings.h"
#include "starpilot/ui/qt/offroad/utilities.h"
#include "starpilot/ui/qt/offroad/vehicle_settings.h"
#include "starpilot/ui/qt/offroad/visual_settings.h"
#include "starpilot/ui/qt/offroad/wheel_settings.h"
#include "system/hardware/hw.h"

bool nnffLogFileExists(const QString &carFingerprint) {
  static QStringList models;
  static QMap<QString, QString> substitutes;

  if (models.isEmpty()) {
    QFileInfoList fileInfoList = QDir(QStringLiteral("../../starpilot/assets/nnff_models")).entryInfoList(QDir::Files | QDir::NoDotAndDotDot);
    for (const QFileInfo &fileInfo : fileInfoList) {
      models.append(fileInfo.completeBaseName());
    }

    QFile sub_file("../../opendbc/car/torque_data/substitute.toml");
    if (sub_file.open(QIODevice::ReadOnly)) {
      QTextStream in(&sub_file);
      while (!in.atEnd()) {
        QString line = in.readLine().trimmed();
        if (line.startsWith("#") || line.startsWith("legend") || !line.contains("=")) {
          continue;
        }

        QStringList parts = line.split("=");
        if (parts.size() == 2) {
          QString key = parts[0].trimmed().remove('"');
          QString value = parts[1].trimmed().remove('"');
          if (!key.isEmpty() && !value.isEmpty()) {
            substitutes[key] = value;
          }
        }
      }
    }
  }

  QStringList fingerprintsToCheck;
  fingerprintsToCheck.append(carFingerprint);
  if (substitutes.contains(carFingerprint)) {
    fingerprintsToCheck.append(substitutes.value(carFingerprint));
  }

  for (const QString &fingerprint : fingerprintsToCheck) {
    for (const QString &match : models) {
      if (match.startsWith(fingerprint)) {
        std::cout << "NNFF model found for fingerprint: " << fingerprint.toStdString() << std::endl;
        return true;
      }
    }
  }

  return false;
}

void StarPilotSettingsWindow::createPanelButtons(StarPilotListWidget *list) {
  StarPilotDataPanel *starpilotDataPanel = new StarPilotDataPanel(this, !shownDescriptions.value("StarPilotDataPanel").toBool(false));
  StarPilotDevicePanel *starpilotDevicePanel = new StarPilotDevicePanel(this, !shownDescriptions.value("StarPilotDevicePanel").toBool(false));
  StarPilotLateralPanel *starpilotLateralPanel = new StarPilotLateralPanel(this, !shownDescriptions.value("StarPilotLateralPanel").toBool(false));
  StarPilotLongitudinalPanel *starpilotLongitudinalPanel = new StarPilotLongitudinalPanel(this, !shownDescriptions.value("StarPilotLongitudinalPanel").toBool(false));
  StarPilotMapsPanel *starpilotMapsPanel = new StarPilotMapsPanel(this, !shownDescriptions.value("StarPilotMapsPanel").toBool(false));
  StarPilotModelPanel *starpilotModelPanel = new StarPilotModelPanel(this);
  StarPilotNavigationPanel *starpilotNavigationPanel = new StarPilotNavigationPanel(this, !shownDescriptions.value("StarPilotNavigationPanel").toBool(false));
  StarPilotSoundsPanel *starpilotSoundsPanel = new StarPilotSoundsPanel(this, !shownDescriptions.value("StarPilotSoundsPanel").toBool(false));
  StarPilotThemesPanel *starpilotThemesPanel = new StarPilotThemesPanel(this, !shownDescriptions.value("StarPilotThemesPanel").toBool(false));
  StarPilotUtilitiesPanel *starpilotUtilitiesPanel = new StarPilotUtilitiesPanel(this, !shownDescriptions.value("StarPilotUtilitiesPanel").toBool(false));
  StarPilotVehiclesPanel *starpilotVehiclesPanel = new StarPilotVehiclesPanel(this, !shownDescriptions.value("StarPilotVehiclesPanel").toBool(false));
  StarPilotVisualsPanel *starpilotVisualsPanel = new StarPilotVisualsPanel(this, !shownDescriptions.value("StarPilotVisualsPanel").toBool(false));
  StarPilotWheelPanel *starpilotWheelPanel = new StarPilotWheelPanel(this, !shownDescriptions.value("StarPilotWheelPanel").toBool(false));

  std::vector<std::vector<std::tuple<QString, QWidget*>>> panelButtons = {
    {{tr("MANAGE"), starpilotSoundsPanel}},
    {{tr("DRIVING MODEL"), starpilotModelPanel}, {tr("GAS / BRAKE"), starpilotLongitudinalPanel}, {tr("STEERING"), starpilotLateralPanel}},
    {{tr("MAP DATA"), starpilotMapsPanel}, {tr("NAVIGATION"), starpilotNavigationPanel}},
    {{tr("DATA"), starpilotDataPanel}, {tr("DEVICE CONTROLS"), starpilotDevicePanel}, {tr("UTILITIES"), starpilotUtilitiesPanel}},
    {{tr("APPEARANCE"), starpilotVisualsPanel}, {tr("THEME"), starpilotThemesPanel}},
    {{tr("VEHICLE SETTINGS"), starpilotVehiclesPanel}, {tr("WHEEL CONTROLS"), starpilotWheelPanel}}
  };

  std::vector<std::tuple<QString, QString, QString>> panelInfo = {
    {tr("Alerts and Sounds"), tr("<b>Adjust alert volumes and enable custom notifications.</b>"), "../../starpilot/assets/toggle_icons/icon_sound.png"},
    {tr("Driving Controls"), tr("<b>Fine-tune custom StarPilot acceleration, braking, and steering controls.</b>"), "../../starpilot/assets/toggle_icons/icon_steering.png"},
    {tr("Navigation"), tr("<b>Download map data for the \"Speed Limit Controller\".</b>"), "../../starpilot/assets/toggle_icons/icon_navigate.png"},
    {tr("System Settings"), tr("<b>Manage backups, device settings, screen options, storage, and tools to keep StarPilot running smoothly.</b>"), "../../starpilot/assets/toggle_icons/icon_system.png"},
    {tr("Theme and Appearance"), tr("<b>Customize the look of the driving screen and interface, including themes!</b>"), "../../starpilot/assets/toggle_icons/icon_display.png"},
    {tr("Vehicle Settings"), tr("<b>Configure car-specific options and steering wheel button mappings.</b>"), "../../starpilot/assets/toggle_icons/icon_vehicle.png"}
  };

  for (size_t i = 0; i < panelInfo.size(); ++i) {
    const QString &title = std::get<0>(panelInfo[i]);
    const QString &description = std::get<1>(panelInfo[i]);
    const QString &icon = std::get<2>(panelInfo[i]);

    const std::vector<std::tuple<QString, QWidget*>> &widgetLabels = panelButtons[i];

    std::vector<QString> labels;
    std::vector<QWidget*> widgets;

    for (size_t j = 0; j < widgetLabels.size(); ++j) {
      labels.push_back(std::get<0>(widgetLabels[j]));

      QWidget *panel = std::get<1>(widgetLabels[j]);
      panel->setContentsMargins(50, 25, 50, 25);

      ScrollView *panelFrame = new ScrollView(panel, this);
      mainLayout->addWidget(panelFrame);
      widgets.push_back(panelFrame);
    }

    StarPilotButtonsControl *panelButton = new StarPilotButtonsControl(title, description, icon, labels);
    if (title == tr("Alerts and Sounds")) soundPanelButtons = panelButton;
    if (title == tr("Driving Controls")) drivingPanelButtons = panelButton;
    if (title == tr("Navigation")) navigationPanelButtons = panelButton;
    if (title == tr("System Settings")) systemPanelButtons = panelButton;
    if (title == tr("Theme and Appearance")) themePanelButtons = panelButton;
    if (title == tr("Vehicle Settings")) vehiclePanelButtons = panelButton;

    if (forceOpenDescriptions) {
      panelButton->showDescription();
    }

    QObject::connect(panelButton, &StarPilotButtonsControl::buttonClicked, [widgets, this](int id) {
      mainLayout->setCurrentWidget(widgets[id]);

      panelOpen = true;

      openPanel();

      ScrollView *panelFrame = qobject_cast<ScrollView*>(widgets[id]);
      if (panelFrame) {
        QWidget *panel = panelFrame->widget();
        QString className = panel->metaObject()->className();

        if (!shownDescriptions.value(className).toBool(false)) {
          shownDescriptions.insert(className, true);
          params.putNonBlocking("ShownToggleDescriptions", QJsonDocument(shownDescriptions).toJson(QJsonDocument::Compact).toStdString());
        }
      }
    });

    list->addItem(panelButton);
  }

  QObject::connect(starpilotDataPanel, &StarPilotDataPanel::openSubPanel, this, &StarPilotSettingsWindow::openSubPanel);
  QObject::connect(starpilotDevicePanel, &StarPilotDevicePanel::openSubPanel, this, &StarPilotSettingsWindow::openSubPanel);
  QObject::connect(starpilotLateralPanel, &StarPilotLateralPanel::openSubPanel, this, &StarPilotSettingsWindow::openSubPanel);
  QObject::connect(starpilotLongitudinalPanel, &StarPilotLongitudinalPanel::openSubPanel, this, &StarPilotSettingsWindow::openSubPanel);
  QObject::connect(starpilotLongitudinalPanel, &StarPilotLongitudinalPanel::openSubSubPanel, this, &StarPilotSettingsWindow::openSubSubPanel);
  QObject::connect(starpilotLongitudinalPanel, &StarPilotLongitudinalPanel::openSubSubSubPanel, this, &StarPilotSettingsWindow::openSubSubSubPanel);
  QObject::connect(starpilotMapsPanel, &StarPilotMapsPanel::openSubPanel, this, &StarPilotSettingsWindow::openSubPanel);
  QObject::connect(starpilotModelPanel, &StarPilotModelPanel::openSubPanel, this, &StarPilotSettingsWindow::openSubPanel);
  QObject::connect(starpilotNavigationPanel, &StarPilotNavigationPanel::closeSubPanel, this, &StarPilotSettingsWindow::closeSubPanel);
  QObject::connect(starpilotNavigationPanel, &StarPilotNavigationPanel::openSubPanel, this, &StarPilotSettingsWindow::openSubPanel);
  QObject::connect(starpilotSoundsPanel, &StarPilotSoundsPanel::openSubPanel, this, &StarPilotSettingsWindow::openSubPanel);
  QObject::connect(starpilotThemesPanel, &StarPilotThemesPanel::openSubPanel, this, &StarPilotSettingsWindow::openSubPanel);
  QObject::connect(starpilotVehiclesPanel, &StarPilotVehiclesPanel::openSubPanel, this, &StarPilotSettingsWindow::openSubPanel);
  QObject::connect(starpilotVisualsPanel, &StarPilotVisualsPanel::openSubPanel, this, &StarPilotSettingsWindow::openSubPanel);
  QObject::connect(starpilotVisualsPanel, &StarPilotVisualsPanel::openSubSubPanel, this, &StarPilotSettingsWindow::openSubSubPanel);
}

StarPilotSettingsWindow::StarPilotSettingsWindow(SettingsWindow *parent) : QFrame(parent) {
  shownDescriptions = QJsonDocument::fromJson(QString::fromStdString(params.get("ShownToggleDescriptions")).toUtf8()).object();

  QString className = this->metaObject()->className();
  QString legacyClassName = className;
  legacyClassName.replace("StarPilot", "FrogPilot");

  bool alreadyShown = shownDescriptions.value(className).toBool(false);
  bool legacyShown = legacyClassName != className && shownDescriptions.value(legacyClassName).toBool(false);
  if (legacyShown && !alreadyShown) {
    shownDescriptions.insert(className, true);
    params.putNonBlocking("ShownToggleDescriptions", QJsonDocument(shownDescriptions).toJson(QJsonDocument::Compact).toStdString());
  } else if (!alreadyShown) {
    forceOpenDescriptions = true;
  }

  mainLayout = new QStackedLayout(this);

  QWidget *starpilotWidget = new QWidget(this);
  QVBoxLayout *starpilotLayout = new QVBoxLayout(starpilotWidget);
  starpilotLayout->setContentsMargins(50, 25, 50, 25);
  starpilotWidget->setLayout(starpilotLayout);

  starpilotPanel = new ScrollView(starpilotWidget, this);
  mainLayout->addWidget(starpilotPanel);
  starpilotPanel->setWidget(starpilotWidget);

  StarPilotListWidget *list = new StarPilotListWidget(this);
  starpilotLayout->addWidget(list);

  std::vector<QString> togglePresets{tr("Minimal"), tr("Standard"), tr("Advanced"), tr("Developer")};
  togglePreset = new StarPilotButtonsControl(tr("Tuning Level"),
                                             tr("Choose your tuning level. Lower levels keep it simple; higher levels unlock more toggles for finer control.\n\n"
                                                "Minimal - Ideal for those who prefer simplicity or ease of use\n"
                                                "Standard - Recommended for most users for a balanced experience\n"
                                                "Advanced - Fine-tuning for experienced users\n"
                                                "Developer - Highly customizable settings for seasoned enthusiasts"),
                                              "../../starpilot/assets/toggle_icons/icon_tuning.png", togglePresets, true);
  QObject::connect(togglePreset, &StarPilotButtonsControl::buttonClicked, [this](int id) {
    tuningLevel = id;

    params.putIntNonBlocking("TuningLevel", tuningLevel);

    updateVariables();

    emit tuningLevelChanged(tuningLevel);

    if (id == 3) {
      ConfirmationDialog::alert(tr("WARNING: These settings are risky and can drastically change how openpilot drives. Only change if you fully understand what they do!"), this);
    }
  });
  togglePreset->setCheckedButton(params.getInt("TuningLevel"));
  if (forceOpenDescriptions) {
    togglePreset->showDescription();
  }
  list->addItem(togglePreset, true);

  createPanelButtons(list);

  QObject::connect(parent, &SettingsWindow::closePanel, this, &StarPilotSettingsWindow::closePanel);
  QObject::connect(parent, &SettingsWindow::closeSubPanel, this, &StarPilotSettingsWindow::closeSubPanel);
  QObject::connect(parent, &SettingsWindow::closeSubSubPanel, this, &StarPilotSettingsWindow::closeSubSubPanel);
  QObject::connect(parent, &SettingsWindow::closeSubSubSubPanel, this, &StarPilotSettingsWindow::closeSubSubSubPanel);
  QObject::connect(parent, &SettingsWindow::updateMetric, this, &StarPilotSettingsWindow::updateMetric);
  QObject::connect(parent, &SettingsWindow::updateTuningLevel, this, &StarPilotSettingsWindow::updateTuningLevel);
  QObject::connect(uiState(), &UIState::offroadTransition, this, &StarPilotSettingsWindow::updateVariables);
  QObject::connect(uiState(), &UIState::uiUpdate, this, &StarPilotSettingsWindow::updateState);

  std::vector<std::string> keys = params.allKeys();
  for (std::vector<std::string>::const_iterator it = keys.begin(); it != keys.end(); ++it) {
    const std::string &key = *it;
    starpilotToggleLevels[QString::fromStdString(key)] = params.getTuningLevel(key);
  }
  tuningLevel = params.getInt("TuningLevel");

  closeSubPanel();
  updateMetric(params.getBool("IsMetric"), true);
  updateVariables();
}

void StarPilotSettingsWindow::updateTuningLevel() {
  tuningLevel = params.getInt("TuningLevel");
  togglePreset->setCheckedButton(params.getInt("TuningLevel"));

  updateVariables();

  emit tuningLevelChanged(tuningLevel);
}

bool StarPilotSettingsWindow::showAllTogglesEnabled() {
  return params.getBool("ShowAllToggles");
}

void StarPilotSettingsWindow::showEvent(QShowEvent *event) {
  static bool alertShown = false;

  QString className = this->metaObject()->className();
  if (!shownDescriptions.value(className).toBool(false)) {
    shownDescriptions.insert(className, true);
    params.putNonBlocking("ShownToggleDescriptions", QJsonDocument(shownDescriptions).toJson(QJsonDocument::Compact).toStdString());
  }

  if (forceOpenDescriptions) {
    togglePreset->showDescription();

    drivingPanelButtons->showDescription();
    navigationPanelButtons->showDescription();
    soundPanelButtons->showDescription();
    systemPanelButtons->showDescription();
    themePanelButtons->showDescription();
    vehiclePanelButtons->showDescription();

    if (!alertShown) {
      ConfirmationDialog::alert(tr("All toggle descriptions are currently expanded. You can tap a toggle's name to open or close its description at any time!"), this);
      alertShown = true;
    }
  }
}

void StarPilotSettingsWindow::hideEvent(QHideEvent *event) {
  closePanel();
}

void StarPilotSettingsWindow::closePanel() {
  if (forceOpenDescriptions) {
    togglePreset->showDescription();

    drivingPanelButtons->showDescription();
    navigationPanelButtons->showDescription();
    soundPanelButtons->showDescription();
    systemPanelButtons->showDescription();
    themePanelButtons->showDescription();
    vehiclePanelButtons->showDescription();
  }

  mainLayout->setCurrentWidget(starpilotPanel);

  panelOpen = false;
}

void StarPilotSettingsWindow::updateState() {
  StarPilotUIState &fs = *starpilotUIState();
  StarPilotUIScene &starpilot_scene = fs.starpilot_scene;

  starpilot_scene.starpilot_panel_active = panelOpen && keepScreenOn;
}

void StarPilotSettingsWindow::updateVariables() {
  StarPilotUIState &fs = *starpilotUIState();
  StarPilotUIScene &starpilot_scene = fs.starpilot_scene;
  QJsonObject &starpilot_toggles = starpilot_scene.starpilot_toggles;
  const bool showAllToggles = showAllTogglesEnabled();

  auto applyDesktopVehicleFallback = [&]() {
    QString fallbackMake = starpilot_toggles.value("car_make").toString();
    QString fallbackModel = starpilot_toggles.value("car_model").toString();
    if (fallbackMake.isEmpty()) {
      fallbackMake = "gm";
    }
    if (fallbackModel.isEmpty()) {
      fallbackModel = "CHEVROLET_BOLT_ACC_2022_2023";
    }

    carMake = fallbackMake.toStdString();
    std::string fallbackFingerprint = fallbackModel.toStdString();

    hasPedal = starpilot_toggles.value("has_pedal").toBool(true);
    hasSDSU = starpilot_toggles.value("has_sdsu").toBool();
    hasZSS = starpilot_toggles.value("has_zss").toBool();
    isBolt = fallbackFingerprint.rfind("CHEVROLET_BOLT", 0) == 0;
    isGM = carMake == "gm";
    isHKG = carMake == "hyundai";
    isSubaru = carMake == "subaru";
    isToyota = carMake == "toyota";
    isVolt = fallbackFingerprint.rfind("CHEVROLET_VOLT", 0) == 0;
    canUsePedal = hasPedal || isBolt;
    canUseSDSU = hasSDSU;
  };

  isFrogsGoMoo = ::isFrogsGoMoo();

  std::string carParams = params.get("CarParamsPersistent");
  if (!carParams.empty()) {
    AlignedBuffer aligned_buf;
    capnp::FlatArrayMessageReader cmsg(aligned_buf.align(carParams.data(), carParams.size()));
    cereal::CarParams::Reader CP = cmsg.getRoot<cereal::CarParams>();
    cereal::CarParams::SafetyModel safetyModel = CP.getSafetyConfigs()[0].getSafetyModel();

    std::string carFingerprint = CP.getCarFingerprint();
    carMake = CP.getBrand();

    friction = CP.getLateralTuning().getTorque().getFriction();
    hasAlphaLongitudinal = CP.getAlphaLongitudinalAvailable();
    hasBSM = CP.getEnableBsm();
    hasDashSpeedLimits = carMake == "ford" || carMake == "hyundai" || carMake == "toyota" || carMake == "honda";
    hasNNFFLog = nnffLogFileExists(QString::fromStdString(carFingerprint));
    hasOpenpilotLongitudinal = hasLongitudinalControl(CP);
    hasPCMCruise = CP.getPcmCruise();
    hasPedal = CP.getEnableGasInterceptorDEPRECATED();
    hasRadar = !CP.getRadarUnavailable();
    hasSDSU = starpilot_toggles.value("has_sdsu").toBool();
    hasSNG = CP.getAutoResumeSng();
    hasZSS = starpilot_toggles.value("has_zss").toBool();
    isAngleCar = CP.getSteerControlType() == cereal::CarParams::SteerControlType::ANGLE;
    isBolt = carFingerprint.rfind("CHEVROLET_BOLT", 0) == 0;
    isGM = carMake == "gm";
    isHKG = carMake == "hyundai";
    isHKGCanFd = isHKG && safetyModel == cereal::CarParams::SafetyModel::HYUNDAI_CANFD;
    isSubaru = carMake == "subaru";
    isTorqueCar = CP.getLateralTuning().which() == cereal::CarParams::LateralTuning::TORQUE;
    isToyota = carMake == "toyota";
    isTSK = CP.getSecOcRequired();
    isVolt = carFingerprint.rfind("CHEVROLET_VOLT", 0) == 0;
    latAccelFactor = CP.getLateralTuning().getTorque().getLatAccelFactor();
    lkasAllowedForAOL = starpilot_toggles.value("lkas_allowed_for_aol").toBool();
    longitudinalActuatorDelay = CP.getLongitudinalActuatorDelay();
    startAccel = CP.getStartAccel();
    steerActuatorDelay = CP.getSteerActuatorDelay();
    steerKp = 1.0f;
    steerRatio = CP.getSteerRatio();
    stopAccel = CP.getStopAccel();
    stoppingDecelRate = CP.getStoppingDecelRate();
    vEgoStarting = CP.getVEgoStarting();
    vEgoStopping = CP.getVEgoStopping();

    float currentDelayStock = params.getFloat("SteerDelayStock");
    float currentFrictionStock = params.getFloat("SteerFrictionStock");
    float currentKPStock = params.getFloat("SteerKPStock");
    float currentLatAccelStock = params.getFloat("SteerLatAccelStock");
    float currentLongDelayStock = params.getFloat("LongitudinalActuatorDelayStock");
    float currentStartAccelStock = params.getFloat("StartAccelStock");
    float currentSteerRatioStock = params.getFloat("SteerRatioStock");
    float currentStopAccelStock = params.getFloat("StopAccelStock");
    float currentStoppingDecelRateStock = params.getFloat("StoppingDecelRateStock");
    float currentVEgoStartingStock = params.getFloat("VEgoStartingStock");
    float currentVEgoStoppingStock = params.getFloat("VEgoStoppingStock");

    if (currentDelayStock != steerActuatorDelay && steerActuatorDelay != 0) {
      if (params.getFloat("SteerDelay") == currentDelayStock || currentDelayStock == 0) {
        params.putFloatNonBlocking("SteerDelay", steerActuatorDelay);
      }
      params.putFloatNonBlocking("SteerDelayStock", steerActuatorDelay);
    }

    if (currentFrictionStock != friction && friction != 0) {
      if (params.getFloat("SteerFriction") == currentFrictionStock || currentFrictionStock == 0) {
        params.putFloatNonBlocking("SteerFriction", friction);
      }
      params.putFloatNonBlocking("SteerFrictionStock", friction);
    }

    if (currentKPStock != steerKp && steerKp != 0) {
      if (params.getFloat("SteerKP") == currentKPStock || currentKPStock == 0) {
        params.putFloatNonBlocking("SteerKP", steerKp);
      }
      params.putFloatNonBlocking("SteerKPStock", steerKp);
    }

    if (currentLatAccelStock != latAccelFactor && latAccelFactor != 0) {
      if (params.getFloat("SteerLatAccel") == currentLatAccelStock || currentLatAccelStock == 0) {
        params.putFloatNonBlocking("SteerLatAccel", latAccelFactor);
      }
      params.putFloatNonBlocking("SteerLatAccelStock", latAccelFactor);
    }

    if (currentLongDelayStock != longitudinalActuatorDelay && longitudinalActuatorDelay != 0) {
      if (params.getFloat("LongitudinalActuatorDelay") == currentLongDelayStock || currentLongDelayStock == 0) {
        params.putFloatNonBlocking("LongitudinalActuatorDelay", longitudinalActuatorDelay);
      }
      params.putFloatNonBlocking("LongitudinalActuatorDelayStock", longitudinalActuatorDelay);
    }

    if (currentStartAccelStock != startAccel && startAccel != 0) {
      if (params.getFloat("StartAccel") == currentStartAccelStock || currentStartAccelStock == 0) {
        params.putFloatNonBlocking("StartAccel", startAccel);
      }
      params.putFloatNonBlocking("StartAccelStock", startAccel);
    }

    if (currentSteerRatioStock != steerRatio && steerRatio != 0) {
      if (params.getFloat("SteerRatio") == currentSteerRatioStock || currentSteerRatioStock == 0) {
        params.putFloatNonBlocking("SteerRatio", steerRatio);
      }
      params.putFloatNonBlocking("SteerRatioStock", steerRatio);
    }

    if (currentStopAccelStock != stopAccel && stopAccel != 0) {
      if (params.getFloat("StopAccel") == currentStopAccelStock || currentStopAccelStock == 0) {
        params.putFloatNonBlocking("StopAccel", stopAccel);
      }
      params.putFloatNonBlocking("StopAccelStock", stopAccel);
    }

    if (currentStoppingDecelRateStock != stoppingDecelRate && stoppingDecelRate != 0) {
      if (params.getFloat("StoppingDecelRate") == currentStoppingDecelRateStock || currentStoppingDecelRateStock == 0) {
        params.putFloatNonBlocking("StoppingDecelRate", stoppingDecelRate);
      }
      params.putFloatNonBlocking("StoppingDecelRateStock", stoppingDecelRate);
    }

    if (currentVEgoStartingStock != vEgoStarting && vEgoStarting != 0) {
      if (params.getFloat("VEgoStarting") == currentVEgoStartingStock || currentVEgoStartingStock == 0) {
        params.putFloatNonBlocking("VEgoStarting", vEgoStarting);
      }
      params.putFloatNonBlocking("VEgoStartingStock", vEgoStarting);
    }

    if (currentVEgoStoppingStock != vEgoStopping && vEgoStopping != 0) {
      if (params.getFloat("VEgoStopping") == currentVEgoStoppingStock || currentVEgoStoppingStock == 0) {
        params.putFloatNonBlocking("VEgoStopping", vEgoStopping);
      }
      params.putFloatNonBlocking("VEgoStoppingStock", vEgoStopping);
    }

    if (Hardware::PC() && (carMake == "mock" || carFingerprint == "MOCK")) {
      applyDesktopVehicleFallback();
    }
  } else if (Hardware::PC()) {
    applyDesktopVehicleFallback();
  }

  std::string starpilotCarParams = params.get("StarPilotCarParamsPersistent");
  if (!starpilotCarParams.empty()) {
    AlignedBuffer aligned_buf;
    capnp::FlatArrayMessageReader fpcmsg(aligned_buf.align(starpilotCarParams.data(), starpilotCarParams.size()));
    cereal::StarPilotCarParams::Reader FPCP = fpcmsg.getRoot<cereal::StarPilotCarParams>();

    canUsePedal = FPCP.getCanUsePedal();
    canUseSDSU = FPCP.getCanUseSDSU();
    openpilotLongitudinalControlDisabled = FPCP.getOpenpilotLongitudinalControlDisabled();
  }

  std::string liveTorqueParameters = params.get("LiveTorqueParameters");
  if (!liveTorqueParameters.empty()) {
    AlignedBuffer aligned_buf;
    capnp::FlatArrayMessageReader reader(aligned_buf.align(liveTorqueParameters.data(), liveTorqueParameters.size()));
    cereal::Event::Reader event = reader.getRoot<cereal::Event>();
    cereal::LiveTorqueParametersData::Reader LTP = event.getLiveTorqueParameters();

    hasAutoTune = LTP.getUseParams();
  }

  drivingPanelButtons->setVisibleButton(0, showAllToggles || tuningLevel >= starpilotToggleLevels.value("DrivingModel").toDouble());
  drivingPanelButtons->setVisibleButton(1, showAllToggles || hasOpenpilotLongitudinal);

  systemPanelButtons->setVisibleButton(1, showAllToggles || tuningLevel >= starpilotToggleLevels.value("DeviceManagement").toDouble() || tuningLevel >= starpilotToggleLevels.value("ScreenManagement").toDouble());

  vehiclePanelButtons->setVisibleButton(1, showAllToggles || tuningLevel >= starpilotToggleLevels.value("WheelControls").toDouble());

  update();
}
