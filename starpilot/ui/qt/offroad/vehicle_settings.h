#pragma once

#include "starpilot/ui/qt/offroad/starpilot_settings.h"

class StarPilotVehiclesPanel : public StarPilotListWidget {
  Q_OBJECT

public:
  explicit StarPilotVehiclesPanel(StarPilotSettingsWindow *parent, bool forceOpen = false);

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

  QSet<QString> chryslerKeys = {"JeepBrakeHold"};
  QSet<QString> gmKeys = {"GMPedalLongitudinal", "GMDashSpoofOffsets", "IgnoreIgnitionLine", "LongPitch", "RemoteStartBootsComma", "RemapCancelToDistance", "VoltSNG"};
  QSet<QString> hkgKeys = {"HKGRemoteStartBootsComma"};
  QSet<QString> longitudinalKeys = {"GMDashSpoofOffsets", "LongPitch", "RemapCancelToDistance", "SNGHack", "VoltSNG"};
  QSet<QString> subaruKeys = {"SubaruSNG", "SubaruSNGManualParkingBrake"};
  QSet<QString> toyotaKeys = {"ClusterOffset", "LockDoorsTimer", "SNGHack", "ToyotaDoors"};
  QSet<QString> vehicleInfoKeys = {"BlindSpotSupport", "HardwareDetected", "OpenpilotLongitudinal", "PedalSupport", "RadarSupport", "SDSUSupport", "SNGSupport"};

  QSet<QString> parentKeys;

  StarPilotSettingsWindow *parent;

  ParamControl *disableOpenpilotLong;
  ParamControl *forceFingerprint;

  Params params;
  Params params_memory{"", true};

  QMap<QString, QString> carModels;
};
