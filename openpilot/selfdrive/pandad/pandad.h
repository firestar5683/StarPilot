#pragma once

#include <string>

#include "common/params.h"
#include "selfdrive/pandad/panda.h"

void pandad_main_thread(std::vector<std::string> serials);

class PandaSafety {
public:
  PandaSafety(const std::vector<Panda *> &pandas) : pandas_(pandas) {}
  void configureSafetyMode(bool is_onroad);
  Panda *aolOwner();
  bool aolStatusMatches(Panda *owner, const aol_safety_health_t &status) const;

private:
  void updateMultiplexingMode();
  std::string fetchCarParams();
  void setSafetyMode(const std::string &params_string);

  bool initialized_ = false;
  bool log_once_ = false;
  bool safety_configured_ = false;
  bool prev_obd_multiplexing_ = false;
  std::vector<Panda *> pandas_;
  std::vector<std::pair<cereal::CarParams::SafetyModel, uint16_t>> safety_slots_;
  uint16_t alternative_experience_ = 0;
  size_t safety_config_count_ = 0;
  Params params_;
};
