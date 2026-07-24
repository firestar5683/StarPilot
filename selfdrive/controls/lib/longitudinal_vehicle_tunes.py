from dataclasses import dataclass


@dataclass(frozen=True)
class LongitudinalPlannerTune:
  lead_filter_tau: float = 0.45
  accel_slew_rate: float = 0.90
  brake_slew_rate: float = 1.40
  launch_accel: float = 0.35


DEFAULT_TUNE = LongitudinalPlannerTune()

# Vehicle exceptions are deliberately declarative and limited to physical
# response differences. Planning and safety logic remain global.
VEHICLE_TUNES = {
  ("honda", "HONDA_HRV_3G"): LongitudinalPlannerTune(
    lead_filter_tau=0.65,
    accel_slew_rate=0.65,
    brake_slew_rate=1.00,
    launch_accel=0.30,
  ),
}


def get_longitudinal_planner_tune(CP):
  key = (str(getattr(CP, "brand", "")), str(getattr(CP, "carFingerprint", "")))
  return VEHICLE_TUNES.get(key, DEFAULT_TUNE)
