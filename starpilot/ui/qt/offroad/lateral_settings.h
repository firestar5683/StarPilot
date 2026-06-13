#pragma once

#include "starpilot/ui/qt/offroad/starpilot_settings.h"

class StarPilotLateralPanel : public StarPilotListWidget {
  Q_OBJECT

public:
  explicit StarPilotLateralPanel(StarPilotSettingsWindow *parent, bool forceOpen = false);

signals:
  void openSubPanel();

protected:
  void showEvent(QShowEvent *event) override;

private:
  void updateMetric(bool metric, bool bootRun);
  void updateState(const UIState &s);
  void updateToggles();

  bool forceOpenDescriptions;
  bool started;

  std::map<QString, AbstractControl*> toggles;

  QSet<QString> advancedLateralTuneKeys = {"ForceAutoTune", "ForceAutoTuneOff", "ForceTorqueController", "SteerDelay", "SteerFriction", "SteerLatAccel", "SteerKP", "SteerRatio"};
  QSet<QString> aolKeys = {"PauseAOLOnBrake"};
  QSet<QString> laneChangeKeys = {"LaneChangeSmoothing", "LaneChangeTime", "LaneDetectionWidth", "MinimumLaneChangeSpeed", "NudgelessLaneChange", "OneLaneChange"};
  QSet<QString> lateralTuneKeys = {"NNFF", "NNFFLite", "TurnDesires", "NavDesiresAllowed"};
  QSet<QString> qolKeys = {"PauseLateralSpeed", "LateralResumeDelay"};

  QSet<QString> parentKeys;

  StarPilotParamValueButtonControl *steerDelayToggle;
  StarPilotParamValueButtonControl *steerFrictionToggle;
  StarPilotParamValueButtonControl *steerLatAccelToggle;
  StarPilotParamValueButtonControl *steerKPToggle;
  StarPilotParamValueButtonControl *steerRatioToggle;

  StarPilotSettingsWindow *parent;

  Params params;
};
