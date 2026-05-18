#pragma once

#include "starpilot/ui/qt/offroad/starpilot_settings.h"

class StarPilotDevicePanel : public StarPilotListWidget {
  Q_OBJECT

public:
  explicit StarPilotDevicePanel(StarPilotSettingsWindow *parent, bool forceOpen = false);

signals:
  void openSubPanel();

protected:
  void showEvent(QShowEvent *event) override;

private:
  void updateState(const UIState &s);
  void updateToggles();

  bool forceOpenDescriptions;
  bool started;

  std::map<QString, AbstractControl*> toggles;

  QSet<QString> deviceManagementKeys = {"DeviceShutdown", "DisableWideRoad", "HigherBitrate", "IncreaseThermalLimits", "LowVoltageShutdown", "NoLogging", "NoUploads", "UseKonikServer"};
  QSet<QString> screenKeys = {"ScreenBrightness", "ScreenBrightnessOnroad", "ScreenRecorder", "ScreenTimeout", "ScreenTimeoutOnroad", "StandbyMode"};

  QSet<QString> parentKeys;

  StarPilotSettingsWindow *parent;

  Params params;
};
