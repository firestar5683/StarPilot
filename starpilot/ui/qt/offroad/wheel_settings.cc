#include "starpilot/ui/qt/offroad/wheel_settings.h"

namespace {

QMap<int, QString> getWheelFunctionsMap() {
  return {
    {0, QObject::tr("No Action")},
    {3, QObject::tr("Pause Steering")},
    {7, QObject::tr("Toggle \"Switchback Mode\" On/Off")},
    {8, QObject::tr("Create Bookmark")},
  };
}

QMap<int, QString> getLongitudinalWheelFunctionsMap() {
  return {
    {1, QObject::tr("Change \"Personality Profile\"")},
    {2, QObject::tr("Force openpilot to Coast")},
    {4, QObject::tr("Pause Acceleration/Braking")},
    {5, QObject::tr("Toggle \"Experimental Mode\" On/Off")},
    {6, QObject::tr("Toggle \"Traffic Mode\" On/Off")},
  };
}

QMap<int, QString> getMergedWheelFunctionsMap() {
  QMap<int, QString> functionsMap = getWheelFunctionsMap();
  const QMap<int, QString> longitudinalFunctionsMap = getLongitudinalWheelFunctionsMap();
  for (auto it = longitudinalFunctionsMap.constBegin(); it != longitudinalFunctionsMap.constEnd(); ++it) {
    functionsMap[it.key()] = it.value();
  }
  return functionsMap;
}

QMap<int, QString> getMainCruiseFunctionsMap() {
  return {
    {0, QObject::tr("No Action")},
    {9, QObject::tr("Toggle Always On Lateral")},
    {10, QObject::tr("Adopt Current Speed Limit")},
  };
}

QString getWheelFunctionLabel(Params &params, const QString &key) {
  QMap<int, QString> functionsMap;
  if (key == "MainCruiseButtonControl") {
    functionsMap = getMainCruiseFunctionsMap();
  } else {
    functionsMap = getMergedWheelFunctionsMap();
    if (key == "LKASButtonControl") {
      functionsMap[9] = QObject::tr("Toggle Always On Lateral");
    }
  }
  return functionsMap.value(params.getInt(key.toStdString()), QObject::tr("No Action"));
}

}  // namespace

StarPilotWheelPanel::StarPilotWheelPanel(StarPilotSettingsWindow *parent, bool forceOpen) : StarPilotListWidget(parent), parent(parent) {
  forceOpenDescriptions = forceOpen;

  ParamControl *nostalgiaModeToggle = new ParamControl(
    "NostalgiaMode",
    tr("Nostalgia Mode"),
    tr("<b>Use the left paddle to pause openpilot acceleration and braking while Always On Lateral stays active on supported Hyundai CAN-FD cars.</b>"),
    "../../starpilot/assets/toggle_icons/icon_mute.png"
  );
  toggles["NostalgiaMode"] = nostalgiaModeToggle;
  addItem(nostalgiaModeToggle);
  QObject::connect(nostalgiaModeToggle, &AbstractControl::hideDescriptionEvent, [this]() {
    update();
  });
  QObject::connect(nostalgiaModeToggle, &AbstractControl::showDescriptionEvent, [this]() {
    update();
  });

  const std::vector<std::tuple<QString, QString, QString, QString>> wheelToggles {
    {"CancelButtonControl", tr("Cancel Button"), tr("<b>Action performed when the remapped \"Cancel\" button is pressed.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"DistanceButtonControl", tr("Distance Button"), tr("<b>Action performed when the \"Distance\" button is pressed.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"LongCancelButtonControl", tr("Cancel Button (Long Press)"), tr("<b>Action performed when the remapped \"Cancel\" button is pressed for more than 0.5 seconds.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"LongDistanceButtonControl", tr("Distance Button (Long Press)"), tr("<b>Action performed when the \"Distance\" button is pressed for more than 0.5 seconds.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"VeryLongCancelButtonControl", tr("Cancel Button (Very Long Press)"), tr("<b>Action performed when the remapped \"Cancel\" button is pressed for more than 2.5 seconds.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"VeryLongDistanceButtonControl", tr("Distance Button (Very Long Press)"), tr("<b>Action performed when the \"Distance\" button is pressed for more than 2.5 seconds.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"LKASButtonControl", tr("LKAS Button"), tr("<b>Action performed when the \"LKAS\" button is pressed.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"MainCruiseButtonControl", tr("CC Main Button"), tr("<b>Action performed when the cruise control main button is pressed.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"ModeButtonControl", tr("Mode Button"), tr("<b>Action performed when the \"Mode\" button is pressed.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"LongModeButtonControl", tr("Mode Button (Long Press)"), tr("<b>Action performed when the \"Mode\" button is pressed for more than 0.5 seconds.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"VeryLongModeButtonControl", tr("Mode Button (Very Long Press)"), tr("<b>Action performed when the \"Mode\" button is pressed for more than 2.5 seconds.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"StarButtonControl", tr("Star Button"), tr("<b>Action performed when the \"Star\" button is pressed.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"LongStarButtonControl", tr("Star Button (Long Press)"), tr("<b>Action performed when the \"Star\" button is pressed for more than 0.5 seconds.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"},
    {"VeryLongStarButtonControl", tr("Star Button (Very Long Press)"), tr("<b>Action performed when the \"Star\" button is pressed for more than 2.5 seconds.</b>"), "../../starpilot/assets/toggle_icons/icon_mute.png"}
  };

  for (const auto &[param, title, desc, icon] : wheelToggles) {
    ButtonControl *wheelToggle = new ButtonControl(title, tr("SELECT"), desc);
    QObject::connect(wheelToggle, &ButtonControl::clicked, [key = param, parent, wheelToggle, this]() {
      QMap<int, QString> functionsMap;
      if (key == "MainCruiseButtonControl") {
        functionsMap = getMainCruiseFunctionsMap();
      } else {
        functionsMap = getWheelFunctionsMap();
        if (parent->hasOpenpilotLongitudinal) {
          const QMap<int, QString> longitudinalFunctionsMap = getLongitudinalWheelFunctionsMap();
          for (auto it = longitudinalFunctionsMap.constBegin(); it != longitudinalFunctionsMap.constEnd(); ++it) {
            functionsMap[it.key()] = it.value();
          }
        }
        if (key == "LKASButtonControl") {
          functionsMap[9] = tr("Toggle Always On Lateral");
        }
      }

      QString selection = MultiOptionDialog::getSelection(tr("Select a function to assign to this button"), functionsMap.values(), functionsMap[params.getInt(key.toStdString())], this);
      if (!selection.isEmpty()) {
        params.putInt(key.toStdString(), functionsMap.key(selection));
        wheelToggle->setValue(selection);
        updateStarPilotToggles();
      }
    });
    wheelToggle->setValue(getWheelFunctionLabel(params, param));

    toggles[param] = wheelToggle;

    addItem(wheelToggle);

    QObject::connect(wheelToggle, &AbstractControl::hideDescriptionEvent, [this]() {
      update();
    });
    QObject::connect(wheelToggle, &AbstractControl::showDescriptionEvent, [this]() {
      update();
    });
  }

  openDescriptions(forceOpenDescriptions, toggles);
}

void StarPilotWheelPanel::showEvent(QShowEvent *event) {
  updateToggles();
}

void StarPilotWheelPanel::updateToggles() {
  const bool showAllToggles = parent->showAllTogglesEnabled();

  for (auto &[key, toggle] : toggles) {
    bool setVisible = showAllToggles || parent->tuningLevel >= parent->starpilotToggleLevels[key].toDouble();

    if (!showAllToggles && key == "LKASButtonControl") {
      setVisible &= !parent->isSubaru;
    }

    if (!showAllToggles && (
        key == "CancelButtonControl" ||
        key == "LongCancelButtonControl" ||
        key == "VeryLongCancelButtonControl")) {
      setVisible &= parent->isBolt;
      setVisible &= parent->hasPedal;
      setVisible &= params.getBool("RemapCancelToDistance");
    }

    if (!showAllToggles && key == "NostalgiaMode") {
      setVisible &= parent->isHKGCanFd;
      setVisible &= parent->hasOpenpilotLongitudinal;
    }

    if (!showAllToggles && (
        key == "ModeButtonControl" ||
        key == "LongModeButtonControl" ||
        key == "VeryLongModeButtonControl" ||
        key == "StarButtonControl" ||
        key == "LongStarButtonControl" ||
        key == "VeryLongStarButtonControl")) {
      setVisible &= parent->hasModeStarButtons;
    }

    if (ButtonControl *wheelToggle = qobject_cast<ButtonControl*>(toggle)) {
      wheelToggle->setValue(getWheelFunctionLabel(params, key));
    }

    toggle->setVisible(setVisible);
  }

  openDescriptions(forceOpenDescriptions, toggles);

  update();
}
