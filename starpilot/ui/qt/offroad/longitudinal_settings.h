#pragma once

#include "starpilot/ui/qt/offroad/starpilot_settings.h"

class StarPilotLongitudinalPanel : public StarPilotListWidget {
  Q_OBJECT

public:
  explicit StarPilotLongitudinalPanel(StarPilotSettingsWindow *parent, bool forceOpen = false);

signals:
  void openSubPanel();
  void openSubSubPanel();
  void openSubSubSubPanel();

protected:
  void showEvent(QShowEvent *event) override;

private:
  void updateMetric(bool metric, bool bootRun);
  void updateToggles();

  bool customPersonalityOpen;
  bool forceOpenDescriptions;
  bool qolOpen;
  bool slcOpen;
  bool weatherOpen;

  std::map<QString, AbstractControl*> toggles;

  QSet<QString> advancedLongitudinalTuneKeys = {"EVTuning", "TruckTuning", "LongitudinalActuatorDelay", "MaxDesiredAcceleration", "StartAccel", "StopAccel", "StoppingDecelRate", "VEgoStarting", "VEgoStopping"};
  QSet<QString> aggressivePersonalityKeys = {"AggressiveFollow", "AggressiveFollowHigh", "AggressiveJerkAcceleration", "AggressiveJerkDeceleration", "AggressiveJerkDanger", "AggressiveJerkSpeed", "AggressiveJerkSpeedDecrease", "ResetAggressivePersonality"};
  QSet<QString> conditionalExperimentalKeys = {"PersistExperimentalState", "CESpeed", "CESpeedLead", "CECurves", "CELead", "CEModelStopTime", "CESignalSpeed", "CEStopLights", "ShowCEMStatus"};
  QSet<QString> curveSpeedKeys = {"CalibratedLateralAcceleration", "CalibrationProgress", "ResetCurveData", "ShowCSCStatus"};
  QSet<QString> customDrivingPersonalityKeys = {"AggressivePersonalityProfile", "RelaxedPersonalityProfile", "StandardPersonalityProfile", "TrafficPersonalityProfile"};
  QSet<QString> longitudinalTuneKeys = {"AccelerationProfile", "DecelerationProfile", "HumanAcceleration", "CoastUpToLeads", "HumanLaneChanges", "LeadDetectionThreshold", "TacoTune", "NavLongitudinalAllowed"};
  QSet<QString> qolKeys = {"CustomCruise", "CustomCruiseLong", "ForceStops", "ForceStopDistanceOffset", "ForceStandstill", "RadarTakeoffs", "IncreasedStoppedDistance", "MapGears", "ReverseCruise", "SetSpeedOffset", "WeatherPresets"};
  QSet<QString> relaxedPersonalityKeys = {"RelaxedFollow", "RelaxedFollowHigh", "RelaxedJerkAcceleration", "RelaxedJerkDeceleration", "RelaxedJerkDanger", "RelaxedJerkSpeed", "RelaxedJerkSpeedDecrease", "ResetRelaxedPersonality"};
  QSet<QString> speedLimitControllerKeys = {"SLCOffsets", "SLCFallback", "SLCOverride", "SLCPriority", "SLCQOL", "SLCVisuals"};
  QSet<QString> speedLimitControllerOffsetsKeys = {"Offset1", "Offset2", "Offset3", "Offset4", "Offset5", "Offset6", "Offset7"};
  QSet<QString> speedLimitControllerQOLKeys = {"SetSpeedLimit", "SLCConfirmation", "SLCLookaheadHigher", "SLCLookaheadLower", "SLCMapboxFiller", "VisionSpeedLimitDetection"};
  QSet<QString> speedLimitControllerVisualKeys = {"ShowSLCOffset", "SLCAbbreviatedSources", "SLCActiveSourcesOnly", "SpeedLimitSources"};
  QSet<QString> standardPersonalityKeys = {"StandardFollow", "StandardFollowHigh", "StandardJerkAcceleration", "StandardJerkDeceleration", "StandardJerkDanger", "StandardJerkSpeed", "StandardJerkSpeedDecrease", "ResetStandardPersonality"};
  QSet<QString> trafficPersonalityKeys = {"TrafficFollow", "TrafficJerkAcceleration", "TrafficJerkDeceleration", "TrafficJerkDanger", "TrafficJerkSpeed", "TrafficJerkSpeedDecrease", "ResetTrafficPersonality"};
  QSet<QString> weatherKeys = {"LowVisibilityOffsets", "RainOffsets", "RainStormOffsets", "SetWeatherKey", "SnowOffsets"};
  QSet<QString> weatherLowVisibilityKeys = {"IncreaseFollowingLowVisibility", "IncreasedStoppedDistanceLowVisibility", "ReduceAccelerationLowVisibility", "ReduceLateralAccelerationLowVisibility"};
  QSet<QString> weatherRainKeys = {"IncreaseFollowingRain", "IncreasedStoppedDistanceRain", "ReduceAccelerationRain", "ReduceLateralAccelerationRain"};
  QSet<QString> weatherRainStormKeys = {"IncreaseFollowingRainStorm", "IncreasedStoppedDistanceRainStorm", "ReduceAccelerationRainStorm", "ReduceLateralAccelerationRainStorm"};
  QSet<QString> weatherSnowKeys = {"IncreaseFollowingSnow", "IncreasedStoppedDistanceSnow", "ReduceAccelerationSnow", "ReduceLateralAccelerationSnow"};

  QSet<QString> parentKeys;



  StarPilotParamValueControl *longitudinalActuatorDelayToggle;
  StarPilotParamValueControl *startAccelToggle;
  StarPilotParamValueControl *stopAccelToggle;
  StarPilotParamValueControl *stoppingDecelRateToggle;
  StarPilotParamValueControl *vEgoStartingToggle;
  StarPilotParamValueControl *vEgoStoppingToggle;

  StarPilotSettingsWindow *parent;

  LabelControl *calibratedLateralAccelerationLabel;
  LabelControl *calibrationProgressLabel;

  Params params;

  QNetworkAccessManager *networkManager;
};
