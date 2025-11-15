#include "frogpilot/ui/qt/offroad/model_settings.h"
#include "frogpilot/ui/qt/offroad/expandable_multi_option_dialog.h"
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QDoubleSpinBox>
#include <QPushButton>
#include <QDialog>
#include <algorithm>

FrogPilotModelPanel::FrogPilotModelPanel(FrogPilotSettingsWindow *parent) : FrogPilotListWidget(parent), parent(parent) {
  QStackedLayout *modelLayout = new QStackedLayout();
  addItem(modelLayout);

  FrogPilotListWidget *modelList = new FrogPilotListWidget(this);

  ScrollView *modelPanel = new ScrollView(modelList, this);

  modelLayout->addWidget(modelPanel);

  FrogPilotListWidget *modelLabelsList = new FrogPilotListWidget(this);

  ScrollView *modelLabelsPanel = new ScrollView(modelLabelsList, this);

  modelLayout->addWidget(modelLabelsPanel);

  const std::vector<std::tuple<QString, QString, QString, QString>> modelToggles {
    {"AutomaticallyDownloadModels", tr("Automatically Download New Models"), tr("Automatically download new driving models as they become available."), ""},
    {"DeleteModel", tr("Delete Driving Models"), tr("Delete driving models from the device."), ""},
    {"DownloadModel", tr("Download Driving Models"), tr("Download driving models to the device."), ""},
    {"ModelRandomizer", tr("Model Randomizer"), tr("Driving models are chosen at random each drive and feedback prompts are used to find the model that best suits your needs."), ""},
    {"StopDistance", tr("Stop Distance"), tr("Adjust the model's stopping distance in meters (minimum 4 for safety). Most users prefer 6."), ""},
    {"ManageBlacklistedModels", tr("Manage Model Blacklist"), tr("Add or remove models from the <b>Model Randomizer</b>'s blacklist list."), ""},
    {"ManageScores", tr("Manage Model Ratings"), tr("Reset or view the saved ratings for the driving models."), ""},
    {"SelectModel", tr("Select Driving Model"), tr("Select the active driving model."), ""},
  };

  FrogPilotParamValueButtonControl *stopDistanceToggle = nullptr;

  for (const auto &[param, title, desc, icon] : modelToggles) {
    AbstractControl *modelToggle;

    if (param == "DeleteModel") {
      deleteModelButton = new FrogPilotButtonsControl(title, desc, icon, {tr("DELETE"), tr("DELETE ALL")});
      QObject::connect(deleteModelButton, &FrogPilotButtonsControl::buttonClicked, [this](int id) {
        QMap<QString, QString> deletableModelsMap = getDeletableModelDisplayNames();
        noModelsDownloaded = deletableModelsMap.isEmpty();

        if (noModelsDownloaded) {
          return;
        }

        if (id == 0) {
          // Group deletable models by series and keep a lookup for selected names
          QMap<QString, QStringList> deletableSeriesToModels;
          QMap<QString, QString> displayNameToKey;
          QMap<QString, QString> deletableFileToNameMap;
          for (auto it = deletableModelsMap.constBegin(); it != deletableModelsMap.constEnd(); ++it) {
            const QString &modelKey = it.key();
            const QString &displayName = it.value();
            QString series = modelSeriesMap.value(modelKey, tr("Custom Series"));
            deletableSeriesToModels[series].append(displayName);
            displayNameToKey.insert(displayName, modelKey);
            deletableFileToNameMap.insert(modelKey, displayName);
          }

          // Sort models within each series
          for (QString &series : deletableSeriesToModels.keys()) {
            QStringList &models = deletableSeriesToModels[series];
            models.removeDuplicates();
            std::sort(models.begin(), models.end());
          }

          QString savedSortMode = QString::fromStdString(params.get("ModelSortMode"));
          if (savedSortMode.isEmpty()) savedSortMode = "alphabetical";

          QString modelToDelete = ExpandableMultiOptionDialog::getSelection(tr("Select a driving model to delete"), deletableSeriesToModels, "", this,
                                                                           QStringList(), QStringList(), QMap<QString, QString>(),
                                                                           deletableFileToNameMap, savedSortMode);
          if (!modelToDelete.isEmpty()) {
            QString modelKey = displayNameToKey.value(modelToDelete);
            if (modelKey.isEmpty()) {
              QString processedName = processModelName(modelToDelete);
              for (auto it = deletableModelsMap.constBegin(); it != deletableModelsMap.constEnd(); ++it) {
                if (processModelName(it.value()) == processedName) {
                  modelKey = it.key();
                  break;
                }
              }
            }

            if (!modelKey.isEmpty() && ConfirmationDialog::confirm(tr("Are you sure you want to delete the \"%1\" model?").arg(modelToDelete), tr("Delete"), this)) {
              for (const QString &file : modelDir.entryList(QDir::Files)) {
                QString base = QFileInfo(file).baseName();
                if (base.startsWith(modelKey)) {
                  QFile::remove(modelDir.filePath(file));
                }
              }

              allModelsDownloaded = false;
              noModelsDownloaded = getDeletableModelDisplayNames().isEmpty();
              deleteModelButton->setEnabled(!(allModelsDownloading || modelDownloading || noModelsDownloaded));
            }
          }
        } else if (id == 1) {
          if (ConfirmationDialog::confirm(tr("Are you sure you want to delete all of your downloaded driving models?"), tr("Delete"), this)) {
            const QList<QString> deletableKeys = deletableModelsMap.keys();
            for (const QString &file : modelDir.entryList(QDir::Files)) {
              QString base = QFileInfo(file).baseName();
              for (const QString &modelKey : deletableKeys) {
                if (base.startsWith(modelKey)) {
                  QFile::remove(modelDir.filePath(file));
                  break;
                }
              }
            }

            allModelsDownloaded = false;
            noModelsDownloaded = true;
            deleteModelButton->setEnabled(false);
          }
        }
      });
      modelToggle = deleteModelButton;
    } else if (param == "DownloadModel") {
      downloadModelButton = new FrogPilotButtonsControl(title, desc, icon, {tr("DOWNLOAD"), tr("DOWNLOAD ALL")});
      QObject::connect(downloadModelButton, &FrogPilotButtonsControl::buttonClicked, [this](int id) {
        if (id == 0) {
          if (modelDownloading) {
            params_memory.putBool("CancelModelDownload", true);

            cancellingDownload = true;
        } else {
          QMap<QString, QStringList> downloadableSeriesToModels;
          QStringList downloadableModelNames;

          for (auto it = modelFileToNameMap.constBegin(); it != modelFileToNameMap.constEnd(); ++it) {
            const QString &modelKey = it.key();
            const QString &modelName = it.value();
            if (modelName.isEmpty() || isModelInstalled(modelKey)) {
              continue;
            }

            QString series = modelSeriesMap.value(modelKey, tr("Custom Series"));
            downloadableSeriesToModels[series].append(modelName);
            if (!downloadableModelNames.contains(modelName)) {
              downloadableModelNames.append(modelName);
            }
          }

          allModelsDownloaded = downloadableModelNames.isEmpty();
          if (allModelsDownloaded) {
            return;
          }

          for (QString &series : downloadableSeriesToModels.keys()) {
            QStringList &models = downloadableSeriesToModels[series];
            models.removeDuplicates();
            std::sort(models.begin(), models.end());
          }

          QStringList userFavorites = QString::fromStdString(params.get("UserFavorites")).split(",");
          userFavorites.removeAll("");

          QStringList communityFavorites = QString::fromStdString(params.get("CommunityFavorites")).split(",");
          communityFavorites.removeAll("");

          QString savedSortMode = QString::fromStdString(params.get("ModelSortMode"));
          if (savedSortMode.isEmpty()) savedSortMode = "alphabetical";

          ExpandableMultiOptionDialog dialog(
              tr("Select a driving model to download"),
              downloadableSeriesToModels,
              "",
              this,
              userFavorites,
              communityFavorites,
              modelReleasedDates,
              modelFileToNameMap,
              savedSortMode);

          int dialogResult = dialog.exec();

          QString sortMode = dialog.getCurrentSortMode();
          QStringList newUserFavs = dialog.getUserFavorites();
          params.put("ModelSortMode", sortMode.toStdString());
          params.put("UserFavorites", newUserFavs.join(",").toStdString());
          userFavorites = newUserFavs;

          if (dialogResult == QDialog::Accepted) {
            QString modelToDownload = dialog.selection;
            if (!modelToDownload.isEmpty()) {
              QString modelKey = modelFileToNameMap.key(modelToDownload);
              params_memory.put("ModelToDownload", modelKey.toStdString());
              // Also persist the version for this downloaded model if known
              {
                QFile vf("/data/models/.model_versions.json");
                if (vf.open(QIODevice::ReadOnly)) {
                  auto doc = QJsonDocument::fromJson(vf.readAll());
                  if (doc.isObject()) {
                    auto obj = doc.object();
                    if (obj.contains(modelKey)) {
                      params.put("ModelVersion", obj.value(modelKey).toString().toStdString());
                    }
                  }
                }
              }
                params_memory.put("ModelDownloadProgress", "Downloading...");

                downloadModelButton->setText(0, tr("CANCEL"));

                downloadModelButton->setValue("Downloading...");

                downloadModelButton->setVisibleButton(1, false);

                modelDownloading = true;
              }
            }
          }
        } else if (id == 1) {
          if (allModelsDownloading) {
            params_memory.putBool("CancelModelDownload", true);

            cancellingDownload = true;
          } else {
            params_memory.putBool("DownloadAllModels", true);
            params_memory.put("ModelDownloadProgress", "Downloading...");

            downloadModelButton->setText(1, tr("CANCEL"));

            downloadModelButton->setValue("Downloading...");

            downloadModelButton->setVisibleButton(0, false);

            allModelsDownloading = true;
          }
        }
      });
      modelToggle = downloadModelButton;
    } else if (param == "ManageBlacklistedModels") {
      FrogPilotButtonsControl *blacklistBtn = new FrogPilotButtonsControl(title, desc, icon, {tr("ADD"), tr("REMOVE"), tr("REMOVE ALL")});
      QObject::connect(blacklistBtn, &FrogPilotButtonsControl::buttonClicked, [this](int id) {
        QStringList blacklistedModels = QString::fromStdString(params.get("BlacklistedModels")).split(",");
        blacklistedModels.removeAll("");

        if (id == 0) {
          QStringList blacklistableModels;
          for (const QString &model : modelFileToNameMapProcessed.keys()) {
            if (!blacklistedModels.contains(model)) {
              blacklistableModels.append(modelFileToNameMapProcessed.value(model));
            }
          }

          if (blacklistableModels.size() <= 1) {
            ConfirmationDialog::alert(tr("There are no more models to blacklist! The only available model is \"%1\"!").arg(blacklistableModels.first()), this);
          } else {
            // Group blacklistable models by series
            QMap<QString, QStringList> blacklistableSeriesToModels;
            for (const QString &modelName : blacklistableModels) {
              QString modelKey = modelFileToNameMapProcessed.key(modelName);
              QString series = modelSeriesMap.value(modelKey, "Custom Series");
              blacklistableSeriesToModels[series].append(modelName);
            }

            // Sort models within each series
            for (QString &series : blacklistableSeriesToModels.keys()) {
              blacklistableSeriesToModels[series].sort();
            }

            QString modelToBlacklist = ExpandableMultiOptionDialog::getSelection(tr("Select a model to add to the blacklist"), blacklistableSeriesToModels, "", this);
            if (!modelToBlacklist.isEmpty()) {
              if (ConfirmationDialog::confirm(tr("Are you sure you want to add the \"%1\" model to the blacklist?").arg(modelToBlacklist), tr("Add"), this)) {
                blacklistedModels.append(modelFileToNameMapProcessed.key(modelToBlacklist));

                params.put("BlacklistedModels", blacklistedModels.join(",").toStdString());
              }
            }
          }
        } else if (id == 1) {
          QStringList whitelistableModels;
          for (const QString &model : blacklistedModels) {
            QString modelName = modelFileToNameMapProcessed.value(model);
            whitelistableModels.append(modelName);
          }

          // Group whitelistable models by series
          QMap<QString, QStringList> whitelistableSeriesToModels;
          for (const QString &modelName : whitelistableModels) {
            QString modelKey = modelFileToNameMapProcessed.key(modelName);
            QString series = modelSeriesMap.value(modelKey, "Custom Series");
            whitelistableSeriesToModels[series].append(modelName);
          }

          // Sort models within each series
          for (QString &series : whitelistableSeriesToModels.keys()) {
            whitelistableSeriesToModels[series].sort();
          }

          QString modelToWhitelist = ExpandableMultiOptionDialog::getSelection(tr("Select a model to remove from the blacklist"), whitelistableSeriesToModels, "", this);
          if (!modelToWhitelist.isEmpty()) {
            if (ConfirmationDialog::confirm(tr("Are you sure you want to remove the \"%1\" model from the blacklist?").arg(modelToWhitelist), tr("Remove"), this)) {
              blacklistedModels.removeAll(modelFileToNameMapProcessed.key(modelToWhitelist));

              params.put("BlacklistedModels", blacklistedModels.join(",").toStdString());
            }
          }
        } else if (id == 2) {
          if (FrogPilotConfirmationDialog::yesorno(tr("Are you sure you want to remove all of your blacklisted models?"), this)) {
            params.remove("BlacklistedModels");
            params_cache.remove("BlacklistedModels");
          }
        }
      });
      modelToggle = blacklistBtn;
    } else if (param == "ManageScores") {
      FrogPilotButtonsControl *manageScoresBtn = new FrogPilotButtonsControl(title, desc, icon, {tr("RESET"), tr("VIEW")});
      QObject::connect(manageScoresBtn, &FrogPilotButtonsControl::buttonClicked, [this, modelLayout, modelLabelsList, modelLabelsPanel](int id) {
        if (id == 0) {
          if (FrogPilotConfirmationDialog::yesorno(tr("Are you sure you want to reset all of your model drives and scores?"), this)) {
            params.remove("ModelDrivesAndScores");
            params_cache.remove("ModelDrivesAndScores");
          }
        } else if (id == 1) {
          openSubPanel();

          updateModelLabels(modelLabelsList);

          modelLayout->setCurrentWidget(modelLabelsPanel);
        }
      });
      modelToggle = manageScoresBtn;
    } else if (param == "SelectModel") {
      selectModelButton = new ButtonControl(title, tr("SELECT"), desc);
      QObject::connect(selectModelButton, &ButtonControl::clicked, [this]() {
        // Group models by series for the enhanced dialog
        QMap<QString, QStringList> seriesToModels;
        QMap<QString, QString> installedModelFileToNameMap;
        QMap<QString, QString> installedReleasedDates;

        // Add all available models by series
        for (const QString &modelKey : modelFileToNameMap.keys()) {
          if (!isModelInstalled(modelKey)) {
            continue;
          }

          QString modelName = modelFileToNameMap.value(modelKey);
          if (modelName.contains("(Default)")) {
            continue;
          }

          installedModelFileToNameMap.insert(modelKey, modelName);
          if (modelReleasedDates.contains(modelKey)) {
            installedReleasedDates.insert(modelKey, modelReleasedDates.value(modelKey));
          }

          QString series = modelSeriesMap.value(modelKey, "Custom Series");
          seriesToModels[series].append(modelName);
        }

        // Sort models alphabetically within each series
        for (QString &series : seriesToModels.keys()) {
          seriesToModels[series].sort();
        }

        // Add default model to the beginning of its series
        QString defaultModelName = modelFileToNameMap.value(QString::fromStdString(params_default.get("Model")));
        QString defaultSeries = modelSeriesMap.value(QString::fromStdString(params_default.get("Model")), "Custom Series");
        if (seriesToModels.contains(defaultSeries) && seriesToModels[defaultSeries].contains(defaultModelName)) {
          seriesToModels[defaultSeries].removeAll(defaultModelName);
          seriesToModels[defaultSeries].prepend(defaultModelName);
        }

        // Prepare favorites and dates for the enhanced dialog
        QStringList userFavs = QString::fromStdString(params.get("UserFavorites")).split(",");
        userFavs.removeAll("");

        QStringList communityFavs = QString::fromStdString(params.get("CommunityFavorites")).split(",");
        communityFavs.removeAll("");

        // Create dialog instance to access sort mode and favorites after selection
        QString savedSortMode = QString::fromStdString(params.get("ModelSortMode"));
        if (savedSortMode.isEmpty()) savedSortMode = "alphabetical";

        ExpandableMultiOptionDialog dialog(tr("Select a model - 🗺️ = Navigation | 📡 = Radar | 👀 = VOACC"),
                                          seriesToModels, currentModel, this,
                                          userFavs, communityFavs, installedReleasedDates, installedModelFileToNameMap, savedSortMode);

        int dialogResult = dialog.exec();

        // Persist sort mode and user favorites even if no selection was made
        QString sortMode = dialog.getCurrentSortMode();
        QStringList newUserFavs = dialog.getUserFavorites();
        params.put("ModelSortMode", sortMode.toStdString());
        params.put("UserFavorites", newUserFavs.join(",").toStdString());

        if (dialogResult == QDialog::Accepted) {
          QString modelToSelect = dialog.selection;
          if (!modelToSelect.isEmpty()) {
            currentModel = modelToSelect;

            params.put("Model", modelFileToNameMap.key(modelToSelect).toStdString());
            // Sync ModelVersion with the selected model if known
            {
              QString modelKey = modelFileToNameMap.key(modelToSelect);
              QFile vf("/data/models/.model_versions.json");
              if (vf.open(QIODevice::ReadOnly)) {
                auto doc = QJsonDocument::fromJson(vf.readAll());
                if (doc.isObject()) {
                  auto obj = doc.object();
                  if (obj.contains(modelKey)) {
                    params.put("ModelVersion", obj.value(modelKey).toString().toStdString());
                  }
                }
              }
            }

            updateFrogPilotToggles();

            if (started) {
              if (FrogPilotConfirmationDialog::toggleReboot(this)) {
                Hardware::reboot();
              }
            }
            selectModelButton->setValue(modelToSelect);

            noModelsDownloaded = getDeletableModelDisplayNames().isEmpty();
            deleteModelButton->setEnabled(!(allModelsDownloading || modelDownloading || noModelsDownloaded));
          }
        }
      });
      modelToggle = selectModelButton;

    } else if (param == "StopDistance") {
      std::vector<QString> stopDistanceButton{"Reset"};
      modelToggle = new FrogPilotParamValueButtonControl(param, title, desc, icon, 4.0, 10.0, QString(), std::map<float, QString>(), 0.1, false, {}, stopDistanceButton, false, false);
      stopDistanceToggle = static_cast<FrogPilotParamValueButtonControl*>(modelToggle);
    } else {
      modelToggle = new ParamControl(param, title, desc, icon);
    }

    toggles[param] = modelToggle;

    modelList->addItem(modelToggle);

    QObject::connect(modelToggle, &AbstractControl::showDescriptionEvent, [this]() {
      update();
    });
  }

  QObject::connect(static_cast<ToggleControl*>(toggles["ModelRandomizer"]), &ToggleControl::toggleFlipped, [this](bool state) {
    updateToggles();

    if (state && !allModelsDownloaded) {
      if (FrogPilotConfirmationDialog::yesorno(tr("The \"Model Randomizer\" only works with downloaded models. Do you want to download all the driving models?"), this)) {
        params_memory.putBool("DownloadAllModels", true);
        params_memory.put("ModelDownloadProgress", "Downloading...");

        downloadModelButton->setValue("Downloading...");

        allModelsDownloading = true;
      }
    }
  });

  if (stopDistanceToggle) {
    QObject::connect(stopDistanceToggle, &FrogPilotParamValueButtonControl::buttonClicked, [this, stopDistanceToggle]() {
      if (ConfirmationDialog::confirm(tr("Are you sure you want to reset your <b>Stop Distance</b> to the default of 6 meters?"), tr("Reset"), this)) {
        params.putFloat("StopDistance", 6.0);
        stopDistanceToggle->refresh();
        updateFrogPilotToggles();
      }
    });
  }

  QObject::connect(parent, &FrogPilotSettingsWindow::closeSubPanel, [modelLayout, modelPanel] {modelLayout->setCurrentWidget(modelPanel);});
  QObject::connect(uiState(), &UIState::uiUpdate, this, &FrogPilotModelPanel::updateState);
}

bool FrogPilotModelPanel::isModelInstalled(const QString &key) const {
  if (key.isEmpty()) {
    return false;
  }

  bool has_thneed = false;
  bool has_policy_meta = false;
  bool has_policy_tg = false;
  bool has_vision_meta = false;
  bool has_vision_tg = false;
  bool foundAny = false;

  for (const QString &file : modelDir.entryList(QDir::Files)) {
    QFileInfo fi(modelDir.filePath(file));
    const QString base = fi.baseName();
    const QString ext = fi.suffix();

    if (!(base.startsWith(key) || base.startsWith(key + "_"))) continue;

    foundAny = true;

    if (ext == "thneed") {
      has_thneed = true;
    } else if (ext == "pkl") {
      if (base.contains("_driving_policy_metadata")) {
        has_policy_meta = true;
      } else if (base.contains("_driving_policy_tinygrad")) {
        has_policy_tg = true;
      } else if (base.contains("_driving_vision_metadata")) {
        has_vision_meta = true;
      } else if (base.contains("_driving_vision_tinygrad")) {
        has_vision_tg = true;
      }
    }
  }

  if (has_thneed) {
    return true;
  }

  if (has_policy_meta && has_policy_tg && has_vision_meta && has_vision_tg) {
    return true;
  }

  return foundAny;
}

QMap<QString, QString> FrogPilotModelPanel::getDeletableModelDisplayNames() {
  QMap<QString, QString> deletable;

  QString defaultModelKey = QString::fromStdString(params_default.get("Model"));
  QString defaultModelName = modelFileToNameMap.value(defaultModelKey);
  QString processedDefault = processModelName(defaultModelName);
  QString processedCurrent = processModelName(currentModel);

  for (auto it = modelFileToNameMap.constBegin(); it != modelFileToNameMap.constEnd(); ++it) {
    const QString &modelKey = it.key();
    const QString &displayName = it.value();
    if (displayName.isEmpty()) {
      continue;
    }

    if (!isModelInstalled(modelKey)) {
      continue;
    }

    QString processedName = processModelName(displayName);
    if (!processedCurrent.isEmpty() && processedName == processedCurrent) {
      continue;
    }

    if (!processedDefault.isEmpty() && processedName == processedDefault) {
      continue;
    }

    deletable.insert(modelKey, displayName);
  }

  return deletable;
}

void FrogPilotModelPanel::showEvent(QShowEvent *event) {
  FrogPilotUIState &fs = *frogpilotUIState();
  UIState &s = *uiState();

  frogpilotToggleLevels = parent->frogpilotToggleLevels;
  tuningLevel = parent->tuningLevel;

  allModelsDownloading = params_memory.getBool("DownloadAllModels");
  modelDownloading = !params_memory.get("ModelToDownload").empty();

  QStringList availableModels = QString::fromStdString(params.get("AvailableModels")).split(",");
  availableModelNames = QString::fromStdString(params.get("AvailableModelNames")).split(",");
  availableModelSeries = QString::fromStdString(params.get("AvailableModelSeries")).split(",");
  QStringList releasedDatesParam = QString::fromStdString(params.get("ModelReleasedDates")).split(",");
  QStringList communityFavsParam = QString::fromStdString(params.get("CommunityFavorites")).split(",");
  QStringList userFavsParam = QString::fromStdString(params.get("UserFavorites")).split(",");

  // Build a simple model->version map for quick lookups elsewhere
  {
    QStringList versionList = QString::fromStdString(params.get("ModelVersions")).split(",");
    QJsonObject versionObj;
    int verCount = qMin(availableModels.size(), versionList.size());
    for (int i = 0; i < verCount; ++i) {
      versionObj.insert(availableModels[i], versionList[i]);
    }
    QFile out("/data/models/.model_versions.json");
    if (out.open(QIODevice::WriteOnly)) {
      out.write(QJsonDocument(versionObj).toJson());
      out.close();
    }
  }

  modelFileToNameMap.clear();
  modelFileToNameMapProcessed.clear();
  modelSeriesMap.clear();
  modelReleasedDates.clear();
  int size = qMin(availableModels.size(), availableModelNames.size());
  for (int i = 0; i < size; ++i) {
    const QString modelKey = availableModels[i].trimmed();
    const QString modelName = availableModelNames[i].trimmed();
    if (modelKey.isEmpty() || modelName.isEmpty()) {
      continue;
    }

    QString series;
    if (i < availableModelSeries.size()) {
      series = availableModelSeries[i].trimmed();
    }
    if (series.isEmpty()) {
      series = tr("Custom Series");
    }

    modelFileToNameMap.insert(modelKey, modelName);
    modelFileToNameMapProcessed.insert(modelKey, processModelName(modelName));
    modelSeriesMap.insert(modelKey, series);

    if (i < releasedDatesParam.size()) {
      const QString released = releasedDatesParam[i].trimmed();
      if (!released.isEmpty()) {
        this->modelReleasedDates.insert(modelKey, released);
      }
    }
  }
  allModelsDownloaded = true;
  for (auto it = modelFileToNameMap.constBegin(); it != modelFileToNameMap.constEnd(); ++it) {
    if (it.value().isEmpty()) {
      continue;
    }
    if (!isModelInstalled(it.key())) {
      allModelsDownloaded = false;
      break;
    }
  }

  QString modelKey = QString::fromStdString(params.get("Model"));
  if (!isModelInstalled(modelKey)) {
    modelKey = QString::fromStdString(params_default.get("Model"));
  }
  currentModel = modelFileToNameMap.value(modelKey);
  selectModelButton->setValue(currentModel);

  noModelsDownloaded = getDeletableModelDisplayNames().isEmpty();

  bool parked = !s.scene.started || fs.frogpilot_scene.parked || fs.frogpilot_toggles.value("frogs_go_moo").toBool();

  deleteModelButton->setEnabled(!(allModelsDownloading || modelDownloading || noModelsDownloaded));

  downloadModelButton->setEnabledButtons(0, !allModelsDownloaded && !allModelsDownloading && !cancellingDownload && fs.frogpilot_scene.online && parked);
  downloadModelButton->setEnabledButtons(1, !allModelsDownloaded && !modelDownloading && !cancellingDownload && fs.frogpilot_scene.online && parked);

  downloadModelButton->setValue(fs.frogpilot_scene.online ? (parked ? "" : "Not parked") : tr("Offline..."));

  started = s.scene.started;

  updateToggles();
}

void FrogPilotModelPanel::updateState(const UIState &s, const FrogPilotUIState &fs) {
  if (!isVisible() || finalizingDownload) {
    return;
  }

  bool parked = !started || fs.frogpilot_scene.parked || fs.frogpilot_toggles.value("frogs_go_moo").toBool();

  if (allModelsDownloading || modelDownloading) {
    QString progress = QString::fromStdString(params_memory.get("ModelDownloadProgress"));
    bool downloadFailed = progress.contains(QRegularExpression("cancelled|exists|failed|offline", QRegularExpression::CaseInsensitiveOption));

    if (progress != "Downloading...") {
      downloadModelButton->setValue(progress);
    }

    if (progress == "All models downloaded!" && allModelsDownloading || progress == "Downloaded!" && modelDownloading || downloadFailed) {
      finalizingDownload = true;

      QTimer::singleShot(2500, [this, progress]() {
        allModelsDownloaded = progress == "All models downloaded!";
        allModelsDownloading = false;
        cancellingDownload = false;
        finalizingDownload = false;
        modelDownloading = false;
        noModelsDownloaded = false;

        params_memory.remove("CancelModelDownload");
        params_memory.remove("DownloadAllModels");
        params_memory.remove("ModelDownloadProgress");
        params_memory.remove("ModelToDownload");

        downloadModelButton->setEnabled(true);
        downloadModelButton->setValue("");
      });
    }
  } else {
    downloadModelButton->setValue(fs.frogpilot_scene.online ? (parked ? "" : "Not parked") : tr("Offline..."));
  }

  deleteModelButton->setEnabled(!(allModelsDownloading || modelDownloading || noModelsDownloaded));

  downloadModelButton->setText(0, modelDownloading ? tr("CANCEL") : tr("DOWNLOAD"));
  downloadModelButton->setText(1, allModelsDownloading ? tr("CANCEL") : tr("DOWNLOAD ALL"));

  downloadModelButton->setEnabledButtons(0, !allModelsDownloaded && !allModelsDownloading && !cancellingDownload && fs.frogpilot_scene.online && parked);
  downloadModelButton->setEnabledButtons(1, !allModelsDownloaded && !modelDownloading && !cancellingDownload && fs.frogpilot_scene.online && parked);

  downloadModelButton->setVisibleButton(0, !allModelsDownloading);
  downloadModelButton->setVisibleButton(1, !modelDownloading);

  started = s.scene.started;

  parent->keepScreenOn = allModelsDownloading || modelDownloading;
}

void FrogPilotModelPanel::updateModelLabels(FrogPilotListWidget *labelsList) {
  labelsList->clear();

  QJsonObject modelDrivesAndScores = QJsonDocument::fromJson(QString::fromStdString(params.get("ModelDrivesAndScores")).toUtf8()).object();

  for (const QString &modelName : availableModelNames) {
    QJsonObject modelData = modelDrivesAndScores.value(processModelName(modelName)).toObject();

    int drives = modelData.value("Drives").toInt(0);
    int score = modelData.value("Score").toInt(0);

    QString drivesDisplay = drives == 1 ? QString("%1 Drive").arg(drives) : drives > 0 ? QString("%1 Drives").arg(drives) : "N/A";
    QString scoreDisplay = drives > 0 ? QString("Score: %1%").arg(score) : "N/A";

    QString labelTitle = processModelName(modelName);
    QString labelText = QString("%1 (%2)").arg(scoreDisplay, drivesDisplay);

    LabelControl *labelControl = new LabelControl(labelTitle, labelText, "", this);
    labelsList->addItem(labelControl);
  }
}

void FrogPilotModelPanel::updateToggles() {
  for (auto &[key, toggle] : toggles) {
    bool setVisible = tuningLevel >= frogpilotToggleLevels[key].toDouble();

    if (key == "ManageBlacklistedModels" || key == "ManageScores") {
      setVisible &= params.getBool("ModelRandomizer");
    } else if (key == "SelectModel") {
      setVisible &= !params.getBool("ModelRandomizer");
    } else if (key == "StopDistance") {
      setVisible &= (tuningLevel == 3); // Only visible in developer tuning level
    }

    toggle->setVisible(setVisible);
  }

  update();
}
