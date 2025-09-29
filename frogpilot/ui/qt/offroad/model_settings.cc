#include "frogpilot/ui/qt/offroad/model_settings.h"
#include "frogpilot/ui/qt/offroad/expandable_multi_option_dialog.h"
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QDoubleSpinBox>
#include <QPushButton>

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
        QStringList deletableModels;
        for (const QString &file : modelDir.entryList(QDir::Files)) {
          QString base = QFileInfo(file).baseName();
          for (const QString &modelKey : modelFileToNameMapProcessed.keys()) {
            if (base.startsWith(modelKey)) {
              QString modelName = modelFileToNameMapProcessed.value(modelKey);
              if (!deletableModels.contains(modelName)) {
                deletableModels.append(modelName);
              }
            }
          }
        }
        deletableModels.removeAll(processModelName(currentModel));
        deletableModels.removeAll(modelFileToNameMapProcessed.value(QString::fromStdString(params_default.get("Model"))));
        deletableModels.removeAll("Space Lab");
        noModelsDownloaded = deletableModels.isEmpty();

        if (id == 0) {
          // Group deletable models by series
          QMap<QString, QStringList> deletableSeriesToModels;
          for (const QString &modelName : deletableModels) {
            QString modelKey = modelFileToNameMapProcessed.key(modelName);
            QString series = modelSeriesMap.value(modelKey, "Custom Series");
            deletableSeriesToModels[series].append(modelName);
          }

          // Sort models within each series
          for (QString &series : deletableSeriesToModels.keys()) {
            deletableSeriesToModels[series].sort();
          }

          QString modelToDelete = ExpandableMultiOptionDialog::getSelection(tr("Select a driving model to delete"), deletableSeriesToModels, "", this);
          if (!modelToDelete.isEmpty() && ConfirmationDialog::confirm(tr("Are you sure you want to delete the \"%1\" model?").arg(modelToDelete), tr("Delete"), this)) {
            QString modelFile = modelFileToNameMapProcessed.key(modelToDelete);
            for (const QString &file : modelDir.entryList(QDir::Files)) {
              QString base = QFileInfo(file).baseName();
              if (base.startsWith(modelFile)) {
                QFile::remove(modelDir.filePath(file));
              }
            }

            allModelsDownloaded = false;
          }
        } else if (id == 1) {
          if (ConfirmationDialog::confirm(tr("Are you sure you want to delete all of your downloaded driving models?"), tr("Delete"), this)) {
            for (const QString &file : modelDir.entryList(QDir::Files)) {
              QString base = QFileInfo(file).baseName();
              for (const QString &modelKey : modelFileToNameMapProcessed.keys()) {
                QString modelName = modelFileToNameMapProcessed.value(modelKey);
                if (deletableModels.contains(modelName) && base.startsWith(modelKey)) {
                  QFile::remove(modelDir.filePath(file));
                  break;
                }
              }
            }

            allModelsDownloaded = false;
            noModelsDownloaded = true;
          }
        }
      });
      modelToggle = deleteModelButton;
    } else if (param == "DownloadModel") {
      downloadModelButton = new FrogPilotButtonsControl(title, desc, icon, {tr("DOWNLOAD"), tr("DOWNLOAD ALL")});
      QObject::connect(downloadModelButton, &FrogPilotButtonsControl::buttonClicked, [this](int id) {
        auto isInstalled = [this](const QString &key) {
          bool has_thneed = false;
          bool has_policy_meta = false;
          bool has_policy_tg = false;
          bool has_vision_meta = false;
          bool has_vision_tg = false;

          for (const QString &file : modelDir.entryList(QDir::Files)) {
            QFileInfo fi(modelDir.filePath(file));
            const QString base = fi.baseName();
            const QString ext = fi.suffix();
            if (!(base.startsWith(key) || base.startsWith(key + "_"))) continue;

            if (ext == "thneed") {
              // Classic model (WD-40 etc.)
              has_thneed = true;
            } else if (ext == "pkl") {
              // TinyGrad bundle uses these four exact suffixes
              if (base.contains("_driving_policy_metadata"))       has_policy_meta  = true;
              else if (base.contains("_driving_policy_tinygrad"))  has_policy_tg    = true;
              else if (base.contains("_driving_vision_metadata"))  has_vision_meta  = true;
              else if (base.contains("_driving_vision_tinygrad"))  has_vision_tg    = true;
            }
          }

          // Classic models: any matching .thneed counts as installed
          if (has_thneed) return true;
          // TinyGrad models: require all four policy/vision files to be present
          return has_policy_meta && has_policy_tg && has_vision_meta && has_vision_tg;
        };
        if (id == 0) {
          if (modelDownloading) {
            params_memory.putBool("CancelModelDownload", true);

            cancellingDownload = true;
          } else {
            QStringList downloadableModels = availableModelNames;
            for (const QString &modelKey : modelFileToNameMap.keys()) {
              QString modelName = modelFileToNameMap.value(modelKey);
              if (isInstalled(modelKey)) {
                downloadableModels.removeAll(modelName);
              }
            }
            downloadableModels.removeAll("Space Lab 👀📡");
            allModelsDownloaded = downloadableModels.isEmpty();

            // Group downloadable models by series
            QMap<QString, QStringList> downloadableSeriesToModels;
            for (const QString &modelName : downloadableModels) {
              QString modelKey = modelFileToNameMap.key(modelName);
              QString series = modelSeriesMap.value(modelKey, "Custom Series");
              downloadableSeriesToModels[series].append(modelName);
            }

            // Sort models within each series
            for (QString &series : downloadableSeriesToModels.keys()) {
              downloadableSeriesToModels[series].sort();
            }

            QString modelToDownload = ExpandableMultiOptionDialog::getSelection(tr("Select a driving model to download"), downloadableSeriesToModels, "", this);
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
        auto isInstalled = [this](const QString &key) {
          bool has_thneed = false;
          bool has_policy_meta = false;
          bool has_policy_tg = false;
          bool has_vision_meta = false;
          bool has_vision_tg = false;

          for (const QString &file : modelDir.entryList(QDir::Files)) {
            QFileInfo fi(modelDir.filePath(file));
            const QString base = fi.baseName();
            const QString ext = fi.suffix();
            if (!(base.startsWith(key) || base.startsWith(key + "_"))) continue;

            if (ext == "thneed") {
              // Classic model (WD-40 etc.)
              has_thneed = true;
            } else if (ext == "pkl") {
              // TinyGrad bundle uses these four exact suffixes
              if (base.contains("_driving_policy_metadata"))       has_policy_meta  = true;
              else if (base.contains("_driving_policy_tinygrad"))  has_policy_tg    = true;
              else if (base.contains("_driving_vision_metadata"))  has_vision_meta  = true;
              else if (base.contains("_driving_vision_tinygrad"))  has_vision_tg    = true;
            }
          }

          // Classic models: any matching .thneed counts as installed
          if (has_thneed) return true;
          // TinyGrad models: require all four policy/vision files to be present
          return has_policy_meta && has_policy_tg && has_vision_meta && has_vision_tg;
        };
        // Group models by series
        QMap<QString, QStringList> seriesToModels;
        for (const QString &modelKey : modelFileToNameMap.keys()) {
          QString modelName = modelFileToNameMap.value(modelKey);
          if (modelName.contains("(Default)")) {
            continue;
          }

          if (isInstalled(modelKey)) {
            QString series = modelSeriesMap.value(modelKey, "Dom Forgot To Label Me");
            seriesToModels[series].append(modelName);
          }
        }

        // Add Space Lab to Custom Series
        QString spaceLabName = modelFileToNameMap.value("space-lab");
        if (isInstalled("space-lab")) {
          seriesToModels["Custom Series"].append(spaceLabName);
        }

        // Sort models within each series
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

        QString modelToSelect = ExpandableMultiOptionDialog::getSelection(tr("Select a model - 🗺️ = Navigation | 📡 = Radar | 👀 = VOACC"), seriesToModels, currentModel, this);
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

          QStringList deletableModels;
          for (const QString &file : modelDir.entryList(QDir::Files)) {
            QString base = QFileInfo(file).baseName();
            for (const QString &modelKey : modelFileToNameMapProcessed.keys()) {
              if (base.startsWith(modelKey)) {
                QString modelName = modelFileToNameMapProcessed.value(modelKey);
                if (!deletableModels.contains(modelName)) {
                  deletableModels.append(modelName);
                }
              }
            }
          }
          deletableModels.removeAll(processModelName(currentModel));
          deletableModels.removeAll(modelFileToNameMapProcessed.value(QString::fromStdString(params_default.get("Model"))));
          noModelsDownloaded = deletableModels.isEmpty();
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
  int size = qMin(qMin(availableModels.size(), availableModelNames.size()), availableModelSeries.size());
  for (int i = 0; i < size; ++i) {
    modelFileToNameMap.insert(availableModels[i], availableModelNames[i]);
    modelFileToNameMapProcessed.insert(availableModels[i], processModelName(availableModelNames[i]));
    modelSeriesMap.insert(availableModels[i], availableModelSeries[i]);
  }
  modelFileToNameMap.insert("space-lab", "Space Lab 👀📡");
  modelFileToNameMapProcessed.insert("space-lab", "Space Lab");
  modelSeriesMap.insert("space-lab", "Dom Forgot To Label Me");

  auto isInstalled = [this](const QString &key) {
    bool has_thneed = false;
    bool has_policy_meta = false;
    bool has_policy_tg = false;
    bool has_vision_meta = false;
    bool has_vision_tg = false;

    for (const QString &file : modelDir.entryList(QDir::Files)) {
      QFileInfo fi(modelDir.filePath(file));
      const QString base = fi.baseName();
      const QString ext = fi.suffix();
      if (!(base.startsWith(key) || base.startsWith(key + "_"))) continue;

      if (ext == "thneed") {
        // Classic model (WD-40 etc.)
        has_thneed = true;
      } else if (ext == "pkl") {
        // TinyGrad bundle uses these four exact suffixes
        if (base.contains("_driving_policy_metadata"))       has_policy_meta  = true;
        else if (base.contains("_driving_policy_tinygrad"))  has_policy_tg    = true;
        else if (base.contains("_driving_vision_metadata"))  has_vision_meta  = true;
        else if (base.contains("_driving_vision_tinygrad"))  has_vision_tg    = true;
      }
    }

    // Classic models: any matching .thneed counts as installed
    if (has_thneed) return true;
    // TinyGrad models: require all four policy/vision files to be present
    return has_policy_meta && has_policy_tg && has_vision_meta && has_vision_tg;
  };
  QStringList downloadableModels = availableModelNames;
  for (const QString &modelKey : modelFileToNameMap.keys()) {
    QString modelName = modelFileToNameMap.value(modelKey);
    if (isInstalled(modelKey)) {
      downloadableModels.removeAll(modelName);
    }
  }
  allModelsDownloaded = downloadableModels.isEmpty();

  QStringList deletableModels;
  for (const QString &file : modelDir.entryList(QDir::Files)) {
    QString base = QFileInfo(file).baseName();
    for (const QString &modelKey : modelFileToNameMapProcessed.keys()) {
      if (base.startsWith(modelKey)) {
        QString modelName = modelFileToNameMapProcessed.value(modelKey);
        if (!deletableModels.contains(modelName)) {
          deletableModels.append(modelName);
        }
      }
    }
  }
  deletableModels.removeAll(processModelName(currentModel));
  deletableModels.removeAll(modelFileToNameMapProcessed.value(QString::fromStdString(params_default.get("Model"))));
  noModelsDownloaded = deletableModels.isEmpty();

  QString modelKey = QString::fromStdString(params.get("Model"));
  if (!isInstalled(modelKey)) {
    modelKey = QString::fromStdString(params_default.get("Model"));
  }
  currentModel = modelFileToNameMap.value(modelKey);
  selectModelButton->setValue(currentModel);

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
    }

    else if (key == "SelectModel") {
      setVisible &= !params.getBool("ModelRandomizer");
    } else if (key == "StopDistance") {
      setVisible &= (tuningLevel == 3); // Only visible in developer tuning level
    }

    toggle->setVisible(setVisible);
  }

  update();
}
