#include <QRegularExpression>
#include <QTextStream>

#include "selfdrive/frogpilot/ui/qt/offroad/vehicle_settings.h"

QStringList getCarNames(const QString &carMake, QMap<QString, QString> &carModels) {
  static const QMap<QString, QString> makeMap = {
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
    {"ram", "chrysler"},
    {"seat", "volkswagen"},
    {"škoda", "volkswagen"},
    {"subaru", "subaru"},
    {"tesla", "tesla"},
    {"toyota", "toyota"},
    {"volkswagen", "volkswagen"}
  };

  QStringList carNameList;
  QSet<QString> uniqueCarNames;

  QFile valuesFile(QString("../car/%1/values.py").arg(makeMap.value(carMake, carMake)));
  if (!valuesFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
    return carNameList;
  }

  QString fileContent = QTextStream(&valuesFile).readAll();
  valuesFile.close();

  fileContent.remove(QRegularExpression("#[^\n]*"));
  fileContent.remove(QRegularExpression("footnotes=\\[[^\\]]*\\],\\s*"));

  static const QRegularExpression platformRegex(R"((\w+)\s*=\s*\w+\s*\(\s*\[([\s\S]*?)\]\s*,)");
  QRegularExpressionMatchIterator platformMatches = platformRegex.globalMatch(fileContent);
  while (platformMatches.hasNext()) {
    QRegularExpressionMatch platformMatch = platformMatches.next();
    QString platformName = platformMatch.captured(1);
    QString platformSection = platformMatch.captured(2);

    static const QRegularExpression carNameRegex("CarDocs\\(\\s*\"([^\"]+)\"[^)]*\\)");
    QRegularExpressionMatchIterator carNameMatches = carNameRegex.globalMatch(platformSection);
    while (carNameMatches.hasNext()) {
      QString carName = carNameMatches.next().captured(1);

      if (carName.contains(QRegularExpression("^[A-Za-z0-9 \u0160.()-]+$")) && carName.count(" ") >= 1) {
        QStringList carNameParts = carName.split(" ");
        if (carNameParts.contains(carMake, Qt::CaseInsensitive) && !uniqueCarNames.contains(carName)) {
          uniqueCarNames.insert(carName);
          carNameList << carName;
          carModels[carName] = platformName;
        }
      }
    }
  }

  std::sort(carNameList.begin(), carNameList.end());
  return carNameList;
}

FrogPilotVehiclesPanel::FrogPilotVehiclesPanel(FrogPilotSettingsWindow *parent) : FrogPilotListWidget(parent), parent(parent) {
  QStringList makes = {
    "Acura", "Audi", "Buick", "Cadillac", "Chevrolet", "Chrysler",
    "CUPRA", "Dodge", "Ford", "Genesis", "GMC", "Holden", "Honda",
    "Hyundai", "Jeep", "Kia", "Lexus", "Lincoln", "MAN", "Mazda",
    "Nissan", "Ram", "SEAT", "Škoda", "Subaru", "Tesla", "Toyota",
    "Volkswagen"
  };
  selectMakeButton = new ButtonControl(tr("Select Make"), tr("SELECT"));
  QObject::connect(selectMakeButton, &ButtonControl::clicked, [this, makes]() {
    QString newMakeSelection = MultiOptionDialog::getSelection(tr("Select a Make"), makes, "", this);
    if (!newMakeSelection.isEmpty()) {
      carMake = newMakeSelection;
      params.put("CarMake", carMake.toStdString());
      selectMakeButton->setValue(newMakeSelection);
      setModels();
    }
  });
  addItem(selectMakeButton);

  selectModelButton = new ButtonControl(tr("Select Model"), tr("SELECT"));
  QObject::connect(selectModelButton, &ButtonControl::clicked, [this]() {
    QString newModelSelection = MultiOptionDialog::getSelection(tr("Select a Model"), models, "", this);
    if (!newModelSelection.isEmpty()) {
      carModel = newModelSelection;
      QString modelIdentifier = carModels.value(newModelSelection);
      params.put("CarModel", modelIdentifier.toStdString());
      params.put("CarModelName", newModelSelection.toStdString());
      selectModelButton->setValue(newModelSelection);
    }
  });
  addItem(selectModelButton);
  selectModelButton->setVisible(false);

  forceFingerprint = new ParamControl("ForceFingerprint", tr("Disable Automatic Fingerprint Detection"), tr("Forces the selected fingerprint and prevents it from ever changing."), "");
  addItem(forceFingerprint);

  disableOpenpilotLongitudinal = params.getBool("DisableOpenpilotLongitudinal");
  disableOpenpilotLong = new ToggleControl(tr("Disable openpilot Longitudinal Control"), tr("Disables openpilot longitudinal control and uses the car's stock ACC instead."), "", disableOpenpilotLongitudinal);
  QObject::connect(disableOpenpilotLong, &ToggleControl::toggleFlipped, [this, parent](bool state) {
    if (state) {
      if (FrogPilotConfirmationDialog::yesorno(tr("Are you sure you want to completely disable openpilot longitudinal control?"), this)) {
        disableOpenpilotLongitudinal = true;
        params.putBool("DisableOpenpilotLongitudinal", true);

        if (started) {
          if (FrogPilotConfirmationDialog::toggle(tr("Reboot required to take effect."), tr("Reboot Now"), this)) {
            Hardware::reboot();
          }
        }
      } else {
        disableOpenpilotLong->refresh();
      }
    } else {
      disableOpenpilotLongitudinal = false;
      params.putBool("DisableOpenpilotLongitudinal", false);
    }
    parent->updateVariables();
  });
  addItem(disableOpenpilotLong);

  std::vector<std::tuple<QString, QString, QString, QString>> vehicleToggles {
    {"VoltSNG", tr("2017 Volt Stop and Go Hack"), tr("Force stop and go for the 2017 Chevy Volt."), ""},
    {"LongPitch", tr("Downhill/Uphill Smoothing"), tr("Smoothen the gas and brake response when driving downhill or uphill."), ""},
    {"ExperimentalGMTune", tr("Experimental GM Longitudinal Tune"), tr("Enable FrogsGoMoo's experimental GM longitudinal tune that is based on nothing but guesswork. Use at your own risk!"), ""},
    {"NewLongAPIGM", tr("Use comma's New Longitudinal API"), tr("Enable comma's new control system that has shown great improvement with acceleration and braking, but has issues on some GM vehicles."), ""},

    {"NewLongAPI", tr("Use comma's New Longitudinal API"), tr("Enable comma's new control system that has shown great improvement with acceleration and braking, but has issues on some Hyundai/Kia/Genesis vehicles."), ""},

    {"CrosstrekTorque", tr("Subaru Crosstrek Torque Increase"), tr("Increase the maximum allowed torque for the 'Subaru Crosstrek'."), ""},

    {"ToyotaDoors", tr("Automatically Lock/Unlock Doors"), tr("Automatically lock the doors when in drive and unlock when in park."), ""},
    {"ClusterOffset", tr("Cluster Speed Offset"), tr("Set the cluster offset openpilot uses to try and match the speed displayed on the dash."), ""},
    {"FrogsGoMoosTweak", tr("FrogsGoMoo's Personal Tweaks"), tr("FrogsGoMoo's personal tweaks to the Toyota/Lexus tune that allows the vehicle to take off and stop a bit smoother."), ""},
    {"LockDoorsTimer", tr("Lock Doors On Ignition Off"), tr("Automatically lock the doors after the car's ignition has been turned off and no one is detected in either of the front seats."), ""},
    {"SNGHack", tr("Stop and Go Hack"), tr("Force stop and go for vehicles without stop and go functionality."), ""},
  };

  for (const auto &[param, title, desc, icon] : vehicleToggles) {
    AbstractControl *vehicleToggle;

    if (param == "ToyotaDoors") {
      std::vector<QString> lockToggles{"LockDoors", "UnlockDoors"};
      std::vector<QString> lockToggleNames{tr("Lock"), tr("Unlock")};
      vehicleToggle = new FrogPilotButtonToggleControl(param, title, desc, lockToggles, lockToggleNames);
    } else if (param == "LockDoorsTimer") {
      std::map<int, QString> autoLockLabels;
      for (int i = 0; i <= 300; ++i) {
        autoLockLabels[i] = i == 0 ? tr("Never") : QString::number(i) + " seconds";
      }
      vehicleToggle = new FrogPilotParamValueControl(param, title, desc, icon, 0, 300, QString(), autoLockLabels, 1);
    } else if (param == "ClusterOffset") {
      std::vector<QString> clusterOffsetButton{"Reset"};
      FrogPilotParamValueButtonControl *clusterOffsetToggle = new FrogPilotParamValueButtonControl(param, title, desc, icon, 1.000, 1.050, "x", std::map<int, QString>(), 0.001, {}, clusterOffsetButton, false, false);
      QObject::connect(clusterOffsetToggle, &FrogPilotParamValueButtonControl::buttonClicked, [=]() {
        params.putFloat("ClusterOffset", params_default.getFloat("ClusterOffset"));
        clusterOffsetToggle->refresh();
      });
      vehicleToggle = clusterOffsetToggle;

    } else {
      vehicleToggle = new ParamControl(param, title, desc, icon);
    }

    addItem(vehicleToggle);
    toggles[param] = vehicleToggle;
  }

  std::set<QString> rebootKeys = {"CrosstrekTorque", "ExperimentalGMTune", "NewLongAPI", "NewLongAPIGM"};
  for (const QString &key : rebootKeys) {
    QObject::connect(static_cast<ToggleControl*>(toggles[key]), &ToggleControl::toggleFlipped, [this]() {
      if (started) {
        if (FrogPilotConfirmationDialog::toggle(tr("Reboot required to take effect."), tr("Reboot Now"), this)) {
          Hardware::reboot();
        }
      }
    });
  }

  QObject::connect(uiState(), &UIState::offroadTransition, [this]() {
    std::thread([this]() {
      carMake = QString::fromStdString(params.get("CarMake", true));
      carModel = QString::fromStdString(params.get(params.get("CarModelName").empty() ? "CarModel" : "CarModelName"));
      setModels();
    }).detach();
  });

  carMake = QString::fromStdString(params.get("CarMake"));
  carModel = QString::fromStdString(params.get(params.get("CarModelName").empty() ? "CarModel" : "CarModelName"));

  if (!carMake.isEmpty()) {
    setModels();
  }

  QObject::connect(uiState(), &UIState::uiUpdate, this, &FrogPilotVehiclesPanel::updateState);
}

void FrogPilotVehiclesPanel::showEvent(QShowEvent *event) {
  frogpilotToggleLevels = parent->frogpilotToggleLevels;
  hasExperimentalOpenpilotLongitudinal = parent->hasExperimentalOpenpilotLongitudinal;
  hasOpenpilotLongitudinal = parent->hasOpenpilotLongitudinal;
  hasSNG = parent->hasSNG;
  isBolt = parent->isBolt;
  isGM = parent->isGM;
  isHKG = parent->isHKG;
  isImpreza = parent->isImpreza;
  isSubaru = parent->isSubaru;
  isToyota = parent->isToyota;
  isVolt = parent->isVolt;
  tuningLevel = parent->tuningLevel;

  UIState *s = uiState();
  UIScene &scene = s->scene;

  allowAutoLockingDoors = scene.allow_auto_locking_doors;

  updateToggles();
}

void FrogPilotVehiclesPanel::updateState(const UIState &s) {
  if (!isVisible()) {
    return;
  }

  started = s.scene.started;
}

void FrogPilotVehiclesPanel::setModels() {
  models = getCarNames(carMake.toLower(), carModels);
  updateToggles();
}

void FrogPilotVehiclesPanel::updateToggles() {
  setUpdatesEnabled(false);

  disableOpenpilotLong->setVisible(hasOpenpilotLongitudinal && !hasExperimentalOpenpilotLongitudinal && tuningLevel >= frogpilotToggleLevels["DisableOpenpilotLongitudinal"].toDouble() || disableOpenpilotLongitudinal);
  forceFingerprint ->setVisible(tuningLevel >= frogpilotToggleLevels["ForceFingerprint"].toDouble() || isBolt);

  selectMakeButton->setValue(carMake);
  selectModelButton->setValue(carModel);
  selectModelButton->setVisible(!carMake.isEmpty());

  for (auto &[key, toggle] : toggles) {
    bool setVisible = false;

    if (isGM && gmKeys.find(key) != gmKeys.end()) {
      setVisible = true;

      if (longitudinalKeys.find(key) != longitudinalKeys.end()) {
        setVisible &= hasOpenpilotLongitudinal;
      }
      if (voltKeys.find(key) != voltKeys.end()) {
        setVisible &= isVolt;
      }
    } else if (isHKG && hyundaiKeys.find(key) != hyundaiKeys.end()) {
      setVisible = true;

      if (longitudinalKeys.find(key) != longitudinalKeys.end()) {
        setVisible &= hasOpenpilotLongitudinal;
      }
    } else if (isSubaru && subaruKeys.find(key) != subaruKeys.end()) {
      setVisible = true;

      if (imprezaKeys.find(key) != imprezaKeys.end()) {
        setVisible &= isImpreza;
      }
      if (longitudinalKeys.find(key) != longitudinalKeys.end()) {
        setVisible &= hasOpenpilotLongitudinal;
      }
    } else if (isToyota && toyotaKeys.find(key) != toyotaKeys.end()) {
      setVisible = true;

      if (longitudinalKeys.find(key) != longitudinalKeys.end()) {
        setVisible &= hasOpenpilotLongitudinal;
      }
      if (sngKeys.find(key) != sngKeys.end()) {
        setVisible &= !hasSNG;
      }
      if (key == "LockDoorsTimer") {
        setVisible &= allowAutoLockingDoors;
      }
    }

    toggle->setVisible(!carMake.isEmpty() && setVisible && tuningLevel >= frogpilotToggleLevels[key].toDouble());
  }

  setUpdatesEnabled(true);

  update();
}
