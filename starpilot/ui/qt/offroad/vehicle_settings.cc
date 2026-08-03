#include <QRegularExpression>

#include "starpilot/ui/qt/offroad/vehicle_settings.h"
#include "system/hardware/hw.h"

QStringList getCarNames(const QString &carMake, QMap<QString, QString> &carModels) {
  static const QHash<QString, QString> makeToFolder = {
    {"acura", "honda"},
    {"audi", "volkswagen"},
    {"buick", "gm"},
    {"cadillac", "gm"},
    {"chevrolet", "gm"},
    {"chrysler", "chrysler"},
    {"cupra", "volkswagen"},
    {"dodge", "chrysler"},
    {"ford", "ford"},
    {"genesis", "hyundai"},
    {"gmc", "gm"},
    {"holden", "gm"},
    {"honda", "honda"},
    {"hyundai", "hyundai"},
    {"jeep", "chrysler"},
    {"kia", "hyundai"},
    {"lexus", "toyota"},
    {"lincoln", "ford"},
    {"man", "volkswagen"},
    {"mazda", "mazda"},
    {"nissan", "nissan"},
    {"peugeot", "psa"},
    {"ram", "chrysler"},
    {"rivian", "rivian"},
    {"seat", "volkswagen"},
    {"škoda", "volkswagen"},
    {"subaru", "subaru"},
    {"tesla", "tesla"},
    {"toyota", "toyota"},
    {"volkswagen", "volkswagen"}
  };

  QStringList carNames;

  const QString folder = makeToFolder.value(carMake.toLower());
  if (folder.isEmpty()) {
    return carNames;
  }

  QFile file(QString("../../opendbc/car/%1/values.py").arg(folder));
  if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
    return carNames;
  }

  QString content = file.readAll();
  file.close();

  static const QRegularExpression commentRe("#[^\\n]*");
  static const QRegularExpression footnoteRe("footnotes=\\[[^\\]]*\\],\\s*");
  content.remove(commentRe).remove(footnoteRe);

  static const QRegularExpression platformRe("(\\w+)\\s*=\\s*\\w+\\s*\\(");
  QRegularExpressionMatchIterator platformIt = platformRe.globalMatch(content);

  QVector<QPair<int, QString>> platforms;
  while (platformIt.hasNext()) {
    QRegularExpressionMatch match = platformIt.next();
    platforms.append({match.capturedStart(), match.captured(1)});
  }
  platforms.append({content.length(), QString()});

  static const QRegularExpression carNameRe("CarDocs\\w*\\s*\\(\\s*\"([^\"]+)\"");
  const QString lowerMake = carMake.toLower();

  for (int i = 0; i < platforms.size() - 1; ++i) {
    int start = platforms[i].first;
    int end = platforms[i + 1].first;
    const QString &platformName = platforms[i].second;

    QRegularExpressionMatchIterator carIt = carNameRe.globalMatch(
      content.mid(start, end - start)
    );

    while (carIt.hasNext()) {
      QString carName = carIt.next().captured(1);
      if (carName.startsWith(carMake, Qt::CaseInsensitive)) {
        carModels[carName] = platformName;
        carNames.append(carName);
      }
    }
  }

  carNames.sort(Qt::CaseInsensitive);
  return carNames;
}

StarPilotVehiclesPanel::StarPilotVehiclesPanel(StarPilotSettingsWindow *parent, bool forceOpen) : StarPilotListWidget(parent), parent(parent) {
  forceOpenDescriptions = forceOpen;

  QStackedLayout *vehiclesLayout = new QStackedLayout();
  addItem(vehiclesLayout);

  StarPilotListWidget *settingsList = new StarPilotListWidget(this);

  ScrollView *vehiclesPanel = new ScrollView(settingsList, this);

  vehiclesLayout->addWidget(vehiclesPanel);

  QStringList makes = {
    "Acura", "Audi", "Buick", "Cadillac", "Chevrolet", "Chrysler", "CUPRA",
    "Dodge", "Ford", "Genesis", "GMC", "Holden", "Honda", "Hyundai", "Jeep",
    "Kia", "Lexus", "Lincoln", "MAN", "Mazda", "Nissan", "Peugeot", "Ram",
    "Rivian", "SEAT", "Škoda", "Subaru", "Tesla", "Toyota", "Volkswagen"
  };

  ButtonControl *selectMakeButton = new ButtonControl(tr("Car Make"), tr("SELECT"));
  QObject::connect(selectMakeButton, &ButtonControl::clicked, [makes, selectMakeButton, this]() {
    QString makeSelection = MultiOptionDialog::getSelection(tr("Choose your car make"), makes, "", this);
    if (!makeSelection.isEmpty()) {
      params.put("CarMake", makeSelection.toStdString());
      selectMakeButton->setValue(makeSelection);
    }
  });
  settingsList->addItem(selectMakeButton);

  ButtonControl *selectModelButton = new ButtonControl(tr("Car Model"), tr("SELECT"));
  QObject::connect(selectModelButton, &ButtonControl::clicked, [selectModelButton, this]() {
    QString modelSelection = MultiOptionDialog::getSelection(tr("Choose your car model"), getCarNames(QString::fromStdString(params.get("CarMake")).toLower(), carModels), "", this);
    if (!modelSelection.isEmpty()) {
      params.put("CarModel", carModels.value(modelSelection).toStdString());
      params.put("CarModelName", modelSelection.toStdString());
      selectModelButton->setValue(modelSelection);
    }
  });
  settingsList->addItem(selectModelButton);

  forceFingerprint = new ParamControl("ForceFingerprint", tr("Disable Automatic Fingerprint Detection"), tr("<b>Force the selected fingerprint</b> and prevent it from ever changing."), "");
  settingsList->addItem(forceFingerprint);

  disableOpenpilotLong = new ParamControl("DisableOpenpilotLongitudinal", tr("Disable openpilot Longitudinal Control"), tr("<b>Disable openpilot longitudinal</b> and use the car's stock ACC instead."), "");
  QObject::connect(disableOpenpilotLong, &ToggleControl::toggleFlipped, [parent, this](bool state) {
    if (state) {
      if (StarPilotConfirmationDialog::yesorno(tr("Are you sure you want to completely disable openpilot longitudinal control?"), this)) {
        if (started) {
          if (StarPilotConfirmationDialog::toggleReboot(this)) {
            Hardware::reboot();
          }
        }
      } else {
        params.putBool("DisableOpenpilotLongitudinal", false);
        disableOpenpilotLong->refresh();
      }
    }

    parent->updateVariables();
    updateToggles();
  });
  settingsList->addItem(disableOpenpilotLong);

  StarPilotListWidget *chryslerList = new StarPilotListWidget(this);
  StarPilotListWidget *gmList = new StarPilotListWidget(this);
  StarPilotListWidget *hkgList = new StarPilotListWidget(this);
  StarPilotListWidget *subaruList = new StarPilotListWidget(this);
  StarPilotListWidget *toyotaList = new StarPilotListWidget(this);
  StarPilotListWidget *vehicleInfoList = new StarPilotListWidget(this);

  ScrollView *chryslerPanel = new ScrollView(chryslerList, this);
  ScrollView *gmPanel = new ScrollView(gmList, this);
  ScrollView *hkgPanel = new ScrollView(hkgList, this);
  ScrollView *subaruPanel = new ScrollView(subaruList, this);
  ScrollView *toyotaPanel = new ScrollView(toyotaList, this);
  ScrollView *vehicleInfoPanel = new ScrollView(vehicleInfoList, this);

  vehiclesLayout->addWidget(chryslerPanel);
  vehiclesLayout->addWidget(gmPanel);
  vehiclesLayout->addWidget(hkgPanel);
  vehiclesLayout->addWidget(subaruPanel);
  vehiclesLayout->addWidget(toyotaPanel);
  vehiclesLayout->addWidget(vehicleInfoPanel);

  std::vector<std::tuple<QString, QString, QString, QString>> vehicleToggles {
    {"ChryslerToggles", tr("Chrysler/Jeep Settings"), tr("<b>StarPilot features for Chrysler and Jeep vehicles.</b>"), ""},
    {"JeepBrakeHold", tr("Brake Hold"), tr("<b>Hold the brakes after Jeep ACC times out at a stop</b>, then send resume when traffic moves again."), ""},

    {"GMToggles", tr("General Motors Settings"), tr("<b>StarPilot features for General Motors vehicles.</b>"), ""},
    {"GMPedalLongitudinal", tr("Use Pedal For Longitudinal"), tr("<b>Use the pedal interceptor for full longitudinal control</b> on supported GM vehicles."), ""},
    {"GMDashSpoofOffsets", tr("Apply Offsets To Dash Spoof"), tr("<b>On GM pedal-long cars, add the configured set-speed offset</b> to the spoofed dash set speed so it matches the on-screen set speed."), ""},
    {"IgnoreIgnitionLine", tr("Use CAN Ignition Only"), tr("<b>Use CAN ignition only and ignore the physical ignition line in Panda firmware.</b><br><br>Requires a Panda flash. Use this only on vehicles with reliable CAN ignition when the harness box reports false ignition."), ""},
    {"LongPitch", tr("Smooth Pedal Response on Hills"), tr("<b>Smoothen acceleration and braking</b> when driving downhill/uphill."), ""},
    {"RemoteStartBootsComma", tr("Remote Start Boots comma"), tr("<b>Use the remote-start GM panda firmware at boot.</b><br><br>Required for GM remote-start startup signal behavior."), ""},
    {"RemapCancelToDistance", tr("Remap Cancel Button"), tr("<b>On pedal-interceptor Bolts, treat the steering-wheel CANCEL button as an extra mappable button.</b>"), ""},
    {"VoltSNG", tr("Stop-and-Go Hack"), tr("<b>Force stop-and-go</b> on the 2017 Chevy Volt."), ""},

    {"HKGToggles", tr("Hyundai/Kia/Genesis Settings"), tr("<b>StarPilot features for Hyundai/Kia/Genesis vehicles.</b>"), ""},
    {"HKGRemoteStartBootsComma", tr("EV Remote Climate"), tr("<b>Use the remote-climate Hyundai/Kia/Genesis CAN-FD panda firmware at boot.</b><br><br>Required for EV remote-climate startup signal behavior."), ""},

    {"SubaruToggles", tr("Subaru Settings"), tr("<b>StarPilot features for Subaru vehicles.</b>"), ""},
    {"SubaruSNG", tr("Stop and Go"), tr("Stop and go for supported Subaru vehicles."), ""},
    {"SubaruSNGManualParkingBrake", tr("Stop and Go for Manual Parking Brake"), tr("<b>Use the manual-parking-brake Subaru stop-and-go strategy.</b><br><br>Enable this for supported Subaru Global models with a manual handbrake. Keep it off on models with an electric parking brake."), ""},

    {"ToyotaToggles", tr("Toyota/Lexus Settings"), tr("<b>StarPilot features for Lexus and Toyota vehicles.</b>"), ""},
    {"ToyotaDoors", tr("Automatically Lock/Unlock Doors"), tr("<b>Automatically lock/unlock doors</b> when shifting in and out of drive."), ""},
    {"ClusterOffset", tr("Dashboard Speed Offset"), tr("<b>The speed offset openpilot uses to match the speed on the dashboard display.</b>"), ""},
    {"LockDoorsTimer", tr("Lock Doors On Ignition Off After"), tr("<b>Automatically lock the doors on ignition off</b> when no one is detected in the front seats."), ""},
    {"SNGHack", tr("Stop-and-Go Hack"), tr("<b>Force stop-and-go</b> on Lexus/Toyota vehicles without stock stop-and-go functionality."), ""},

    {"VehicleInfo", tr("Vehicle Info"), tr("<b>Information about your vehicle in regards to openpilot support and functionality.</b>"), ""},
    {"HardwareDetected", tr("3rd Party Hardware Detected"), tr("<b>Detected 3rd party hardware.</b>"), ""},
    {"BlindSpotSupport", tr("Blind Spot Support"), tr("<b>Does openpilot use the vehicle's blind spot data?</b>"), ""},
    {"PedalSupport", tr("comma Pedal Support"), tr("<b>Does your vehicle support the \"comma pedal\"?</b>"), ""},
    {"OpenpilotLongitudinal", tr("openpilot Longitudinal Support"), tr("<b>Can openpilot control the vehicle's acceleration and braking?</b>"), ""},
    {"RadarSupport", tr("Radar Support"), tr("<b>Does openpilot use the vehicle's radar data</b> alongside the device's camera for tracking lead vehicles?"), ""},
    {"SDSUSupport", tr("SDSU Support"), tr("<b>Does your vehicle support \"SDSUs\"?</b>"), ""},
    {"SNGSupport", tr("Stop-and-Go Support"), tr("<b>Does your vehicle support stop-and-go driving?</b>"), ""}
  };

  for (const auto &[param, title, desc, icon] : vehicleToggles) {
    AbstractControl *vehicleToggle;

    if (param == "ChryslerToggles") {
      ButtonControl *chryslerButton = new ButtonControl(title, tr("MANAGE"), desc);
      QObject::connect(chryslerButton, &ButtonControl::clicked, [vehiclesLayout, chryslerPanel, this]() {
        openDescriptions(forceOpenDescriptions, toggles);
        vehiclesLayout->setCurrentWidget(chryslerPanel);
      });
      vehicleToggle = chryslerButton;

    } else if (param == "GMToggles") {
      ButtonControl *gmButton = new ButtonControl(title, tr("MANAGE"), desc);
      QObject::connect(gmButton, &ButtonControl::clicked, [vehiclesLayout, gmPanel, this]() {
        openDescriptions(forceOpenDescriptions, toggles);
        vehiclesLayout->setCurrentWidget(gmPanel);
      });
      vehicleToggle = gmButton;

    } else if (param == "HKGToggles") {
      ButtonControl *hkgButton = new ButtonControl(title, tr("MANAGE"), desc);
      QObject::connect(hkgButton, &ButtonControl::clicked, [vehiclesLayout, hkgPanel, this]() {
        openDescriptions(forceOpenDescriptions, toggles);
        vehiclesLayout->setCurrentWidget(hkgPanel);
      });
      vehicleToggle = hkgButton;

    } else if (param == "SubaruToggles") {
      ButtonControl *subaruButton = new ButtonControl(title, tr("MANAGE"), desc);
      QObject::connect(subaruButton, &ButtonControl::clicked, [vehiclesLayout, subaruPanel, this]() {
        openDescriptions(forceOpenDescriptions, toggles);
        vehiclesLayout->setCurrentWidget(subaruPanel);
      });
      vehicleToggle = subaruButton;

    } else if (param == "ToyotaToggles") {
      ButtonControl *toyotaButton = new ButtonControl(title, tr("MANAGE"), desc);
      QObject::connect(toyotaButton, &ButtonControl::clicked, [vehiclesLayout, toyotaPanel, this]() {
        openDescriptions(forceOpenDescriptions, toggles);
        vehiclesLayout->setCurrentWidget(toyotaPanel);
      });
      vehicleToggle = toyotaButton;
    } else if (param == "ToyotaDoors") {
      std::vector<QString> lockToggles{"LockDoors", "UnlockDoors"};
      std::vector<QString> lockToggleNames{tr("Lock"), tr("Unlock")};
      vehicleToggle = new StarPilotButtonToggleControl(param, title, desc, icon, lockToggles, lockToggleNames);
    } else if (param == "LockDoorsTimer") {
      std::map<float, QString> autoLockLabels;
      for (int i = 0; i <= 300; ++i) {
        autoLockLabels[i] = i == 0 ? tr("Never") : QString::number(i) + tr(" seconds");
      }
      vehicleToggle = new StarPilotParamValueControl(param, title, desc, icon, 0, 300, QString(), autoLockLabels, 5);
    } else if (param == "ClusterOffset") {
      std::vector<QString> clusterOffsetButton{"Reset"};
      StarPilotParamValueButtonControl *clusterOffsetToggle = new StarPilotParamValueButtonControl(param, title, desc, icon, 1.000, 1.050, "x", std::map<float, QString>(), 0.001, false, {}, clusterOffsetButton, false, false);
      QObject::connect(clusterOffsetToggle, &StarPilotParamValueButtonControl::buttonClicked, [clusterOffsetToggle, this]() {
        params.putFloat("ClusterOffset", std::stof(params.getKeyDefaultValue("ClusterOffset").value()));
        clusterOffsetToggle->refresh();
      });
      vehicleToggle = clusterOffsetToggle;

    } else if (param == "VehicleInfo") {
      ButtonControl *VehicleInfoButton = new ButtonControl(title, tr("VIEW"), desc);
      QObject::connect(VehicleInfoButton, &ButtonControl::clicked, [vehiclesLayout, vehicleInfoPanel, this]() {
        openDescriptions(forceOpenDescriptions, toggles);
        vehiclesLayout->setCurrentWidget(vehicleInfoPanel);
      });
      vehicleToggle = VehicleInfoButton;
    } else if (vehicleInfoKeys.contains(param)) {
      vehicleToggle = new LabelControl(title, "", desc);

    } else {
      vehicleToggle = new ParamControl(param, title, desc, icon);
    }

    toggles[param] = vehicleToggle;

    if (chryslerKeys.contains(param)) {
      chryslerList->addItem(vehicleToggle);
    } else if (gmKeys.contains(param)) {
      gmList->addItem(vehicleToggle);
    } else if (hkgKeys.contains(param)) {
      hkgList->addItem(vehicleToggle);
    } else if (subaruKeys.contains(param)) {
      subaruList->addItem(vehicleToggle);
    } else if (toyotaKeys.contains(param)) {
      toyotaList->addItem(vehicleToggle);
    } else if (vehicleInfoKeys.contains(param)) {
      vehicleInfoList->addItem(vehicleToggle);
    } else {
      settingsList->addItem(vehicleToggle);

      parentKeys.insert(param);
    }

    if (ButtonControl *buttonControl = qobject_cast<ButtonControl*>(vehicleToggle)) {
      QObject::connect(buttonControl, &ButtonControl::clicked, this, &StarPilotVehiclesPanel::openSubPanel);
    }

    QObject::connect(vehicleToggle, &AbstractControl::hideDescriptionEvent, [this]() {
      update();
    });
    QObject::connect(vehicleToggle, &AbstractControl::showDescriptionEvent, [this]() {
      update();
    });
  }

  static_cast<StarPilotParamValueControl*>(toggles["LockDoorsTimer"])->setWarning("<b>Warning:</b> openpilot can't detect if keys are still inside the car, so ensure you have a spare key to prevent accidental lockouts!");

  QSet<QString> rebootKeys = {"RemapCancelToDistance"};
  for (const QString &key : rebootKeys) {
    QObject::connect(static_cast<ToggleControl*>(toggles[key]), &ToggleControl::toggleFlipped, [key, this](bool state) {
      if (started) {
        if (StarPilotConfirmationDialog::toggleReboot(this)) {
          Hardware::reboot();
        }
      }
    });
  }

  auto connectPandaFlashToggle = [parent, this](const QString &key, const QString &prompt) {
    ParamControl *toggle = static_cast<ParamControl*>(toggles[key]);
    QObject::connect(toggle, &ToggleControl::toggleFlipped, [parent, key, prompt, toggle, this](bool state) {
      if (!StarPilotConfirmationDialog::yesorno(prompt, this)) {
        params.putBool(key.toStdString(), !state);
        toggle->refresh();
        return;
      }

      std::thread([parent, this]() {
        parent->keepScreenOn = true;
        params_memory.putBool("FlashPanda", true);
        while (params_memory.getBool("FlashPanda")) {
          std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        Hardware::reboot();
      }).detach();
    });
  };

  connectPandaFlashToggle("IgnoreIgnitionLine", tr("CAN Ignition Only requires a Panda firmware update. Flash the Panda now?"));
  connectPandaFlashToggle("HKGRemoteStartBootsComma", tr("EV Remote Climate requires a Panda firmware update. Flash the Panda now?"));
  connectPandaFlashToggle("RemoteStartBootsComma", tr("Remote Start requires a Panda firmware update. Flash the Panda now?"));

  openDescriptions(forceOpenDescriptions, toggles);

  QObject::connect(uiState(), &UIState::offroadTransition, [selectMakeButton, selectModelButton, this]() {
    std::thread([selectMakeButton, selectModelButton, this]() {
      selectMakeButton->setValue(QString::fromStdString(params.get("CarMake", true)));
      selectModelButton->setValue(QString::fromStdString(params.get(params.get("CarModelName").empty() ? "CarModel" : "CarModelName", true)));
    }).detach();
  });

  QObject::connect(parent, &StarPilotSettingsWindow::closeSubPanel, [vehiclesLayout, vehiclesPanel, this] {
    if (forceOpenDescriptions) {
      openDescriptions(forceOpenDescriptions, toggles);
      disableOpenpilotLong->showDescription();
      forceFingerprint->showDescription();
    }
    vehiclesLayout->setCurrentWidget(vehiclesPanel);
  });
  QObject::connect(uiState(), &UIState::uiUpdate, this, &StarPilotVehiclesPanel::updateState);
}

void StarPilotVehiclesPanel::showEvent(QShowEvent *event) {
  if (forceOpenDescriptions) {
    disableOpenpilotLong->showDescription();
    forceFingerprint->showDescription();
  }

  QStringList detected;
  if (parent->hasPedal) detected << "comma Pedal";
  if (parent->hasSDSU) detected << "SDSU";
  if (parent->hasZSS) detected << "ZSS";
  static_cast<LabelControl*>(toggles["HardwareDetected"])->setText(detected.isEmpty() ? tr("None") : detected.join(", "));

  static_cast<LabelControl*>(toggles["BlindSpotSupport"])->setText(parent->hasBSM ? tr("Yes") : tr("No"));
  static_cast<LabelControl*>(toggles["OpenpilotLongitudinal"])->setText(parent->hasOpenpilotLongitudinal ? tr("Yes") : tr("No"));
  static_cast<LabelControl*>(toggles["PedalSupport"])->setText(parent->canUsePedal ? tr("Yes") : tr("No"));
  static_cast<LabelControl*>(toggles["RadarSupport"])->setText(parent->hasRadar ? tr("Yes") : tr("No"));
  static_cast<LabelControl*>(toggles["SDSUSupport"])->setText(parent->canUseSDSU ? tr("Yes") : tr("No"));
  static_cast<LabelControl*>(toggles["SNGSupport"])->setText(parent->hasSNG ? tr("Yes") : tr("No"));

  updateToggles();
}

void StarPilotVehiclesPanel::updateState(const UIState &s) {
  if (!isVisible()) {
    return;
  }

  started = s.scene.started;
}

void StarPilotVehiclesPanel::updateToggles() {
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
      if (chryslerKeys.contains(key)) {
        setVisible &= parent->isJeep;
      } else if (gmKeys.contains(key)) {
        setVisible &= parent->isGM;
      } else if (hkgKeys.contains(key)) {
        setVisible &= parent->isHKGCanFd && parent->hasOpenpilotLongitudinal;
      } else if (subaruKeys.contains(key)) {
        setVisible &= parent->isSubaru;
      } else if (toyotaKeys.contains(key)) {
        setVisible &= parent->isToyota;
      } else if (vehicleInfoKeys.contains(key)) {
        setVisible = true;
      }

      if (longitudinalKeys.contains(key)) {
        setVisible &= parent->hasOpenpilotLongitudinal;
      }

      if (key == "SNGHack") {
        setVisible &= !parent->hasSNG;
      }

      else if (key == "GMPedalLongitudinal") {
        setVisible &= parent->hasPedal || (Hardware::PC() && parent->canUsePedal);
      }

      else if (key == "GMDashSpoofOffsets") {
        setVisible &= parent->hasPedal || (Hardware::PC() && parent->canUsePedal);
      }

      else if (key == "RemapCancelToDistance") {
        setVisible &= parent->isBolt && (parent->hasPedal || (Hardware::PC() && parent->canUsePedal));
      }

      else if (key == "SubaruSNG") {
        setVisible &= parent->hasSNG;
      }

      else if (key == "SubaruSNGManualParkingBrake") {
        setVisible &= parent->hasSNG && params.getBool("SubaruSNG");
      }

      else if (key == "VoltSNG") {
        setVisible &= parent->isVolt && !parent->hasSNG;
      }
    }

    toggle->setVisible(setVisible);

    if (setVisible) {
      if (chryslerKeys.contains(key)) {
        toggles["ChryslerToggles"]->setVisible(true);
      } else if (gmKeys.contains(key)) {
        toggles["GMToggles"]->setVisible(true);
      } else if (hkgKeys.contains(key)) {
        toggles["HKGToggles"]->setVisible(true);
      } else if (subaruKeys.contains(key)) {
        toggles["SubaruToggles"]->setVisible(true);
      } else if (toyotaKeys.contains(key)) {
        toggles["ToyotaToggles"]->setVisible(true);
      } else if (vehicleInfoKeys.contains(key)) {
        toggles["VehicleInfo"]->setVisible(true);
      }
    }
  }

  disableOpenpilotLong->setVisible(showAllToggles || ((parent->hasOpenpilotLongitudinal || parent->openpilotLongitudinalControlDisabled) && !parent->hasAlphaLongitudinal && parent->tuningLevel >= parent->starpilotToggleLevels["DisableOpenpilotLongitudinal"].toDouble()));
  forceFingerprint->setVisible(showAllToggles || parent->tuningLevel >= parent->starpilotToggleLevels["ForceFingerprint"].toDouble());

  openDescriptions(forceOpenDescriptions, toggles);

  update();
}
