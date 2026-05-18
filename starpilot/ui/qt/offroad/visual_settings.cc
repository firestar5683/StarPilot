#include "starpilot/ui/qt/offroad/visual_settings.h"

StarPilotVisualsPanel::StarPilotVisualsPanel(StarPilotSettingsWindow *parent, bool forceOpen) : StarPilotListWidget(parent), parent(parent) {
  forceOpenDescriptions = forceOpen;

  QStackedLayout *visualsLayout = new QStackedLayout();
  addItem(visualsLayout);

  StarPilotListWidget *visualsList = new StarPilotListWidget(this);

  ScrollView *visualsPanel = new ScrollView(visualsList, this);

  visualsLayout->addWidget(visualsPanel);

  StarPilotListWidget *advancedCustomList = new StarPilotListWidget(this);
  StarPilotListWidget *customUIList = new StarPilotListWidget(this);
  StarPilotListWidget *modelUIList = new StarPilotListWidget(this);
  StarPilotListWidget *navigationUIList = new StarPilotListWidget(this);
  StarPilotListWidget *qualityOfLifeList = new StarPilotListWidget(this);

  ScrollView *advancedCustomPanel = new ScrollView(advancedCustomList, this);
  ScrollView *customUIPanel = new ScrollView(customUIList, this);
  ScrollView *modelUIPanel = new ScrollView(modelUIList, this);
  ScrollView *navigationUIPanel = new ScrollView(navigationUIList, this);
  ScrollView *qualityOfLifePanel = new ScrollView(qualityOfLifeList, this);

  visualsLayout->addWidget(advancedCustomPanel);
  visualsLayout->addWidget(customUIPanel);
  visualsLayout->addWidget(modelUIPanel);
  visualsLayout->addWidget(navigationUIPanel);
  visualsLayout->addWidget(qualityOfLifePanel);

  const std::vector<std::tuple<QString, QString, QString, QString>> visualToggles {
    {"AdvancedCustomUI", tr("Advanced UI Controls"), tr("<b>Advanced visual changes</b> to fine-tune how the driving screen looks."), "../../starpilot/assets/toggle_icons/icon_advanced_device.png"},
    {"HideSpeed", tr("Hide Current Speed"), tr("<b>Hide the current speed</b> from the driving screen."), ""},
    {"HideLeadMarker", tr("Hide Lead Marker"), tr("<b>Hide the lead-vehicle marker</b> from the driving screen."), ""},
    {"HideMaxSpeed", tr("Hide Max Speed"), tr("<b>Hide the max speed</b> from the driving screen."), ""},
    {"HideAlerts", tr("Hide Non-Critical Alerts"), tr("<b>Hide non-critical alerts</b> from the driving screen."), ""},
    {"HideChangingLanesBanner", tr("Hide Changing Lanes Banner"), tr("<b>Hide the 'Changing Lanes' banner</b> from the driving screen."), ""},
    {"HideDistanceProfileBanner", tr("Hide Distance Profile Banner"), tr("<b>Hide the driving personality banner</b> when changing distance profiles."), ""},
    {"HideDMIcon", tr("Hide Driver Monitoring Icon"), tr("<b>Hide the driver monitoring icon</b> from the driving screen."), ""},
    {"HideTurningBanner", tr("Hide Turning Banner"), tr("<b>Hide the 'Turning Left/Right' banner</b> from the driving screen."), ""},
    {"HideSpeedLimit", tr("Hide Speed Limits"), tr("<b>Hide posted speed limits</b> from the driving screen."), ""},
    {"HideSteeringWheel", tr("Hide Steering Wheel"), tr("<b>Hide the steering-wheel button</b> from the top-right of the driving screen."), ""},
    {"WheelSpeed", tr("Use Wheel Speed"), tr("<b>Use the vehicle's wheel speed</b> instead of the cluster speed. This is purely a visual change and doesn't impact how openpilot drives!"), ""},

    {"CustomUI", tr("Driving Screen Widgets"), tr("<b>Custom StarPilot widgets</b> for the driving screen."), "../assets/icons/calibration.png"},
    {"AccelerationPath", tr("Acceleration Path"), tr("<b>Color the driving path by planned acceleration and braking.</b>"), ""},
    {"AdjacentPath", tr("Adjacent Lanes"), tr("<b>Show the driving paths for the left and right lanes.</b>"), ""},
    {"BlindSpotPath", tr("Blind Spot Path"), tr("<b>Show a red path when a vehicle is in that lane's blind spot.</b>"), ""},
    {"Compass", tr("Compass"), tr("<b>Show the current driving direction</b> with a simple on-screen compass."), ""},
    {"OnroadDistanceButton", tr("Driving Personality Button"), tr("<b>Control and view the current driving personality</b> via a driving screen widget."), ""},
    {"PedalsOnUI", tr("Gas / Brake Pedal Indicators"), tr("<b>On-screen gas and brake indicators.</b><br><br><b>Dynamic</b>: Opacity changes according to how much openpilot is accelerating or braking<br><b>Static</b>: Full when active, dim when not"), ""},
    {"RotatingWheel", tr("Rotating Steering Wheel"), tr("<b>Rotate the driving screen wheel</b> with the physical steering wheel."), ""},

    {"ModelUI", tr("Model UI"), tr("<b>Model visualizations</b> for the driving path, lane lines, path edges, and road edges."), "../../starpilot/assets/toggle_icons/icon_road.png"},
    {"DynamicPathWidth", tr("Dynamic Path Width"), tr("<b>Change the path width based on engagement.</b><br><br><b>Fully Engaged</b>: 100%<br><b>Always On Lateral</b>: 75%<br><b>Disengaged</b>: 50%"), ""},
    {"LaneLinesWidth", tr("Lane Lines Width"), tr("<b>Set the lane-line thickness.</b><br><br>Default matches the MUTCD lane-line width standard of 4 inches."), ""},
    {"PathEdgeWidth", tr("Path Edges Width"), tr("<b>Set the driving-path edge width</b> that represents different driving modes and statuses.<br><br>Default is 20% of the total path width.<br><br>Color Guide:<br><br>- <b>Light Blue</b>: Always On Lateral<br>- <b>Green</b>: Default<br>- <b>Orange</b>: Experimental Mode<br>- <b>Red</b>: Traffic Mode<br>- <b>Yellow</b>: Conditional Experimental Mode overridden"), ""},
    {"PathWidth", tr("Path Width"), tr("<b>Set the driving-path width.</b><br><br>Default (6.1 feet) matches the width of a 2019 Lexus ES 350."), ""},
    {"RoadEdgesWidth", tr("Road Edges Width"), tr("<b>Set the road-edge thickness.</b><br><br>Default matches half of the MUTCD lane-line width standard of 4 inches."), ""},

    {"NavigationUI", tr("Navigation Widgets"), tr("<b>Speed limits, and other navigation widgets.</b>"), "../../starpilot/assets/toggle_icons/icon_map.png"},
    {"RoadNameUI", tr("Road Name"), tr("<b>Display the road name at the bottom of the driving screen</b> using data from \"OpenStreetMap (OSM)\"."), ""},
    {"ShowSpeedLimits", tr("Show Speed Limits"), tr("<b>Show speed limits</b> in the top-left corner of the driving screen. Uses data from the car's dashboard (if supported) and \"OpenStreetMap (OSM)\"."), ""},
    {"SLCMapboxFiller", tr("Show Speed Limits from Mapbox"), tr("<b>Use Mapbox speed-limit data when no other source is available.</b>"), ""},
    {"UseVienna", tr("Use Vienna-Style Speed Signs"), tr("<b>Show Vienna-style (EU) speed-limit signs</b> instead of MUTCD (US)."), ""},

    {"QOLVisuals", tr("Quality of Life"), tr("<b>Miscellaneous visual changes</b> to fine-tune how the driving screen looks."), "../../starpilot/assets/toggle_icons/icon_quality_of_life.png"},
    {"CameraView", tr("Camera View"), tr("<b>Select the active camera view.</b> This is purely a visual change and doesn't impact how openpilot drives!"), ""},
    {"DriverCamera", tr("Show Driver Camera When In Reverse"), tr("<b>Show the driver camera feed</b> when the vehicle is in reverse."), ""},
    {"StoppedTimer", tr("Stopped Timer"), tr("<b>Show a timer when stopped</b> in place of the current speed to indicate how long the vehicle has been stopped."), ""},

    {"DisableWideRoad", tr("Disable Wide Road Camera"), QString("<b>%1</b><br><br>%2").arg(tr("Only enable this if the wide camera is broken or for development!")).arg(tr("<b>Disabling the wide camera may degrade driving performance and cause instability.</b><br><br>Requires a reboot to take effect.")), "../../starpilot/assets/toggle_icons/icon_advanced_device.png"}
  };

  for (const auto &[param, title, desc, icon] : visualToggles) {
    AbstractControl *visualToggle;

    if (param == "AdvancedCustomUI") {
      StarPilotManageControl *advancedCustomUIToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(advancedCustomUIToggle, &StarPilotManageControl::manageButtonClicked, [visualsLayout, advancedCustomPanel]() {
        visualsLayout->setCurrentWidget(advancedCustomPanel);
      });
      visualToggle = advancedCustomUIToggle;

    } else if (param == "CustomUI") {
      StarPilotManageControl *customUIToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(customUIToggle, &StarPilotManageControl::manageButtonClicked, [visualsLayout, customUIPanel]() {
        visualsLayout->setCurrentWidget(customUIPanel);
      });
      visualToggle = customUIToggle;
    } else if (param == "PedalsOnUI") {
      std::vector<QString> pedalsToggles{"DynamicPedalsOnUI", "StaticPedalsOnUI"};
      std::vector<QString> pedalsToggleNames{tr("Dynamic"), tr("Static")};
      StarPilotButtonToggleControl *pedalsToggle = new StarPilotButtonToggleControl(param, title, desc, icon, pedalsToggles, pedalsToggleNames, true);
      QObject::connect(pedalsToggle, &StarPilotButtonToggleControl::buttonClicked, [this](int id) {
        if (id == 0) {
          params.putBool("StaticPedalsOnUI", false);
        } else if (id == 1) {
          params.putBool("DynamicPedalsOnUI", false);
        }
      });
      visualToggle = pedalsToggle;

    } else if (param == "ModelUI") {
      StarPilotManageControl *modelUIToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(modelUIToggle, &StarPilotManageControl::manageButtonClicked, [visualsLayout, modelUIPanel]() {
        visualsLayout->setCurrentWidget(modelUIPanel);
      });
      visualToggle = modelUIToggle;
    } else if (param == "LaneLinesWidth" || param == "RoadEdgesWidth") {
      visualToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 24, tr(" inches"));
    } else if (param == "PathEdgeWidth") {
      std::map<float, QString> pathEdgeLabels;
      for (int i = 0; i <= 100; ++i) {
        pathEdgeLabels[i] = i == 0 ? tr("Off") : QString::number(i) + "%";
      }
      visualToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 100, QString(), pathEdgeLabels);
    } else if (param == "PathWidth") {
      visualToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 10, tr(" feet"), std::map<float, QString>(), 0.1);

    } else if (param == "NavigationUI") {
      StarPilotManageControl *navigationUIToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(navigationUIToggle, &StarPilotManageControl::manageButtonClicked, [visualsLayout, navigationUIPanel]() {
        visualsLayout->setCurrentWidget(navigationUIPanel);
      });
      visualToggle = navigationUIToggle;

    } else if (param == "QOLVisuals") {
      StarPilotManageControl *qolToggle = new StarPilotManageControl(param, title, desc, icon);
      QObject::connect(qolToggle, &StarPilotManageControl::manageButtonClicked, [visualsLayout, qualityOfLifePanel]() {
        visualsLayout->setCurrentWidget(qualityOfLifePanel);
      });
      visualToggle = qolToggle;
    } else if (param == "CameraView") {
      std::vector<QString> cameraOptions{tr("Auto"), tr("Driver"), tr("Standard"), tr("Wide")};
      ButtonParamControl *cameraSelection = new ButtonParamControl(param, title, desc, icon, cameraOptions);
      visualToggle = cameraSelection;

    } else {
      visualToggle = new ParamControl(param, title, desc, icon);
    }

    toggles[param] = visualToggle;

    if (advancedCustomOnroadUIKeys.contains(param)) {
      advancedCustomList->addItem(visualToggle);
    } else if (customOnroadUIKeys.contains(param)) {
      customUIList->addItem(visualToggle);
    } else if (modelUIKeys.contains(param)) {
      modelUIList->addItem(visualToggle);
    } else if (navigationUIKeys.contains(param)) {
      navigationUIList->addItem(visualToggle);
    } else if (qualityOfLifeKeys.contains(param)) {
      qualityOfLifeList->addItem(visualToggle);
    } else {
      visualsList->addItem(visualToggle);

      parentKeys.insert(param);
    }

    if (StarPilotManageControl *frogPilotManageToggle = qobject_cast<StarPilotManageControl*>(visualToggle)) {
      QObject::connect(frogPilotManageToggle, &StarPilotManageControl::manageButtonClicked, [this]() {
        emit openSubPanel();
        openDescriptions(forceOpenDescriptions, toggles);
      });
    }

    QObject::connect(visualToggle, &AbstractControl::hideDescriptionEvent, [this]() {
      update();
    });
    QObject::connect(visualToggle, &AbstractControl::showDescriptionEvent, [this]() {
      update();
    });
  }

  QSet<QString> forceUpdateKeys = {"HideLeadMarker", "ShowSpeedLimits"};
  for (const QString &key : forceUpdateKeys) {
    QObject::connect(static_cast<ToggleControl*>(toggles[key]), &ToggleControl::toggleFlipped, this, &StarPilotVisualsPanel::updateToggles);
  }

  static_cast<ParamControl*>(toggles["DisableWideRoad"])->setConfirmation(true, false);
  QObject::connect(static_cast<ToggleControl*>(toggles["DisableWideRoad"]), &ToggleControl::toggleFlipped, [this](bool state) {
    if (StarPilotConfirmationDialog::toggleReboot(this)) {
      Hardware::reboot();
    }
  });

  openDescriptions(forceOpenDescriptions, toggles);

  QObject::connect(parent, &StarPilotSettingsWindow::closeSubPanel, [visualsLayout, visualsPanel, this] {
    openDescriptions(forceOpenDescriptions, toggles);
    visualsLayout->setCurrentWidget(visualsPanel);
  });
  QObject::connect(parent, &StarPilotSettingsWindow::closeSubSubPanel, [this]() {
    openDescriptions(forceOpenDescriptions, toggles);
  });
  QObject::connect(parent, &StarPilotSettingsWindow::updateMetric, this, &StarPilotVisualsPanel::updateMetric);
}

void StarPilotVisualsPanel::showEvent(QShowEvent *event) {
  updateToggles();
}

void StarPilotVisualsPanel::updateMetric(bool metric, bool bootRun) {
  static bool previousMetric;
  if (metric != previousMetric && !bootRun) {
    double distanceConversion = metric ? FOOT_TO_METER : METER_TO_FOOT;
    double smallDistanceConversion = metric ? INCH_TO_CM : CM_TO_INCH;

    params.putIntNonBlocking("LaneLinesWidth", params.getInt("LaneLinesWidth") * smallDistanceConversion);
    params.putIntNonBlocking("RoadEdgesWidth", params.getInt("RoadEdgesWidth") * smallDistanceConversion);

    params.putFloatNonBlocking("PathWidth", params.getFloat("PathWidth") * distanceConversion);
  }
  previousMetric = metric;

  static std::map<float, QString> imperialDistanceLabels;
  static std::map<float, QString> imperialSmallDistanceLabels;
  static std::map<float, QString> metricDistanceLabels;
  static std::map<float, QString> metricSmallDistanceLabels;

  static bool labelsInitialized = false;
  if (!labelsInitialized) {
    for (int i = 0; i <= 10; ++i) {
      imperialDistanceLabels[i] = i == 0 ? tr("Off") : i == 1 ? QString::number(i) + tr(" foot") : QString::number(i) + tr(" feet");
    }

    for (int i = 0; i <= 24; ++i) {
      imperialSmallDistanceLabels[i] = i == 0 ? tr("Off") : i == 1 ? QString::number(i) + tr(" inch") : QString::number(i) + tr(" inches");
    }

    for (float i = 0.0f; i <= 3.0f; i += 0.1f) {
      metricDistanceLabels[i] = i == 0.0f ? tr("Off") : i == 1.0 ? QString::number(i) + tr(" meter") : QString::number(i, 'f', 1) + tr(" meters");
    }

    for (int i = 0; i <= 60; ++i) {
      metricSmallDistanceLabels[i] = i == 0 ? tr("Off") : i == 1 ? QString::number(i) + tr(" centimeter") : QString::number(i) + tr(" centimeters");
    }

    labelsInitialized = true;
  }

  StarPilotParamValueControl *laneLinesWidthToggle = static_cast<StarPilotParamValueControl*>(toggles["LaneLinesWidth"]);
  StarPilotParamValueControl *pathWidthToggle = static_cast<StarPilotParamValueControl*>(toggles["PathWidth"]);
  StarPilotParamValueControl *roadEdgesWidthToggle = static_cast<StarPilotParamValueControl*>(toggles["RoadEdgesWidth"]);

  if (metric) {
    laneLinesWidthToggle->setDescription(tr("<b>Set the lane-line thickness.</b><br><br>Default matches the MUTCD lane-line width standard of 10 centimeters."));
    pathWidthToggle->setDescription(tr("<b>Set the driving-path width.</b><br><br>Default (1.9 meters) matches the width of a 2019 Lexus ES 350."));
    roadEdgesWidthToggle->setDescription(tr("<b>Set the road-edge thickness.</b><br><br>Default matches half of the MUTCD lane-line width standard of 10 centimeters."));

    laneLinesWidthToggle->updateControl(0, 60, metricSmallDistanceLabels);
    roadEdgesWidthToggle->updateControl(0, 60, metricSmallDistanceLabels);

    pathWidthToggle->updateControl(0, 3, metricDistanceLabels);
  } else {
    laneLinesWidthToggle->setDescription(tr("<b>Set the lane-line thickness.</b><br><br>Default matches the MUTCD lane-line width standard of 4 inches."));
    pathWidthToggle->setDescription(tr("<b>Set the driving-path width.</b><br><br>Default (6.1 feet) matches the width of a 2019 Lexus ES 350."));
    roadEdgesWidthToggle->setDescription(tr("<b>Set the road-edge thickness.</b><br><br>Default matches half of the MUTCD lane-line width standard of 4 inches."));

    laneLinesWidthToggle->updateControl(0, 24, imperialSmallDistanceLabels);
    roadEdgesWidthToggle->updateControl(0, 24, imperialSmallDistanceLabels);

    pathWidthToggle->updateControl(0, 10, imperialDistanceLabels);
  }
}

void StarPilotVisualsPanel::updateToggles() {
  const bool showAllToggles = parent->showAllTogglesEnabled();

  for (auto &[key, toggle] : toggles) {
    if (parentKeys.contains(key)) {
      toggle->setVisible(showAllToggles);
    }
  }

  for (auto &[key, toggle] : toggles) {
    if (parentKeys.contains(key)) {
      continue;
    }

    bool setVisible = showAllToggles || parent->tuningLevel >= parent->starpilotToggleLevels[key].toDouble();

    if (!showAllToggles) {
      if (key == "AccelerationPath") {
        setVisible &= parent->hasOpenpilotLongitudinal;
      }

      else if (key == "BlindSpotPath") {
        setVisible &= parent->hasBSM;
      }

      else if (key == "HideLeadMarker") {
        setVisible &= parent->hasOpenpilotLongitudinal;
      }

      else if (key == "HideSpeedLimit") {
        setVisible &= parent->hasOpenpilotLongitudinal && params.getBool("SpeedLimitController");
      }

      else if (key == "OnroadDistanceButton") {
        setVisible &= parent->hasOpenpilotLongitudinal;
      }

      else if (key == "PedalsOnUI") {
        setVisible &= parent->hasOpenpilotLongitudinal;
      }

      else if (key == "ShowSpeedLimits") {
        setVisible &= !params.getBool("SpeedLimitController") || !parent->hasOpenpilotLongitudinal;
      }

      else if (key == "SLCMapboxFiller") {
        setVisible &= params.getBool("ShowSpeedLimits");
        setVisible &= !params.getBool("SpeedLimitController") || !parent->hasOpenpilotLongitudinal;
        setVisible &= !params.get("MapboxSecretKey").empty();
      }

      else if (key == "UseVienna") {
        setVisible &= params.getBool("ShowSpeedLimits") || params.getBool("SpeedLimitController");
      }
    }

    toggle->setVisible(setVisible);

    if (setVisible) {
      if (advancedCustomOnroadUIKeys.contains(key)) {
        toggles["AdvancedCustomUI"]->setVisible(true);
      } else if (customOnroadUIKeys.contains(key)) {
        toggles["CustomUI"]->setVisible(true);
      } else if (modelUIKeys.contains(key)) {
        toggles["ModelUI"]->setVisible(true);
      } else if (navigationUIKeys.contains(key)) {
        toggles["NavigationUI"]->setVisible(true);
      } else if (qualityOfLifeKeys.contains(key)) {
        toggles["QOLVisuals"]->setVisible(true);
      }
    }
  }

  openDescriptions(forceOpenDescriptions, toggles);

  update();
}
