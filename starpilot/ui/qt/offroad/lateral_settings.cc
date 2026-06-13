#include "starpilot/ui/qt/offroad/lateral_settings.h"

StarPilotLateralPanel::StarPilotLateralPanel(StarPilotSettingsWindow *parent, bool forceOpen) : StarPilotListWidget(parent), parent(parent) {
  forceOpenDescriptions = forceOpen;

  QStackedLayout *lateralLayout = new QStackedLayout();
  addItem(lateralLayout);

  StarPilotListWidget *lateralList = new StarPilotListWidget(this);

  ScrollView *lateralPanel = new ScrollView(lateralList, this);

  lateralLayout->addWidget(lateralPanel);

  StarPilotListWidget *advancedLateralTuneList = new StarPilotListWidget(this);
  StarPilotListWidget *aolList = new StarPilotListWidget(this);
  StarPilotListWidget *laneChangeList = new StarPilotListWidget(this);
  StarPilotListWidget *lateralTuneList = new StarPilotListWidget(this);
  StarPilotListWidget *qolList = new StarPilotListWidget(this);

  ScrollView *advancedLateralTunePanel = new ScrollView(advancedLateralTuneList, this);
  ScrollView *aolPanel = new ScrollView(aolList, this);
  ScrollView *laneChangePanel = new ScrollView(laneChangeList, this);
  ScrollView *lateralTunePanel = new ScrollView(lateralTuneList, this);
  ScrollView *qolPanel = new ScrollView(qolList, this);

  lateralLayout->addWidget(advancedLateralTunePanel);
  lateralLayout->addWidget(aolPanel);
  lateralLayout->addWidget(laneChangePanel);
  lateralLayout->addWidget(lateralTunePanel);
  lateralLayout->addWidget(qolPanel);

  const std::vector<std::tuple<QString, QString, QString, QString>> lateralToggles {
    {"AdvancedLateralTune", tr("Advanced Lateral Tuning"), tr("<b>Advanced steering control changes to fine-tune how openpilot drives.</b>"), "../../starpilot/assets/toggle_icons/icon_advanced_lateral_tune.png"},
    {"SteerDelay", parent->steerActuatorDelay != 0 ? QString(tr("Actuator Delay (Default: %1)")).arg(QString::number(parent->steerActuatorDelay, 'f', 2)) : tr("Actuator Delay"), tr("<b>The time between openpilot's steering command and the vehicle's response.</b> Increase if the vehicle reacts late; decrease if it feels jumpy. Auto-learned by default."), ""},
    {"SteerFriction", parent->friction != 0 ? QString(tr("Friction (Default: %1)")).arg(QString::number(parent->friction, 'f', 2)) : tr("Friction"), tr("<b>Compensates for steering friction.</b> Increase if the wheel sticks near center; decrease if it jitters. Auto-learned by default."), ""},
    {"SteerKP", parent->steerKp != 0 ? QString(tr("Kp Factor (Default: %1)")).arg(QString::number(parent->steerKp, 'f', 2)) : tr("Kp Factor"), tr("<b>How strongly openpilot corrects lane position.</b> Higher is tighter but twitchier; lower is smoother but slower. Auto-learned by default."), ""},
    {"SteerLatAccel", parent->latAccelFactor != 0 ? QString(tr("Lateral Acceleration (Default: %1)")).arg(QString::number(parent->latAccelFactor, 'f', 2)) : tr("Lateral Acceleration"), tr("<b>Maps steering torque to turning response.</b> Increase for sharper turns; decrease for gentler steering. Auto-learned by default."), ""},
    {"SteerRatio", parent->steerRatio != 0 ? QString(tr("Steer Ratio (Default: %1)")).arg(QString::number(parent->steerRatio, 'f', 2)) : tr("Steer Ratio"), tr("<b>The relationship between steering wheel rotation and road wheel angle.</b> Increase if steering feels too quick or twitchy; decrease if it feels too slow or weak. Auto-learned by default."), ""},
    {"ForceAutoTune", tr("Force Auto-Tune On"), tr("<b>Force-enable openpilot's live auto-tuning for \"Friction\" and \"Lateral Acceleration\".</b>"), ""},
    {"ForceAutoTuneOff", tr("Force Auto-Tune Off"), tr("<b>Force-disable openpilot's live auto-tuning for \"Friction\" and \"Lateral Acceleration\" and use the set value instead.</b>"), ""},
    {"ForceTorqueController", tr("Force Torque Controller"), tr("<b>Use torque-based steering control instead of angle-based control for smoother lane keeping, especially in curves.</b>"), ""},

    {"AlwaysOnLateral", tr("Always On Lateral"), tr("<b>openpilot's steering remains active even when the accelerator or brake pedals are pressed.</b>"), "../../starpilot/assets/toggle_icons/icon_always_on_lateral.png"},
    {"PauseAOLOnBrake", tr("Pause on Brake Press Below"), tr("<b>Pause \"Always On Lateral\" below the set speed while the brake pedal is pressed.</b>"), ""},

    {"LaneChanges", tr("Lane Changes"), tr("<b>Allow openpilot to change lanes.</b>"), "../../starpilot/assets/toggle_icons/icon_lane.png"},
    {"NudgelessLaneChange", tr("Automatic Lane Changes"), tr("<b>When the turn signal is on, openpilot will automatically change lanes.</b> No steering-wheel nudge required!"), ""},
    {"LaneChangeTime", tr("Lane Change Delay"), tr("<b>Delay between turn signal activation and the start of an automatic lane change.</b>"), ""},
    {"MinimumLaneChangeSpeed", tr("Minimum Lane Change Speed"), tr("<b>Lowest speed at which openpilot will change lanes.</b>"), ""},
    {"LaneDetectionWidth", tr("Minimum Lane Width"), tr("<b>Prevent automatic lane changes into lanes narrower than the set width.</b>"), ""},
    {"OneLaneChange", tr("One Lane Change Per Signal"), tr("<b>Limit automatic lane changes to one per turn-signal activation.</b>"), ""},
    {"LaneChangeSmoothing", tr("Lane Change Smoothing"), tr("<b>Controls how smoothly openpilot commits to a lane change.</b> 10 is stock behavior; lower values produce a gentler, more gradual maneuver. 1 stretches the maneuver to ~8 seconds."), ""},

    {"LateralTune", tr("Lateral Tuning"), tr("<b>Miscellaneous steering control changes</b> to fine-tune how openpilot drives."), "../../starpilot/assets/toggle_icons/icon_lateral_tune.png"},
    {"TurnDesires", tr("Force Turn Desires Below Lane Change Speed"), tr("<b>While driving below the minimum lane change speed with an active turn signal, instruct openpilot to turn left/right.</b>"), ""},
    {"NavDesiresAllowed", tr("Use Route Desires"), tr("<b>Allow an active navigation route to request keep-left, keep-right, and low-speed turn desires.</b>"), ""},
    {"NNFF", tr("Neural Network Feedforward (NNFF)"), tr("<b>Twilsonco's \"Neural Network FeedForward\" controller.</b> Uses a trained neural network model to predict steering torque based on vehicle speed, roll, and past/future planned path data for smoother, model-based steering."), ""},
    {"NNFFLite", tr("Neural Network Feedforward (NNFF) Lite"), tr("<b>A lightweight version of Twilsonco's \"Neural Network FeedForward\" controller.</b> Uses the \"look-ahead\" planned lateral jerk logic from the full model to help smoothen steering adjustments in curves, but does not use the full neural network for torque calculation."), ""},

    {"QOLLateral", tr("Quality of Life"), tr("<b>Steering control changes to fine-tune how openpilot drives.</b>"), "../../starpilot/assets/toggle_icons/icon_quality_of_life.png"},
    {"PauseLateralSpeed", tr("Pause Steering Below"), tr("<b>Pause steering below the set speed.</b>"), ""},
    {"LateralResumeDelay", tr("Lateral Resume Delay"), tr("<b>Delay before lateral control resumes after the turn signal is turned off.</b> Only applies when the vehicle speed dropped below half the \"Pause Steering Below\" speed during the turn signal. Set to 0 to disable."), ""}
  };

  for (const auto &[param, title, desc, icon] : lateralToggles) {
    AbstractControl *lateralToggle;

    if (param == "AdvancedLateralTune") {
      StarPilotManageControl *advancedLateralTuneToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(advancedLateralTuneToggle, &StarPilotManageControl::manageButtonClicked, [lateralLayout, advancedLateralTunePanel]() {
        lateralLayout->setCurrentWidget(advancedLateralTunePanel);
      });
      lateralToggle = advancedLateralTuneToggle;
    } else if (param == "SteerDelay") {
      std::vector<QString> steerDelayButton{"Reset"};
      lateralToggle = new StarPilotParamValueButtonControl(param, title, desc, icon, 0.01, 1, QString(), std::map<float, QString>(), 0.01, false, {}, steerDelayButton, false, false);
    } else if (param == "SteerFriction") {
      std::vector<QString> steerFrictionButton{"Reset"};
      lateralToggle = new StarPilotParamValueButtonControl(param, title, desc, icon, 0, 1, QString(), std::map<float, QString>(), 0.01, false, {}, steerFrictionButton, false, false);
    } else if (param == "SteerKP") {
      std::vector<QString> steerKPButton{"Reset"};
      lateralToggle = new StarPilotParamValueButtonControl(param, title, desc, icon, parent->steerKp * 0.5, parent->steerKp * 1.5, QString(), std::map<float, QString>(), 0.01, false, {}, steerKPButton, false, false);
    } else if (param == "SteerLatAccel") {
      std::vector<QString> steerLatAccelButton{"Reset"};
      lateralToggle = new StarPilotParamValueButtonControl(param, title, desc, icon, parent->latAccelFactor * 0.5, parent->latAccelFactor * 1.5, QString(), std::map<float, QString>(), 0.01, false, {}, steerLatAccelButton, false, false);
    } else if (param == "SteerRatio") {
      std::vector<QString> steerRatioButton{"Reset"};
      lateralToggle = new StarPilotParamValueButtonControl(param, title, desc, icon, parent->steerRatio * 0.5, parent->steerRatio * 1.5, QString(), std::map<float, QString>(), 0.01, false, {}, steerRatioButton, false, false);

    } else if (param == "AlwaysOnLateral") {
      StarPilotManageControl *aolToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(aolToggle, &StarPilotManageControl::manageButtonClicked, [lateralLayout, aolPanel]() {
        lateralLayout->setCurrentWidget(aolPanel);
      });
      lateralToggle = aolToggle;
    } else if (param == "PauseAOLOnBrake") {
      lateralToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 99, QString(), std::map<float, QString>(), 1, true);

    } else if (param == "LaneChanges") {
      StarPilotManageControl *laneChangeToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(laneChangeToggle, &StarPilotManageControl::manageButtonClicked, [lateralLayout, laneChangePanel]() {
        lateralLayout->setCurrentWidget(laneChangePanel);
      });
      lateralToggle = laneChangeToggle;
    } else if (param == "LaneChangeTime") {
      std::map<float, QString> laneChangeTimeLabels;
      for (float i = 0; i <= 5; i += 0.1) {
        laneChangeTimeLabels[i] = i == 0 ? tr("Instant") : std::lround(i / 0.1) == 1 / 0.1 ? QString::number(i, 'f', 1) + tr(" second") : QString::number(i, 'f', 1) + tr(" seconds");
      }
      lateralToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 5, QString(), laneChangeTimeLabels, 0.1);
    } else if (param == "LaneDetectionWidth") {
      lateralToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 15, QString(), std::map<float, QString>(), 0.1, true);
    } else if (param == "MinimumLaneChangeSpeed") {
      lateralToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 99, QString(), std::map<float, QString>(), 1, true);
    } else if (param == "LaneChangeSmoothing") {
      std::map<float, QString> smoothingLabels;
      smoothingLabels[10] = tr("Stock");
      smoothingLabels[1] = tr("Smoothest");
      lateralToggle = new StarPilotParamValueControl(param, title, desc, icon, 1, 10, QString(), smoothingLabels, 1);

    } else if (param == "LateralTune") {
      StarPilotManageControl *lateralTuneToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(lateralTuneToggle, &StarPilotManageControl::manageButtonClicked, [lateralLayout, lateralTunePanel]() {
        lateralLayout->setCurrentWidget(lateralTunePanel);
      });
      lateralToggle = lateralTuneToggle;

    } else if (param == "QOLLateral") {
      StarPilotManageControl *qolLateralToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(qolLateralToggle, &StarPilotManageControl::manageButtonClicked, [lateralLayout, qolPanel]() {
        lateralLayout->setCurrentWidget(qolPanel);
      });
      lateralToggle = qolLateralToggle;
    } else if (param == "PauseLateralSpeed") {
      std::vector<QString> pauseLateralToggles{"PauseLateralOnSignal"};
      std::vector<QString> pauseLateralToggleNames{tr("Turn Signal Only")};
      lateralToggle = new StarPilotParamValueButtonControl(param, title, desc, icon, 0, 99, QString(), std::map<float, QString>(), 1, true, pauseLateralToggles, pauseLateralToggleNames, true);

    } else if (param == "LateralResumeDelay") {
      std::map<float, QString> delayLabels;
      for (int i = 0; i <= 50; ++i) {
        float key = i / 10.0f;
        delayLabels[key] = key == 0.0f ? tr("Off") : QString::number(key, 'f', 1) + tr(" s");
      }
      lateralToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 5, QString(), delayLabels, 0.1);

    } else {
      lateralToggle = new ParamControl(param, title, desc, icon);
    }

    toggles[param] = lateralToggle;

    if (advancedLateralTuneKeys.contains(param)) {
      advancedLateralTuneList->addItem(lateralToggle);
    } else if (aolKeys.contains(param)) {
      aolList->addItem(lateralToggle);
    } else if (laneChangeKeys.contains(param)) {
      laneChangeList->addItem(lateralToggle);
    } else if (lateralTuneKeys.contains(param)) {
      lateralTuneList->addItem(lateralToggle);
    } else if (qolKeys.contains(param)) {
      qolList ->addItem(lateralToggle);
    } else {
      lateralList->addItem(lateralToggle);

      parentKeys.insert(param);
    }

    if (StarPilotManageControl *frogPilotManageToggle = qobject_cast<StarPilotManageControl*>(lateralToggle)) {
      QObject::connect(frogPilotManageToggle, &StarPilotManageControl::manageButtonClicked, [this]() {
        emit openSubPanel();
        openDescriptions(forceOpenDescriptions, toggles);
      });
    }

    QObject::connect(lateralToggle, &AbstractControl::hideDescriptionEvent, [this]() {
      update();
    });
    QObject::connect(lateralToggle, &AbstractControl::showDescriptionEvent, [this]() {
      update();
    });
  }

  QSet<QString> forceUpdateKeys = {"ForceAutoTune", "ForceAutoTuneOff", "LateralTune", "NNFF", "NudgelessLaneChange"};
  for (const QString &key : forceUpdateKeys) {
    QObject::connect(static_cast<ToggleControl*>(toggles[key]), &ToggleControl::toggleFlipped, this, &StarPilotLateralPanel::updateToggles);
  }

  QSet<QString> rebootKeys = {"AlwaysOnLateral", "ForceTorqueController", "NNFF", "NNFFLite"};
  for (const QString &key : rebootKeys) {
    QObject::connect(static_cast<ToggleControl*>(toggles[key]), &ToggleControl::toggleFlipped, [key, this](bool state) {
      if (started) {
        if (key == "AlwaysOnLateral" && state) {
          if (StarPilotConfirmationDialog::toggleReboot(this)) {
            Hardware::reboot();
          }
        } else if (key != "AlwaysOnLateral") {
          if (StarPilotConfirmationDialog::toggleReboot(this)) {
            Hardware::reboot();
          }
        }
      }
    });
  }

  steerDelayToggle = static_cast<StarPilotParamValueButtonControl*>(toggles["SteerDelay"]);
  QObject::connect(steerDelayToggle, &StarPilotParamValueButtonControl::buttonClicked, [parent, this]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Reset <b>Actuator Delay</b> to its default value?"), this)) {
      params.putFloat("SteerDelay", parent->steerActuatorDelay);
      steerDelayToggle->refresh();
    }
  });

  steerFrictionToggle = static_cast<StarPilotParamValueButtonControl*>(toggles["SteerFriction"]);
  QObject::connect(steerFrictionToggle, &StarPilotParamValueButtonControl::buttonClicked, [parent, this]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Reset <b>Friction</b> to its default value?"), this)) {
      params.putFloat("SteerFriction", parent->friction);
      steerFrictionToggle->refresh();
    }
  });

  steerKPToggle = static_cast<StarPilotParamValueButtonControl*>(toggles["SteerKP"]);
  QObject::connect(steerKPToggle, &StarPilotParamValueButtonControl::buttonClicked, [parent, this]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Reset <b>Kp Factor</b> to its default value?"), this)) {
      params.putFloat("SteerKP", parent->steerKp);
      steerKPToggle->refresh();
    }
  });

  steerLatAccelToggle = static_cast<StarPilotParamValueButtonControl*>(toggles["SteerLatAccel"]);
  QObject::connect(steerLatAccelToggle, &StarPilotParamValueButtonControl::buttonClicked, [parent, this]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Reset <b>Lateral Accel</b> to its default value?"), this)) {
      params.putFloat("SteerLatAccel", parent->latAccelFactor);
      steerLatAccelToggle->refresh();
    }
  });

  steerRatioToggle = static_cast<StarPilotParamValueButtonControl*>(toggles["SteerRatio"]);
  QObject::connect(steerRatioToggle, &StarPilotParamValueButtonControl::buttonClicked, [parent, this]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Reset <b>Steer Ratio</b> to its default value?"), this)) {
      params.putFloat("SteerRatio", parent->steerRatio);
      steerRatioToggle->refresh();
    }
  });

  openDescriptions(forceOpenDescriptions, toggles);

  QObject::connect(parent, &StarPilotSettingsWindow::closeSubPanel, [lateralLayout, lateralPanel, this] {
    openDescriptions(forceOpenDescriptions, toggles);
    lateralLayout->setCurrentWidget(lateralPanel);
  });
  QObject::connect(parent, &StarPilotSettingsWindow::updateMetric, this, &StarPilotLateralPanel::updateMetric);
  QObject::connect(uiState(), &UIState::uiUpdate, this, &StarPilotLateralPanel::updateState);
}

void StarPilotLateralPanel::showEvent(QShowEvent *event) {
  steerDelayToggle->setTitle(QString(tr("Actuator Delay (Default: %1)")).arg(QString::number(parent->steerActuatorDelay, 'f', 2)));
  steerFrictionToggle->setTitle(QString(tr("Friction (Default: %1)")).arg(QString::number(parent->friction, 'f', 2)));
  steerKPToggle->setTitle(QString(tr("Kp Factor (Default: %1)")).arg(QString::number(parent->steerKp, 'f', 2)));
  steerKPToggle->updateControl(parent->steerKp * 0.5, parent->steerKp * 1.5);
  steerLatAccelToggle->setTitle(QString(tr("Lateral Accel (Default: %1)")).arg(QString::number(parent->latAccelFactor, 'f', 2)));
  steerLatAccelToggle->updateControl(parent->latAccelFactor * 0.5, parent->latAccelFactor * 1.5);
  steerRatioToggle->setTitle(QString(tr("Steer Ratio (Default: %1)")).arg(QString::number(parent->steerRatio, 'f', 2)));
  steerRatioToggle->updateControl(parent->steerRatio * 0.5, parent->steerRatio * 1.5);

  updateToggles();
}

void StarPilotLateralPanel::updateState(const UIState &s) {
  if (!isVisible()) return;

  started = s.scene.started;
}

void StarPilotLateralPanel::updateMetric(bool metric, bool bootRun) {
  static bool previousMetric;
  if (metric != previousMetric && !bootRun) {
    double distanceConversion = metric ? FOOT_TO_METER : METER_TO_FOOT;
    double speedConversion = metric ? MILE_TO_KM : KM_TO_MILE;

    params.putFloatNonBlocking("LaneDetectionWidth", params.getFloat("LaneDetectionWidth") * distanceConversion);

    params.putIntNonBlocking("MinimumLaneChangeSpeed", params.getInt("MinimumLaneChangeSpeed") * speedConversion);
    params.putIntNonBlocking("PauseAOLOnBrake", params.getInt("PauseAOLOnBrake") * speedConversion);
    params.putIntNonBlocking("PauseLateralSpeed", params.getInt("PauseLateralSpeed") * speedConversion);
  }
  previousMetric = metric;

  static std::map<float, QString> imperialDistanceLabels;
  static std::map<float, QString> imperialSpeedLabels;
  static std::map<float, QString> metricDistanceLabels;
  static std::map<float, QString> metricSpeedLabels;

  static bool labelsInitialized = false;
  if (!labelsInitialized) {
    for (int i = 0; i <= 150; ++i) {
      float key = i / 10.0f;
      imperialDistanceLabels[key] = key == 0 ? tr("Off") : i == 1 ? QString::number(i) + tr(" foot") : QString::number(key, 'f', 1) + tr(" feet");
    }

    for (int i = 0; i <= 99; ++i) {
      imperialSpeedLabels[i] = i == 0 ? tr("Off") : QString::number(i) + tr(" mph");
    }

    for (int i = 0; i <= 50; ++i) {
      float key = i / 10.0f;
      metricDistanceLabels[key] = key == 0 ? tr("Off") : i == 1 ? QString::number(i) + tr(" meter") : QString::number(key, 'f', 1) + tr(" meters");
    }

    for (int i = 0; i <= 150; ++i) {
      metricSpeedLabels[i] = i == 0 ? tr("Off") : QString::number(i) + tr(" km/h");
    }

    labelsInitialized = true;
  }

  StarPilotParamValueControl *laneWidthToggle = static_cast<StarPilotParamValueControl*>(toggles["LaneDetectionWidth"]);
  StarPilotParamValueControl *minimumLaneChangeSpeedToggle = static_cast<StarPilotParamValueControl*>(toggles["MinimumLaneChangeSpeed"]);
  StarPilotParamValueControl *pauseAOLOnBrakeToggle = static_cast<StarPilotParamValueControl*>(toggles["PauseAOLOnBrake"]);
  StarPilotParamValueControl *pauseLateralToggle = static_cast<StarPilotParamValueControl*>(toggles["PauseLateralSpeed"]);

  if (metric) {
    laneWidthToggle->updateControl(0, 5, metricDistanceLabels);

    minimumLaneChangeSpeedToggle->updateControl(0, 150, metricSpeedLabels);
    pauseAOLOnBrakeToggle->updateControl(0, 150, metricSpeedLabels);
    pauseLateralToggle->updateControl(0, 150, metricSpeedLabels);
  } else {
    laneWidthToggle->updateControl(0, 15, imperialDistanceLabels);

    minimumLaneChangeSpeedToggle->updateControl(0, 99, imperialSpeedLabels);
    pauseAOLOnBrakeToggle->updateControl(0, 99, imperialSpeedLabels);
    pauseLateralToggle->updateControl(0, 99, imperialSpeedLabels);
  }
}

void StarPilotLateralPanel::updateToggles() {
  const bool showAllToggles = parent->showAllTogglesEnabled();

  for (auto &[key, toggle] : toggles) {
    if (parentKeys.contains(key)) {
      toggle->setVisible(showAllToggles);
    }
  }

  bool forcingAutoTune = !parent->hasAutoTune && params.getBool("ForceAutoTune");
  bool forcingAutoTuneOff = parent->hasAutoTune && params.getBool("ForceAutoTuneOff");
  bool forcingTorqueController = !parent->isAngleCar && params.getBool("ForceTorqueController");
  bool usingNNFF = parent->hasNNFFLog && params.getBool("LateralTune") && params.getBool("NNFF");

  for (auto &[key, toggle] : toggles) {
    if (parentKeys.contains(key)) {
      continue;
    }

    bool setVisible = showAllToggles || parent->tuningLevel >= parent->starpilotToggleLevels[key].toDouble();

    if (!showAllToggles) {
      if (key == "ForceAutoTune") {
        setVisible &= !parent->hasAutoTune;
        setVisible &= !parent->isAngleCar;
        setVisible &= parent->isTorqueCar || forcingTorqueController || usingNNFF;
      }

      else if (key == "ForceAutoTuneOff") {
        setVisible &= parent->hasAutoTune;
      }

      else if (key == "ForceTorqueController") {
        setVisible &= !parent->isAngleCar;
        setVisible &= !parent->isTorqueCar;
      }

      else if (key == "LaneChangeTime") {
        setVisible &= params.getBool("LaneChanges") && params.getBool("NudgelessLaneChange");
      }

      else if (key == "LaneDetectionWidth") {
        setVisible &= params.getBool("LaneChanges") && params.getBool("NudgelessLaneChange");
      }

      else if (key == "LateralResumeDelay") {
        setVisible &= params.getBool("PauseLateralOnSignal");
      }

      else if (key == "NNFF") {
        setVisible &= parent->hasNNFFLog;
        setVisible &= !parent->isAngleCar;
      }

      else if (key == "NNFFLite") {
        setVisible &= !usingNNFF;
        setVisible &= !parent->isAngleCar;
      }

      else if (key == "SteerDelay") {
        setVisible &= parent->steerActuatorDelay != 0;
      }

      else if (key == "SteerFriction") {
        setVisible &= parent->friction != 0;
        setVisible &= parent->hasAutoTune ? forcingAutoTuneOff : !forcingAutoTune;
        setVisible &= parent->isTorqueCar || forcingTorqueController || usingNNFF;
        setVisible &= !usingNNFF;
      }

      else if (key == "SteerKP") {
        setVisible &= parent->steerKp != 0;
        setVisible &= parent->isTorqueCar || forcingTorqueController || usingNNFF;
        setVisible &= !parent->isAngleCar;
      }

      else if (key == "SteerLatAccel") {
        setVisible &= parent->latAccelFactor != 0;
        setVisible &= parent->hasAutoTune ? forcingAutoTuneOff : !forcingAutoTune;
        setVisible &= parent->isTorqueCar || forcingTorqueController || usingNNFF;
        setVisible &= !usingNNFF;
      }

      else if (key == "SteerRatio") {
        setVisible &= parent->steerRatio != 0;
        setVisible &= parent->hasAutoTune ? forcingAutoTuneOff : !forcingAutoTune;
      }
    }

    toggle->setVisible(setVisible);

    if (setVisible) {
      if (advancedLateralTuneKeys.contains(key)) {
        toggles["AdvancedLateralTune"]->setVisible(true);
      } else if (aolKeys.contains(key)) {
        toggles["AlwaysOnLateral"]->setVisible(true);
      } else if (laneChangeKeys.contains(key)) {
        toggles["LaneChanges"]->setVisible(true);
      } else if (lateralTuneKeys.contains(key)) {
        toggles["LateralTune"]->setVisible(true);
      } else if (qolKeys.contains(key)) {
        toggles["QOLLateral"]->setVisible(true);
      }
    }
  }

  openDescriptions(forceOpenDescriptions, toggles);

  update();
}
